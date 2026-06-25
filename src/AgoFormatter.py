#!/usr/bin/env python3
"""Opinionated source formatter for Ago (`ago fmt`).

The goal is gofmt/black-style canonicalization: any *valid* program, however it
is spaced, formats to one canonical form. Ago's structure is brace/newline
based, so the formatter is token-driven — it never reorders or drops code, it
only re-spaces and re-indents — which keeps it safe and lets it preserve
comments and string contents verbatim.

Canonical style:
  * 4-space indentation, one level per open bracket;
  * one space around binary/assignment operators and after commas/`:` in maps;
  * `?`/`:` in ternaries are spaced (`a ? b : c`); range operators `..`/`.<`
    and member `.` are tight (`0.<n`, `x.foo`);
  * unary `-`/`+` bind to their operand (`-1`), `non` reads as a word (`non x`);
  * calls/indexes are tight (`f(a, b)`, `xs[0]`); map literals are unpadded
    (`{"a": 1}`) while inline blocks are padded (`{ redeo 1 }`);
  * `;` statement separators become newlines;
  * blank-line runs collapse to one, with a blank line between top-level
    definitions; the file ends in a single newline.

If anything about a file would cause the token stream to change (it never
should for valid input), the formatter falls back to a minimal whitespace-only
pass so it can never corrupt code.
"""

INDENT_UNIT = "    "

# Multi-character operators, longest first so the tokenizer is greedy.
_MULTI_OPS = [
    ":=", "==", "!=", ">=", "<=", "+=", "-=", "*=", "/=", "%=", "..", ".<", "?:",
]
_SINGLE = set("+-*/%=<>!&|^?:.,;()[]{}")

_KEYWORDS = {
    "si", "aluid", "pro", "dum", "in", "est", "et", "vel", "non", "des",
    "redeo", "frio", "pergo", "omitto", "discerne", "inporto", "tunc",
}
# Keywords that are values (operands) for spacing purposes.
_VALUE_KEYWORDS = {"verum", "falsus", "inanis", "id"}

_BINARY_SPACED = {
    "+", "-", "*", "/", "%", "==", "!=", "<", ">", "<=", ">=",
    "=", ":=", "+=", "-=", "*=", "/=", "%=", "&", "|", "^", "?:",
    "et", "vel", "est", "in",
}


class Tok:
    __slots__ = ("kind", "text")

    def __init__(self, kind, text):
        self.kind = kind
        self.text = text


def _tokenize_line(s: str):
    """Tokenize a single physical line (Ago strings/comments never span lines)."""
    toks = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c in " \t":
            i += 1
            continue
        if c == "#":
            toks.append(Tok("comment", s[i:]))
            break
        if c == '"':
            j = i + 1
            while j < n:
                if s[j] == "\\":
                    j += 2
                    continue
                if s[j] == '"':
                    j += 1
                    break
                j += 1
            toks.append(Tok("string", s[i:j]))
            i = j
            continue
        if c.isdigit() or (c == "." and i + 1 < n and s[i + 1].isdigit()):
            j = i
            while j < n and s[j].isdigit():
                j += 1
            if j < n and s[j] == "." and j + 1 < n and s[j + 1].isdigit():
                j += 1
                while j < n and s[j].isdigit():
                    j += 1
            toks.append(Tok("number", s[i:j]))
            i = j
            continue
        if c.isalpha() or c == "_":
            j = i
            while j < n and (s[j].isalnum() or s[j] == "_"):
                j += 1
            word = s[i:j]
            if word in _KEYWORDS:
                kind = "kw"
            elif word in _VALUE_KEYWORDS:
                kind = "value_kw"
            else:
                kind = "ident"
            toks.append(Tok(kind, word))
            i = j
            continue
        matched = None
        for op in _MULTI_OPS:
            if s.startswith(op, i):
                matched = op
                break
        if matched:
            toks.append(Tok("op", matched))
            i += len(matched)
            continue
        if c in _SINGLE:
            toks.append(Tok("op", c))
            i += 1
            continue
        # Unknown char (shouldn't happen for valid input): keep verbatim.
        toks.append(Tok("op", c))
        i += 1
    return toks


def _is_value(tok) -> bool:
    return tok is not None and tok.kind in ("ident", "number", "string", "value_kw")


