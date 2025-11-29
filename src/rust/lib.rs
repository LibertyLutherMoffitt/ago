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
    // It returns a Result, which allows us to handle invalid casts
    // (like converting a struct to an integer) gracefully.
    pub fn as_type(&self, target: TargetType) -> Result<AgoType, String> {
        match (self, target) {
            // --- Identity Conversions ---
            (AgoType::Int(val), TargetType::Int) => Ok(AgoType::Int(*val)),
            (AgoType::Float(val), TargetType::Float) => Ok(AgoType::Float(*val)),
            (AgoType::Bool(val), TargetType::Bool) => Ok(AgoType::Bool(*val)),
            (AgoType::String(val), TargetType::String) => Ok(AgoType::String(val.clone())),
            (AgoType::IntList(val), TargetType::IntList) => Ok(AgoType::IntList(val.clone())),
            (AgoType::FloatList(val), TargetType::FloatList) => Ok(AgoType::FloatList(val.clone())),
            (AgoType::BoolList(val), TargetType::BoolList) => Ok(AgoType::BoolList(val.clone())),
            (AgoType::StringList(val), TargetType::StringList) => Ok(AgoType::StringList(val.clone())),
            (AgoType::Struct(val), TargetType::Struct) => Ok(AgoType::Struct(val.clone())),
            (AgoType::ListAny(val), TargetType::ListAny) => Ok(AgoType::ListAny(val.clone())),
            (AgoType::Null, TargetType::Null) => Ok(AgoType::Null),

            // --- Meaningful Conversions ---

            // Int to Float
            (AgoType::Int(val), TargetType::Float) => Ok(AgoType::Float(*val as f64)),
            // Int to String
            (AgoType::Int(val), TargetType::String) => Ok(AgoType::String(val.to_string())),
            // Int to Bool (0 is false, anything else is true)
            (AgoType::Int(val), TargetType::Bool) => Ok(AgoType::Bool(*val != 0)),

            // Float to Int (truncates)
            (AgoType::Float(val), TargetType::Int) => Ok(AgoType::Int(*val as i128)),
            // Float to String
            (AgoType::Float(val), TargetType::String) => Ok(AgoType::String(val.to_string())),
            // Float to Bool (0.0 is false, anything else is true)
            (AgoType::Float(val), TargetType::Bool) => Ok(AgoType::Bool(*val != 0.0)),

            // Bool to Int (true=1, false=0)
            (AgoType::Bool(val), TargetType::Int) => Ok(AgoType::Int(if *val { 1 } else { 0 })),
            // Bool to Float (true=1.0, false=0.0)
            (AgoType::Bool(val), TargetType::Float) => Ok(AgoType::Float(if *val { 1.0 } else { 0.0 })),
            // Bool to String
            (AgoType::Bool(val), TargetType::String) => Ok(AgoType::String(val.to_string())),

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
            // String to Bool (empty string is false, "true" is true, "false" is false, others error?)
            // For now, let's say "true" (case-insensitive) is true, "false" is false, others error.
            (AgoType::String(val), TargetType::Bool) => {
                let lower_val = val.to_lowercase();
                if lower_val == "true" {
                    Ok(AgoType::Bool(true))
                } else if lower_val == "false" {
                    Ok(AgoType::Bool(false))
                } else {
                    Err(format!("Cannot cast string '{}' to Bool", val))
                }
            }

            // --- List Conversions (e.g., IntList to StringList) ---
            // This will require iterating and casting each element.
            (AgoType::IntList(val), TargetType::StringList) => {
                let new_list: Result<Vec<String>, String> = val.iter()
                    .map(|&item| AgoType::Int(item).as_type(TargetType::String).map(|v| match v { AgoType::String(s) => s, _ => unreachable!() }))
                    .collect();
                new_list.map(AgoType::StringList)
            }
            // ... other list conversions will follow a similar pattern ...

            // --- Struct and ListAny conversions ---
            // These are more complex and might require specific rules or be disallowed.
            // For now, most direct conversions to/from these types will be errors.

            // Default error for unsupported conversions
            _ => Err(format!("Unsupported cast from {:?} to {:?}", self, target)),
        }
    }
}
