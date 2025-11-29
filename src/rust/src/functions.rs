use crate::types::{AgoInt, AgoType, FileStruct};

pub fn dico(val: AgoType) {
    match val {
        AgoType::String(val) => {
            println!("{}", val);
        }
        _ => panic!("dico function expects a String type"),
    }
}

pub fn aperto(val: AgoType) -> FileStruct {
    match val {
        AgoType::String(val) => match std::fs::read_to_string(&val) {
            Ok(content) => {
                let metadata = std::fs::metadata(&val).expect("Unable to read file metadata");
                let filesize = metadata.len() as AgoInt;
                FileStruct {
                    filename: val,
                    content,
                    filesize,
                }
            }
            Err(e) => panic!("Failed to open file '{}': {}", val, e),
        },
        _ => panic!("aperto function expects a String type"),
    }
}

/// Returns the string name of an AgoType.
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
pub fn exeo(code: &AgoType) {
    if let AgoType::Int(exit_code) = code {
        std::process::exit(*exit_code as i32);
    } else {
        panic!("exeo function expects an Int exit code, but got {:?}", code);
    }
}

pub fn aequalem(left: &AgoType, right: &AgoType) -> AgoType {
    AgoType::Bool(left == right)
}

pub fn claverum(val: AgoType) -> AgoType {
    match val {
        AgoType::Struct(map) => {
            let keys = map.keys().cloned().collect();
            AgoType::StringList(keys)
        }
        _ => panic!("claverum function expects a Struct type"),
    }
}
