"""Tests for the Ago language server's diagnostics."""

import pytest

pytest.importorskip("pygls")

from src.AgoLsp import compute_diagnostics  # noqa: E402


def test_clean_program_has_no_diagnostics():
    assert compute_diagnostics("xa := 1\ndici(xes)\n") == []


def test_undefined_variable_reported_on_user_line():
    # `zes` (a string) is never defined; the diagnostic must land on the user's
    # line 1, not be shifted by the prepended prelude.
    diags = compute_diagnostics("xa := 1\nya := zes\n")
    assert len(diags) == 1
    assert diags[0].range.start.line == 1
    assert "zes" in diags[0].message


def test_parse_error_reported():
    diags = compute_diagnostics("xa := \n")
    assert len(diags) >= 1
    assert "parse error" in diags[0].message.lower()


def test_prelude_functions_resolve():
    # mutatuum/finderum etc. live in the prelude; using them must not produce
    # "undefined" diagnostics.
    src = 'luum := [1, 2, 3].mutatuum(des {id * 2})\ndici(luum.es())\n'
    assert compute_diagnostics(src) == []


# ---- symbols: completion + go-to-definition ----

from src.AgoLsp import collect_definitions, prelude_functions, _stem, _BUILTINS  # noqa: E402


def test_collect_definitions_finds_vars_funcs_params():
    src = "xa := 5\ndes addia(pa, qa) {\n  redeo pa + qa\n}\n"
    names = {(d["name"], d["kind"]) for d in collect_definitions(src)}
    assert ("xa", "variable") in names
    assert ("addia", "function") in names
    assert ("pa", "parameter") in names
    assert ("qa", "parameter") in names


def test_goto_definition_is_stem_aware():
    # Cursor on `xes` (string ending) must resolve to the `xa` declaration
    # (int ending) — same stem, different suffix.
    src = "xa := 5\nya := xes + 1\n"
    defs = collect_definitions(src)
    cands = [d for d in defs if d["stem"] == _stem("xes")]
    assert cands
    assert min(cands, key=lambda d: d["line"])["name"] == "xa"
    assert min(cands, key=lambda d: d["line"])["line"] == 0


def test_goto_definition_prefers_enclosing_function_scope():
    # `xa` is declared at top level and re-declared in two functions. A
    # reference inside `bari` must resolve to bari's own `xa`, not the
    # earlier top-level or fooi declaration.
    from src.AgoLsp import _function_spans, _select_definition

    src = (
        "xa := 1\n"            # line 0  (top-level)
        "des fooi(ya) {\n"     # line 1
        "    xa := 10\n"       # line 2  (fooi's xa)
        "    redeo xa\n"       # line 3
        "}\n"                  # line 4
        "des bari(za) {\n"     # line 5
        "    xa := 20\n"       # line 6  (bari's xa)
        "    redeo xa + za\n"  # line 7
        "}\n"
    )
    spans = _function_spans(src.split("\n"))
    cands = [d for d in collect_definitions(src) if d["stem"] == "x"]

    assert _select_definition([dict(d) for d in cands], spans, 7)["line"] == 6
    assert _select_definition([dict(d) for d in cands], spans, 3)["line"] == 2
    assert _select_definition([dict(d) for d in cands], spans, 0)["line"] == 0


def _goto(src: str, word: str, cursor_line: int):
    """Mirror the definition handler's resolution: exact-name first, then stem,
    each scoped to the nearest enclosing block."""
    from src.AgoLsp import _function_spans, _select_definition

    lines = src.split("\n")
    same = [d for d in collect_definitions(src) if d["stem"] == _stem(word)]
    spans = _function_spans(lines)
    exact = [d for d in same if d["name"] == word]
    pool = exact if exact else same
    return _select_definition([dict(d) for d in pool], spans, cursor_line)["line"]


