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

fn main() {
    let mut producta = AgoType::Int(1);
    for ia in into_iter(&slice(&AgoType::Int(1), &AgoType::Int(5))) {
        producta = multiply(&producta.clone(), &ia.clone());
    }
    dici(&producta.clone().as_type(TargetType::String));
}