#!/usr/bin/env python3
"""
Ago - A Latin-inspired programming language that transpiles to Rust.

Usage:
    ago <file.ago>              Run the program (compile and execute)
    ago <file.ago> --check      Only run semantic checks
    ago <file.ago> --emit=rust  Output generated Rust code to stdout
    ago <file.ago> --emit=bin   Compile to binary (output to ./program or -o path)
    ago <file.ago> --ast        Print the parsed AST (for debugging)
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from tatsu.util import asjson

from src.AgoParser import AgoParser
from src.AgoSemanticChecker import AgoSemanticChecker
from src.AgoCodeGenerator import generate
from src.AgoLLVMGenerator import generate as generate_llvm

# Directory where this script lives
SCRIPT_DIR = Path(__file__).parent.resolve()

# Use AGO_HOME if set (for nix package), otherwise use script dir
AGO_HOME = Path(os.environ.get("AGO_HOME", SCRIPT_DIR))

# Standard library location
STDLIB_DIR = AGO_HOME / "stdlib"
PRELUDE_FILE = STDLIB_DIR / "prelude.ago"

# For output, use XDG_CACHE_HOME or ~/.cache/ago
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ago"
OUTPUT_DIR = CACHE_DIR / "build"

# Version
VERSION = "0.1.0"


# Colors for terminal output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[35m"
    WHITE = "\033[97m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"


def color_enabled():
    """Check if colors should be enabled."""
    return sys.stdout.isatty() and sys.stderr.isatty()


def c(text, color):
    """Colorize text if colors are enabled."""
    if color_enabled():
        return f"{color}{text}{Colors.ENDC}"
    return text


def get_banner():
    """Get the Ago banner with colors."""
    if color_enabled():
        return f"""
{Colors.CYAN}{Colors.BOLD}   ___    ____  ____  {Colors.ENDC}
{Colors.CYAN}{Colors.BOLD}  / _ |  / ___// __ \\ {Colors.ENDC}  {Colors.DIM}A Latin-inspired language{Colors.ENDC}
{Colors.CYAN}{Colors.BOLD} / __ | / (_ // /_/ / {Colors.ENDC}  {Colors.DIM}that transpiles to Rust{Colors.ENDC}
{Colors.CYAN}{Colors.BOLD}/_/ |_| \\___/ \\____/  {Colors.ENDC}  {Colors.DIM}v{VERSION}{Colors.ENDC}
"""
    return f"""
   ___    ____  ____
  / _ |  / ___// __ \\   A Latin-inspired language
 / __ | / (_ // /_/ /   that transpiles to Rust
/_/ |_| \\___/ \\____/    v{VERSION}
"""


def print_error(msg):
    """Print an error message."""
    print(c("error:", Colors.RED + Colors.BOLD), msg, file=sys.stderr)


def print_warning(msg):
    """Print a warning message."""
    print(c("warning:", Colors.YELLOW + Colors.BOLD), msg, file=sys.stderr)


def print_info(msg):
    """Print an info message."""
    print(c("info:", Colors.CYAN + Colors.BOLD), msg, file=sys.stderr)


def print_success(msg):
    """Print a success message."""
    print(c("✓", Colors.GREEN + Colors.BOLD), msg, file=sys.stderr)


def print_help():
    """Print custom help message with proper alignment."""
    if color_enabled():
        Y = Colors.YELLOW + Colors.BOLD  # Options
        G = Colors.GREEN  # Args
        C = Colors.CYAN + Colors.BOLD  # Headers
        D = Colors.DIM  # Dim
        E = Colors.ENDC  # End
    else:
        Y = G = C = D = E = ""

    print(f"""{get_banner()}
{C}Usage:{E} ago {G}FILE{E} [{Y}OPTIONS{E}]

{C}Arguments:{E}
  {G}FILE{E}                   Ago source file (.ago)

{C}Options:{E}
  {Y}-h{E}, {Y}--help{E}             Show this help message and exit
  {Y}-v{E}, {Y}--version{E}          Show version and exit
  {Y}--check{E}                Only run semantic checks
  {Y}--emit{E} {G}TYPE{E}            Emit 'rust' source or 'bin' binary
  {Y}-o{E}, {Y}--output{E} {G}PATH{E}      Output path for binary (default: ./program)
  {Y}--ast{E}                  Print the parsed AST
  {Y}--no-color{E}             Disable colored output
  {Y}-q{E}, {Y}--quiet{E}            Suppress info messages
  {Y}--verbose{E}              Show verbose output

{C}Examples:{E}
  {D}${E} ago hello.ago                      {D}# Run the program{E}
  {D}${E} ago hello.ago {Y}--check{E}              {D}# Check for errors{E}
  {D}${E} ago hello.ago {Y}--emit{E}=rust          {D}# Output Rust code{E}
  {D}${E} ago hello.ago {Y}--emit{E}=bin {Y}-o{E} hello  {D}# Compile to binary{E}

{C}Type Endings:{E}
  {G}-a{E}    int        {G}-ae{E}   float      {G}-es{E}    string     {G}-am{E}   bool
  {G}-aem{E}  int[]      {G}-arum{E} float[]    {G}-erum{E}  string[]   {G}-as{E}   bool[]
  {G}-u{E}    struct     {G}-o{E}    function   {G}-e{E}     range      {G}-i{E}    null
  {G}-ium{E}  any        {G}-uum{E}  any[]

{D}Learn more: https://github.com/libertyluthermoffitt/ago{E}
""")


def parse_args():
    """Parse command line arguments."""
    # Handle --help manually for custom colored output
    if "-h" in sys.argv or "--help" in sys.argv:
        print_help()
        sys.exit(0)

    # Handle --version manually
    if "-v" in sys.argv or "--version" in sys.argv:
        print(f"ago {VERSION} - A Latin-inspired language that transpiles to Rust")
        sys.exit(0)

    parser = argparse.ArgumentParser(
        prog="ago",
        add_help=False,
    )

    parser.add_argument("file", metavar="FILE")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--emit", choices=["rust", "bin", "llvm"], metavar="TYPE")
    parser.add_argument("--backend", choices=["rust", "llvm"], default="rust", metavar="TYPE")
    parser.add_argument("-o", "--output", metavar="PATH")
    parser.add_argument("--ast", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    return parser.parse_args()


def load_prelude() -> str:
    """Load the standard library prelude if it exists."""
    if PRELUDE_FILE.exists():
        try:
            with open(PRELUDE_FILE, "r") as f:
                return f.read() + "\n"
        except (PermissionError, IOError):
            # Silently skip prelude if we can't read it
            return ""
    return ""


def read_source(file_path: Path) -> str:
    """Read source file with automatic stdlib prelude inclusion."""
    # Load stdlib prelude
    prelude = load_prelude()

    # Load user code
    try:
        with open(file_path, "r") as f:
            user_code = f.read() + "\n"
    except FileNotFoundError:
        print_error(f"file not found: {file_path}")
        sys.exit(1)
    except PermissionError:
        print_error(f"permission denied: {file_path}")
        sys.exit(1)

    # Combine prelude + user code
    return prelude + user_code


def parse_source(source: str, file_path: Path):
    """Parse source and run semantic checks."""
    parser = AgoParser()
    semantics = AgoSemanticChecker()

    try:
        ast = parser.parse(source, semantics=semantics)
    except Exception as e:
        print_error(f"parse error in {file_path}")
        print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    return ast, semantics


def setup_build_dir():
    """Set up the build directory with Cargo.toml."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    src_dir = OUTPUT_DIR / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    # Path to the stdlib - either in AGO_HOME (nix) or relative to script
    stdlib_path = AGO_HOME / "src" / "rust"

    # Create Cargo.toml pointing to the stdlib
    cargo_toml = OUTPUT_DIR / "Cargo.toml"
    cargo_toml.write_text(f'''[package]
name = "ago_program"
version = "0.1.0"
edition = "2021"

[dependencies]
ago_stdlib = {{ path = "{stdlib_path}" }}
''')


def compile_rust(
    rust_code: str, output_path: Path, quiet: bool = False, verbose: bool = False
) -> Path:
    """Compile Rust code to binary."""
    # Set up build directory
    setup_build_dir()

    # Write to output/src/main.rs
    src_dir = OUTPUT_DIR / "src"
    main_rs = src_dir / "main.rs"
    main_rs.write_text(rust_code)

    if verbose:
        print_info(f"generated Rust: {main_rs}")

    # Compile with cargo
    if not quiet:
        print_info("compiling...")

    result = subprocess.run(
        ["cargo", "build", "--release"],
        cwd=OUTPUT_DIR,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print_error("compilation failed")
        # Filter out common warnings for cleaner output
        stderr = result.stderr
        if not verbose:
            lines = stderr.split("\n")
            error_lines = [
                line for line in lines if "error" in line.lower() or "->" in line
            ]
            if error_lines:
                stderr = "\n".join(error_lines[:20])  # Limit output
        print(stderr, file=sys.stderr)
        sys.exit(1)

    # Copy/link to output path
    exe_path = OUTPUT_DIR / "target" / "release" / "ago_program"

    if output_path != exe_path:
        import shutil

        shutil.copy2(exe_path, output_path)

    return output_path


def run_binary(exe_path: Path) -> int:
    """Run the compiled binary."""
    result = subprocess.run([exe_path])
    return result.returncode


def main():
    args = parse_args()

    # Handle --no-color
    if args.no_color:

        def _no_color():
            return False

        global color_enabled
        color_enabled = _no_color

    file_path = Path(args.file)

    # Validate file extension
    if not file_path.suffix == ".ago":
        print_warning(f"file does not have .ago extension: {file_path}")

    # Read source
    source = read_source(file_path)

    # Parse and semantic check
    ast, semantics = parse_source(source, file_path)

    # Handle --ast
    if args.ast:
        print(json.dumps(asjson(ast), indent=2))
        sys.exit(0)

    # Report semantic errors
    if semantics.errors:
        print_error(f"found {len(semantics.errors)} error(s) in {file_path}")
        for error in semantics.errors:
            print(f"  {c('→', Colors.RED)} {error}", file=sys.stderr)
        sys.exit(1)

    # Handle --check
    if args.check:
        print_success(f"no errors in {file_path}")
        sys.exit(0)

    # Generate code based on backend
    if args.backend == "llvm" or args.emit == "llvm":
        # Generate LLVM IR
        llvm_code = generate_llvm(ast)
        
        # Handle --emit=llvm
        if args.emit == "llvm":
            print(llvm_code)
            sys.exit(0)
        
        # For LLVM backend, we need to compile differently
        # For now, just output LLVM IR
        print(llvm_code)
        sys.exit(0)
    else:
        # Generate Rust code
        rust_code = generate(ast)

        # Handle --emit=rust
        if args.emit == "rust":
            print(rust_code)
            sys.exit(0)

    # Handle --emit=bin
    if args.emit == "bin":
        output_path = Path(args.output) if args.output else Path("program")
        exe_path = compile_rust(rust_code, output_path, args.quiet, args.verbose)
        print_success(f"compiled to {exe_path}")
        sys.exit(0)

    # Default: compile and run
    with tempfile.TemporaryDirectory():
        exe_path = compile_rust(
            rust_code,
            OUTPUT_DIR / "target" / "release" / "ago_program",
            args.quiet,
            args.verbose,
        )

        if not args.quiet:
            print(c("─" * 40, Colors.DIM), file=sys.stderr)

        exit_code = run_binary(exe_path)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
