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



_STDLIB_DOCS_CACHE = {}
_RUST_DOCS_CACHE: dict = {}
_RUST_SRC_DIR = _AGO_HOME / "src" / "rust" / "src"
_RUST_FN_RE = re.compile(r"^\s*pub fn ([a-z_][A-Za-z0-9_]*)\s*[(<]")


def _rust_builtin_docs() -> dict:
    """Map each Rust stdlib `pub fn` to its `///` (or `//`) doc comment, scanned
    from the runtime source so builtins are documented from one place (the same
    model as prelude `#` docstrings)."""
    if _RUST_DOCS_CACHE:
        return _RUST_DOCS_CACHE
    if not _RUST_SRC_DIR.is_dir():
        return _RUST_DOCS_CACHE
    for rs in sorted(_RUST_SRC_DIR.glob("*.rs")):
        try:
            lines = rs.read_text().split("\n")
        except OSError:
            continue
        for i, line in enumerate(lines):
            m = _RUST_FN_RE.match(line)
            if not m:
                continue
            name = m.group(1)
            if name in _RUST_DOCS_CACHE:
                continue
            doc = []
            j = i - 1
            while j >= 0:
                s = lines[j].strip()
                if s.startswith("///"):
                    doc.append(s[3:].strip())
                elif s.startswith("//"):
                    doc.append(s[2:].strip())
                elif s.startswith("#["):
                    pass  # attribute (e.g. #[inline]) — keep walking up
                else:
                    break
                j -= 1
            if doc:
                _RUST_DOCS_CACHE[name] = "\n".join(reversed(doc)).strip()
    return _RUST_DOCS_CACHE


def builtin_doc(name: str) -> str:
    """Documentation for a builtin, by exact name: the Rust `///` docstring if
    present, else the docs/stdlib.md section."""
    rd = _rust_builtin_docs().get(name)
    if rd:
        return rd
    if not _STDLIB_DOCS_CACHE:
        stdlib_path = _AGO_HOME / "docs" / "stdlib.md"
        if stdlib_path.exists():
            text = stdlib_path.read_text()
            current_func = None
            current_doc = []
            for line in text.split("\n"):
                if line.startswith("#### "):
                    if current_func:
                        _STDLIB_DOCS_CACHE[current_func] = "\n".join(current_doc).strip()
                    current_func = line[5:].strip()
                    current_doc = []
                elif current_func:
                    current_doc.append(line)
            if current_func:
                _STDLIB_DOCS_CACHE[current_func] = "\n".join(current_doc).strip()
    return _STDLIB_DOCS_CACHE.get(name, "")


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


def _prelude_ast():
    """Cached prelude AST, shared with the CLI (parsed once, keyed on disk)."""
    from src.AgoPreludeCache import prelude_ast

    cache_dir = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "ago"
    return prelude_ast(_load_prelude(), cache_dir / "prelude_ast.pkl")


