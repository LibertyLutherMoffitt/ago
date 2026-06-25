use crate::types::{AgoRange, AgoType};

/// Length of an indexable collection, if it has one (for negative-index math).
#[inline]
fn index_len(iter: &AgoType) -> Option<usize> {
    match iter {
        AgoType::IntList(l) => Some(l.len()),
        AgoType::FloatList(l) => Some(l.len()),
        AgoType::BoolList(l) => Some(l.len()),
        AgoType::StringList(l) => Some(l.len()),
        AgoType::ListAny(l) => Some(l.len()),
        AgoType::String(s) => Some(s.chars().count()),
        _ => None,
    }
}

/// Python-style negative indexing: a negative integer index counts from the end
/// of the collection (`-1` is the last element). Returns the key unchanged for
/// non-negative ints, non-int keys, or non-indexable collections. Out-of-range
/// negatives stay negative and fall through to the usual out-of-bounds panic.
#[inline]
fn norm_index(iter: &AgoType, n: &AgoType) -> AgoType {
    if let AgoType::Int(i) = n {
        if *i < 0 {
            if let Some(len) = index_len(iter) {
                return AgoType::Int(len as i128 + *i);
            }
        }
    }
    n.clone()
}

/// Helper to compute slice bounds from a range, supporting negative bounds
/// (counted from the end, Python-style).
#[inline]
fn range_bounds(range: &AgoRange, len: usize) -> (usize, usize) {
    let norm = |v: i128| -> i128 {
        if v < 0 {
            len as i128 + v
        } else {
            v
        }
    };
    let start = norm(range.start).max(0).min(len as i128) as usize;
    let end_raw = norm(range.end);
    let end = if range.inclusive {
        (end_raw + 1).clamp(0, len as i128) as usize
    } else {
        end_raw.clamp(0, len as i128) as usize
    };
    (start.min(len), end.min(len))
}

