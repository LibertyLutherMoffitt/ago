"""Fast sanity layer for Ago.

The full suite recompiles the prelude in `--release` for almost every test and
takes ~27 minutes on this container — far too slow to run while iterating. This
module is the cheap alternative: a tiny set of checks that still catch most
breakage in seconds.

Two tiers:

* `TestCodegenStructure` — pure-Python checks on the generated Rust *text*. No
  cargo, no prelude; runs in milliseconds. Good for codegen regressions.

* `TestEndToEnd` — ONE comprehensive Ago program, built once in *debug* mode
  (~1s cold / ~0.2s warm) and run once, asserting the whole output block. Debug
  avoids the release optimizer that makes prelude builds slow.

Run just this layer while developing:

    python -m pytest test/test_smoke.py -q

Leave the exhaustive `--release` suite (test_codegen.py, test_mergesort_and_range.py)
for a full pre-merge / end-of-day run.
"""

from pathlib import Path

from src.AgoParser import AgoParser
from src.AgoSemanticChecker import AgoSemanticChecker
from src.AgoCodeGenerator import generate, AgoCodeGenerator

from ago_build import compile_and_run

# Trimmed prelude (only the functions the smoke program needs). Used instead of
# the full stdlib/prelude.ago because the parser is superlinear and parsing the
# full prelude alone takes ~19s; the trimmed version parses in ~1.5s.
SMOKE_PRELUDE = (Path(__file__).parent / "smoke_prelude.ago").read_text()


def _gen(src: str) -> str:
    parser = AgoParser()
    semantics = AgoSemanticChecker()
    ast = parser.parse(src + "\n", semantics=semantics)
    assert not semantics.errors, semantics.errors
    return generate(ast)


def _gen_p(src: str) -> str:
    """Like _gen but with the trimmed prelude prepended, for programs that call
    prelude higher-order functions (mutatuum, plicium, ...). Those names are only
    'defined' once the prelude is in scope, which the real CLI always does."""
    return _gen(SMOKE_PRELUDE + "\n" + src)


