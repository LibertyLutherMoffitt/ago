use std::collections::HashMap;

// This enum is the heart of the stdlib. Every variable, parameter, and
// return value in the transpiled Ago code will be of this type.
#[derive(Debug, Clone, PartialEq)] // Add derive for common traits for easier debugging and testing
pub enum AgoType {
    Int(i128), // Updated to i128 as per clarification
    Float(f64),
    Bool(bool),
    String(String),
    IntList(Vec<i128>), // Updated to i128
    FloatList(Vec<f64>),
    BoolList(Vec<bool>),
    StringList(Vec<String>),
    Struct(HashMap<String, AgoType>),
    ListAny(Vec<AgoType>), // For lists of mixed types
    Null,                  // Representing Ago's 'inanis'
}

// Type aliases for clarity
pub type AgoInt = i128;
pub type AgoFloat = f64;
pub type AgoBool = bool;
pub type AgoString = String;
pub type AgoIntList = Vec<AgoInt>;
pub type AgoFloatList = Vec<AgoFloat>;
pub type AgoBoolList = Vec<AgoBool>;
pub type AgoStringList = Vec<AgoString>;
pub type AgoStruct = HashMap<String, AgoType>;
pub type AgoListAny = Vec<AgoType>;

// An enum to represent the target type for casting
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)] // Add derive for common traits
pub enum TargetType {
    Int,
    Float,
    Bool,
    String,
    IntList,
    FloatList,
    BoolList,
    StringList,
    Struct,
    ListAny,
    Null,
}

