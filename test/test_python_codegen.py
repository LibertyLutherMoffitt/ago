"""
Tests for the Python code generator.
"""

import ast
import pytest
from src.AgoParser import AgoParser
from src.AgoPythonCodeGenerator import generate_python_ast

def transpile_ago_to_python(ago_code: str) -> str:
    """Helper function to transpile Ago code to a Python code string."""
    parser = AgoParser()
    ago_ast = parser.parse(ago_code)
    py_ast = generate_python_ast(ago_ast)
    return ast.unparse(py_ast)

def test_variable_declaration_and_expressions():
    ago_code = """
    xa := 10
    ya := xa + 5
    """
    expected_python = """
x = 10
y = x + 5
"""
    generated_python = transpile_ago_to_python(ago_code)
    assert generated_python.strip() == expected_python.strip()

def test_if_statement():
    ago_code = """
    si verum {
        xa := 1
    } aluid falsus {
        xa := 2
    } aluid {
        xa := 3
    }
    """
    expected_python = """
if True:
    x = 1
elif False:
    x = 2
else:
    x = 3
"""
    generated_python = transpile_ago_to_python(ago_code)
    assert generated_python.strip() == expected_python.strip()

def test_while_loop():
    ago_code = """
    dum verum {
        frio
    }
    """
    expected_python = """
while True:
    break
"""
    generated_python = transpile_ago_to_python(ago_code)
    assert generated_python.strip() == expected_python.strip()

def test_for_loop_with_range():
    ago_code = """
    pro ia in 1..10 {
        omitto
    }
    """
    expected_python = """
for i in range(1, 10 + 1):
    pass
"""
    generated_python = transpile_ago_to_python(ago_code)
    assert generated_python.strip() == expected_python.strip()

def test_function_declaration_and_call():
    ago_code = """
    des testao(param_a) {
        redeo param_a
    }
    testao(42)
    """
    expected_python = """
def testa(param):
    return param
testa(42)
"""
    generated_python = transpile_ago_to_python(ago_code)
    assert generated_python.strip() == expected_python.strip()

def test_method_call():
    ago_code = """
    "hello".dici()
    """
    expected_python = "dici('hello')"
    generated_python = transpile_ago_to_python(ago_code)
    assert generated_python.strip() == expected_python.strip()

def test_list_and_slicing():
    ago_code = """
    lista := [1, 2, 3, 4]
    sublista := lista[1..3]
    """
    expected_python = """
lista = [1, 2, 3, 4]
sublista = lista[1:3 + 1]
"""
    generated_python = transpile_ago_to_python(ago_code)
    assert generated_python.strip() == expected_python.strip()

def test_exclusive_slicing():
    ago_code = """
    lista := [1, 2, 3, 4]
    sublista := lista[1.<3]
    """
    expected_python = """
lista = [1, 2, 3, 4]
sublista = lista[1:3]
"""
    generated_python = transpile_ago_to_python(ago_code)
    assert generated_python.strip() == expected_python.strip()

def test_lambda_assignment():
    ago_code = """
    addo := des(xa, ya) { redeo xa + ya }
    """
    expected_python = "add = lambda xa, ya: xa + ya"
    generated_python = transpile_ago_to_python(ago_code)
    assert generated_python.strip() == expected_python.strip()

def test_implicit_id_lambda():
    ago_code = """
    incro := des { redeo id + 1 }
    """
    expected_python = "incr = lambda id: id + 1"
    generated_python = transpile_ago_to_python(ago_code)
    assert generated_python.strip() == expected_python.strip()

def test_full_program():
    ago_code = """
    des legies() {
        redeo "hello"
    }
    
    des sates() {
        xa := 10
        pro ia in 0..xa {
            si ia % 2 == 0 {
                legies().dici()
            }
        }
    }

    sates()
    """
    expected_python = """
def legie():
    return 'hello'
def sate():
    x = 10
    for i in range(0, x + 1):
        if i % 2 == 0:
            dici(legie())
sate()
"""
    generated_python = transpile_ago_to_python(ago_code)
    assert generated_python.strip() == expected_python.strip()