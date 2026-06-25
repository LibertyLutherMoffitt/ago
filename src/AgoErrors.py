#!/usr/bin/env python3
"""Pretty, Rust-style diagnostics for the Ago CLI.

Renders an error with the message, a `file:line:col` location, the offending
source line, a caret underline, and an optional suggestion, e.g.:

    error: expected ')' to close this call
     --> hello.ago:3:14
      |
    3 |     dici("hi"
      |              ^ expected ')'
      = help: add a closing ')'

All inputs use 0-based line/col internally; display is 1-based.
"""

from __future__ import annotations

from typing import Optional


class Colors:
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


def _c(text: str, color: str, enabled: bool) -> str:
    return f"{color}{text}{Colors.END}" if enabled else text


def render_diagnostic(
    *,
    filename: str,
    source_lines: list[str],
    line: int,
    col: Optional[int] = None,
    length: int = 1,
    message: str,
    label: Optional[str] = None,
    suggestion: Optional[str] = None,
    note: Optional[str] = None,
    severity: str = "error",
    color: bool = True,
) -> str:
    """Build a formatted diagnostic string. `line`/`col` are 0-based."""
    sev_color = Colors.RED if severity == "error" else Colors.YELLOW
    out = []
    out.append(
        _c(f"{severity}:", sev_color + Colors.BOLD, color) + " " + _c(message, Colors.BOLD, color)
    )

    # Clamp the line into range.
    n = len(source_lines)
    if n == 0:
        return out[0] + "\n"
    line = max(0, min(line, n - 1))
    src = source_lines[line].replace("\t", " ")

    loc = f"{filename}:{line + 1}"
    if col is not None:
        loc += f":{col + 1}"
    out.append(" " + _c("-->", Colors.BLUE + Colors.BOLD, color) + " " + loc)

    gutter = str(line + 1)
    pad = " " * len(gutter)
    bar = _c("|", Colors.BLUE + Colors.BOLD, color)
    out.append(f"{pad} {bar}")
    out.append(f"{_c(gutter, Colors.BLUE + Colors.BOLD, color)} {bar} {src}")

    if col is not None:
        c = max(0, min(col, len(src)))
        underline = " " * c + _c("^" * max(1, length), sev_color + Colors.BOLD, color)
        tail = f" {_c(label, sev_color, color)}" if label else ""
        out.append(f"{pad} {bar} {underline}{tail}")
    elif label:
        out.append(f"{pad} {bar} {_c(label, sev_color, color)}")

    if suggestion:
        out.append(f"{pad} {_c('=', Colors.BLUE + Colors.BOLD, color)} {_c('help:', Colors.CYAN + Colors.BOLD, color)} {suggestion}")
    if note:
        out.append(f"{pad} {_c('=', Colors.BLUE + Colors.BOLD, color)} {_c('note:', Colors.CYAN + Colors.BOLD, color)} {note}")
    return "\n".join(out) + "\n"


def levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def closest(name: str, candidates, max_dist: int = 2) -> Optional[str]:
    """Nearest candidate to `name` within edit distance `max_dist` (for
    'did you mean ...?' suggestions)."""
    best = None
    best_d = max_dist + 1
    for cand in candidates:
        d = levenshtein(name, cand)
        if d < best_d:
            best_d = d
            best = cand
    return best if best_d <= max_dist else None
