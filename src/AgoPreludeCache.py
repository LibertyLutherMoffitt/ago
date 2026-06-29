"""Shared on-disk cache for the parsed prelude AST.

The parser is superlinear and the prelude dominates every parse (~4s). It never
changes between runs, so parse it once and cache the AST, keyed by a hash of the
prelude text and the parser source (so a grammar change invalidates it). The
user's program is parsed on its own and the two ASTs are concatenated, keeping
the user's line numbers their own.

Used by both the CLI (main.py) and the language server (AgoLsp.py); they share
the same cache file.
"""

from __future__ import annotations

import hashlib
import pickle
from pathlib import Path

from src.AgoParser import AgoParser

_CACHE_VERSION = 1


def cache_key(prelude_text: str) -> str:
    h = hashlib.sha256()
    h.update(f"v{_CACHE_VERSION}\n".encode())
    h.update(prelude_text.encode())
    try:
        import src.AgoParser as _agp

        h.update(Path(_agp.__file__).read_bytes())
    except OSError:
        pass
    return h.hexdigest()


def prelude_ast(prelude_text: str, cache_file: Path):
    """Return the parsed prelude AST (a tuple of top-level items), using the
    on-disk cache at `cache_file` when its key matches. Returns () for an empty
    prelude. Parsed without parseinfo: the prelude is trusted, and parseinfo
    holds tokenizer references that don't survive pickling."""
    if not prelude_text:
        return ()
    key = cache_key(prelude_text)
    try:
        with open(cache_file, "rb") as f:
            blob = pickle.load(f)
        if blob.get("key") == key:
            return blob["ast"]
    except (OSError, pickle.PickleError, EOFError, AttributeError, KeyError, TypeError):
        pass

    ast = AgoParser(parseinfo=False).parse(prelude_text)
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_file.with_suffix(".pkl.tmp")
        with open(tmp, "wb") as f:
            pickle.dump({"key": key, "ast": ast}, f, protocol=pickle.HIGHEST_PROTOCOL)
        tmp.replace(cache_file)
    except OSError:
        pass
    return ast
