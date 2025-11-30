import sys
import subprocess
from pathlib import Path

from src.AgoParser import AgoParser
from src.AgoSemanticChecker import AgoSemanticChecker
from src.AgoCodeGenerator import generate

# Directory where this script lives
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "output"


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <file.ago> [options]", file=sys.stderr)
        print("Options:", file=sys.stderr)
        print("  --check-only   Only run semantic checks", file=sys.stderr)
        print("  --compile      Compile to executable", file=sys.stderr)
        print("  --run          Compile and run", file=sys.stderr)
        sys.exit(1)

    file = sys.argv[1]
    check_only = "--check-only" in sys.argv
    do_compile = "--compile" in sys.argv or "--run" in sys.argv
    do_run = "--run" in sys.argv

    with open(file, "r") as f:
        source = f.read() + "\n"

    # Parse and run semantic checks
    semantics = AgoSemanticChecker()
    parser = AgoParser()
    ast = parser.parse(source, semantics=semantics)

    if semantics.errors:
        print("Semantic errors found:", file=sys.stderr)
        for error in semantics.errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    if check_only:
        print("Semantic check passed - no errors.", file=sys.stderr)
        sys.exit(0)

    # Generate Rust code
    rust_code = generate(ast)

    if do_compile:
        # Write to output/src/main.rs
        src_dir = OUTPUT_DIR / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        main_rs = src_dir / "main.rs"
        main_rs.write_text(rust_code)
        print(f"Generated: {main_rs}", file=sys.stderr)

        # Compile with cargo
        print("Compiling...", file=sys.stderr)
        result = subprocess.run(
            ["cargo", "build", "--release"],
            cwd=OUTPUT_DIR,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print("Compilation failed:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            sys.exit(1)

        exe_path = OUTPUT_DIR / "target" / "release" / "ago_program"
        print(f"Compiled: {exe_path}", file=sys.stderr)

        if do_run:
            print("Running...", file=sys.stderr)
            print("-" * 40, file=sys.stderr)
            subprocess.run([exe_path])
    else:
        # Just print the generated code
        print(rust_code)


if __name__ == "__main__":
    main()
