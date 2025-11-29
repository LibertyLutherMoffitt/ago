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
    | {"struct", "function", "void", "Any", "unknown", "range"}
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
    if list_type.endswith("_list"):
        return list_type[:-5]  # Remove "_list" suffix
    return "unknown"


def is_type_compatible(from_type: str, to_type: str) -> bool:
    """
    Check if from_type can be used where to_type is expected.
    This implements Ago's type coercion rules.
    """
    if from_type == to_type:
        return True
    if from_type == "Any" or to_type == "Any":
        return True
    if from_type == "unknown" or to_type == "unknown":
        return True
    if from_type in NUMERIC_TYPES and to_type in NUMERIC_TYPES:
        return True
    if from_type == "bool" and to_type in NUMERIC_TYPES:
        return True
    if from_type in NUMERIC_TYPES and to_type == "bool":
        return True
    if to_type == "string":
        return True
    if from_type == "string" and to_type in NUMERIC_TYPES:
        return True
    if from_type == "range" and to_type == "bool":
        return True
    if from_type == "range" and to_type == "int_list":
        return True
    if from_type in LIST_TYPES and to_type == "range":
        return True
    if from_type in LIST_TYPES and to_type in LIST_TYPES:
        from_elem = get_element_type(from_type)
        to_elem = get_element_type(to_type)
        return is_type_compatible(from_elem, to_elem)
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
            return "void"

        # String keywords
        if isinstance(expr, str):
            if expr == "verum":
                return "bool"
            if expr == "falsus":
                return "bool"
            if expr == "inanis":
                return "void"
            sym = self.sym_table.get_symbol(expr)
            if sym:
                return sym.type_t
            return "unknown"

        # AST nodes
        if hasattr(expr, "parseinfo") or isinstance(expr, dict):
            return self._infer_node_type(expr)

        # Lists
        if isinstance(expr, (list, tuple)):
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
                    return "void"
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

        # Identifier reference
        if d.get("id") is not None:
            name = str(d["id"])
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
                    if is_type_compatible(source_type, target_type):
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

        # Map/struct literal
        if d.get("mapstruct") is not None:
            return "struct"

        # Function call
        if d.get("call") is not None:
            return self._infer_call_type(d["call"])

        # Method chain
        if d.get("mchain") is not None:
            return "Any"

        # Indexed access
        if d.get("indexed") is not None:
            return self._infer_indexed_type(d["indexed"])

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

    def _infer_call_type(self, call_node: Any) -> str:
        """Infer return type of a function call."""
        d = to_dict(call_node)
        # call_stmt has structure: {recv, first, chain}
        first = d.get("first")
        if first:
            first_d = to_dict(first)
            func_name = first_d.get("func")
            if func_name:
                sym = self.sym_table.get_symbol(str(func_name))
                if sym and sym.category == "func" and sym.return_type:
                    return sym.return_type
        return "Any"

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
                        if base_type in LIST_TYPES:
                            return get_element_type(base_type)
                        if base_type == "string":
                            return "string"
        return "Any"

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

        if op in ("==", "!=", "<", ">", "<=", ">="):
            if left_type != right_type and not (
                left_type in NUMERIC_TYPES and right_type in NUMERIC_TYPES
            ):
                self.report_error(
                    f"{left_type} {op} {right_type} is an invalid comparision between types."
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
            return left_type if left_type != "void" else right_type

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

        return_type = "unknown"
        if func_name.endswith("o"):
            return_type = "function"
        else:
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
        self.current_function = func_symbol
        self.sym_table.increment_scope()

        # Declare parameters
        for param in param_symbols:
            param.category = "param"
            self.declare_symbol(param, ast)

        # Process body
        body = d.get("body")
        if body:
            self._process_block(body)

        # Exit function context
        self.sym_table.decrement_scope()
        self.current_function = previous_function

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
        actual_type = self.infer_expr_type(d.get("value"))

        self.check_type_compatible(
            actual_type, expected_type, f"declaration of '{var_name}'", ast
        )

        symbol = Symbol(name=var_name, type_t=expected_type, category="var")
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

        # Elif blocks
        elifs = d.get("elifs")
        if elifs:
            for elif_block in elifs:
                elif_d = to_dict(elif_block)
                elif_cond = elif_d.get("elif_cond")
                if elif_cond:
                    elif_cond_type = self.infer_expr_type(elif_cond)
                    self.check_type_compatible(
                        elif_cond_type, "bool", "elif condition", elif_block
                    )
                    self.sym_table.increment_scope()
                    self._process_block(elif_d.get("elif_body"))
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
        first = d.get("first")
        if first:
            first_d = to_dict(first)
            func_name = first_d.get("func")
            if func_name:
                func_name = str(func_name)
                sym = self.sym_table.get_symbol(func_name)
                if sym is None:
                    self.report_error(
                        f"Use of undeclared identifier '{func_name}'", call_node
                    )
                elif sym.category == "func":
                    self._validate_call_args(first, sym)

    def _validate_call_args(self, call_node, func_sym: Symbol):
        """Validate function call arguments."""
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

        expected_count = func_sym.num_of_params
        actual_count = len(args)

        if actual_count != expected_count:
            self.report_error(
                f"Function '{func_sym.name}' expects {expected_count} arguments, "
                f"but got {actual_count}",
                call_node,
            )
            return

        for i, (arg, expected_type) in enumerate(zip(args, func_sym.param_types)):
            actual_type = self.infer_expr_type(arg)
            if actual_type != expected_type:
                self.report_error(
                    f"argument {i + 1} of '{func_sym.name} is a {actual_type}, should be a {expected_type}'"
                )

    def _handle_return(self, ast):
        """Handle return statement."""
        if self.current_function is None:
            self.report_error("'redeo' (return) outside of function", ast)
            return

        d = to_dict(ast)
        # return_stmt is ["redeo", value] or value is directly available
        return_value = d.get("value")
        if return_value is not None:
            returned_type = self.infer_expr_type(return_value)
            expected_type = self.current_function.return_type
            if expected_type:
                if returned_type != expected_type:
                    self.report_error(
                        f"return statement is a {returned_type}, should be a {expected_type}'"
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
