"""
Ago Code Generator - Generates Rust code from parsed Ago AST.

This module walks the AST produced by the parser and generates
equivalent Rust code using the ago_stdlib runtime library.
"""

from typing import Any, Optional


def to_dict(node: Any) -> dict:
    """Convert an AST node to a dict for easier access."""
    if isinstance(node, dict):
        return node
    if hasattr(node, "items"):
        return dict(node)
    if hasattr(node, "__dict__"):
        return node.__dict__
    return {}


# Type suffix to Rust TargetType mapping
ENDING_TO_TARGET_TYPE = {
    "a": "Int",
    "ae": "Float",
    "am": "Bool",
    "aem": "IntList",
    "arum": "FloatList",
    "as": "BoolList",
    "es": "String",
    "erum": "StringList",
    "u": "Struct",
    "uum": "ListAny",
    "e": "Range",
    "ium": "Any",
}

# Sorted by length descending for proper matching
ENDINGS_BY_LENGTH = sorted(ENDING_TO_TARGET_TYPE.keys(), key=len, reverse=True)

# Standard library functions (take &AgoType parameters)
STDLIB_FUNCTIONS = {
    "dici",
    "apertu",
    "species",
    "scribi",
    "audies",
    "exei",
    "aequalam",
    "claverum",
    "add",
    "subtract",
    "multiply",
    "divide",
    "modulo",
    "greater_than",
    "greater_equal",
    "less_than",
    "less_equal",
    "and",
    "or",
    "not",
    "bitwise_and",
    "bitwise_or",
    "bitwise_xor",
    "slice",
    "sliceto",
    "contains",
    "elvis",
    "unary_minus",
    "unary_plus",
    "get",
    "set",
    "inseri",
    "removium",
    "into_iter",
}

# Stdlib functions that mutate their first argument (need &mut)
MUTATING_STDLIB_FUNCTIONS = {
    "set",
    "inseri",
    "removium",
}


def get_suffix_and_stem(name: str) -> tuple[Optional[str], Optional[str]]:
    """Get the type suffix and stem from a variable name."""
    for ending in ENDINGS_BY_LENGTH:
        if name.endswith(ending) and len(name) > len(ending):
            return ending, name[: -len(ending)]
    return None, None


# Mapping from Ago type suffixes to Rust TargetType enum
ENDING_TO_RUST_TARGET = {
    "a": "Int",
    "ae": "Float",
    "am": "Bool",
    "es": "String",
    "aem": "IntList",
    "arum": "FloatList",
    "as": "BoolList",
    "erum": "StringList",
    "u": "Struct",
    "uum": "ListAny",
    "ium": "Any",
    # These don't have direct TargetType equivalents
    # "e": "Range",
    # "o": "Function",
    # "i": "Null",
}