/// Gets a value from an indexable AgoType. Panics on error.
#[inline]
pub fn get(iter: &AgoType, n: &AgoType) -> AgoType {
    let n_owned = norm_index(iter, n);
    let n = &n_owned;
    match (iter, n) {
        // --- List Access by Index ---
        (AgoType::IntList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            list.get(idx)
                .map(|val| AgoType::Int(*val))
                .expect(&format!("Index out of bounds: {}", idx))
        }
        (AgoType::FloatList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            list.get(idx)
                .map(|val| AgoType::Float(*val))
                .expect(&format!("Index out of bounds: {}", idx))
        }
        (AgoType::BoolList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            list.get(idx)
                .map(|val| AgoType::Bool(*val))
                .expect(&format!("Index out of bounds: {}", idx))
        }
        (AgoType::StringList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            list.get(idx)
                .map(|val| AgoType::String(val.clone()))
                .expect(&format!("Index out of bounds: {}", idx))
        }
        (AgoType::ListAny(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            list.get(idx)
                .map(|val| val.clone())
                .expect(&format!("Index out of bounds: {}", idx))
        }

        // --- List Access by Range (sublists) ---
        (AgoType::IntList(list), AgoType::Range(range)) => {
            let (start, end) = range_bounds(range, list.len());
            AgoType::IntList(list[start..end].to_vec())
        }
        (AgoType::FloatList(list), AgoType::Range(range)) => {
            let (start, end) = range_bounds(range, list.len());
            AgoType::FloatList(list[start..end].to_vec())
        }
        (AgoType::BoolList(list), AgoType::Range(range)) => {
            let (start, end) = range_bounds(range, list.len());
            AgoType::BoolList(list[start..end].to_vec())
        }
        (AgoType::StringList(list), AgoType::Range(range)) => {
            let (start, end) = range_bounds(range, list.len());
            AgoType::StringList(list[start..end].to_vec())
        }
        (AgoType::ListAny(list), AgoType::Range(range)) => {
            let (start, end) = range_bounds(range, list.len());
            AgoType::ListAny(list[start..end].to_vec())
        }

        // --- String Access (get character) ---
        (AgoType::String(s), AgoType::Int(index)) => {
            let idx = *index as usize;
            s.chars()
                .nth(idx)
                .map(|c| AgoType::String(c.to_string()))
                .expect(&format!("Index out of bounds: {}", idx))
        }

        // --- String Access by Range (substring) ---
        (AgoType::String(s), AgoType::Range(range)) => {
            let chars: Vec<char> = s.chars().collect();
            let (start, end) = range_bounds(range, chars.len());
            AgoType::String(chars[start..end].iter().collect())
        }

        // --- Struct Access ---
        // A missing key yields inanis (Null) rather than panicking, matching
        // invena's "not found -> inanis" convention and enabling default/get
        // and set-membership idioms without a separate `in` check.
        (AgoType::Struct(map), AgoType::String(key)) => {
            map.borrow().get(key).cloned().unwrap_or(AgoType::Null)
        }

        // --- Error Cases ---
        (AgoType::Struct(_), other) => panic!("Struct key must be a String, but got {:?}", other),
        (
            AgoType::IntList(_)
            | AgoType::FloatList(_)
            | AgoType::BoolList(_)
            | AgoType::StringList(_)
            | AgoType::ListAny(_)
            | AgoType::String(_),
            other,
        ) => {
            panic!("Index must be an Int or Range, but got {:?}", other)
        }
        (other, _) => panic!("Cannot call 'get' on type {:?}", other),
    }
}

/// Sets a value in a mutable, indexable AgoType. Panics on error.
pub fn set(iter: &mut AgoType, n: &AgoType, value: &AgoType) {
    let n_owned = norm_index(iter, n);
    let n = &n_owned;
    match (iter, n) {
        // --- List Mutation ---
        (AgoType::IntList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let Some(elem) = list.get_mut(idx) {
                if let AgoType::Int(new_val) = value.clone() {
                    *elem = new_val;
                } else {
                    panic!("Cannot set value of type {:?} in an IntList", value);
                }
            } else {
                panic!("Index out of bounds: {}", idx);
            }
        }
        (AgoType::FloatList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let Some(elem) = list.get_mut(idx) {
                if let AgoType::Float(new_val) = value.clone() {
                    *elem = new_val;
                } else {
                    panic!("Cannot set value of type {:?} in a FloatList", value);
                }
            } else {
                panic!("Index out of bounds: {}", idx);
            }
        }
        (AgoType::BoolList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let Some(elem) = list.get_mut(idx) {
                if let AgoType::Bool(new_val) = value.clone() {
                    *elem = new_val;
                } else {
                    panic!("Cannot set value of type {:?} in a BoolList", value);
                }
            } else {
                panic!("Index out of bounds: {}", idx);
            }
        }
        (AgoType::StringList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let Some(elem) = list.get_mut(idx) {
                if let AgoType::String(new_val) = value.clone() {
                    *elem = new_val;
                } else {
                    panic!("Cannot set value of type {:?} in a StringList", value);
                }
            } else {
                panic!("Index out of bounds: {}", idx);
            }
        }
        (AgoType::ListAny(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let Some(elem) = list.get_mut(idx) {
                *elem = value.clone(); // ListAny can hold any AgoType
            } else {
                panic!("Index out of bounds: {}", idx);
            }
        }

        // --- String Mutation ---
        (AgoType::String(s), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let AgoType::String(char_to_set) = value {
                if char_to_set.chars().count() != 1 {
                    panic!(
                        "Cannot set string with value '{}' that is not a single character",
                        char_to_set
                    );
                }
                let mut chars: Vec<char> = s.chars().collect();
                if idx < chars.len() {
                    chars[idx] = char_to_set.chars().next().unwrap(); // Safe because we checked count() == 1
                    *s = chars.into_iter().collect();
                } else {
                    panic!("Index out of bounds: {}", idx);
                }
            } else {
                panic!("Cannot set string character with value of type {:?}", value);
            }
        }

        // --- Struct Mutation ---
        (AgoType::Struct(map), AgoType::String(key)) => {
            map.borrow_mut().insert(key.clone(), value.clone());
        }

        // --- Error Cases ---
        (AgoType::Struct(_), other) => panic!("Struct key must be a String, but got {:?}", other),
        (
            AgoType::IntList(_)
            | AgoType::FloatList(_)
            | AgoType::BoolList(_)
            | AgoType::StringList(_)
            | AgoType::ListAny(_),
            other,
        ) => {
            panic!("Index must be an Int, but got {:?}", other)
        }
        (other, _) => panic!("Cannot call 'set' on type {:?}", other),
    }
}

/// Inserts a value into an indexable AgoType. Panics on error.
/// Name ends in -i (returns null/inanis)
#[inline]
pub fn inseri(coll: &mut AgoType, key: &AgoType, value: &AgoType) {
    let key_owned = norm_index(coll, key);
    let key = &key_owned;
    match (coll, key) {
        // --- List Insertion ---
        (AgoType::IntList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let AgoType::Int(new_val) = value {
                list.insert(idx, *new_val);
            } else {
                panic!("Cannot insert value of type {:?} into an IntList", value);
            }
        }
        (AgoType::FloatList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let AgoType::Float(new_val) = value {
                list.insert(idx, *new_val);
            } else {
                panic!("Cannot insert value of type {:?} into a FloatList", value);
            }
        }
        (AgoType::BoolList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let AgoType::Bool(new_val) = value {
                list.insert(idx, *new_val);
            } else {
                panic!("Cannot insert value of type {:?} into a BoolList", value);
            }
        }
        (AgoType::StringList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let AgoType::String(new_val) = value {
                list.insert(idx, new_val.clone());
            } else {
                panic!("Cannot insert value of type {:?} into a StringList", value);
            }
        }
        (AgoType::ListAny(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            list.insert(idx, value.clone());
        }

        // --- Struct Insertion (same as set) ---
        (AgoType::Struct(map), AgoType::String(key)) => {
            map.borrow_mut().insert(key.clone(), value.clone());
        }

        // --- Error Cases ---
        (AgoType::Struct(_), other) => panic!("Struct key must be a String, but got {:?}", other),
        (
            AgoType::IntList(_)
            | AgoType::FloatList(_)
            | AgoType::BoolList(_)
            | AgoType::StringList(_)
            | AgoType::ListAny(_),
            other,
        ) => {
            panic!("Index must be an Int, but got {:?}", other)
        }
        (other, _) => panic!("Cannot call 'inseri' on type {:?}", other),
    }
}

/// Removes a value from an indexable AgoType and returns it. Panics on error.
/// Name ends in -ium (returns Any)
pub fn removium(coll: &mut AgoType, key: &AgoType) -> AgoType {
    let key_owned = norm_index(coll, key);
    let key = &key_owned;
    match (coll, key) {
        // --- List Removal ---
        (AgoType::IntList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            AgoType::Int(list.remove(idx))
        }
        (AgoType::FloatList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            AgoType::Float(list.remove(idx))
        }
        (AgoType::BoolList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            AgoType::Bool(list.remove(idx))
        }
        (AgoType::StringList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            AgoType::String(list.remove(idx))
        }
        (AgoType::ListAny(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            list.remove(idx)
        }

        // --- Struct Removal ---
        (AgoType::Struct(map), AgoType::String(key)) => {
            let removed = map.borrow_mut().remove(key);
            removed.expect(&format!("Key not found: {}", key))
        }

        // --- Error Cases ---
        (AgoType::Struct(_), other) => panic!("Struct key must be a String, but got {:?}", other),
        (
            AgoType::IntList(_)
            | AgoType::FloatList(_)
            | AgoType::BoolList(_)
            | AgoType::StringList(_)
            | AgoType::ListAny(_),
            other,
        ) => {
            panic!("Index must be an Int, but got {:?}", other)
        }
        (other, _) => panic!("Cannot call 'removium' on type {:?}", other),
    }
}

/// Keys of a struct as a sorted string list (sorted for deterministic output).
/// Name ends in -erum (returns string list).
pub fn claverum(coll: &AgoType) -> AgoType {
    match coll {
        AgoType::Struct(m) => {
            let mut keys: Vec<String> = m.borrow().keys().cloned().collect();
            keys.sort();
            AgoType::StringList(keys)
        }
        _ => panic!("claverum expects a Struct, got {:?}", coll),
    }
}

/// Values of a struct as a list, ordered by sorted key for determinism.
/// Name ends in -uum (returns list_any).
pub fn valuum(coll: &AgoType) -> AgoType {
    match coll {
        AgoType::Struct(m) => {
            let m = m.borrow();
            let mut keys: Vec<&String> = m.keys().collect();
            keys.sort();
            AgoType::ListAny(keys.into_iter().map(|k| m[k].clone()).collect())
        }
        _ => panic!("valuum expects a Struct, got {:?}", coll),
    }
}

/// Merge two structs into a new struct; keys in `b` override keys in `a`.
/// Name ends in -u (returns struct).
pub fn misceu(a: &AgoType, b: &AgoType) -> AgoType {
    match (a, b) {
        (AgoType::Struct(ma), AgoType::Struct(mb)) => {
            let mut out = ma.borrow().clone();
            for (k, v) in mb.borrow().iter() {
                out.insert(k.clone(), v.clone());
            }
            AgoType::new_struct(out)
        }
        _ => panic!("misceu expects two Structs, got {:?} and {:?}", a, b),
    }
}

/// Validates that all elements in a ListAny match the expected element type.
/// Used for runtime type checking when assigning to typed lists.
pub fn validate_list_type(list: &AgoType, expected_elem: &str) -> AgoType {
    if let AgoType::ListAny(items) = list {
        for (i, item) in items.iter().enumerate() {
            let actual_type = match item {
                AgoType::Int(_) => "int",
                AgoType::Float(_) => "float",
                AgoType::Bool(_) => "bool",
                AgoType::String(_) => "string",
                AgoType::IntList(_) => "int_list",
                AgoType::FloatList(_) => "float_list",
                AgoType::BoolList(_) => "bool_list",
                AgoType::StringList(_) => "string_list",
                AgoType::ListAny(_) => "list_any",
                AgoType::Struct(_) => "struct",
                AgoType::Range(_) => "range",
                AgoType::Null => "null",
            };

            // Check if types match
            let matches = actual_type == expected_elem
                // Allow int in float list (widening)
                || (actual_type == "int" && expected_elem == "float");

            if !matches {
                panic!(
                    "List element {} has type '{}', but list expects '{}' elements",
                    i, actual_type, expected_elem
                );
            }
        }
    }
    list.clone()
}
