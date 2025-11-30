"""
Comprehensive test suite for Ago code generation.
Tests compile Ago code to Rust and verify execution output.
"""

import subprocess
import pytest
from pathlib import Path

from src.AgoParser import AgoParser
from src.AgoSemanticChecker import AgoSemanticChecker
from src.AgoCodeGenerator import generate

# Paths
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "output"
SRC_DIR = OUTPUT_DIR / "src"
MAIN_RS = SRC_DIR / "main.rs"


def compile_and_run(ago_source: str) -> str:
    """Compile Ago source to Rust and run it, returning stdout."""
    # Parse and check
    parser = AgoParser()
    semantics = AgoSemanticChecker()
    ast = parser.parse(ago_source + "\n", semantics=semantics)
    
    if semantics.errors:
        raise ValueError(f"Semantic errors: {semantics.errors}")
    
    # Generate Rust
    rust_code = generate(ast)
    
    # Write to file
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    MAIN_RS.write_text(rust_code)
    
    # Compile
    result = subprocess.run(
        ["cargo", "build", "--release"],
        cwd=OUTPUT_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Compilation failed:\n{result.stderr}")
    
    # Run
    exe_path = OUTPUT_DIR / "target" / "release" / "ago_program"
    result = subprocess.run([str(exe_path)], capture_output=True, text=True)
    
    return result.stdout


# =============================================================================
# BASIC LITERALS AND DECLARATIONS
# =============================================================================

class TestLiterals:
    """Test basic literal values."""
    
    def test_int_literal(self):
        output = compile_and_run('xa := 42\ndici(xes)')
        assert output.strip() == "42"
    
    def test_negative_int(self):
        output = compile_and_run('xa := -17\ndici(xes)')
        assert output.strip() == "-17"
    
    def test_float_literal(self):
        output = compile_and_run('xae := 3.14\ndici(xes)')
        assert "3.14" in output.strip()
    
    def test_negative_float(self):
        output = compile_and_run('xae := -2.5\ndici(xes)')
        assert "-2.5" in output.strip()
    
    def test_string_literal(self):
        output = compile_and_run('dici("hello world")')
        assert output.strip() == "hello world"
    
    def test_string_with_escape(self):
        output = compile_and_run('dici("line1\\nline2")')
        assert "line1" in output and "line2" in output
    
    def test_bool_true(self):
        output = compile_and_run('xam := verum\ndici(xes)')
        assert output.strip() == "true"
    
    def test_bool_false(self):
        output = compile_and_run('xam := falsus\ndici(xes)')
        assert output.strip() == "false"
    
    def test_roman_numeral_i(self):
        output = compile_and_run('xa := I\ndici(xes)')
        assert output.strip() == "1"
    
    def test_roman_numeral_iv(self):
        output = compile_and_run('xa := IV\ndici(xes)')
        assert output.strip() == "4"
    
    def test_roman_numeral_xlii(self):
        output = compile_and_run('xa := XLII\ndici(xes)')
        assert output.strip() == "42"
    
    def test_roman_numeral_mcmxcix(self):
        output = compile_and_run('xa := MCMXCIX\ndici(xes)')
        assert output.strip() == "1999"


# =============================================================================
# TYPE CASTING VIA VARIABLE ENDINGS
# =============================================================================

class TestTypeCasting:
    """Test type casting via variable name endings."""
    
    def test_int_to_string(self):
        output = compile_and_run('xa := 123\ndici(xes)')
        assert output.strip() == "123"
    
    def test_float_to_string(self):
        output = compile_and_run('xae := 1.5\ndici(xes)')
        assert "1.5" in output.strip()
    
    def test_bool_to_string(self):
        output = compile_and_run('xam := verum\ndici(xes)')
        assert output.strip() == "true"
    
    def test_int_to_float(self):
        output = compile_and_run('xa := 5\nyae := xae\ndici(yes)')
        assert "5" in output.strip()
    
    def test_float_to_int(self):
        output = compile_and_run('xae := 3.7\nya := xa\ndici(yes)')
        assert output.strip() == "3"
    
    def test_int_to_bool(self):
        output = compile_and_run('xa := 1\nyam := xam\ndici(yes)')
        assert output.strip() == "true"
    
    def test_zero_to_bool(self):
        output = compile_and_run('xa := 0\nyam := xam\ndici(yes)')
        assert output.strip() == "false"
    
    def test_string_to_int(self):
        output = compile_and_run('xes := "42"\nya := xa\ndici(yes)')
        assert output.strip() == "42"
    
    def test_stem_replacement(self):
        """Test that declaring a new variable with same stem replaces the old one."""
        output = compile_and_run('xa := 10\nxes := xes\ndici(xes)')
        assert output.strip() == "10"
    
    def test_stem_replacement_chain(self):
        """Test chained stem replacements."""
        output = compile_and_run('''
xa := 5
xae := xae
xa := xa
dici(xes)
''')
        assert output.strip() == "5"


# =============================================================================
# ARITHMETIC OPERATIONS
# =============================================================================

class TestArithmetic:
    """Test arithmetic operations."""
    
    def test_addition(self):
        output = compile_and_run('xa := 2 + 3\ndici(xes)')
        assert output.strip() == "5"
    
    def test_subtraction(self):
        output = compile_and_run('xa := 10 - 4\ndici(xes)')
        assert output.strip() == "6"
    
    def test_multiplication(self):
        output = compile_and_run('xa := 6 * 7\ndici(xes)')
        assert output.strip() == "42"
    
    def test_division(self):
        output = compile_and_run('xa := 20 / 4\ndici(xes)')
        assert output.strip() == "5"
    
    def test_modulo(self):
        output = compile_and_run('xa := 17 % 5\ndici(xes)')
        assert output.strip() == "2"
    
    def test_float_addition(self):
        output = compile_and_run('xae := 1.5 + 2.5\ndici(xes)')
        assert "4" in output.strip()
    
    def test_mixed_arithmetic(self):
        output = compile_and_run('xa := 2 + 3 * 4\ndici(xes)')
        assert output.strip() == "14"
    
    def test_parentheses(self):
        output = compile_and_run('xa := (2 + 3) * 4\ndici(xes)')
        assert output.strip() == "20"
    
    def test_unary_minus(self):
        output = compile_and_run('xa := 5\nya := -xa\ndici(yes)')
        assert output.strip() == "-5"
    
    def test_complex_expression(self):
        output = compile_and_run('xa := (10 - 2) * 3 + 4 / 2\ndici(xes)')
        assert output.strip() == "26"


# =============================================================================
# COMPARISON OPERATIONS
# =============================================================================

class TestComparisons:
    """Test comparison operations."""
    
    def test_less_than_true(self):
        output = compile_and_run('xam := 3 < 5\ndici(xes)')
        assert output.strip() == "true"
    
    def test_less_than_false(self):
        output = compile_and_run('xam := 5 < 3\ndici(xes)')
        assert output.strip() == "false"
    
    def test_greater_than_true(self):
        output = compile_and_run('xam := 5 > 3\ndici(xes)')
        assert output.strip() == "true"
    
    def test_greater_than_false(self):
        output = compile_and_run('xam := 3 > 5\ndici(xes)')
        assert output.strip() == "false"
    
    def test_less_equal_true(self):
        output = compile_and_run('xam := 3 <= 3\ndici(xes)')
        assert output.strip() == "true"
    
    def test_less_equal_false(self):
        output = compile_and_run('xam := 4 <= 3\ndici(xes)')
        assert output.strip() == "false"
    
    def test_greater_equal_true(self):
        output = compile_and_run('xam := 5 >= 5\ndici(xes)')
        assert output.strip() == "true"
    
    def test_greater_equal_false(self):
        output = compile_and_run('xam := 4 >= 5\ndici(xes)')
        assert output.strip() == "false"
    
    def test_equality_int(self):
        output = compile_and_run('xam := 5 == 5\ndici(xes)')
        assert output.strip() == "true"
    
    def test_inequality_int(self):
        output = compile_and_run('xam := 5 != 3\ndici(xes)')
        assert output.strip() == "true"


# =============================================================================
# BOOLEAN OPERATIONS
# =============================================================================

class TestBooleanOps:
    """Test boolean operations."""
    
    def test_and_true(self):
        output = compile_and_run('xam := verum et verum\ndici(xes)')
        assert output.strip() == "true"
    
    def test_and_false(self):
        output = compile_and_run('xam := verum et falsus\ndici(xes)')
        assert output.strip() == "false"
    
    def test_or_true(self):
        output = compile_and_run('xam := falsus vel verum\ndici(xes)')
        assert output.strip() == "true"
    
    def test_or_false(self):
        output = compile_and_run('xam := falsus vel falsus\ndici(xes)')
        assert output.strip() == "false"
    
    def test_not_true(self):
        output = compile_and_run('xam := non verum\ndici(xes)')
        assert output.strip() == "false"
    
    def test_not_false(self):
        output = compile_and_run('xam := non falsus\ndici(xes)')
        assert output.strip() == "true"
    
    def test_complex_boolean(self):
        output = compile_and_run('xam := (verum et falsus) vel verum\ndici(xes)')
        assert output.strip() == "true"


# =============================================================================
# CONTROL FLOW - IF STATEMENTS
# =============================================================================

class TestIfStatements:
    """Test if/else control flow."""
    
    def test_if_true(self):
        output = compile_and_run('''
si verum {
    dici("yes")
}
''')
        assert output.strip() == "yes"
    
    def test_if_false(self):
        output = compile_and_run('''
si falsus {
    dici("yes")
}
dici("done")
''')
        assert output.strip() == "done"
    
    def test_if_else_true(self):
        output = compile_and_run('''
si verum {
    dici("true branch")
} aluid {
    dici("false branch")
}
''')
        assert output.strip() == "true branch"
    
    def test_if_else_false(self):
        output = compile_and_run('''
si falsus {
    dici("true branch")
} aluid {
    dici("false branch")
}
''')
        assert output.strip() == "false branch"
    
    def test_if_elif(self):
        output = compile_and_run('''
xa := 2
si xa == 1 {
    dici("one")
} aluid xa == 2 {
    dici("two")
} aluid {
    dici("other")
}
''')
        assert output.strip() == "two"
    
    def test_if_with_comparison(self):
        output = compile_and_run('''
xa := 10
si xa > 5 {
    dici("big")
} aluid {
    dici("small")
}
''')
        assert output.strip() == "big"
    
    def test_nested_if(self):
        output = compile_and_run('''
xa := 5
si xa > 0 {
    si xa < 10 {
        dici("between 0 and 10")
    }
}
''')
        assert output.strip() == "between 0 and 10"


# =============================================================================
# CONTROL FLOW - LOOPS
# =============================================================================

class TestLoops:
    """Test loop control flow."""
    
    def test_while_basic(self):
        output = compile_and_run('''
xa := 0
dum xa < 3 {
    dici(xes)
    xa = xa + 1
}
''')
        lines = output.strip().split('\n')
        assert lines == ["0", "1", "2"]
    
    def test_while_countdown(self):
        output = compile_and_run('''
xa := 3
dum xa > 0 {
    dici(xes)
    xa = xa - 1
}
''')
        lines = output.strip().split('\n')
        assert lines == ["3", "2", "1"]
    
    def test_for_range_inclusive(self):
        output = compile_and_run('''
pro ia in 1..3 {
    dici(ies)
}
''')
        lines = output.strip().split('\n')
        assert lines == ["1", "2", "3"]
    
    def test_for_range_exclusive(self):
        output = compile_and_run('''
pro ia in 1.<4 {
    dici(ies)
}
''')
        lines = output.strip().split('\n')
        assert lines == ["1", "2", "3"]
    
    def test_for_list(self):
        output = compile_and_run('''
pro ia in [10, 20, 30] {
    dici(ies)
}
''')
        lines = output.strip().split('\n')
        assert lines == ["10", "20", "30"]


# =============================================================================
# FUNCTIONS
# =============================================================================

class TestFunctions:
    """Test function definitions and calls."""
    
    def test_simple_function(self):
        output = compile_and_run('''
des greetingi() {
    dici("hello")
}
greetingi()
''')
        assert output.strip() == "hello"
    
    def test_function_with_param(self):
        output = compile_and_run('''
des printi(xa) {
    dici(xes)
}
printi(42)
''')
        assert output.strip() == "42"
    
    def test_function_with_return(self):
        output = compile_and_run('''
des doublea(xa) {
    redeo xa * 2
}
ya := doublea(5)
dici(yes)
''')
        assert output.strip() == "10"
    
    def test_function_multiple_params(self):
        output = compile_and_run('''
des adda(xa, ya) {
    redeo xa + ya
}
za := adda(3, 4)
dici(zes)
''')
        assert output.strip() == "7"
    
    def test_recursive_factorial(self):
        output = compile_and_run('''
des facta(na) {
    si na <= 1 {
        redeo 1
    }
    redeo na * facta(na - 1)
}
xa := facta(5)
dici(xes)
''')
        assert output.strip() == "120"
    
    def test_recursive_fibonacci(self):
        output = compile_and_run('''
des fiba(na) {
    si na <= 1 {
        redeo na
    }
    redeo fiba(na - 1) + fiba(na - 2)
}
xa := fiba(10)
dici(xes)
''')
        assert output.strip() == "55"
    
    def test_function_calling_function(self):
        output = compile_and_run('''
des squarea(xa) {
    redeo xa * xa
}
des square_plus_onea(xa) {
    redeo squarea(xa) + 1
}
ya := square_plus_onea(4)
dici(yes)
''')
        assert output.strip() == "17"


# =============================================================================
# LAMBDAS
# =============================================================================

class TestLambdas:
    """Test lambda functions."""
    
    def test_lambda_id_keyword(self):
        output = compile_and_run('''
des makeo() {
    redeo des {
        dici(ides)
    }
}
fo := makeo()
fo("hello from lambda")
''')
        assert output.strip() == "hello from lambda"
    
    def test_lambda_with_param(self):
        output = compile_and_run('''
des makeo() {
    redeo des (xes) {
        dici(xes)
    }
}
fo := makeo()
fo("explicit param")
''')
        assert output.strip() == "explicit param"
    
    def test_lambda_simple_return(self):
        """Test lambda that returns a value."""
        output = compile_and_run('''
des makeo() {
    redeo des {
        redeo ida * 2
    }
}
fo := makeo()
xa := fo(5)
dici(xes)
''')
        assert output.strip() == "10"


# =============================================================================
# LISTS
# =============================================================================

class TestLists:
    """Test list operations."""
    
    def test_empty_list(self):
        output = compile_and_run('''
xuum := []
dici(xes)
''')
        assert "[]" in output.strip() or output.strip() == ""
    
    def test_int_list(self):
        output = compile_and_run('''
xaem := [1, 2, 3]
dici(xes)
''')
        assert "1" in output and "2" in output and "3" in output
    
    def test_bool_list(self):
        output = compile_and_run('''
xas := [verum, falsus, verum]
dici(xes)
''')
        assert "true" in output and "false" in output
    
    def test_string_list(self):
        output = compile_and_run('''
xerum := ["a", "b", "c"]
dici(xes)
''')
        assert "a" in output and "b" in output and "c" in output
    
    def test_list_cast_to_string_list(self):
        output = compile_and_run('''
xaem := [1, 2, 3]
yerum := xerum
dici(yes)
''')
        assert "1" in output and "2" in output and "3" in output


# =============================================================================
# STRUCTS
# =============================================================================

class TestStructs:
    """Test struct/map operations."""
    
    def test_simple_struct(self):
        output = compile_and_run('''
xu := {"namees": "Alice", "agea": 30}
dici(xes)
''')
        assert "Alice" in output or "namees" in output
    
    def test_struct_field_access(self):
        output = compile_and_run('''
personu := {"namees": "Bob", "agea": 25}
dici(personu.namees)
''')
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
        output = compile_and_run('''
xes := "world"
xes.dici()
''')
        assert output.strip() == "world"
    
    def test_cast_method_chain(self):
        output = compile_and_run('''
xa := 123
xes.dici()
''')
        assert output.strip() == "123"


# =============================================================================
# RANGES
# =============================================================================

class TestRanges:
    """Test range operations."""
    
    def test_inclusive_range(self):
        output = compile_and_run('''
pro ia in 1..5 {
    dici(ies)
}
''')
        lines = output.strip().split('\n')
        assert lines == ["1", "2", "3", "4", "5"]
    
    def test_exclusive_range(self):
        output = compile_and_run('''
pro ia in 0.<3 {
    dici(ies)
}
''')
        lines = output.strip().split('\n')
        assert lines == ["0", "1", "2"]


# =============================================================================
# REASSIGNMENT
# =============================================================================

class TestReassignment:
    """Test variable reassignment."""
    
    def test_simple_reassignment(self):
        output = compile_and_run('''
xa := 1
xa = 2
dici(xes)
''')
        assert output.strip() == "2"
    
    def test_reassignment_with_expression(self):
        output = compile_and_run('''
xa := 5
xa = xa + 10
dici(xes)
''')
        assert output.strip() == "15"
    
    def test_reassignment_in_loop(self):
        output = compile_and_run('''
suma := 0
pro ia in 1..5 {
    suma = suma + ia
}
dici(sumes)
''')
        assert output.strip() == "15"


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and special scenarios."""
    
    def test_zero(self):
        output = compile_and_run('xa := 0\ndici(xes)')
        assert output.strip() == "0"
    
    def test_large_number(self):
        output = compile_and_run('xa := 1000000\ndici(xes)')
        assert output.strip() == "1000000"
    
    def test_empty_string(self):
        output = compile_and_run('dici("")')
        assert output.strip() == ""
    
    def test_multiple_statements(self):
        output = compile_and_run('''
dici("one")
dici("two")
dici("three")
''')
        lines = output.strip().split('\n')
        assert lines == ["one", "two", "three"]
    
    def test_nested_parentheses(self):
        output = compile_and_run('xa := ((1 + 2) * (3 + 4))\ndici(xes)')
        assert output.strip() == "21"
    
    def test_chained_comparisons_in_if(self):
        output = compile_and_run('''
xa := 5
si xa > 0 et xa < 10 {
    dici("in range")
}
''')
        assert output.strip() == "in range"
    
    def test_function_param_reassignment(self):
        output = compile_and_run('''
des modifya(xa) {
    xa = xa * 2
    redeo xa
}
ya := modifya(5)
dici(yes)
''')
        assert output.strip() == "10"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple features."""
    
    def test_fizzbuzz_simple(self):
        output = compile_and_run('''
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
''')
        lines = output.strip().split('\n')
        assert lines[0] == "1"
        assert lines[2] == "Fizz"
        assert lines[4] == "Buzz"
        assert lines[14] == "FizzBuzz"
    
    def test_sum_of_squares(self):
        output = compile_and_run('''
des squarea(xa) {
    redeo xa * xa
}
suma := 0
pro ia in 1..5 {
    suma = suma + squarea(ia)
}
dici(sumes)
''')
        # 1 + 4 + 9 + 16 + 25 = 55
        assert output.strip() == "55"
    
    def test_countdown_with_function(self):
        output = compile_and_run('''
des countdowni(na) {
    dum na > 0 {
        dici(nes)
        na = na - 1
    }
    dici("Blast off!")
}
countdowni(3)
''')
        lines = output.strip().split('\n')
        assert lines == ["3", "2", "1", "Blast off!"]
    
    def test_power_function(self):
        output = compile_and_run('''
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
''')
        assert output.strip() == "256"
    
    def test_gcd(self):
        output = compile_and_run('''
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
''')
        assert output.strip() == "6"
    
    def test_is_prime(self):
        output = compile_and_run('''
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
''')
        lines = output.strip().split('\n')
        assert lines == ["true", "false", "true"]
    
    def test_list_iteration_sum(self):
        output = compile_and_run('''
numbersaem := [10, 20, 30, 40]
suma := 0
pro na in numbersaem {
    suma = suma + na
}
dici(sumes)
''')
        assert output.strip() == "100"
    
    def test_nested_loops(self):
        output = compile_and_run('''
pro ia in 1..3 {
    pro ja in 1..3 {
        xa := ia * ja
        dici(xes)
    }
}
''')
        lines = output.strip().split('\n')
        expected = ["1", "2", "3", "2", "4", "6", "3", "6", "9"]
        assert lines == expected
    
    def test_accumulator_pattern(self):
        output = compile_and_run('''
producta := 1
pro ia in 1..5 {
    producta = producta * ia
}
dici(productes)
''')
        # 5! = 120
        assert output.strip() == "120"
