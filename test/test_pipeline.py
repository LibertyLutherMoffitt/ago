"""Tests for the compile pipeline: prelude AST caching and the separate
user-code parse (which keeps user line numbers their own)."""

import importlib

import main as ago_main
from src.AgoParser import AgoParser
from src.AgoSemanticChecker import AgoSemanticChecker
from src.AgoCodeGenerator import generate


def test_prelude_ast_is_tuple_and_nonempty():
    ast = ago_main.prelude_ast()
    assert isinstance(ast, tuple)
    assert len(ast) > 0


def test_cached_pipeline_matches_uncached():
    # The cached path (cached prelude AST + freshly parsed user code) must
    # produce exactly the same Rust as parsing both fresh with the same method
    # (prelude without parseinfo, user with). This is the cache==no-cache
    # invariant. (It is NOT compared to a single combined parse, because that
    # would give the prelude parseinfo and thus extra line-tracking calls.)
    user = (
        "des doublea(xa) { redeo xa * 2 }\n"
        "resuum := [1, 2, 3].mutatuum(doublea)\n"
        "dici(resuum.es())\n"
    )
    prelude = ago_main.load_prelude()

    fresh_prelude = AgoParser(parseinfo=False).parse(prelude)
    fresh_user = AgoParser(parseinfo=True).parse(user)
    ref = generate(tuple(fresh_prelude) + tuple(fresh_user))

    combined, semantics = ago_main.parse_source(user, "mem.ago")
    assert semantics.errors == []
    assert generate(combined) == ref


def test_user_error_line_is_user_relative():
    # An error on the user's second line must report line 2, not a
    # prelude-shifted line. The CLI maps a node to a display line via _node_loc
    # against the user source (0-based internally, shown +1).
    user = "xa := 5\ndici(xes + yundefineda)\n"
    _combined, semantics = ago_main.parse_source(user, "mem.ago")
    assert semantics.errors
    err = semantics.errors[0]
    assert "yundefineda" in str(err)
    loc = ago_main._node_loc(err.node, user)
    assert loc is not None
    line0, _col0, _length = loc
    assert line0 + 1 == 2  # displayed as line 2


def test_codegen_emits_line_tracking():
    # The generated program installs the panic hook and tags user statements
    # with their source line so a panic can be mapped back to Ago.
    user = "luum := [1, 2]\ndici(luum[5].es())\n"
    combined, _semantics = ago_main.parse_source(user, "mem.ago")
    rust = generate(combined)
    assert "ago_install_panic_hook();" in rust
    assert "ago_set_line(1);" in rust  # the declaration on line 1
    assert "ago_set_line(2);" in rust  # the dici(...) call on line 2


def test_runtime_error_marker_renders_source_line(capsys):
    # The CLI turns the runtime panic marker into a diagnostic at the Ago line.
    user = "luum := [1, 2]\ndici(luum[5].es())\n"
    stderr = "__AGO_RT__2\tIndex out of bounds: 5\n"
    ago_main._report_runtime_error(stderr, "prog.ago", user)
    out = capsys.readouterr()
    combined = out.out + out.err
    assert "runtime error: Index out of bounds: 5" in combined
    assert "prog.ago:2" in combined
    assert "dici(luum[5].es())" in combined


def test_prelude_cache_roundtrips(tmp_path, monkeypatch):
    # Point the cache at a temp file, build it, and confirm a second call reads
    # it back to an identical AST.
    cache = tmp_path / "prelude_ast.pkl"
    monkeypatch.setattr(ago_main, "PRELUDE_AST_CACHE", cache)
    monkeypatch.setattr(ago_main, "CACHE_DIR", tmp_path)
    if cache.exists():
        cache.unlink()
    first = ago_main.prelude_ast()
    assert cache.exists()
    second = ago_main.prelude_ast()
    # Same generated Rust from both (the unpickled AST is equivalent).
    u = AgoParser(parseinfo=True).parse("dici(\"hi\")\n")
    assert generate(tuple(first) + tuple(u)) == generate(tuple(second) + tuple(u))
