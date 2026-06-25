import re

with open("src/AgoLsp.py", "r") as f:
    content = f.read()

# 1. Add _STDLIB_DOCS_CACHE and builtin_doc
docs_code = """
_STDLIB_DOCS_CACHE = {}

def builtin_doc(stem: str) -> str:
    if not _STDLIB_DOCS_CACHE:
        stdlib_path = _AGO_HOME / "docs" / "stdlib.md"
        if stdlib_path.exists():
            text = stdlib_path.read_text()
            current_func = None
            current_doc = []
            for line in text.split("\\n"):
                if line.startswith("#### "):
                    if current_func:
                        _STDLIB_DOCS_CACHE[current_func] = "\\n".join(current_doc).strip()
                    current_func = line[5:].strip()
                    current_doc = []
                elif current_func:
                    current_doc.append(line)
            if current_func:
                _STDLIB_DOCS_CACHE[current_func] = "\\n".join(current_doc).strip()
    return _STDLIB_DOCS_CACHE.get(stem, "")
"""

content = content.replace("def _load_prelude() -> str:", docs_code + "\n\ndef _load_prelude() -> str:")

# 2. Modify collect_definitions to capture docstrings
old_collect = """    lines = text.split("\\n")
    defs = []
    def add(name, line, kind):
        name = name.strip()
        if name and name.isidentifier():
            defs.append({"name": name, "stem": _stem(name), "line": line, "kind": kind})

    for i, line in enumerate(lines):
        # Variables
        m = _FAST_DECL_RE.match(line)"""

new_collect = """    lines = text.split("\\n")
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
            continue"""
content = content.replace(old_collect, new_collect)

old_func = """        # Functions
        m = _FAST_FUNC_RE.match(line)
        if m:
            add(m.group(1), i, "function")
            for p in m.group(2).split(","):
                add(p, i, "parameter")
            continue"""
new_func = """        # Functions
        m = _FAST_FUNC_RE.match(line)
        if m:
            sig = line.strip()
            if "{" in sig: sig = sig.split("{")[0].strip()
            doc_str = f"```ago\\n{sig}\\n```\\n\\n" + "\\n".join(current_doc) if current_doc else f"```ago\\n{sig}\\n```"
            add(m.group(1), i, "function", doc_str)
            for p in m.group(2).split(","):
                add(p, i, "parameter")
            current_doc = []
            continue"""
content = content.replace(old_func, new_func)

old_for = """        # For loops
        m = _FAST_FOR_RE.match(line)
        if m:
            for v in m.group(1).split(","):
                add(v, i, "variable")
            continue"""
new_for = """        # For loops
        m = _FAST_FOR_RE.match(line)
        if m:
            for v in m.group(1).split(","):
                add(v, i, "variable")
            current_doc = []
            continue"""
content = content.replace(old_for, new_for)

old_lambda = """        # Lambdas
        m = _FAST_LAMBDA_RE.match(line)
        if m:
            for p in m.group(1).split(","):
                add(p, i, "parameter")"""
new_lambda = """        # Lambdas
        m = _FAST_LAMBDA_RE.match(line)
        if m:
            for p in m.group(1).split(","):
                add(p, i, "parameter")
            current_doc = []
            continue

        if stripped:
            current_doc = []"""
content = content.replace(old_lambda, new_lambda)


# 3. Use builtin_doc in hover
old_hover_parts = """    parts = []
    if target_stem in _BUILTINS:
        parts.append(f"_builtin function: {target_stem}_")
    elif prelude_funcs:
        func = prelude_funcs[0]
        parts.append(f"_prelude function: {func['name']}_\\n\\n{func.get('doc', '')}")
    elif local_funcs:
        func = local_funcs[0]
        parts.append(f"_local function: {func['name']}_\\n\\nDefined at line {func['line'] + 1}")"""

new_hover_parts = """    parts = []
    if target_stem in _BUILTINS:
        bdoc = builtin_doc(target_stem)
        if bdoc:
            parts.append(f"_builtin function: {target_stem}_\\n\\n{bdoc}")
        else:
            parts.append(f"_builtin function: {target_stem}_")
    elif prelude_funcs:
        func = prelude_funcs[0]
        parts.append(f"_prelude function: {func['name']}_\\n\\n{func.get('doc', '')}")
    elif local_funcs:
        func = local_funcs[0]
        parts.append(f"_local function: {func['name']}_\\n\\n{func.get('doc', '')}\\n\\nDefined at line {func['line'] + 1}")"""
content = content.replace(old_hover_parts, new_hover_parts)

with open("src/AgoLsp.py", "w") as f:
    f.write(content)
