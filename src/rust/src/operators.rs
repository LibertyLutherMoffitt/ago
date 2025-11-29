use crate::types::{AgoRange, AgoType};

// --- Operator Functions ---

macro_rules! numeric_op {
    ($name:ident, $op:tt) => {
        pub fn $name(left: &AgoType, right: &AgoType) -> AgoType {
            match (left, right) {
                (AgoType::Float(a), AgoType::Float(b)) => AgoType::Float(a $op b),
                (AgoType::Float(a), AgoType::Int(b)) => AgoType::Float(a $op (*b as f64)),
                (AgoType::Int(a), AgoType::Float(b)) => AgoType::Float((*a as f64) $op b),
                (AgoType::Int(a), AgoType::Int(b)) => AgoType::Int(a $op b),
                _ => panic!("Cannot perform numeric operation on {:?} and {:?}", left, right),
            }
        }
    };
}

macro_rules! bitwise_op {
    ($name:ident, $op:tt) => {
        pub fn $name(left: &AgoType, right: &AgoType) -> AgoType {
            match (left, right) {
                (AgoType::Int(a), AgoType::Int(b)) => AgoType::Int(a $op b),
                _ => panic!("Cannot perform bitwise operation on {:?} and {:?}", left, right),
            }
        }
    };
}

macro_rules! comparison_op {
    ($name:ident, $op:tt) => {
        pub fn $name(left: &AgoType, right: &AgoType) -> AgoType {
            let result = match (left, right) {
                (AgoType::Float(a), AgoType::Float(b)) => a $op b,
                (AgoType::Float(a), AgoType::Int(b)) => a $op &(*b as f64),
                (AgoType::Int(a), AgoType::Float(b)) => &(*a as f64) $op b,
                (AgoType::Int(a), AgoType::Int(b)) => a $op b,
                (AgoType::String(a), AgoType::String(b)) => a $op b,
                _ => panic!("Cannot perform comparison on {:?} and {:?}", left, right),
            };
            AgoType::Bool(result)
        }
    };
}

/// Implements the '..' operator for inclusive ranges.
pub fn slice(left: &AgoType, right: &AgoType) -> AgoType {
    match (left, right) {
        (AgoType::Int(start), AgoType::Int(end)) => AgoType::Range(AgoRange {
            start: *start,
            end: *end,
            inclusive: true,
        }),
        _ => panic!(
            "Range operators can only be used with integers, but got {:?} and {:?}",
            left, right
        ),
    }
}

/// Implements the '.<' operator for exclusive ranges.
pub fn sliceto(left: &AgoType, right: &AgoType) -> AgoType {
    match (left, right) {
        (AgoType::Int(start), AgoType::Int(end)) => AgoType::Range(AgoRange {
            start: *start,
            end: *end,
            inclusive: false,
        }),
        _ => panic!(
            "Range operators can only be used with integers, but got {:?} and {:?}",
            left, right
        ),
    }
}

/// Implements the '+' operator.
/// Handles numeric addition, string concatenation, and list concatenation.
pub fn add(left: &AgoType, right: &AgoType) -> AgoType {
    match (left, right) {
        // Numeric
        (AgoType::Float(a), AgoType::Float(b)) => AgoType::Float(a + b),
        (AgoType::Float(a), AgoType::Int(b)) => AgoType::Float(a + (*b as f64)),
        (AgoType::Int(a), AgoType::Float(b)) => AgoType::Float((*a as f64) + b),
        (AgoType::Int(a), AgoType::Int(b)) => AgoType::Int(a + b),

        // String concat
        (AgoType::String(a), AgoType::String(b)) => AgoType::String(format!("{}{}", a, b)),

        // List concat
        (AgoType::IntList(a), AgoType::IntList(b)) => {
            let mut new_list = a.clone();
            new_list.extend_from_slice(b);
            AgoType::IntList(new_list)
        }
        (AgoType::FloatList(a), AgoType::FloatList(b)) => {
            let mut new_list = a.clone();
            new_list.extend_from_slice(b);
            AgoType::FloatList(new_list)
        }
        (AgoType::BoolList(a), AgoType::BoolList(b)) => {
            let mut new_list = a.clone();
            new_list.extend_from_slice(b);
            AgoType::BoolList(new_list)
        }
        (AgoType::StringList(a), AgoType::StringList(b)) => {
            let mut new_list = a.clone();
            new_list.extend_from_slice(b);
            AgoType::StringList(new_list)
        }
        (AgoType::ListAny(a), AgoType::ListAny(b)) => {
            let mut new_list = a.clone();
            new_list.extend_from_slice(b);
            AgoType::ListAny(new_list)
        }

        _ => panic!("Cannot add {:?} and {:?}", left, right),
    }
}

