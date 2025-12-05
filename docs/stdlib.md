# Ago Core Runtime Documentation

This document outlines the core runtime functions for the Ago language. These functions are implemented in Rust and are intended to be used by the transpiler when generating Rust code from Ago source. They form the standard library (`stdlib`) that all transpiled Ago programs link against.

### Core Types

All Ago values are represented by the `ago_stdlib::AgoType` enum in Rust. The following imports are assumed for the examples below.

```rust
use ago_stdlib::{
    apertu, dici, exei, get, inseri, removium, set, species, AgoType,
    TargetType,
};
use std::collections::HashMap;
```

### Core Concepts

#### Type Casting with `.as_type()`

The transpiler can generate calls to the `.as_type()` method to handle Ago's type conversions.

**Rust Signature:** `value.as_type(target: TargetType) -> AgoType`

- **`target`**: An enum variant from `ago_stdlib::TargetType` (e.g., `TargetType::Float`).

**Example:**
```rust
let my_int = AgoType::Int(42);
let my_float = my_int.as_type(TargetType::Float); // my_float is now AgoType::Float(42.0)

assert_eq!(my_float, AgoType::Float(42.0));
```


### Functions

#### species

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


#### get

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


#### set

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


#### inseri

Inserts a value into a collection. For `List`s, it inserts at an index, shifting other elements. For `Struct`s, it behaves identically to `set`.

- **Rust Signature:** `pub fn inseri(coll: &mut AgoType, key: &AgoType, value: AgoType)`
- **Parameters:**
  - `coll` (`&mut AgoType`): A mutable reference to the collection.
  - `key` (`&AgoType`): The `AgoType::Int` index for Lists or `AgoType::String` key for Structs.
  - `value` (`AgoType`): The new value to insert.
- **Returns:** None (name ends in -i indicating inanis/null return).
- **Errors:** Panics if the index is out of bounds for a List or if the value's type doesn't match a typed List's type.
- **Example:**
  ```rust
  let mut my_list = AgoType::IntList(vec![10, 30]);
  inseri(&mut my_list, &AgoType::Int(1), AgoType::Int(20));
  assert_eq!(my_list, AgoType::IntList(vec![10, 20, 30]));
  ```


#### removium

Removes a value from a collection by its index or key and returns the removed value.

- **Rust Signature:** `pub fn removium(coll: &mut AgoType, key: &AgoType) -> AgoType`
- **Parameters:**
  - `coll` (`&mut AgoType`): A mutable reference to the collection.
  - `key` (`&AgoType`): The `AgoType::Int` index for Lists or `AgoType::String` key for Structs.
- **Returns:** (`AgoType`): The value that was removed (name ends in -ium indicating Any return).
- **Errors:** Panics if the index is out of bounds or the key is not found.
- **Example:**
  ```rust
  let mut my_list = AgoType::IntList(vec![10, 20, 30]);
  let removed_val = removium(&mut my_list, &AgoType::Int(1));
  assert_eq!(removed_val, AgoType::Int(20));
  assert_eq!(my_list, AgoType::IntList(vec![10, 30]));
  ```


#### aequalam

Performs a strict equality comparison between two `AgoType` values. This function is used to implement the `==` operator in Ago, adhering to strict type equality (e.g., `Int(5)` is not equal to `Float(5.0)`).

- **Rust Signature:** `pub fn aequalam(left: &AgoType, right: &AgoType) -> AgoType`
- **Parameters:**
  - `left` (`&AgoType`): The left-hand side value for comparison.
  - `right` (`&AgoType`): The right-hand side value for comparison.
- **Returns:** (`AgoType::Bool`): `true` if both values are of the same `AgoType` variant and have the same value, `false` otherwise.
- **Example:**
  ```rust
  let int_five = AgoType::Int(5);
  let float_five = AgoType::Float(5.0);
  let string_five = AgoType::String("5".to_string());

  assert_eq!(aequalam(&int_five, &AgoType::Int(5)), AgoType::Bool(true));
  assert_eq!(aequalam(&int_five, &AgoType::Int(6)), AgoType::Bool(false));
  assert_eq!(aequalam(&int_five, &float_five), AgoType::Bool(false)); // Strict equality
  assert_eq!(aequalam(&int_five, &string_five), AgoType::Bool(false)); // Strict equality
  ```


