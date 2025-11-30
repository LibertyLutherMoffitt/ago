"""
Ago Semantic Checker - Performs semantic analysis on parsed Ago AST.

This module implements a Tatsu semantic actions class that validates:
- Variable declarations and usage
- Type compatibility
- Function definitions and calls
- Control flow (break/continue in loops, return in functions)
- Scope management
"""

from dataclasses import dataclass
from typing import Any, Optional

from src.AgoSymbolTable import Symbol, SymbolTable, SymbolTableError

# --- Type System Constants ---

NUMERIC_TYPES = {"int", "float"}
LIST_TYPES = {"int_list", "float_list", "bool_list", "string_list", "list_any"}
PRIMITIVE_TYPES = {"int", "float", "bool", "string"}
ALL_TYPES = (
    PRIMITIVE_TYPES
    | LIST_TYPES
    | {"struct", "function", "null", "Any", "unknown", "range"}
)

ENDING_TO_TYPE = {
    "a": "int",
    "ae": "float",
    "am": "bool",
    "aem": "int_list",
    "arum": "float_list",
    "as": "bool_list",
    "es": "string",
    "erum": "string_list",
    "u": "struct",
    "uum": "list_any",
    "e": "range",
    "o": "function",
    "i": "null",
    "ium": "Any",
}

# Sorted by length descending for proper matching
ENDINGS_BY_LENGTH = sorted(ENDING_TO_TYPE.keys(), key=len, reverse=True)


# --- Error Handling ---


@dataclass
class SemanticError:
    """Represents a semantic error found during analysis."""

    message: str
    line: Optional[int] = None
    col: Optional[int] = None
    node: Any = None

    def __str__(self) -> str:
        location = ""
        if self.line is not None and self.col is not None:
            location = f"(line {self.line}, col {self.col}) "
        elif self.line is not None:
            location = f"(line {self.line}) "
        return f"{location}{self.message}"


# --- Helper Functions ---


def get_node_location(node: Any) -> tuple[Optional[int], Optional[int]]:
    """Extract line and column from a Tatsu AST node if available."""
    if hasattr(node, "parseinfo") and node.parseinfo:
        info = node.parseinfo
        return (getattr(info, "line", None), getattr(info, "col", None))
    return (None, None)


def infer_type_from_name(name: str) -> Optional[str]:
    """
    Infer type from variable name suffix.
    Returns None if no valid suffix is found.
    """
    for ending in ENDINGS_BY_LENGTH:
        if name.endswith(ending):
            return ENDING_TO_TYPE[ending]
    return None


def get_element_type(list_type: str) -> str:
    """Get the element type of a list type."""
    if list_type == "list_any":
        return "Any"
    if list_type == "Any":
        return "Any"  # Indexing Any returns Any
    if list_type.endswith("_list"):
        return list_type[:-5]  # Remove "_list" suffix
    return "unknown"


def get_stem(name: str) -> Optional[str]:
    """Extract the stem from a variable name by removing the type suffix."""
    for ending in ENDINGS_BY_LENGTH:
        if name.endswith(ending) and len(name) > len(ending):
            return name[: -len(ending)]
    return None


def is_type_compatible(from_type: str, to_type: str) -> bool:
    """
    Check if from_type can be used where to_type is expected.
    Ago has strict typing - users can easily cast by changing variable name endings.
    The only implicit conversion is int -> float in arithmetic contexts.
    """
    if from_type == to_type:
        return True
    if from_type == "Any" or to_type == "Any":
        return True
    if from_type == "unknown" or to_type == "unknown":
        return True
    # int can be promoted to float (arithmetic promotion)
    if from_type == "int" and to_type == "float":
        return True
    # range is compatible with int_list (range produces ints)
    if from_type == "range" and to_type == "int_list":
        return True
    # list_any is compatible with specific list types
    if from_type == "list_any" and to_type in LIST_TYPES:
        return True
    if from_type in LIST_TYPES and to_type == "list_any":
        return True
    return False


def can_cast(from_type: str, to_type: str) -> bool:
    """
    Check if explicit cast via variable name ending is allowed.
    This is more permissive than is_type_compatible since the user
    is explicitly requesting a cast by using a different name ending.
    Based on Rust runtime casting rules in casting.rs.
    """
    if from_type == to_type:
        return True
    # Any type can be cast to/from anything
    if from_type == "Any" or to_type == "Any":
        return True
    if from_type == "unknown" or to_type == "unknown":
        return True
    # list_any elements are Any, so list_any is compatible with specific lists
    if from_type == "list_any" and to_type in LIST_TYPES:
        return True
    if from_type in LIST_TYPES and to_type == "list_any":
        return True
    # Numeric types can cast between each other (int, float)
    if from_type in NUMERIC_TYPES and to_type in NUMERIC_TYPES:
        return True
    # Bool can cast to/from numeric (bool->int: 0/1, int->bool: !=0)
    if from_type == "bool" and to_type in NUMERIC_TYPES:
        return True
    if from_type in NUMERIC_TYPES and to_type == "bool":
        return True
    # Anything can cast to string (stringify)
    if to_type == "string":
        return True
    # String can cast to numeric (parsing), bool (non-empty check), or string_list (chars)
    if from_type == "string" and to_type in NUMERIC_TYPES:
        return True
    if from_type == "string" and to_type == "bool":
        return True
    if from_type == "string" and to_type == "string_list":
        return True
    # Range can cast to int_list, bool, or string
    if from_type == "range" and to_type in ("int_list", "bool", "string"):
        return True
    # Lists can cast to int (length), bool (non-empty), string, or range
    if from_type in LIST_TYPES and to_type in ("int", "bool", "string", "range"):
        return True
    # Struct can cast to bool (non-empty) or string
    if from_type == "struct" and to_type in ("bool", "string"):
        return True
    # List types can cast between each other if elements can cast
    if from_type in LIST_TYPES and to_type in LIST_TYPES:
        from_elem = get_element_type(from_type)
        to_elem = get_element_type(to_type)
        return can_cast(from_elem, to_elem)
    return False


def result_type_for_arithmetic(left: str, right: str) -> str:
    """Determine the result type for arithmetic operations."""

    if left == "float" or right == "float":
        return "float"
    return "int"


def to_dict(node: Any) -> dict:
    """Convert an AST node to a dict for easier access."""
    if isinstance(node, dict):
        return node
    if hasattr(node, "items"):
        return dict(node)
    if hasattr(node, "__dict__"):
        return node.__dict__
    return {}


# --- Semantic Checker Class ---