def compute_diagnostics(text: str) -> list[lsp.Diagnostic]:
    """Parse + semantically check `text`, returning diagnostics on its lines.

    The user's code is parsed on its own (fast) and concatenated with the cached
    prelude AST, so user line numbers are their own (no offset to subtract) and
    the slow prelude parse happens at most once per prelude change."""
    user_lines = text.split("\n")
    parser = AgoParser(parseinfo=True)
    diagnostics: list[lsp.Diagnostic] = []

    try:
        user_ast = parser.parse(text)
    except Exception as exc:  # noqa: BLE001 - surface any parse failure
        line = _parse_error_line(exc)  # already user-relative now
        diagnostics.append(
            lsp.Diagnostic(
                range=_full_line_range(user_lines, line),
                message=f"parse error: {exc}",
                severity=lsp.DiagnosticSeverity.Error,
                source="ago",
            )
        )
        return diagnostics

    combined = tuple(_prelude_ast()) + tuple(user_ast)
    semantics = AgoSemanticChecker()
    semantics.principio(combined)

    for err in semantics.errors:
        node = getattr(err, "node", None)
        node_line, _ = get_node_location(node)
        if node_line is None:
            if node is not None:
                # Node from the prelude (no parseinfo) — not the user's code.
                continue
            line = 0  # unlocatable -> first user line
        else:
            line = node_line  # user nodes carry their own line
        diagnostics.append(
            lsp.Diagnostic(
                range=_full_line_range(user_lines, line),
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


def _word_info_at(line_text: str, character: int):
    for m in _IDENT_RE.finditer(line_text):
        if m.start() <= character <= m.end():
            return m.group(0), m.start(), m.end()
    return None, None, None


server = LanguageServer("ago-lsp", "0.1.0")


import asyncio
import sys

_diag_process = None
_diag_task = None

async def _publish(ls: LanguageServer, uri: str) -> None:
    if uri.endswith("prelude.ago"):
        ls.text_document_publish_diagnostics(
            lsp.PublishDiagnosticsParams(uri=uri, diagnostics=[])
        )
        return

    doc = ls.workspace.get_text_document(uri)
    source = doc.source

    global _diag_task
    if _diag_task is not None and not _diag_task.done():
        _diag_task.cancel()

    async def task():
        try:
            await asyncio.sleep(0.5)
            
            global _diag_process
            if _diag_process is not None and _diag_process.returncode is None:
                try:
                    _diag_process.kill()
                except ProcessLookupError:
                    pass

            script_path = _AGO_HOME / "src" / "check_syntax.py"
            _diag_process = await asyncio.create_subprocess_exec(
                sys.executable, str(script_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await _diag_process.communicate(input=source.encode('utf-8'))
            
            if stdout:
                import json
                try:
                    data = json.loads(stdout.decode('utf-8'))
                    diags = []
                    for item in data:
                        d = lsp.Diagnostic(
                            range=lsp.Range(
                                start=lsp.Position(line=item["line"], character=item["col"]),
                                end=lsp.Position(line=item["end_line"], character=item["end_col"])
                            ),
                            message=item["msg"]
                        )
                        diags.append(d)
                    ls.text_document_publish_diagnostics(
                        lsp.PublishDiagnosticsParams(uri=uri, diagnostics=diags)
                    )
                except Exception:
                    pass
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    _diag_task = asyncio.create_task(task())


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: LanguageServer, params: lsp.DidOpenTextDocumentParams) -> None:
    await _publish(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
async def did_change(ls: LanguageServer, params: lsp.DidChangeTextDocumentParams) -> None:
    await _publish(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
async def did_save(ls: LanguageServer, params: lsp.DidSaveTextDocumentParams) -> None:
    await _publish(ls, params.text_document.uri)


@server.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(ls: LanguageServer, params: lsp.HoverParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    lines = doc.source.split("\n")
    pos = params.position
    if pos.line >= len(lines):
        return None
    word, start_col, end_col = _word_info_at(lines[pos.line], pos.character)
    if not word:
        return None
        
    keywords = {
        "si", "aluid", "pro", "in", "dum", "discerne",
        "redeo", "frio", "pergo", "omitto", "des", "vel",
        "et", "est", "non", "verum", "falsus", "inanis", "id",
        "inporto", "tunc"
    }
    if word in keywords:
        return lsp.Hover(contents=lsp.MarkupContent(kind=lsp.MarkupKind.Markdown, value=f"**keyword:** `{word}`"))
        
    target_stem = _stem(word)
    prelude_funcs = [f for f in prelude_functions() if f["stem"] == target_stem]
    local_funcs = [d for d in collect_definitions(doc.source) if d["stem"] == target_stem and d["kind"] == "function"]
    local_vars = [d for d in collect_definitions(doc.source) if d["stem"] == target_stem and d["kind"] == "variable"]

    parts = []
    if word in _BUILTINS:
        # Builtins are matched by their exact name (they don't use the
        # suffix-cast convention), and documented from their Rust source.
        bdoc = builtin_doc(word)
        if bdoc:
            parts.append(f"_builtin function: {word}_\n\n{bdoc}")
        else:
            parts.append(f"_builtin function: {word}_")
    elif prelude_funcs:
        func = prelude_funcs[0]
        parts.append(f"_prelude function: {func['name']}_\n\n{func.get('doc', '')}")
    elif local_funcs:
        func = local_funcs[0]
        parts.append(f"_local function: {func['name']}_\n\n{func.get('doc', '')}\n\nDefined at line {func['line'] + 1}")
    elif local_vars:
        func = local_vars[0]
        ty = infer_type_from_name(word) or "unknown type"
        parts.append(f"`{word}` — **{ty}** variable\n\nDefined at line {func['line'] + 1}")
    else:
        ty = infer_type_from_name(word)
        if ty:
            parts.append(f"`{word}` — **{ty}** (from suffix)")

    if not parts:
        return None
    return lsp.Hover(
        contents=lsp.MarkupContent(
            kind=lsp.MarkupKind.Markdown, value="  \n".join(parts)
        ),
        range=lsp.Range(
            start=lsp.Position(line=pos.line, character=start_col),
            end=lsp.Position(line=pos.line, character=end_col),
        ),
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


_FAST_DECL_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z_0-9]*(?:\s*,\s*[A-Za-z_][A-Za-z_0-9]*)*)\s*:=")
_FAST_FUNC_RE = re.compile(r"^\s*des\s+([A-Za-z_][A-Za-z_0-9]*)\s*\((.*?)\)")
_FAST_FOR_RE = re.compile(r"^\s*pro\s+([A-Za-z_][A-Za-z_0-9]*(?:\s*,\s*[A-Za-z_][A-Za-z_0-9]*)*)\s+in")
_FAST_LAMBDA_RE = re.compile(r"^\s*des\s*\((.*?)\)")

def collect_definitions(text: str) -> list[dict]:
    """Fast regex-based definition collection to avoid slow Tatsu backtracking on invalid ASTs."""
    lines = text.split("\n")
    defs = []
    def add(name, line, kind, doc=""):
        name = name.strip()
        if name and name.isidentifier():
            defs.append({"name": name, "stem": _stem(name), "line": line, "kind": kind, "doc": doc})

    current_doc = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            current_doc.append(stripped.lstrip("#").strip())
            continue

        # Variables
        m = _FAST_DECL_RE.match(line)
        if m:
            for v in m.group(1).split(","):
                add(v, i, "variable")
            current_doc = []
            continue
        if m:
            for v in m.group(1).split(","):
                add(v, i, "variable")
            continue
        # Functions
        m = _FAST_FUNC_RE.match(line)
        if m:
            sig = line.strip()
            if "{" in sig: sig = sig.split("{")[0].strip()
            doc_str = f"```ago\n{sig}\n```\n\n" + "\n".join(current_doc) if current_doc else f"```ago\n{sig}\n```"
            add(m.group(1), i, "function", doc_str)
            for p in m.group(2).split(","):
                add(p, i, "parameter")
            current_doc = []
            continue
        # For loops
        m = _FAST_FOR_RE.match(line)
        if m:
            for v in m.group(1).split(","):
                add(v, i, "variable")
            current_doc = []
            continue
        # Lambdas
        m = _FAST_LAMBDA_RE.match(line)
        if m:
            for p in m.group(1).split(","):
                add(p, i, "parameter")
            current_doc = []
            continue

        if stripped:
            current_doc = []
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
        doc_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#"):
                doc_lines.append(stripped.lstrip("#").strip())
            else:
                m = _PRELUDE_FUNC_RE.match(line)
                if m:
                    sig = line.strip()
                    if "{" in sig:
                        sig = sig.split("{")[0].strip()
                    doc = f"```ago\n{sig}\n```\n\n" + "\n".join(doc_lines)
                    out.append({"name": m.group(1), "stem": _stem(m.group(1)), "line": i, "uri": uri, "doc": doc})
                if stripped:
                    doc_lines = []
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


def _function_spans(lines: list[str]) -> list[tuple[int, int, str]]:
    """(start_line, end_line, name) for every brace-delimited block.

    This covers ``des`` function bodies *and* ``pro``/``dum``/``si`` blocks, so a
    variable declared inside a block — e.g. a ``pro`` loop variable — is scoped
    to that block and is not resolved from outside it. Brace matching skips
    strings and comments so the spans reflect real nesting. The name is only the
    enclosing function's (when known) and is otherwise unused by selection.
    """
    spans: list[tuple[int, int, str]] = []
    stack: list[dict] = []          # open braces, tagged with a function name
    pending: str | None = None      # function name awaiting its opening brace
    for ln, text in enumerate(lines):
        m = _FAST_FUNC_RE.match(text)
        if m:
            pending = m.group(1)
        i, n = 0, len(text)
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
            if c == "{":
                stack.append({"name": pending or "", "start": ln})
                pending = None
            elif c == "}":
                if stack:
                    top = stack.pop()
                    spans.append((top["start"], ln, top["name"]))
            i += 1
    # Close any blocks left open by incomplete/being-edited code.
    while stack:
        top = stack.pop()
        spans.append((top["start"], len(lines) - 1, top["name"]))
    return spans


def _innermost_scope(spans: list[tuple[int, int, str]], line: int):
    """The deepest block span containing ``line``, or None for top level."""
    best = None
    for s, e, name in spans:
        if s <= line <= e and (best is None or (s >= best[0] and e <= best[1])):
            best = (s, e, name)
    return best


def _select_definition(candidates: list[dict], spans, cursor_line: int) -> dict:
    """Choose the same-stem definition nearest to the cursor by scope.

    Walks outward from the cursor's enclosing function to top level; the first
    scope that owns a matching definition wins. Within that scope the most
    recent definition at or before the cursor is preferred (falling back to the
    earliest one declared later in the same scope, e.g. for forward references).
    """
    containing = [s for s in spans if s[0] <= cursor_line <= s[1]]
    containing.sort(key=lambda s: (s[0], -s[1]), reverse=True)  # innermost first
    chain = containing + [None]  # None == top-level scope

    for d in candidates:
        d["_scope"] = _innermost_scope(spans, d["line"])

    for scope in chain:
        key = None if scope is None else (scope[0], scope[1])
        in_scope = [
            d for d in candidates
            if (d["_scope"][:2] if d["_scope"] else None) == key
        ]
        if in_scope:
            before = [d for d in in_scope if d["line"] <= cursor_line]
            if before:
                return max(before, key=lambda d: d["line"])
            return min(in_scope, key=lambda d: d["line"])

    return min(candidates, key=lambda d: d["line"])


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

    # 1) Resolve within the current file. Prefer a definition whose name matches
    #    the word under the cursor exactly; only when there is none fall back to
    #    stem matching (xes -> the `xa := ...` that defined it). Either way, pick
    #    the definition in the nearest enclosing block scope, so a block-local
    #    name (e.g. a `pro` loop variable) never wins from outside its block.
    same_stem = [d for d in collect_definitions(doc.source) if d["stem"] == target_stem]
    if same_stem:
        spans = _function_spans(lines)
        exact = [d for d in same_stem if d["name"] == word]
        pool = exact if exact else same_stem
        best = _select_definition(pool, spans, pos.line)
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


def _resolved_def_line(name: str, ln: int, defs: list[dict], spans) -> int | None:
    """The definition line that an occurrence of `name` at line `ln` resolves to,
    using the same rule as go-to-definition (exact-name first, then stem, scoped
    to the nearest enclosing block). Lets references/rename stay within scope."""
    same = [d for d in defs if d["stem"] == _stem(name)]
    if not same:
        return None
    exact = [d for d in same if d["name"] == name]
    pool = exact if exact else same
    return _select_definition([dict(d) for d in pool], spans, ln)["line"]


def _scoped_occurrences(lines: list[str], word: str, cursor_line: int):
    """Yield (line, col, name) for every identifier that resolves to the same
    definition as `word` at `cursor_line` — i.e. the *same variable*, respecting
    block scope, not merely the same stem."""
    src = "\n".join(lines)
    defs = collect_definitions(src)
    spans = _function_spans(lines)
    target_stem = _stem(word)
    target_line = _resolved_def_line(word, cursor_line, defs, spans)
    if target_line is None:
        return
    for ln, col, name in _iter_identifiers(lines):
        if _stem(name) != target_stem:
            continue
        if _resolved_def_line(name, ln, defs, spans) == target_line:
            yield ln, col, name


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
    locs = []
    for ln, col, name in _scoped_occurrences(lines, word, pos.line):
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
    new_stem = _stem(params.new_name)
    edits = []
    for ln, col, name in _scoped_occurrences(lines, word, pos.line):
        suffix, _stem_part = get_suffix_and_stem(name)
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
