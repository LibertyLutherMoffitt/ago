import pytest

from src.AgoParser import parser
from src.AgoSemanticChecker import AgoSemanticChecker

# ---------- helpers ----------


def infer_type(expr_src: str, semantics=None):
    """
    Parse a single expression and ask the semantic checker for its type.
    """
    semantics = AgoSemanticChecker() if not semantics else semantics
    ast = parser.parse(expr_src + "\n", rule_name="expression", semantics=semantics)
    t = semantics.infer_expr_type(ast)
    return t, semantics


def run_program(src: str):
    """
    Parse a full program (principio rule) and return the semantics object
    so we can inspect symbols, function types, and errors.
    """
    semantics = AgoSemanticChecker()
    parser.parse(src, semantics=semantics)  # uses 'principio' by default
    return semantics


# ---------- literal type inference ----------


@pytest.mark.parametrize(
    "expr, expected_type",
    [
        ("42", "int"),
        ("3.14", "float"),
        ('"hello"', "string"),
        ("verum", "bool"),
        ("falsus", "bool"),
        ("XII", "int"),  # ROMAN_NUMERAL treated as int
    ],
)
def test_literal_types(expr, expected_type):
    t, sem = infer_type(expr)
    assert t == expected_type
    assert sem.errors == []


# ---------- identifiers & declarations ----------


def test_identifier_uses_declared_type_from_assignment():
    src = """\
xa := 1
xa = 2
"""
    # Parse the whole program first to set up the symbol table
    semantics = run_program(src)
    # Look up variable type
    sym = semantics.sym_table.get_symbol("xa")
    assert sym is not None
    assert sym.type_t == "int"

    # Now parse just "xa" as an expression and infer its type
    t, _ = infer_type("xa", semantics)
    assert t == "int"


def test_identifier_unknown_if_never_declared_but_no_crash():
    t, sem = infer_type("ya")
    # Should report undeclared identifier, but still return a type

    assert any("variable 'ya' not defined." in str(e).lower() for e in sem.errors)


# ---------- unary operators ----------


def test_unary_minus_on_int_and_float():
    t_int, sem_int = infer_type("-42")
    t_float, sem_float = infer_type("-3.14")

    assert t_int == "int"
    assert t_float == "float"
    assert sem_int.errors == []
    assert sem_float.errors == []


def test_unary_not_on_bool_only():
    t, sem = infer_type("non verum")
    assert t == "bool"
    assert sem.errors == []

    _, sem_bad = infer_type("non 42")
    assert any("non" in str(e).lower() for e in sem_bad.errors)


# ---------- binary arithmetic operators ----------


def test_addition_int_int_gives_int():
    t, sem = infer_type("1 + 2")
    assert t == "int"
    assert sem.errors == []


def test_addition_float_int_gives_float():
    t, sem = infer_type("3.0 + 2")
    assert t == "float"
    assert sem.errors == []


def test_arithmetic_on_non_numbers_is_error():
    # Use subtraction to avoid string concatenation ambiguity
    _, sem = infer_type('"hello" - 1')
    assert any("is not a numeric type" in str(e).lower() for e in sem.errors)


@pytest.mark.parametrize("expr", ["1 * 2", "4 / 2", "5 % 2"])
def test_multiplicative_ops_on_ints(expr):
    t, sem = infer_type(expr)
    # you can choose to always return 'int' here
    assert t == "int"
    assert sem.errors == []


# ---------- boolean operators ----------


def test_logical_and_or_require_bool():
    t_and, sem_and = infer_type("(verum et falsus)")
    t_or, sem_or = infer_type("(verum vel falsus)")

    assert t_and == "bool"
    assert t_or == "bool"


# ---------- comparison operators ----------


@pytest.mark.parametrize(
    "expr",
    [
        "1 < 2",
        "1 <= 2",
        "1 > 2",
        "1 >= 2",
        "1 == 2",
        "non (1 == 2)",
    ],
)
def test_comparison_operators_return_bool(expr):
    t, sem = infer_type(expr)
    assert t == "bool"
    assert sem.errors == []


