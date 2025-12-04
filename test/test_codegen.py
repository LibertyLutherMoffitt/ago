"""
Comprehensive test suite for Ago code generation.
Tests compile Ago code to Rust and verify execution output.
"""

import subprocess
import tempfile
import os
from pathlib import Path

from src.AgoParser import AgoParser
from src.AgoSemanticChecker import AgoSemanticChecker
from src.AgoCodeGenerator import generate

# Paths
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
STDLIB_DIR = SCRIPT_DIR / "src" / "rust"
PRELUDE_FILE = SCRIPT_DIR / "stdlib" / "prelude.ago"


def compile_and_run(ago_source: str, include_prelude: bool = False) -> str:
    """Compile Ago source to Rust and run it, returning stdout.
    
    Uses a unique temp directory for each invocation to support parallel testing.
    """
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
# BASIC LITERALS AND DECLARATIONS
# =============================================================================


class TestLiterals:
    """Test basic literal values."""

    def test_int_literal(self):
        output = compile_and_run("xa := 42\ndici(xes)")
        assert output.strip() == "42"

    def test_negative_int(self):
        output = compile_and_run("xa := -17\ndici(xes)")
        assert output.strip() == "-17"

    def test_float_literal(self):
        output = compile_and_run("xae := 3.14\ndici(xes)")
        assert "3.14" in output.strip()

    def test_negative_float(self):
        output = compile_and_run("xae := -2.5\ndici(xes)")
        assert "-2.5" in output.strip()

    def test_string_literal(self):
        output = compile_and_run('dici("hello world")')
        assert output.strip() == "hello world"

    def test_string_with_escape(self):
        output = compile_and_run('dici("line1\\nline2")')
        assert "line1" in output and "line2" in output

    def test_bool_true(self):
        output = compile_and_run("xam := verum\ndici(xes)")
        assert output.strip() == "true"

    def test_bool_false(self):
        output = compile_and_run("xam := falsus\ndici(xes)")
        assert output.strip() == "false"

    def test_roman_numeral_i(self):
        output = compile_and_run("xa := I\ndici(xes)")
        assert output.strip() == "1"

    def test_roman_numeral_iv(self):
        output = compile_and_run("xa := IV\ndici(xes)")
        assert output.strip() == "4"

    def test_roman_numeral_xlii(self):
        output = compile_and_run("xa := XLII\ndici(xes)")
        assert output.strip() == "42"

    def test_roman_numeral_mcmxcix(self):
        output = compile_and_run("xa := MCMXCIX\ndici(xes)")
        assert output.strip() == "1999"


# =============================================================================
# TYPE CASTING VIA VARIABLE ENDINGS
# =============================================================================


class TestTypeCasting:
    """Test type casting via variable name endings."""

    def test_int_to_string(self):
        output = compile_and_run("xa := 123\ndici(xes)")
        assert output.strip() == "123"

    def test_float_to_string(self):
        output = compile_and_run("xae := 1.5\ndici(xes)")
        assert "1.5" in output.strip()

    def test_bool_to_string(self):
        output = compile_and_run("xam := verum\ndici(xes)")
        assert output.strip() == "true"

    def test_int_to_float(self):
        output = compile_and_run("xa := 5\nyae := xae\ndici(yes)")
        assert "5" in output.strip()

    def test_float_to_int(self):
        output = compile_and_run("xae := 3.7\nya := xa\ndici(yes)")
        assert output.strip() == "3"

    def test_int_to_bool(self):
        output = compile_and_run("xa := 1\nyam := xam\ndici(yes)")
        assert output.strip() == "true"

    def test_zero_to_bool(self):
        output = compile_and_run("xa := 0\nyam := xam\ndici(yes)")
        assert output.strip() == "false"

    def test_string_to_int(self):
        output = compile_and_run('xes := "42"\nya := xa\ndici(yes)')
        assert output.strip() == "42"

    def test_stem_replacement(self):
        """Test that declaring a new variable with same stem replaces the old one."""
        output = compile_and_run("xa := 10\nxes := xes\ndici(xes)")
        assert output.strip() == "10"

    def test_stem_replacement_chain(self):
        """Test chained stem replacements."""
        output = compile_and_run("""
xa := 5
xae := xae
xa := xa
dici(xes)
""")
        assert output.strip() == "5"


# =============================================================================
# ARITHMETIC OPERATIONS
# =============================================================================


