#!/usr/bin/env python3
"""A Language Server for Ago.

Reuses the compiler's own parser and semantic checker (src/AgoParser.py,
src/AgoSemanticChecker.py) plus the formatter (src/AgoFormatter.py) to provide:

  * live diagnostics (parse + semantic errors) on open/change/save;
  * hover showing the type implied by an identifier's ending;
  * completion (in-scope vars/functions, prelude functions, Rust builtins);
  * stem-aware go-to-definition, find-references and rename (they treat
    `xa`/`xes`/`xerum` as one variable, renaming the stem and preserving each
    occurrence's ending);
  * document symbols (outline);
  * whole-document formatting (the same `ago fmt` canonicalization);
  * semantic tokens that color each identifier by its stem, so editors that
    support semantic highlighting get the same-variable-same-color behavior.

To resolve the standard-library prelude functions (which are written in Ago),
the prelude is prepended before analysis and the reported line numbers are
shifted back so diagnostics land on the user's own lines.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from pygls.lsp.server import LanguageServer
from lsprotocol import types as lsp

from src.AgoParser import AgoParser
from src.AgoSemanticChecker import AgoSemanticChecker, get_node_location
from src.AgoSemanticChecker import infer_type_from_name  # suffix -> type
from src.AgoCodeGenerator import to_dict, get_suffix_and_stem
from src.AgoFormatter import format_source
from src.AgoFormatter import _KEYWORDS as _FMT_KEYWORDS, _VALUE_KEYWORDS as _FMT_VALUE_KW

# Number of stem color buckets exposed as semantic-token types.
_STEM_BUCKETS = 16
_NONVALUE = set(_FMT_KEYWORDS) | set(_FMT_VALUE_KW)

# Rust-implemented builtins (always in scope). Mirrors the semantic checker's
# stdlib table plus the collection/regex helpers callable by name.
_BUILTINS = [
    "dici", "audies", "species", "apertu", "scribi", "exei", "aequalam",
    "ordina", "literes", "exemplium", "claverum", "valuum", "misceu",
    "congruam", "congruum", "get", "set", "inseri", "removium",
]

# Locate the prelude the same way the CLI does.
_AGO_HOME = Path(os.environ.get("AGO_HOME", Path(__file__).parent.parent))
_PRELUDE_FILE = _AGO_HOME / "stdlib" / "prelude.ago"

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


def _load_prelude() -> str:
    try:
        return _PRELUDE_FILE.read_text() + "\n"
    except OSError:
        return ""


def _full_line_range(lines: list[str], line: int) -> lsp.Range:
    """A range covering the whole of `line` (0-based) in `lines`."""
    line = max(0, min(line, len(lines) - 1)) if lines else 0
    end_char = len(lines[line]) if 0 <= line < len(lines) else 0
    return lsp.Range(
        start=lsp.Position(line=line, character=0),
        end=lsp.Position(line=line, character=end_char),
    )


def _parse_error_line(exc: Exception) -> int:
    """Best-effort extraction of a 0-based line number from a TatSu parse error.

    TatSu messages look like `(LINE:COL) message`, with 1-based line numbers.
    """
    m = re.search(r"\((\d+):(\d+)\)", str(exc))
    if m:
        return max(0, int(m.group(1)) - 1)
    info = getattr(exc, "tokenizer", None) or getattr(exc, "buf", None)
    line = getattr(getattr(exc, "pos", None), "line", None)
    if isinstance(line, int):
        return line
    return 0


def compute_diagnostics(text: str) -> list[lsp.Diagnostic]:
    """Parse + semantically check `text`, returning diagnostics on its lines."""
    prelude = _load_prelude()
    offset = prelude.count("\n")  # number of prelude lines prepended
    source = prelude + text
    user_lines = text.split("\n")

    parser = AgoParser(parseinfo=True)
    semantics = AgoSemanticChecker()
    diagnostics: list[lsp.Diagnostic] = []

    try:
        parser.parse(source, semantics=semantics)
    except Exception as exc:  # noqa: BLE001 - surface any parse failure
        line = _parse_error_line(exc) - offset
        if line < 0:
            line = 0
        diagnostics.append(
            lsp.Diagnostic(
                range=_full_line_range(user_lines, line),
                message=f"parse error: {exc}",
                severity=lsp.DiagnosticSeverity.Error,
                source="ago",
            )
        )
        return diagnostics

    for err in semantics.errors:
        line = err.line
        if line is None:
            node_line, _ = get_node_location(getattr(err, "node", None))
            line = node_line
        if line is None:
            line = offset  # unknown -> first user line
        user_line = line - offset
        if user_line < 0:
            # Error attributed to the prelude; skip (not the user's code).
            continue
        diagnostics.append(
            lsp.Diagnostic(
                range=_full_line_range(user_lines, user_line),
                message=str(err.message),
                severity=lsp.DiagnosticSeverity.Error,
                source="ago",
            )
        )
    return diagnostics


def _word_at(line_text: str, character: int) -> str | None:
    for m in _IDENT_RE.finditer(line_text):
        if m.start() <= character <= m.end():
            return m.group(0)
    return None


server = LanguageServer("ago-lsp", "0.1.0")


def _publish(ls: LanguageServer, uri: str) -> None:
    doc = ls.workspace.get_text_document(uri)
    diags = compute_diagnostics(doc.source)
    ls.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=uri, diagnostics=diags)
    )


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: lsp.DidOpenTextDocumentParams) -> None:
    _publish(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params: lsp.DidChangeTextDocumentParams) -> None:
    _publish(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(ls: LanguageServer, params: lsp.DidSaveTextDocumentParams) -> None:
    _publish(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(ls: LanguageServer, params: lsp.HoverParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    lines = doc.source.split("\n")
    pos = params.position
    if pos.line >= len(lines):
        return None
    word = _word_at(lines[pos.line], pos.character)
    if not word:
        return None
    ty = infer_type_from_name(word)
    parts = []
    if ty:
        parts.append(f"`{word}` — **{ty}** (from suffix)")
    if word in _BUILTINS:
        parts.append("_builtin function_")
    elif any(f["name"] == word for f in prelude_functions()):
        parts.append("_prelude function_")
    if not parts:
        return None
    return lsp.Hover(
        contents=lsp.MarkupContent(
            kind=lsp.MarkupKind.Markdown, value="  \n".join(parts)
        ),
        range=_full_line_range(lines, pos.line),
    )


# --------------------------------------------------------------------------
# Symbol collection (for completion and go-to-definition)
# --------------------------------------------------------------------------


def _stem(name: str) -> str:
    _, stem = get_suffix_and_stem(name)
    return stem if stem else name


_PARAMS_RE = re.compile(r"\(([^)]*)\)")


def _params_on_line(line_text: str) -> list:
    """Extract parameter names from a `des ...(a, b)` header line via its
    parenthesised list (robust and avoids walking parseinfo-laden nodes)."""
    m = _PARAMS_RE.search(line_text)
    if not m:
        return []
    out = []
    for part in m.group(1).split(","):
        name = part.strip()
        if name.isidentifier():
            out.append(name)
    return out


def _extra_names(d: dict) -> list:
    names = []
    extra = d.get("extra_names")
    if not extra:
        return names
    if not isinstance(extra, (list, tuple)):
        extra = [extra]

    def grab(x):
        if isinstance(x, str):
            return x if x != "," else None
        if isinstance(x, (list, tuple)):
            for y in x:
                r = grab(y)
                if r:
                    return r
            return None
        xd = to_dict(x)
        return str(xd["extra"]) if isinstance(xd, dict) and xd.get("extra") else None

    for e in extra:
        nm = grab(e)
        if nm:
            names.append(nm)
    return names


def collect_definitions(text: str) -> list[dict]:
    """Walk the user file's AST and collect variable/function/param definitions
    as {name, stem, line}. Parsed alone (no prelude) so lines are 0-based and
    in the user's own coordinates."""
    try:
        ast = AgoParser(parseinfo=True).parse(text, semantics=AgoSemanticChecker())
    except Exception:  # noqa: BLE001
        return []
    lines = text.split("\n")
    defs: list[dict] = []
    seen: set[int] = set()

    def add(name, line, kind):
        if name and name.isidentifier():
            defs.append({"name": name, "stem": _stem(name), "line": line or 0, "kind": kind})

    def line_of(node):
        pi = getattr(node, "parseinfo", None)
        return getattr(pi, "line", None) if pi is not None else None

    def visit(node):
        if node is None or isinstance(node, str):
            return
        if isinstance(node, (list, tuple)):
            for x in node:
                visit(x)
            return
        if id(node) in seen:
            return
        seen.add(id(node))
        d = to_dict(node)
        if not isinstance(d, dict):
            return
        line = line_of(node)
        hdr = lines[line] if line is not None and 0 <= line < len(lines) else ""
        # function definition: name + body + params
        if "name" in d and "body" in d and "params" in d:
            add(str(d["name"]), line, "function")
            for p in _params_on_line(hdr):
                add(p, line, "parameter")
        # declaration: name := value (no target)
        elif "name" in d and "value" in d and "target" not in d:
            add(str(d["name"]), line, "variable")
            for nm in _extra_names(d):
                add(nm, line, "variable")
        # lambda: body + params, no name
        if "body" in d and "name" not in d and "params" in d:
            for p in _params_on_line(hdr):
                add(p, line, "parameter")
        # for loop iterators
        if "iterator" in d and "iterable" in d:
            for key in ("iterator", "iterator2"):
                it = d.get(key)
                if isinstance(it, str):
                    add(it, line, "variable")
        # Recurse only into AST values, skipping the parseinfo payload.
        for key, v in d.items():
            if key == "parseinfo":
                continue
            visit(v)

    visit(ast)
    return defs


