use crate::types::{AgoInt, AgoType};

/// Prints a string to stdout. Returns Null.
/// Name ends in -i (returns null/inanis)
pub fn dici(val: &AgoType) -> AgoType {
    match val {
        AgoType::String(s) => println!("{}", s),
        _ => panic!("dici expects a String, got {:?}", val),
    }
    AgoType::Null
}

// writes a string to a file named filename, fails otherwise.
// names end in -i (returns null/inanis)
pub fn scribi(filename: &AgoType, content: &AgoType) -> AgoType {
    if let (AgoType::String(path), AgoType::String(data)) = (filename, content) {
        match std::fs::write(path, data) {
            Ok(_) => AgoType::Null,
            Err(e) => panic!("Failed to write to file '{}': {}", path, e),
        }
    } else {
        panic!("scribi expects a String for the filename and a String for the content");
    }
}

// reads in a line from stdin, "input()" style
// name ends in -es (returns string)
pub fn audies() -> AgoType {
    let mut input = String::new();
    match std::io::stdin().read_line(&mut input) {
        Ok(_) => {
            AgoType::String(input.trim_end_matches(&['\r', '\n'][..]).to_string())
        }
        Err(_e) => panic!("Failed to read from stdin:"),
    }
}

/// Opens a file and returns its contents as a struct.
/// Name ends in -u (returns struct)
pub fn apertu(val: &AgoType) -> AgoType {
    match val {
        AgoType::String(path) => match std::fs::read_to_string(path) {
            Ok(content) => {
                let metadata = std::fs::metadata(path).expect("Unable to read file metadata");
                let filesize = metadata.len() as AgoInt;
                let mut map = std::collections::HashMap::new();
                map.insert("filenames".to_string(), AgoType::String(path.clone()));
                map.insert("contentes".to_string(), AgoType::String(content));
                map.insert("filesizea".to_string(), AgoType::Int(filesize));
                AgoType::Struct(map)
            }
            Err(e) => panic!("Failed to open file '{}': {}", path, e),
        },
        _ => panic!("apertu function expects a String type"),
    }
}

/// Returns the string name of an AgoType.
/// Name ends in -es (returns string)
pub fn species(val: &AgoType) -> AgoType {
    let type_name = match val {
        AgoType::Int(_) => "Int",
        AgoType::Float(_) => "Float",
        AgoType::Bool(_) => "Bool",
        AgoType::String(_) => "String",
        AgoType::IntList(_) => "IntList",
        AgoType::FloatList(_) => "FloatList",
        AgoType::BoolList(_) => "BoolList",
        AgoType::StringList(_) => "StringList",
        AgoType::Struct(_) => "Struct",
        AgoType::ListAny(_) => "ListAny",
        AgoType::Range(_) => "Range",
        AgoType::Null => "Null",
    };
    AgoType::String(type_name.to_string())
}

/// Exits the program with the given exit code.
/// Name ends in -i (returns null/inanis - never returns)
pub fn exei(code: &AgoType) -> AgoType {
    if let AgoType::Int(exit_code) = code {
        std::process::exit(*exit_code as i32);
    } else {
        panic!("exei function expects an Int exit code, but got {:?}", code);
    }
}

/// Checks equality of two values.
/// Name ends in -am (returns bool)
pub fn aequalam(left: &AgoType, right: &AgoType) -> AgoType {
    AgoType::Bool(left == right)
}
