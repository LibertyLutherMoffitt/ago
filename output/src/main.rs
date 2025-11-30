use ago_stdlib::{
    AgoType, AgoRange, TargetType,
    add, subtract, multiply, divide, modulo,
    greater_than, greater_equal, less_than, less_equal,
    and, or, not, bitwise_and, bitwise_or, bitwise_xor,
    slice, sliceto, contains, elvis,
    unary_minus, unary_plus,
    get, set, insero, removeo, into_iter,
    dici, apertu, species, exei, aequalam, claverum,
};
use std::collections::HashMap;

fn numbera() -> AgoType {
    return AgoType::Int(99);
    AgoType::Null
}

fn main() {
    dici(&numbera().as_type(TargetType::String));
}