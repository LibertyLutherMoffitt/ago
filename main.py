#!/usr/bin/env python3
"""
Ago - A Latin-inspired programming language that transpiles to Python.

Usage:
    ago <file.ago>              Run the program (transpile and execute)
    ago <file.ago> --check      Only run semantic checks
    ago <file.ago> --emit=python  Output generated Python code to stdout
    ago <file.ago> --ast        Print the parsed AST (for debugging)
"""

import argparse
import json
import os
import sys
import ast
from pathlib import Path

from tatsu.util import asjson

from src.AgoParser import AgoParser
from src.AgoSemanticChecker import AgoSemanticChecker
from src.AgoPythonCodeGenerator import generate_python_ast

# Directory where this script lives
SCRIPT_DIR = Path(__file__).parent.resolve()

# Use AGO_HOME if set (for nix package), otherwise use script dir
AGO_HOME = Path(os.environ.get("AGO_HOME", SCRIPT_DIR))

# Standard library location
STDLIB_DIR = AGO_HOME / "stdlib"
AGO_PRELUDE_FILE = STDLIB_DIR / "prelude.ago"
PYTHON_PRELUDE_FILE = AGO_HOME / "src" / "python" / "prelude.py"


# Version
VERSION = "0.2.0" # Bumped version for new backend


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
{Colors.CYAN}{Colors.BOLD} / __ | / (_ // /_/ / {Colors.ENDC}  {Colors.DIM}that transpiles to Python{Colors.ENDC}
{Colors.CYAN}{Colors.BOLD}/_/ |_| \\___/ \\____/  {Colors.ENDC}  {Colors.DIM}v{VERSION}{Colors.ENDC}
"""
    return f"""
   ___    ____  ____
  / _ |  / ___// __ \\   A Latin-inspired language
 / __ | / (_ // /_/ /   that transpiles to Python
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
  {Y}--emit{E}={G}python{E}          Output generated Python code to stdout
  {Y}--ast{E}                  Print the parsed AST
  {Y}--no-color{E}             Disable colored output
  {Y}-q{E}, {Y}--quiet{E}            Suppress info messages

{C}Examples:{E}
  {D}${E} ago hello.ago                      {D}# Run the program{E}
  {D}${E} ago hello.ago {Y}--check{E}              {D}# Check for errors{E}
  {D}${E} ago hello.ago {Y}--emit{E}=python         {D}# Output Python code{E}

{C}Type Endings:{E}
  {G}-a{E}    int        {G}-ae{E}   float      {G}-es{E}    string     {G}-am{E}   bool
  {G}-aem{E}  int[]      {G}-arum{E} float[]    {G}-erum{E}  string[]   {G}-as{E}   bool[]
  {G}-u{E}    struct     {G}-o{E}    function   {G}-e{E}     range      {G}-i{E}    null
  {G}-ium{E}  any        {G}-uum{E}  any[]

{D}Learn more: https://github.com/libertyluthermoffitt/ago{E}
""")


def parse_args():
    """Parse command line arguments."""
    if "-h" in sys.argv or "--help" in sys.argv:
        print_help()
        sys.exit(0)

    if "-v" in sys.argv or "--version" in sys.argv:
        print(f"ago {VERSION} - A Latin-inspired language that transpiles to Python")
        sys.exit(0)

    parser = argparse.ArgumentParser(prog="ago", add_help=False)
    parser.add_argument("file", metavar="FILE")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--emit", choices=["python"], metavar="TYPE")
    parser.add_argument("--ast", action="store_true")
    parser.add_argument("--no-color", action="store_true")
    parser.add_argument("--quiet", "-q", action="store_true")

    return parser.parse_args()


def load_prelude(prelude_file: Path) -> str:
    """Load a prelude file if it exists."""
    if prelude_file.exists():
        try:
            with open(prelude_file, "r") as f:
                return f.read() + "\n"
        except (PermissionError, IOError):
            return ""
    return ""


def read_source(file_path: Path) -> str:
    """Read source file with automatic stdlib prelude inclusion."""
    ago_prelude = load_prelude(AGO_PRELUDE_FILE)
    try:
        with open(file_path, "r") as f:
            user_code = f.read() + "\n"
    except FileNotFoundError:
        print_error(f"file not found: {file_path}")
        sys.exit(1)
    except PermissionError:
        print_error(f"permission denied: {file_path}")
        sys.exit(1)
    return ago_prelude + user_code


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


def main():
    args = parse_args()

    if args.no_color:
        global color_enabled
        color_enabled = lambda: False

    file_path = Path(args.file)
    if not file_path.suffix == ".ago":
        print_warning(f"file does not have .ago extension: {file_path}")

    source = read_source(file_path)
    ago_ast, semantics = parse_source(source, file_path)

    if args.ast:
        print(json.dumps(asjson(ago_ast), indent=2))
        sys.exit(0)

    if semantics.errors:
        print_error(f"found {len(semantics.errors)} error(s) in {file_path}")
        for error in semantics.errors:
            print(f"  {c('→', Colors.RED)} {error}", file=sys.stderr)
        sys.exit(1)

    if args.check:
        print_success(f"no errors in {file_path}")
        sys.exit(0)

    # Generate Python AST
    python_ast = generate_python_ast(ago_ast)
    
    # Unparse to Python code
    python_code = ast.unparse(python_ast)
    
    # Inject Python prelude
    python_prelude = load_prelude(PYTHON_PRELUDE_FILE)
    final_code = python_prelude + "\n" + python_code

    if args.emit == "python":
        print(final_code)
        sys.exit(0)

    # Default: execute the code
    if not args.quiet:
        print(c("─" * 40, Colors.DIM), file=sys.stderr)
    
    try:
        # Execute the generated Python code in its own scope
        exec(final_code, globals())
    except Exception as e:
        print_error("runtime error")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
