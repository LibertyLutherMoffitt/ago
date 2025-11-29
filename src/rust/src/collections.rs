use crate::types::AgoType;

/// Gets a value from an indexable AgoType. Panics on error.
pub fn get(iter: &AgoType, n: &AgoType) -> AgoType {
    match (iter, n) {
        // --- List Access ---
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

        // --- String Access (get character) ---
        (AgoType::String(s), AgoType::Int(index)) => {
            let idx = *index as usize;
            s.chars()
                .nth(idx)
                .map(|c| AgoType::String(c.to_string()))
                .expect(&format!("Index out of bounds: {}", idx))
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
            panic!("Index must be an Int, but got {:?}", other)
        }
        (other, _) => panic!("Cannot call 'get' on type {:?}", other),
    }
}

/// Sets a value in a mutable, indexable AgoType. Panics on error.
pub fn set(iter: &mut AgoType, n: &AgoType, value: AgoType) {
    match (iter, n) {
        // --- List Mutation ---
        (AgoType::IntList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let Some(elem) = list.get_mut(idx) {
                if let AgoType::Int(new_val) = value {
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
                if let AgoType::Float(new_val) = value {
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
                if let AgoType::Bool(new_val) = value {
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
                if let AgoType::String(new_val) = value {
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
                *elem = value; // ListAny can hold any AgoType
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
            map.insert(key.clone(), value);
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
pub fn insero(coll: &mut AgoType, key: &AgoType, value: AgoType) {
    match (coll, key) {
        // --- List Insertion ---
        (AgoType::IntList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let AgoType::Int(new_val) = value {
                list.insert(idx, new_val);
            } else {
                panic!("Cannot insert value of type {:?} into an IntList", value);
            }
        }
        (AgoType::FloatList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let AgoType::Float(new_val) = value {
                list.insert(idx, new_val);
            } else {
                panic!("Cannot insert value of type {:?} into a FloatList", value);
            }
        }
        (AgoType::BoolList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let AgoType::Bool(new_val) = value {
                list.insert(idx, new_val);
            } else {
                panic!("Cannot insert value of type {:?} into a BoolList", value);
            }
        }
        (AgoType::StringList(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            if let AgoType::String(new_val) = value {
                list.insert(idx, new_val);
            } else {
                panic!("Cannot insert value of type {:?} into a StringList", value);
            }
        }
        (AgoType::ListAny(list), AgoType::Int(index)) => {
            let idx = *index as usize;
            list.insert(idx, value);
        }

        // --- Struct Insertion (same as set) ---
        (AgoType::Struct(map), AgoType::String(key)) => {
            map.insert(key.clone(), value);
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
        (other, _) => panic!("Cannot call 'insero' on type {:?}", other),
    }
}

/// Removes a value from an indexable AgoType and returns it. Panics on error.
pub fn removeo(coll: &mut AgoType, key: &AgoType) -> AgoType {
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
        (other, _) => panic!("Cannot call 'removeo' on type {:?}", other),
    }
}