def test_comparison_with_mixed_numeric_types():
    # int compared with float should work
    t1, sem1 = infer_type("1 >= 3.14")
    t2, sem2 = infer_type("2.5 >= 2")

    # assert sem1.errors == []
    assert t1 == "bool"

    assert sem2.errors == []
    assert t2 == "bool"


def test_comparison_with_incompatible_types():
    # comparing string with int should error
    _, sem = infer_type('"hello" < 5')
    assert len(sem.errors) > 0


def test_equality_with_same_types():
    t1, sem1 = infer_type('"hello" == "world"')
    t2, sem2 = infer_type("verum == falsus")

    assert t1 == "bool"
    assert t2 == "bool"
    assert sem1.errors == []
    assert sem2.errors == []


# ---------- complex expressions ----------


def test_nested_arithmetic():
    t, sem = infer_type("(1 + 2) * (3 - 4)")
    assert t == "int"
    assert sem.errors == []


def test_mixed_float_int_arithmetic():
    t1, sem1 = infer_type("1.5 + 2")
    t2, sem2 = infer_type("3 * 2.0")
    t3, sem3 = infer_type("(1 + 2.5) / 2")

    assert t1 == "float"
    assert t2 == "float"
    assert t3 == "float"
    assert sem1.errors == []
    assert sem2.errors == []
    assert sem3.errors == []


def test_complex_boolean_expression():
    t, sem = infer_type("(1 < 2) et (3 > 2) vel falsus")
    assert t == "bool"
    assert sem.errors == []


def test_boolean_with_non_boolean_operands():
    _, sem = infer_type("1 et 2")
    assert any(
        "bool" in str(e).lower() or "logical" in str(e).lower() for e in sem.errors
    )


# ---------- type coercion and promotion ----------


def test_int_promotes_to_float_in_division():
    # Depending on language semantics: 5 / 2 might be int division or float
    t, sem = infer_type("5 / 2")
    # Typically should be float or int depending on language design
    assert t in ["int", "float"]


def test_roman_numeral_treated_as_int():
    t1, sem1 = infer_type("XII + 5")
    t2, sem2 = infer_type("X * III")

    assert t1 == "int"
    assert t2 == "int"
    assert sem1.errors == []
    assert sem2.errors == []


# ---------- variable type consistency ----------


def test_variable_type_consistency_across_assignments():
    src = """\
xa := 10
xa = 20
xa = 30
"""
    semantics = run_program(src)
    sym = semantics.sym_table.get_symbol("xa")
    assert sym is not None
    assert sym.type_t == "int"
    assert len(semantics.errors) == 0


def test_variable_used_before_declaration():
    src = """\
ya = xa + 1
xa := 10
"""
    semantics = run_program(src)
    # Should error on xa not being declared
    assert any(
        "not defined" in str(e).lower() or "undeclared" in str(e).lower()
        for e in semantics.errors
    )


# ---------- function calls (if supported) ----------


def test_function_call_with_correct_types():
    src = """\
des vala(aa, ba) {
    redeo aa + ba
}
xa := add(2, 2)
"""
    semantics = run_program(src)
    # Function should be registered
    func_sym = semantics.sym_table.get_symbol("vala")
    assert func_sym is not None
    assert func_sym.return_type == "int"  # return type


# Uncomment if you want to not handle on runtime ig
# def test_function_call_with_wrong_argument_types():
#     src = """\
# des vala(aa, ba) {
#     redeo aa + ba
# }
# xa := vala("hello", 5)
# """
#     semantics = run_program(src)
#     # Should error on argument type mismatch
#     assert semantics.errors != []


def test_function_return_type_mismatch():
    src = """\
des vala() {
    redeo "not an int"
}
"""
    semantics = run_program(src)
    assert semantics.errors != []


# ---------- array/list operations (if supported) ----------


def test_array_element_access():
    src = """\
xa := [1, 2, 3]
ya := xa[0]
"""
    semantics = run_program(src)
    # If arrays are supported, ya should be int
    sym = semantics.sym_table.get_symbol("ya")
    if sym:
        assert sym.type_t == "int"