class AgoSemanticChecker:
    """
    Tatsu semantic actions class for Ago language.
    """

    def __init__(self):
        self.sym_table = SymbolTable()
        self.errors: list[SemanticError] = []
        self.loop_depth: int = 0
        self.current_function: Optional[Symbol] = None
        # Track lambda context: None if not in lambda, else the Symbol for the lambda
        self.current_lambda: Optional[Symbol] = None
        # Track if current function has a return statement
        self.function_has_return: bool = False
        # Register stdlib functions
        self._register_stdlib()

    def _register_stdlib(self) -> None:
        """Register standard library functions in the symbol table."""
        # Format: (name, return_type, param_types_list)
        # param_types_list is a list of type strings
        stdlib_functions = [
            # Output functions
            ("dici", "null", ["string"]),  # prints string
            # Type inspection
            ("species", "string", ["Any"]),  # returns type name as string
            # File operations
            ("apertu", "struct", ["string"]),  # opens file, returns struct
            # Program control
            ("exei", "null", ["int"]),  # exits program
            # Comparison
            ("aequalam", "bool", ["Any", "Any"]),  # equality check
            # Collection operations
            ("claverum", "string_list", ["struct"]),  # get struct keys
            # Collection access/mutation
            ("get", "Any", ["Any", "Any"]),
            ("set", "null", ["Any", "Any", "Any"]),
            ("insero", "null", ["Any", "Any", "Any"]),
            ("removeo", "Any", ["Any", "Any"]),
            # Iteration
            ("into_iter", "list_any", ["Any"]),
        ]

        for func_name, return_type, param_types in stdlib_functions:
            func_sym = Symbol(
                name=func_name,
                type_t="function",
                category="func",
                num_of_params=len(param_types),
                param_types=param_types,
                return_type=return_type,
            )
            self.sym_table.add_symbol(func_sym)

    # --- Error Reporting ---

    def report_error(self, message: str, node: Any = None) -> None:
        """Record a semantic error."""
        line, col = get_node_location(node) if node else (None, None)
        self.errors.append(SemanticError(message, line, col, node))

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    # --- Type Inference ---

    def require_type_from_name(self, name: str, node: Any = None) -> str:
        """Get type from name suffix, reporting error if invalid."""
        type_t = infer_type_from_name(name)
        if type_t is None:
            self.report_error(
                f"Variable '{name}' does not have a valid type suffix. "
                f"Valid suffixes: {', '.join(ENDINGS_BY_LENGTH)}",
                node,
            )
            return "unknown"
        return type_t

    def check_type_compatible(
        self, actual: str, expected: str, context: str, node: Any = None
    ) -> bool:
        """Check type compatibility and report error if incompatible."""
        if not is_type_compatible(actual, expected):
            self.report_error(
                f"Type mismatch in {context}: expected '{expected}', got '{actual}'",
                node,
            )
            return False
        return True

    # --- Symbol Management ---

    def require_symbol(self, name: str, node: Any = None) -> Optional[Symbol]:
        """Look up a symbol, reporting error if not found."""
        sym = self.sym_table.get_symbol(name)
        if sym is None:
            self.report_error(f"Use of undeclared identifier '{name}'", node)
        return sym

    def declare_symbol(self, symbol: Symbol, node: Any = None) -> bool:
        """Declare a new symbol, reporting error if it already exists."""
        try:
            self.sym_table.add_symbol(symbol)
            return True
        except SymbolTableError as e:
            self.report_error(str(e), node)
            return False

    # --- Expression Type Inference ---

    def infer_expr_type(self, expr: Any) -> str:
        """Infer the type of an expression."""
        if expr is None:
            return "null"

        # String keywords
        if isinstance(expr, str):
            if expr == "verum":
                return "bool"
            if expr == "falsus":
                return "bool"
            if expr == "inanis":
                return "null"
            sym = self.sym_table.get_symbol(expr)
            if sym:
                return sym.type_t
            return "unknown"

        # AST nodes
        if hasattr(expr, "parseinfo") or isinstance(expr, dict):
            return self._infer_node_type(expr)

        # Lists and tuples
        if isinstance(expr, (list, tuple)):
            # Check for mapstruct pattern ['{', content, '}'] first
            if len(expr) >= 2 and expr[0] == "{" and expr[-1] == "}":
                return "struct"

            if len(expr) == 0:
                return "list_any"
            elem_types = set()
            for e in expr:
                if e is not None and e != "," and not isinstance(e, str):
                    elem_types.add(self.infer_expr_type(e))
            if len(elem_types) == 1:
                elem = elem_types.pop()
                return f"{elem}_list" if elem not in LIST_TYPES else "list_any"
            return "list_any"

        return "unknown"

    def _infer_node_type(self, node: Any) -> str:
        """Infer type from an AST node."""
        d = to_dict(node)

        # Unwrap 'value' wrapper
        if "value" in d and d.get("value") is not None:
            inner = d["value"]
            if isinstance(inner, str):
                if inner in ("verum", "falsus"):
                    return "bool"
                if inner == "inanis":
                    return "null"
            if isinstance(inner, dict) or hasattr(inner, "parseinfo"):
                return self._infer_node_type(inner)

        # Literals
        if d.get("int") is not None:
            return "int"
        if d.get("float") is not None:
            return "float"
        if d.get("str") is not None:
            return "string"
        if d.get("roman") is not None:
            return "int"

        # Handle 'id' keyword (IT token) - only valid inside single-param lambdas
        # Can appear as IT token, id key with value "id", or just string "id" in value wrapper
        if d.get("IT") is not None or (
            isinstance(d.get("id"), str) and d.get("id") == "id"
        ):
            return self._handle_id_keyword(node)

        # Check for 'id' as a plain string in value wrapper
        if "value" in d and d.get("value") == "id":
            return self._handle_id_keyword(node)

        # Identifier reference
        if d.get("id") is not None:
            name = str(d["id"])

            # Check for 'id' keyword variants (ida, ides, etc.) inside lambdas
            if name.startswith("id") and len(name) > 2:
                suffix = name[2:]
                if suffix in ENDING_TO_TYPE and self.current_lambda is not None:
                    return self._infer_id_cast_type(name, node)

            sym = self.sym_table.get_symbol(name)
            if sym:
                return sym.type_t

            # On-the-fly casting based on stem name
            # e.g., if 'xa' (int) is declared, 'xes' is a valid expression of type string.
            req_stem = None
            req_suffix_ending = None
            for ending in ENDINGS_BY_LENGTH:
                if name.endswith(ending):
                    if len(name) > len(ending):
                        req_stem = name[: -len(ending)]
                        req_suffix_ending = ending
                        break

            if req_stem is not None:
                visible_symbols = self.sym_table.get_all_visible_symbols()
                base_sym = None
                for sym_name in visible_symbols:
                    if sym_name.startswith(req_stem):
                        suffix_part = sym_name[len(req_stem) :]
                        if suffix_part in ENDING_TO_TYPE:
                            base_sym = visible_symbols[sym_name]
                            break

                if base_sym and req_suffix_ending is not None:
                    source_type = base_sym.type_t
                    target_type = ENDING_TO_TYPE[req_suffix_ending]
                    # Use can_cast for explicit casting via name endings
                    if can_cast(source_type, target_type):
                        return target_type
                    else:
                        self.report_error(
                            f"Cannot cast variable '{base_sym.name}' (type '{source_type}') "
                            f"to '{target_type}' using identifier '{name}'",
                            node,
                        )
                        return "unknown"

            self.report_error(f"Variable '{name}' not defined.", node)
            return "unknown"

        # Parenthesized expression
        if d.get("paren") is not None:
            paren = d["paren"]
            if hasattr(paren, "expr"):
                return self.infer_expr_type(paren.expr)
            if isinstance(paren, (list, tuple)) and len(paren) >= 2:
                return self.infer_expr_type(paren[1])
            return self.infer_expr_type(paren)

        # List literal
        if d.get("list") is not None:
            return self._infer_list_type(d["list"])

        # Map/struct literal - check for mapstruct key or list pattern ['{', ..., '}']
        if d.get("mapstruct") is not None:
            self._validate_mapstruct(d["mapstruct"], node)
            return "struct"

        # Check if this is a mapstruct as a list pattern
        mapstruct_content = self._get_mapstruct_content(node)
        if mapstruct_content is not None:
            self._validate_mapstruct_content(mapstruct_content, node)
            return "struct"

        # Function call
        if d.get("call") is not None:
            return self._infer_call_type(d["call"])

        # Method chain (a.b().c(d) = c(b(a), d))
        if d.get("mchain") is not None:
            return self._infer_method_chain_type(d["mchain"], node)

        # Indexed access
        if d.get("indexed") is not None:
            return self._infer_indexed_type(d["indexed"])

        # Struct field access (struct_indexed)
        if d.get("struct_indexed") is not None:
            return self._infer_struct_indexed_type(d["struct_indexed"])

        # Lambda
        if d.get("body") is not None and "name" not in d:
            return "function"

        # Binary operators
        if d.get("op") is not None and d.get("left") is not None:
            return self._infer_binary_op_type(d)

        # Unary operators
        if (
            d.get("op") is not None
            and d.get("right") is not None
            and d.get("left") is None
        ):
            return self._infer_unary_op_type(d)

        return "Any"

    def _infer_list_type(self, list_node: Any) -> str:
        """Infer type of a list literal."""
        items = []
        if hasattr(list_node, "__iter__") and not isinstance(list_node, str):
            items = [i for i in list_node if i is not None and i != ","]
        if not items:
            return "list_any"

        elem_types = {self.infer_expr_type(item) for item in items}

        if len(elem_types) == 1:
            elem = elem_types.pop()
            if elem in LIST_TYPES:
                return "list_any"
            return f"{elem}_list"
        return "list_any"

    def _get_list_items(self, value_node: Any) -> list:
        """Extract list items from a value node containing a list literal."""
        items = []

        def extract_items(node: Any) -> None:
            """Recursively extract items from list structure."""
            if node is None or isinstance(node, str) and node in (",", "[", "]"):
                return
            if isinstance(node, str):
                # String literals or identifiers
                items.append(node)
                return

            d = to_dict(node)

            # If this is a value wrapper with actual content, it's an item
            if "value" in d:
                inner = d["value"]
                # Check if it's a list literal (starts with "[")
                if isinstance(inner, (list, tuple)) and inner and inner[0] == "[":
                    # This is a list literal - extract its items
                    for elem in inner:
                        extract_items(elem)
                else:
                    # This is an actual value item
                    items.append(node)
                return

            # If this has op/right (unary) or left/op/right (binary), it's an expression item
            if d.get("op") is not None:
                items.append(node)
                return

            # If this is a list/tuple, recurse into it
            if isinstance(node, (list, tuple)):
                for elem in node:
                    extract_items(elem)

        d = to_dict(value_node)
        if "value" in d:
            extract_items(d["value"])
        else:
            extract_items(value_node)

        return items

    def _validate_list_element_types(
        self, value_node: Any, expected_list_type: str, var_name: str, ast: Any
    ) -> None:
        """Validate that list elements match the expected list element type."""
        if expected_list_type not in LIST_TYPES or expected_list_type == "list_any":
            return  # No validation needed for list_any

        expected_elem_type = get_element_type(expected_list_type)
        items = self._get_list_items(value_node)

        for i, item in enumerate(items):
            item_type = self.infer_expr_type(item)
            # Check if element type is compatible with expected element type
            if item_type != expected_elem_type and item_type != "unknown":
                # Only allow int -> float coercion (widening), not float -> int (narrowing)
                if not (item_type == "int" and expected_elem_type == "float"):
                    self.report_error(
                        f"List element {i} has type '{item_type}', "
                        f"but '{var_name}' expects '{expected_elem_type}' elements",
                        ast,
                    )

    def _is_mapstruct_list(self, node: Any) -> bool:
        """Check if node is a mapstruct in list form ['{', content, '}']."""
        return self._get_mapstruct_content(node) is not None

    def _get_mapstruct_content(self, node: Any) -> Any:
        """Get mapstruct content from node if it's a struct, else return None."""
        if isinstance(node, (list, tuple)) and len(node) >= 2:
            if node[0] == "{" and node[-1] == "}":
                # Content is between { and }
                return (
                    node[1:-1] if len(node) > 2 else node[1] if len(node) == 3 else None
                )
        # Also check wrapped in value
        d = to_dict(node) if not isinstance(node, (list, tuple, str)) else {}
        if "value" in d and d.get("value") is not None:
            inner = d["value"]
            if isinstance(inner, (list, tuple)) and len(inner) >= 2:
                if inner[0] == "{" and inner[-1] == "}":
                    return inner[1] if len(inner) == 3 else inner[1:-1]
        return None

    def _validate_mapstruct_content(self, content: Any, parent_node: Any) -> None:
        """Validate mapstruct content for key naming conventions."""
        if content is None:
            return

        # Content could be a list like ['key', ':', value] or nested
        if isinstance(content, (list, tuple)):
            i = 0
            while i < len(content):
                item = content[i]
                # Look for key:value patterns
                if isinstance(item, str) and item not in ("{", "}", ",", ":", "\n"):
                    # This might be a key - look for colon and value
                    if i + 2 < len(content) and content[i + 1] == ":":
                        key = item
                        value = content[i + 2]
                        self._validate_struct_key(key, value, parent_node)
                        i += 3
                        continue
                elif isinstance(item, (list, tuple)):
                    # Nested content - recurse
                    self._validate_mapstruct_content(item, parent_node)
                i += 1
        elif hasattr(content, "parseinfo") or isinstance(content, dict):
            d = to_dict(content)
            for k, v in d.items():
                if k not in ("parseinfo",) and isinstance(v, (list, tuple)):
                    self._validate_mapstruct_content(v, parent_node)

    def _find_function_by_stem(
        self, func_name: str
    ) -> tuple[Optional[Symbol], Optional[str]]:
        """
        Find a function by name or by stem.
        Returns (symbol, target_cast_type) where target_cast_type is None if exact match,
        or the type to cast to if found via stem.
        """
        # First try exact match
        sym = self.sym_table.get_symbol(func_name)
        if sym and (sym.category == "func" or sym.type_t == "function"):
            return (sym, None)

        # Try to find by stem - e.g., aae() should find aa()
        stem = get_stem(func_name)
        if stem:
            # Get the ending of the call name to determine cast type
            call_ending = None
            for ending in ENDINGS_BY_LENGTH:
                if func_name.endswith(ending) and len(func_name) > len(ending):
                    call_ending = ending
                    break

            # Look for functions with the same stem
            visible = self.sym_table.get_all_visible_symbols()
            for sym_name, sym in visible.items():
                if sym.category != "func" and sym.type_t != "function":
                    continue
                sym_stem = get_stem(sym_name)
                if sym_stem == stem and sym_name != func_name:
                    # Found a function with the same stem
                    if call_ending:
                        target_type = ENDING_TO_TYPE.get(call_ending)
                        if target_type:
                            return (sym, target_type)

        return (None, None)

    def _infer_call_type(self, call_node: Any) -> str:
        """Infer return type of a function call."""
        d = to_dict(call_node)
        # call_stmt has structure: {recv, first, chain}
        first = d.get("first")
        if first:
            first_d = to_dict(first)
            func_name = first_d.get("func")
            if func_name:
                func_name = str(func_name)
                sym, cast_type = self._find_function_by_stem(func_name)
                if sym:
                    if cast_type:
                        # Calling with different ending - return the cast type
                        return cast_type
                    elif sym.category == "func" and sym.return_type:
                        return sym.return_type
                    elif sym.type_t == "function" and sym.return_type:
                        # Lambda stored in variable
                        return sym.return_type
        return "Any"

    def _infer_method_chain_type(self, mchain_node: Any, parent_node: Any) -> str:
        """
        Infer type from method chain (e.g., a.b().c(d)).
        Method chaining semantics: a.b() = b(a), a.b().c(d) = c(b(a), d)
        """
        # Handle list format: [base_item, chain_items]
        if isinstance(mchain_node, (list, tuple)) and len(mchain_node) >= 2:
            base = mchain_node[0]
            chain = mchain_node[1] if len(mchain_node) > 1 else None
        else:
            d = to_dict(mchain_node)
            base = d.get("base")
            chain = d.get("chain")

        if not chain:
            # No chain, just return base type
            return self.infer_expr_type(base)

        # Track the current type through the chain
        current_type = self.infer_expr_type(base)

        # Process each method call in the chain
        if isinstance(chain, (list, tuple)):
            for item in chain:
                if item is None or item == ".":
                    continue

                # Handle different chain item formats:
                # 1. ['.', method_node] - list format
                # 2. {'method': method_node} or {'more': method_node} - dict format
                method = None
                if isinstance(item, (list, tuple)):
                    # List format: ['.', method_node]
                    for sub in item:
                        if sub != "." and sub is not None:
                            if isinstance(sub, dict) or hasattr(sub, "parseinfo"):
                                method = sub
                                break
                else:
                    item_d = to_dict(item) if not isinstance(item, str) else {}
                    method = item_d.get("method") or item_d.get("more")

                if method:
                    method_d = to_dict(method)
                    func_name = method_d.get("func")

                    if func_name:
                        func_name_str = str(func_name)
                        sym = self.sym_table.get_symbol(func_name_str)

                        if sym is None:
                            # Method not found directly
                            # Check if it's a bare type suffix (e.g., .es(), .a())
                            if func_name_str in ENDING_TO_TYPE:
                                # Valid type cast
                                current_type = ENDING_TO_TYPE[func_name_str]
                            else:
                                # Check if it's a stem+suffix that matches a function
                                suffix, stem = None, None
                                for ending in ENDINGS_BY_LENGTH:
                                    if func_name_str.endswith(ending) and len(
                                        func_name_str
                                    ) > len(ending):
                                        suffix = ending
                                        stem = func_name_str[: -len(ending)]
                                        break

                                if stem and suffix:
                                    # Look for a function with matching stem
                                    found_func = None
                                    for scope in self.sym_table.scopes.values():
                                        for name, s in scope.items():
                                            if s.category == "func":
                                                func_stem = None
                                                for e in ENDINGS_BY_LENGTH:
                                                    if name.endswith(e) and len(
                                                        name
                                                    ) > len(e):
                                                        func_stem = name[: -len(e)]
                                                        break
                                                if func_stem == stem:
                                                    found_func = s
                                                    break
                                        if found_func:
                                            break

                                    if found_func:
                                        # Valid stem-based function call with cast
                                        if suffix in ENDING_TO_TYPE:
                                            current_type = ENDING_TO_TYPE[suffix]
                                        elif found_func.return_type:
                                            current_type = found_func.return_type
                                        else:
                                            current_type = "Any"
                                    else:
                                        # No matching function found - error
                                        self.report_error(
                                            f"No function with stem '{stem}' found for '{func_name_str}'. "
                                            f"Use '.{suffix}()' for type casting.",
                                            parent_node,
                                        )
                                        current_type = "Any"
                                else:
                                    # Not a valid suffix pattern - might be stdlib
                                    inferred = infer_type_from_name(func_name_str)
                                    if inferred:
                                        current_type = inferred
                                    else:
                                        current_type = "Any"
                        elif sym.category == "func" or sym.type_t == "function":
                            # Validate the call - first arg should be compatible with current_type
                            self._validate_method_chain_call(
                                method, sym, current_type, parent_node
                            )
                            # Update current type to return type
                            # For method chaining, null/function returns are treated as Any
                            # since they can't meaningfully continue the chain
                            if sym.return_type and sym.return_type not in (
                                "null",
                                "function",
                            ):
                                current_type = sym.return_type
                            else:
                                current_type = "Any"
                        else:
                            self.report_error(
                                f"'{func_name_str}' is not callable in method chain",
                                parent_node,
                            )
                            current_type = "Any"

        return current_type

    def _validate_method_chain_call(
        self, call_node: Any, func_sym: Symbol, receiver_type: str, parent_node: Any
    ) -> None:
        """
        Validate a method chain call.
        In method chaining, the receiver becomes the first argument.
        If function has 0 params, we're lenient (legacy functions without receiver).
        """
        d = to_dict(call_node)
        args = []
        args_node = d.get("args")

        if args_node:
            args_d = to_dict(args_node)
            first = args_d.get("first")
            if first:
                args.append(first)
            rest = args_d.get("rest")
            if rest:
                for item in rest:
                    if isinstance(item, list) and len(item) >= 2:
                        args.append(item[1])
                    else:
                        item_d = to_dict(item)
                        if "expr" in item_d:
                            args.append(item_d["expr"])

        # In method chaining, receiver is implicitly the first argument
        # So actual_count = len(args) + 1 (for receiver)
        expected_count = func_sym.num_of_params
        actual_count = len(args) + 1  # +1 for receiver

        # Be lenient if function has 0 params (legacy function not designed for chaining)
        # Only validate if function expects at least 1 param (for receiver)
        if expected_count == 0:
            # No validation - function wasn't designed for method chaining
            return

        if actual_count != expected_count:
            self.report_error(
                f"Method '{func_sym.name}' expects {expected_count} argument(s) "
                f"(including receiver), but got {actual_count}",
                parent_node,
            )
            return

        # Validate receiver type (first param)
        if func_sym.param_types:
            first_param_type = func_sym.param_types[0]
            if not is_type_compatible(receiver_type, first_param_type):
                self.report_error(
                    f"Method '{func_sym.name}' expects first argument of type "
                    f"'{first_param_type}', but receiver has type '{receiver_type}'",
                    parent_node,
                )

        # Validate remaining arguments
        for i, (arg, expected_type) in enumerate(
            zip(args, func_sym.param_types[1:]), start=2
        ):
            actual_type = self.infer_expr_type(arg)
            if not is_type_compatible(actual_type, expected_type):
                self.report_error(
                    f"Argument {i} of '{func_sym.name}' expects type '{expected_type}', "
                    f"but got '{actual_type}'",
                    parent_node,
                )

    def _infer_indexed_type(self, indexed: Any) -> str:
        """Infer type of an indexed access."""
        if hasattr(indexed, "__iter__"):
            items = list(indexed)
            if items:
                base = items[0]
                if isinstance(base, str):
                    sym = self.sym_table.get_symbol(base)
                    if sym:
                        base_type = sym.type_t
                        if base_type == "list_any":
                            return "Any"  # Elements of list_any are Any
                        if base_type in LIST_TYPES:
                            return get_element_type(base_type)
                        if base_type == "string":
                            return "string"
                        if base_type == "Any":
                            return "Any"  # Indexing Any returns Any
        return "Any"

    def _infer_struct_indexed_type(self, struct_indexed: Any) -> str:
        """Infer type from struct field access (e.g., structu.fielda)."""
        d = to_dict(struct_indexed)

        # struct_indexed has: base, chain
        # chain contains field accesses via dot notation
        chain = d.get("chain")
        if chain:
            # Get the last field in the chain to determine final type
            last_field = None
            if isinstance(chain, (list, tuple)):
                for item in reversed(chain):
                    if item is not None and item != ".":
                        item_d = to_dict(item) if not isinstance(item, str) else {}
                        sub_item = item_d.get("sub_item") if item_d else item
                        if sub_item:
                            last_field = sub_item
                            break
                        elif isinstance(item, str) and not item.startswith('"'):
                            last_field = item
                            break

            if last_field:
                # If it's a string literal, return string
                if isinstance(last_field, str) and last_field.startswith('"'):
                    return "Any"
                # Infer type from field name suffix
                field_name = str(last_field)
                inferred = infer_type_from_name(field_name)
                if inferred:
                    return inferred

        return "Any"

    def _validate_mapstruct(self, mapstruct_node: Any, parent_node: Any) -> None:
        """Validate struct/map key naming conventions match value types."""
        if mapstruct_node is None:
            return

        # mapstruct is typically ['{', nl?, mapcontent?, nl?, '}']
        # We need to find the mapcontent
        content = None
        if isinstance(mapstruct_node, (list, tuple)):
            for item in mapstruct_node:
                if item is not None and item not in ("{", "}", "\n", "\r\n"):
                    if hasattr(item, "parseinfo") or isinstance(item, dict):
                        content = item
                        break
                    elif isinstance(item, list):
                        content = item
                        break
        else:
            content = mapstruct_node

        if content is None:
            return

        self._validate_mapcontent(content, parent_node)

    def _validate_mapcontent(self, content: Any, parent_node: Any) -> None:
        """Recursively validate mapcontent entries."""
        if content is None:
            return

        # mapcontent structure: [nl?, key, ':', value, (',', nl?, mapcontent)? | nl?]
        if isinstance(content, (list, tuple)):
            items = list(content)
            key = None
            value = None
            rest = None

            # Parse the content structure
            i = 0
            while i < len(items):
                item = items[i]
                if item is None or item in (",", ":", "\n", "\r\n"):
                    i += 1
                    continue
                if isinstance(item, str) and item.startswith('"'):
                    # String literal key - no naming convention needed
                    key = item
                    i += 1
                elif isinstance(item, str) and item not in ("{", "}", ",", ":"):
                    # Identifier key
                    key = item
                    i += 1
                elif hasattr(item, "parseinfo") or isinstance(item, dict):
                    if key is not None and value is None:
                        value = item
                    else:
                        # Could be nested mapcontent
                        rest = item
                    i += 1
                elif isinstance(item, list):
                    if key is not None and value is None:
                        value = item
                    else:
                        rest = item
                    i += 1
                else:
                    i += 1

            # Validate this key-value pair
            if key is not None and value is not None:
                self._validate_struct_key(key, value, parent_node)

            # Process rest recursively
            if rest is not None:
                self._validate_mapcontent(rest, parent_node)

        elif hasattr(content, "parseinfo") or isinstance(content, dict):
            d = to_dict(content)
            # Look for key-value patterns in the dict
            for k, v in d.items():
                if k not in ("parseinfo", "nl") and v is not None:
                    if isinstance(v, list):
                        self._validate_mapcontent(v, parent_node)

    def _validate_struct_key(self, key: Any, value: Any, parent_node: Any) -> None:
        """Validate that a struct key's naming matches the value's type."""
        # Only validate identifier keys, not string literals
        if isinstance(key, str) and key.startswith('"'):
            return  # String literal key, no convention needed

        key_str = str(key)
        expected_type = infer_type_from_name(key_str)

        if expected_type is None:
            self.report_error(
                f"Struct key '{key_str}' does not have a valid type suffix",
                parent_node,
            )
            return

        actual_type = self.infer_expr_type(value)

        if not is_type_compatible(actual_type, expected_type):
            self.report_error(
                f"Struct key '{key_str}' expects type '{expected_type}' but value has type '{actual_type}'",
                parent_node,
            )

    def _infer_binary_op_type(self, d: dict) -> str:
        """Infer result type of a binary operation."""
        op = d.get("op")
        left_type = self.infer_expr_type(d.get("left"))
        right_type = self.infer_expr_type(d.get("right"))

        if op in ("et", "vel"):
            if left_type != "bool" and left_type not in ("Any", "unknown"):
                self.report_error(
                    f"Left operand of '{op}' must be bool, got '{left_type}'", d
                )
            if right_type != "bool" and right_type not in ("Any", "unknown"):
                self.report_error(
                    f"Right operand of '{op}' must be bool, got '{right_type}'", d
                )
            return "bool"

        if op in ("&", "|", "^"):
            return "int"

        if op in ("==", "!="):
            # Equality can compare same types or numeric types with each other
            # Also allow comparing any type with null or Any
            types_compatible = (
                left_type == right_type
                or (left_type in NUMERIC_TYPES and right_type in NUMERIC_TYPES)
                or left_type == "null"
                or right_type == "null"
                or left_type == "Any"
                or right_type == "Any"
                or left_type == "unknown"
                or right_type == "unknown"
            )
            if not types_compatible:
                self.report_error(
                    f"{left_type} {op} {right_type} is an invalid comparison between types."
                )
            return "bool"

        if op == "est":
            # 'est' checks if two values are the same type - always returns bool
            # No type restrictions - any two values can be compared for type equality
            return "bool"

        if op == "in":
            # 'in' membership operator: needle in haystack
            # haystack must be a collection type (string, list, struct)
            valid_haystack = (
                right_type == "string"
                or right_type in LIST_TYPES
                or right_type == "struct"
                or right_type in ("Any", "unknown")
            )
            if not valid_haystack:
                self.report_error(
                    f"Cannot use 'in' operator with '{right_type}' - "
                    f"right operand must be string, list, or struct",
                    d,
                )
            # Validate needle type matches haystack element type
            if right_type == "string":
                if left_type != "string" and left_type not in ("Any", "unknown"):
                    self.report_error(
                        f"String membership requires string needle, got '{left_type}'",
                        d,
                    )
            elif right_type == "struct":
                if left_type != "string" and left_type not in ("Any", "unknown"):
                    self.report_error(
                        f"Struct key lookup requires string needle, got '{left_type}'",
                        d,
                    )
            elif right_type in LIST_TYPES:
                elem_type = get_element_type(right_type)
                if elem_type != "Any" and not is_type_compatible(left_type, elem_type):
                    self.report_error(
                        f"List membership: needle type '{left_type}' incompatible "
                        f"with list element type '{elem_type}'",
                        d,
                    )
            return "bool"

        if op in ("<", ">", "<=", ">="):
            # Ordering comparisons only work on: numeric vs numeric, string vs string
            # Based on Rust runtime - bool comparisons are NOT allowed
            valid_comparison = False
            if left_type in NUMERIC_TYPES and right_type in NUMERIC_TYPES:
                valid_comparison = True
            elif left_type == "string" and right_type == "string":
                valid_comparison = True
            elif left_type in ("Any", "unknown") or right_type in ("Any", "unknown"):
                valid_comparison = True

            if not valid_comparison:
                self.report_error(
                    f"Cannot compare {left_type} {op} {right_type}. "
                    f"Ordering comparisons only work on numeric or string types.",
                )
            return "bool"

        if op in ("+", "-", "*", "/", "%"):
            if op == "+" and (left_type == "string" or right_type == "string"):
                return "string"

            if left_type not in NUMERIC_TYPES and left_type not in ("Any", "unknown"):
                self.report_error(
                    f"'{left_type}' is not a numeric type, but you're trying to use it in a numeric expression.",
                    d,
                )
            if right_type not in NUMERIC_TYPES and right_type not in ("Any", "unknown"):
                self.report_error(
                    f"'{right_type}' is not a numeric type, but you're trying to use it in a numeric expression.",
                    d,
                )
            return result_type_for_arithmetic(left_type, right_type)

        if op in ("..", ".<"):
            if left_type != "int" and left_type not in ("Any", "unknown"):
                self.report_error(
                    f"Left operand of '{op}' must be int, got '{left_type}'", d
                )
            if right_type != "int" and right_type not in ("Any", "unknown"):
                self.report_error(
                    f"Right operand of '{op}' must be int, got '{right_type}'", d
                )
            return "range"

        if op == "?:":
            return left_type if left_type != "null" else right_type

        return "Any"

    def _infer_unary_op_type(self, d: dict) -> str:
        """Infer result type of a unary operation."""
        op = d.get("op")
        right_type = self.infer_expr_type(d.get("right"))

        if op == "non":
            if right_type != "bool" and right_type not in ("Any", "unknown"):
                self.report_error(
                    f"Unary 'non' requires bool operand, got '{right_type}'", d
                )
            return "bool"

        if op in ("+", "-"):
            if right_type not in NUMERIC_TYPES and right_type not in ("Any", "unknown"):
                self.report_error(
                    f"Unary '{op}' requires numeric operand, got '{right_type}'", d
                )
                return "unknown"
            return right_type

        return "Any"

    def _handle_id_keyword(self, node: Any) -> str:
        """
        Handle the 'id' keyword which references the single parameter of a lambda.
        The actual type accessed depends on the suffix: ida = int, ides = string, etc.
        """
        if self.current_lambda is None:
            self.report_error(
                "'id' keyword can only be used inside a lambda function", node
            )
            return "unknown"

        if self.current_lambda.num_of_params != 1:
            self.report_error(
                f"'id' keyword can only be used in lambdas with exactly 1 parameter, "
                f"but this lambda has {self.current_lambda.num_of_params} parameters",
                node,
            )
            return "unknown"

        # The base type is the lambda's single parameter type
        if self.current_lambda.param_types:
            return self.current_lambda.param_types[0]
        return "Any"

    def _infer_id_cast_type(self, name: str, node: Any) -> str:
        """
        Handle 'id' with suffix casting (e.g., 'ida' for int, 'ides' for string).
        The base 'id' accesses the parameter, and suffix converts it.
        """
        if self.current_lambda is None:
            self.report_error(
                f"'{name}' (id keyword variant) can only be used inside a lambda function",
                node,
            )
            return "unknown"

        if self.current_lambda.num_of_params != 1:
            self.report_error(
                f"'{name}' (id keyword variant) can only be used in lambdas with exactly 1 parameter",
                node,
            )
            return "unknown"

        # Extract suffix from name (remove 'id' prefix)
        if name.startswith("id") and len(name) > 2:
            suffix = name[2:]
            if suffix in ENDING_TO_TYPE:
                return ENDING_TO_TYPE[suffix]

        return "Any"

    # --- Main AST Processing ---

    def principio(self, ast):
        """Entry point - process the entire program."""
        if ast is None:
            return ast

        # ast is a list: [item, [[newlines]], more_items...]
        for item in ast:
            self._process_top_level_item(item)

        return ast

    def _process_top_level_item(self, item):
        """Process a top-level item."""
        if item is None:
            return
        if isinstance(item, str):
            # Could be break/continue at top level (error)
            if item == "frio":
                self._handle_break(item)
            elif item == "pergo":
                self._handle_continue(item)
            return
        if isinstance(item, list):
            # Nested list of items or newlines
            for sub in item:
                self._process_top_level_item(sub)
            return

        d = to_dict(item)

        # Method declaration: has name, params, body
        if "name" in d and "body" in d and "params" in d:
            self._handle_method_decl(item)
        # Statement
        else:
            self._process_statement(item)

    def _process_statement(self, stmt):
        """Process a single statement."""
        if stmt is None:
            return

        # String tokens
        if isinstance(stmt, str):
            if stmt == "frio":
                self._handle_break(stmt)
            elif stmt == "pergo":
                self._handle_continue(stmt)
            elif stmt == "omitto":
                pass  # Pass statement
            return

        # List of statements
        if isinstance(stmt, list):
            for sub in stmt:
                self._process_statement(sub)
            return

        d = to_dict(stmt)

        # Return statement: has return_stmt key
        if "return_stmt" in d:
            self._handle_return(stmt)
        # Declaration: has name and value, no target
        elif "name" in d and "value" in d and "target" not in d:
            self._handle_declaration(stmt)
        # Reassignment: has target and value
        elif "target" in d and "value" in d:
            self._handle_reassignment(stmt)
        # If statement
        elif "if_stmt" in d:
            self._handle_if(d["if_stmt"])
        elif "cond" in d and "then" in d:
            self._handle_if(stmt)
        # While statement
        elif "while_stmt" in d:
            self._handle_while(d["while_stmt"])
        elif "cond" in d and "body" in d and "iterator" not in d:
            self._handle_while(stmt)
        # For statement
        elif "for_stmt" in d:
            self._handle_for(d["for_stmt"])
        elif "iterator" in d and "iterable" in d:
            self._handle_for(stmt)
        # Call statement: has call key
        elif "call" in d:
            self._handle_call_stmt(d["call"])
        # Break/Continue as dict keys
        elif d.get("BREAK") is not None:
            self._handle_break(stmt)
        elif d.get("CONTINUE") is not None:
            self._handle_continue(stmt)

    def _handle_method_decl(self, ast):
        """Handle function declaration."""
        d = to_dict(ast)
        func_name = str(d["name"])

        # Function return type is inferred from name ending:
        # -o returns function/lambda, -i returns null, -a returns int, etc.
        return_type = self.require_type_from_name(func_name, ast)

        # Parse parameters
        param_symbols = self._parse_params(d.get("params"))
        param_types = [p.type_t for p in param_symbols]

        func_symbol = Symbol(
            name=func_name,
            type_t="function",
            category="func",
            return_type=return_type,
            param_types=param_types,
            num_of_params=len(param_symbols),
        )

        self.declare_symbol(func_symbol, ast)

        # Enter function context
        previous_function = self.current_function
        previous_has_return = self.function_has_return
        self.current_function = func_symbol
        self.function_has_return = False
        self.sym_table.increment_scope()

        # Declare parameters
        for param in param_symbols:
            param.category = "param"
            self.declare_symbol(param, ast)

        # Process body
        body = d.get("body")
        if body:
            self._process_block(body)

        # Check for missing return statement
        # Functions returning 'null' don't need explicit return (implicit null)
        if (
            return_type not in ("null", "unknown", "Any")
            and not self.function_has_return
        ):
            self.report_error(
                f"Function '{func_name}' expects to return '{return_type}' "
                f"but has no return statement",
                ast,
            )

        # Exit function context
        self.sym_table.decrement_scope()
        self.current_function = previous_function
        self.function_has_return = previous_has_return

    def _handle_lambda_decl(self, ast, expected_type: str = "function") -> Symbol:
        """Handle lambda declaration and return a Symbol representing it."""
        d = to_dict(ast)

        # Unwrap 'value' wrapper if present
        if "value" in d and d.get("value") is not None:
            inner = d["value"]
            if isinstance(inner, dict) or hasattr(inner, "parseinfo"):
                d = to_dict(inner)

        # Parse parameters
        param_symbols = self._parse_params(d.get("params"))
        param_types = [p.type_t for p in param_symbols]

        lambda_symbol = Symbol(
            name="<lambda>",
            type_t="function",
            category="lambda",
            return_type="Any",  # Lambdas have inferred return type
            param_types=param_types,
            num_of_params=len(param_symbols),
        )

        # Enter lambda context
        previous_lambda = self.current_lambda
        previous_function = self.current_function
        self.current_lambda = lambda_symbol
        self.current_function = lambda_symbol
        self.sym_table.increment_scope()

        # Declare parameters
        for param in param_symbols:
            param.category = "param"
            self.declare_symbol(param, ast)

        # Process body
        body = d.get("body")
        if body:
            self._process_block(body)

        # Exit lambda context
        self.sym_table.decrement_scope()
        self.current_lambda = previous_lambda
        self.current_function = previous_function

        return lambda_symbol

    def _is_lambda_decl(self, node: Any) -> bool:
        """Check if a node is a lambda declaration."""
        if node is None:
            return False
        d = to_dict(node)

        # Unwrap 'value' wrapper if present
        if "value" in d and d.get("value") is not None:
            inner = d["value"]
            if isinstance(inner, dict) or hasattr(inner, "parseinfo"):
                d = to_dict(inner)

        # Lambda has 'body' but no 'name' (unlike method_decl)
        return "body" in d and "name" not in d

    def _parse_params(self, params_node) -> list[Symbol]:
        """Parse parameter list into Symbol objects."""
        if params_node is None:
            return []

        d = to_dict(params_node)
        symbols = []

        first = d.get("first")
        if first:
            name = self._extract_identifier(first)
            if name:
                type_t = self.require_type_from_name(name, params_node)
                symbols.append(Symbol(name=name, type_t=type_t))

        rest = d.get("rest")
        if rest:
            for item in rest:
                item_d = to_dict(item) if not isinstance(item, list) else {}
                expr = item_d.get("expr") if item_d else None
                if expr is None and isinstance(item, list) and len(item) >= 2:
                    expr = item[1]
                if expr:
                    name = self._extract_identifier(expr)
                    if name:
                        type_t = self.require_type_from_name(name, params_node)
                        symbols.append(Symbol(name=name, type_t=type_t))

        return symbols

    def _extract_identifier(self, node) -> Optional[str]:
        """Extract identifier name from various node formats."""
        if isinstance(node, str):
            return node
        d = to_dict(node)
        if "id" in d:
            return str(d["id"])
        # Check value wrapper
        if "value" in d:
            inner = d["value"]
            if isinstance(inner, dict) or hasattr(inner, "parseinfo"):
                return self._extract_identifier(inner)
        return None

    def _process_block(self, block):
        """Process statements in a block."""
        if block is None:
            return

        d = to_dict(block)
        stmts = d.get("stmts")
        if stmts is None:
            return

        stmts_d = to_dict(stmts)
        first = stmts_d.get("first")
        if first:
            self._process_statement(first)

        rest = stmts_d.get("rest")
        if rest:
            for item in rest:
                if isinstance(item, list):
                    for sub in item:
                        if (
                            sub
                            and sub != "\n"
                            and not (isinstance(sub, str) and sub.strip() == "")
                        ):
                            self._process_statement(sub)
                elif item and item != "\n":
                    self._process_statement(item)

    def _handle_declaration(self, ast):
        """Handle variable declaration: name := value"""
        d = to_dict(ast)
        var_name = str(d["name"])
        expected_type = self.require_type_from_name(var_name, ast)
        value = d.get("value")

        # First, evaluate the RHS expression (before removing old variables with same stem)
        # This allows `xarum := xarum` to work - RHS refers to existing `xas` variable
        if self._is_lambda_decl(value):
            lambda_sym = self._handle_lambda_decl(value, expected_type)
            actual_type = "function"
            # Store lambda info in the variable symbol
            symbol = Symbol(
                name=var_name,
                type_t=expected_type,
                category="var",
                param_types=lambda_sym.param_types,
                num_of_params=lambda_sym.num_of_params,
                return_type=lambda_sym.return_type,
            )
        else:
            actual_type = self.infer_expr_type(value)
            # If actual_type is function (returned from another function),
            # use -1 to indicate unknown param count
            if actual_type == "function" or expected_type == "function":
                symbol = Symbol(
                    name=var_name,
                    type_t=expected_type,
                    category="var",
                    num_of_params=-1,  # Unknown param count
                )
            else:
                symbol = Symbol(name=var_name, type_t=expected_type, category="var")

        self.check_type_compatible(
            actual_type, expected_type, f"declaration of '{var_name}'", ast
        )

        # Validate list element types if assigning to a typed list
        if expected_type in LIST_TYPES and expected_type != "list_any":
            self._validate_list_element_types(value, expected_type, var_name, ast)

        # In Ago, only one variable per stem can exist in a scope.
        # If declaring a new variable with the same stem, remove the old one.
        # This happens AFTER evaluating the RHS so the old variable is available for casting.
        new_stem = get_stem(var_name)
        if new_stem:
            # Find and remove any existing variable with the same stem in current scope
            current_scope_symbols = self.sym_table.scopes.get(
                self.sym_table.current_scope, {}
            )
            for existing_name in list(current_scope_symbols.keys()):
                existing_sym = current_scope_symbols[existing_name]
                if existing_sym.category == "var":  # Only variables, not functions
                    existing_stem = get_stem(existing_name)
                    if existing_stem == new_stem and existing_name != var_name:
                        self.sym_table.remove_symbol_from_current_scope(existing_name)

        self.declare_symbol(symbol, ast)

    def _handle_reassignment(self, ast):
        """Handle variable reassignment: target = value"""
        d = to_dict(ast)
        var_name = str(d["target"])
        sym = self.require_symbol(var_name, ast)

        if sym is None:
            return

        target_type = sym.type_t

        # Handle indexed assignment
        if d.get("index") is not None:
            if target_type in LIST_TYPES:
                target_type = get_element_type(target_type)
            elif target_type == "string":
                target_type = "string"
            elif target_type == "struct":
                target_type = "Any"
            else:
                self.report_error(
                    f"Cannot index non-indexable type '{sym.type_t}'", ast
                )

        rhs_type = self.infer_expr_type(d.get("value"))
        self.check_type_compatible(
            rhs_type, target_type, f"assignment to '{var_name}'", ast
        )

    def _handle_if(self, ast):
        """Handle if statement."""
        d = to_dict(ast)

        cond_type = self.infer_expr_type(d.get("cond"))
        self.check_type_compatible(cond_type, "bool", "if condition", ast)

        self.sym_table.increment_scope()
        self._process_block(d.get("then"))
        self.sym_table.decrement_scope()

        # Elif blocks - can be list structure ['aluid', condition, body] or dict
        elifs = d.get("elifs")
        if elifs:
            for elif_block in elifs:
                elif_cond = None
                elif_body = None

                # Handle list structure: ['aluid', condition_expr, body_block]
                if isinstance(elif_block, (list, tuple)):
                    for item in elif_block:
                        if item == "aluid":
                            continue
                        if elif_cond is None and item is not None:
                            # First non-aluid item is the condition
                            if isinstance(item, dict) or hasattr(item, "parseinfo"):
                                elif_cond = item
                        elif elif_body is None and item is not None:
                            # Second non-aluid item is the body
                            if isinstance(item, dict) or hasattr(item, "parseinfo"):
                                elif_body = item
                else:
                    # Handle dict structure
                    elif_d = to_dict(elif_block)
                    elif_cond = elif_d.get("elif_cond")
                    elif_body = elif_d.get("elif_body")

                if elif_cond:
                    elif_cond_type = self.infer_expr_type(elif_cond)
                    self.check_type_compatible(
                        elif_cond_type, "bool", "elif condition", elif_block
                    )
                if elif_body:
                    self.sym_table.increment_scope()
                    self._process_block(elif_body)
                    self.sym_table.decrement_scope()

        # Else block
        else_frag = d.get("else_fragment")
        if else_frag:
            else_d = to_dict(else_frag)
            self.sym_table.increment_scope()
            self._process_block(else_d.get("else_body"))
            self.sym_table.decrement_scope()

    def _handle_while(self, ast):
        """Handle while loop."""
        d = to_dict(ast)

        cond_type = self.infer_expr_type(d.get("cond"))
        self.check_type_compatible(cond_type, "bool", "while condition", ast)

        self.loop_depth += 1
        self.sym_table.increment_scope()
        self._process_block(d.get("body"))
        self.sym_table.decrement_scope()
        self.loop_depth -= 1

    def _handle_for(self, ast):
        """Handle for loop."""
        d = to_dict(ast)

        iterable_type = self.infer_expr_type(d.get("iterable"))
        if iterable_type not in LIST_TYPES and iterable_type not in (
            "string",
            "range",
            "Any",
            "unknown",
        ):
            self.report_error(
                f"Cannot iterate over non-iterable type '{iterable_type}'", ast
            )

        if iterable_type in LIST_TYPES:
            iterator_type = get_element_type(iterable_type)
        elif iterable_type == "string":
            iterator_type = "string"
        elif iterable_type == "range":
            iterator_type = "int"
        else:
            iterator_type = "Any"

        iterator_name = self._extract_identifier(d.get("iterator"))
        if iterator_name:
            expected_type = self.require_type_from_name(iterator_name, ast)
            if expected_type != "unknown" and iterator_type != "Any":
                # For loops require a stricter type match than assignment.
                # The loop variable type must match the iterable's element type.
                if iterator_type != expected_type:
                    self.report_error(
                        f"Type mismatch in for loop iterator '{iterator_name}': expected '{expected_type}', got '{iterator_type}'",
                        ast,
                    )

        self.loop_depth += 1
        self.sym_table.increment_scope()

        if iterator_name:
            iter_symbol = Symbol(
                name=iterator_name, type_t=iterator_type, category="var"
            )
            self.declare_symbol(iter_symbol, ast)

        self._process_block(d.get("body"))

        self.sym_table.decrement_scope()
        self.loop_depth -= 1

    def _handle_call_stmt(self, call_node):
        """Handle call statement."""
        d = to_dict(call_node)

        # call_stmt structure: {recv, first, chain}
        recv = d.get("recv")
        first = d.get("first")

        if first:
            first_d = to_dict(first)
            func_name = first_d.get("func")
            if func_name:
                func_name = str(func_name)
                sym, cast_type = self._find_function_by_stem(func_name)

                if sym is None:
                    # Check if there's a non-callable symbol with this exact name
                    exact_sym = self.sym_table.get_symbol(func_name)
                    if (
                        exact_sym
                        and exact_sym.category != "func"
                        and exact_sym.type_t != "function"
                    ):
                        self.report_error(
                            f"'{func_name}' is not callable (type '{exact_sym.type_t}')",
                            call_node,
                        )
                    else:
                        self.report_error(
                            f"Use of undeclared identifier '{func_name}'", call_node
                        )
                elif sym.category == "func":
                    # For method chains, recv becomes the first argument
                    self._validate_call_args(first, sym, receiver=recv)
                    # If casting, validate the cast is possible
                    if cast_type and sym.return_type:
                        if not can_cast(sym.return_type, cast_type):
                            self.report_error(
                                f"Cannot cast return type '{sym.return_type}' of '{sym.name}' "
                                f"to '{cast_type}' when calling as '{func_name}'",
                                call_node,
                            )
                elif sym.type_t == "function":
                    # Variable holding a lambda - validate call args
                    self._validate_call_args(first, sym, receiver=recv)
                else:
                    self.report_error(
                        f"'{func_name}' is not callable (type '{sym.type_t}')",
                        call_node,
                    )

    def _validate_call_args(self, call_node, func_sym: Symbol, receiver=None):
        """Validate function call arguments (count and types)."""
        d = to_dict(call_node)
        args = []

        # If there's a receiver (method chain), it becomes the first argument
        if receiver is not None:
            args.append(receiver)

        args_node = d.get("args")
        if args_node:
            args_d = to_dict(args_node)
            first = args_d.get("first")
            if first:
                args.append(first)
            rest = args_d.get("rest")
            if rest:
                for item in rest:
                    if isinstance(item, list) and len(item) >= 2:
                        args.append(item[1])
                    else:
                        item_d = to_dict(item)
                        if "expr" in item_d:
                            args.append(item_d["expr"])

        expected_count = func_sym.num_of_params
        actual_count = len(args)

        # Skip validation if param count is unknown (-1 means function returned from another function)
        if expected_count < 0:
            return

        # Check argument count
        if actual_count != expected_count:
            self.report_error(
                f"'{func_sym.name}' expects {expected_count} argument(s), "
                f"but got {actual_count}",
                call_node,
            )
            return

        # Check argument types
        for i, (arg, expected_type) in enumerate(zip(args, func_sym.param_types)):
            actual_type = self.infer_expr_type(arg)
            if not is_type_compatible(actual_type, expected_type):
                self.report_error(
                    f"Argument {i + 1} of '{func_sym.name}' expects type '{expected_type}', "
                    f"but got '{actual_type}'",
                    call_node,
                )

    def _handle_return(self, ast):
        """Handle return statement."""
        if self.current_function is None:
            self.report_error("'redeo' (return) outside of function", ast)
            return

        # Mark that this function has a return statement
        self.function_has_return = True

        d = to_dict(ast)
        # return_stmt is ["redeo", value] or value is directly available
        return_value = d.get("value")
        if return_value is not None:
            returned_type = self.infer_expr_type(return_value)
            expected_type = self.current_function.return_type
            if expected_type and expected_type not in ("Any", "unknown"):
                if not is_type_compatible(returned_type, expected_type):
                    self.report_error(
                        f"Return type mismatch: expected '{expected_type}', "
                        f"but got '{returned_type}'",
                        ast,
                    )

    def _handle_break(self, ast):
        """Handle break statement."""
        if self.loop_depth <= 0:
            self.report_error("'frio' (break) outside of loop", ast)

    def _handle_continue(self, ast):
        """Handle continue statement."""
        if self.loop_depth <= 0:
            self.report_error("'pergo' (continue) outside of loop", ast)

    # --- Tatsu Semantic Action Stubs ---
    # These just return the AST unchanged; actual processing is done in principio

    def sub_principio(self, ast):
        return ast

    def statement(self, ast):
        return ast

    def declaration_stmt(self, ast):
        return ast

    def reassignment_stmt(self, ast):
        return ast

    def method_decl(self, ast):
        return ast

    def lambda_decl(self, ast):
        return ast

    def if_stmt(self, ast):
        return ast

    def while_stmt(self, ast):
        return ast

    def for_stmt(self, ast):
        return ast

    def call_stmt(self, ast):
        return ast

    def nodotcall_stmt(self, ast):
        return ast

    def return_stmt(self, ast):
        return ast

    def else_fragment(self, ast):
        return ast

    def block(self, ast):
        return ast

    def statement_list(self, ast):
        return ast

    def expression_list(self, ast):
        return ast

    def expression(self, ast):
        return ast

    def pa(self, ast):
        return ast

    def pb(self, ast):
        return ast

    def pc(self, ast):
        return ast

    def pd(self, ast):
        return ast

    def pe(self, ast):
        return ast

    def pf(self, ast):
        return ast

    def pg(self, ast):
        return ast

    def ph(self, ast):
        return ast

    def item(self, ast):
        return ast

    def list(self, ast):
        return ast

    def mapstruct(self, ast):
        return ast

    def mapcontent(self, ast):
        return ast

    def indexing(self, ast):
        return ast

    def identifier(self, ast):
        return ast

    def INTLIT(self, ast):
        return ast

    def FLOATLIT(self, ast):
        return ast

    def STR_LIT(self, ast):
        return ast

    def ROMAN_NUMERAL(self, ast):
        return ast

    def TRUE(self, ast):
        return ast

    def FALSE(self, ast):
        return ast

    def NULL(self, ast):
        return ast

    def IT(self, ast):
        return ast

    def BREAK(self, ast):
        return ast

    def CONTINUE(self, ast):
        return ast

    def PASS(self, ast):
        return ast

    def nl(self, ast):
        return ast

    def CR(self, ast):
        return ast