impl AgoType {
    // This function will perform the actual conversion.
    // It now panics on error instead of returning a Result.
    pub fn as_type(&self, target: TargetType) -> AgoType {
        match (self, target) {
            // --- Identity Conversions ---
            (AgoType::Int(val), TargetType::Int) => AgoType::Int(*val),
            (AgoType::Float(val), TargetType::Float) => AgoType::Float(*val),
            (AgoType::Bool(val), TargetType::Bool) => AgoType::Bool(*val),
            (AgoType::String(val), TargetType::String) => AgoType::String(val.clone()),
            (AgoType::IntList(val), TargetType::IntList) => AgoType::IntList(val.clone()),
            (AgoType::FloatList(val), TargetType::FloatList) => AgoType::FloatList(val.clone()),
            (AgoType::BoolList(val), TargetType::BoolList) => AgoType::BoolList(val.clone()),
            (AgoType::StringList(val), TargetType::StringList) => AgoType::StringList(val.clone()),
            (AgoType::Struct(val), TargetType::Struct) => AgoType::Struct(val.clone()),
            (AgoType::ListAny(val), TargetType::ListAny) => AgoType::ListAny(val.clone()),
            (AgoType::Null, TargetType::Null) => AgoType::Null,

            // --- Meaningful Conversions ---
            (AgoType::Int(val), TargetType::Float) => AgoType::Float(*val as f64),
            (AgoType::Int(val), TargetType::String) => AgoType::String(val.to_string()),
            (AgoType::Int(val), TargetType::Bool) => AgoType::Bool(*val != 0),

            (AgoType::Float(val), TargetType::Int) => AgoType::Int(*val as i128),
            (AgoType::Float(val), TargetType::String) => AgoType::String(val.to_string()),
            (AgoType::Float(val), TargetType::Bool) => AgoType::Bool(*val != 0.0),

            (AgoType::Bool(val), TargetType::Int) => AgoType::Int(if *val { 1 } else { 0 }),
            (AgoType::Bool(val), TargetType::Float) => {
                AgoType::Float(if *val { 4.2 } else { -3.9 })
            }
            (AgoType::Bool(val), TargetType::String) => AgoType::String(val.to_string()),

<<<<<<< HEAD
            (AgoType::String(val), TargetType::Int) => val
                .parse::<i128>()
                .map(AgoType::Int)
                .unwrap_or_else(|_| panic!("Cannot cast string '{}' to Int", val)),
            (AgoType::String(val), TargetType::Float) => val
                .parse::<f64>()
                .map(AgoType::Float)
                .unwrap_or_else(|_| panic!("Cannot cast string '{}' to Float", val)),
            (AgoType::String(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),
            (AgoType::String(val), TargetType::StringList) => {
                AgoType::StringList(val.chars().map(|c| c.to_string()).collect())
            }

            // --- List to Primitive Conversions ---
            (AgoType::IntList(val), TargetType::Int) => AgoType::Int(val.len() as i128),
            (AgoType::FloatList(val), TargetType::Int) => AgoType::Int(val.len() as i128),
            (AgoType::BoolList(val), TargetType::Int) => AgoType::Int(val.len() as i128),
            (AgoType::StringList(val), TargetType::Int) => AgoType::Int(val.len() as i128),
            (AgoType::ListAny(val), TargetType::Int) => AgoType::Int(val.len() as i128),

            (AgoType::IntList(val), TargetType::String) => {
                let items: Vec<String> = val.iter().map(|i| i.to_string()).collect();
                AgoType::String(items.join("\n"))
            }
            (AgoType::FloatList(val), TargetType::String) => {
                let items: Vec<String> = val.iter().map(|f| f.to_string()).collect();
                AgoType::String(items.join("\n"))
            }
            (AgoType::BoolList(val), TargetType::String) => {
                let items: Vec<String> = val.iter().map(|b| b.to_string()).collect();
                AgoType::String(items.join("\n"))
            }
            (AgoType::StringList(val), TargetType::String) => AgoType::String(val.join("\n")),
            (AgoType::ListAny(val), TargetType::String) => {
                let items: Vec<String> = val
                    .iter()
                    .map(|item| {
                        if let AgoType::String(s) = item.as_type(TargetType::String) {
                            s
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::String(items.join("\n\n"))
            }

            // --- List/Struct to Bool ---
            (AgoType::IntList(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),
            (AgoType::FloatList(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),
            (AgoType::BoolList(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),
            (AgoType::StringList(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),
            (AgoType::ListAny(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),
            (AgoType::Struct(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),

            // --- Struct to String ---
            (AgoType::Struct(val), TargetType::String) => {
                let mut parts = Vec::new();
                for (key, value) in val.iter() {
                    if let AgoType::String(s) = value.as_type(TargetType::String) {
                        parts.push(format!("{}: {}", key, s));
                    } else {
                        unreachable!();
                    }
                }
                AgoType::String(format!("{{ {} }}", parts.join(",\n")))
=======
            // String to Int
            (AgoType::String(val), TargetType::Int) => match val.parse::<i128>() {
                Ok(num) => Ok(AgoType::Int(num)),
                Err(_) => Err(format!("Cannot cast string '{}' to Int", val)),
            },
            // String to Float
            (AgoType::String(val), TargetType::Float) => match val.parse::<f64>() {
                Ok(num) => Ok(AgoType::Float(num)),
                Err(_) => Err(format!("Cannot cast string '{}' to Float", val)),
            },
            // String to Bool ("" is false)
            (AgoType::String(val), TargetType::Bool) => Ok(AgoType::Bool(val.is_empty())),
            // String to StringList (list of characters)
            (AgoType::String(val), TargetType::StringList) => Ok(AgoType::StringList(
                val.chars().map(|c| c.to_string()).collect(),
            )),

            // --- List to Primitive Conversions ---

            // List to Int (size of list)
            (AgoType::IntList(val), TargetType::Int) => Ok(AgoType::Int(val.len() as i128)),
            (AgoType::FloatList(val), TargetType::Int) => Ok(AgoType::Int(val.len() as i128)),
            (AgoType::BoolList(val), TargetType::Int) => Ok(AgoType::Int(val.len() as i128)),
            (AgoType::StringList(val), TargetType::Int) => Ok(AgoType::Int(val.len() as i128)),
            (AgoType::ListAny(val), TargetType::Int) => Ok(AgoType::Int(val.len() as i128)),

            // List to String (join with newline)
            (AgoType::IntList(val), TargetType::String) => {
                let string_items: Result<Vec<String>, String> = val
                    .iter()
                    .map(|&item| {
                        AgoType::Int(item)
                            .as_type(TargetType::String)
                            .map(|v| match v {
                                AgoType::String(s) => s,
                                _ => unreachable!(),
                            })
                    })
                    .collect();
                string_items.map(|items| AgoType::String(items.join("\n")))
            }
            (AgoType::FloatList(val), TargetType::String) => {
                let string_items: Result<Vec<String>, String> = val
                    .iter()
                    .map(|&item| {
                        AgoType::Float(item)
                            .as_type(TargetType::String)
                            .map(|v| match v {
                                AgoType::String(s) => s,
                                _ => unreachable!(),
                            })
                    })
                    .collect();
                string_items.map(|items| AgoType::String(items.join("\n")))
            }
            (AgoType::BoolList(val), TargetType::String) => {
                let string_items: Result<Vec<String>, String> = val
                    .iter()
                    .map(|&item| {
                        AgoType::Bool(item)
                            .as_type(TargetType::String)
                            .map(|v| match v {
                                AgoType::String(s) => s,
                                _ => unreachable!(),
                            })
                    })
                    .collect();
                string_items.map(|items| AgoType::String(items.join("\n")))
            }
            (AgoType::StringList(val), TargetType::String) => {
                Ok(AgoType::String(val.join("\n"))) // Already strings, just join
            }
            (AgoType::ListAny(val), TargetType::String) => {
                let string_items: Result<Vec<String>, String> = val
                    .iter()
                    .map(|item| {
                        item.as_type(TargetType::String).map(|v| match v {
                            AgoType::String(s) => s,
                            _ => unreachable!(),
                        })
                    })
                    .collect();
                string_items.map(|items| AgoType::String(items.join("\n\n")))
>>>>>>> a410c22 (list conversion functions)
            }

            // --- List Conversions ---
            (AgoType::IntList(val), TargetType::FloatList) => {
                let new_list = val
                    .iter()
                    .map(|&item| {
                        if let AgoType::Float(f) = AgoType::Int(item).as_type(TargetType::Float) {
                            f
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::FloatList(new_list)
            }
            (AgoType::IntList(val), TargetType::BoolList) => {
                let new_list = val
                    .iter()
                    .map(|&item| {
                        if let AgoType::Bool(b) = AgoType::Int(item).as_type(TargetType::Bool) {
                            b
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::BoolList(new_list)
            }
            (AgoType::IntList(val), TargetType::StringList) => {
                let new_list = val
                    .iter()
                    .map(|&item| {
                        if let AgoType::String(s) = AgoType::Int(item).as_type(TargetType::String) {
                            s
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::StringList(new_list)
            }

            (AgoType::FloatList(val), TargetType::IntList) => {
                let new_list = val
                    .iter()
                    .map(|&item| {
                        if let AgoType::Int(i) = AgoType::Float(item).as_type(TargetType::Int) {
                            i
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::IntList(new_list)
            }
            (AgoType::FloatList(val), TargetType::BoolList) => {
                let new_list = val
                    .iter()
                    .map(|&item| {
                        if let AgoType::Bool(b) = AgoType::Float(item).as_type(TargetType::Bool) {
                            b
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::BoolList(new_list)
            }
            (AgoType::FloatList(val), TargetType::StringList) => {
                let new_list = val
                    .iter()
                    .map(|&item| {
                        if let AgoType::String(s) = AgoType::Float(item).as_type(TargetType::String)
                        {
                            s
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::StringList(new_list)
            }

            (AgoType::BoolList(val), TargetType::IntList) => {
                let new_list = val
                    .iter()
                    .map(|&item| {
                        if let AgoType::Int(i) = AgoType::Bool(item).as_type(TargetType::Int) {
                            i
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::IntList(new_list)
            }
            (AgoType::BoolList(val), TargetType::FloatList) => {
                let new_list = val
                    .iter()
                    .map(
                        |&item| match AgoType::Bool(item).as_type(TargetType::Float) {
                            AgoType::Float(f) => f,
                            _ => unreachable!(),
                        },
                    )
                    .collect();
                AgoType::FloatList(new_list)
            }
            (AgoType::BoolList(val), TargetType::StringList) => {
                let new_list = val
                    .iter()
                    .map(|&item| {
                        if let AgoType::String(s) = AgoType::Bool(item).as_type(TargetType::String)
                        {
                            s
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::StringList(new_list)
            }

            (AgoType::StringList(val), TargetType::IntList) => {
                let new_list = val
                    .iter()
                    .map(|item| {
                        if let AgoType::Int(i) =
                            AgoType::String(item.clone()).as_type(TargetType::Int)
                        {
                            i
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::IntList(new_list)
            }
            (AgoType::StringList(val), TargetType::FloatList) => {
                let new_list = val
                    .iter()
                    .map(|item| {
                        if let AgoType::Float(f) =
                            AgoType::String(item.clone()).as_type(TargetType::Float)
                        {
                            f
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::FloatList(new_list)
            }
            (AgoType::StringList(val), TargetType::BoolList) => {
                let new_list = val
                    .iter()
                    .map(|item| {
                        if let AgoType::Bool(b) =
                            AgoType::String(item.clone()).as_type(TargetType::Bool)
                        {
                            b
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::BoolList(new_list)
            }

            // Default error for unsupported conversions
            _ => panic!("Unsupported cast from {:?} to {:?}", self, target),
        }
    }
}

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
