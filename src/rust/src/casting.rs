use crate::types::{AgoRange, AgoType, TargetType};

impl AgoType {
    // This function will perform the actual conversion.
    // It now panics on error instead of returning a Result.
    pub fn as_type(&self, target: TargetType) -> AgoType {
        match (self, target) {
            // --- Any Conversions (dynamic/generic typing) ---
            // Casting TO Any: just clone the value (AgoType IS the Any type)
            (_, TargetType::Any) => self.clone(),

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
            (AgoType::Range(val), TargetType::Range) => AgoType::Range(val.clone()),
            (AgoType::Null, TargetType::Null) => AgoType::Null,

            // --- Null Conversions ---
            (AgoType::Null, TargetType::Bool) => AgoType::Bool(false),
            (AgoType::Null, TargetType::String) => AgoType::String("inanis".to_string()),
            (AgoType::Null, TargetType::Int) => AgoType::Int(0),
            (AgoType::Null, TargetType::Float) => AgoType::Float(0.0),

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
                AgoType::String(items.join("\n"))
            }

            // --- List/Struct/Range to Bool ---
            (AgoType::IntList(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),
            (AgoType::FloatList(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),
            (AgoType::BoolList(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),
            (AgoType::StringList(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),
            (AgoType::ListAny(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),
            (AgoType::Struct(val), TargetType::Bool) => AgoType::Bool(!val.is_empty()),
            (AgoType::Range(val), TargetType::Bool) => {
                let is_empty = if val.inclusive {
                    val.start > val.end
                } else {
                    val.start >= val.end
                };
                AgoType::Bool(!is_empty)
            }

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
                AgoType::String(format!("{{ {} }}", parts.join(", ")))
            }

            // --- Range to String ---
            (AgoType::Range(val), TargetType::String) => {
                let operator = if val.inclusive { ".." } else { ".<" };
                AgoType::String(format!("{}{}{}", val.start, operator, val.end))
            }

            // --- Range to IntList ---
            (AgoType::Range(val), TargetType::IntList) => {
                let mut vec = Vec::new();
                if val.start > val.end {
                    return AgoType::IntList(vec);
                }
                let mut i = val.start;
                let end = val.end;
                while i < end {
                    vec.push(i);
                    i += 1;
                }
                if val.inclusive && i == end {
                    vec.push(i);
                }
                AgoType::IntList(vec)
            }

            // --- List to Range ---
            (AgoType::IntList(val), TargetType::Range) => {
                let len = val.len() as i128;
                AgoType::Range(AgoRange {
                    start: 0,
                    end: len - 1,
                    inclusive: true,
                })
            }
            (AgoType::FloatList(val), TargetType::Range) => {
                let len = val.len() as i128;
                AgoType::Range(AgoRange {
                    start: 0,
                    end: len - 1,
                    inclusive: true,
                })
            }
            (AgoType::BoolList(val), TargetType::Range) => {
                let len = val.len() as i128;
                AgoType::Range(AgoRange {
                    start: 0,
                    end: len - 1,
                    inclusive: true,
                })
            }
            (AgoType::StringList(val), TargetType::Range) => {
                let len = val.len() as i128;
                AgoType::Range(AgoRange {
                    start: 0,
                    end: len - 1,
                    inclusive: true,
                })
            }
            (AgoType::ListAny(val), TargetType::Range) => {
                let len = val.len() as i128;
                AgoType::Range(AgoRange {
                    start: 0,
                    end: len - 1,
                    inclusive: true,
                })
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

            // --- Typed lists to ListAny ---
            (AgoType::IntList(val), TargetType::ListAny) => {
                AgoType::ListAny(val.iter().map(|&i| AgoType::Int(i)).collect())
            }
            (AgoType::FloatList(val), TargetType::ListAny) => {
                AgoType::ListAny(val.iter().map(|&f| AgoType::Float(f)).collect())
            }
            (AgoType::BoolList(val), TargetType::ListAny) => {
                AgoType::ListAny(val.iter().map(|&b| AgoType::Bool(b)).collect())
            }
            (AgoType::StringList(val), TargetType::ListAny) => {
                AgoType::ListAny(val.iter().map(|s| AgoType::String(s.clone())).collect())
            }

            // --- ListAny to typed lists ---
            (AgoType::ListAny(val), TargetType::StringList) => {
                let new_list = val
                    .iter()
                    .map(|item| {
                        if let AgoType::String(s) = item.clone().as_type(TargetType::String) {
                            s
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::StringList(new_list)
            }
            (AgoType::ListAny(val), TargetType::IntList) => {
                let new_list = val
                    .iter()
                    .map(|item| {
                        if let AgoType::Int(i) = item.clone().as_type(TargetType::Int) {
                            i
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::IntList(new_list)
            }
            (AgoType::ListAny(val), TargetType::FloatList) => {
                let new_list = val
                    .iter()
                    .map(|item| {
                        if let AgoType::Float(f) = item.clone().as_type(TargetType::Float) {
                            f
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::FloatList(new_list)
            }
            (AgoType::ListAny(val), TargetType::BoolList) => {
                let new_list = val
                    .iter()
                    .map(|item| {
                        if let AgoType::Bool(b) = item.clone().as_type(TargetType::Bool) {
                            b
                        } else {
                            unreachable!()
                        }
                    })
                    .collect();
                AgoType::BoolList(new_list)
            }

            // --- ListAny to Struct ---
            // Rules:
            // 1. If all elements are strings: keys are strings, values are IntList of original indices
            // 2. If all elements are 2-element lists: first item is key (as string), second is value
            // 3. Otherwise: keys are index strings ("0", "1", ...), values are elements
            (AgoType::ListAny(val), TargetType::Struct) => {
                use std::collections::HashMap;
                
                // Check if all elements are strings
                let all_strings = val.iter().all(|item| matches!(item, AgoType::String(_)));
                
                if all_strings && !val.is_empty() {
                    // Case 1: All strings - values become keys, values are lists of original indices
                    let mut result: HashMap<String, Vec<i128>> = HashMap::new();
                    for (idx, item) in val.iter().enumerate() {
                        if let AgoType::String(s) = item {
                            result.entry(s.clone()).or_insert_with(Vec::new).push(idx as i128);
                        }
                    }
                    let struct_map: HashMap<String, AgoType> = result
                        .into_iter()
                        .map(|(k, v)| (k, AgoType::IntList(v)))
                        .collect();
                    return AgoType::Struct(struct_map);
                }
                
                // Check if all elements are 2-element lists
                let all_pairs = val.iter().all(|item| {
                    match item {
                        AgoType::ListAny(inner) => inner.len() == 2,
                        _ => false,
                    }
                });
                
                if all_pairs && !val.is_empty() {
                    // Case 2: All pairs - first item is key, second is value
                    let mut struct_map: HashMap<String, AgoType> = HashMap::new();
                    for item in val.iter() {
                        if let AgoType::ListAny(inner) = item {
                            let key = match &inner[0] {
                                AgoType::String(s) => s.clone(),
                                other => {
                                    if let AgoType::String(s) = other.as_type(TargetType::String) {
                                        s
                                    } else {
                                        unreachable!()
                                    }
                                }
                            };
                            struct_map.insert(key, inner[1].clone());
                        }
                    }
                    return AgoType::Struct(struct_map);
                }
                
                // Case 3: Default - keys are index strings
                let struct_map: HashMap<String, AgoType> = val
                    .iter()
                    .enumerate()
                    .map(|(idx, item)| (idx.to_string(), item.clone()))
                    .collect();
                AgoType::Struct(struct_map)
            }

            // --- Struct to StringList (keys) ---
            (AgoType::Struct(val), TargetType::StringList) => {
                let keys: Vec<String> = val.keys().cloned().collect();
                AgoType::StringList(keys)
            }

            // Default error for unsupported conversions
            _ => panic!("Unsupported cast from {:?} to {:?}", self, target),
        }
    }
}