def _is_closer(tok) -> bool:
    return tok is not None and tok.kind == "op" and tok.text in (")", "]", "}")


def _classify_brace(tokens, idx) -> str:
    """Classify a `{` at tokens[idx] as 'map' or 'block' by lookahead."""
    nxt = tokens[idx + 1] if idx + 1 < len(tokens) else None
    if nxt is None:
        return "block"  # `{` at end of line -> multi-line block
    if nxt.kind == "op" and nxt.text == "}":
        return "map"  # `{}` -> empty map
    after = tokens[idx + 2] if idx + 2 < len(tokens) else None
    if nxt.kind in ("string", "ident") and after is not None and after.kind == "op" and after.text == ":":
        return "map"
    return "block"


def _split_semicolons(tokens):
    """Split a token list at top-level `;` separators into separate statement
    segments. A `;` inside brackets (e.g. an inline `si x { a; b }`) is kept, so
    inline blocks stay intact and valid."""
    segments = []
    cur = []
    depth = 0
    for t in tokens:
        if t.kind == "op" and t.text in _OPEN:
            depth += 1
        elif t.kind == "op" and t.text in _CLOSE:
            depth = max(0, depth - 1)
        if t.kind == "op" and t.text == ";" and depth == 0:
            if cur:
                segments.append(cur)
            cur = []
        else:
            cur.append(t)
    if cur:
        segments.append(cur)
    return segments or [[]]


def _respace(tokens) -> str:
    """Render a single statement's tokens with canonical spacing."""
    out = []
    prev = None
    prev_unary = False
    # pending ternary `?` count and brace-kind stack for the line
    pending_q = 0
    brace_stack = []

    for idx, t in enumerate(tokens):
        space = _space_before(prev, t, prev_unary, pending_q, brace_stack)
        if space and out:
            out.append(" ")
        out.append(t.text)

        # update unary tracking: a '-'/'+' is unary if it can't be binary here
        if t.kind == "op" and t.text in ("-", "+"):
            prev_unary = not (_is_value(prev) or _is_closer(prev))
        else:
            prev_unary = False

        if t.kind == "op":
            if t.text == "?":
                pending_q += 1
            elif t.text == ":":
                if pending_q > 0:
                    pending_q -= 1
            elif t.text == "{":
                brace_stack.append(_classify_brace(tokens, idx))
            elif t.text == "}":
                if brace_stack:
                    brace_stack.pop()
        prev = t
    return "".join(out)


def _space_before(prev, cur, prev_unary, pending_q, brace_stack) -> bool:
    if prev is None:
        return False
    pt = prev.text if prev.kind == "op" else None
    ct = cur.text if cur.kind == "op" else None

    # After unary -/+ : tight to operand.
    if prev_unary:
        return False

    # No space after openers.
    if pt in ("(", "["):
        return False
    # Map brace: no padding right after `{` (map).
    if pt == "{" and brace_stack and brace_stack[-1] == "map":
        return False
    # No space before closers / comma.
    if ct in (")", "]", ",", ";"):
        return False
    # Map brace: no padding right before `}` (map).
    if ct == "}" and brace_stack and brace_stack[-1] == "map":
        return False

    # Member access and range operators are tight.
    if pt == "." or ct == ".":
        return False
    if pt in ("..", ".<") or ct in ("..", ".<"):
        return False

    # Call / index: tight `(`/`[` directly after a value or closer.
    if ct in ("(", "[") and (_is_value(prev) or _is_closer(prev)):
        return False

    # Comma: one space after (handled by default), none before (above).
    if pt == ",":
        return True

    # Ternary colon vs map colon.
    if ct == ":":
        return pending_q > 0  # spaced only for ternary
    if pt == ":":
        return True  # always a space after a colon (map `k: v` / ternary)

    # `?` ternary spaced.
    if ct == "?" or pt == "?":
        return True

    # Binary / assignment operators are spaced.
    if (cur.kind == "op" and ct in _BINARY_SPACED) or (prev.kind == "op" and pt in _BINARY_SPACED):
        return True
    if (cur.kind == "kw" and cur.text in _BINARY_SPACED) or (prev.kind == "kw" and prev.text in _BINARY_SPACED):
        return True

    # `non` keyword reads as a word.
    if (prev.kind == "kw" and prev.text == "non") or (cur.kind == "kw" and cur.text == "non"):
        return True

    # Space before an opening brace (block ` {`, or map after an operator).
    if ct == "{":
        return True
    if pt == "{":
        return True  # block padding `{ ... `
    if ct == "}":
        return True  # block padding ` }`

    # Keyword followed by something (si cond, redeo x, pro x ...).
    if prev.kind == "kw":
        return True
    # Something followed by a keyword (x in y, a et b handled above; `} aluid`).
    if cur.kind == "kw":
        return True

    # Two adjacent value-ish tokens (shouldn't normally happen) -> space.
    return True


