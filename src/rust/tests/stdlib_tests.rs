//! Integration tests for the ago_stdlib crate.

use ago_stdlib::types::{AgoRange, AgoType, TargetType};
use ago_stdlib::collections::{get, set, insero, removeo};
use ago_stdlib::functions::{aequalem, claverum, species};
use ago_stdlib::operators::{
    add, and, bitwise_and, bitwise_or, bitwise_xor, contains, divide, elvis, greater_equal,
    greater_than, less_equal, less_than, modulo, multiply, not, or, slice, sliceto, subtract, unary_minus,
    unary_plus,
};
use std::collections::HashMap;

// --- Helpers ---

fn sample_struct() -> AgoType {
    let mut map = HashMap::new();
    map.insert("a".to_string(), AgoType::Int(1));
    map.insert(
        "b".to_string(),
        AgoType::String("hello".to_string()),
    );
    AgoType::Struct(map)
}

fn sample_any_list() -> AgoType {
    AgoType::ListAny(vec![
        AgoType::Int(1),
        AgoType::String("two".to_string()),
        AgoType::Bool(false),
    ])
}

// --- Test Cases ---

#[test]
fn test_species() {
    assert_eq!(
        species(&AgoType::Int(10)),
        AgoType::String("Int".to_string())
    );
    assert_eq!(
        species(&AgoType::Float(1.0)),
        AgoType::String("Float".to_string())
    );
    assert_eq!(
        species(&AgoType::Bool(true)),
        AgoType::String("Bool".to_string())
    );
    assert_eq!(
        species(&AgoType::String("s".to_string())),
        AgoType::String("String".to_string())
    );
    assert_eq!(
        species(&AgoType::IntList(vec![])),
        AgoType::String("IntList".to_string())
    );
    assert_eq!(
        species(&AgoType::FloatList(vec![])),
        AgoType::String("FloatList".to_string())
    );
    assert_eq!(
        species(&AgoType::BoolList(vec![])),
        AgoType::String("BoolList".to_string())
    );
    assert_eq!(
        species(&AgoType::StringList(vec![])),
        AgoType::String("StringList".to_string())
    );
    assert_eq!(
        species(&AgoType::Struct(HashMap::new())),
        AgoType::String("Struct".to_string())
    );
    assert_eq!(
        species(&AgoType::ListAny(vec![])),
        AgoType::String("ListAny".to_string())
    );
    assert_eq!(
        species(&AgoType::Null),
        AgoType::String("Null".to_string())
    );
    assert_eq!(
        species(&AgoType::Range(AgoRange { start: 1, end: 5, inclusive: true })),
        AgoType::String("Range".to_string())
    );
}

#[test]
fn test_as_type_primitive_conversions() {
    // Int
    assert_eq!(AgoType::Int(42).as_type(TargetType::Float), AgoType::Float(42.0));
    assert_eq!(
        AgoType::Int(42).as_type(TargetType::String),
        AgoType::String("42".to_string())
    );
    assert_eq!(AgoType::Int(42).as_type(TargetType::Bool), AgoType::Bool(true));
    assert_eq!(AgoType::Int(0).as_type(TargetType::Bool), AgoType::Bool(false));

    // Float
    assert_eq!(AgoType::Float(1.5).as_type(TargetType::Int), AgoType::Int(1));
    assert_eq!(
        AgoType::Float(1.5).as_type(TargetType::String),
        AgoType::String("1.5".to_string())
    );
    assert_eq!(AgoType::Float(0.0).as_type(TargetType::Bool), AgoType::Bool(false));

    // Bool
    assert_eq!(AgoType::Bool(true).as_type(TargetType::Int), AgoType::Int(1));
    assert_eq!(AgoType::Bool(false).as_type(TargetType::Int), AgoType::Int(0));
    assert_eq!(
        AgoType::Bool(true).as_type(TargetType::String),
        AgoType::String("true".to_string())
    );

    // String
    assert_eq!(AgoType::String("123".to_string()).as_type(TargetType::Int), AgoType::Int(123));
    assert_eq!(AgoType::String("".to_string()).as_type(TargetType::Bool), AgoType::Bool(false));
    assert_eq!(AgoType::String("hi".to_string()).as_type(TargetType::Bool), AgoType::Bool(true));
}

