pub mod casting;
pub mod collections;
pub mod functions;
pub mod iterators;
pub mod operators;
pub mod types;

// Re-export everything for easy importing
pub use collections::{get, insero, removeo, set};
pub use functions::{aequalam, apertu, claverum, dici, exei, species};
pub use iterators::into_iter;
pub use operators::{
    add, and, bitwise_and, bitwise_or, bitwise_xor, contains, divide, elvis, greater_equal,
    greater_than, less_equal, less_than, modulo, multiply, not, or, slice, sliceto, subtract,
    unary_minus, unary_plus,
};
pub use types::{AgoBool, AgoFloat, AgoInt, AgoRange, AgoString, AgoType, TargetType};
// Note: casting is done via AgoType::as_type(TargetType::X)
