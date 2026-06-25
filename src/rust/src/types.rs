use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

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
    // A map is Ago's one reference type: it is shared (Rc) and mutable in place
    // (RefCell), so passing a map into a function and mutating it is visible to
    // the caller (Python object / call-by-sharing semantics). Cloning an
    // AgoType::Struct shares the same map; use `exemplium` for a deep copy.
    Struct(Rc<RefCell<HashMap<String, AgoType>>>),
    ListAny(Vec<AgoType>), // For lists of mixed types
    Range(AgoRange),
    Null, // Representing Ago's 'inanis'
}

impl AgoType {
    /// Build a map value from a plain HashMap, wrapping it in the shared,
    /// interior-mutable cell that gives maps their reference semantics.
    pub fn new_struct(map: HashMap<String, AgoType>) -> AgoType {
        AgoType::Struct(Rc::new(RefCell::new(map)))
    }

    /// Recursively deep-copy a value. For maps (and maps nested inside lists)
    /// this allocates fresh, independent cells rather than sharing them.
    pub fn deep_copy(&self) -> AgoType {
        match self {
            AgoType::Struct(m) => {
                let copied: HashMap<String, AgoType> =
                    m.borrow().iter().map(|(k, v)| (k.clone(), v.deep_copy())).collect();
                AgoType::new_struct(copied)
            }
            AgoType::ListAny(v) => AgoType::ListAny(v.iter().map(|x| x.deep_copy()).collect()),
            // Scalars and the homogeneous list variants contain no shared cells,
            // so a normal clone is already a deep copy.
            other => other.clone(),
        }
    }

    /// Human-readable name of this value's variant, for diagnostics.
    /// Mirrors the names reported by the `species` builtin.
    pub fn type_name(&self) -> &'static str {
        match self {
            AgoType::Int(_) => "Int",
            AgoType::Float(_) => "Float",
            AgoType::Bool(_) => "Bool",
            AgoType::String(_) => "String",
            AgoType::IntList(_) => "IntList",
            AgoType::FloatList(_) => "FloatList",
            AgoType::BoolList(_) => "BoolList",
            AgoType::StringList(_) => "StringList",
            AgoType::Struct(_) => "Struct",
            AgoType::ListAny(_) => "ListAny",
            AgoType::Range(_) => "Range",
            AgoType::Null => "Null (inanis)",
        }
    }
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
// Use Rc instead of Box so lambdas can be cloned for recursive functions
pub type AgoLambda = Rc<dyn Fn(&[AgoType]) -> AgoType>;

#[derive(Debug, Clone, PartialEq)]
pub struct AgoRange {
    pub start: AgoInt,
    pub end: AgoInt,
    pub inclusive: bool,
    /// Iteration step magnitude (always >= 1). Direction is inferred from
    /// start/end at iteration time, so a descending range (`start > end`)
    /// counts down. Defaults to 1.
    pub step: AgoInt,
}

impl AgoRange {
    /// Number of elements this range yields when iterated.
    #[inline]
    pub fn count(&self) -> AgoInt {
        let s = self.step.max(1);
        let span = (self.end - self.start).abs();
        if self.inclusive {
            span / s + 1
        } else {
            (span + s - 1) / s
        }
    }

    /// Signed increment applied per step (negative for descending ranges).
    #[inline]
    pub fn increment(&self) -> AgoInt {
        let s = self.step.max(1);
        if self.end >= self.start {
            s
        } else {
            -s
        }
    }
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