#[test]
fn test_as_type_container_conversions() {
    // To Bool
    assert_eq!(AgoType::IntList(vec![1]).as_type(TargetType::Bool), AgoType::Bool(true));
    assert_eq!(AgoType::IntList(vec![]).as_type(TargetType::Bool), AgoType::Bool(false));
    assert_eq!(sample_struct().as_type(TargetType::Bool), AgoType::Bool(true));
    assert_eq!(AgoType::Struct(HashMap::new()).as_type(TargetType::Bool), AgoType::Bool(false));

    // List to String
    assert_eq!(
        AgoType::IntList(vec![1, 2]).as_type(TargetType::String),
        AgoType::String("1\n2".to_string())
    );
    assert_eq!(
        AgoType::StringList(vec!["a".to_string(), "b".to_string()]).as_type(TargetType::String),
        AgoType::String("a\nb".to_string())
    );

    // List to List
    assert_eq!(
        AgoType::IntList(vec![1, 0]).as_type(TargetType::BoolList),
        AgoType::BoolList(vec![true, false])
    );
    assert_eq!(
        AgoType::FloatList(vec![1.1, 2.2]).as_type(TargetType::StringList),
        AgoType::StringList(vec!["1.1".to_string(), "2.2".to_string()])
    );
}

#[test]
#[should_panic]
fn test_as_type_panic_str_to_int() {
    AgoType::String("not-a-number".to_string()).as_type(TargetType::Int);
}

#[test]
#[should_panic]
fn test_as_type_panic_unsupported() {
    AgoType::Int(1).as_type(TargetType::Struct);
}

#[test]
fn test_get() {
    // Lists
    assert_eq!(get(&AgoType::IntList(vec![10, 20]), &AgoType::Int(1)), AgoType::Int(20));
    assert_eq!(get(&AgoType::FloatList(vec![10.0, 20.0]), &AgoType::Int(0)), AgoType::Float(10.0));
    assert_eq!(get(&AgoType::BoolList(vec![true, false]), &AgoType::Int(1)), AgoType::Bool(false));
    assert_eq!(get(&AgoType::StringList(vec!["a".to_string(), "b".to_string()]), &AgoType::Int(1)), AgoType::String("b".to_string()));
    assert_eq!(get(&sample_any_list(), &AgoType::Int(1)), AgoType::String("two".to_string()));

    // String
    assert_eq!(get(&AgoType::String("abc".to_string()), &AgoType::Int(1)), AgoType::String("b".to_string()));

    // Struct
    assert_eq!(get(&sample_struct(), &AgoType::String("a".to_string())), AgoType::Int(1));
}

#[test]
#[should_panic]
fn test_get_list_out_of_bounds() {
    get(&AgoType::IntList(vec![10]), &AgoType::Int(1));
}

#[test]
#[should_panic]
fn test_get_struct_key_not_found() {
    get(&sample_struct(), &AgoType::String("z".to_string()));
}

#[test]
#[should_panic]
fn test_get_wrong_key_type_for_struct() {
    get(&sample_struct(), &AgoType::Int(0));
}

#[test]
#[should_panic]
fn test_get_wrong_index_type_for_list() {
    get(&AgoType::IntList(vec![1]), &AgoType::String("a".to_string()));
}

#[test]
fn test_set() {
    // List
    let mut list = AgoType::IntList(vec![10, 20, 30]);
    set(&mut list, &AgoType::Int(1), AgoType::Int(99));
    assert_eq!(list, AgoType::IntList(vec![10, 99, 30]));

    // Struct (update existing)
    let mut s1 = sample_struct();
    set(&mut s1, &AgoType::String("b".to_string()), AgoType::String("world".to_string()));
    assert_eq!(get(&s1, &AgoType::String("b".to_string())), AgoType::String("world".to_string()));

    // Struct (add new)
    let mut s2 = sample_struct();
    set(&mut s2, &AgoType::String("c".to_string()), AgoType::Int(100));
    assert_eq!(get(&s2, &AgoType::String("c".to_string())), AgoType::Int(100));
}