### Operator Functions

These functions are the Rust implementations for the operators available in the Ago language (e.g., `+`, `-`, `et`, `>`). The transpiler is responsible for generating calls to these functions when it encounters an operator in Ago source code.

#### Arithmetic Operators

- **`add(left, right)`**: Performs numeric addition. If types are mixed (`Int`, `Float`), the result is promoted to `Float`. Also performs concatenation for two `String`s or two `List`s of the same type.
- **`subtract(left, right)`**: Performs numeric subtraction. Promotes to `Float` for mixed types.
- **`multiply(left, right)`**: Performs numeric multiplication. Promotes to `Float` for mixed types.
- **`divide(left, right)`**: Performs numeric division. Promotes to `Float` for mixed types. Division of two `Int`s results in a truncated `Int`.
- **`modulo(left, right)`**: Performs the remainder operation. Promotes to `Float` for mixed types.

#### Comparison Operators

These functions compare two values and return an `AgoType::Bool`.
- **`greater_than(left, right)`**
- **`greater_equal(left, right)`**
- **`less_than(left, right)`**
- **`less_equal(left, right)`**
- **Behavior**: They operate on numeric types (promoting to `Float` if mixed) and `String` types (lexicographical comparison). Panics on other type combinations.

#### Logical Operators

- **`and(left, right)`**: Returns `AgoType::Bool(true)` if both inputs are `AgoType::Bool(true)`, otherwise `false`. Panics if inputs are not `Bool`.
- **`or(left, right)`**: Returns `AgoType::Bool(true)` if either input is `AgoType::Bool(true)`, otherwise `false`. Panics if inputs are not `Bool`.
- **`not(value)`**: A unary operator that flips a `Bool` value. Panics if the input is not a `Bool`.

#### Bitwise Operators

These functions operate only on `AgoType::Int` values and panic on any other type.
- **`bitwise_and(left, right)`**
- **`bitwise_or(left, right)`**
- **`bitwise_xor(left, right)`**

#### Unary Operators

- **`unary_minus(value)`**: Negates an `Int` or `Float` value.
- **`unary_plus(value)`**: Returns the `Int` or `Float` value unmodified. (A semantic no-op).

#### Membership Operator

- **`contains(haystack, needle)`**: Implements the `in` operator. Returns `AgoType::Bool(true)` if the `needle` is found in the `haystack`.
- **Behavior**:
  - **String**: Checks if `needle` (String) is a substring of `haystack` (String).
  - **Struct**: Checks if `needle` (String) is a key in `haystack` (Struct).
  - **List**: Checks if `needle` (Any) is an element in `haystack` (List).

#### Elvis Operator (`?:`)

- **`elvis(left, right)`**: Implements the null-coalescing operator. It returns the left value if it is not `AgoType::Null`. If the left value is `Null`, it returns the right value.
- **Errors**: Panics if both `left` and `right` values are `AgoType::Null`.
- **Example**:
  ```rust
  let user_name = AgoType::String("Cato".to_string());
  let default_name = AgoType::String("Anonymous".to_string());
  let null_val = AgoType::Null;

  // user_name is not null, so it is returned.
  let result1 = elvis(&user_name, &default_name);
  assert_eq!(result1, user_name);

  // nickname is null, so the default is returned.
  let result2 = elvis(&null_val, &default_name);
  assert_eq!(result2, default_name);
  ```


#### dico

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


#### aperto

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


#### exeo

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


### **abbium**

Returns the absolute value of an integer or float.

* **Ago Signature:** `des abbium(xium)`
* **Parameters:**

  * `xium` (`Int` or `Float`)