# --- bracket-depth scanner (string/comment aware) for indentation ---

_OPEN = "([{"
_CLOSE = ")]}"


def _scan_brackets(code_line: str):
    leading_closes = 0
    counting_leading = True
    depth_delta = 0
    in_string = False
    i = 0
    n = len(code_line)
    while i < n:
        c = code_line[i]
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            counting_leading = False
            i += 1
            continue
        if c == "#":
            break
        if c in _OPEN:
            depth_delta += 1
            counting_leading = False
        elif c in _CLOSE:
            depth_delta -= 1
            if counting_leading:
                leading_closes += 1
        elif not c.isspace():
            counting_leading = False
        i += 1
    return leading_closes, depth_delta


def _canonical(text: str) -> str:
    out = []
    depth = 0
    for raw in text.split("\n"):
        stripped = raw.strip()
        if stripped == "":
            out.append("")
            continue
        leading_closes, delta = _scan_brackets(stripped)
        indent = max(0, depth - leading_closes)
        toks = _tokenize_line(stripped)
        for seg in _split_semicolons(toks):
            out.append(INDENT_UNIT * indent + _respace(seg))
        depth = max(0, depth + delta)

    # Collapse blank runs to one; ensure a blank line after each top-level block
    # close (`}` at column 0) so definitions are separated while doc-comments
    # stay glued to the definition that follows them.
    collapsed = []
    blank = False
    for line in out:
        if line == "":
            if not blank:
                collapsed.append("")
            blank = True
            continue
        if collapsed and collapsed[-1] == "}":
            collapsed.append("")
        collapsed.append(line)
        blank = False

    while collapsed and collapsed[0] == "":
        collapsed.pop(0)
    while collapsed and collapsed[-1] == "":
        collapsed.pop()
    return "\n".join(collapsed) + "\n"


def _token_signature(text: str):
    """Sequence of (kind, text) over the whole file, ignoring comments and the
    `;`/whitespace that the formatter is allowed to change. Used to prove the
    formatter only re-spaced and never altered code."""
    sig = []
    for line in text.split("\n"):
        for t in _tokenize_line(line):
            if t.kind == "comment":
                continue
            if t.kind == "op" and t.text == ";":
                continue
            sig.append((t.kind, t.text))
    return sig


def _comment_signature(text: str):
    return [
        t.text.rstrip()
        for line in text.split("\n")
        for t in _tokenize_line(line)
        if t.kind == "comment"
    ]


def format_source(text: str) -> str:
    """Return the canonical formatting of `text`, or a safe whitespace-only
    normalization if canonicalization would alter the token stream."""
    try:
        result = _canonical(text)
    except Exception:
        return _whitespace_only(text)
    # Safety: code tokens and comments must be preserved exactly.
    if (
        _token_signature(result) == _token_signature(text)
        and _comment_signature(result) == _comment_signature(text)
    ):
        return result
    return _whitespace_only(text)


def _whitespace_only(text: str) -> str:
    """Fallback: re-indent and tidy blank lines without touching token spacing."""
    out = []
    depth = 0
    for raw in text.split("\n"):
        stripped = raw.strip()
        if stripped == "":
            out.append("")
            continue
        leading_closes, delta = _scan_brackets(stripped)
        indent = max(0, depth - leading_closes)
        out.append(INDENT_UNIT * indent + stripped)
        depth = max(0, depth + delta)
    collapsed = []
    blank = False
    for line in out:
        if line == "":
            if not blank:
                collapsed.append("")
            blank = True
        else:
            collapsed.append(line)
            blank = False
    while collapsed and collapsed[0] == "":
        collapsed.pop(0)
    while collapsed and collapsed[-1] == "":
        collapsed.pop()
    return "\n".join(collapsed) + "\n"
