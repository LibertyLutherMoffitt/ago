# test/test_semantics.py

import pytest

from src.GeminiAgoSemanticChecker import AgoSemanticChecker
from src.AgoParser import parser  # make sure this exposes `parser`


def run_semantics(source: str):
    """
    Helper: parse `source` with AgoSemantics and return the list of errors.
    Assumes `source` is syntactically valid according to the grammar.
    """
    semantics = AgoSemanticChecker()
    parser.parse(source, semantics=semantics)
    return semantics.errors


# ---------- BASIC VARIABLE SEMANTICS ----------


def test_declaration_then_assignment_has_no_errors():
    src = """\
x := 1
x = 2
"""
    errors = run_semantics(src)
    assert errors == []


def test_undeclared_variable_in_assignment_reports_error():
    src = """\
x = 1
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "Use of undeclared identifier 'x'" in str(errors[0])


def test_duplicate_declaration_reports_error():
    src = """\
x := 1
x := 2
"""
    errors = run_semantics(src)
    # One semantic error from SymbolTable duplicate
    assert len(errors) == 1
    assert "Variable name already exists in this scope" in str(errors[0])


def test_reassignment_with_indexing_requires_declaration():
    src = """\
arr[0] = 1
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "Use of undeclared identifier 'arr'" in str(errors[0])


# ---------- FUNCTION / RETURN SEMANTICS ----------


def test_return_outside_function_reports_error():
    src = """\
redeo verum
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "'redeo' (return) outside of function" in str(errors[0])


def test_return_inside_function_is_allowed():
    src = """\
des foo(x) {
    redeo x
}
"""
    errors = run_semantics(src)
    # No semantic errors from just having a return inside a function
    assert errors == []


def test_call_to_undeclared_function_reports_error():
    src = """\
foo(1, 2)
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "Use of undeclared identifier 'foo'" in str(errors[0])


def test_call_to_declared_function_has_no_errors():
    src = """\
des foo(x) {
    redeo x
}

foo(1)
"""
    errors = run_semantics(src)
    assert errors == []


# ---------- LOOP / BREAK / CONTINUE SEMANTICS ----------


def test_break_outside_loop_reports_error():
    src = """\
frio
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "'frio' (break) outside of loop" in str(errors[0])


def test_continue_outside_loop_reports_error():
    src = """\
pergo
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "'pergo' (continue) outside of loop" in str(errors[0])


def test_break_inside_while_loop_is_allowed():
    src = """\
x := 0
dum x < 10 {
    frio
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_continue_inside_for_loop_is_allowed():
    src = """\
x := 0
pro i in [1, 2, 3] {
    pergo
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_nested_loops_allow_break_and_continue():
    src = """\
x := 0
dum x < 10 {
    pro i in [1, 2, 3] {
        pergo
    }
    frio
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_break_in_function_but_outside_loop_is_error():
    src = """\
des foo() {
    frio
}
"""
    errors = run_semantics(src)
    # break is still outside any loop, even though it's inside a function
    assert len(errors) == 1
    assert "'frio' (break) outside of loop" in str(errors[0])


# ---------- IF / CONTROL-FLOW CONTEXT (NO EXTRA ERRORS) ----------


def test_if_statement_with_decl_and_use_is_ok():
    src = """\
x := 0
si x < 10 {
    x = x + 1
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_if_else_with_return_inside_function_is_ok():
    src = """\
des sign(x) {
    si x < 0 {
        redeo -1
    }
    aluid x == 0 {
        redeo 0
    }
    aluid {
        redeo 1
    }
}
"""
    errors = run_semantics(src)
    assert errors == []


# ---------- MULTIPLE ERRORS IN ONE PROGRAM ----------


def test_multiple_semantic_errors_are_all_collected():
    src = """\
x = 1          # undeclared
frio           # break outside loop
redeo verum    # return outside function
"""
    errors = run_semantics(src)

    # We expect 3 independent errors
    messages = [str(e) for e in errors]
    assert len(errors) == 3
    assert any("Use of undeclared identifier 'x'" in m for m in messages)
    assert any("'frio' outside of loop" in m for m in messages)
    assert any("'redeo' outside of function" in m for m in messages)
