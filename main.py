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

# Directory where this script lives
SCRIPT_DIR = Path(__file__).parent.resolve()

# Use AGO_HOME if set (for nix package), otherwise use script dir
AGO_HOME = Path(os.environ.get("AGO_HOME", SCRIPT_DIR))

# For output, use XDG_CACHE_HOME or ~/.cache/ago
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ago"
OUTPUT_DIR = CACHE_DIR / "build"

# Version
VERSION = "0.1.0"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

def color_enabled():
    """Check if colors should be enabled."""
    return sys.stderr.isatty()

def c(text, color):
    """Colorize text if colors are enabled."""
    if color_enabled():
        return f"{color}{text}{Colors.ENDC}"
    return text

def print_banner():
    """Print the Ago banner."""
    banner = r"""
   ___    ____  ____
  / _ |  / ___// __ \
 / __ | / (_ // /_/ /
/_/ |_| \___/ \____/
"""
    if color_enabled():
        print(c(banner, Colors.CYAN), file=sys.stderr)
    

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


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="ago",
        description="Ago - A Latin-inspired programming language that transpiles to Rust",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ago hello.ago              Run the program
  ago hello.ago --check      Check for errors without running
  ago hello.ago --emit=rust  Output Rust code to stdout
  ago hello.ago --emit=bin -o hello  Compile to binary './hello'
  ago hello.ago --ast        Print the AST for debugging

Learn more: https://github.com/joshammer/ago
""",
    )
    
    parser.add_argument(
        "file",
        metavar="FILE",
        help="Ago source file (.ago)",
    )
    
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only run semantic checks, don't compile or run",
    )
    
    parser.add_argument(
        "--emit",
        choices=["rust", "bin"],
        metavar="TYPE",
        help="Emit output: 'rust' for Rust source, 'bin' for compiled binary",
    )
    
    parser.add_argument(
        "-o", "--output",
        metavar="PATH",
        help="Output path for --emit=bin (default: ./program)",
    )
    
    parser.add_argument(
        "--ast",
        action="store_true",
        help="Print the parsed AST (for debugging)",
    )
    
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress informational messages",
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output",
    )
    
    return parser.parse_args()


def read_source(file_path: Path) -> str:
    """Read source file."""
    try:
        with open(file_path, "r") as f:
            return f.read() + "\n"
    except FileNotFoundError:
        print_error(f"file not found: {file_path}")
        sys.exit(1)
    except PermissionError:
        print_error(f"permission denied: {file_path}")
        sys.exit(1)


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


def compile_rust(rust_code: str, output_path: Path, quiet: bool = False, verbose: bool = False) -> Path:
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
            lines = stderr.split('\n')
            error_lines = [l for l in lines if 'error' in l.lower() or '->' in l]
            if error_lines:
                stderr = '\n'.join(error_lines[:20])  # Limit output
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
        global color_enabled
        color_enabled = lambda: False
    
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
    with tempfile.TemporaryDirectory() as tmpdir:
        exe_path = compile_rust(rust_code, OUTPUT_DIR / "target" / "release" / "ago_program", args.quiet, args.verbose)
        
        if not args.quiet:
            print(c("─" * 40, Colors.DIM), file=sys.stderr)
        
        exit_code = run_binary(exe_path)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
