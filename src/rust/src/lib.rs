pub mod casting;
pub mod collections;
pub mod functions;
pub mod iterators;
pub mod operators;
pub mod types;

// Re-export everything for easy importing
pub use types::{AgoType, TargetType, AgoRange, AgoInt, AgoFloat, AgoBool, AgoString};
pub use operators::{
    add, subtract, multiply, divide, modulo,
    greater_than, greater_equal, less_than, less_equal,
    and, or, not, bitwise_and, bitwise_or, bitwise_xor,
    slice, sliceto, contains, elvis,
    unary_minus, unary_plus,
};
pub use collections::{get, set, insero, removeo};
pub use functions::{dici, apertu, species, exei, aequalam, claverum};
pub use iterators::into_iter;
// Note: casting is done via AgoType::as_type(TargetType::X)
