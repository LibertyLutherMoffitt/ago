use crate::types::{AgoInt, AgoString, AgoType};

/// Prints a string to stdout. Returns Null.
/// Name ends in -i (returns null/inanis)
pub fn dici(val: &AgoType) -> AgoType {
    match val {
        AgoType::String(s) => println!("{}", s),
        _ => panic!("dici expects a String, got {:?}", val),
    }
    AgoType::Null
}

pub fn apertes(filename: AgoString) -> AgoString {
    match std::fs::read_to_string(&filename) {
        Ok(content) => AgoType::String(content),
        Err(e) => panic!("Failed to open file '{}': {}", filename, e),
    }
}

pub fn scribo(filename: AgoString, content: AgoString) -> AgoType {
    match std::fs::write(&filename, content) {
        Ok(_) => AgoType::Null,
        Err(e) => panic!("Failed to write to file '{}': {}", filename, e),
    }

}

pub fn audies() -> AgoString {
    let mut input = String::new();
    match std::io::stdin().read_line(&mut input) {
        Ok(_) => AgoType::String(input.trim_end_matches(&['\r', '\n'][..]).to_string()),
        Err(e) => panic!("Failed to read from stdin: {}", e),
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

/// Returns the keys of a struct as a string list.
/// Name ends in -erum (returns string_list)
pub fn claverum(val: &AgoType) -> AgoType {
    match val {
        AgoType::Struct(map) => {
            let keys = map.keys().cloned().collect();
            AgoType::StringList(keys)
        }
        _ => panic!("claverum function expects a Struct type"),
    }
}
