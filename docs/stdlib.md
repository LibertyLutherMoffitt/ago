# Ago Core Runtime Documentation

This document outlines the core runtime functions for the Ago language. These functions are implemented in Rust and are intended to be used by the transpiler when generating Rust code from Ago source. They form the standard library (`stdlib`) that all transpiled Ago programs link against.

## Core Types

All Ago values are represented by the `ago_stdlib::AgoType` enum in Rust. The following imports are assumed for the examples below.

```rust
use ago_stdlib::{
    aperto, claverum, dico, exeo, get, insero, removeo, set, species, AgoType, FileStruct,
    TargetType,
};
use std::collections::HashMap;
```

## Core Concepts

### Type Casting with `.as_type()`

The transpiler can generate calls to the `.as_type()` method to handle Ago's type conversions.

**Rust Signature:** `value.as_type(target: TargetType) -> AgoType`

- **`target`**: An enum variant from `ago_stdlib::TargetType` (e.g., `TargetType::Float`).

**Example:**
```rust
let my_int = AgoType::Int(42);
let my_float = my_int.as_type(TargetType::Float); // my_float is now AgoType::Float(42.0)

assert_eq!(my_float, AgoType::Float(42.0));
```

---

## Functions

### species

Returns the string name of an `AgoType`'s variant.

- **Rust Signature:** `pub fn species(val: &AgoType) -> AgoType`
- **Parameters:**
  - `val` (`&AgoType`): A reference to the value to inspect.
- **Returns:** (`AgoType::String`): The name of the type (e.g., "Int", "String", "Struct").
- **Example:**
  ```rust
  let x = AgoType::Struct(HashMap::new());
  let type_name = species(&x); // type_name is AgoType::String("Struct".to_string())
  assert_eq!(type_name, AgoType::String("Struct".to_string()));
  ```

---

### get

Retrieves a value from a collection (`List`, `String`, or `Struct`) by its index or key.

- **Rust Signature:** `pub fn get(iter: &AgoType, n: &AgoType) -> AgoType`
- **Parameters:**
  - `iter` (`&AgoType`): A reference to the collection.
  - `n` (`&AgoType`): The `AgoType::Int` index or `AgoType::String` key.
- **Returns:** (`AgoType`): A clone of the value found at the specified location.
- **Errors:** Panics if the index is out of bounds or the key is not found.
- **Example:**
  ```rust
  let my_list = AgoType::IntList(vec![10, 20, 30]);
  let val = get(&my_list, &AgoType::Int(1)); // val is AgoType::Int(20)
  assert_eq!(val, AgoType::Int(20));

  let my_struct = AgoType::Struct(HashMap::from([("name".to_string(), AgoType::String("Ago".to_string()))]));
  let name = get(&my_struct, &AgoType::String("name".to_string())); // name is AgoType::String("Ago")
  assert_eq!(name, AgoType::String("Ago".to_string()));
  ```

---

### set

Updates a value in a mutable collection (`List` or `Struct`). For a `Struct`, it creates the key if it doesn't exist.

- **Rust Signature:** `pub fn set(iter: &mut AgoType, n: &AgoType, value: AgoType)`
- **Parameters:**
  - `iter` (`&mut AgoType`): A mutable reference to the collection.
  - `n` (`&AgoType`): The `AgoType::Int` index or `AgoType::String` key.
  - `value` (`AgoType`): The new value.
- **Returns:** None.
- **Errors:** Panics if the index is out of bounds or if the value's type doesn't match a typed List's type.
- **Example:**
  ```rust
  let mut my_list = AgoType::IntList(vec![10, 20, 30]);
  set(&mut my_list, &AgoType::Int(1), AgoType::Int(99));
  assert_eq!(my_list, AgoType::IntList(vec![10, 99, 30]));
  ```

---

### insero

Inserts a value into a collection. For `List`s, it inserts at an index, shifting other elements. For `Struct`s, it behaves identically to `set`.