class TestArithmetic:
    """Test arithmetic operations."""

    def test_addition(self):
        output = compile_and_run("xa := 2 + 3\ndici(xes)")
        assert output.strip() == "5"

    def test_subtraction(self):
        output = compile_and_run("xa := 10 - 4\ndici(xes)")
        assert output.strip() == "6"

    def test_multiplication(self):
        output = compile_and_run("xa := 6 * 7\ndici(xes)")
        assert output.strip() == "42"

    def test_division(self):
        output = compile_and_run("xa := 20 / 4\ndici(xes)")
        assert output.strip() == "5"

    def test_modulo(self):
        output = compile_and_run("xa := 17 % 5\ndici(xes)")
        assert output.strip() == "2"

    def test_float_addition(self):
        output = compile_and_run("xae := 1.5 + 2.5\ndici(xes)")
        assert "4" in output.strip()

    def test_mixed_arithmetic(self):
        output = compile_and_run("xa := 2 + 3 * 4\ndici(xes)")
        assert output.strip() == "14"

    def test_parentheses(self):
        output = compile_and_run("xa := (2 + 3) * 4\ndici(xes)")
        assert output.strip() == "20"

    def test_unary_minus(self):
        output = compile_and_run("xa := 5\nya := -xa\ndici(yes)")
        assert output.strip() == "-5"

    def test_complex_expression(self):
        output = compile_and_run("xa := (10 - 2) * 3 + 4 / 2\ndici(xes)")
        assert output.strip() == "26"


# =============================================================================
# COMPARISON OPERATIONS
# =============================================================================


class TestComparisons:
    """Test comparison operations."""

    def test_less_than_true(self):
        output = compile_and_run("xam := 3 < 5\ndici(xes)")
        assert output.strip() == "true"

    def test_less_than_false(self):
        output = compile_and_run("xam := 5 < 3\ndici(xes)")
        assert output.strip() == "false"

    def test_greater_than_true(self):
        output = compile_and_run("xam := 5 > 3\ndici(xes)")
        assert output.strip() == "true"

    def test_greater_than_false(self):
        output = compile_and_run("xam := 3 > 5\ndici(xes)")
        assert output.strip() == "false"

    def test_less_equal_true(self):
        output = compile_and_run("xam := 3 <= 3\ndici(xes)")
        assert output.strip() == "true"

    def test_less_equal_false(self):
        output = compile_and_run("xam := 4 <= 3\ndici(xes)")
        assert output.strip() == "false"

    def test_greater_equal_true(self):
        output = compile_and_run("xam := 5 >= 5\ndici(xes)")
        assert output.strip() == "true"

    def test_greater_equal_false(self):
        output = compile_and_run("xam := 4 >= 5\ndici(xes)")
        assert output.strip() == "false"

    def test_equality_int(self):
        output = compile_and_run("xam := 5 == 5\ndici(xes)")
        assert output.strip() == "true"

    def test_inequality_int(self):
        output = compile_and_run("xam := 5 != 3\ndici(xes)")
        assert output.strip() == "true"


# =============================================================================
# BOOLEAN OPERATIONS
# =============================================================================


class TestBooleanOps:
    """Test boolean operations."""

    def test_and_true(self):
        output = compile_and_run("xam := verum et verum\ndici(xes)")
        assert output.strip() == "true"

    def test_and_false(self):
        output = compile_and_run("xam := verum et falsus\ndici(xes)")
        assert output.strip() == "false"

    def test_or_true(self):
        output = compile_and_run("xam := falsus vel verum\ndici(xes)")
        assert output.strip() == "true"

    def test_or_false(self):
        output = compile_and_run("xam := falsus vel falsus\ndici(xes)")
        assert output.strip() == "false"

    def test_not_true(self):
        output = compile_and_run("xam := non verum\ndici(xes)")
        assert output.strip() == "false"

    def test_not_false(self):
        output = compile_and_run("xam := non falsus\ndici(xes)")
        assert output.strip() == "true"

    def test_complex_boolean(self):
        output = compile_and_run("xam := (verum et falsus) vel verum\ndici(xes)")
        assert output.strip() == "true"


# =============================================================================
# CONTROL FLOW - IF STATEMENTS
# =============================================================================


class TestIfStatements:
    """Test if/else control flow."""

    def test_if_true(self):
        output = compile_and_run("""
si verum {
    dici("yes")
}
""")
        assert output.strip() == "yes"

    def test_if_false(self):
        output = compile_and_run("""
si falsus {
    dici("yes")
}
dici("done")
""")
        assert output.strip() == "done"

    def test_if_else_true(self):
        output = compile_and_run("""
si verum {
    dici("true branch")
} aluid {
    dici("false branch")
}
""")
        assert output.strip() == "true branch"

    def test_if_else_false(self):
        output = compile_and_run("""
si falsus {
    dici("true branch")
} aluid {
    dici("false branch")
}
""")
        assert output.strip() == "false branch"

    def test_if_elif(self):
        output = compile_and_run("""
xa := 2
si xa == 1 {
    dici("one")
} aluid xa == 2 {
    dici("two")
} aluid {
    dici("other")
}
""")
        assert output.strip() == "two"

    def test_if_with_comparison(self):
        output = compile_and_run("""
xa := 10
si xa > 5 {
    dici("big")
} aluid {
    dici("small")
}
""")
        assert output.strip() == "big"

    def test_nested_if(self):
        output = compile_and_run("""
xa := 5
si xa > 0 {
    si xa < 10 {
        dici("between 0 and 10")
    }
}
""")
        assert output.strip() == "between 0 and 10"


