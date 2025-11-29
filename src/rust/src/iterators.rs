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
        AgoType::Range(r) => {
            let range: Box<dyn Iterator<Item = i128>> = if r.inclusive {
                Box::new(r.start..=r.end)
            } else {
                Box::new(r.start..r.end)
            };
            Box::new(range.map(AgoType::Int))
        }
        _ => {
            // Return an empty iterator for non-iterable types.
            // The semantic checker should have already caught this error.
            Box::new(std::iter::empty())
        }
    }
}
