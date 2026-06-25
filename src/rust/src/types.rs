use std::cell::RefCell;
use std::collections::HashMap;
use std::rc::Rc;

// This enum is the heart of the stdlib. Every variable, parameter, and
// return value in the transpiled Ago code will be of this type.
//
// Debug and PartialEq are implemented by hand (below) rather than derived,
// because the Lambda variant holds an `Rc<dyn Fn>` which is neither Debug nor
// PartialEq. Clone is still derived (Rc is Clone).
#[derive(Clone)]
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
    // A first-class function value (lambda or a function reference). Like a map,
    // it is reference-counted and shared on clone; equality is by identity.
    Lambda(AgoLambda),
    Null, // Representing Ago's 'inanis'
}

impl std::fmt::Debug for AgoType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AgoType::Int(v) => write!(f, "Int({:?})", v),
            AgoType::Float(v) => write!(f, "Float({:?})", v),
            AgoType::Bool(v) => write!(f, "Bool({:?})", v),
            AgoType::String(v) => write!(f, "String({:?})", v),
            AgoType::IntList(v) => write!(f, "IntList({:?})", v),
            AgoType::FloatList(v) => write!(f, "FloatList({:?})", v),
            AgoType::BoolList(v) => write!(f, "BoolList({:?})", v),
            AgoType::StringList(v) => write!(f, "StringList({:?})", v),
            AgoType::Struct(v) => write!(f, "Struct({:?})", v.borrow()),
            AgoType::ListAny(v) => write!(f, "ListAny({:?})", v),
            AgoType::Range(v) => write!(f, "Range({:?})", v),
            AgoType::Lambda(_) => write!(f, "Lambda(<fn>)"),
            AgoType::Null => write!(f, "Null"),
        }
    }
}

impl PartialEq for AgoType {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (AgoType::Int(a), AgoType::Int(b)) => a == b,
            (AgoType::Float(a), AgoType::Float(b)) => a == b,
            (AgoType::Bool(a), AgoType::Bool(b)) => a == b,
            (AgoType::String(a), AgoType::String(b)) => a == b,
            (AgoType::IntList(a), AgoType::IntList(b)) => a == b,
            (AgoType::FloatList(a), AgoType::FloatList(b)) => a == b,
            (AgoType::BoolList(a), AgoType::BoolList(b)) => a == b,
            (AgoType::StringList(a), AgoType::StringList(b)) => a == b,
            (AgoType::Struct(a), AgoType::Struct(b)) => *a.borrow() == *b.borrow(),
            (AgoType::ListAny(a), AgoType::ListAny(b)) => a == b,
            (AgoType::Range(a), AgoType::Range(b)) => a == b,
            // Lambdas have no structural equality; compare by identity.
            (AgoType::Lambda(a), AgoType::Lambda(b)) => Rc::ptr_eq(a, b),
            (AgoType::Null, AgoType::Null) => true,
            _ => false,
        }
    }
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
            // Scalars, the homogeneous list variants and lambdas contain no
            // shared mutable cells, so a normal clone is already a deep copy.
            other => other.clone(),
        }
    }

    /// Invoke this value as a function. Panics with a clear message if it is not
    /// a lambda / function value (the semantic checker rejects most such cases,
    /// but a dynamically-typed `inanis` could still reach here).
    pub fn call_lambda(&self, args: &[AgoType]) -> AgoType {
        match self {
            AgoType::Lambda(f) => f(args),
            other => panic!(
                "value of type {} is not callable (not a function)",
                other.type_name()
            ),
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
            AgoType::Lambda(_) => "Lambda",
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
