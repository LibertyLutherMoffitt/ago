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
    Range(AgoRange),
    Null, // Representing Ago's 'inanis'
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
pub type AgoLambda = Box<dyn Fn(&[AgoType]) -> AgoType>;

#[derive(Debug, Clone, PartialEq)]
pub struct AgoRange {
    pub start: AgoInt,
    pub end: AgoInt,
    pub inclusive: bool,
}

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
    Range,
    Null,
    Any, // For generic/dynamic typing - returns value as-is
}

pub struct FileStruct {
    pub filename: AgoString,
    pub content: AgoString,
    pub filesize: AgoInt,
}
