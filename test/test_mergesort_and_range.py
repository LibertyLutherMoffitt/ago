"""
Tests for merge sort (genorduum) and range-to-list casting with indexing.
"""

import subprocess
import tempfile
from pathlib import Path

from src.AgoParser import AgoParser
from src.AgoSemanticChecker import AgoSemanticChecker
from src.AgoCodeGenerator import generate

# Paths
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
STDLIB_DIR = SCRIPT_DIR / "src" / "rust"
PRELUDE_FILE = SCRIPT_DIR / "stdlib" / "prelude.ago"


def compile_and_run(ago_source: str, include_prelude: bool = False) -> str:
    """Compile Ago source to Rust and run it, returning stdout."""
    # Optionally prepend the prelude
    if include_prelude and PRELUDE_FILE.exists():
        prelude = PRELUDE_FILE.read_text() + "\n"
        ago_source = prelude + ago_source

    # Parse and check
    parser = AgoParser()
    semantics = AgoSemanticChecker()
    ast = parser.parse(ago_source + "\n", semantics=semantics)

    if semantics.errors:
        raise ValueError(f"Semantic errors: {semantics.errors}")

    # Generate Rust
    rust_code = generate(ast)

    # Use a unique temp directory for this test
    with tempfile.TemporaryDirectory(prefix="ago_test_") as tmpdir:
        output_dir = Path(tmpdir)
        src_dir = output_dir / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        
        # Write main.rs
        main_rs = src_dir / "main.rs"
        main_rs.write_text(rust_code)
        
        # Write Cargo.toml pointing to the stdlib
        cargo_toml = output_dir / "Cargo.toml"
        cargo_toml.write_text(f'''[package]
name = "ago_program"
version = "0.1.0"
edition = "2021"

[dependencies]
ago_stdlib = {{ path = "{STDLIB_DIR}" }}
''')

        # Compile
        result = subprocess.run(
            ["cargo", "build", "--release"],
            cwd=output_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Compilation failed:\n{result.stderr}")

        # Run
        exe_path = output_dir / "target" / "release" / "ago_program"
        result = subprocess.run([str(exe_path)], capture_output=True, text=True)

        return result.stdout


# =============================================================================
# MERGE SORT (genorduum) TESTS
# =============================================================================


class TestMergeSort:
    """Tests for genorduum merge sort function."""

    def test_sort_ascending_basic(self):
        """Sort a simple list in ascending order."""
        output = compile_and_run(
            '[3, 1, 4, 1, 5, 9, 2, 6].genorduum(des (aium, bium) { aium < bium }).mutatuum(des {ides}).iunges(",").dici()',
            include_prelude=True
        )
        assert output.strip() == "1,1,2,3,4,5,6,9"

    def test_sort_descending_basic(self):
        """Sort a simple list in descending order."""
        output = compile_and_run(
            '[3, 1, 4, 1, 5, 9, 2, 6].genorduum(des (aium, bium) { aium > bium }).mutatuum(des {ides}).iunges(",").dici()',
            include_prelude=True
        )
        assert output.strip() == "9,6,5,4,3,2,1,1"

    def test_sort_already_sorted(self):
        """Sort an already sorted list."""
        output = compile_and_run(
            '[1, 2, 3, 4, 5].genorduum(des (aium, bium) { aium < bium }).mutatuum(des {ides}).iunges(",").dici()',
            include_prelude=True
        )
        assert output.strip() == "1,2,3,4,5"

    def test_sort_reverse_sorted(self):
        """Sort a reverse-sorted list."""
        output = compile_and_run(
            '[5, 4, 3, 2, 1].genorduum(des (aium, bium) { aium < bium }).mutatuum(des {ides}).iunges(",").dici()',
            include_prelude=True
        )
        assert output.strip() == "1,2,3,4,5"

    def test_sort_single_element(self):
        """Sort a single element list."""
        output = compile_and_run(
            '[42].genorduum(des (aium, bium) { aium < bium }).mutatuum(des {ides}).iunges(",").dici()',
            include_prelude=True
        )
        assert output.strip() == "42"

    def test_sort_empty_list(self):
        """Sort an empty list."""
        output = compile_and_run(
            '[].genorduum(des (aium, bium) { aium < bium }).a().es().dici()',
            include_prelude=True
        )
        assert output.strip() == "0"

    def test_sort_two_elements(self):
        """Sort a two element list."""
        output = compile_and_run(
            '[2, 1].genorduum(des (aium, bium) { aium < bium }).mutatuum(des {ides}).iunges(",").dici()',
            include_prelude=True
        )
        assert output.strip() == "1,2"

    def test_sort_negative_numbers(self):
        """Sort a list with negative numbers."""
        output = compile_and_run(
            '[3, -1, 4, -1, 5, -9, 2, -6].genorduum(des (aium, bium) { aium < bium }).mutatuum(des {ides}).iunges(",").dici()',
            include_prelude=True
        )
        assert output.strip() == "-9,-6,-1,-1,2,3,4,5"

    def test_sort_all_same(self):
        """Sort a list where all elements are the same."""
        output = compile_and_run(
            '[5, 5, 5, 5, 5].genorduum(des (aium, bium) { aium < bium }).mutatuum(des {ides}).iunges(",").dici()',
            include_prelude=True
        )
        assert output.strip() == "5,5,5,5,5"

    def test_sort_large_list(self):
        """Sort a larger list to verify recursion works correctly."""
        output = compile_and_run(
            '[1,6,4,2,6,-9,-4,2,1,4,6,89,9,6,4,2,112,3456,78,7654,2,3,456].genorduum(des (aium, bium) { aium < bium }).mutatuum(des {ides}).iunges(",").dici()',
            include_prelude=True
        )
        expected = "-9,-4,1,1,2,2,2,2,3,4,4,4,6,6,6,6,9,78,89,112,456,3456,7654"
        assert output.strip() == expected

    def test_sort_with_zero(self):
        """Sort a list containing zero."""
        output = compile_and_run(
            '[3, 0, -2, 5, 0, -1].genorduum(des (aium, bium) { aium < bium }).mutatuum(des {ides}).iunges(",").dici()',
            include_prelude=True
        )
        assert output.strip() == "-2,-1,0,0,3,5"

    def test_sort_preserves_length(self):
        """Verify sort preserves list length."""
        output = compile_and_run(
            '[9, 1, 8, 2, 7, 3, 6, 4, 5].genorduum(des (aium, bium) { aium < bium }).a().es().dici()',
            include_prelude=True
        )
        assert output.strip() == "9"

    def test_sort_then_min(self):
        """Sort then get minimum (should be first element)."""
        output = compile_and_run(
            '[5, 3, 8, 1, 9].genorduum(des (aium, bium) { aium < bium }).minium().es().dici()',
            include_prelude=True
        )
        assert output.strip() == "1"

    def test_sort_then_max(self):
        """Sort then get maximum (should be last element)."""
        output = compile_and_run(
            '[5, 3, 8, 1, 9].genorduum(des (aium, bium) { aium < bium }).maxium().es().dici()',
            include_prelude=True
        )
        assert output.strip() == "9"


# =============================================================================
# RANGE TO LIST CASTING WITH INDEXING TESTS
# =============================================================================


class TestRangeToListIndexing:
    """Tests for range-to-list casting and indexing."""

    def test_inclusive_range_to_list_index(self):
        """Cast inclusive range to list and index it."""
        output = compile_and_run("""
le := (X..XX)
laem[IV].es().dici()
""")
        # X..XX = 10..20 inclusive = [10,11,12,13,14,15,16,17,18,19,20]
        # Index IV = 4 -> element is 14
        assert output.strip() == "14"

    def test_inclusive_range_first_element(self):
        """Access first element of range cast to list."""
        output = compile_and_run("""
le := (V..X)
laem[0].es().dici()
""")
        # V..X = 5..10 inclusive, index 0 = 5
        assert output.strip() == "5"

    def test_inclusive_range_last_element(self):
        """Access last element of range cast to list."""
        output = compile_and_run("""
le := (I..V)
laem[IV].es().dici()
""")
        # I..V = 1..5 inclusive = [1,2,3,4,5], index 4 = 5
        assert output.strip() == "5"

    def test_exclusive_range_to_list_index(self):
        """Cast exclusive range to list and index it."""
        output = compile_and_run("""
le := (X.<XX)
laem[IV].es().dici()
""")
        # X.<XX = 10..<20 exclusive = [10,11,12,13,14,15,16,17,18,19]
        # Index IV = 4 -> element is 14
        assert output.strip() == "14"

    def test_exclusive_range_last_element(self):
        """Access last element of exclusive range cast to list."""
        output = compile_and_run("""
le := (0.<V)
laem[IV].es().dici()
""")
        # 0.<5 = [0,1,2,3,4], index 4 = 4
        assert output.strip() == "4"

    def test_range_to_list_length(self):
        """Get length of range cast to list."""
        output = compile_and_run("""
le := (I..X)
laem.a().es().dici()
""")
        # I..X = 1..10 inclusive = 10 elements
        assert output.strip() == "10"

    def test_range_to_list_sum(self):
        """Sum elements of range cast to list."""
        output = compile_and_run("""
le := (I..V)
laem.sumium().es().dici()
""", include_prelude=True)
        # I..V = 1..5 = [1,2,3,4,5], sum = 15
        assert output.strip() == "15"

    def test_range_cast_inline(self):
        """Cast range to list inline without intermediate variable."""
        output = compile_and_run("""
le := (I..V)
xa := laem[II]
xes.dici()
""")
        # I..V = 1..5 = [1,2,3,4,5], index 2 = 3
        assert output.strip() == "3"

    def test_range_to_list_iterate(self):
        """Iterate over range cast to list."""
        output = compile_and_run("""
le := (I..III)
pro ia in laem {
    dici(ies)
}
""")
        lines = output.strip().split("\n")
        assert lines == ["1", "2", "3"]

    def test_range_roman_numerals_various(self):
        """Test various Roman numeral ranges."""
        output = compile_and_run("""
le := (I..X)
# First element (I=1)
laem[0].es().dici()
# Middle element (V=5)
laem[IV].es().dici()
# Last element (X=10)
laem[IX].es().dici()
""")
        lines = output.strip().split("\n")
        assert lines == ["1", "5", "10"]

    def test_range_to_list_filter(self):
        """Filter a range cast to list."""
        output = compile_and_run("""
le := (I..X)
laem.liquum(des { id % II == 0 }).mutatuum(des {ides}).iunges(",").dici()
""", include_prelude=True)
        # Filter even numbers from 1..10 = [2,4,6,8,10]
        assert output.strip() == "2,4,6,8,10"

    def test_range_to_list_sort(self):
        """Sort a range (already sorted, should stay same)."""
        output = compile_and_run("""
le := (V..I)
# This range is empty since start > end, but let's test a valid one
re := (I..V)
raem.genorduum(des (aium, bium) { aium > bium }).mutatuum(des {ides}).iunges(",").dici()
""", include_prelude=True)
        # Sort 1..5 descending = [5,4,3,2,1]
        assert output.strip() == "5,4,3,2,1"