# =============================================================================
# CONTROL FLOW - LOOPS
# =============================================================================


class TestLoops:
    """Test loop control flow."""

    def test_while_basic(self):
        output = compile_and_run("""
xa := 0
dum xa < 3 {
    dici(xes)
    xa = xa + 1
}
""")
        lines = output.strip().split("\n")
        assert lines == ["0", "1", "2"]

    def test_while_countdown(self):
        output = compile_and_run("""
xa := 3
dum xa > 0 {
    dici(xes)
    xa = xa - 1
}
""")
        lines = output.strip().split("\n")
        assert lines == ["3", "2", "1"]

    def test_for_range_inclusive(self):
        output = compile_and_run("""
pro ia in 1..3 {
    dici(ies)
}
""")
        lines = output.strip().split("\n")
        assert lines == ["1", "2", "3"]

    def test_for_range_exclusive(self):
        output = compile_and_run("""
pro ia in 1.<4 {
    dici(ies)
}
""")
        lines = output.strip().split("\n")
        assert lines == ["1", "2", "3"]

    def test_for_list(self):
        output = compile_and_run("""
pro ia in [10, 20, 30] {
    dici(ies)
}
""")
        lines = output.strip().split("\n")
        assert lines == ["10", "20", "30"]


# =============================================================================
# FUNCTIONS
# =============================================================================


class TestFunctions:
    """Test function definitions and calls."""

    def test_simple_function(self):
        output = compile_and_run("""
des greetingi() {
    dici("hello")
}
greetingi()
""")
        assert output.strip() == "hello"

    def test_function_with_param(self):
        output = compile_and_run("""
des printi(xa) {
    dici(xes)
}
printi(42)
""")
        assert output.strip() == "42"

    def test_function_with_return(self):
        output = compile_and_run("""
des doublea(xa) {
    redeo xa * 2
}
ya := doublea(5)
dici(yes)
""")
        assert output.strip() == "10"

    def test_function_multiple_params(self):
        output = compile_and_run("""
des adda(xa, ya) {
    redeo xa + ya
}
za := adda(3, 4)
dici(zes)
""")
        assert output.strip() == "7"

    def test_recursive_factorial(self):
        output = compile_and_run("""
des facta(na) {
    si na <= 1 {
        redeo 1
    }
    redeo na * facta(na - 1)
}
xa := facta(5)
dici(xes)
""")
        assert output.strip() == "120"

    def test_recursive_fibonacci(self):
        output = compile_and_run("""
des fiba(na) {
    si na <= 1 {
        redeo na
    }
    redeo fiba(na - 1) + fiba(na - 2)
}
xa := fiba(10)
dici(xes)
""")
        assert output.strip() == "55"

    def test_function_calling_function(self):
        output = compile_and_run("""
des squarea(xa) {
    redeo xa * xa
}
des square_plus_onea(xa) {
    redeo squarea(xa) + 1
}
ya := square_plus_onea(4)
dici(yes)
""")
        assert output.strip() == "17"


# =============================================================================
# LAMBDAS
# =============================================================================


class TestLambdas:
    """Test lambda functions."""

    def test_lambda_id_keyword(self):
        output = compile_and_run("""
des makeo() {
    redeo des {
        dici(ides)
    }
}
fo := makeo()
fo("hello from lambda")
""")
        assert output.strip() == "hello from lambda"

    def test_lambda_with_param(self):
        output = compile_and_run("""
des makeo() {
    redeo des (xes) {
        dici(xes)
    }
}
fo := makeo()
fo("explicit param")
""")
        assert output.strip() == "explicit param"

    def test_lambda_simple_return(self):
        """Test lambda that returns a value."""
        output = compile_and_run("""
des makeo() {
    redeo des {
        redeo ida * 2
    }
}
fo := makeo()
xa := fo(5)
dici(xes)
""")
        assert output.strip() == "10"

    def test_lambda_implicit_return(self):
        """Test lambda with implicit return (no redeo needed)."""
        output = compile_and_run("""
xo := des { ida * 2 }
xa := xo(5)
dici(xes)
""")
        assert output.strip() == "10"

    def test_lambda_implicit_return_comparison(self):
        """Test lambda with implicit return of a comparison."""
        output = compile_and_run("""
xo := des { ida % 2 == 0 }
xam := xo(4)
dici(xes)
""")
        assert output.strip() == "true"

    def test_ternary_operator(self):
        """Test ternary operator (condition ? true_val : false_val)."""
        output = compile_and_run("""
xa := 5
xes := xa > 3 ? "big" : "small"
dici(xes)
""")
        assert output.strip() == "big"

    def test_ternary_in_lambda(self):
        """Test ternary operator inside a lambda with implicit return."""
        output = compile_and_run("""
xo := des (aium, bium) { aium < bium ? aium : bium }
xa := xo(10, 5)
dici(xes)
""")
        assert output.strip() == "5"

    def test_lambda_filter_with_implicit_return(self):
        """Test filter using lambda with implicit return - the main use case."""
        output = compile_and_run("""
# Define liquum filter function (from prelude)
# Using la shorthand for luum.a() to work around semantic checker limitation
des liquum(luum, xo) {
    ia := 0
    dum ia < la {
        si non xo(luum[ia]) {
            luum.removium(ia)
        } aluid {
            ia = ia + 1
        }
    }
    redeo luum
}

# Test: (0..10).aem().liqes(des { id % 2 == 0 }).dici()
# Range 0..10 cast to int list, filter evens with implicit return, print as string
(0..10).aem().liqes(des { id % 2 == 0 }).dici()
""")
        # Should contain 0, 2, 4, 6, 8, 10 (even numbers from 0 to 10)
        lines = output.strip().split("\n")
        expected = ["0", "2", "4", "6", "8", "10"]
        assert lines == expected

    def test_filter_then_min_with_stem_cast(self):
        """Test filtering a list then finding minimum with stem-based cast."""
        output = compile_and_run("""
des minium(luum) {
    mium := inanis 
    pro lium in luum {
        si non mam vel lium < mium {
            mium = lium
        }
    }
    redeo mium
}

des liquum(luum, xo) {
    ia := 0
    dum ia < la {
        si non xo(luum[ia]) {
            luum.removium(ia)
        } aluid {
            ia = ia + 1
        }
    }
    redeo luum
}

# Filter evens, then get minimum as string
# [-101, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 37].liquum(des { id % 2 == 0 }).mines().dici()
[-101, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 37].liquum(des { id % 2 == 0 }).mines().dici()
""")
        # Even numbers from list are [2, 4, 6, 8, 10], minimum is 2
        assert output.strip() == "2"