* **Returns:** (`Int` or `Float`): The absolute magnitude of the value.
* **Behavior:**

  * If `xium < 0`, the negated value is returned.
  * Otherwise, `xium` is returned unchanged.
* **Example:**

  ```ago
  abbium(-5)   # → 5
  abbium(3.2)  # → 3.2
  ```


### **appenduum**

Appends a value to the end of a list.

* **Ago Signature:** `des appenduum(xuum, yium)`
* **Parameters:**

  * `xuum` (`List[Any]`): The list to modify.
  * `yium` (`Any`): The element to append.
* **Returns:** (`List[Any]`): The list after modification.
* **Behavior:**

  * Uses `inseri` to insert `yium` at the end (`xa` refers to the list’s length).
* **Example:**

  ```ago
  appenduum([1,2,3], 4)  # → [1,2,3,4]
  ```


### **vicissuum**

Reverses a list.

* **Ago Signature:** `des vicissuum(ruum)`
* **Parameters:**

  * `ruum` (`List[Any]`)
* **Returns:** (`List[Any]`): A new list in reversed order.
* **Behavior:**

  * Builds a new list by iterating from the end to the beginning.
* **Example:**

  ```ago
  vicissuum([1,2,3])  # → [3,2,1]
  ```


### **spoliares**

Removes leading and trailing whitespace (space, tab, newline) from a string.

* **Ago Signature:** `des spoliares(ses)`
* **Parameters:**

  * `ses` (`String`)
* **Returns:** (`String`)
* **Behavior:**

  * Acts like Python’s `.strip()`.
  * Implements a two-pass approach:

    * Scan from the left to find the first non-whitespace character.
    * Scan from the right to find the last non-whitespace character.
* **Example:**

  ```ago
  spoliares("   salve   ")  # → "salve"
  ```


### **digitam**

Checks whether a string contains only digit characters.

* **Ago Signature:** `des digitam(ses)`
* **Parameters:**

  * `ses` (`String`)
* **Returns:** (`Bool`)
* **Behavior:**

  * Returns `verum` only if every character is between `"0"` and `"9"`.
* **Example:**

  ```ago
  digitam("1234")  # → verum
  digitam("12a4")  # → falsus
  ```


### **iunges**

Joins a list of strings with a separator.

* **Ago Signature:** `des iunges(lerum, ses)`
* **Parameters:**

  * `lerum` (`StringList`)
  * `ses` (`String`): Separator
* **Returns:** (`String`)
* **Behavior:**

  * Equivalent to Python `"sep".join(list)`.
  * Does not prepend or append the separator.
* **Example:**

  ```ago
  iunges(["a","b","c"], ",")  # → "a,b,c"
  ```


### **liquum**

Filters a list using a predicate function.

* **Ago Signature:** `des liquum(luum, xo)`
* **Parameters:**

  * `luum` (`List[Any]`)
  * `xo` (lambda): Called as `xo(element)` and must return `Bool`
* **Returns:** (`List[Any]`)
* **Behavior:**

  * Builds and returns a new list containing only elements where the predicate is true.
  * Runs in O(n).
* **Example:**

  ```ago
  liquum([1,2,3,4], des (x) { x % 2 == 0 })
  # → [2,4]
  ```


### **plicium**

Left-fold / reduce operation on a list.

* **Ago Signature:** `des plicium(luum, xo)`
* **Parameters:**

  * `luum` (`List[Any]`)
  * `xo` (lambda `(acc, element)` → new_acc)
* **Returns:** (`Any` or `inanis`)
* **Behavior:**

  * For empty lists, returns `inanis`.
  * Otherwise, uses the first element as the accumulator initial value.
  * Combines sequentially left-to-right.
* **Example:**

  ```ago
  plicium([1,2,3], des (a,b) { a + b })  # → 6
  ```


### **mutatuum**

Maps a list in place.

* **Ago Signature:** `des mutatuum(luum, xo)`
* **Parameters:**

  * `luum` (`List[Any]`)
  * `xo` (lambda `(element)` → new_element)
