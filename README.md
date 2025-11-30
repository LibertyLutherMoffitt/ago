# Ago

<div align="center">

```
   ___    ____  ____
  / _ |  / ___// __ \
 / __ | / (_ // /_/ /
/_/ |_| \___/ \____/
```

**A Latin-inspired programming language that transpiles to Rust**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

## Overview

Ago is an experimental programming language with Latin-inspired syntax that compiles to Rust. Its most distinctive feature is a **type-indicating naming system** where variable and function name endings determine their types.

```go
xa := 42              # Integer (ends in -a)
yam := verum          # Boolean (ends in -am)
zes := "Salvete!"     # String (ends in -es)

dici(zes)             # Print: "Salvete!"
```

## Installation

### Using Nix (Recommended)

```bash
# Run directly
nix run github:libertyluthermoffitt/ago -- hello.ago

# Or install
nix profile install github:libertyluthermoffitt/ago
```

### From Source

Requirements: Python 3.11+, Rust/Cargo, [TatSu](https://pypi.org/project/TatSu/)

```bash
git clone https://github.com/libertyluthermoffitt/ago
cd ago
pip install tatsu
python main.py hello.ago
```

## Quick Start

Create `hello.ago`:

```go
dici("Salvete Mundi!")
```

Run it:

```bash
ago hello.ago
```

## Language Guide

### Type Endings

In Ago, variable names must end with a suffix that indicates their type:

| Ending | Type | Example |
|--------|------|---------|
| `-a` | Integer | `xa := 42` |
| `-ae` | Float | `xae := 3.14` |
| `-am` | Boolean | `xam := verum` |
| `-es` | String | `xes := "hello"` |
| `-u` | Struct | `personu := {"namees": "Alice"}` |
| `-ium` | Any | `xium := mixuum[0]` |
| `-aem` | Int List | `numaem := [1, 2, 3]` |
| `-arum` | Float List | `valarum := [1.0, 2.0]` |
| `-as` | Bool List | `flagas := [verum, falsus]` |
| `-erum` | String List | `namerum := ["a", "b"]` |
| `-uum` | Any List | `mixuum := [1, "two", 3.0]` |
| `-e` | Range | `re := 1..100` |
| `-o` | Function/Lambda | `addo := des (a, b) { redeo a + b }` |
| `-i` | Null (inanis) | Function returns nothing |

### Implicit Type Casting

One of Ago's most powerful features is **implicit casting through name endings**. If you have a variable and reference it with a different ending, it automatically casts:

```go
xa := 42           # Integer
dici(xes)          # Automatically casts to string, prints "42"

yae := 3.14        # Float  
xa  := ya          # Casts to int: ya = 3
```

This also works with function calls:

```go
des geta() {
    redeo 42       # Returns int
}

xae := getae()     # Calls geta(), casts result to float
```

### Variables

```go
# Declaration (creates new variable)
xa := 10

# Reassignment (modifies existing)
xa = 20

# Stem-based shadowing: only one variable per "stem" in scope
xa := 5
xes := xes    # Replaces xa with xes (string version)
```

### Control Flow

```go
# If/else (si/aluid)
si xa > 10 {
    dici("big")
} aluid xa > 5 {
    dici("medium")
} aluid {
    dici("small")
}

# While loop (dum)
dum xa > 0 {
    dici(xes)
    xa = xa - 1
}

# For loop (pro)
pro ia in 1..10 {
    dici(ies)
}

pro itemes in ["a", "b", "c"] {
    dici(itemes)
}
```

### Functions

```go
# Function that returns int (name ends in -a)
des adda(xa, ya) {
    redeo xa + ya
}

# Function that returns nothing (name ends in -i)
des greeti(namees) {
    dici("Hello, ")
    dici(namees)
}

# Recursive example
des factoriala(na) {
    si na <= 1 {
        redeo 1
    }
    redeo na * factoriala(na - 1)
}
```

### Lambdas

```go
# Lambda with explicit parameter
des makeo() {
    redeo des (xes) {
        dici(xes)
    }
}

# Lambda with implicit "id" parameter
des printo() {
    redeo des {
        dici(ides)    # "id" is the implicit parameter, "ides" casts it to string
    }
}

fo := makeo()
fo("Hello!")
```

### Structs

```go
personu := {
    "namees": "Alice",
    "agea": 30
}

dici(personu.namees)    # Access field
```

### Operators

```go
# Arithmetic
xa := 2 + 3 * 4    # 14

# Comparison
xam := 5 > 3       # verum
yam := 5 == 5      # verum

# Boolean (et = and, vel = or, non = not)
zam := verum et falsus    # falsus
wam := verum vel falsus   # verum
vam := non verum          # falsus

# Ranges
pro ia in 1..5 { }     # Inclusive: 1, 2, 3, 4, 5
pro ia in 1.<5 { }     # Exclusive: 1, 2, 3, 4
```

### Keywords Reference

| Ago | English | Usage |
|-----|---------|-------|
| `des` | define | Function definition |
| `redeo` | return | Return from function |
| `si` | if | Conditional |
| `aluid` | else | Else branch |
| `dum` | while | While loop |
| `pro` | for | For loop |
| `in` | in | Iterator/range |
| `et` | and | Logical AND |
| `vel` | or | Logical OR |
| `non` | not | Logical NOT |
| `verum` | true | Boolean true |
| `falsus` | false | Boolean false |
| `inanis` | null | Null value |

## CLI Usage

```bash
ago <file.ago>              # Compile and run
ago <file.ago> --check      # Check for errors only
ago <file.ago> --emit=rust  # Output generated Rust code
ago <file.ago> --emit=bin -o prog  # Compile to binary
ago <file.ago> --ast        # Print AST (debugging)
```

## How It Works

Ago is a **transpiler** that converts Ago source code to Rust:

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Ago Source │ ──▶ │    Parser    │ ──▶ │  Semantic   │ ──▶ │     Code     │
│   (.ago)    │     │   (TatSu)    │     │   Checker   │     │  Generator   │
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                                                                     │
                                                                     ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────────┐
│   Execute   │ ◀── │ Rust Compiler│ ◀── │  Generated Rust + Ago Stdlib    │
└─────────────┘     │    (cargo)   │     └─────────────────────────────────┘
                    └──────────────┘
```

The Ago standard library (`ago_stdlib`) provides:
- Type system (`AgoType` enum with Int, Float, String, Bool, etc.)
- Runtime type casting (`as_type()`)
- Built-in functions (`dici`, `apertu`, etc.)
- Operators and collections

## Development

```bash
# Enter development shell
nix develop

# Run tests
pytest test/

# Format code
nix run .#fmt

# Check formatting
nix run .#check-fmt
```

## Project Structure

```
ago/
├── main.py              # CLI entry point
├── src/
│   ├── Ago.g4           # Grammar (TatSu PEG)
│   ├── AgoParser.py     # Generated parser
│   ├── AgoSemanticChecker.py  # Type checking & validation
│   ├── AgoCodeGenerator.py    # Rust code generation
│   └── rust/            # Ago standard library (Rust)
│       └── src/
│           ├── types.rs
│           ├── operators.rs
│           ├── functions.rs
│           └── casting.rs
├── test/                # Test suite
└── flake.nix           # Nix package definition
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [GitHub Repository](https://github.com/libertyluthermoffitt/ago)
- [Standard Library Documentation](docs/stdlib.md)