#[test]
#[should_panic]
fn test_set_list_wrong_value_type() {
    let mut list = AgoType::IntList(vec![10]);
    set(&mut list, &AgoType::Int(0), AgoType::Float(1.0));
}

#[test]
fn test_insero() {
    // List start
    let mut list_start = AgoType::IntList(vec![10, 30]);
    insero(&mut list_start, &AgoType::Int(0), AgoType::Int(5));
    assert_eq!(list_start, AgoType::IntList(vec![5, 10, 30]));

    // List middle
    let mut list_mid = AgoType::IntList(vec![10, 30]);
    insero(&mut list_mid, &AgoType::Int(1), AgoType::Int(20));
    assert_eq!(list_mid, AgoType::IntList(vec![10, 20, 30]));

    // List end
    let mut list_end = AgoType::IntList(vec![10, 30]);
    insero(&mut list_end, &AgoType::Int(2), AgoType::Int(40));
    assert_eq!(list_end, AgoType::IntList(vec![10, 30, 40]));

    // Struct (same as set)
    let mut s = sample_struct();
    insero(&mut s, &AgoType::String("c".to_string()), AgoType::Bool(true));
    assert_eq!(get(&s, &AgoType::String("c".to_string())), AgoType::Bool(true));
}

#[test]
#[should_panic]
fn test_insero_list_wrong_value_type() {
    let mut list = AgoType::StringList(vec!["a".to_string()]);
    insero(&mut list, &AgoType::Int(0), AgoType::Int(123));
}

#[test]
fn test_removeo() {
    // List
    let mut list = AgoType::IntList(vec![10, 20, 30]);
    let removed_list = removeo(&mut list, &AgoType::Int(1));
    assert_eq!(removed_list, AgoType::Int(20));
    assert_eq!(list, AgoType::IntList(vec![10, 30]));

    // Struct
    let mut s = sample_struct();
    let removed_struct = removeo(&mut s, &AgoType::String("a".to_string()));
    assert_eq!(removed_struct, AgoType::Int(1));
    if let AgoType::Struct(map) = s {
        assert!(!map.contains_key("a"));
        assert!(map.contains_key("b"));
    } else {
        panic!("Expected a struct");
    }
}

#[test]
#[should_panic]
fn test_removeo_struct_key_not_found() {
    let mut s = sample_struct();
    removeo(&mut s, &AgoType::String("z".to_string()));
}

#[test]
fn test_claverum() {
    // Non-empty struct
    let s = sample_struct();
    let keys_ago = claverum(s);
    if let AgoType::StringList(mut keys) = keys_ago {
        keys.sort(); // Sort for deterministic comparison
        assert_eq!(keys, vec!["a".to_string(), "b".to_string()]);
    } else {
        panic!("claverum should return a StringList");
    }

    // Empty struct
    let empty_s = AgoType::Struct(HashMap::new());
    let empty_keys_ago = claverum(empty_s);
    if let AgoType::StringList(keys) = empty_keys_ago {
        assert!(keys.is_empty());
    } else {
        panic!("claverum should return a StringList for an empty struct");
    }
}

#[test]
#[should_panic]
fn test_claverum_on_non_struct() {
    claverum(AgoType::Int(1));
}




#[test]
fn test_aequalem() {
    // Same type, same value
    assert_eq!(aequalem(&AgoType::Int(5), &AgoType::Int(5)), AgoType::Bool(true));
    assert_eq!(aequalem(&AgoType::Float(5.0), &AgoType::Float(5.0)), AgoType::Bool(true));
    assert_eq!(aequalem(&AgoType::String("hello".to_string()), &AgoType::String("hello".to_string())), AgoType::Bool(true));
    assert_eq!(aequalem(&AgoType::Bool(true), &AgoType::Bool(true)), AgoType::Bool(true));
    assert_eq!(aequalem(&AgoType::Null, &AgoType::Null), AgoType::Bool(true));

    // Same type, different value
    assert_eq!(aequalem(&AgoType::Int(5), &AgoType::Int(6)), AgoType::Bool(false));
    assert_eq!(aequalem(&AgoType::Float(5.0), &AgoType::Float(5.1)), AgoType::Bool(false));
    assert_eq!(aequalem(&AgoType::String("hello".to_string()), &AgoType::String("world".to_string())), AgoType::Bool(false));
    assert_eq!(aequalem(&AgoType::Bool(true), &AgoType::Bool(false)), AgoType::Bool(false));

    // Different types, same conceptual value (should be false due to strict equality)
    assert_eq!(aequalem(&AgoType::Int(5), &AgoType::Float(5.0)), AgoType::Bool(false));
    assert_eq!(aequalem(&AgoType::Int(1), &AgoType::Bool(true)), AgoType::Bool(false));
    assert_eq!(aequalem(&AgoType::String("5".to_string()), &AgoType::Int(5)), AgoType::Bool(false));

    // Different types, different values
    assert_eq!(aequalem(&AgoType::Int(5), &AgoType::String("hello".to_string())), AgoType::Bool(false));
    assert_eq!(aequalem(&AgoType::Float(1.0), &AgoType::Bool(false)), AgoType::Bool(false));
}

