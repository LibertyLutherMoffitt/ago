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

/// Writes a string to the file named by the first argument (fails otherwise).
/// Name ends in -i (returns null/inanis).
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

/// Reads one line from stdin (Python `input()` style), trimming the newline.
/// Name ends in -es (returns string).
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
                AgoType::new_struct(map)
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
        AgoType::Lambda(_) => "Lambda",
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

/// Deep copy of a value ("exemplum" -> a copy). Because maps are reference
/// types, a plain assignment shares them; `exemplium` returns a fully
/// independent value (recursively copying maps, including maps nested inside
/// lists). Name ends in -ium (returns any, since it preserves the input type).
pub fn exemplium(val: &AgoType) -> AgoType {
    val.deep_copy()
}

/// Unicode code point of the first character of a string ("ordo" -> ordinal).
/// Name ends in -a (returns int). Empty string yields inanis.
pub fn ordina(val: &AgoType) -> AgoType {
    match val {
        AgoType::String(s) => match s.chars().next() {
            Some(c) => AgoType::Int(c as AgoInt),
            None => AgoType::Null,
        },
        _ => panic!("ordina expects a String, got {:?}", val),
    }
}

/// The single-character string for a Unicode code point ("litera" -> letter).
/// Name ends in -es (returns string). An invalid code point yields inanis.
pub fn literes(val: &AgoType) -> AgoType {
    match val {
        AgoType::Int(n) => match u32::try_from(*n).ok().and_then(char::from_u32) {
            Some(c) => AgoType::String(c.to_string()),
            None => AgoType::Null,
        },
        _ => panic!("literes expects an Int code point, got {:?}", val),
    }
}