def test_array_with_mixed_types():
    src = """\
xa := [1, "hello", 3.14]
"""
    run_program(src)
    # Should either error or infer a union type
    # Depending on language design


# ---------- conditional expressions ----------


def test_ternary_operator_type_checking():
    # If your language has ternary: condition ? true_expr : false_expr
    # Test that both branches have compatible types
    # TODO add in ternaries lol
    pass  # Implement based on your language syntax


def test_if_statement_condition_must_be_bool():
    src = """\
si "hello" {
    xa := 1
}
"""
    semantics = run_program(src)
    # Condition should be bool, not int
    assert any(
        "bool" in str(e).lower() or "condition" in str(e).lower()
        for e in semantics.errors
    )


# ---------- loop type checking ----------


def test_while_loop_condition_must_be_bool():
    src = """\
dum "hello" {
    xa := 1
}
"""
    semantics = run_program(src)
    # Loop condition should be bool
    assert len(semantics.errors) > 0


# ---------- unary operators edge cases ----------


def test_double_negation():
    t, sem = infer_type("--42")
    assert t == "int"
    assert sem.errors == []


def test_double_logical_not():
    t, sem = infer_type("non non verum")
    assert t == "bool"
    assert sem.errors == []


def test_invalid_unary_operator_combinations():
    _, sem = infer_type('-"hello"')
    assert len(sem.errors) > 0


# ---------- type inference with parentheses ----------


def test_parenthesized_expressions_preserve_type():
    t1, sem1 = infer_type("(42)")
    t2, sem2 = infer_type("((1 + 2))")
    t3, sem3 = infer_type('("hello")')

    assert t1 == "int"
    assert t2 == "int"
    assert t3 == "string"
    assert sem1.errors == []
    assert sem2.errors == []
    assert sem3.errors == []


# ---------- empty and null values (if supported) ----------


def test_null_or_void_type():
    # If your language has null/void
    # TODO
    pass


# ---------- type checking across scopes ----------


def test_variable_shadowing_in_nested_scopes():
    src = """\
xa := 10

des testa () {

    xa := 42
    redeo xa
}

"""
    semantics = run_program(src)
    assert semantics.errors == []
    # Depending on scoping rules, this might be allowed or not


def test_function_local_variables():
    src = """\
des testa() {
    xa := 5
    redeo xa
}
xa := "global"
"""
    run_program(src)
    # Function local xa should be int, global xa should be string


# ---------- operator precedence type checking ----------


def test_operator_precedence_with_types():
    t, sem = infer_type("1 + 2 * 3")
    assert t == "int"
    assert sem.errors == []


def test_operator_precedence_with_types_electric_boogaloo():
    t, sem = infer_type("1 + 2.2 * 3.3")
    assert t == "float"
    assert sem.errors == []


def test_mixed_operators_precedence():
    t, sem = infer_type("1 < 2 et 3 > 2")
    assert t == "bool"
    assert sem.errors == []


# ---------- division by zero (runtime vs compile-time) ----------


def test_division_by_literal_zero():
    # This is typically a runtime error, but could warn at compile time
    t, sem = infer_type("42 / 0")
    # Should still infer correct type even if it would error at runtime
    assert t in ["int", "float"]


# ---------- modulo operator type checking ----------


def test_modulo_with_floats():
    t, sem = infer_type("5.5 % 2.2")

    assert t == "float"
    assert sem.errors == []


# ---------- string comparison ----------


def test_string_lexicographic_comparison():
    t, sem = infer_type('"abc" < "def"')
    assert t == "bool"
    # Check if errors depending on whether string comparison is supported


# ---------- edge cases ----------


def test_extremely_nested_expression():
    expr = "(" * 5 + "42" + ")" * 5
    t, sem = infer_type(expr)
    assert t == "int"


def test_empty_string():
    t, sem = infer_type('""')
    assert t == "string"
    assert sem.errors == []


def test_multiple_operators_same_precedence():
    t, sem = infer_type("10 - 5 - 2")
    assert t == "int"
    assert sem.errors == []
