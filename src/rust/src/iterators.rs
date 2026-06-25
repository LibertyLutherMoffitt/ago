use crate::types::AgoType;

/// Creates a standard Rust iterator for any iterable AgoType.
///
/// This function provides a unified way to iterate over Ago's iterable types
/// (lists, strings, and ranges) by returning a boxed trait object that
/// implements the `Iterator` trait. This simplifies code generation for loops,
/// as the generator can produce the same code for any iterable.
///
/// For ranges, this is highly memory-efficient as it does not allocate a
/// collection, instead yielding numbers on the fly.
///
/// For types that are not iterable, it returns an empty iterator. The semantic
/// checker is expected to catch and report such errors before code generation.
pub fn into_iter(iterable: &AgoType) -> Box<dyn Iterator<Item = AgoType> + '_> {
    match iterable {
        AgoType::IntList(v) => Box::new(v.iter().map(|i| AgoType::Int(*i))),
        AgoType::FloatList(v) => Box::new(v.iter().map(|f| AgoType::Float(*f))),
        AgoType::BoolList(v) => Box::new(v.iter().map(|b| AgoType::Bool(*b))),
        AgoType::StringList(v) => Box::new(v.iter().map(|s| AgoType::String(s.clone()))),
        AgoType::ListAny(v) => Box::new(v.iter().cloned()),
        AgoType::String(s) => Box::new(s.chars().map(|c| AgoType::String(c.to_string()))),
        // Iterating a map yields its keys, in sorted order for determinism
        // (the backing HashMap has no inherent order).
        AgoType::Struct(m) => {
            let mut keys: Vec<String> = m.borrow().keys().cloned().collect();
            keys.sort();
            Box::new(keys.into_iter().map(AgoType::String))
        }
        AgoType::Range(r) => {
            let (count, inc, start) = (r.count(), r.increment(), r.start);
            Box::new((0..count).map(move |k| AgoType::Int(start + inc * k)))
        }
        _ => {
            // Return an empty iterator for non-iterable types.
            // The semantic checker should have already caught this error.
            Box::new(std::iter::empty())
        }
    }
}

/// Pair iterator for dual-binding `pro a, b in iterable` loops.
///
/// - Sequences (lists, strings, ranges) yield `(index, element)` — the Python
///   `enumerate` shape.
/// - Maps yield `(key, value)` with keys in sorted order for determinism.
pub fn into_pairs(iterable: &AgoType) -> Box<dyn Iterator<Item = (AgoType, AgoType)> + '_> {
    match iterable {
        AgoType::IntList(v) => Box::new(
            v.iter()
                .enumerate()
                .map(|(i, x)| (AgoType::Int(i as i128), AgoType::Int(*x))),
        ),
        AgoType::FloatList(v) => Box::new(
            v.iter()
                .enumerate()
                .map(|(i, x)| (AgoType::Int(i as i128), AgoType::Float(*x))),
        ),
        AgoType::BoolList(v) => Box::new(
            v.iter()
                .enumerate()
                .map(|(i, x)| (AgoType::Int(i as i128), AgoType::Bool(*x))),
        ),
        AgoType::StringList(v) => Box::new(
            v.iter()
                .enumerate()
                .map(|(i, x)| (AgoType::Int(i as i128), AgoType::String(x.clone()))),
        ),
        AgoType::ListAny(v) => Box::new(
            v.iter()
                .enumerate()
                .map(|(i, x)| (AgoType::Int(i as i128), x.clone())),
        ),
        AgoType::String(s) => Box::new(
            s.chars()
                .enumerate()
                .map(|(i, c)| (AgoType::Int(i as i128), AgoType::String(c.to_string()))),
        ),
        AgoType::Struct(m) => {
            let mut pairs: Vec<(String, AgoType)> =
                m.borrow().iter().map(|(k, v)| (k.clone(), v.clone())).collect();
            pairs.sort_by(|a, b| a.0.cmp(&b.0));
            Box::new(pairs.into_iter().map(|(k, v)| (AgoType::String(k), v)))
        }
        AgoType::Range(r) => {
            let (count, inc, start) = (r.count(), r.increment(), r.start);
            Box::new(
                (0..count).map(move |k| (AgoType::Int(k), AgoType::Int(start + inc * k))),
            )
        }
        _ => Box::new(std::iter::empty()),
    }
}