# =============================================================================
# LISTS
# =============================================================================


class TestLists:
    """Test list operations."""

    def test_empty_list(self):
        output = compile_and_run("""
xuum := []
dici(xes)
""")
        assert "[]" in output.strip() or output.strip() == ""

    def test_int_list(self):
        output = compile_and_run("""
xaem := [1, 2, 3]
dici(xes)
""")
        assert "1" in output and "2" in output and "3" in output

    def test_bool_list(self):
        output = compile_and_run("""
xas := [verum, falsus, verum]
dici(xes)
""")
        assert "true" in output and "false" in output

    def test_string_list(self):
        output = compile_and_run("""
xerum := ["a", "b", "c"]
dici(xes)
""")
        assert "a" in output and "b" in output and "c" in output

    def test_list_cast_to_string_list(self):
        output = compile_and_run("""
xaem := [1, 2, 3]
yerum := xerum
dici(yes)
""")
        assert "1" in output and "2" in output and "3" in output


# =============================================================================
# STRUCTS
# =============================================================================


class TestStructs:
    """Test struct/map operations."""

    def test_simple_struct(self):
        output = compile_and_run("""
xu := {"namees": "Alice", "agea": 30}
dici(xes)
""")
        assert "Alice" in output or "namees" in output

    def test_struct_field_access(self):
        output = compile_and_run("""
personu := {"namees": "Bob", "agea": 25}
dici(personu.namees)
""")
        assert output.strip() == "Bob"

    def test_struct_field_access_with_method_chain(self):
        """Test struct field access followed by method call."""
        output = compile_and_run("""
personu := {"namees": "Bob", "agea": 25}
personu.namees.dici()
""")
        assert output.strip() == "Bob"


# =============================================================================
# METHOD CHAINING
# =============================================================================


class TestMethodChaining:
    """Test method chaining on various types."""

    def test_string_literal_method_chain(self):
        output = compile_and_run('"hello".dici()')
        assert output.strip() == "hello"

    def test_variable_method_chain(self):
        output = compile_and_run("""
xes := "world"
xes.dici()
""")
        assert output.strip() == "world"

    def test_cast_method_chain(self):
        output = compile_and_run("""
xa := 123
xes.dici()
""")
        assert output.strip() == "123"


# =============================================================================
# RANGES
# =============================================================================


class TestRanges:
    """Test range operations."""

    def test_inclusive_range(self):
        output = compile_and_run("""
pro ia in 1..5 {
    dici(ies)
}
""")
        lines = output.strip().split("\n")
        assert lines == ["1", "2", "3", "4", "5"]

    def test_exclusive_range(self):
        output = compile_and_run("""
pro ia in 0.<3 {
    dici(ies)
}
""")
        lines = output.strip().split("\n")
        assert lines == ["0", "1", "2"]


# =============================================================================
# REASSIGNMENT
# =============================================================================


