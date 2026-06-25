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
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from tatsu.util import asjson

from src.AgoParser import AgoParser
from src.AgoSemanticChecker import AgoSemanticChecker
from src.AgoCodeGenerator import generate
from src.AgoFormatter import format_source
from src.AgoErrors import render_diagnostic, closest

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
       ago fmt [{Y}--check{E}|{Y}-w{E}] {G}FILE...{E}   {D}# format Ago source{E}
       ago lsp                       {D}# run the language server (stdio){E}

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
    parser.add_argument("--emit", choices=["rust", "bin"], metavar="TYPE")
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


def read_source(file_path: Path):
    """Read source with the stdlib prelude prepended.

    Returns (combined_source, user_code, prelude_line_offset). The offset lets
    error reporting map combined line numbers back to the user's own lines.
    """
    prelude = load_prelude()
    try:
        with open(file_path, "r") as f:
            user_code = f.read() + "\n"
    except FileNotFoundError:
        print_error(f"file not found: {file_path}")
        sys.exit(1)
    except PermissionError:
        print_error(f"permission denied: {file_path}")
        sys.exit(1)
    return prelude + user_code, user_code, prelude.count("\n")


# Keywords + builtins used for "did you mean ...?" suggestions on parse errors.
_KNOWN_WORDS = [
    "si", "aluid", "pro", "dum", "in", "est", "et", "vel", "non", "des",
    "redeo", "frio", "pergo", "omitto", "discerne", "verum", "falsus", "inanis",
]

_CLOSERS = {")": "(", "]": "[", "}": "{"}


def _report_parse_error(exc, file_path, user_code, prelude_offset):
    """Render a TatSu parse failure as a clean Ago diagnostic (no rule stack)."""
    text = str(exc)
    m = re.search(r"\((\d+):(\d+)\)", text)
    user_lines = user_code.split("\n")
    line0 = col0 = None
    if m:
        line0 = int(m.group(1)) - 1 - prelude_offset
        col0 = int(m.group(2)) - 1
    # Pull the "expecting ..." phrase (first line, before the rule stack).
    first = text.split("\n", 1)[0]
    em = re.search(r"expecting (?:one of: )?(.+?)\s*:?\s*$", first)
    expecting = em.group(1).strip() if em else None
    message = "syntax error"
    suggestion = None
    if expecting:
        message = f"syntax error: expecting {expecting}"
        # If exactly one closer is expected, give a concrete hint.
        toks = re.findall(r"'([^']+)'", expecting)
        for t in toks:
            if t in _CLOSERS:
                suggestion = f"add a closing '{t}'"
                break
    if line0 is None or line0 < 0 or not user_lines:
        print_error(f"parse error in {file_path}")
        print(f"  {first}", file=sys.stderr)
        sys.exit(1)
    sys.stderr.write(
        render_diagnostic(
            filename=str(file_path),
            source_lines=user_lines,
            line=line0,
            col=col0,
            length=1,
            message=message,
            label=expecting and f"expected {expecting}" or None,
            suggestion=suggestion,
            color=color_enabled(),
        )
    )
    sys.exit(1)


_OPENERS = {"(": ")", "[": "]", "{": "}"}
_NAMES = {"(": "parenthesis", "[": "bracket", "{": "brace"}


def _check_brackets(user_code, file_path):
    """Precise diagnostics for unbalanced brackets / unterminated strings, which
    TatSu otherwise reports confusingly (e.g. "expecting '['" for a missing
    ')'). Returns True if it reported an error (and exits), else False."""
    lines = user_code.split("\n")
    stack = []  # (char, line0, col0)
    for ln, text in enumerate(lines):
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch == "#":
                break
            if ch == '"':
                j = i + 1
                closed = False
                while j < n:
                    if text[j] == "\\":
                        j += 2
                        continue
                    if text[j] == '"':
                        closed = True
                        break
                    j += 1
                if not closed:
                    _emit_syntax(file_path, lines, ln, i, 1,
                                 "unterminated string literal",
                                 "string is never closed",
                                 "add a closing '\"'")
                    return True
                i = j + 1
                continue
            if ch in _OPENERS:
                stack.append((ch, ln, i))
            elif ch in (")", "]", "}"):
                if not stack:
                    _emit_syntax(file_path, lines, ln, i, 1,
                                 f"unexpected closing '{ch}'",
                                 f"no matching opening {_NAMES[{')':'(',']':'[','}':'{'}[ch]]}",
                                 None)
                    return True
                op, oln, ocol = stack.pop()
                if _OPENERS[op] != ch:
                    _emit_syntax(file_path, lines, ln, i, 1,
                                 f"mismatched '{ch}': expected '{_OPENERS[op]}'",
                                 f"opened with '{op}' here is closed by '{ch}'",
                                 f"did you mean '{_OPENERS[op]}'?")
                    return True
            i += 1
    if stack:
        op, oln, ocol = stack[-1]
        _emit_syntax(file_path, lines, oln, ocol, 1,
                     f"unclosed '{op}'",
                     f"this {_NAMES[op]} is never closed",
                     f"add a closing '{_OPENERS[op]}'")
        return True
    return False


def _emit_syntax(file_path, lines, line0, col0, length, message, label, suggestion):
    sys.stderr.write(
        render_diagnostic(
            filename=str(file_path),
            source_lines=lines,
            line=line0,
            col=col0,
            length=length,
            message=f"syntax error: {message}",
            label=label,
            suggestion=suggestion,
            color=color_enabled(),
        )
    )