class TestCodegenStructure:
    """Pure-Python codegen checks — no cargo, sub-second."""

    def test_int_literal_and_cast(self):
        rust = _gen("xa := 42\ndici(xes)")
        assert "AgoType::Int(42)" in rust

    def test_lambda_is_first_class_agotype(self):
        # Lambdas are ordinary first-class AgoType values: a function holding a
        # lambda takes it as `&AgoType` (like any value), calls it via
        # `call_lambda`, and an inline lambda is passed by reference exactly like
        # a lambda stored in a variable.
        rust = _gen(
            "des applica(xo, vium) { redeo xo(vium) }\n"
            "des indira(luum, xo) { redeo applica(xo, luum[0]) }\n"
            "[5,2,8].indira(des (xium) { xium + 1 }).es().dici()"
        )
        # Lambda parameter is a plain reference, invoked with call_lambda.
        assert "xo: &AgoType" in rust
        assert "xo.call_lambda(" in rust
        # A lambda param forwarded to another function is passed by reference,
        # not cloned by value.
        assert "applica(xo," in rust
        assert "xo.clone()" not in rust
        # An inline lambda literal is a first-class AgoType::Lambda value.
        assert "&AgoType::Lambda(Rc::new(" in rust

    def test_native_int_loop_unboxed(self):
        # Typed-unboxing: a scalar int accumulator over a range loop should emit
        # native i128 (let mut x: i128, native arithmetic, native range), not the
        # boxed AgoType form, while still boxing at the print boundary.
        rust = _gen(
            "sa := 0\n"
            "pro ia in 0.<10 { sa = sa + ia * ia }\n"
            "sa.es().dici()"
        )
        assert "let mut sa: i128" in rust
        # Count-based native range loop: a register i128 index, with the loop
        # variable computed natively (lo + inc*k) so descending/stepped ranges
        # stay correct without boxing.
        assert "in 0..__cnt" in rust
        assert "let ia: i128 =" in rust
        assert "sa = (sa + (ia * ia));" in rust
        assert "AgoType::Int(sa).as_type(TargetType::String)" in rust

    def test_native_div_mod_routed_through_helpers(self):
        # Native int / and % go through ago_div/ago_mod so a literal zero divisor
        # is a clean runtime panic, not a rustc unconditional_panic lint.
        rust = _gen(
            "sa := 0\n"
            "pro ia in 1.<5 { sa = sa + 100 / ia + 7 % ia }\n"
            "sa.es().dici()"
        )
        assert "ago_div(" in rust
        assert "ago_mod(" in rust

    def test_native_int_not_applied_to_params(self):
        # Parameters are never native (they arrive as &AgoType / cloned AgoType),
        # even when mutated in the body.
        rust = _gen(
            "des powa(basea, expa) {\n"
            "    resulta := 1\n"
            "    dum expa > 0 { resulta = resulta * basea\n expa = expa - 1 }\n"
            "    redeo resulta\n"
            "}\n"
            "powa(2, 8).es().dici()"
        )
        assert "let mut expa: i128" not in rust
        assert "let mut resulta: i128" not in rust  # demoted: RHS uses param basea

    def test_native_int_loop_unboxed_runs(self):
        out = compile_and_run(
            "sa := 0\npro ia in 0.<1000 { sa = sa + ia }\nsa.es().dici()",
            release=False,
        )
        assert out.strip() == "499500"

    def test_native_int_loop_with_runtime_bound(self):
        # Loop bound that isn't statically native is unboxed at runtime via as_int().
        rust = _gen(
            "luum := [1,2,3,4]\nsa := 0\npro ia in 0.<luum.a() { sa = sa + ia }\nsa.es().dici()"
        )
        assert ".as_int()" in rust

    def test_list_literal_clones_ref_param(self):
        # Regression: a function parameter (a reference) used as an element of a
        # list literal must be cloned, not emitted as a borrow inside vec![].
        rust = _gen(
            "des wrapuum(xium, posa) { redeo [xium, posa] }\n"
            "wrapuum(1, 2).es().dici()"
        )
        assert "vec![xium.clone(), posa.clone()]" in rust

    def test_captured_ref_param_passed_by_ref_to_user_fn(self):
        # Regression: a reference parameter captured into a lambda becomes an
        # owned value inside the closure (cloned), so passing it to a user
        # function (which takes &AgoType) must add `&` — it must not be treated
        # as a still-live reference parameter.
        rust = _gen_p(
            "des helpera(xium, yium) { redeo xium + yium }\n"
            "des fuum(luum, basea) { redeo luum.mutatuum(des { helpera(id, basea) }) }\n"
            "[1,2,3].fuum(10).es().dici()"
        )
        assert "helpera(&id, &basea)" in rust

    def test_first_class_lambda_shapes(self):
        # A function returning a lambda returns a plain AgoType (the lambda is an
        # AgoType::Lambda value), and a nested lambda compiles as a value too.
        rust = _gen(
            "des makero() { redeo des { id + 1 } }\n"
            "addo := makero()\n"
            "addo(5).es().dici()"
        )
        # No special AgoLambda return type — everything is AgoType now.
        assert "-> AgoType {" in rust
        assert "-> AgoLambda" not in rust
        # The returned lambda is an AgoType::Lambda value, and calling the
        # variable goes through call_lambda.
        assert "AgoType::Lambda(Rc::new(" in rust
        assert "addo.call_lambda(" in rust

    def test_named_function_as_first_class_value(self):
        # A named `des fooi(...)` used as a value (passed to a lambda param) is
        # wrapped in an AgoType::Lambda adapter of the right arity, so a function
        # works wherever a lambda does.
        rust = _gen_p(
            "des doublea(xa) { redeo xa * 2 }\n"
            "resuum := [1,2,3].mutatuum(doublea)\n"
            "resuum.es().dici()"
        )
        assert "AgoType::Lambda(Rc::new(move |args: &[AgoType]| -> AgoType { doublea(" in rust

    def test_call_postfix_on_index_and_call(self):
        # A call can directly follow an index or another call: `luum[0](5)` and
        # `makero()(5)` both invoke the resulting value via call_lambda.
        rust = _gen(
            "fo := des { id * 2 }\n"
            "luum := [fo]\n"
            "luum[0](5).es().dici()"
        )
        assert "get(&luum, &AgoType::Int(0)).call_lambda(&[AgoType::Int(5)])" in rust

    def test_is_lambda_expr_helper(self):
        # _is_lambda_expr now recognizes only inline lambda *literals*
        # (AgoType::Lambda(...)); lambda *variables* are ordinary AgoType values
        # and need no special handling.
        g = AgoCodeGenerator()
        g.declared_vars = {"xo", "luum"}
        g._lambda_params = {"yo"}
        assert g._is_lambda_expr(
            "AgoType::Lambda(Rc::new(|args: &[AgoType]| -> AgoType { x }) as AgoLambda)"
        )
        assert g._is_lambda_expr(
            "{ let a = a.clone(); AgoType::Lambda(Rc::new(move |args| x) as AgoLambda) }"
        )
        assert not g._is_lambda_expr("xo")
        assert not g._is_lambda_expr("luum")
        assert not g._is_lambda_expr("AgoType::Int(1)")