_PRELUDE_FUNC_RE = re.compile(r"^des\s+([A-Za-z_][A-Za-z_0-9]*)\s*\(")
_prelude_funcs_cache: list[dict] | None = None


def prelude_functions() -> list[dict]:
    """Prelude (`des`) functions as {name, stem, line, uri}. Cached."""
    global _prelude_funcs_cache
    if _prelude_funcs_cache is not None:
        return _prelude_funcs_cache
    out: list[dict] = []
    try:
        lines = _PRELUDE_FILE.read_text().split("\n")
        uri = _PRELUDE_FILE.as_uri()
        for i, line in enumerate(lines):
            m = _PRELUDE_FUNC_RE.match(line)
            if m:
                out.append({"name": m.group(1), "stem": _stem(m.group(1)), "line": i, "uri": uri})
    except OSError:
        pass
    _prelude_funcs_cache = out
    return out


@server.feature(lsp.TEXT_DOCUMENT_COMPLETION)
def completion(ls: LanguageServer, params: lsp.CompletionParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    items = {}
    for d in collect_definitions(doc.source):
        kind = (
            lsp.CompletionItemKind.Function
            if d["kind"] == "function"
            else lsp.CompletionItemKind.Variable
        )
        items[d["name"]] = lsp.CompletionItem(label=d["name"], kind=kind, detail=d["kind"])
    for f in prelude_functions():
        items.setdefault(
            f["name"],
            lsp.CompletionItem(
                label=f["name"], kind=lsp.CompletionItemKind.Function, detail="prelude"
            ),
        )
    for b in _BUILTINS:
        items.setdefault(
            b,
            lsp.CompletionItem(
                label=b, kind=lsp.CompletionItemKind.Function, detail="builtin"
            ),
        )
    return lsp.CompletionList(is_incomplete=False, items=list(items.values()))


def _name_range(lines: list[str], line: int, name: str) -> lsp.Range:
    col = lines[line].find(name) if 0 <= line < len(lines) else -1
    if col < 0:
        col = 0
    return lsp.Range(
        start=lsp.Position(line=line, character=col),
        end=lsp.Position(line=line, character=col + len(name)),
    )


@server.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def definition(ls: LanguageServer, params: lsp.DefinitionParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    lines = doc.source.split("\n")
    pos = params.position
    if pos.line >= len(lines):
        return None
    word = _word_at(lines[pos.line], pos.character)
    if not word:
        return None
    target_stem = _stem(word)

    # 1) Stem-aware match in the current file: the variable resolves regardless
    #    of the ending under the cursor (xes -> the `xa := ...` that defined it).
    candidates = [d for d in collect_definitions(doc.source) if d["stem"] == target_stem]
    if candidates:
        best = min(candidates, key=lambda d: d["line"])
        return lsp.Location(
            uri=params.text_document.uri,
            range=_name_range(lines, best["line"], best["name"]),
        )

    # 2) Fall back to a prelude function with the same stem.
    pf = [f for f in prelude_functions() if f["stem"] == target_stem]
    if pf:
        f = pf[0]
        plines = _PRELUDE_FILE.read_text().split("\n")
        return lsp.Location(uri=f["uri"], range=_name_range(plines, f["line"], f["name"]))

    return None


# --------------------------------------------------------------------------
# Identifier scanning (references / rename / semantic tokens)
# --------------------------------------------------------------------------


def _iter_identifiers(lines: list[str]):
    """Yield (line, start_col, name) for every identifier occurrence that is not
    a keyword (so we operate on variables/functions, not syntax)."""
    in_block_ctx = False  # (no multi-line strings in Ago, so per-line is fine)
    _ = in_block_ctx
    for ln, text in enumerate(lines):
        # Skip string and comment regions cheaply.
        i = 0
        n = len(text)
        while i < n:
            c = text[i]
            if c == "#":
                break
            if c == '"':
                i += 1
                while i < n and text[i] != '"':
                    if text[i] == "\\":
                        i += 1
                    i += 1
                i += 1
                continue
            if c.isalpha() or c == "_":
                m = _IDENT_RE.match(text, i)
                name = m.group(0)
                if name not in _NONVALUE:
                    yield ln, i, name
                i = m.end()
                continue
            i += 1


def _stem_bucket(name: str) -> int:
    s = _stem(name)
    h = 5381
    for ch in s:
        h = (h * 33 + ord(ch)) % 2147483648
    return h % _STEM_BUCKETS


# --------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------


@server.feature(lsp.TEXT_DOCUMENT_FORMATTING)
def formatting(ls: LanguageServer, params: lsp.DocumentFormattingParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    new_text = format_source(doc.source)
    if new_text == doc.source:
        return []
    lines = doc.source.split("\n")
    end = lsp.Position(line=len(lines) - 1, character=len(lines[-1]))
    whole = lsp.Range(start=lsp.Position(line=0, character=0), end=end)
    return [lsp.TextEdit(range=whole, new_text=new_text)]


# --------------------------------------------------------------------------
# Document symbols (outline)
# --------------------------------------------------------------------------


@server.feature(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbol(ls: LanguageServer, params: lsp.DocumentSymbolParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    lines = doc.source.split("\n")
    syms = []
    for d in collect_definitions(doc.source):
        if d["kind"] == "parameter":
            continue
        kind = (
            lsp.SymbolKind.Function
            if d["kind"] == "function"
            else lsp.SymbolKind.Variable
        )
        rng = _name_range(lines, d["line"], d["name"])
        syms.append(
            lsp.DocumentSymbol(
                name=d["name"], kind=kind, range=rng, selection_range=rng
            )
        )
    return syms


# --------------------------------------------------------------------------
# References & rename (stem-aware)
# --------------------------------------------------------------------------


@server.feature(lsp.TEXT_DOCUMENT_REFERENCES)
def references(ls: LanguageServer, params: lsp.ReferenceParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    lines = doc.source.split("\n")
    pos = params.position
    if pos.line >= len(lines):
        return None
    word = _word_at(lines[pos.line], pos.character)
    if not word:
        return None
    target = _stem(word)
    locs = []
    for ln, col, name in _iter_identifiers(lines):
        if _stem(name) == target:
            locs.append(
                lsp.Location(
                    uri=params.text_document.uri,
                    range=lsp.Range(
                        start=lsp.Position(line=ln, character=col),
                        end=lsp.Position(line=ln, character=col + len(name)),
                    ),
                )
            )
    return locs


@server.feature(lsp.TEXT_DOCUMENT_RENAME)
def rename(ls: LanguageServer, params: lsp.RenameParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    lines = doc.source.split("\n")
    pos = params.position
    if pos.line >= len(lines):
        return None
    word = _word_at(lines[pos.line], pos.character)
    if not word:
        return None
    old_stem = _stem(word)
    new_stem = _stem(params.new_name)
    edits = []
    for ln, col, name in _iter_identifiers(lines):
        suffix, stem = get_suffix_and_stem(name)
        if stem == old_stem:
            replacement = new_stem + (suffix or "")
            edits.append(
                lsp.TextEdit(
                    range=lsp.Range(
                        start=lsp.Position(line=ln, character=col),
                        end=lsp.Position(line=ln, character=col + len(name)),
                    ),
                    new_text=replacement,
                )
            )
    if not edits:
        return None
    return lsp.WorkspaceEdit(changes={params.text_document.uri: edits})


# --------------------------------------------------------------------------
# Semantic tokens: color each identifier by its stem (cross-editor stem colors)
# --------------------------------------------------------------------------

_SEMANTIC_LEGEND = lsp.SemanticTokensLegend(
    token_types=[f"agoStem{i}" for i in range(_STEM_BUCKETS)],
    token_modifiers=[],
)


@server.feature(lsp.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL, _SEMANTIC_LEGEND)
def semantic_tokens(ls: LanguageServer, params: lsp.SemanticTokensParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    lines = doc.source.split("\n")
    data = []
    prev_line = 0
    prev_col = 0
    for ln, col, name in _iter_identifiers(lines):
        ttype = _stem_bucket(name)
        delta_line = ln - prev_line
        delta_col = col - prev_col if delta_line == 0 else col
        data.extend([delta_line, delta_col, len(name), ttype, 0])
        prev_line, prev_col = ln, col
    return lsp.SemanticTokens(data=data)


def main() -> None:
    server.start_io()


if __name__ == "__main__":
    main()
