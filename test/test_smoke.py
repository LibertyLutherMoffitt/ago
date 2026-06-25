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
        rust = _gen(
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