class TestReassignment:
    """Test variable reassignment."""

    def test_simple_reassignment(self):
        output = compile_and_run("""
xa := 1
xa = 2
dici(xes)
""")
        assert output.strip() == "2"

    def test_reassignment_with_expression(self):
        output = compile_and_run("""
xa := 5
xa = xa + 10
dici(xes)
""")
        assert output.strip() == "15"

    def test_reassignment_in_loop(self):
        output = compile_and_run("""
suma := 0
pro ia in 1..5 {
    suma = suma + ia
}
dici(sumes)
""")
        assert output.strip() == "15"


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_zero(self):
        output = compile_and_run("xa := 0\ndici(xes)")
        assert output.strip() == "0"

    def test_large_number(self):
        output = compile_and_run("xa := 1000000\ndici(xes)")
        assert output.strip() == "1000000"

    def test_empty_string(self):
        output = compile_and_run('dici("")')
        assert output.strip() == ""

    def test_multiple_statements(self):
        output = compile_and_run("""
dici("one")
dici("two")
dici("three")
""")
        lines = output.strip().split("\n")
        assert lines == ["one", "two", "three"]

    def test_nested_parentheses(self):
        output = compile_and_run("xa := ((1 + 2) * (3 + 4))\ndici(xes)")
        assert output.strip() == "21"

    def test_chained_comparisons_in_if(self):
        output = compile_and_run("""
xa := 5
si xa > 0 et xa < 10 {
    dici("in range")
}
""")
        assert output.strip() == "in range"

    def test_function_param_reassignment(self):
        output = compile_and_run("""
des modifya(xa) {
    xa = xa * 2
    redeo xa
}
ya := modifya(5)
dici(yes)
""")
        assert output.strip() == "10"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_fizzbuzz_simple(self):
        output = compile_and_run("""
pro ia in 1..15 {
    si ia % 15 == 0 {
        dici("FizzBuzz")
    } aluid ia % 3 == 0 {
        dici("Fizz")
    } aluid ia % 5 == 0 {
        dici("Buzz")
    } aluid {
        dici(ies)
    }
}
""")
        lines = output.strip().split("\n")
        assert lines[0] == "1"
        assert lines[2] == "Fizz"
        assert lines[4] == "Buzz"
        assert lines[14] == "FizzBuzz"

    def test_sum_of_squares(self):
        output = compile_and_run("""
des squarea(xa) {
    redeo xa * xa
}
suma := 0
pro ia in 1..5 {
    suma = suma + squarea(ia)
}
dici(sumes)
""")
        # 1 + 4 + 9 + 16 + 25 = 55
        assert output.strip() == "55"

    def test_countdown_with_function(self):
        output = compile_and_run("""
des countdowni(na) {
    dum na > 0 {
        dici(nes)
        na = na - 1
    }
    dici("Blast off!")
}
countdowni(3)
""")
        lines = output.strip().split("\n")
        assert lines == ["3", "2", "1", "Blast off!"]

    def test_power_function(self):
        output = compile_and_run("""
des powa(basea, expa) {
    resulta := 1
    dum expa > 0 {
        resulta = resulta * basea
        expa = expa - 1
    }
    redeo resulta
}
xa := powa(2, 8)
dici(xes)
""")
        assert output.strip() == "256"

    def test_gcd(self):
        output = compile_and_run("""
des gcda(aa, ba) {
    dum ba != 0 {
        tempa := ba
        ba = aa % ba
        aa = tempa
    }
    redeo aa
}
xa := gcda(48, 18)
dici(xes)
""")
        assert output.strip() == "6"

    def test_is_prime(self):
        output = compile_and_run("""
des is_primeam(na) {
    si na < 2 {
        redeo falsus
    }
    ia := 2
    dum ia * ia <= na {
        si na % ia == 0 {
            redeo falsus
        }
        ia = ia + 1
    }
    redeo verum
}
xam := is_primeam(7)
dici(xes)
yam := is_primeam(8)
dici(yes)
zam := is_primeam(11)
dici(zes)
""")
        lines = output.strip().split("\n")
        assert lines == ["true", "false", "true"]

    def test_list_iteration_sum(self):
        output = compile_and_run("""
numbersaem := [10, 20, 30, 40]
suma := 0
pro na in numbersaem {
    suma = suma + na
}
dici(sumes)
""")
        assert output.strip() == "100"

    def test_nested_loops(self):
        output = compile_and_run("""
pro ia in 1..3 {
    pro ja in 1..3 {
        xa := ia * ja
        dici(xes)
    }
}
""")
        lines = output.strip().split("\n")
        expected = ["1", "2", "3", "2", "4", "6", "3", "6", "9"]
        assert lines == expected

    def test_accumulator_pattern(self):
        output = compile_and_run("""
producta := 1
pro ia in 1..5 {
    producta = producta * ia
}
dici(productes)
""")
        # 5! = 120
        assert output.strip() == "120"


# =============================================================================
# FUNCTION CALL CASTING (Stem-based)
# =============================================================================


