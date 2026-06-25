use ago_stdlib::iterators::into_iter;
use ago_stdlib::types::{AgoRange, AgoType};

#[test]
fn test_iter_int_list() {
    let list = AgoType::IntList(vec![10, 20, 30]);
    let mut iter = into_iter(&list);
    assert_eq!(iter.next(), Some(AgoType::Int(10)));
    assert_eq!(iter.next(), Some(AgoType::Int(20)));
    assert_eq!(iter.next(), Some(AgoType::Int(30)));
    assert_eq!(iter.next(), None);
}

#[test]
fn test_iter_string_list() {
    let list = AgoType::StringList(vec!["a".to_string(), "b".to_string()]);
    let mut iter = into_iter(&list);
    assert_eq!(iter.next(), Some(AgoType::String("a".to_string())));
    assert_eq!(iter.next(), Some(AgoType::String("b".to_string())));
    assert_eq!(iter.next(), None);
}

#[test]
fn test_iter_list_any() {
    let list = AgoType::ListAny(vec![AgoType::Int(1), AgoType::String("a".to_string())]);
    let mut iter = into_iter(&list);
    assert_eq!(iter.next(), Some(AgoType::Int(1)));
    assert_eq!(iter.next(), Some(AgoType::String("a".to_string())));
    assert_eq!(iter.next(), None);
}

#[test]
fn test_iter_string() {
    let s = AgoType::String("ab".to_string());
    let mut iter = into_iter(&s);
    assert_eq!(iter.next(), Some(AgoType::String("a".to_string())));
    assert_eq!(iter.next(), Some(AgoType::String("b".to_string())));
    assert_eq!(iter.next(), None);
}

#[test]
fn test_iter_range_inclusive() {
    let range = AgoType::Range(AgoRange {
        start: 1,
        end: 3,
        inclusive: true,
        step: 1,
    });
    let mut iter = into_iter(&range);
    assert_eq!(iter.next(), Some(AgoType::Int(1)));
    assert_eq!(iter.next(), Some(AgoType::Int(2)));
    assert_eq!(iter.next(), Some(AgoType::Int(3)));
    assert_eq!(iter.next(), None);
}

#[test]
fn test_iter_range_exclusive() {
    let range = AgoType::Range(AgoRange {
        start: 1,
        end: 3,
        inclusive: false,
        step: 1,
    });
    let mut iter = into_iter(&range);
    assert_eq!(iter.next(), Some(AgoType::Int(1)));
    assert_eq!(iter.next(), Some(AgoType::Int(2)));
    assert_eq!(iter.next(), None);
}

#[test]
fn test_iter_range_empty() {
    // Exclusive with start == end is empty.
    let range2 = AgoType::Range(AgoRange {
        start: 5,
        end: 5,
        inclusive: false,
        step: 1,
    });
    let mut iter2 = into_iter(&range2);
    assert_eq!(iter2.next(), None);
}

#[test]
fn test_iter_range_descending() {
    // A descending inclusive range counts down (Python range(5, 0, -1) shape).
    let range = AgoType::Range(AgoRange {
        start: 5,
        end: 1,
        inclusive: true,
        step: 1,
    });
    let got: Vec<AgoType> = into_iter(&range).collect();
    assert_eq!(
        got,
        vec![
            AgoType::Int(5),
            AgoType::Int(4),
            AgoType::Int(3),
            AgoType::Int(2),
            AgoType::Int(1),
        ]
    );
}

#[test]
fn test_iter_range_stepped() {
    // Stepped exclusive range: 0, 2, 4, 6, 8.
    let range = AgoType::Range(AgoRange {
        start: 0,
        end: 10,
        inclusive: false,
        step: 2,
    });
    let got: Vec<AgoType> = into_iter(&range).collect();
    assert_eq!(
        got,
        vec![
            AgoType::Int(0),
            AgoType::Int(2),
            AgoType::Int(4),
            AgoType::Int(6),
            AgoType::Int(8),
        ]
    );
}

#[test]
fn test_iter_non_iterable() {
    let val = AgoType::Int(123);
    let mut iter = into_iter(&val);
    assert_eq!(iter.next(), None);
}
