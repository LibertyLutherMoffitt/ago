pub mod casting;
pub mod collections;
pub mod functions;
pub mod iterators;
pub mod operators;
pub mod regex;
pub mod trace;
pub mod types;

// Re-export everything for easy importing
pub use collections::{
    claverum, get, inseri, misceu, removium, set, validate_list_type, valuum,
};
pub use functions::{
    aequalam, apertu, audies, dici, exei, exemplium, literes, ordina, species, scribi,
};
pub use iterators::{into_iter, into_pairs};
pub use trace::{
    ago_current_line, ago_div, ago_install_panic_hook, ago_mod, ago_set_line,
};
pub use regex::{congruam, congruum};
pub use operators::{
    add, and, bitwise_and, bitwise_or, bitwise_xor, contains, divide, elvis, greater_equal,
    greater_than, less_equal, less_than, modulo, multiply, not, or, slice, sliceto, subtract,
    unary_minus, unary_plus,
};
pub use types::{AgoBool, AgoFloat, AgoInt, AgoLambda, AgoRange, AgoString, AgoType, TargetType};
// Note: casting is done via AgoType::as_type(TargetType::X)
