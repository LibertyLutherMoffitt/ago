#!/usr/bin/env python3
"""Tiny runner for the Ago AoC solutions.

For each day directory under aoc/2024/, compiles dayNN.ago with the Ago
compiler (main.py), runs the resulting binary in that directory (so its
`apertu("in.txt")` reads the local example input), and compares stdout against
expected.txt (one expected line per part).

Usage:
    python aoc/run.py            # run all days
    python aoc/run.py 01 03      # run only day 01 and 03
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
MAIN = ROOT / "main.py"
YEAR_DIR = Path(__file__).parent / "2024"


def run_day(day_dir: Path) -> bool:
    sol = day_dir / f"{day_dir.name}.ago"
    expected_file = day_dir / "expected.txt"
    if not sol.exists() or not expected_file.exists():
        print(f"  {day_dir.name}: SKIP (missing solution or expected.txt)")
        return True

    expected = expected_file.read_text().strip().splitlines()
    binpath = day_dir / "program"

    build = subprocess.run(
        [sys.executable, str(MAIN), str(sol), "--emit", "bin", "-o", str(binpath), "-q"],
        capture_output=True, text=True,
    )
    if build.returncode != 0:
        print(f"  {day_dir.name}: BUILD FAILED")
        print(build.stderr or build.stdout)
        return False

    run = subprocess.run([str(binpath)], cwd=day_dir, capture_output=True, text=True)
    got = run.stdout.strip().splitlines()
    if run.returncode != 0:
        print(f"  {day_dir.name}: RUNTIME PANIC")
        print(run.stderr)
        return False

    if got == expected:
        print(f"  {day_dir.name}: OK  {got}")
        return True
    print(f"  {day_dir.name}: MISMATCH  expected {expected}  got {got}")
    return False


def main():
    wanted = set(sys.argv[1:])
    days = sorted(d for d in YEAR_DIR.iterdir() if d.is_dir()) if YEAR_DIR.exists() else []
    if wanted:
        days = [d for d in days if d.name.removeprefix("day") in wanted or d.name in wanted]
    if not days:
        print("No day directories found.")
        return 0
    print("AoC 2024 (Ago):")
    ok = all(run_day(d) for d in days)
    print("ALL PASS" if ok else "FAILURES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
