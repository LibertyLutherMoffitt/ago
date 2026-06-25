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