# One program that exercises a broad slice of the language + prelude. Built once.
SMOKE_PROGRAM = """
# arithmetic, ternary, comparison
xa := 7
ya := 3
(xa + ya).es().dici()
(xa % ya).es().dici()
(xa > ya ? "big" : "small").dici()

# strings: split + join
linerum := "a,bb,ccc".finderum(",")
linerum.a().es().dici()
linerum.iunges("-").dici()

# range -> int list -> sum
re := (1..5)
re.aem().sumes().dici()

# list slice + map-to-string + join
[10,20,30,40][1.<3].mutatuum(des {ides}).iunges(",").dici()

# higher-order with lambda key through prelude (genorduum, liquum)
[3,1,2,9,5].genorduum(des { id }).mutatuum(des {ides}).iunges(",").dici()
[3,1,2,9,5].liquum(des { id > 2 }).mutatuum(des {ides}).iunges(",").dici()

# user function + recursion
des facta(na) {
    si na <= 1 { redeo 1 }
    redeo na * facta(na - 1)
}
facta(5).es().dici()

# control flow accumulation (pergo / odd sum)
ca := 0
pro ia in 0.<10 {
    si ia % 2 == 0 { pergo }
    ca = ca + ia
}
ca.es().dici()

# map / struct indexing
mu := {}
mu["k"] = 42
mu["k"].es().dici()
"""

EXPECTED = [
    "10",         # 7 + 3
    "1",          # 7 % 3
    "big",        # ternary
    "3",          # list length
    "a-bb-ccc",   # string join
    "15",         # sum 1..5
    "20,30",      # slice [1.<3]
    "1,2,3,5,9",  # genorduum sort (lambda key through prelude)
    "3,9,5",      # liquum keep > 2, order preserved
    "120",        # 5! via recursion
    "25",         # 1+3+5+7+9
    "42",         # map get
]


class TestEndToEnd:
    """Single debug build that covers a broad language slice."""

    def test_smoke_program(self):
        # Prepend the trimmed prelude (not the full one) for a fast parse, and
        # build in debug for a fast compile.
        out = compile_and_run(
            SMOKE_PRELUDE + "\n" + SMOKE_PROGRAM,
            include_prelude=False,
            release=False,
        )
        assert out.splitlines() == EXPECTED


class TestStringInterpolation:
    def test_interpolation_codegen(self):
        rust = _gen('na := 5\ndici("n=${na}")\n')
        assert ".as_type(TargetType::String)" in rust
        assert "add(" in rust

    def test_interpolation_runs(self):
        out = compile_and_run(
            'na := 5\nses := "hi"\ndici("${ses} n=${na} sum=${na + 1}")\n',
            release=False,
        )
        assert out.strip() == "hi n=5 sum=6"

    def test_nested_quote_interpolation_runs(self):
        out = compile_and_run('na := 42\ndici("outer ${"inner=" + na.es()}")\n', release=False)
        assert out.strip() == "outer inner=42"

    def test_plain_string_unaffected(self):
        rust = _gen('dici("plain")\n')
        assert 'AgoType::String("plain".to_string())' in rust


