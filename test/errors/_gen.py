#!/usr/bin/env python3
"""Generate the Ago error corpus under test/errors/ and survey current messages.

Each entry is (name, category, source). Categories:
  parse   - syntax errors (lexer/parser)
  sem     - semantic errors
  run     - runtime errors
  ok      - SHOULD compile/run but historically may not (consistency checks)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ERR_DIR = ROOT / "test" / "errors"
MAIN = ROOT / "main.py"

CASES = [
    # ---- missing brackets / parens / braces ----
    ("e01_missing_close_paren", "parse", 'dici("hi"\n'),
    ("e02_missing_open_paren", "parse", 'dici "hi")\n'),
    ("e03_missing_close_brace", "parse", 'si verum {\n    dici("hi")\n'),
    ("e04_missing_close_bracket", "parse", "luum := [1, 2, 3\n"),
    ("e05_missing_open_bracket", "parse", "luum := 1, 2, 3]\n"),
    ("e06_extra_close_brace", "parse", 'dici("hi")\n}\n'),
    ("e07_unclosed_string", "parse", 'dici("hello)\n'),
    ("e08_unclosed_block_func", "parse", "des fooi(xa) {\n    redeo xa\n"),
    # ---- missing separators / operators ----
    ("e09_missing_assign_op", "parse", "xa 5\n"),
    ("e10_missing_comma_list", "parse", "luum := [1 2 3]\n"),
    ("e11_missing_comma_args", "sem", "des adda(xa, ya) {\n    redeo xa + ya\n}\nadda(1 2)\n"),
    ("e12_trailing_operator", "parse", "xa := 1 +\n"),
    ("e13_double_operator", "parse", "xa := 1 ** 2\n"),
    ("e14_stray_comma_list", "parse", "luum := [1, , 2]\n"),
    # ---- control-flow shapes ----
    ("e15_if_missing_cond", "parse", 'si {\n    dici("hi")\n}\n'),
    ("e16_if_missing_block", "parse", 'si verum dici("hi")\n'),
    ("e17_for_missing_in", "parse", "pro ia 0.<3 {\n    dici(ies)\n}\n"),
    ("e18_for_missing_iterable", "parse", "pro ia in {\n    omitto\n}\n"),
    ("e19_while_missing_block", "parse", "dum verum\n"),
    ("e20_ternary_missing_colon", "parse", "xa := verum ? 1\n"),
    # ---- functions ----
    ("e21_func_missing_parens", "parse", "des fooi {\n    redeo 1\n}\n"),
    ("e22_func_missing_body", "parse", "des fooi(xa)\n"),
    ("e23_bad_func_suffix", "sem", "des foozzz() {\n    redeo 1\n}\n"),
    ("e24_func_wrong_arg_count", "sem", "des adda(xa, ya) {\n    redeo xa + ya\n}\nadda(1)\n"),
    ("e25_return_type_mismatch", "sem", 'des fooa() {\n    redeo "hi"\n}\n'),
    # ---- maps ----
    ("e26_map_missing_colon", "parse", 'mu := {"a" 1}\n'),
    ("e27_map_missing_value", "parse", 'mu := {"a": }\n'),
    # ---- names / suffixes / spelling ----
    ("e28_undefined_var", "sem", "dici(xes)\n"),
    ("e29_undefined_func", "sem", "fooi(1)\n"),
    ("e30_bad_var_suffix", "sem", "xzz := 5\n"),
    ("e31_misspelled_keyword", "parse", 'sii verum {\n    dici("hi")\n}\n'),
    ("e32_misspelled_builtin", "sem", 'dicii("hi")\n'),
    ("e33_type_mismatch_decl", "sem", 'xa := "hello"\n'),
    ("e34_reassign_undefined", "sem", "xa = 5\n"),
    # ---- indexing / types ----
    ("e35_index_nonindexable", "sem", "xa := 5\ndici(xa[0].es())\n"),
    ("e36_call_non_function", "sem", "xa := 5\nxa(1)\n"),
    # ---- loop control outside loop ----
    ("e37_break_outside_loop", "sem", "frio\n"),
    ("e38_continue_outside_loop", "sem", "pergo\n"),
    # ---- runtime ----
    ("e39_index_out_of_bounds", "run", "luum := [1, 2]\ndici(luum[5].es())\n"),
    ("e40_divide_by_zero", "run", "xa := 5 / 0\ndici(xes)\n"),
    ("e41_file_not_found", "run", 'fu := apertu("does_not_exist.txt")\ndici(fu["contentes"])\n'),
    ("e42_parse_int_runtime", "run", 'xa := "abc".a()\ndici(xes)\n'),
    ("e43_modulo_by_zero", "run", "xa := 5 % 0\ndici(xes)\n"),
    # ---- SHOULD work (consistency) ----
    ("e44_lambda_in_var_to_func", "ok", "fo := des {id * 2}\nresuum := [1, 2, 3].mutatuum(fo)\ndici(resuum.es())\n"),
    ("e45_string_literal_method", "ok", 'dici("hello".es())\n'),
    ("e46_chained_ternary", "ok", "xa := 1\nyes := xa == 0 ? \"zero\" : xa == 1 ? \"one\" : \"many\"\ndici(yes)\n"),
    ("e47_map_identifier_key", "ok", 'mu := {keya: 1}\ndici(mu["keya"].es())\n'),
    ("e48_nested_lambda", "ok", "makeo := des {des {id + 1}}\naddo := makeo()\ndici(addo(5).es())\n"),
    ("e49_lambda_var_direct_call", "ok", "fo := des {id * 10}\ndici(fo(4).es())\n"),
    ("e50_neg_index", "ok", "luum := [1, 2, 3]\ndici(luum[-1].es())\n"),

    # ================= second batch (e51+) =================
    # ---- more syntax errors ----
    ("e51_nested_unclosed_paren", "parse", "dici(adda(1, 2)\n"),
    ("e52_trailing_arg_comma", "parse", "des adda(xa, ya) { redeo xa + ya }\ndici(adda(1, 2,))\n"),
    ("e53_trailing_compare", "parse", "xa := 1 <\n"),
    ("e54_unclosed_map", "parse", 'mu := {"a": 1\n'),
    ("e55_keyword_as_var", "parse", "pro := 5\n"),
    ("e56_double_colon_map", "parse", 'mu := {"a":: 1}\n'),
    ("e57_else_missing_block", "parse", 'si verum {\n    dici("a")\n} aluid dici("b")\n'),
    ("e58_double_dot_field", "parse", "luum := [1, 2]\ndici(luum..es())\n"),
    ("e59_extra_close_paren", "parse", 'dici("hi"))\n'),
    ("e60_leading_dot_float", "ok", "xae := -.5\ndici((xae * 2.0).es())\n"),
    ("e61_empty_index", "parse", "luum := [1, 2]\ndici(luum[].es())\n"),
    ("e62_for_two_vars_no_comma", "parse", "luum := [1, 2]\npro ia ja in luum {\n    omitto\n}\n"),
    ("e63_lambda_missing_brace", "parse", "fo := des id * 2\n"),
    ("e64_unterminated_string_concat", "parse", 'dici("a" + "b)\n'),
    ("e65_assign_to_literal", "parse", "5 := xa\n"),
    ("e66_ternary_missing_false", "parse", "xa := verum ? 1 :\n"),
    ("e67_reserved_as_name", "parse", "redeo := 1\n"),
    ("e68_map_missing_comma", "parse", 'mu := {"a": 1 "b": 2}\n'),
    ("e69_list_trailing_operator", "parse", "luum := [1, 2 +]\n"),
    ("e70_mismatched_list_close", "parse", "luum := [1, 2)\n"),
    # ---- semantic errors (expect readable message / suggestion) ----
    ("e71_misspelled_user_func", "sem", "des doublea(xa) { redeo xa * 2 }\ndici(doubela(2).es())\n"),
    ("e72_misspelled_prelude", "sem", "fo := des {id + 1}\nresuum := [1,2,3].mutatuuum(fo)\n"),
    ("e73_undefined_in_expr", "sem", "totala := couna + 1\ndici(totala.es())\n"),
    ("e74_call_string_var", "sem", 'ses := "hi"\ndici(ses(1).es())\n'),
    ("e75_undefined_assign_target", "sem", "xa += 1\n"),
    # ---- runtime ----
    ("e76_parse_float_runtime", "run", 'xae := "notnum".ae()\ndici(xae.es())\n'),
    ("e77_index_oob_empty", "run", "luum := []\ndici(luum[0].es())\n"),
    # ---- SHOULD work (consistency / first-class functions) ----
    ("e78_func_as_value_var", "ok", "des doublea(xa) { redeo xa * 2 }\nfo := doublea\ndici(fo(21).es())\n"),
    ("e79_func_through_user_fn", "ok", "des inca(xa) { redeo xa + 1 }\ndes applya(fo, va) { redeo fo(va) }\ndici(applya(inca, 9).es())\n"),
    ("e80_func_in_list_called", "ok", "des doublea(xa) { redeo xa * 2 }\nluum := [doublea]\ndici(luum[0](5).es())\n"),
    ("e81_func_to_prelude_hof", "ok", "des inca(xa) { redeo xa + 1 }\nresuum := [1,2,3].mutatuum(inca)\ndici(resuum.es())\n"),
    ("e82_chain_after_call_index", "ok", "fo := des {id * 2}\nluum := [fo]\ndici(luum[0](5).es())\n"),
    ("e83_recursion_named", "ok", "des facta(na) {\n    si na < 2 { redeo 1 }\n    redeo na * facta(na - 1)\n}\ndici(facta(5).es())\n"),
    ("e84_func_value_to_reduce", "ok", "des adda(aa, ba) { redeo aa + ba }\ntota := [1,2,3,4].plicium(adda)\ndici(tota.es())\n"),
    ("e85_ternary_of_funcs", "ok", "des doublea(xa) { redeo xa * 2 }\ndes inca(xa) { redeo xa + 1 }\nflagam := verum\nfo := flagam ? doublea : inca\ndici(fo(10).es())\n"),
    ("e86_compound_assign_index", "ok", "luum := [1, 2, 3]\nluum[0] += 10\ndici(luum.es())\n"),
    ("e87_destructure_from_return", "ok", "des pairuum() { redeo [3, 4] }\naa, ba := pairuum()\ndici((aa + ba).es())\n"),
    ("e88_negative_float_literal", "ok", "xae := -1.5\ndici((xae * 2.0).es())\n"),
    ("e89_nested_index", "ok", "gruum := [[1, 2], [3, 4]]\ndici(gruum[1][0].es())\n"),
    ("e90_map_of_lists", "ok", 'mu := {"nuum": [10, 20, 30]}\ndici(mu["nuum"][2].es())\n'),
    ("e91_string_plus_num_cast", "ok", "na := 5\ndici(\"n=\" + na.es())\n"),
    ("e92_empty_list_hof", "ok", "fo := des {id * 2}\nresuum := [].mutatuum(fo)\ndici(resuum.a().es())\n"),
    ("e93_closure_captures_param", "ok", "des addero(na) {\n    redeo des {id + na}\n}\nadd5o := addero(5)\ndici(add5o(10).es())\n"),
    ("e94_lambda_captures_loop_var", "ok", "luum := []\npro ia in 0.<3 {\n    luum = luum.appenduum(des {id + ia})\n}\nfirsto := luum[0]\ndici(firsto(100).es())\n"),
    ("e95_bool_op_chain", "ok", "am := verum et falsus vel verum\ndici(am.es())\n"),
    ("e96_func_value_three_args", "ok", "des suma(aa, ba, ca) { redeo aa + ba + ca }\ndes apply3a(fo) { redeo fo(1, 2, 3) }\ndici(apply3a(suma).es())\n"),
    ("e97_method_chain_on_lambda_call", "ok", "fo := des {id * 2}\ndici(fo(8).es().a().es())\n"),
    ("e98_compose_functions", "ok", "des doublea(xa) { redeo xa * 2 }\ndes inca(xa) { redeo xa + 1 }\ndes composo(fo, go) {\n    redeo des {fo(go(id))}\n}\ndio := composo(doublea, inca)\ndici(dio(10).es())\n"),
    ("e99_map_value_lambda", "ok", 'fo := des {id + 1}\nmu := {"fo": fo}\ngo := mu["fo"]\ndici(go(41).es())\n'),
    ("e100_higher_order_returns_func", "ok", "des makeaddero(na) { redeo des {id + na} }\nadd3o := makeaddero(3)\nluum := [1, 2, 3].mutatuum(add3o)\ndici(luum.es())\n"),
]


def main():
    ERR_DIR.mkdir(parents=True, exist_ok=True)
    for name, _cat, src in CASES:
        (ERR_DIR / f"{name}.ago").write_text(src)

    survey = "--survey" in sys.argv
    if not survey:
        print(f"wrote {len(CASES)} files to {ERR_DIR}")
        return

    for name, cat, _src in CASES:
        f = ERR_DIR / f"{name}.ago"
        args = [sys.executable, str(MAIN), str(f), "--no-color"]
        if cat in ("parse", "sem"):
            args.append("--check")
        else:
            args += ["-q"]
        p = subprocess.run(args, capture_output=True, text=True, cwd=ERR_DIR, timeout=120)
        out = (p.stdout + p.stderr).strip()
        leaked = "Traceback (most recent call last)" in out
        rustbt = "stack backtrace" in out or "/rustc/" in out
        flag = "PYLEAK" if leaked else ("RUSTBT" if rustbt else "")
        print(f"\n===== [{cat}] {name}  rc={p.returncode} {flag} =====")
        print(out[:600])


if __name__ == "__main__":
    main()
