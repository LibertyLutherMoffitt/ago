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

@pytest.mark.parametrize("filename", [
    "./test/resources/temptare_lambda.ago",
    "./test/resources/temptare_lego.ago",
    "./test/resources/temptare_loop.ago",
    "./test/resources/temptare_var.ago",
    "./test/resources/temptare.ago"
])
def test_semantic_checker(filename):
    """Test AgoSemanticChecker on individual files."""
    with open(filename, 'r') as f:
        semantics = AgoSemanticChecker()
        parser.parse(f.read() + "\n", semantics=semantics)
        assert len(semantics.errors) == 0, f"Semantic errors found: {semantics.errors}"

    def test_reassignment_to_undeclared(self):
        ast = {"target": "non_existent_vara", "value": {"type": "int"}}
        self.checker.infer_expr_type = lambda x: "int"
        self.checker._handle_reassignment(ast)
        self.assertTrue(self.checker.has_errors())
        self.assertIn("undeclared identifier", self.checker.errors[0].message)

    def test_infer_type_range_operator(self):
        ast = {"op": "..", "left": {}, "right": {}}
        self.checker.infer_expr_type = lambda x: "int"
        op_type = self.checker._infer_binary_op_type(ast)
        self.assertEqual(op_type, "range")
        self.assertFalse(self.checker.has_errors())

    def test_infer_type_range_operator_type_mismatch(self):
        ast = {"op": "..", "left": {}, "right": {}}
        self.checker.infer_expr_type = lambda x: "float"
        self.checker._infer_binary_op_type(ast)
        self.assertTrue(self.checker.has_errors())
        self.assertIn("must be int", self.checker.errors[0].message)

    def test_valid_range_declaration(self):
        # my_rangee := 1..5
        self.checker.infer_expr_type = lambda x: "range"
        ast = make_decl("my_rangee", {"type": "range"})
        self.checker._handle_declaration(ast)
        self.assertFalse(self.checker.has_errors())
        sym = self.checker.sym_table.get_symbol("my_rangee")
        self.assertIsNotNone(sym)
        self.assertEqual(sym.type_t, "range")

    def test_for_loop_over_range(self):
        # for itema in my_rangee { ... }
        self.checker.sym_table.add_symbol(Symbol(name="my_rangee", type_t="range"))
        
        ast = {
            "iterator": {"id": "itema"},
            "iterable": {"id": "my_rangee"},
            "body": {"stmts": None}
        }
        
        # This mock is a bit more specific to handle the different expressions
        def mock_infer(expr):
            if expr.get("id") == "my_rangee":
                return "range"
            if expr.get("id") == "itema":
                return "int" 
            return "unknown"
        self.checker.infer_expr_type = mock_infer

        self.checker._handle_for(ast)
        self.assertFalse(self.checker.has_errors())
