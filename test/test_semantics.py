# test/test_semantics.py
import pytest
from src.AgoParser import parser
from src.AgoSemanticChecker import AgoSemanticChecker


def run_semantics(source: str):
    """
    Helper: parse `source` with AgoSemanticChecker and return the list of errors.
    Assumes `source` is syntactically valid according to the grammar.
    """
    semantics = AgoSemanticChecker()
    parser.parse(source, semantics=semantics)
    return semantics.errors


# ---------- BASIC VARIABLE SEMANTICS ----------


def test_declaration_then_assignment_has_no_errors():
    src = """\
xa := 1
xa = 2
"""
    errors = run_semantics(src)
    assert errors == []


def test_undeclared_variable_in_assignment_reports_error():
    src = """\
xa = 1
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "Use of undeclared identifier 'xa'" in str(errors[0])


def test_duplicate_declaration_reports_error():
    src = """\
xa := 1
xa := 2
"""
    errors = run_semantics(src)
    # One semantic error from SymbolTable duplicate
    assert len(errors) == 1
    assert "Variable name already exists in this scope" in str(errors[0])


def test_reassignment_with_indexing_requires_declaration():
    src = """\
arraem[0] = 1
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "Use of undeclared identifier 'arraem'" in str(errors[0])


def test_reassignment_to_undeclared_variable_reports_error():
    src = """
non_existent_vara = 1
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "Use of undeclared identifier 'non_existent_vara'" in str(errors[0])


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
des fooa(xa) {
    redeo xa
}
"""
    errors = run_semantics(src)
    # No semantic errors from just having a return inside a function
    assert errors == []


def test_call_to_undeclared_function_reports_error():
    src = """\
fooa(1, 2)
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "Use of undeclared identifier 'fooa'" in str(errors[0])


def test_call_to_declared_function_has_no_errors():
    src = """\
des fooa(xa) {
    redeo xa
}