class TestFunctionCallCasting:
    """Test stem-based function call casting (e.g., aae() calls aa() with float cast)."""

    def test_int_to_float_cast(self):
        """Calling geta() as getae() casts result to float."""
        output = compile_and_run("""
des geta() {
    redeo 42
}
xae := getae()
dici(xes)
""")
        assert "42" in output.strip()

    def test_int_to_string_cast(self):
        """Calling geta() as getes() casts result to string."""
        output = compile_and_run("""
des geta() {
    redeo 123
}
xes := getes()
dici(xes)
""")
        assert output.strip() == "123"

    def test_int_to_bool_cast(self):
        """Calling geta() as getam() casts result to bool."""
        output = compile_and_run("""
des geta() {
    redeo 1
}
xam := getam()
dici(xes)
""")
        assert output.strip() == "true"

    def test_zero_to_bool_cast(self):
        """Calling geta() as getam() casts 0 to false."""
        output = compile_and_run("""
des zeroa() {
    redeo 0
}
xam := zeroam()
dici(xes)
""")
        assert output.strip() == "false"

    def test_float_to_int_cast(self):
        """Calling getae() as geta() casts result to int (truncation)."""
        output = compile_and_run("""
des pirae() {
    redeo 3.14
}
xa := pira()
dici(xes)
""")
        assert output.strip() == "3"

    def test_float_to_string_cast(self):
        """Calling getae() as getes() casts result to string."""
        output = compile_and_run("""
des pirae() {
    redeo 3.14
}
xes := pires()
dici(xes)
""")
        assert "3.14" in output.strip()

    def test_bool_to_string_cast(self):
        """Calling getam() as getes() casts result to string."""
        output = compile_and_run("""
des flagam() {
    redeo verum
}
xes := flages()
dici(xes)
""")
        assert output.strip() == "true"

    def test_function_with_params_cast(self):
        """Function with parameters can also have its result casted."""
        output = compile_and_run("""
des adda(xa, ya) {
    redeo xa + ya
}
xae := addae(3, 4)
dici(xes)
""")
        assert "7" in output.strip()

    def test_recursive_function_cast(self):
        """Recursive function call with cast on the outer call."""
        output = compile_and_run("""
des facta(na) {
    si na <= 1 {
        redeo 1
    }
    redeo na * facta(na - 1)
}
xes := factes(5)
dici(xes)
""")
        assert output.strip() == "120"

    def test_cast_in_expression(self):
        """Cast result used in expression."""
        output = compile_and_run("""
des geta() {
    redeo 10
}
xae := getae() + 0.5
dici(xes)
""")
        assert "10.5" in output.strip()

    def test_direct_print_cast(self):
        """Cast result directly used without assignment."""
        output = compile_and_run("""
des numbera() {
    redeo 99
}
dici(numberes())
""")
        assert output.strip() == "99"


