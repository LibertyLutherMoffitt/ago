import pytest

from src.AgoParser import parser
from src.AgoSemanticChecker import AgoSemantics

# ---------- helpers ----------


def infer_type(expr_src: str, semantics=None):
    """
    Parse a single expression and ask the semantic checker for its type.
    """
    semantics = AgoSemantics() if not semantics else semantics
    ast = parser.parse(expr_src + "\n", rule_name="expression", semantics=semantics)
    t = semantics.infer_expr_type(ast)
    return t, semantics


def run_program(src: str):
    """
    Parse a full program (principio rule) and return the semantics object
    so we can inspect symbols, function types, and errors.
    """
    semantics = AgoSemantics()
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
x := 1
x := 2
x
"""
    # Parse the whole program first to set up the symbol table
    semantics = run_program(src)
    # Look up variable type
    sym = semantics.symtab.get_symbol("x")
    assert sym is not None
    assert sym.type_t == "int"

    # Now parse just "x" as an expression and infer its type
    t, _ = infer_type("x", semantics)
    assert t == "int"


def test_identifier_unknown_if_never_declared_but_no_crash():
    t, sem = infer_type("y")
    # Should report undeclared identifier, but still return a type

    assert any("undeclared identifier 'y'" in str(e).lower() for e in sem.errors)


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
    _, sem = infer_type('"hello" + 1')
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