fooa(1)
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
xa := 0
dum xa < 10 {
    frio
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_continue_inside_for_loop_is_allowed():
    src = """\
xa := 0
pro ia in [1, 2, 3] {
    pergo
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_nested_loops_allow_break_and_continue():
    src = """\
xa := 0
dum xa < 10 {
    pro ia in [1, 2, 3] {
        pergo
    }
    frio
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_break_in_function_but_outside_loop_is_error():
    src = """\
des fooa() {
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
xa := 0
si xa < 10 {
    xa = xa + 1
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_if_else_with_return_inside_function_is_ok():
    src = """\
des signa(xa) {
    si xa < 0 {
        redeo -1
    }
    aluid xa == 0 {
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
xa = 1
frio
redeo verum
"""
    errors = run_semantics(src)

    # We expect 3 independent errors
    messages = [str(e) for e in errors]
    assert len(errors) == 3
    assert any("Use of undeclared identifier 'xa'" in m for m in messages)
    assert any("'frio'" in m and "outside of loop" in m for m in messages)
    assert any("'redeo'" in m and "outside of function" in m for m in messages)


@pytest.mark.parametrize(
    "filename",
    [
        "./test/resources/temptare_lambda.ago",
        "./test/resources/temptare_lego.ago",
        "./test/resources/temptare_loop.ago",
        "./test/resources/temptare_var.ago",
        "./test/resources/temptare.ago",
    ],
)
def test_semantic_checker(filename):
    """Test AgoSemanticChecker on individual files."""
    with open(filename, "r") as f:
        semantics = AgoSemanticChecker()
        parser.parse(f.read() + "\n", semantics=semantics)
        assert len(semantics.errors) == 0, f"Semantic errors found: {semantics.errors}"


# ---------- RANGE SEMANTICS ----------


def test_range_operator_type_inference():
    src = "rangee := 1 .. 5"
    errors = run_semantics(src)
    assert errors == []


def test_range_operator_requires_int_operands():
    src = "rangee := 1.0 .. 5"
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "must be int" in str(errors[0])


def test_for_loop_over_range_is_allowed():
    src = """
rangee := 1 .. 5
pro itema in rangee {
    omitto
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_for_loop_over_range_iterator_type_mismatch():
    src = """
rangee := 1 .. 5
pro item_es in rangee { # 'es' is string, but range yields int
    omitto
}
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "Type mismatch" in str(errors[0])
    assert "expected 'string', got 'int'" in str(errors[0])


# ---------- LAMBDA VARIABLE SEMANTICS ----------


def test_lambda_variable_with_o_ending():
    """Variables storing lambdas should have -o ending."""
    src = """
addo := des (xa) {
    redeo xa + 1
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_lambda_variable_wrong_ending_reports_error():
    """Lambda assigned to non-o ending variable should error."""
    src = """
adda := des (xa) {
    redeo xa + 1
}
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "Type mismatch" in str(errors[0])


def test_lambda_can_be_called():
    """Lambda stored in variable can be called."""
    src = """
addo := des (xa) {
    redeo xa + 1
}
addo(5)
"""
    errors = run_semantics(src)
    assert errors == []


def test_lambda_call_wrong_arg_count():
    """Lambda called with wrong number of args should error."""
    src = """
addo := des (xa) {
    redeo xa + 1
}
addo(1, 2)
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "expects 1 argument" in str(errors[0])


def test_lambda_call_wrong_arg_type():
    """Lambda called with wrong arg type should error."""
    src = """
addo := des (listaem) {
    redeo listaem[0]
}
addo({keya: 1})
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "Argument 1" in str(errors[0])


def test_calling_non_callable_reports_error():
    """Calling a non-function variable should error."""
    src = """
xa := 5
xa()
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "not callable" in str(errors[0])


# ---------- ID KEYWORD SEMANTICS ----------


def test_id_keyword_outside_lambda_reports_error():
    """Using 'id' outside a lambda should error."""
    src = """
xa := id
"""
    errors = run_semantics(src)
    assert len(errors) >= 1
    assert any("id" in str(e) and "lambda" in str(e) for e in errors)


def test_id_keyword_in_multi_param_lambda_reports_error():
    """Using 'id' in lambda with multiple params should error."""
    src = """
addo := des (xa, ya) {
    redeo id + 1
}
"""
    errors = run_semantics(src)
    assert len(errors) >= 1
    assert any("exactly 1 parameter" in str(e) for e in errors)


def test_id_keyword_in_single_param_lambda_is_ok():
    """Using 'id' in single-param lambda should work."""
    src = """
addo := des (xa) {
    redeo ida + 1
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_id_cast_variant_in_lambda():
    """Using ida, ides etc. in single-param lambda for casting."""
    src = """
stringifyo := des (xa) {
    redeo ides
}
"""
    errors = run_semantics(src)
    assert errors == []


# ---------- STRUCT KEY NAMING SEMANTICS ----------


def test_struct_key_valid_type_suffix():
    """Struct keys with proper type suffix should work."""
    src = """
personu := {
    namees: "John",
    agea: 30
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_struct_key_type_mismatch():
    """Struct key type suffix should match value type (struct vs int_list)."""
    src = """
personu := {
    listaem: {inner: 1}
}
"""
    errors = run_semantics(src)
    assert len(errors) >= 1
    assert any("listaem" in str(e) for e in errors)


def test_struct_string_literal_key_no_validation():
    """String literal keys don't need type suffix validation."""
    src = """
datau := {
    "anything": 123
}
"""
    errors = run_semantics(src)
    assert errors == []


# ---------- STRUCT INDEXED TYPE INFERENCE ----------


def test_struct_field_access_type_from_name():
    """Accessing struct field infers type from field name suffix."""
    src = """
personu := {namees: "John", agea: 30}
namees := personu.namees
agea := personu.agea
"""
    errors = run_semantics(src)
    assert errors == []


# ---------- METHOD CHAIN SEMANTICS ----------


def test_method_chain_type_inference():
    """Method chain should infer return type from last function."""
    src = """
des processes(xes) {
    redeo xes
}
des convertes(xes) {
    redeo xes
}
resultes := "hello".processes().convertes()
"""
    errors = run_semantics(src)
    assert errors == []


def test_method_chain_validates_receiver_type():
    """Method chain should validate receiver type matches first param."""
    src = """
des processa(listaem) {
    redeo listaem[0]
}
resulta := {keya: 1}.processa()
"""
    errors = run_semantics(src)
    assert len(errors) >= 1
    assert any("expects first argument" in str(e) or "type" in str(e) for e in errors)


def test_method_chain_validates_arg_count():
    """Method chain should validate argument count (including receiver)."""
    src = """
des processa(xa, ya, za) {
    redeo xa + ya + za
}
resulta := 1.processa(2)
"""
    errors = run_semantics(src)
    assert len(errors) >= 1
    assert any("expects 3 argument" in str(e) for e in errors)


# ---------- FUNCTION PARAM CHECKING ----------


def test_function_call_wrong_arg_count():
    """Function called with wrong arg count should error."""
    src = """
des adda(xa, ya) {
    redeo xa + ya
}
adda(1)
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "expects 2 argument" in str(errors[0])


def test_function_call_wrong_arg_type():
    """Function called with wrong arg type should error (struct vs int_list)."""
    src = """
des processo(listaem) {
    xa := listaem[0]
}
processo({keya: 1})
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "Argument 1" in str(errors[0])


def test_function_return_type_mismatch():
    """Return type should match function's expected return type (struct vs int)."""
    src = """
des geta() {
    redeo {keya: 1}
}
"""
    errors = run_semantics(src)
    assert len(errors) == 1
    assert "Return type mismatch" in str(errors[0])


def test_function_return_type_compatible():
    """Compatible return types should not error (int -> float)."""
    src = """
des getae() {
    redeo 5
}
"""
    errors = run_semantics(src)
    assert errors == []


# ---------- FUNCTION ENDING -O SEMANTICS ----------


def test_function_o_ending_returns_lambda():
    """Function with -o ending returning lambda is valid."""
    src = """
des makeo() {
    redeo des (xa) { redeo xa }
}
"""
    errors = run_semantics(src)
    assert errors == []


def test_function_o_ending_void_return():
    """Function with -o ending with no return is valid (void)."""
    src = """
des printo() {
    xa := 5
}
"""
    errors = run_semantics(src)
    assert errors == []
