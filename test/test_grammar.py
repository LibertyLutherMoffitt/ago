# test/test_ago_parser.py

from textwrap import dedent

import pytest
from tatsu.exceptions import FailedParse

from src.AgoParser import AgoParser


@pytest.fixture(scope="module")
def parser():
    return AgoParser()


# ---------- PRINCIPIO / TOP LEVEL ----------


def test_simple_program_declaration(parser):
    src = "x := 1\n"
    ast = parser.parse(src)
    assert ast is not None


def test_multiple_sub_principio_with_newlines_and_comments(parser):
    src = dedent("""
        # comment line
        x := 1  # inline comment

        des foo(a, b) {
            omitto
        }

        pro i in [1, 2, 3] {
            pergo
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


# ---------- STATEMENTS ----------


def test_lambda_decl_empty_parens(parser):
    src = "des() { omitto }\n"
    ast = parser.parse(src, rule_name="expression")
    assert ast is not None


def test_method_decl_no_params(parser):
    src = dedent("""
        des foo() {
            omitto
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_declaration_stmt(parser):
    src = "x := 1\n"
    ast = parser.parse(src)
    assert ast is not None


def test_reassignment_stmt_simple(parser):
    src = dedent("""
        x := 0
        x = x + 1
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_reassignment_stmt_with_indexing(parser):
    src = dedent("""
        arr := [1, 2, 3]
        arr[1] = 10
        arr[1][0] = 20
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_pass_break_continue_and_return(parser):
    src = dedent("""
        omitto
        frio
        pergo
        redeo verum
    """)
    ast = parser.parse(src)
    assert ast is not None


# ---------- METHOD DECL / LAMBDA ----------


def test_method_decl_with_params(parser):
    src = dedent("""
        des sum(a, b) {
            redeo a + b
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_lambda_decl_as_expression(parser):
    src = "des(x, y){ redeo x + y }\n"
    ast = parser.parse(src, rule_name="expression")
    assert ast is not None


def test_lambda_decl_no_params(parser):
    src = "des { omitto }\n"
    ast = parser.parse(src, rule_name="expression")
    assert ast is not None


# ---------- IF / WHILE / FOR ----------


def test_if_stmt_simple(parser):
    src = dedent("""
        si verum {
            omitto
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_if_stmt_with_elif_and_else(parser):
    src = dedent("""
        si x < 0 {
            omitto
        }
        aluid x == 0 {
            pergo
        }
        aluid {
            frio
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_if_with_single_elif_no_else(parser):
    src = dedent("""
        si x < 0 {
            omitto
        }
        aluid x == 0 {
            pergo
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_if_with_multiple_elifs_no_else(parser):
    src = dedent("""
        si x < 0 {
            omitto
        }
        aluid x == 0 {
            pergo
        }
        aluid x > 0 {
            frio
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_while_stmt(parser):
    src = dedent("""
        dum x < 10 {
            x = x + 1
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_for_stmt(parser):
    src = dedent("""
        pro i in [1,2,3] {
            omitto
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


# ---------- CALLS / METHOD CHAINS ----------


def test_simple_function_call_stmt(parser):
    src = "foo(1, 2, 3)\n"
    ast = parser.parse(src)
    assert ast is not None


def test_call_with_receiver_and_chain(parser):
    src = "obj.foo(1).bar(2, 3)\n"
    ast = parser.parse(src)
    assert ast is not None


def test_nested_call_in_expression(parser):
    src = "foo(bar(1), baz(2))\n"
    ast = parser.parse(src, rule_name="expression")
    assert ast is not None


def test_call_stmt_no_args(parser):
    src = "foo()\n"
    ast = parser.parse(src)
    assert ast is not None


def test_call_stmt_receiver_no_chain(parser):
    src = "obj.foo()\n"
    ast = parser.parse(src)
    assert ast is not None


# ---------- BLOCK / STATEMENT LIST ----------


def test_empty_block_no_newlines(parser):
    src = "{}"
    ast = parser.parse(src, rule_name="block")
    assert ast is not None


def test_block_only_newlines(parser):
    src = "{\n\n}"
    ast = parser.parse(src, rule_name="block")
    assert ast is not None


def test_block_with_multiple_statements_and_newlines(parser):
    src = dedent("""{
            x := 1

            y := 2


            x = x + y
                 }""")
    ast = parser.parse(src, rule_name="block")
    assert ast is not None


# ---------- EXPRESSION PRECEDENCE LEVELS ----------


@pytest.mark.parametrize(
    "expr",
    [
        # pa: OR/BOR/BXOR/ELVIS
        "a vel b",
        "a | b",
        "a ^ b",
        "a ?: b",
        # pb: AND/BAND
        "a et b",
        "a & b",
        # pc: comparisons
        "a == b",
        "a > b",
        "a >= b",
        "a < b",
        "a <= b",
        # pd: slices
        "a .. b",
        "a .< b",
        # pe: addition/subtraction
        "a + b",
        "a - b",
        # pf: mult/div/mod
        "a * b",
        "a / b",
        "a % b",
        # pg: unary
        "-a",
        "+a",
        "non verum",
        # combos for precedence sanity
        "a + b * c",
        "a et b vel c",
        "a .. b + c",
    ],
)
def test_expression_variants(parser, expr):
    ast = parser.parse(expr + "\n", rule_name="expression")
    assert ast is not None


def test_list_as_expression(parser):
    src = "[1, 2, 3]\n"
    ast = parser.parse(src, rule_name="expression")
    assert ast is not None


def test_mapstruct_as_expression(parser):
    src = "{foo: 1, bar: 2}\n"
    ast = parser.parse(src, rule_name="expression")
    assert ast is not None


def test_expression_list_multiple(parser):
    src = "a, b + 1, [1,2], {k: v}\n"
    ast = parser.parse(src, rule_name="expression_list")
    assert ast is not None


# ---------- LISTS, MAPS, ITEMS ----------


def test_list_literal_empty(parser):
    src = "[]\n"
    ast = parser.parse(src, rule_name="list")
    assert ast is not None


def test_list_literal_non_empty(parser):
    src = "[1, 2, 3]\n"
    ast = parser.parse(src, rule_name="list")
    assert ast is not None


def test_mapstruct_with_string_keys(parser):
    src = '{"a": 1, "b": 2}\n'
    ast = parser.parse(src, rule_name="mapstruct")
    assert ast is not None


def test_mapstruct_with_identifier_keys_and_trailing(parser):
    src = "{foo: 1, bar: baz(2)}\n"
    ast = parser.parse(src, rule_name="mapstruct")
    assert ast is not None


def test_item_variants_literals_and_specials(parser):
    exprs = [
        '"hello"',  # STR_LIT
        "3.14",  # FLOATLIT
        "42",  # INTLIT
        "verum",  # TRUE
        "falsus",  # FALSE
        "inanis",  # NULL
        "id",  # IT
        "XII",  # ROMAN_NUMERAL
        "foo",  # identifier
    ]
    for e in exprs:
        ast = parser.parse(e + "\n", rule_name="item")
        assert ast is not None


def test_item_paren_expression(parser):
    src = "(1 + 2 * 3)\n"
    ast = parser.parse(src, rule_name="item")
    assert ast is not None


def test_item_indexed_identifier(parser):
    src = "arr[0][1]\n"
    ast = parser.parse(src, rule_name="item")
    assert ast is not None


def test_item_method_chain(parser):
    src = "arr[0].foo(1).bar(2)\n"
    ast = parser.parse(src, rule_name="item")
    assert ast is not None


def test_item_lambda(parser):
    src = "des(x){ redeo x * x }\n"
    ast = parser.parse(src, rule_name="item")
    assert ast is not None


# ---------- INDEXING ----------


def test_indexing_multiple(parser):
    src = "[0][1][2]\n"
    ast = parser.parse(src, rule_name="indexing")
    assert ast is not None


# ---------- NEGATIVE / ERROR TEST ----------


def test_invalid_syntax_raises(parser):
    src = "si { omitto }\n"  # missing condition expression
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_reserved_keyword_cannot_be_identifier(parser):
    # 'si' is IF keyword, not identifier
    src = "si := 1\n"
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_empty_program_is_invalid(parser):
    src = ""
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_unterminated_block_is_invalid(parser):
    src = "x := 1\n{"  # missing closing }
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_unterminated_paren_in_expression_is_invalid(parser):
    src = "foo(1, 2\n"
    with pytest.raises(FailedParse):
        parser.parse(src)


@pytest.mark.parametrize("kw", ["si", "dum", "pro", "verum", "falsus", "inanis", "des"])
def test_reserved_keywords_cannot_be_identifiers(parser, kw):
    src = f"{kw} := 1\n"
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_if_missing_block_is_invalid(parser):
    src = "si x < 0\n"
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_if_missing_condition_is_invalid(parser):
    src = "si { omitto }\n"
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_while_missing_condition_is_invalid(parser):
    src = "dum { omitto }\n"
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_while_missing_block_is_invalid(parser):
    src = "dum x < 10\n"
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_for_missing_in_keyword_is_invalid(parser):
    src = "pro i [1, 2, 3] { omitto }\n"
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_for_missing_iterable_is_invalid(parser):
    src = "pro i in { omitto }\n"
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_method_decl_missing_parens_is_invalid(parser):
    src = "des foo { omitto }\n"
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_lambda_decl_at_toplevel_is_invalid(parser):
    # lambda_decl is only valid as an item/expression, not as sub_principio
    src = "des(x){ redeo x }\n"
    with pytest.raises(FailedParse):
        parser.parse(src)  # using principio rule


def test_call_missing_closing_paren_is_invalid(parser):
    src = "foo(1, 2\n"
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_call_with_trailing_comma_is_invalid(parser):
    src = "foo(1, 2, )\n"
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_unterminated_string_literal_is_invalid(parser):
    src = '"hello\n'
    with pytest.raises(FailedParse):
        parser.parse(src, rule_name="expression")


def test_string_with_invalid_escape_is_invalid(parser):
    # '\x' is not allowed by your STR_LIT rule
    src = r'"\x"' + "\n"
    with pytest.raises(FailedParse):
        parser.parse(src, rule_name="expression")


# ---------- STRUCT TESTS ----------


def test_struct_declaration(parser):
    src = dedent("""
        personu := {
            "names": "Tom",
            "agea": 30,
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_struct_access(parser):
    src = dedent("""
        personu := {"names": "Alice", "agea": 25}
        names := person.names
        agea := person.agea
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_struct_missing_comma_is_invalid(parser):
    src = dedent("""
        personu := {
            "names": "Tom"
            "agea": 30,
        }
    """)
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_struct_missing_colon_is_invalid(parser):
    src = dedent("""
        personu := {
            "names" "Tom",
            "agea": 30,
        }
    """)
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_struct_access_with_space(parser):
    src = dedent("""
        personu := {"first names": "Alice", "agea": 25}
        names := personu."first names" 
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_struct_declaration_empty(parser):
    src = dedent("""
        emptyStructu := {
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_struct_with_nested_struct(parser):
    src = dedent("""
        addressu := {
            "streetes": "123 Main St",
            "cityes": "Anytown",
            "owneru": {
                "names": "Bob",
                "agea": 40,
            },
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_struct_access_nested(parser):
    src = dedent("""
        addressu := {
            "streetes": "123 Main St",
            "cityes": "Anytown",
            "owneru": {
                "names": "Bob",
                "agea": 40,
            },
        }
        ownerNames := addressu.owneru.names
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_struct_with_non_string_key_is_invalid(parser):
    src = dedent("""
        invalidStructu := {
            123: "Invalid Key",
            "agea": 30,
        }
    """)
    with pytest.raises(FailedParse):
        parser.parse(src)


def test_struct_nested_with_space(parser):
    src = dedent("""
        complexStructu := {
            "level one": {
                "level two": {
                    "level three": "Deep Value"
                }
            }
        }
    """)
    ast = parser.parse(src)
    assert ast is not None


def test_struct_access_nested_with_space(parser):
    src = dedent("""
        complexStructu := {
            "level one": {
                "level two": {
                    "level three": "Deep Value"
                }
            }
        }
        deepValues := complexStructu."level one"."level two"."level three"
    """)
    ast = parser.parse(src)
    assert ast is not None
