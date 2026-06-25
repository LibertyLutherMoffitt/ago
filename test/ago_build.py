"""Shared build helper for the Ago test suite.

Centralizes "compile an Ago snippet to Rust, build it, run it, return stdout".

Speed matters a lot here: a `cargo build` per test dominates wall-clock time.
Two things make this as cheap as possible:

1. A persistent, per-worker build directory with a *fixed* crate name. Because
   the crate name and path are stable, cargo does a true incremental rebuild and
   only recompiles the per-test `main.rs` (and relinks) — the `ago_stdlib`
   dependency is compiled once and then reused for every subsequent test, and we
   never accumulate hundreds of distinct crates in the target dir.

2. A per-worker directory keyed off the pytest-xdist worker id (falling back to
   the pid). That keeps the fixed crate name parallel-safe: each worker owns its
   own build dir and target dir, so workers never clash, while still getting
   incremental reuse within the worker.
"""

import os
import subprocess
from pathlib import Path

from src.AgoParser import AgoParser
from src.AgoSemanticChecker import AgoSemanticChecker
from src.AgoCodeGenerator import generate

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
STDLIB_DIR = SCRIPT_DIR / "src" / "rust"
PRELUDE_FILE = SCRIPT_DIR / "stdlib" / "prelude.ago"

CRATE_NAME = "ago_program"

# Root for persistent per-worker build dirs (gitignored under target/).
_BUILD_ROOT = Path(
    os.environ.get("AGO_TEST_BUILD_ROOT", SCRIPT_DIR / "target" / "ago_test_build")
)


def _worker_dir() -> Path:
    """A stable build dir for this worker, created on demand.

    Keyed by the pytest-xdist worker id when running in parallel, else a single
    fixed name. Crucially this is *not* keyed by pid, so the compiled stdlib
    persists across separate test runs and only the per-test main.rs recompiles.
    """
    worker = os.environ.get("PYTEST_XDIST_WORKER") or "local"
    d = _BUILD_ROOT / worker
    (d / "src").mkdir(parents=True, exist_ok=True)
    return d


def _ensure_manifest(build_dir: Path) -> None:
    """Write the Cargo.toml once (stable, so it doesn't trigger rebuilds)."""
    manifest = build_dir / "Cargo.toml"
    content = f'''[package]
name = "{CRATE_NAME}"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "{CRATE_NAME}"
path = "src/main.rs"

[dependencies]
ago_stdlib = {{ path = "{STDLIB_DIR}" }}
'''
    if not manifest.exists() or manifest.read_text() != content:
        manifest.write_text(content)


def compile_and_run(
    ago_source: str, include_prelude: bool = False, release: bool = True
) -> str:
    """Compile Ago source to Rust, build it, run it, and return stdout.

    `release=True` (the default) matches the historical behaviour of the suite.
    Pass `release=False` for a *much* faster debug build (~1s cold / ~0.2s warm
    vs ~46s/~11s in release for prelude-heavy programs) — the release optimizer
    is what's slow on the prelude's many monomorphized closures. Note debug
    builds enable integer-overflow checks, so they may panic where release wraps.
    """
    if include_prelude and PRELUDE_FILE.exists():
        ago_source = PRELUDE_FILE.read_text() + "\n" + ago_source

    # Parse and check
    parser = AgoParser()
    semantics = AgoSemanticChecker()
    ast = parser.parse(ago_source + "\n", semantics=semantics)
    if semantics.errors:
        raise ValueError(f"Semantic errors: {semantics.errors}")

    rust_code = generate(ast)

    build_dir = _worker_dir()
    _ensure_manifest(build_dir)
    (build_dir / "src" / "main.rs").write_text(rust_code)

    target_dir = build_dir / "target"
    env = dict(os.environ, CARGO_TARGET_DIR=str(target_dir))

    cmd = ["cargo", "build"]
    profile_dir = "debug"
    if release:
        cmd.append("--release")
        profile_dir = "release"

    result = subprocess.run(
        cmd, cwd=build_dir, capture_output=True, text=True, env=env
    )
    if result.returncode != 0:
        raise RuntimeError(f"Compilation failed:\n{result.stderr}")

    exe_path = target_dir / profile_dir / CRATE_NAME
    result = subprocess.run([str(exe_path)], capture_output=True, text=True)
    return result.stdout