class TestNativeFloatBool:
    def test_native_float_unboxed(self):
        rust = _gen("xae := 1.5\nyae := xae * 2.0 + 0.5\nyae.es().dici()")
        assert "let mut xae: f64 = 1.5f64;" in rust
        assert "let mut yae: f64 = ((xae * 2.0f64) + 0.5f64);" in rust

    def test_native_bool_unboxed(self):
        rust = _gen("xa := 7\nevenam := xa % 2 == 0\nbigam := xa > 5 et xa < 9\nevenam.es().dici()")
        assert "let mut evenam: bool = (ago_mod(xa, 2i128) == 0i128);" in rust
        assert "&&" in rust

    def test_native_float_runs(self):
        out = compile_and_run("xae := 1.5\nyae := xae * 2.0 + 0.5\nyae.es().dici()", release=False)
        assert out.strip() == "3.5"

    def test_native_bool_runs(self):
        out = compile_and_run("xa := 7\nbigam := xa > 5 et xa < 9\nbigam.es().dici()", release=False)
        assert out.strip() == "true"

    def test_native_cast_operand_unboxed(self):
        # `ia.ae()` (int->float cast) inside a native float expr converts natively.
        rust = _gen("sumae := 0.0\npro ia in 1.<5 { sumae = sumae + 1.0 / ia.ae() }\nsumae.es().dici()")
        assert "(ia as f64)" in rust
        assert "let mut sumae: f64" in rust

    def test_native_float_boxes_at_boundary(self):
        # A native float passed to a function / printed is re-boxed as AgoType::Float.
        rust = _gen("xae := 2.5\ndici(xae.es())")
        assert "AgoType::Float(xae)" in rust


class TestForDestructuring:
    def test_destructure_pairs_codegen(self):
        rust = _gen("puum := [[1, 2]]\npro (fa, sa) in puum {\n  dici((fa + sa).es())\n}")
        assert "into_iter(" in rust
        assert "let fa = get(" in rust
        assert "let sa = get(" in rust

    def test_destructure_pairs_runs(self):
        out = compile_and_run(
            "puum := [[123, 148], [999, 1000]]\npro (fa, sa) in puum {\n  dici((fa + sa).es())\n}",
            release=False,
        )
        assert out.split() == ["271", "1999"]


class TestTailCallOptimization:
    def test_tail_self_call_becomes_loop(self):
        rust = _gen(
            "des suma(na, acca) {\n  si na == 0 { redeo acca }\n  redeo suma(na - 1, acca + na)\n}\n"
            "suma(3, 0).es().dici()"
        )
        assert "'tco: loop {" in rust
        assert "continue 'tco;" in rust

    def test_non_tail_recursion_not_transformed(self):
        rust = _gen(
            "des facta(na) {\n  si na < 2 { redeo 1 }\n  redeo na * facta(na - 1)\n}\n"
            "facta(5).es().dici()"
        )
        assert "'tco" not in rust

    def test_deep_tail_recursion_runs(self):
        out = compile_and_run(
            "des suma(na, acca) {\n  si na == 0 { redeo acca }\n  redeo suma(na - 1, acca + na)\n}\n"
            "suma(100000, 0).es().dici()",
            release=False,
        )
        assert out.strip() == "5000050000"