def test_goto_definition_loop_variable_is_block_scoped():
    # `guum` and the loop variable `ga` share the stem `g`. Go-to-def on `guum`
    # outside the loop, and on the loop header, must land on the `guum`
    # declaration (line 0), not the block-local `ga`.
    src = (
        'guum := apertu("b").contentes.finduum("x")\n'  # 0
        "\n"                                              # 1
        "mapuum := []\n"                                  # 2
        "pro ga in guum[0].erum().e() {\n"                # 3
        "    mapuum = mapuum.appenduum(0)\n"              # 4
        "}\n"                                             # 5
        'mapuum[guum[0].erum().invena("S")] = 1\n'        # 6
    )
    assert _goto(src, "guum", 6) == 0   # below the loop
    assert _goto(src, "guum", 3) == 0   # on the loop header (iterable)
    assert _goto(src, "ga", 4) == 3     # the loop var, from inside the loop
    # Pure stem fallback (no exact name) still respects block scope.
    assert _goto(src, "gaem", 6) == 0


def test_references_respect_block_scope():
    # `guum` (stem g) and the loop var `ga` (stem g) must not be conflated by
    # find-references / rename.
    from src.AgoLsp import _scoped_occurrences

    src = (
        "guum := [1, 2, 3]\n"          # 0
        "pro ga in guum.erum() {\n"    # 1
        "    dici(ga.es())\n"          # 2
        "}\n"                          # 3
        "dici(guum.es())\n"            # 4
    )
    lines = src.split("\n")
    guum_refs = sorted(l for l, _c, _n in _scoped_occurrences(lines, "guum", 4))
    ga_refs = sorted(l for l, _c, _n in _scoped_occurrences(lines, "ga", 2))
    assert guum_refs == [0, 1, 4]   # not the loop variable
    assert ga_refs == [1, 2]        # not guum


def test_prelude_functions_indexed_by_stem():
    pf = prelude_functions()
    names = {f["name"] for f in pf}
    assert "finderum" in names and "mutatuum" in names
    # stem-aware lookup of a prelude function
    assert any(f["stem"] == _stem("finderum") for f in pf)


def test_builtins_present():
    for b in ("dici", "congruum", "exemplium", "ordina"):
        assert b in _BUILTINS


# ---- references / rename (stem-aware) / semantic tokens ----

from src.AgoLsp import _iter_identifiers, _stem_bucket  # noqa: E402
from src.AgoCodeGenerator import get_suffix_and_stem  # noqa: E402


def test_iter_identifiers_skips_keywords_and_strings():
    lines = ['si xa { dici("xa not here") }  # xa not here']
    found = [name for _, _, name in _iter_identifiers(lines)]
    assert "xa" in found and "dici" in found
    assert "si" not in found  # keyword excluded
    assert found.count("xa") == 1  # the one in the string/comment is skipped


def test_references_are_stem_aware():
    lines = ["xa := 5", "ya := xes + 1", "dici(xerum)"]
    hits = [(ln, name) for ln, _, name in _iter_identifiers(lines) if get_suffix_and_stem(name)[1] == "x"]
    assert sorted(n for _, n in hits) == ["xa", "xerum", "xes"]


def test_rename_preserves_each_ending():
    lines = ["xa := 5", "ya := xes + 1", "dici(xerum)"]
    new_stem = "z"
    out = []
    for _, _, name in _iter_identifiers(lines):
        suffix, stem = get_suffix_and_stem(name)
        if stem == "x":
            out.append(new_stem + (suffix or ""))
    assert sorted(out) == ["za", "zerum", "zes"]


def test_stem_bucket_is_stable_and_stem_based():
    # Same stem -> same bucket, regardless of ending.
    assert _stem_bucket("xa") == _stem_bucket("xes") == _stem_bucket("xerum")
    assert 0 <= _stem_bucket("foo") < 16


def test_builtin_docs_come_from_rust_source():
    from src.AgoLsp import builtin_doc, _BUILTINS
    # Every exported builtin should now have documentation (from its Rust ///).
    missing = [b for b in _BUILTINS if not builtin_doc(b)]
    assert missing == [], f"builtins missing docs: {missing}"
    assert "stdout" in builtin_doc("dici").lower()
    assert "struct" in builtin_doc("valuum").lower()