class TestStdlibPrelude:
    """Tests for all stdlib/prelude.ago functions."""

    # ===== abbium (absolute value) =====
    def test_abbium_positive(self):
        """abbium returns positive number unchanged."""
        output = compile_and_run('abbium(42).es().dici()', include_prelude=True)
        assert output.strip() == "42"

    def test_abbium_negative(self):
        """abbium returns absolute value of negative number."""
        output = compile_and_run('abbium(-42).es().dici()', include_prelude=True)
        assert output.strip() == "42"

    def test_abbium_zero(self):
        """abbium returns zero unchanged."""
        output = compile_and_run('abbium(0).es().dici()', include_prelude=True)
        assert output.strip() == "0"

    # ===== appenduum (append to list) =====
    def test_appenduum_basic(self):
        """appenduum appends element to list."""
        output = compile_and_run('[1, 2, 3].appenduum(4).a().es().dici()', include_prelude=True)
        assert output.strip() == "4"

    def test_appenduum_empty_list(self):
        """appenduum works on empty list."""
        output = compile_and_run('[].appenduum(1).a().es().dici()', include_prelude=True)
        assert output.strip() == "1"

    def test_appenduum_string_list(self):
        """appenduum works with string lists."""
        output = compile_and_run('["a", "b"].appenduum("c").iunges("").dici()', include_prelude=True)
        assert output.strip() == "abc"

    # ===== vicissuum (reverse list) =====
    def test_vicissuum_basic(self):
        """vicissuum reverses a list."""
        output = compile_and_run('[1, 2, 3].vicissuum().mutatuum(des {ides}).iunges(",").dici()', include_prelude=True)
        assert output.strip() == "3,2,1"

    def test_vicissuum_empty(self):
        """vicissuum handles empty list."""
        output = compile_and_run('[].vicissuum().a().es().dici()', include_prelude=True)
        assert output.strip() == "0"

    def test_vicissuum_single(self):
        """vicissuum handles single element list."""
        output = compile_and_run('[42].vicissuum().sumium().es().dici()', include_prelude=True)
        assert output.strip() == "42"

    # ===== spoliares (strip whitespace) =====
    def test_spoliares_leading(self):
        """spoliares removes leading whitespace."""
        output = compile_and_run('"   hello".spoliares().dici()', include_prelude=True)
        assert output.strip() == "hello"

    def test_spoliares_trailing(self):
        """spoliares removes trailing whitespace."""
        output = compile_and_run('"hello   ".spoliares().dici()', include_prelude=True)
        assert output.strip() == "hello"

    def test_spoliares_both(self):
        """spoliares removes both leading and trailing whitespace."""
        output = compile_and_run('"  hello  ".spoliares().dici()', include_prelude=True)
        assert output.strip() == "hello"

    def test_spoliares_tabs_newlines(self):
        """spoliares removes tabs and newlines."""
        output = compile_and_run('"\\t\\nhello\\n\\t".spoliares().dici()', include_prelude=True)
        assert output.strip() == "hello"

    def test_spoliares_no_whitespace(self):
        """spoliares handles string with no whitespace."""
        output = compile_and_run('"hello".spoliares().dici()', include_prelude=True)
        assert output.strip() == "hello"

    # ===== digitam (is all digits) =====
    def test_digitam_all_digits(self):
        """digitam returns true for all digits."""
        output = compile_and_run('"12345".digitam().es().dici()', include_prelude=True)
        assert output.strip() == "true"

    def test_digitam_with_letters(self):
        """digitam returns false if letters present."""
        output = compile_and_run('"123a45".digitam().es().dici()', include_prelude=True)
        assert output.strip() == "false"

    def test_digitam_empty(self):
        """digitam returns true for empty string."""
        output = compile_and_run('"".digitam().es().dici()', include_prelude=True)
        assert output.strip() == "true"

    def test_digitam_with_space(self):
        """digitam returns false if space present."""
        output = compile_and_run('"123 45".digitam().es().dici()', include_prelude=True)
        assert output.strip() == "false"

    # ===== iunges (join list with separator) =====
    def test_iunges_basic(self):
        """iunges joins list with separator."""
        output = compile_and_run('["a", "b", "c"].iunges("-").dici()', include_prelude=True)
        assert output.strip() == "a-b-c"

    def test_iunges_empty_separator(self):
        """iunges joins with empty separator."""
        output = compile_and_run('["a", "b", "c"].iunges("").dici()', include_prelude=True)
        assert output.strip() == "abc"

    def test_iunges_single_element(self):
        """iunges handles single element list."""
        output = compile_and_run('["hello"].iunges(",").dici()', include_prelude=True)
        assert output.strip() == "hello"

    def test_iunges_multi_char_separator(self):
        """iunges works with multi-char separator."""
        output = compile_and_run('["a", "b", "c"].iunges(" - ").dici()', include_prelude=True)
        assert output.strip() == "a - b - c"

    # ===== liquum (filter list) =====
    def test_liquum_filter_evens(self):
        """liquum filters list keeping elements where predicate is true."""
        output = compile_and_run('[1, 2, 3, 4, 5, 6].liquum(des {id % 2 == 0}).sumium().es().dici()', include_prelude=True)
        assert output.strip() == "12"  # 2+4+6

    def test_liquum_filter_all(self):
        """liquum filters out all elements."""
        output = compile_and_run('[1, 2, 3].liquum(des {id > 10}).a().es().dici()', include_prelude=True)
        assert output.strip() == "0"

    def test_liquum_filter_none(self):
        """liquum keeps all elements when predicate always true."""
        output = compile_and_run('[1, 2, 3].liquum(des {id > 0}).a().es().dici()', include_prelude=True)
        assert output.strip() == "3"

    # ===== plicium (fold/reduce) =====
    def test_plicium_sum(self):
        """plicium sums list elements."""
        output = compile_and_run('[1, 2, 3, 4].plicium(des (aium, bium) {aium + bium}).es().dici()', include_prelude=True)
        assert output.strip() == "10"

    def test_plicium_product(self):
        """plicium multiplies list elements."""
        output = compile_and_run('[1, 2, 3, 4].plicium(des (aium, bium) {aium * bium}).es().dici()', include_prelude=True)
        assert output.strip() == "24"

    def test_plicium_empty_list(self):
        """plicium returns inanis for empty list."""
        output = compile_and_run("""
xa := [].plicium(des (aium, bium) {aium + bium})
si xa == inanis { dici("null") } aluid { dici("not null") }
""", include_prelude=True)
        assert output.strip() == "null"

    def test_plicium_single_element(self):
        """plicium returns single element unchanged."""
        output = compile_and_run('[42].plicium(des (aium, bium) {aium + bium}).es().dici()', include_prelude=True)
        assert output.strip() == "42"

    # ===== mutatuum (map list) =====
    def test_mutatuum_double(self):
        """mutatuum doubles all elements."""
        output = compile_and_run('[1, 2, 3].mutatuum(des {id * 2}).sumium().es().dici()', include_prelude=True)
        assert output.strip() == "12"  # 2+4+6

    def test_mutatuum_square(self):
        """mutatuum squares all elements."""
        output = compile_and_run('[1, 2, 3, 4].mutatuum(des {id * id}).sumium().es().dici()', include_prelude=True)
        assert output.strip() == "30"  # 1+4+9+16

    def test_mutatuum_empty_list(self):
        """mutatuum handles empty list."""
        output = compile_and_run('[].mutatuum(des {id * 2}).a().es().dici()', include_prelude=True)
        assert output.strip() == "0"

    # ===== minium (minimum element) =====
    def test_minium_basic(self):
        """minium returns minimum element."""
        output = compile_and_run('[3, 1, 4, 1, 5].minium().es().dici()', include_prelude=True)
        assert output.strip() == "1"

    def test_minium_negative(self):
        """minium works with negative numbers."""
        output = compile_and_run('[3, -5, 2, -1].minium().es().dici()', include_prelude=True)
        assert output.strip() == "-5"

    def test_minium_single(self):
        """minium returns single element."""
        output = compile_and_run('[42].minium().es().dici()', include_prelude=True)
        assert output.strip() == "42"

    # ===== maxium (maximum element) =====
    def test_maxium_basic(self):
        """maxium returns maximum element."""
        output = compile_and_run('[3, 1, 4, 1, 5].maxium().es().dici()', include_prelude=True)
        assert output.strip() == "5"

    def test_maxium_negative(self):
        """maxium works with negative numbers."""
        output = compile_and_run('[-3, -5, -2, -1].maxium().es().dici()', include_prelude=True)
        assert output.strip() == "-1"

    def test_maxium_single(self):
        """maxium returns single element."""
        output = compile_and_run('[42].maxium().es().dici()', include_prelude=True)
        assert output.strip() == "42"

    # ===== finderum (split string) =====
    def test_finderum_basic(self):
        """finderum splits string on separator."""
        output = compile_and_run('"a,b,c".finderum(",").iunges("-").dici()', include_prelude=True)
        assert output.strip() == "a-b-c"

    def test_finderum_no_separator(self):
        """finderum returns single element when separator not found."""
        output = compile_and_run('"hello".finderum(",").a().es().dici()', include_prelude=True)
        assert output.strip() == "1"

    def test_finderum_multiple_separators(self):
        """finderum handles multiple consecutive separators."""
        output = compile_and_run('"a,,b".finderum(",").a().es().dici()', include_prelude=True)
        assert output.strip() == "2"

    def test_finderum_newline(self):
        """finderum splits on newline."""
        output = compile_and_run('"line1\\nline2\\nline3".finderum("\\n").a().es().dici()', include_prelude=True)
        assert output.strip() == "3"

    # ===== sumium (sum of list) =====
    def test_sumium_basic(self):
        """sumium returns sum of list elements."""
        output = compile_and_run('[1, 2, 3, 4, 5].sumium().es().dici()', include_prelude=True)
        assert output.strip() == "15"

    def test_sumium_negative(self):
        """sumium handles negative numbers."""
        output = compile_and_run('[1, -2, 3, -4].sumium().es().dici()', include_prelude=True)
        assert output.strip() == "-2"

    def test_sumium_single(self):
        """sumium returns single element."""
        output = compile_and_run('[42].sumium().es().dici()', include_prelude=True)
        assert output.strip() == "42"

    def test_sumium_floats(self):
        """sumium works with floats."""
        output = compile_and_run('[1.5, 2.5, 3.0].sumium().es().dici()', include_prelude=True)
        assert "7" in output.strip()

    # ===== prodium (product of list) =====
    def test_prodium_basic(self):
        """prodium returns product of list elements."""
        output = compile_and_run('[1, 2, 3, 4].prodium().es().dici()', include_prelude=True)
        assert output.strip() == "24"

    def test_prodium_with_zero(self):
        """prodium returns zero if any element is zero."""
        output = compile_and_run('[1, 2, 0, 4].prodium().es().dici()', include_prelude=True)
        assert output.strip() == "0"

    def test_prodium_negative(self):
        """prodium handles negative numbers."""
        output = compile_and_run('[2, -3, 4].prodium().es().dici()', include_prelude=True)
        assert output.strip() == "-24"

    def test_prodium_single(self):
        """prodium returns single element."""
        output = compile_and_run('[42].prodium().es().dici()', include_prelude=True)
        assert output.strip() == "42"

    # ===== invena (find index) =====
    def test_invena_found(self):
        """invena returns index when element found."""
        output = compile_and_run('[10, 20, 30, 40].invena(30).es().dici()', include_prelude=True)
        assert output.strip() == "2"

    def test_invena_first(self):
        """invena returns first occurrence index."""
        output = compile_and_run('[1, 2, 2, 3].invena(2).es().dici()', include_prelude=True)
        assert output.strip() == "1"

    def test_invena_not_found(self):
        """invena returns inanis when element not found."""
        output = compile_and_run("""
xa := [1, 2, 3].invena(99)
si xa == inanis { dici("not found") } aluid { dici("found") }
""", include_prelude=True)
        assert output.strip() == "not found"

    def test_invena_string_list(self):
        """invena works with string lists."""
        output = compile_and_run('["a", "b", "c"].invena("b").es().dici()', include_prelude=True)
        assert output.strip() == "1"