// --- Operator Tests ---

#[test]
fn test_arithmetic_operators() {
    // Int, Int
    assert_eq!(add(&AgoType::Int(5), &AgoType::Int(2)), AgoType::Int(7));
    assert_eq!(subtract(&AgoType::Int(5), &AgoType::Int(2)), AgoType::Int(3));
    assert_eq!(multiply(&AgoType::Int(5), &AgoType::Int(2)), AgoType::Int(10));
    assert_eq!(divide(&AgoType::Int(5), &AgoType::Int(2)), AgoType::Int(2));
    assert_eq!(modulo(&AgoType::Int(5), &AgoType::Int(2)), AgoType::Int(1));

    // Float, Float
    assert_eq!(add(&AgoType::Float(5.0), &AgoType::Float(2.0)), AgoType::Float(7.0));
    assert_eq!(subtract(&AgoType::Float(5.0), &AgoType::Float(2.0)), AgoType::Float(3.0));
    assert_eq!(multiply(&AgoType::Float(5.0), &AgoType::Float(2.0)), AgoType::Float(10.0));
    assert_eq!(divide(&AgoType::Float(5.0), &AgoType::Float(2.0)), AgoType::Float(2.5));

    // Mixed
    assert_eq!(add(&AgoType::Int(5), &AgoType::Float(2.5)), AgoType::Float(7.5));
    assert_eq!(subtract(&AgoType::Float(5.0), &AgoType::Int(2)), AgoType::Float(3.0));
}

#[test]
fn test_add_concatenation() {
    // String
    let s1 = AgoType::String("hello".to_string());
    let s2 = AgoType::String(" world".to_string());
    assert_eq!(add(&s1, &s2), AgoType::String("hello world".to_string()));

    // List
    let l1 = AgoType::IntList(vec![1, 2]);
    let l2 = AgoType::IntList(vec![3, 4]);
    assert_eq!(add(&l1, &l2), AgoType::IntList(vec![1, 2, 3, 4]));
}

#[test]
#[should_panic]
fn test_arithmetic_panic() {
    add(&AgoType::Int(5), &AgoType::String("hello".to_string()));
}

#[test]
fn test_comparison_operators() {
    // Numeric
    assert_eq!(greater_than(&AgoType::Int(5), &AgoType::Int(2)), AgoType::Bool(true));
    assert_eq!(less_than(&AgoType::Float(5.0), &AgoType::Int(2)), AgoType::Bool(false));
    assert_eq!(greater_equal(&AgoType::Int(5), &AgoType::Float(5.0)), AgoType::Bool(true));
    assert_eq!(less_equal(&AgoType::Int(5), &AgoType::Int(5)), AgoType::Bool(true));

    // String
    assert_eq!(greater_than(&AgoType::String("b".to_string()), &AgoType::String("a".to_string())), AgoType::Bool(true));
    assert_eq!(less_than(&AgoType::String("b".to_string()), &AgoType::String("a".to_string())), AgoType::Bool(false));
}

#[test]
fn test_logical_operators() {
    assert_eq!(and(&AgoType::Bool(true), &AgoType::Bool(false)), AgoType::Bool(false));
    assert_eq!(and(&AgoType::Bool(true), &AgoType::Bool(true)), AgoType::Bool(true));
    assert_eq!(or(&AgoType::Bool(true), &AgoType::Bool(false)), AgoType::Bool(true));
    assert_eq!(or(&AgoType::Bool(false), &AgoType::Bool(false)), AgoType::Bool(false));
    assert_eq!(not(&AgoType::Bool(true)), AgoType::Bool(false));
    assert_eq!(not(&AgoType::Bool(false)), AgoType::Bool(true));
}