def parse_source(source, file_path, user_code, prelude_offset):
    """Parse source (with positions) and run semantic checks."""
    # A cheap, precise pre-check catches the most common syntax mistakes with
    # better messages than the generic parser can give.
    if _check_brackets(user_code, file_path):
        sys.exit(1)

    parser = AgoParser(parseinfo=True)
    semantics = AgoSemanticChecker()
    try:
        ast = parser.parse(source, semantics=semantics)
    except Exception as e:
        _report_parse_error(e, file_path, user_code, prelude_offset)

    return ast, semantics


def _node_loc(node, combined_source):
    """(combined_line0, col0, length) from a node's parseinfo, or None."""
    pi = getattr(node, "parseinfo", None)
    if pi is None:
        return None
    pos = getattr(pi, "pos", None)
    endpos = getattr(pi, "endpos", None)
    line0 = getattr(pi, "line", None)
    if pos is None or line0 is None:
        return None
    line_start = combined_source.rfind("\n", 0, pos) + 1
    col0 = pos - line_start
    length = max(1, (endpos - pos)) if endpos else 1
    return line0, col0, length


def _report_semantic_errors(errors, source, file_path, user_code, prelude_offset):
    user_lines = user_code.split("\n")
    for err in errors:
        loc = _node_loc(getattr(err, "node", None), source)
        if loc:
            cline0, col0, length = loc
            line0 = cline0 - prelude_offset
        elif err.line is not None:
            line0, col0, length = err.line - prelude_offset, None, 1
        else:
            line0, col0, length = 0, None, 1
        if line0 < 0:
            line0 = 0
        suggestion = getattr(err, "suggestion", None)
        sys.stderr.write(
            render_diagnostic(
                filename=str(file_path),
                source_lines=user_lines,
                line=line0,
                col=col0,
                length=min(length, 80),
                message=str(err.message),
                suggestion=suggestion,
                color=color_enabled(),
            )
        )
        sys.stderr.write("\n")


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
    """Run the compiled binary.

    stdout streams to the user live; stderr is captured so that a Rust panic can
    be reformatted as a clean Ago runtime error (no Rust backtrace / file paths).
    """
    env = dict(os.environ)
    env["RUST_BACKTRACE"] = "0"
    result = subprocess.run([exe_path], stderr=subprocess.PIPE, text=True, env=env)
    if result.returncode != 0 and result.stderr:
        _report_runtime_error(result.stderr)
    elif result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode


def _report_runtime_error(stderr: str) -> None:
    """Turn a Rust panic dump into a one-line Ago runtime error."""
    msg = None
    lines = stderr.split("\n")
    for i, line in enumerate(lines):
        if "panicked at" in line:
            # The human message is on the following line(s).
            msg = "\n".join(lines[i + 1 :]).strip()
            # Drop the trailing "note: run with RUST_BACKTRACE..." hint.
            msg = msg.split("\nnote:")[0].strip()
            break
    if not msg:
        # Not a panic we recognize; pass the original through.
        sys.stderr.write(stderr)
        return
    print_error(f"runtime error: {msg}")


def run_fmt(argv) -> int:
    """`ago fmt [--check] [-w|--write] FILE...` - format Ago source.

    With no flags, prints the formatted source to stdout (reads stdin if no
    files). --check reports unformatted files and exits non-zero. -w/--write
    rewrites files in place.
    """
    write = False
    check = False
    files = []
    for a in argv:
        if a in ("-w", "--write"):
            write = True
        elif a == "--check":
            check = True
        elif a in ("-h", "--help"):
            print("usage: ago fmt [--check] [-w|--write] FILE...")
            return 0
        elif a.startswith("-"):
            print_error(f"unknown fmt option: {a}")
            return 2
        else:
            files.append(a)

    if not files:
        sys.stdout.write(format_source(sys.stdin.read()))
        return 0

    rc = 0
    unformatted = False
    for f in files:
        path = Path(f)
        try:
            original = path.read_text()
        except OSError as e:
            print_error(f"cannot read {f}: {e}")
            rc = 1
            continue
        formatted = format_source(original)
        if check:
            if formatted != original:
                print(f"{f}: not formatted", file=sys.stderr)
                unformatted = True
        elif write:
            if formatted != original:
                path.write_text(formatted)
                print_success(f"formatted {f}")
        else:
            sys.stdout.write(formatted)
    if check and unformatted:
        return 1
    return rc


def main():
    # `ago fmt` subcommand
    if len(sys.argv) >= 2 and sys.argv[1] == "fmt":
        sys.exit(run_fmt(sys.argv[2:]))

    # `ago lsp` subcommand: run the language server over stdio
    if len(sys.argv) >= 2 and sys.argv[1] == "lsp":
        from src.AgoLsp import main as lsp_main

        lsp_main()
        sys.exit(0)

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
    source, user_code, prelude_offset = read_source(file_path)

    # Parse and semantic check
    ast, semantics = parse_source(source, file_path, user_code, prelude_offset)

    # Handle --ast
    if args.ast:
        print(json.dumps(asjson(ast), indent=2))
        sys.exit(0)

    # Report semantic errors
    if semantics.errors:
        _report_semantic_errors(
            semantics.errors, source, file_path, user_code, prelude_offset
        )
        n = len(semantics.errors)
        print_error(f"found {n} error(s) in {file_path}")
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