- **Rust Signature:** `pub fn insero(coll: &mut AgoType, key: &AgoType, value: AgoType)`
- **Parameters:**
  - `coll` (`&mut AgoType`): A mutable reference to the collection.
  - `key` (`&AgoType`): The `AgoType::Int` index for Lists or `AgoType::String` key for Structs.
  - `value` (`AgoType`): The new value to insert.
- **Returns:** None.
- **Errors:** Panics if the index is out of bounds for a List or if the value's type doesn't match a typed List's type.
- **Example:**
  ```rust
  let mut my_list = AgoType::IntList(vec![10, 30]);
  insero(&mut my_list, &AgoType::Int(1), AgoType::Int(20));
  assert_eq!(my_list, AgoType::IntList(vec![10, 20, 30]));
  ```

---

### removeo

Removes a value from a collection by its index or key and returns the removed value.

- **Rust Signature:** `pub fn removeo(coll: &mut AgoType, key: &AgoType) -> AgoType`
- **Parameters:**
  - `coll` (`&mut AgoType`): A mutable reference to the collection.
  - `key` (`&AgoType`): The `AgoType::Int` index for Lists or `AgoType::String` key for Structs.
- **Returns:** (`AgoType`): The value that was removed.
- **Errors:** Panics if the index is out of bounds or the key is not found.
- **Example:**
  ```rust
  let mut my_list = AgoType::IntList(vec![10, 20, 30]);
  let removed_val = removeo(&mut my_list, &AgoType::Int(1));
  assert_eq!(removed_val, AgoType::Int(20));
  assert_eq!(my_list, AgoType::IntList(vec![10, 30]));
  ```

---

### claverum

Returns a list of all keys within a `Struct`.

- **Rust Signature:** `pub fn claverum(val: AgoType) -> AgoType`
- **Parameters:**
  - `val` (`AgoType::Struct`): The struct to get the keys from.
- **Returns:** (`AgoType::StringList`): A list containing all the keys from the struct. The order is not guaranteed.
- **Errors:** Panics if the provided value is not a `Struct`.
- **Example:**
  ```rust
  let my_struct = AgoType::Struct(HashMap::from([
      ("name".to_string(), AgoType::String("Ago".to_string())),
      ("version".to_string(), AgoType::Int(1))
  ]));
  let keys = claverum(my_struct); // keys is an AgoType::StringList
  ```

---

### dico

Prints an `AgoType::String` value to standard output.

- **Rust Signature:** `pub fn dico(val: AgoType)`
- **Parameters:**
  - `val` (`AgoType::String`): The string to be printed.
- **Returns:** None.
- **Errors:** Panics if the provided value is not an `AgoType::String`.
- **Example:**
  ```rust
  dico(AgoType::String("Hello, World!".to_string()));
  ```

---

### aperto

Opens a file and returns a `FileStruct`.

- **Rust Signature:** `pub fn aperto(val: AgoType) -> FileStruct`
- **Parameters:**
  - `val` (`AgoType::String`): The path to the file to open.
- **Returns:** (`FileStruct`): A struct containing `filename`, `content`, and `filesize`.
- **Errors:** Panics if the file cannot be found or read.
- **Example:**
  ```rust
  // In a real scenario, you would create a file first for the test to pass.
  // std::fs::write("my_file.txt", "hello").unwrap();
  // let file_data = aperto(AgoType::String("my_file.txt".to_string()));
  // assert_eq!(file_data.content, "hello");
  ```

---

### exeo

Exits the program immediately with a given integer exit code.

- **Rust Signature:** `pub fn exeo(code: &AgoType)`
- **Parameters:**
  - `code` (`&AgoType::Int`): The exit code.
- **Returns:** This function never returns.
- **Errors:** Panics if the provided value is not an `Int`.
- **Example:**
  ```rust
  // This code would terminate the program, so it cannot be tested directly.
  // let has_error = true;
  // if has_error {
  //     exeo(&AgoType::Int(1));
  // }
  ```
