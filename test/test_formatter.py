"""Tests for the opinionated Ago source formatter (`ago fmt`)."""

from textwrap import dedent

from src.AgoFormatter import format_source


# ---- indentation / structure ----

def test_reindents_to_four_spaces():
    assert format_source("pro ia in 0.<3 {\ndici(ies)\n}\n") == (
        "pro ia in 0.<3 {\n    dici(ies)\n}\n"
    )


def test_nested_blocks():
    src = "si xa {\nsi ya {\ndici(zes)\n}\n}\n"
    assert format_source(src) == (
        "si xa {\n    si ya {\n        dici(zes)\n    }\n}\n"
    )


def test_closing_brace_dedents_its_own_line():
    src = "si xa {\ndici(aes)\n} aluid {\ndici(bes)\n}\n"
    assert format_source(src) == (
        "si xa {\n    dici(aes)\n} aluid {\n    dici(bes)\n}\n"
    )


def test_blank_runs_collapsed_and_single_final_newline():
    assert format_source("xa := 1\n\n\n\nya := 2\n\n\n") == "xa := 1\n\nya := 2\n"


def test_leading_blank_lines_removed():
    assert format_source("\n\nxa := 1\n") == "xa := 1\n"


# ---- canonical spacing (opinionated) ----

def test_operator_spacing():
    assert format_source("xa:=1+2*3\n") == "xa := 1 + 2 * 3\n"


def test_compound_assignment_spacing():
    assert format_source("za+=ia\n") == "za += ia\n"


def test_ternary_spacing():
    assert format_source("ya:=xa>0?xa:-xa\n") == "ya := xa > 0 ? xa : -xa\n"


def test_map_is_unpadded_with_spaced_colons():
    assert format_source('mu:={"a":1,"b":2}\n') == 'mu := {"a": 1, "b": 2}\n'


def test_list_and_negative_literals():
    assert format_source("luum:=[1,-2,3]\n") == "luum := [1, -2, 3]\n"


def test_calls_and_index_are_tight():
    assert format_source("za:=foo(1,2 ,3)[0]\n") == "za := foo(1, 2, 3)[0]\n"


def test_method_chain_tight():
    assert format_source("res:=xs.baruum( ).a()\n") == "res := xs.baruum().a()\n"


def test_ranges_are_tight():
    assert format_source("pro ia in 0 .< 10 {\nomitto\n}\n") == (
        "pro ia in 0.<10 {\n    omitto\n}\n"
    )


def test_word_operators_spaced():
    assert format_source("flagam:=non verum et falsus\n") == (
        "flagam := non verum et falsus\n"
    )


def test_toplevel_semicolons_become_newlines():
    assert format_source("xa:=1; ya:=2; za:=3\n") == "xa := 1\nya := 2\nza := 3\n"


def test_inline_block_semicolons_kept():
    # A `;` inside an inline block stays (the block remains valid on one line).
    assert format_source('si xa {dici(aes);dici(bes)}\n') == (
        'si xa { dici(aes); dici(bes) }\n'
    )


# ---- comments / safety ----

def test_braces_in_strings_do_not_affect_indent():
    assert format_source('xes := "a { b } c"\ndici(xes)\n') == (
        'xes := "a { b } c"\ndici(xes)\n'
    )


def test_comment_preserved_and_indent_unaffected():
    out = format_source("xa := 1  # a brace { here\nya := 2\n")
    assert "# a brace { here" in out
    assert "\nya := 2\n" in out  # not indented by the comment's brace


def test_doc_comment_stays_attached_to_def():
    src = "# doc\ndes fooi(yes) {\nredeo inanis\n}\n"
    out = format_source(src)
    assert out.startswith("# doc\ndes fooi(yes) {")


def test_blank_line_inserted_after_toplevel_block():
    src = "des ai() {\nredeo 1\n}\ndes bi() {\nredeo 2\n}\n"
    out = format_source(src)
    assert "}\n\ndes bi()" in out


# ---- robustness ----

def test_idempotent():
    src = dedent(
        """
        xa:=1+2
          pro ia in 0.<3 {
        za:=luum[ia]+mu["k"]
            si za==1 {dici("one")}
           }
        """
    )
    once = format_source(src)
    assert format_source(once) == once


def test_convergent_from_different_spacing():
    v1 = "xa:=1+2*3\nya := xa>0?xa:-xa\n"
    v2 = "xa  :=  1 +2* 3\nya:=xa > 0 ? xa : -xa\n"
    assert format_source(v1) == format_source(v2)


# ---- `ago fmt` CLI: in-place + recursive directory ----

import main as ago_main  # noqa: E402


def test_fmt_formats_file_in_place(tmp_path):
    f = tmp_path / "a.ago"
    f.write_text("xa:=1+2\n")
    rc = ago_main.run_fmt([str(f)])
    assert rc == 0
    assert f.read_text() == "xa := 1 + 2\n"


def test_fmt_recurses_into_directory(tmp_path):
    (tmp_path / "sub").mkdir()
    a = tmp_path / "a.ago"
    b = tmp_path / "sub" / "b.ago"
    a.write_text("xa:=1\n")
    b.write_text("ya:=2*3\n")
    other = tmp_path / "note.txt"
    other.write_text("xa:=1\n")  # not .ago, must be left alone
    rc = ago_main.run_fmt([str(tmp_path)])
    assert rc == 0
    assert a.read_text() == "xa := 1\n"
    assert b.read_text() == "ya := 2 * 3\n"
    assert other.read_text() == "xa:=1\n"


def test_fmt_check_reports_without_writing(tmp_path):
    f = tmp_path / "a.ago"
    f.write_text("xa:=1\n")
    rc = ago_main.run_fmt([str(f), "--check"])
    assert rc == 1
    assert f.read_text() == "xa:=1\n"  # unchanged


def test_fmt_missing_path_errors(tmp_path):
    rc = ago_main.run_fmt([str(tmp_path / "nope.ago")])
    assert rc == 1