class TestMapFilterFusion:
    def test_map_filter_chain_is_fused(self):
        rust = _gen_p(
            "auum := [1, 2, 3, 4].mutatuum(des { id * 2 }).liquum(des { id > 4 })\n"
            "auum.es().dici()"
        )
        # The two stages collapse into a single lazy iterator pipeline.
        assert "into_iter(&" in rust
        assert ".map(|__e|" in rust
        assert ".filter(|__e|" in rust
        assert "__fuse_fn" in rust

    def test_single_map_is_not_fused(self):
        # A lone map has nothing to fuse with, so it stays on the eager path.
        rust = _gen_p("auum := [1, 2, 3].mutatuum(des { id * 2 })\nauum.es().dici()")
        assert "__fuse_fn" not in rust

    def test_cast_suffix_form_falls_back(self):
        # `.mutataem` carries a list cast; only the canonical `mutatuum` /
        # `liquum` forms fuse, so this stays eager.
        rust = _gen_p(
            "auum := [1, 2, 3].mutataem(des { id * 2 }).liquum(des { id > 2 })\n"
            "auum.es().dici()"
        )
        assert "__fuse_fn" not in rust

    def test_fused_chain_runs_correctly(self):
        out = compile_and_run(
            "auum := [1, 2, 3, 4, 5, 6].mutatuum(des { id * 2 }).liquum(des { id > 5 })\n"
            "auum.es().dici()",
            include_prelude=True,
            release=False,
        )
        assert out.strip() == "6\n8\n10\n12"

    def test_fusion_does_not_consume_source(self):
        # Fusing over a variable must borrow, not move it: the source list is
        # still usable afterwards.
        out = compile_and_run(
            "xsaem := [1, 2, 3, 4]\n"
            "auum := xsaem.mutatuum(des { id + 1 }).liquum(des { id > 2 })\n"
            "auum.es().dici()\n"
            "xsaem.es().dici()",
            include_prelude=True,
            release=False,
        )
        assert out.strip() == "3\n4\n5\n1\n2\n3\n4"


class TestTerminalFusion:
    def test_map_any_fuses_to_short_circuit(self):
        rust = _gen_p(
            "xsaem := [1, 2, 3]\n"
            "dici(xsaem.mutatuum(des { id * 2 }).ullam(des { id > 4 }).es())"
        )
        assert ".any(|__e|" in rust and "__fuse_fn" in rust

    def test_filter_reduce_fuses(self):
        rust = _gen_p(
            "xsaem := [1, 2, 3, 4]\n"
            "dici(xsaem.liquum(des { id % 2 == 0 })"
            ".plicium(des (aium, bium) { aium + bium }).es())"
        )
        assert ".reduce(|__a, __b|" in rust and "__fuse_fn" in rust

    def test_standalone_terminal_not_fused(self):
        # A terminal with no preceding map/filter stays on the eager prelude
        # path (which already short-circuits).
        rust = _gen_p("xsaem := [1, 2, 3]\ndici(xsaem.ullam(des { id > 2 }).es())")
        assert "__fuse_fn" not in rust

    def test_any_all_none_run_correctly(self):
        out = compile_and_run(
            "xsaem := [1, 2, 3, 4, 5, 6]\n"
            "dici(xsaem.mutatuum(des { id * 2 }).ullam(des { id > 10 }).es())\n"
            "dici(xsaem.mutatuum(des { id * 2 }).omnam(des { id % 2 == 0 }).es())\n"
            "dici(xsaem.mutatuum(des { id * 2 }).nullam(des { id % 2 == 1 }).es())",
            include_prelude=True,
            release=False,
        )
        assert out.strip() == "true\ntrue\ntrue"

    def test_find_index_fuses(self):
        out = compile_and_run(
            "xsaem := [1, 2, 3, 4, 5, 6]\n"
            "dici(xsaem.mutatuum(des { id * 2 }).invena(8).es())\n"
            "dici(xsaem.mutatuum(des { id * 2 }).invena(7).species())",
            include_prelude=True,
            release=False,
        )
        assert out.strip() == "3\nNull"

    def test_reduce_fuses_with_empty_yielding_inanis(self):
        out = compile_and_run(
            "xsaem := [1, 2, 3, 4, 5, 6]\n"
            "dici(xsaem.liquum(des { id % 2 == 0 })"
            ".plicium(des (aium, bium) { aium + bium }).es())\n"
            "dici(xsaem.liquum(des { id > 100 })"
            ".plicium(des (aium, bium) { aium + bium }).species())",
            include_prelude=True,
            release=False,
        )
        assert out.strip() == "12\nNull"
