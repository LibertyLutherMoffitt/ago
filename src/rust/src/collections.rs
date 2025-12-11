use crate::types::{AgoRange, AgoType};

/// Helper to compute slice bounds from a range
#[inline]
fn range_bounds(range: &AgoRange, len: usize) -> (usize, usize) {
    let start = range.start.max(0) as usize;
    let end = if range.inclusive {
        (range.end + 1).min(len as i128) as usize
    } else {
        range.end.min(len as i128) as usize
    };
    (start.min(len), end.min(len))
}

/// Gets a value from an indexable AgoType. Panics on error.
#[inline]
pub fn get(iter: &AgoType, n: &AgoType) -> AgoType {
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
        (AgoType::Struct(map), AgoType::String(key)) => map
            .get(key)
            .map(|val| val.clone())
            .expect(&format!("Key not found: {}", key)),

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
            map.insert(key.clone(), value.clone());
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
            map.insert(key.clone(), value.clone());
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
            map.remove(key).expect(&format!("Key not found: {}", key))
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