#[test]
#[should_panic]
fn test_logical_panic() {
    and(&AgoType::Bool(true), &AgoType::Int(1));
}

#[test]
fn test_bitwise_operators() {
    assert_eq!(bitwise_and(&AgoType::Int(6), &AgoType::Int(3)), AgoType::Int(2)); // 110 & 011 = 010
    assert_eq!(bitwise_or(&AgoType::Int(6), &AgoType::Int(3)), AgoType::Int(7));  // 110 | 011 = 111
    assert_eq!(bitwise_xor(&AgoType::Int(6), &AgoType::Int(3)), AgoType::Int(5)); // 110 ^ 011 = 101
}

#[test]
#[should_panic]
fn test_bitwise_panic() {
    bitwise_and(&AgoType::Int(6), &AgoType::Float(3.0));
}

#[test]
fn test_unary_operators() {
    assert_eq!(unary_minus(&AgoType::Int(5)), AgoType::Int(-5));
    assert_eq!(unary_minus(&AgoType::Float(5.0)), AgoType::Float(-5.0));
    assert_eq!(unary_plus(&AgoType::Int(5)), AgoType::Int(5));
}

#[test]
fn test_contains() {
    // In String
    assert_eq!(contains(&AgoType::String("hello".to_string()), &AgoType::String("ell".to_string())), AgoType::Bool(true));
    assert_eq!(contains(&AgoType::String("hello".to_string()), &AgoType::String("z".to_string())), AgoType::Bool(false));

    // In Struct (key)
    assert_eq!(contains(&sample_struct(), &AgoType::String("a".to_string())), AgoType::Bool(true));
    assert_eq!(contains(&sample_struct(), &AgoType::String("z".to_string())), AgoType::Bool(false));

    // In List
    assert_eq!(contains(&AgoType::IntList(vec![1, 2, 3]), &AgoType::Int(2)), AgoType::Bool(true));
    assert_eq!(contains(&AgoType::IntList(vec![1, 2, 3]), &AgoType::Int(4)), AgoType::Bool(false));
    assert_eq!(contains(&sample_any_list(), &AgoType::String("two".to_string())), AgoType::Bool(true));
}

#[test]
fn test_elvis() {
    let val = AgoType::Int(10);
    let default = AgoType::Int(20);
    let null = AgoType::Null;

    // Returns left if not null
    assert_eq!(elvis(&val, &default), val);
    assert_eq!(elvis(&val, &null), val);

    // Returns right if left is null
    assert_eq!(elvis(&null, &default), default);
}

#[test]
#[should_panic(expected = "Cannot coalesce two null values")]
fn test_elvis_panic() {
    elvis(&AgoType::Null, &AgoType::Null);
}

#[test]
fn test_slice_operator_creation() {
    let range = slice(&AgoType::Int(1), &AgoType::Int(5));
    assert_eq!(range, AgoType::Range(AgoRange { start: 1, end: 5, inclusive: true }));

    let range_reverse = slice(&AgoType::Int(5), &AgoType::Int(1));
    assert_eq!(range_reverse, AgoType::Range(AgoRange { start: 5, end: 1, inclusive: true }));
}

#[test]
fn test_sliceto_operator_creation() {
    let range = sliceto(&AgoType::Int(1), &AgoType::Int(5));
    assert_eq!(range, AgoType::Range(AgoRange { start: 1, end: 5, inclusive: false }));

    let range_reverse = sliceto(&AgoType::Int(5), &AgoType::Int(1));
    assert_eq!(range_reverse, AgoType::Range(AgoRange { start: 5, end: 1, inclusive: false }));
}

#[test]
#[should_panic(expected = "Range operators can only be used with integers")]
fn test_range_operator_panic_non_int_slice() {
    slice(&AgoType::Float(1.0), &AgoType::Int(5));
}

