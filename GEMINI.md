# GEMINI.md: Project "Ago"

This document provides a comprehensive overview of the "Ago" project for future development and analysis.

## Project Overview

**Ago** is a compiler for a custom programming language, also named "Ago". The language features Latin-based keywords and a C-style syntax. The compiler's toolchain is written in Python and it is designed to transpile Ago source code into Rust.

The project is in an early, incomplete stage of development. The final architecture is outlined in the Nix configuration, but the core transpilation logic is not yet implemented.

### Key Technologies

*   **Language Implementation:** Python
*   **Parsing:** [Tatsu](https://tatsu.readthedocs.io/en/stable/) library is used to parse the Ago grammar.
*   **Environment & Build:** [Nix Flakes](https://nixos.wiki/wiki/Flakes) are used to define a reproducible development environment and the final build process.
*   **Target Language:** Rust
*   **Development Tools:**
    *   `pytest` for testing.
    *   `ruff` for Python linting.
    *   `pyright` for static type checking.

### Architecture

The project consists of several key components:

1.  **Grammar (`src/Ago.g4`):** A Tatsu grammar file defining the syntax of the Ago language.
2.  **Parser (`src/main.py`):** The current entry point. It uses Tatsu to parse an Ago source file and prints the resulting Abstract Syntax Tree (AST).
3.  **Semantic Analyzer (`src/semantic_checker.py`):** A semantic walker designed to traverse the AST, check for correctness (e.g., variable declarations, type compatibility), and manage symbols using a `SymbolTable`. **Note: This is not yet integrated into the main execution flow.**
4.  **Symbol Table (`src/symbol_table.py`):** A data structure for tracking identifiers (variables, functions) and their properties within different scopes.
5.  **Build Configuration (`flake.nix`):** The source of truth for the intended project architecture. It defines a build process that:
    a.  Executes `src/main.py` to transpile an `.ago` file into a temporary `.rs` file.
    b.  Compiles the generated Rust file with `rustc` to create a native executable.

## Building and Running

The project uses Nix for environment management.

### 1. Setup Development Environment

To get a shell with all the required dependencies (`python`, `tatsu`, `rustc`, `ruff`, `pytest`), run:

```sh
nix develop
```

All subsequent commands should be run inside this shell.

### 2. Running the Parser (Current State)

The `main.py` script currently only parses a file and prints its AST. It does not yet transpile to Rust.

```sh
python src/main.py test/resources/temptare.ago
```

### 3. Building the Transpiler (Intended Final Product)

The `flake.nix` file defines the intended build process. This command will create an `ago` executable in the `result/bin/` directory.

```sh
nix build
```

**Note:** This will currently produce a broken executable. The `ago` script expects `src/main.py` to output Rust code, but it currently outputs a printed AST, which will cause `rustc` to fail.

### 4. Running Tests

The project is configured to use `pytest`.

```sh
pytest
```

## Development Conventions

*   **Linting:** Use `ruff` to check for style and code quality issues.
    ```sh
    ruff check .
    ```
*   **Type Checking:** Use `pyright` to perform static type analysis.
    ```sh
    pyright
    ```
*   **Grammar:** The language grammar is defined in `src/Ago.g4` using Tatsu's syntax.
*   **Semantic Analysis:** The `AgoSemantics` class in `src/semantic_checker.py` is the designated place for implementing semantic rules and checks. Any new language feature will likely require corresponding changes here.
*   **Code Generation:** The Rust code generation logic needs to be implemented in `src/main.py` (or a module it calls) to fulfill the contract defined in `flake.nix`.