numeric_op!(subtract, -);
numeric_op!(multiply, *);
numeric_op!(divide, /);
numeric_op!(modulo, %);

comparison_op!(greater_than, >);
comparison_op!(greater_equal, >=);
comparison_op!(less_than, <);
comparison_op!(less_equal, <=);

bitwise_op!(bitwise_and, &);
bitwise_op!(bitwise_or, |);
bitwise_op!(bitwise_xor, ^);

/// Implements the logical 'and' operator. Panics if inputs are not booleans.
pub fn and(left: &AgoType, right: &AgoType) -> AgoType {
    match (left, right) {
        (AgoType::Bool(a), AgoType::Bool(b)) => AgoType::Bool(*a && *b),
        _ => panic!("Cannot perform logical 'and' on {:?} and {:?}", left, right),
    }
}

/// Implements the logical 'or' operator. Panics if inputs are not booleans.
pub fn or(left: &AgoType, right: &AgoType) -> AgoType {
    match (left, right) {
        (AgoType::Bool(a), AgoType::Bool(b)) => AgoType::Bool(*a || *b),
        _ => panic!("Cannot perform logical 'or' on {:?} and {:?}", left, right),
    }
}

/// Implements the unary 'not' operator.
pub fn not(val: &AgoType) -> AgoType {
    match val {
        AgoType::Bool(a) => AgoType::Bool(!a),
        _ => panic!("Cannot perform logical 'not' on {:?}", val),
    }
}

/// Implements the unary '-' operator.
pub fn unary_minus(val: &AgoType) -> AgoType {
    match val {
        AgoType::Int(a) => AgoType::Int(-a),
        AgoType::Float(a) => AgoType::Float(-a),
        _ => panic!("Cannot perform unary minus on {:?}", val),
    }
}

/// Implements the unary '+' operator (generally a no-op).
pub fn unary_plus(val: &AgoType) -> AgoType {
    match val {
        AgoType::Int(_) | AgoType::Float(_) => val.clone(),
        _ => panic!("Cannot perform unary plus on {:?}", val),
    }
}

/// Implements the 'in' operator.
pub fn contains(haystack: &AgoType, needle: &AgoType) -> AgoType {
    let result = match haystack {
        AgoType::String(h) => {
            if let AgoType::String(n) = needle {
                h.contains(n)
            } else {
                panic!("Can only search for a String in a String, not {:?}", needle);
            }
        }
        AgoType::Struct(h) => {
            if let AgoType::String(n) = needle {
                h.contains_key(n)
            } else {
                panic!(
                    "Struct keys must be Strings, cannot search for {:?}",
                    needle
                );
            }
        }
        AgoType::IntList(h) => h.contains(match needle {
            AgoType::Int(n) => n,
            _ => panic!("Can only search for an Int in an IntList, not {:?}", needle),
        }),
        AgoType::FloatList(h) => h.contains(match needle {
            AgoType::Float(n) => n,
            _ => panic!(
                "Can only search for a Float in a FloatList, not {:?}",
                needle
            ),
        }),
        AgoType::BoolList(h) => h.contains(match needle {
            AgoType::Bool(n) => n,
            _ => panic!("Can only search for a Bool in a BoolList, not {:?}", needle),
        }),
        AgoType::StringList(h) => h.contains(match needle {
            AgoType::String(n) => n,
            _ => panic!(
                "Can only search for a String in a StringList, not {:?}",
                needle
            ),
        }),
        AgoType::ListAny(h) => h.contains(needle), // relies on AgoType's PartialEq
        _ => panic!("The 'in' operator is not supported for {:?}", haystack),
    };
    AgoType::Bool(result)
}

/// Implements the null-coalescing '?:' operator.
/// Returns the left value if it is not Null. Otherwise, returns the right value.
/// Panics if both values are Null.
pub fn elvis(left: &AgoType, right: &AgoType) -> AgoType {
    if !matches!(left, AgoType::Null) {
        return left.clone();
    }
    if !matches!(right, AgoType::Null) {
        return right.clone();
    }
    panic!("Cannot coalesce two null values with '?:' operator");
}