#[test]
#[should_panic(expected = "Range operators can only be used with integers")]
fn test_range_operator_panic_non_int_sliceto() {
    sliceto(&AgoType::Int(1), &AgoType::String("5".to_string()));
}

#[test]
fn test_range_as_type_to_string() {
    let inclusive_range = AgoType::Range(AgoRange { start: 1, end: 5, inclusive: true });
    assert_eq!(inclusive_range.as_type(TargetType::String), AgoType::String("1..5".to_string()));

    let exclusive_range = AgoType::Range(AgoRange { start: 1, end: 5, inclusive: false });
    assert_eq!(exclusive_range.as_type(TargetType::String), AgoType::String("1.<5".to_string()));
}

#[test]
fn test_range_as_type_to_bool() {
    // Valid ranges
    let inclusive_valid = AgoType::Range(AgoRange { start: 1, end: 5, inclusive: true });
    assert_eq!(inclusive_valid.as_type(TargetType::Bool), AgoType::Bool(true));

    let exclusive_valid = AgoType::Range(AgoRange { start: 1, end: 5, inclusive: false });
    assert_eq!(exclusive_valid.as_type(TargetType::Bool), AgoType::Bool(true));

    let single_point_inclusive = AgoType::Range(AgoRange { start: 5, end: 5, inclusive: true });
    assert_eq!(single_point_inclusive.as_type(TargetType::Bool), AgoType::Bool(true));

    // Invalid ranges (start > end)
    let inclusive_invalid = AgoType::Range(AgoRange { start: 5, end: 1, inclusive: true });
    assert_eq!(inclusive_invalid.as_type(TargetType::Bool), AgoType::Bool(false));

    let exclusive_invalid = AgoType::Range(AgoRange { start: 5, end: 1, inclusive: false });
    assert_eq!(exclusive_invalid.as_type(TargetType::Bool), AgoType::Bool(false));
}

#[test]
fn test_range_as_type_to_intlist() {
    // Inclusive ranges
    let inclusive_range = AgoType::Range(AgoRange { start: 1, end: 5, inclusive: true });
    assert_eq!(inclusive_range.as_type(TargetType::IntList), AgoType::IntList(vec![1, 2, 3, 4, 5]));

    let single_point_inclusive = AgoType::Range(AgoRange { start: 5, end: 5, inclusive: true });
    assert_eq!(single_point_inclusive.as_type(TargetType::IntList), AgoType::IntList(vec![5]));

    let inclusive_negative = AgoType::Range(AgoRange { start: -2, end: 2, inclusive: true });
    assert_eq!(inclusive_negative.as_type(TargetType::IntList), AgoType::IntList(vec![-2, -1, 0, 1, 2]));

    // Exclusive ranges
    let exclusive_range = AgoType::Range(AgoRange { start: 1, end: 5, inclusive: false });
    assert_eq!(exclusive_range.as_type(TargetType::IntList), AgoType::IntList(vec![1, 2, 3, 4]));

    let exclusive_empty = AgoType::Range(AgoRange { start: 5, end: 5, inclusive: false });
    assert_eq!(exclusive_empty.as_type(TargetType::IntList), AgoType::IntList(vec![]));

    let exclusive_negative = AgoType::Range(AgoRange { start: -2, end: 2, inclusive: false });
    assert_eq!(exclusive_negative.as_type(TargetType::IntList), AgoType::IntList(vec![-2, -1, 0, 1]));

    // Invalid ranges (start > end)
    let inclusive_invalid = AgoType::Range(AgoRange { start: 5, end: 1, inclusive: true });
    assert_eq!(inclusive_invalid.as_type(TargetType::IntList), AgoType::IntList(vec![]));

    let exclusive_invalid = AgoType::Range(AgoRange { start: 5, end: 1, inclusive: false });
    assert_eq!(exclusive_invalid.as_type(TargetType::IntList), AgoType::IntList(vec![]));
}

// Note: Testing `dico` is complex as it prints to stdout.
// It would require capturing stdout, which is possible but adds complexity.


// Note: Testing `aperto` requires file I/O and setting up test files.
// This can be done but is skipped here for simplicity.

// Note: Testing `exeo` is not feasible in a standard test suite
// because it terminates the test process itself. It would require
// running a test in a separate process and checking its exit code.