* **Returns:** (`List[Any]`)
* **Behavior:**

  * Updates each element of the list by calling the modifying function.
* **Example:**

  ```ago
  mutatuum([1,2,3], des (x) { x * 2 })
  # → [2,4,6]
  ```


### **minium**

Returns the minimum element of a list.

* **Ago Signature:** `des minium(luum)`
* **Parameters:**

  * `luum` (`List[Any]` of comparable items)
* **Returns:** (`Any` or `inanis`)
* **Behavior:**

  * Delegates to `plicium` with a minimum-selecting reducer.
* **Example:**

  ```ago
  minium([5,3,7])  # → 3
  ```


### **maxium**

Returns the maximum element of a list.

* **Ago Signature:** `des maxium(luum)`
* **Parameters:**

  * `luum` (`List[Any]` of comparable items)
* **Returns:** (`Any` or `inanis`)
* **Behavior:**

  * Delegates to `plicium` with a maximum-selecting reducer.
* **Example:**

  ```ago
  maxium([5,3,7])  # → 7
  ```


### **finderum**

Splits a string on a single-character separator.

* **Ago Signature:** `des finderum(les, ses)`
* **Parameters:**

  * `les` (`String`)
  * `ses` (`String` of length 1)
* **Returns:** (`StringList`)
* **Behavior:**

  * Equivalent to Python `str.split(sep)` but only for one-character separators.
  * Returns empty substrings where appropriate.
* **Example:**

  ```ago
  finderum("a,b,c", ",")  # → ["a","b","c"]
  ```


### **sumium**

Sums all elements in a numeric list.

* **Ago Signature:** `des sumium(luum)`
* **Parameters:**

  * `luum` (`List[Int|Float]`)
* **Returns:** (`Int` or `Float` or `inanis`)
* **Behavior:**

  * Uses `plicium` with addition.
  * Empty list → `inanis`.
* **Example:**

  ```ago
  sumium([1,2,3])  # → 6
  ```


### **prodium**

Computes the product of all numeric list elements.

* **Ago Signature:** `des prodium(luum)`
* **Parameters:**

  * `luum` (`List[Int|Float]`)
* **Returns:** (`Int` or `Float` or `inanis`)
* **Behavior:**

  * Uses `plicium` with multiplication.
* **Example:**

  ```ago
  prodium([2,3,4])  # → 24
  ```


### **invena**

Finds the first index of a value in a list.

* **Ago Signature:** `des invena(luum, xium)`
* **Parameters:**

  * `luum` (`List[Any]`)
  * `xium` (`Any`)
* **Returns:** (`Int` or `inanis`)
* **Behavior:**

  * Scans left-to-right.
  * Returns the index of the first equality match, or `inanis` if not found.
* **Example:**

  ```ago
  invena([10,20,30], 20)  # → 1
  invena([10,20,30], 40)  # → inanis
  ```


### **_conuum** *(internal)*

Internal merge routine used by `genorduum`.

* **Ago Signature:** `des _conuum(auum, buum, xo)`
* **Parameters:**

  * `auum` (`List[Any]`): First sorted list.
  * `buum` (`List[Any]`): Second sorted list.
  * `xo` (lambda): Key extraction function used for comparison.
* **Returns:** (`List[Any]`)
* **Behavior:**

  * Performs the classic merge step of merge sort.
  * Compares `xo(element)` to determine ordering.
* **Example:**
  *Internal use only; not intended for general use.*


### **genorduum**

Merge sort using a key function.

* **Ago Signature:** `des genorduum(luum, xo)`
* **Parameters:**

  * `luum` (`List[Any]`)
  * `xo` (lambda): Extracts a sortable key.
* **Returns:** (`List[Any]`)
* **Behavior:**

  * Recursively splits the list in half.
  * Uses `_conuum` to merge sorted halves.
  * Stable and O(n log n).
* **Example:**

  ```ago
  genorduum([3,1,2], des (x) { x })  # → [1,2,3]
  ```