class AgoCodeGenerator:
    """
    Generates Rust code from an Ago AST.
    """

    def __init__(self):
        self.indent_level = 0
        self.output_lines: list[str] = []
        # Track declared variables for mutability
        self.declared_vars: set[str] = set()
        # Track functions for forward declarations
        self.functions: list[str] = []
        # Track user-defined function names for stem-based resolution
        self.user_functions: set[str] = set()
        # Track generated lambdas
        self.lambdas: list[str] = []
        self.lambda_counter = 0
        # Counter for temp variables
        self.temp_counter = 0

    def _get_temp_counter(self) -> int:
        """Get a unique temp variable counter."""
        count = self.temp_counter
        self.temp_counter += 1
        return count

    def indent(self) -> str:
        """Return current indentation string."""
        return "    " * self.indent_level

    def _generate_variable_ref(self, name: str) -> str:
        """
        Generate a variable reference, with casting if needed.

        If `name` is directly declared, return `name.clone()`.
        If `name` has a suffix that differs from a declared variable with same stem,
        generate a cast: `base_var.clone().as_type(TargetType::X)`.
        Special case: `id` variants (ides, ida, etc.) in lambdas.
        Special case: bare `id` without suffix works like `idium` (Any type).
        """
        # Direct reference to declared variable
        if name in self.declared_vars:
            return f"{name}.clone()"

        # Special case: bare `id` without suffix (works like idium - Any type)
        if name == "id" and "id" in self.declared_vars:
            return "id.clone()"

        # Check for variable casting via suffix
        suffix, stem = get_suffix_and_stem(name)
        if stem and suffix:
            # Special case: `id` variants in lambdas (ides, ida, idam, etc.)
            if stem == "id" and "id" in self.declared_vars:
                target_type = ENDING_TO_TARGET_TYPE.get(suffix)
                if target_type:
                    return f"id.clone().as_type(TargetType::{target_type})"

            # Look for a variable with the same stem but different suffix
            for declared_var in self.declared_vars:
                decl_suffix, decl_stem = get_suffix_and_stem(declared_var)
                if decl_stem == stem and decl_suffix != suffix:
                    # Found a base variable - generate cast
                    target_type = ENDING_TO_TARGET_TYPE.get(suffix)
                    if target_type:
                        return (
                            f"{declared_var}.clone().as_type(TargetType::{target_type})"
                        )

        # Fall back to direct reference (may be undefined, will error at Rust compile)
        return f"{name}.clone()"

    def emit(self, line: str) -> None:
        """Emit a line of code."""
        self.output_lines.append(f"{self.indent()}{line}")

    def emit_raw(self, line: str) -> None:
        """Emit a line without indentation."""
        self.output_lines.append(line)

    def generate(self, ast: Any) -> str:
        """Generate Rust code from the AST and return as string."""
        # Emit prelude
        self._emit_prelude()

        # First pass: collect lambdas (they need to be defined before user functions)
        self._collect_lambdas(ast)

        # Emit lambda functions (before user functions)
        if self.lambdas:
            for lambda_code in self.lambdas:
                self.emit_raw("")
                self.emit_raw(lambda_code)

        # Second pass: collect and emit user function declarations
        self._collect_functions(ast)

        # Generate main function wrapper
        self.emit_raw("")
        self.emit_raw("fn main() {")
        self.indent_level += 1

        # Process the AST
        self._process_principio(ast)

        self.indent_level -= 1
        self.emit_raw("}")

        return "\n".join(self.output_lines)

    def _collect_lambdas(self, ast: Any, seen: set = None) -> None:
        """First pass to collect all lambda declarations."""
        if seen is None:
            seen = set()
        if ast is None:
            return
        # Use id() to track nodes we've already visited
        node_id = id(ast)
        if node_id in seen:
            return
        seen.add(node_id)

        if isinstance(ast, (list, tuple)):
            for item in ast:
                self._collect_lambdas(item, seen)
            return
        if isinstance(ast, dict) or hasattr(ast, "parseinfo"):
            d = to_dict(ast)
            # Check if this is a lambda (has body but no name)
            # Exclude loops (while has 'cond', for has 'iterator'/'iterable')
            is_lambda = (
                d.get("body") is not None
                and "name" not in d
                and "cond" not in d  # not a while loop
                and "iterator" not in d  # not a for loop
                and "iterable" not in d  # not a for loop
            )
            if is_lambda:
                self._register_lambda(d)
                # Don't recurse into lambda body (it's already processed)
                return
            # Recurse
            for key, val in d.items():
                if val is not None:
                    self._collect_lambdas(val, seen)

    def _register_lambda(self, d: dict) -> int:
        """Register a lambda and return its ID."""
        lambda_id = self.lambda_counter
        self.lambda_counter += 1

        params = self._parse_params(d.get("params"))

        # Save current state
        old_lines = self.output_lines
        old_indent = self.indent_level
        old_declared = self.declared_vars.copy()
        old_in_lambda = getattr(self, "_in_id_lambda", False)

        # Set up for lambda generation
        self.output_lines = []
        self.indent_level = 1

        # Emit function header
        self.output_lines.append(
            f"fn __lambda_{lambda_id}(args: &[AgoType]) -> AgoType {{"
        )

        if params:
            # Explicit params - unpack from args array
            for i, p in enumerate(params):
                self.emit(f"let {p} = args.get({i}).cloned().unwrap_or(AgoType::Null);")
                self.declared_vars.add(p)
            self._in_id_lambda = False
        else:
            # No explicit params - this is an `id` lambda
            # Create the implicit `id` parameter from args[0]
            self.emit("let id = args.get(0).cloned().unwrap_or(AgoType::Null);")
            self.declared_vars.add("id")
            self._in_id_lambda = True

        # Generate body - for lambdas, the final expression is implicitly returned
        body = d.get("body")
        if body:
            self._process_lambda_block(body)
        else:
            self.emit("AgoType::Null")

        self.output_lines.append("}")

        # Capture and restore state
        lambda_code = "\n".join(self.output_lines)
        self.output_lines = old_lines
        self.indent_level = old_indent
        self.declared_vars = old_declared
        self._in_id_lambda = old_in_lambda

        self.lambdas.append(lambda_code)
        return lambda_id

    def _process_lambda_block(self, block: Any) -> None:
        """Process a lambda block where the final statement is implicitly returned."""
        if block is None:
            self.emit("AgoType::Null")
            return

        d = to_dict(block)
        
        stmts = d.get("stmts")
        if stmts is None:
            self.emit("AgoType::Null")
            return

        stmts_d = to_dict(stmts)
        first = stmts_d.get("first")
        rest = stmts_d.get("rest")

        # Collect all statements
        all_stmts = []
        if first:
            all_stmts.append(first)

        if rest:
            for item in rest:
                if isinstance(item, list):
                    for sub in item:
                        if (
                            sub
                            and sub != "\n"
                            and not (isinstance(sub, str) and sub.strip() == "")
                        ):
                            all_stmts.append(sub)
                elif item and item != "\n":
                    all_stmts.append(item)

        if not all_stmts:
            self.emit("AgoType::Null")
            return

        # Process all statements except the last normally
        for stmt in all_stmts[:-1]:
            self._generate_lambda_statement(stmt)

        # For the last statement, check if it's an expression that should be returned
        last_stmt = all_stmts[-1]
        self._generate_lambda_final_statement(last_stmt)

    def _generate_lambda_statement(self, stmt: Any) -> None:
        """Generate code for a lambda statement (may include implicit_return)."""
        if stmt is None:
            return
        
        d = to_dict(stmt)
        
        # Check for implicit_return (expression statement in lambda)
        # This includes function calls since they are valid expressions
        if "implicit_return" in d:
            # This is an expression statement - just evaluate it (not return, since it's not last)
            expr = self._generate_expr(d["implicit_return"])
            self.emit(f"{expr};")
            return
        
        # Otherwise, generate as normal statement (declarations, control flow, etc.)
        self._generate_statement(stmt)

    def _generate_lambda_final_statement(self, stmt: Any) -> None:
        """
        Generate the final statement of a lambda, implicitly returning expressions.
        
        If the final statement is a pure expression (not a declaration, assignment,
        control flow, etc.), it's returned implicitly. Otherwise, process it normally
        and return Null.
        """
        if stmt is None:
            self.emit("AgoType::Null")
            return

        if isinstance(stmt, str):
            # Keywords like verum, falsus, inanis are expressions
            if stmt == "verum":
                self.emit("AgoType::Bool(true)")
            elif stmt == "falsus":
                self.emit("AgoType::Bool(false)")
            elif stmt == "inanis":
                self.emit("AgoType::Null")
            elif stmt in ("frio", "pergo", "omitto"):
                # Control flow - process normally and return Null
                self._generate_statement(stmt)
                self.emit("AgoType::Null")
            else:
                # Likely a variable reference - return it
                expr = self._generate_variable_ref(stmt)
                self.emit(expr)
            return

        if isinstance(stmt, list):
            # Could be an expression wrapped in a list
            for sub in stmt:
                if sub is not None and sub not in (",", "[", "]", "{", "}"):
                    self._generate_lambda_final_statement(sub)
                    return
            self.emit("AgoType::Null")
            return

        d = to_dict(stmt)

        # Check for implicit_return (expression statement in lambda) - return it
        if "implicit_return" in d:
            expr = self._generate_expr(d["implicit_return"])
            self.emit(expr)
            return

        # Check if this is a statement (should be processed normally)
        # vs an expression (should be returned)
        
        # Return statement - handle explicitly
        if "return_stmt" in d or ("value" in d and d.get("return_stmt") is not None):
            self._generate_return(stmt)
            return
        
        # Declaration - process normally, return Null
        if "name" in d and "value" in d and "target" not in d:
            self._generate_declaration(stmt)
            self.emit("AgoType::Null")
            return
        
        # Reassignment - process normally, return Null
        if "target" in d and "value" in d:
            self._generate_reassignment(stmt)
            self.emit("AgoType::Null")
            return
        
        # Control flow (if, while, for) - process normally, return Null
        if "if_stmt" in d or ("cond" in d and "then" in d):
            self._generate_if(d.get("if_stmt") or stmt)
            self.emit("AgoType::Null")
            return
        if "while_stmt" in d or ("cond" in d and "body" in d and "iterator" not in d):
            self._generate_while(d.get("while_stmt") or stmt)
            self.emit("AgoType::Null")
            return
        if "for_stmt" in d or ("iterator" in d and "iterable" in d):
            self._generate_for(d.get("for_stmt") or stmt)
            self.emit("AgoType::Null")
            return

        # Call statement - the result should be returned
        if "call" in d:
            expr = self._generate_expr(d["call"])
            self.emit(expr)
            return

        # Everything else is treated as an expression - return it
        expr = self._generate_expr(stmt)
        self.emit(expr)

    def _emit_prelude(self) -> None:
        """Emit the Rust prelude with imports."""
        self.emit_raw("use ago_stdlib::{")
        self.emit_raw("    AgoType, AgoRange, AgoLambda, TargetType,")
        self.emit_raw("    add, subtract, multiply, divide, modulo,")
        self.emit_raw("    greater_than, greater_equal, less_than, less_equal,")
        self.emit_raw("    and, or, not, bitwise_and, bitwise_or, bitwise_xor,")
        self.emit_raw("    slice, sliceto, contains, elvis,")
        self.emit_raw("    unary_minus, unary_plus,")
        self.emit_raw("    get, set, inseri, removium, validate_list_type, into_iter,")
        self.emit_raw("    dici, apertu, species, exei, aequalam, claverum, scribi, audies")
        self.emit_raw("};")
        self.emit_raw("use std::collections::HashMap;")

    def _collect_functions(self, ast: Any) -> None:
        """First pass: collect all function declarations."""
        if ast is None:
            return
        if isinstance(ast, str):
            return
        if isinstance(ast, (list, tuple)):
            for item in ast:
                self._collect_functions(item)
            return

        d = to_dict(ast)
        # Method declaration: has name, params, body
        if "name" in d and "body" in d and "params" in d:
            self._generate_function(ast)

    def _process_principio(self, ast: Any) -> None:
        """Process the top-level principio rule."""
        if ast is None:
            return
        if isinstance(ast, (list, tuple)):
            for item in ast:
                self._process_top_level(item)
            return
        self._process_top_level(ast)

    def _process_top_level(self, item: Any) -> None:
        """Process a top-level item (skip function decls, process statements)."""
        if item is None:
            return
        if isinstance(item, str):
            # Newlines, etc.
            return
        if isinstance(item, (list, tuple)):
            for sub in item:
                self._process_top_level(sub)
            return

        d = to_dict(item)
        # Skip method declarations (already processed)
        if "name" in d and "body" in d and "params" in d:
            return
        # Check for call statement
        if "call" in d:
            expr = self._generate_expr(d["call"])
            self.emit(f"{expr};")
            return
        # Process as statement
        self._generate_statement(item)

    def _function_returns_lambda(self, body: Any) -> bool:
        """Check if function body returns a lambda directly (not as an argument)."""
        if body is None:
            return False
        if isinstance(body, (list, tuple)):
            for item in body:
                if self._function_returns_lambda(item):
                    return True
            return False
        if isinstance(body, dict) or hasattr(body, "parseinfo"):
            d = to_dict(body)
            # Check if this is a return statement with a lambda
            if d.get("value") is not None:
                value = d["value"]
                value_d = to_dict(value) if not isinstance(value, str) else {}
                # The return value is wrapped: value -> value -> actual_content
                inner = value_d.get("value")
                if inner:
                    inner_d = to_dict(inner) if not isinstance(inner, str) else {}
                    # Direct lambda return: inner has 'body' and 'params' keys (lambda structure)
                    # but NOT 'base', 'chain', 'mchain', 'call', 'func' (method chain/call structure)
                    if inner_d.get("body") is not None:
                        # Check it's not a method chain or call
                        if not inner_d.get("base") and not inner_d.get("chain") and not inner_d.get("call") and not inner_d.get("func"):
                            return True
            # Recurse into statements but NOT into expression arguments
            stmts = d.get("stmts")
            if stmts:
                if self._function_returns_lambda(stmts):
                    return True
            # Check first/rest for statement lists
            first = d.get("first")
            if first and self._function_returns_lambda(first):
                return True
            rest = d.get("rest")
            if rest and self._function_returns_lambda(rest):
                return True
            # Check if/else branches
            if_body = d.get("if_body")
            if if_body and self._function_returns_lambda(if_body):
                return True
            else_body = d.get("else_body")
            if else_body and self._function_returns_lambda(else_body):
                return True
        return False

    def _generate_function(self, ast: Any) -> None:
        """Generate a Rust function from a method declaration."""
        d = to_dict(ast)
        func_name = str(d["name"])

        # Track this function for stem-based resolution
        self.user_functions.add(func_name)

        # Parse parameters (all mut since they can be reassigned in Ago)
        params = self._parse_params(d.get("params"))
        
        # Generate parameter string with correct types
        # Parameters ending in -o are lambda types
        param_parts = []
        lambda_params = set()  # Track which params are lambdas
        for name in params:
            # Check if this is a lambda parameter (ends in 'o' with at least one char before)
            if len(name) > 1 and name.endswith("o"):
                param_parts.append(f"{name}: AgoLambda")
                lambda_params.add(name)
            else:
                param_parts.append(f"mut {name}: AgoType")
        param_str = ", ".join(param_parts)

        # Check if this function returns a lambda
        returns_lambda = self._function_returns_lambda(d.get("body"))
        return_type = "AgoLambda" if returns_lambda else "AgoType"

        # Emit function signature
        self.emit_raw("")
        self.emit_raw(f"fn {func_name}({param_str}) -> {return_type} {{")
        self.indent_level += 1

        # Track parameters as declared
        old_declared = self.declared_vars.copy()
        old_lambda_params = getattr(self, "_lambda_params", set()).copy()
        self._lambda_params = lambda_params
        for p in params:
            self.declared_vars.add(p)

        # Track if current function returns lambda (for use in return generation)
        old_returns_lambda = getattr(self, "_current_func_returns_lambda", False)
        self._current_func_returns_lambda = returns_lambda

        # Process body
        body = d.get("body")
        if body:
            self._process_block(body)

        # Default return if no explicit return (only for non-lambda returning functions)
        if not returns_lambda:
            self.emit("AgoType::Null")

        self.indent_level -= 1
        self.emit_raw("}")

        # Restore state
        self.declared_vars = old_declared
        self._lambda_params = old_lambda_params
        self._current_func_returns_lambda = old_returns_lambda

    def _parse_params(self, params_node: Any) -> list[str]:
        """Parse parameter list into variable names."""
        if params_node is None:
            return []

        d = to_dict(params_node)
        names = []

        first = d.get("first")
        if first:
            name = self._extract_identifier(first)
            if name:
                names.append(name)

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
                        names.append(name)

        return names

    def _extract_identifier(self, node: Any) -> Optional[str]:
        """Extract identifier name from node."""
        if isinstance(node, str):
            return node
        d = to_dict(node)
        if "id" in d:
            return str(d["id"])
        if "value" in d:
            inner = d["value"]
            if isinstance(inner, dict) or hasattr(inner, "parseinfo"):
                return self._extract_identifier(inner)
        return None

    def _process_block(self, block: Any) -> None:
        """Process a block of statements."""
        if block is None:
            return

        d = to_dict(block)
        stmts = d.get("stmts")
        if stmts is None:
            return

        stmts_d = to_dict(stmts)
        first = stmts_d.get("first")
        if first:
            self._generate_statement(first)

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
                            self._generate_statement(sub)
                elif item and item != "\n":
                    self._generate_statement(item)

    def _generate_statement(self, stmt: Any) -> None:
        """Generate code for a statement."""
        if stmt is None:
            return

        if isinstance(stmt, str):
            if stmt == "frio":
                self.emit("break;")
            elif stmt == "pergo":
                self.emit("continue;")
            elif stmt == "omitto":
                pass  # No-op
            return

        if isinstance(stmt, list):
            for sub in stmt:
                self._generate_statement(sub)
            return

        d = to_dict(stmt)

        # Return statement
        if "return_stmt" in d or ("value" in d and d.get("return_stmt") is not None):
            self._generate_return(stmt)
        # Declaration: has name and value, no target
        elif "name" in d and "value" in d and "target" not in d:
            self._generate_declaration(stmt)
        # Reassignment: has target and value
        elif "target" in d and "value" in d:
            self._generate_reassignment(stmt)
        # If statement
        elif "if_stmt" in d:
            self._generate_if(d["if_stmt"])
        elif "cond" in d and "then" in d:
            self._generate_if(stmt)
        # While statement
        elif "while_stmt" in d:
            self._generate_while(d["while_stmt"])
        elif "cond" in d and "body" in d and "iterator" not in d:
            self._generate_while(stmt)
        # For statement
        elif "for_stmt" in d:
            self._generate_for(d["for_stmt"])
        elif "iterator" in d and "iterable" in d:
            self._generate_for(stmt)
        # Call statement
        elif "call" in d:
            expr = self._generate_expr(d["call"])
            self.emit(f"{expr};")
        # Check for nested return
        elif "value" in d:
            inner = d["value"]
            if isinstance(inner, dict):
                inner_d = to_dict(inner)
                if "return_stmt" in inner_d:
                    self._generate_return(inner)

    def _generate_declaration(self, stmt: Any) -> None:
        """Generate variable declaration."""
        d = to_dict(stmt)
        var_name = str(d["name"])
        value = d.get("value")

        # First, generate the RHS expression (before removing old variables with same stem)
        # This allows `xarum := xarum` to work - RHS refers to existing `xas` variable
        expr = self._generate_expr(value)

        # In Ago, only one variable per stem can exist at a time.
        # Remove any existing variable with the same stem AFTER evaluating RHS.
        new_suffix, new_stem = get_suffix_and_stem(var_name)
        if new_stem:
            to_remove = []
            for existing_var in self.declared_vars:
                existing_suffix, existing_stem = get_suffix_and_stem(existing_var)
                if existing_stem == new_stem and existing_var != var_name:
                    to_remove.append(existing_var)
            for var in to_remove:
                self.declared_vars.discard(var)

        # Add runtime type validation for typed lists
        # Map suffixes to expected element types
        list_elem_types = {
            "aem": "int",
            "arum": "float",
            "as": "bool",
            "erum": "string",
        }
        if new_suffix in list_elem_types:
            elem_type = list_elem_types[new_suffix]
            expr = f'validate_list_type(&{expr}, "{elem_type}")'

        self.emit(f"let mut {var_name} = {expr};")
        self.declared_vars.add(var_name)

    def _generate_reassignment(self, stmt: Any) -> None:
        """Generate variable reassignment."""
        d = to_dict(stmt)
        var_name = str(d["target"])
        value = d.get("value")
        index = d.get("index")

        expr = self._generate_expr(value)

        if index:
            # Indexed assignment: var[idx] = value
            # Evaluate RHS first to avoid borrow conflicts when RHS references var
            idx_expr = self._generate_indexing(index)
            temp_var = f"__temp_{self._get_temp_counter()}"
            self.emit(f"let {temp_var} = {expr};")
            self.emit(f"set(&mut {var_name}, &{idx_expr}, {temp_var});")
        else:
            self.emit(f"{var_name} = {expr};")

    def _generate_indexing(self, index_node: Any) -> str:
        """Generate index expression."""
        d = to_dict(index_node)

        # The index expression is in 'expr' at the top level
        expr = d.get("expr")
        if expr:
            return self._generate_expr(expr)

        # Fallback: check indexes array for backwards compatibility
        indexes = d.get("indexes", [])
        if indexes:
            if isinstance(indexes, list) and len(indexes) > 0:
                first = indexes[0]
                first_d = to_dict(first)
                expr = first_d.get("expr")
                if expr:
                    return self._generate_expr(expr)

        return "AgoType::Int(0)"

    def _generate_return(self, stmt: Any) -> None:
        """Generate return statement."""
        d = to_dict(stmt)
        return_stmt = d.get("return_stmt")
        if return_stmt and isinstance(return_stmt, list) and len(return_stmt) >= 2:
            value = return_stmt[1]
            expr = self._generate_expr(value)
            self.emit(f"return {expr};")
        elif d.get("value"):
            expr = self._generate_expr(d["value"])
            self.emit(f"return {expr};")
        else:
            self.emit("return AgoType::Null;")

    def _generate_if(self, stmt: Any) -> None:
        """Generate if statement."""
        d = to_dict(stmt)

        cond = d.get("cond")
        cond_expr = self._generate_expr(cond)

        self.emit(f"if matches!({cond_expr}, AgoType::Bool(true)) {{")
        self.indent_level += 1
        self._process_block(d.get("then"))
        self.indent_level -= 1

        # Handle elifs
        elifs = d.get("elifs")
        if elifs:
            for elif_block in elifs:
                elif_cond = None
                elif_body = None

                if isinstance(elif_block, (list, tuple)):
                    for item in elif_block:
                        if item == "aluid":
                            continue
                        if elif_cond is None and item is not None:
                            if isinstance(item, dict) or hasattr(item, "parseinfo"):
                                elif_cond = item
                        elif elif_body is None and item is not None:
                            if isinstance(item, dict) or hasattr(item, "parseinfo"):
                                elif_body = item

                if elif_cond:
                    elif_expr = self._generate_expr(elif_cond)
                    self.emit(
                        f"}} else if matches!({elif_expr}, AgoType::Bool(true)) {{"
                    )
                    self.indent_level += 1
                    if elif_body:
                        self._process_block(elif_body)
                    self.indent_level -= 1

        # Handle else
        else_frag = d.get("else_frag") or d.get("else_fragment")
        if else_frag:
            else_d = to_dict(else_frag)
            self.emit("} else {")
            self.indent_level += 1
            self._process_block(else_d.get("else_body"))
            self.indent_level -= 1

        self.emit("}")

    def _generate_while(self, stmt: Any) -> None:
        """Generate while loop."""
        d = to_dict(stmt)

        cond = d.get("cond")
        cond_expr = self._generate_expr(cond)

        self.emit(f"while matches!({cond_expr}, AgoType::Bool(true)) {{")
        self.indent_level += 1
        self._process_block(d.get("body"))
        self.indent_level -= 1
        self.emit("}")

    def _generate_for(self, stmt: Any) -> None:
        """Generate for loop."""
        d = to_dict(stmt)

        iterator = self._extract_identifier(d.get("iterator"))
        iterable = d.get("iterable")
        iterable_expr = self._generate_expr(iterable)

        # In Ago, only one variable per stem can exist at a time.
        # Save and remove variables with the same stem as the iterator.
        iter_suffix, iter_stem = get_suffix_and_stem(iterator)
        shadowed_vars = []
        if iter_stem:
            for existing_var in list(self.declared_vars):
                existing_suffix, existing_stem = get_suffix_and_stem(existing_var)
                if existing_stem == iter_stem and existing_var != iterator:
                    shadowed_vars.append(existing_var)
                    self.declared_vars.discard(existing_var)

        self.emit(f"for {iterator} in into_iter(&{iterable_expr}) {{")
        self.indent_level += 1
        self.declared_vars.add(iterator)
        self._process_block(d.get("body"))
        self.indent_level -= 1
        self.emit("}")

        # Restore shadowed variables after loop exits
        self.declared_vars.discard(iterator)
        for var in shadowed_vars:
            self.declared_vars.add(var)

    def _generate_expr(self, expr: Any) -> str:
        """Generate an expression and return as string."""
        if expr is None:
            return "AgoType::Null"

        if isinstance(expr, str):
            if expr == "verum":
                return "AgoType::Bool(true)"
            if expr == "falsus":
                return "AgoType::Bool(false)"
            if expr == "inanis":
                return "AgoType::Null"
            # Variable reference
            return expr

        if isinstance(expr, (list, tuple)):
            # Could be a list literal or struct
            if len(expr) >= 2 and expr[0] == "{" and expr[-1] == "}":
                return self._generate_struct(expr)
            if len(expr) >= 2 and expr[0] == "[" and expr[-1] == "]":
                return self._generate_list(expr)
            # Process first non-None element
            for item in expr:
                if item is not None and item not in (",", "[", "]", "{", "}"):
                    return self._generate_expr(item)
            return "AgoType::Null"

        d = to_dict(expr)

        # Unwrap value wrapper
        if "value" in d and d.get("value") is not None:
            inner = d["value"]
            if isinstance(inner, str):
                if inner == "verum":
                    return "AgoType::Bool(true)"
                if inner == "falsus":
                    return "AgoType::Bool(false)"
                if inner == "inanis":
                    return "AgoType::Null"
                return inner
            return self._generate_expr(inner)

        # Literals
        if d.get("int") is not None:
            return f"AgoType::Int({d['int']})"
        if d.get("float") is not None:
            return f"AgoType::Float({d['float']})"
        if d.get("str") is not None:
            # String literal - remove surrounding quotes for Rust
            s = d["str"]
            return f"AgoType::String({s}.to_string())"
        if d.get("roman") is not None:
            val = self._roman_to_int(d["roman"])
            return f"AgoType::Int({val})"

        # Boolean literals
        if d.get("TRUE") is not None:
            return "AgoType::Bool(true)"
        if d.get("FALSE") is not None:
            return "AgoType::Bool(false)"
        if d.get("NULL") is not None:
            return "AgoType::Null"

        # Identifier
        if d.get("id") is not None:
            name = str(d["id"])
            if name == "id":
                return "id"  # Lambda parameter
            return self._generate_variable_ref(name)

        # Parenthesized expression
        if d.get("paren") is not None:
            paren = d["paren"]
            if isinstance(paren, (list, tuple)) and len(paren) >= 2:
                return self._generate_expr(paren[1])
            return self._generate_expr(paren)

        # List literal
        if d.get("list") is not None:
            return self._generate_list(d["list"])

        # Struct literal
        if d.get("mapstruct") is not None:
            return self._generate_struct(d["mapstruct"])

        # Function call
        if d.get("call") is not None:
            return self._generate_call(d["call"])

        # Direct call_stmt (has first with func, or has chain for method calls)
        if d.get("first") is not None:
            first = d["first"]
            chain = d.get("chain")
            # Method chain: identifier.method() or method chain
            if chain and isinstance(chain, (list, tuple)) and len(chain) > 0:
                return self._generate_call(d)
            # Simple function call
            first_d = to_dict(first) if not isinstance(first, str) else {}
            # Handle new chain_elem structure: {call: {...}} or {field: ...}
            if first_d.get("call"):
                first_d = to_dict(first_d["call"])
            if first_d.get("func") is not None:
                return self._generate_call(d)

        # Method chain
        if d.get("mchain") is not None:
            return self._generate_method_chain(d["mchain"])

        # Indexed access
        if d.get("indexed") is not None:
            return self._generate_indexed(d["indexed"])

        # Struct field access - base and chain are in the same dict as struct_indexed
        if d.get("struct_indexed") is not None:
            return self._generate_struct_indexed(d)

        # Ternary operator (condition ? true_val : false_val)
        if d.get("condition") is not None and d.get("true_val") is not None and d.get("false_val") is not None:
            return self._generate_ternary(d)

        # Binary operators
        if d.get("op") is not None and d.get("left") is not None:
            return self._generate_binary_op(d)

        # Unary operators
        if (
            d.get("op") is not None
            and d.get("right") is not None
            and d.get("left") is None
        ):
            return self._generate_unary_op(d)

        # Lambda declaration
        if d.get("body") is not None and "name" not in d:
            return self._generate_lambda(d)

        return "AgoType::Null"

    def _generate_ternary(self, d: dict) -> str:
        """Generate ternary operator (condition ? true_val : false_val)."""
        condition = self._generate_expr(d.get("condition"))
        true_val = self._generate_expr(d.get("true_val"))
        false_val = self._generate_expr(d.get("false_val"))
        return f"(if matches!(({condition}).as_type(TargetType::Bool), AgoType::Bool(true)) {{ {true_val} }} else {{ {false_val} }})"

    def _generate_binary_op(self, d: dict) -> str:
        """Generate binary operation."""
        op = d.get("op")

        # Short-circuit evaluation for et (and) and vel (or)
        # We need to NOT evaluate the right side if the left side determines the result
        if op == "et":
            left = self._generate_expr(d.get("left"))
            right = self._generate_expr(d.get("right"))
            # If left is false, return false without evaluating right
            return f"(if matches!(({left}).as_type(TargetType::Bool), AgoType::Bool(true)) {{ {right} }} else {{ AgoType::Bool(false) }})"

        if op == "vel":
            left = self._generate_expr(d.get("left"))
            right = self._generate_expr(d.get("right"))
            # If left is true, return true without evaluating right
            return f"(if matches!(({left}).as_type(TargetType::Bool), AgoType::Bool(true)) {{ AgoType::Bool(true) }} else {{ {right} }})"

        left = self._generate_expr(d.get("left"))
        right = self._generate_expr(d.get("right"))

        op_map = {
            "+": "add",
            "-": "subtract",
            "*": "multiply",
            "/": "divide",
            "%": "modulo",
            ">": "greater_than",
            ">=": "greater_equal",
            "<": "less_than",
            "<=": "less_equal",
            "&": "bitwise_and",
            "|": "bitwise_or",
            "^": "bitwise_xor",
            "..": "slice",
            ".<": "sliceto",
            "?:": "elvis",
            "in": "contains",
        }

        if op == "==":
            return f"aequalam(&{left}, &{right})"
        if op == "!=":
            return f"not(&aequalam(&{left}, &{right}))"
        if op == "est":
            # Type equality - check if same variant
            return f"AgoType::Bool(std::mem::discriminant(&{left}) == std::mem::discriminant(&{right}))"

        if op in op_map:
            func = op_map[op]
            if op == "in":
                # 'in' operator: needle in haystack -> contains(haystack, needle)
                return f"{func}(&{right}, &{left})"
            return f"{func}(&{left}, &{right})"

        return f"/* unknown op {op} */ AgoType::Null"

    def _generate_unary_op(self, d: dict) -> str:
        """Generate unary operation."""
        op = d.get("op")
        right = self._generate_expr(d.get("right"))

        if op == "-":
            return f"unary_minus(&{right})"
        if op == "+":
            return f"unary_plus(&{right})"
        if op == "non":
            return f"not(&{right})"

        return f"/* unknown unary op {op} */ {right}"

    def _generate_call(self, call_node: Any) -> str:
        """Generate function call or method chain."""
        d = to_dict(call_node)

        # Check if this is a method chain (first is identifier, chain has methods)
        first = d.get("first")
        chain = d.get("chain")

        recv = d.get("recv")
        
        if first and chain and isinstance(chain, (list, tuple)) and len(chain) > 0:
            # Method chain: receiver.method1().method2()
            # Track base variable name for mutating functions
            base_var_name = None
            if isinstance(first, str):
                base_var_name = first
            
            # first is the receiver (identifier or call)
            result = None  # Track whether result was set
            if isinstance(first, str):
                result = self._generate_variable_ref(first)
            else:
                first_d = to_dict(first)
                # Handle new chain_elem structure: {call: {...}} or {field: ...}
                if first_d.get("call"):
                    first_d = to_dict(first_d["call"])
                elif first_d.get("field"):
                    # Field access as first element - treat as variable reference
                    field_name = str(first_d["field"])
                    result = self._generate_variable_ref(field_name)
                    base_var_name = field_name
                    first_d = {}  # Skip the func check below
                if first_d.get("func"):
                    # first is a nodotcall_stmt (method call)
                    func_name = str(first_d.get("func"))
                    args = []
                    if first_d.get("args"):
                        args = self._parse_args(first_d["args"])
                    
                    # Generate receiver expression if there is one
                    recv_expr = None
                    if recv is not None:
                        recv_expr = self._generate_expr(recv)
                    
                    # Check if func_name is a bare type suffix (type cast)
                    # e.g., (0..10).aem() should cast to IntList, not call aem()
                    if (
                        not args
                        and func_name in ENDING_TO_TARGET_TYPE
                        and func_name not in STDLIB_FUNCTIONS
                        and func_name not in self.user_functions
                        and recv_expr is not None
                    ):
                        # This is a type cast
                        target_type = ENDING_TO_TARGET_TYPE[func_name]
                        result = f"{recv_expr}.as_type(TargetType::{target_type})"
                    else:
                        # This is a function call
                        if recv_expr is not None:
                            args = [recv_expr] + args
                        
                        # Check for stem-based function call (e.g., mina() -> minium())
                        actual_func = func_name
                        cast_suffix = None
                        if func_name not in self.user_functions and func_name not in STDLIB_FUNCTIONS:
                            suffix, stem = get_suffix_and_stem(func_name)
                            if stem and suffix:
                                for uf in self.user_functions:
                                    uf_suffix, uf_stem = get_suffix_and_stem(uf)
                                    if uf_stem == stem:
                                        actual_func = uf
                                        cast_suffix = suffix
                                        break
                        
                        # Add references for stdlib functions
                        if actual_func in STDLIB_FUNCTIONS:
                            ref_args = []
                            for i, arg in enumerate(args):
                                if actual_func in MUTATING_STDLIB_FUNCTIONS and i == 0:
                                    if arg.endswith(".clone()"):
                                        arg = arg[:-8]
                                    if not arg.startswith("&mut"):
                                        ref_args.append(f"&mut {arg}")
                                    else:
                                        ref_args.append(arg)
                                elif not arg.startswith("&"):
                                    ref_args.append(f"&{arg}")
                                else:
                                    ref_args.append(arg)
                            args_str = ", ".join(ref_args)
                        else:
                            args_str = ", ".join(args)
                        result = f"{actual_func}({args_str})"
                        
                        if cast_suffix and cast_suffix in ENDING_TO_TARGET_TYPE:
                            target_type = ENDING_TO_TARGET_TYPE[cast_suffix]
                            result = f"{result}.as_type(TargetType::{target_type})"
                elif result is None:
                    # Only generate expr if result wasn't already set (e.g., by field branch)
                    result = self._generate_expr(first)

            # Process chain
            for item in chain:
                if item is None or item == ".":
                    continue
                if isinstance(item, (list, tuple)):
                    for sub in item:
                        if sub == "." or sub is None:
                            continue
                        if isinstance(sub, dict) or hasattr(sub, "parseinfo"):
                            sub_d = to_dict(sub)
                            # Handle new chain_elem structure: {call: {...}} or {field: ...}
                            if sub_d.get("call"):
                                sub_d = to_dict(sub_d["call"])
                            elif sub_d.get("field"):
                                # Field access - generate struct field access
                                field_name = str(sub_d["field"])
                                result = f'get(&{result}, &AgoType::String("{field_name}".to_string()))'
                                continue
                            func_name = sub_d.get("func")
                            if func_name:
                                func_name_str = str(func_name)
                                args = []
                                if sub_d.get("args"):
                                    args = self._parse_args(sub_d["args"])
                                # Check if this is a type cast (no args, name is or ends with type suffix)
                                # BUT only if it's not a known stdlib or user function
                                if (
                                    not args
                                    and func_name_str not in STDLIB_FUNCTIONS
                                    and func_name_str not in self.user_functions
                                ):
                                    # First check if the name IS a type suffix (e.g., .a(), .es())
                                    # ONLY bare suffixes like .es(), .a() are pure type casts
                                    if func_name_str in ENDING_TO_TARGET_TYPE:
                                        target_type = ENDING_TO_TARGET_TYPE[
                                            func_name_str
                                        ]
                                        result = f"{result}.as_type(TargetType::{target_type})"
                                        continue
                                    # For stem+suffix names (like .mines()), check if there's a matching
                                    # function first. If not, it's a type cast on a variable.
                                    suffix, stem = get_suffix_and_stem(func_name_str)
                                    if suffix and suffix in ENDING_TO_TARGET_TYPE:
                                        # Check if there's a user function with this stem
                                        found_func = None
                                        for uf in self.user_functions:
                                            uf_suffix, uf_stem = get_suffix_and_stem(uf)
                                            if uf_stem == stem:
                                                found_func = uf
                                                break
                                        if found_func is None:
                                            # No function with this stem - just a type cast
                                            target_type = ENDING_TO_TARGET_TYPE[suffix]
                                            result = f"{result}.as_type(TargetType::{target_type})"
                                            continue
                                        # Otherwise fall through to stem-based function call
                                # Try stem-based function resolution
                                actual_func_name = func_name_str
                                cast_target = None
                                if (
                                    func_name_str not in self.user_functions
                                    and func_name_str not in STDLIB_FUNCTIONS
                                ):
                                    call_suffix, call_stem = get_suffix_and_stem(func_name_str)
                                    if call_stem and call_suffix:
                                        for uf in self.user_functions:
                                            uf_suffix, uf_stem = get_suffix_and_stem(uf)
                                            if uf_stem == call_stem and uf != func_name_str:
                                                actual_func_name = uf
                                                cast_target = ENDING_TO_RUST_TARGET.get(call_suffix)
                                                break
                                
                                # Handle mutating stdlib functions
                                if actual_func_name in MUTATING_STDLIB_FUNCTIONS and base_var_name:
                                    actual_var = base_var_name
                                    if base_var_name not in self.declared_vars:
                                        suffix, stem = get_suffix_and_stem(base_var_name)
                                        if stem:
                                            for dv in self.declared_vars:
                                                dv_suffix, dv_stem = get_suffix_and_stem(dv)
                                                if dv_stem == stem:
                                                    actual_var = dv
                                                    break
                                    
                                    # Check if any args reference the variable being mutated
                                    # If so, evaluate them into temp vars first to avoid borrow conflicts
                                    ref_args = []
                                    for arg in args:
                                        if actual_var in arg:
                                            temp_var = f"__temp_{self._get_temp_counter()}"
                                            self.emit(f"let {temp_var} = {arg};")
                                            ref_args.append(f"&{temp_var}")
                                        elif not arg.startswith("&"):
                                            ref_args.append(f"&{arg}")
                                        else:
                                            ref_args.append(arg)
                                    
                                    receiver = f"&mut {actual_var}"
                                    all_args = [receiver] + ref_args
                                elif actual_func_name in STDLIB_FUNCTIONS:
                                    # Stdlib functions take &AgoType references
                                    receiver = (
                                        f"&{result}"
                                        if not result.startswith("&")
                                        else result
                                    )
                                    ref_args = [f"&{arg}" if not arg.startswith("&") else arg for arg in args]
                                    all_args = [receiver] + ref_args
                                else:
                                    # User-defined functions take AgoType by value
                                    all_args = [result] + args
                                result = f"{actual_func_name}({', '.join(all_args)})"
                                
                                # Apply cast if needed
                                if cast_target:
                                    result = f"{result}.as_type(TargetType::{cast_target})"
                else:
                    item_d = to_dict(item) if not isinstance(item, str) else {}
                    func_name = item_d.get("func")
                    if func_name:
                        func_name_str = str(func_name)
                        args = []
                        if item_d.get("args"):
                            args = self._parse_args(item_d["args"])
                        # Check if this is a type cast (no args, name is or ends with type suffix)
                        # BUT only if it's not a known stdlib or user function
                        if (
                            not args
                            and func_name_str not in STDLIB_FUNCTIONS
                            and func_name_str not in self.user_functions
                        ):
                            # First check if the name IS a type suffix (e.g., .a(), .es())
                            # ONLY bare suffixes like .es(), .a() are pure type casts
                            if func_name_str in ENDING_TO_TARGET_TYPE:
                                target_type = ENDING_TO_TARGET_TYPE[func_name_str]
                                result = f"{result}.as_type(TargetType::{target_type})"
                                continue
                            # For stem+suffix names (like .mines()), check if there's a matching
                            # function first. If not, it's a type cast on a variable.
                            suffix, stem = get_suffix_and_stem(func_name_str)
                            if suffix and suffix in ENDING_TO_TARGET_TYPE:
                                # Check if there's a user function with this stem
                                found_func = None
                                for uf in self.user_functions:
                                    uf_suffix, uf_stem = get_suffix_and_stem(uf)
                                    if uf_stem == stem:
                                        found_func = uf
                                        break
                                if found_func is None:
                                    # No function with this stem - just a type cast
                                    target_type = ENDING_TO_TARGET_TYPE[suffix]
                                    result = f"{result}.as_type(TargetType::{target_type})"
                                    continue
                                # Otherwise fall through to stem-based function call
                        # Try stem-based function resolution
                        actual_func_name = func_name_str
                        cast_target = None
                        if (
                            func_name_str not in self.user_functions
                            and func_name_str not in STDLIB_FUNCTIONS
                        ):
                            call_suffix, call_stem = get_suffix_and_stem(func_name_str)
                            if call_stem and call_suffix:
                                for uf in self.user_functions:
                                    uf_suffix, uf_stem = get_suffix_and_stem(uf)
                                    if uf_stem == call_stem and uf != func_name_str:
                                        actual_func_name = uf
                                        cast_target = ENDING_TO_RUST_TARGET.get(call_suffix)
                                        break
                        
                        # Handle mutating stdlib functions
                        if actual_func_name in MUTATING_STDLIB_FUNCTIONS and base_var_name:
                            actual_var = base_var_name
                            if base_var_name not in self.declared_vars:
                                suffix, stem = get_suffix_and_stem(base_var_name)
                                if stem:
                                    for dv in self.declared_vars:
                                        dv_suffix, dv_stem = get_suffix_and_stem(dv)
                                        if dv_stem == stem:
                                            actual_var = dv
                                            break
                            
                            # Check if any args reference the variable being mutated
                            # If so, evaluate them into temp vars first to avoid borrow conflicts
                            ref_args = []
                            for arg in args:
                                if actual_var in arg:
                                    temp_var = f"__temp_{self._get_temp_counter()}"
                                    self.emit(f"let {temp_var} = {arg};")
                                    ref_args.append(f"&{temp_var}")
                                elif not arg.startswith("&"):
                                    ref_args.append(f"&{arg}")
                                else:
                                    ref_args.append(arg)
                            
                            receiver = f"&mut {actual_var}"
                            all_args = [receiver] + ref_args
                        elif actual_func_name in STDLIB_FUNCTIONS:
                            # Stdlib functions take &AgoType references
                            receiver = (
                                f"&{result}" if not result.startswith("&") else result
                            )
                            ref_args = [f"&{arg}" if not arg.startswith("&") else arg for arg in args]
                            all_args = [receiver] + ref_args
                        else:
                            # User-defined functions take AgoType by value
                            all_args = [result] + args
                        result = f"{actual_func_name}({', '.join(all_args)})"
                        
                        # Apply cast if needed
                        if cast_target:
                            result = f"{result}.as_type(TargetType::{cast_target})"

            return result

        # Check for recv (method chain on literal like "string".dici())
        recv = d.get("recv")

        # Simple function call
        func_name = None
        args = []

        if first:
            first_d = to_dict(first) if not isinstance(first, str) else {}
            # Handle new chain_elem structure: {call: {...}} or {field: ...}
            if first_d.get("call"):
                first_d = to_dict(first_d["call"])
            func = first_d.get("func") if first_d else None
            if func:
                func_name = str(func)
                args_node = first_d.get("args")
                if args_node:
                    args = self._parse_args(args_node)

        if not func_name:
            # Direct call node (from nodotcall_stmt)
            func = d.get("func")
            if func:
                func_name = str(func)
            args_node = d.get("args")
            if args_node:
                args = self._parse_args(args_node)

        if func_name:
            # If there's a receiver (method chain), it becomes the first argument
            if recv is not None:
                recv_expr = self._generate_expr(recv)
                
                # Check if func_name is a bare type suffix (e.g., .aem(), .es())
                # If so, this is a type cast, not a function call
                if (
                    not args  # no additional args
                    and func_name in ENDING_TO_TARGET_TYPE
                    and func_name not in STDLIB_FUNCTIONS
                    and func_name not in self.user_functions
                ):
                    target_type = ENDING_TO_TARGET_TYPE[func_name]
                    return f"{recv_expr}.as_type(TargetType::{target_type})"
                
                args = [recv_expr] + args

            # Check if this is a lambda variable (ends with 'o' and is a declared var)
            if func_name in self.declared_vars:
                # Lambda call - pass args as slice
                args_str = ", ".join(args)
                return f"{func_name}(&[{args_str}])"

            # Check for stem-based function call (e.g., aae() to call aa() and cast to float)
            actual_func_name = func_name
            cast_target = None

            # If function doesn't exist directly, try to find by stem
            if (
                func_name not in self.user_functions
                and func_name not in STDLIB_FUNCTIONS
            ):
                call_suffix, call_stem = get_suffix_and_stem(func_name)
                if call_stem and call_suffix:
                    # Look for user-defined function with the same stem
                    for uf in self.user_functions:
                        uf_suffix, uf_stem = get_suffix_and_stem(uf)
                        if uf_stem == call_stem and uf != func_name:
                            # Found a function with the same stem
                            actual_func_name = uf
                            # Determine the cast target type
                            cast_target = ENDING_TO_RUST_TARGET.get(call_suffix)
                            break

            # Only add references for stdlib functions (they take &AgoType)
            # User-defined functions take AgoType by value
            if actual_func_name in STDLIB_FUNCTIONS:
                ref_args = []
                for i, arg in enumerate(args):
                    # For mutating functions, first arg needs &mut
                    if actual_func_name in MUTATING_STDLIB_FUNCTIONS and i == 0:
                        # Remove .clone() and add &mut
                        if arg.endswith(".clone()"):
                            arg = arg[:-8]  # Remove .clone()
                        if not arg.startswith("&mut"):
                            ref_args.append(f"&mut {arg}")
                        else:
                            ref_args.append(arg)
                    elif not arg.startswith("&"):
                        ref_args.append(f"&{arg}")
                    else:
                        ref_args.append(arg)
                args_str = ", ".join(ref_args)
            else:
                # User-defined function - pass by value
                args_str = ", ".join(args)

            call_expr = f"{actual_func_name}({args_str})"

            # If we need to cast the result, wrap with .as_type()
            if cast_target:
                return f"{call_expr}.as_type(TargetType::{cast_target})"

            return call_expr

        return "AgoType::Null"

    def _parse_args(self, args_node: Any) -> list[str]:
        """Parse argument list."""
        d = to_dict(args_node)
        args = []

        first = d.get("first")
        if first:
            args.append(self._generate_expr(first))

        rest = d.get("rest")
        if rest:
            for item in rest:
                if isinstance(item, list) and len(item) >= 2:
                    args.append(self._generate_expr(item[1]))
                else:
                    item_d = to_dict(item)
                    if "expr" in item_d:
                        args.append(self._generate_expr(item_d["expr"]))

        return args

    def _generate_method_chain(self, mchain: Any) -> str:
        """Generate method chain: a.b().c(d) -> c(&a, d)."""
        if isinstance(mchain, (list, tuple)) and len(mchain) >= 2:
            base = mchain[0]
            chain = mchain[1] if len(mchain) > 1 else None
        else:
            d = to_dict(mchain)
            base = d.get("base")
            chain = d.get("chain")

        # Track base variable name for mutating functions
        base_var_name = None
        base_d = to_dict(base) if not isinstance(base, str) else {}
        if isinstance(base, str):
            base_var_name = base
        elif base_d.get("id"):
            base_var_name = str(base_d["id"])

        result = self._generate_expr(base)

        if chain and isinstance(chain, (list, tuple)):
            for item in chain:
                if item is None or item == ".":
                    continue

                method = None
                if isinstance(item, (list, tuple)):
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
                    # Handle new chain_elem structure: {call: {...}} or {field: ...}
                    if method_d.get("call"):
                        method_d = to_dict(method_d["call"])
                    elif method_d.get("field"):
                        # Field access - generate struct field access
                        field_name = str(method_d["field"])
                        result = f'get(&{result}, &AgoType::String("{field_name}".to_string()))'
                        continue
                    func_name = method_d.get("func")
                    if func_name:
                        func_name_str = str(func_name)
                        args = []
                        args_node = method_d.get("args")
                        if args_node:
                            args = self._parse_args(args_node)
                        # Check if this is a type cast (no args, name is or ends with type suffix)
                        # BUT only if it's not a known stdlib or user function
                        if (
                            not args
                            and func_name_str not in STDLIB_FUNCTIONS
                            and func_name_str not in self.user_functions
                        ):
                            # First check if the name IS a type suffix (e.g., .a(), .es())
                            # ONLY bare suffixes are allowed for casting
                            if func_name_str in ENDING_TO_TARGET_TYPE:
                                target_type = ENDING_TO_TARGET_TYPE[func_name_str]
                                result = f"{result}.as_type(TargetType::{target_type})"
                                continue
                            # Check if it's a stem-based function call (e.g., .mines() calls minium())
                            suffix, stem = get_suffix_and_stem(func_name_str)
                            if suffix and stem:
                                # Look for a user function with the same stem
                                found_func = None
                                for uf in self.user_functions:
                                    uf_suffix, uf_stem = get_suffix_and_stem(uf)
                                    if uf_stem == stem and uf != func_name_str:
                                        found_func = uf
                                        break
                                if found_func:
                                    # Call the function with receiver as first arg, then cast result
                                    receiver = (
                                        result if result.startswith("&") else result
                                    )
                                    call_result = f"{found_func}({receiver}.clone())"
                                    if suffix in ENDING_TO_TARGET_TYPE:
                                        target_type = ENDING_TO_TARGET_TYPE[suffix]
                                        result = f"{call_result}.as_type(TargetType::{target_type})"
                                    else:
                                        result = call_result
                                    continue
                                else:
                                    # No matching function found - this is an error
                                    # Don't silently cast, let it fail at Rust compile time
                                    # with a clear "unknown function" error
                                    pass  # Fall through to regular method call which will error
                        # Method chaining: receiver becomes first arg
                        # For mutating stdlib functions, use &mut on the base variable
                        if func_name_str in MUTATING_STDLIB_FUNCTIONS and base_var_name:
                            # Resolve the actual variable name (handle stem-based references)
                            actual_var = base_var_name
                            if base_var_name not in self.declared_vars:
                                suffix, stem = get_suffix_and_stem(base_var_name)
                                if stem:
                                    for dv in self.declared_vars:
                                        dv_suffix, dv_stem = get_suffix_and_stem(dv)
                                        if dv_stem == stem:
                                            actual_var = dv
                                            break
                            
                            # Check if any args reference the variable being mutated
                            # If so, evaluate them into temp vars first to avoid borrow conflicts
                            ref_args = []
                            for arg in args:
                                # Check if arg references the variable being mutated (by stem)
                                _, base_stem = get_suffix_and_stem(actual_var)
                                if base_stem and actual_var in arg:
                                    # Need to evaluate this arg first
                                    temp_var = f"__temp_{self._get_temp_counter()}"
                                    self.emit(f"let {temp_var} = {arg};")
                                    ref_args.append(f"&{temp_var}")
                                elif not arg.startswith("&"):
                                    ref_args.append(f"&{arg}")
                                else:
                                    ref_args.append(arg)
                            
                            receiver = f"&mut {actual_var}"
                            all_args = [receiver] + ref_args
                        elif func_name_str in STDLIB_FUNCTIONS:
                            # Stdlib functions take &AgoType references
                            receiver = (
                                f"&{result}" if not result.startswith("&") else result
                            )
                            ref_args = [f"&{arg}" if not arg.startswith("&") else arg for arg in args]
                            all_args = [receiver] + ref_args
                        else:
                            # User-defined functions take AgoType by value
                            all_args = [result] + args
                        result = f"{func_name_str}({', '.join(all_args)})"

        return result

    def _generate_indexed(self, indexed: Any) -> str:
        """Generate indexed access."""
        if hasattr(indexed, "__iter__"):
            items = list(indexed)
            if items:
                base = items[0]
                if isinstance(base, str):
                    # Use _generate_variable_ref to handle stem-based variable resolution
                    base_expr = self._generate_variable_ref(base)
                else:
                    base_expr = self._generate_expr(base)

                # Get index expression
                if len(items) > 1:
                    idx_node = items[1]
                    idx_d = to_dict(idx_node)
                    # The index expression is in 'expr' at the top level
                    expr = idx_d.get("expr")
                    if expr:
                        idx_expr = self._generate_expr(expr)
                        return f"get(&{base_expr}, &{idx_expr})"
                    # Fallback: check indexes array for backwards compatibility
                    indexes = idx_d.get("indexes", [])
                    if indexes and len(indexes) > 0:
                        first_idx = indexes[0]
                        first_d = to_dict(first_idx)
                        idx_expr = self._generate_expr(first_d.get("expr"))
                        return f"get(&{base_expr}, &{idx_expr})"

        return "AgoType::Null"

    def _generate_struct_indexed(self, struct_indexed: Any) -> str:
        """Generate struct field access."""
        d = to_dict(struct_indexed)
        base = d.get("base")
        chain = d.get("chain")

        result = self._generate_expr(base)

        if chain:
            for item in chain:
                if item is None or item == ".":
                    continue

                # Handle different chain formats
                field_name = None

                if isinstance(item, str):
                    if item != ".":
                        field_name = item
                elif isinstance(item, (list, tuple)):
                    # Chain item is like ['.', 'fieldname'] or ['.', '"field name"']
                    for sub in item:
                        if sub and sub != ".":
                            field_name = sub if isinstance(sub, str) else str(sub)
                            break
                else:
                    item_d = to_dict(item)
                    field_name = item_d.get("sub_item")

                if field_name:
                    # Handle quoted vs unquoted field names
                    if field_name.startswith('"') and field_name.endswith('"'):
                        key = field_name  # Already quoted
                    else:
                        key = f'"{field_name}"'
                    result = f"get(&{result}, &AgoType::String({key}.to_string()))"

        return result

    def _generate_list(self, list_node: Any) -> str:
        """Generate list literal."""
        items = []

        def collect_items(node: Any) -> None:
            if node is None:
                return
            if isinstance(node, str):
                if node not in (",", "[", "]"):
                    # Handle boolean and null literals
                    if node == "verum":
                        items.append("AgoType::Bool(true)")
                    elif node == "falsus":
                        items.append("AgoType::Bool(false)")
                    elif node == "inanis":
                        items.append("AgoType::Null")
                    else:
                        # Variable reference
                        items.append(self._generate_variable_ref(node))
                return
            if isinstance(node, (list, tuple)):
                for item in node:
                    collect_items(item)
                return
            d = to_dict(node)
            # Check if this is an actual value node
            if d.get("int") or d.get("float") or d.get("str") or d.get("roman"):
                items.append(self._generate_expr(node))
            elif d.get("id"):
                items.append(self._generate_expr(node))
            elif d.get("value"):
                items.append(self._generate_expr(node))
            elif d.get("list"):
                items.append(self._generate_expr(node))
            elif d.get("op") and d.get("right"):
                # Unary operation (e.g., -3)
                items.append(self._generate_expr(node))
            elif d.get("left") and d.get("op") and d.get("right"):
                # Binary operation
                items.append(self._generate_expr(node))

        if hasattr(list_node, "__iter__") and not isinstance(list_node, str):
            for item in list_node:
                if item is not None and item not in (",", "[", "]"):
                    collect_items(item)

        if not items:
            return "AgoType::ListAny(vec![])"

        items_str = ", ".join(items)
        return f"AgoType::ListAny(vec![{items_str}])"

    def _generate_struct(self, struct_node: Any) -> str:
        """Generate struct/map literal."""
        # Parse key-value pairs
        pairs = []

        def extract_pairs(content: Any) -> None:
            if content is None:
                return
            if isinstance(content, str):
                return
            if isinstance(content, (list, tuple)):
                i = 0
                while i < len(content):
                    item = content[i]
                    if isinstance(item, str) and item not in ("{", "}", ",", ":", "\n"):
                        # Key - look for colon and value
                        if i + 2 < len(content) and content[i + 1] == ":":
                            key = item
                            value = content[i + 2]
                            if key.startswith('"'):
                                key_str = key
                            else:
                                key_str = f'"{key}"'
                            val_expr = self._generate_expr(value)
                            pairs.append(f"({key_str}.to_string(), {val_expr})")
                            i += 3
                            continue
                    elif isinstance(item, (list, tuple)):
                        extract_pairs(item)
                    i += 1
            elif hasattr(content, "parseinfo") or isinstance(content, dict):
                d = to_dict(content)
                for key, val in d.items():
                    if key not in ("parseinfo",) and val is not None:
                        if isinstance(val, (list, tuple)):
                            extract_pairs(val)

        if isinstance(struct_node, (list, tuple)):
            extract_pairs(struct_node)
        else:
            d = to_dict(struct_node)
            for key, val in d.items():
                if key not in ("parseinfo",) and isinstance(val, (list, tuple)):
                    extract_pairs(val)

        if pairs:
            pairs_str = ", ".join(pairs)
            return f"AgoType::Struct(HashMap::from([{pairs_str}]))"
        return "AgoType::Struct(HashMap::new())"

    def _generate_lambda(self, d: dict) -> str:
        """Generate lambda/closure reference."""
        # Find the lambda ID by looking for it in our registered lambdas
        # We need to find the matching lambda by generating it again and comparing
        # For simplicity, use a counter that matches registration order

        # Find or create the lambda ID
        # Since we already collected lambdas, find the matching one
        # This is a simplified approach - track lambda_ids during generation
        if not hasattr(self, "_lambda_gen_counter"):
            self._lambda_gen_counter = 0

        lambda_id = self._lambda_gen_counter
        self._lambda_gen_counter += 1

        # Return a boxed reference to the lambda function
        return f"Box::new(__lambda_{lambda_id}) as AgoLambda"

    def _roman_to_int(self, roman: str) -> int:
        """Convert Roman numeral to integer."""
        values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        result = 0
        prev = 0
        for c in reversed(roman):
            curr = values.get(c, 0)
            if curr < prev:
                result -= curr
            else:
                result += curr
            prev = curr
        return result


def generate(ast: Any) -> str:
    """Generate Rust code from an Ago AST."""
    generator = AgoCodeGenerator()
    return generator.generate(ast)
