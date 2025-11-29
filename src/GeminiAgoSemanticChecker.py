from dataclasses import dataclass
from typing import Optional

from tatsu.walkers import NodeWalker

# --- Provided Data Structures & Helpers ---


class AgoSemanticException(Exception):
    pass


@dataclass
class Symbol:
    name: str
    type_t: str
    category: str = "var"
    scope: Optional[int] = -1
    num_of_params: Optional[int] = -1
    param_types: Optional[list[str]] = None
    return_type: Optional[str] = None
    num_of_fields: Optional[int] = -1
    field_types: Optional[list[str]] = None


class SymbolTable:
    def __init__(self):
        self.scopes: dict[int, dict[str, Symbol]] = {0: {}}
        self.current_scope = 0

    def increment_scope(self) -> int:
        self.current_scope += 1
        if self.current_scope not in self.scopes:
            self.scopes[self.current_scope] = {}
        return self.current_scope

    def decrement_scope(self) -> int:
        if self.current_scope == 0:
            raise Exception("Scope is -1. Unallowable.")
        self.current_scope -= 1
        return self.current_scope

    def add_symbol(self, s: Symbol) -> bool:
        if s.name in self.scopes[self.current_scope]:
            raise AgoSemanticException(
                f"Variable '{s.name}' already exists in scope {self.current_scope}."
            )
        self.scopes[self.current_scope][s.name] = s
        return True

    def get_symbol(self, n: str) -> Symbol | None:
        # Look up in current scope, then work backwards to 0
        search_scope = self.current_scope
        while search_scope >= 0:
            if search_scope in self.scopes and n in self.scopes[search_scope]:
                return self.scopes[search_scope][n]
            search_scope -= 1
        return None


def ending_to_type(ending: str) -> str:
    endings_to_str = {
        "a": "int",
        "ae": "float",
        "am": "bool",
        "aem": "int_list",
        "arum": "float_list",
        "as": "bool_list",
        "es": "string",
        "erum": "string_list",
        "u": "struct",
        "uum": "list_list",
    }
    assert (t := endings_to_str.get(ending)) is not None
    return t


def type_to_type_check(current: str, to: str) -> bool:
    if current == to:
        return True

    # Allow Any for things like NULL or print statements if needed
    if current == "Any" or to == "Any":
        return True

    acceptables = {
        "int": ["float", "bool", "string"],
        "float": ["int", "bool", "string"],
        "bool": ["int", "float", "string"],
        "int_list": ["int", "string", "float_list", "bool_list", "string_list", "bool"],
        "float_list": ["int", "string", "int_list", "bool_list", "string_list", "bool"],
        "bool_list": ["int", "string", "int_list", "float_list", "string_list", "bool"],
        "string_list": ["int", "string", "int_list", "float_list", "bool_list", "bool"],
        "string": ["int", "float", "bool", "string_list"],
        "struct": ["string", "int", "bool"],
        "list_list": ["int", "string", "bool"],
    }

    if current not in acceptables:
        # Fail gracefully if type is unknown
        return False

    if to not in acceptables and to not in acceptables.get(current, []):
        return False

    if to not in acceptables[current]:
        raise AgoSemanticException(
            f"Type mismatch: cannot convert '{current}' to '{to}'. Accepted: {acceptables[current]}"
        )

    return True


# --- Semantic Checker (Walker) ---


class AgoSemanticChecker(NodeWalker):
    def __init__(self):
        self.sym_table = SymbolTable()

    def _infer_type_from_name(self, name: str) -> str:
        # Sort endings by length descending to catch 'aem' before 'am'
        endings = sorted(
            ["a", "ae", "am", "aem", "arum", "as", "es", "erum", "u", "uum"],
            key=len,
            reverse=True,
        )

        for ending in endings:
            if name.endswith(ending):
                return ending_to_type(ending)

        raise AgoSemanticException(
            f"Variable '{name}' does not have a valid type suffix."
        )

    # --- Scope Management ---

    def walk_method_decl(self, node):
        # DEF name LPAREN params RPAREN body
        func_name = node.name
        # Add function to CURRENT scope (before entering new scope)
        # Note: In a real compiler, we might check param types here.
        func_symbol = Symbol(name=func_name, type_t="function", category="func")
        self.sym_table.add_symbol(func_symbol)

        self.sym_table.increment_scope()

        # Add parameters to the new local scope
        if node.params:
            # node.params might be a list of expressions/identifiers depending on grammar structure
            # Assuming params is an 'expression_list' which contains 'first' and 'rest'
            # We need to manually walk/unpack the list to register symbols
            self._register_params(node.params)

        self.walk(node.body)
        self.sym_table.decrement_scope()

    def _register_params(self, params_node):
        # Helper to flatten the recursive expression_list and add symbols
        # This depends heavily on how TatSu structures the list object.
        # Recursively walk or iterate:
        items = []
        if hasattr(params_node, "first"):
            items.append(params_node.first)
        if hasattr(params_node, "rest"):
            for item in params_node.rest:
                # Grammar says: COMMA expr:expression
                items.append(item.expr)

        for item in items:
            # In param definitions, the expression is usually just an identifier
            # We need to extract the name.
            if isinstance(item, str):  # Raw identifier
                name = item
            elif hasattr(item, "id"):  # Item -> identifier wrapper
                name = item.id
            else:
                # If it's a deep object, we might need to walk it or look at type
                continue

            t_type = self._infer_type_from_name(name)
            self.sym_table.add_symbol(Symbol(name=name, type_t=t_type))

    def walk_block(self, node):
        # Block: LBRACE stmts RBRACE
        # NOTE: If methods/ifs handle their own scoping, we might not need to increment here.
        # But usually a block implies a scope. Let's protect against double scoping
        # if the parent (like method_decl) already did it.
        # For this implementation, let's assume Blocks ALWAYS create a new scope
        # unless we add flags. To be safe with the grammar provided:
        # if_stmt -> block. method_decl -> block.
        # Let's increment scope here for safety.

        # self.sym_table.increment_scope()
        # (Commented out because method_decl handled it.
        #  If if_stmt doesn't handle it, uncomment or add logic in if_stmt)

        if node.stmts:
            self.walk(node.stmts)

        # self.sym_table.decrement_scope()

    def walk_if_stmt(self, node):
        # Check condition
        cond_type = self.walk(node.cond)
        type_to_type_check(cond_type, "bool")

        self.sym_table.increment_scope()
        self.walk(node.then)
        self.sym_table.decrement_scope()

        if node.elifs:
            for elif_block in node.elifs:
                cond_t = self.walk(elif_block.elif_cond)
                type_to_type_check(cond_t, "bool")
                self.sym_table.increment_scope()
                self.walk(elif_block.elif_body)
                self.sym_table.decrement_scope()

        if node.else_fragment:
            self.sym_table.increment_scope()
            self.walk(node.else_fragment.else_body)
            self.sym_table.decrement_scope()

    def walk_while_stmt(self, node):
        cond_type = self.walk(node.cond)
        type_to_type_check(cond_type, "bool")

        self.sym_table.increment_scope()
        self.walk(node.body)
        self.sym_table.decrement_scope()

    # --- Statements ---

    def walk_declaration_stmt(self, node):
        # name:identifier ASSIGNMENT_OP value:expression
        var_name = node.name
        expected_type = self._infer_type_from_name(var_name)

        # Calculate type of the right-hand side
        actual_type = self.walk(node.value)

        # Validate compatibility
        type_to_type_check(actual_type, expected_type)

        # Register
        sym = Symbol(name=var_name, type_t=expected_type)
        self.sym_table.add_symbol(sym)

        print(f"Declared: {var_name} ({expected_type})")

    def walk_reassignment_stmt(self, node):
        # target:identifier [ index:indexing ] REASSIGNMENT_OP value:expression
        var_name = node.target
        sym = self.sym_table.get_symbol(var_name)

        if not sym:
            raise AgoSemanticException(
                f"Variable '{var_name}' not defined before assignment."
            )

        target_type = sym.type_t

        # If indexing is present, we are assigning to an element, so expected type changes
        # e.g., int_list -> int
        if node.index:
            if target_type == "int_list":
                target_type = "int"
            elif target_type == "float_list":
                target_type = "float"
            # ... handle other list types ...

        rhs_type = self.walk(node.value)
        type_to_type_check(rhs_type, target_type)
        print(f"Reassigned: {var_name}")

    # --- Expressions & Types ---
    # These methods MUST return a type string (e.g., "int", "float")

    def walk_identifier(self, node):
        # When an identifier appears in an expression
        sym = self.sym_table.get_symbol(str(node))
        if not sym:
            raise AgoSemanticException(f"Undefined variable used: {node}")
        return sym.type_t

    def walk_INTLIT(self, _):
        return "int"

    def walk_FLOATLIT(self, _):
        return "float"

    def walk_STR_LIT(self, _):
        return "string"

    def walk_TRUE(self, _):
        return "bool"

    def walk_FALSE(self, _):
        return "bool"

    def walk_pa(self, node):
        return self._handle_binop(node)

    def walk_pb(self, node):
        return self._handle_binop(node)

    def walk_pc(self, node):
        return self._handle_binop(node)

    def walk_pd(self, node):
        return self._handle_binop(node)

    def walk_pe(self, node):
        return self._handle_binop(node)

    def walk_pf(self, node):
        return self._handle_binop(node)

    def _handle_binop(self, node):
        # Generic handler for binary operations in the chain
        # If node has 'left', 'op', 'right'
        if hasattr(node, "left") and node.left is not None:
            left_type = self.walk(node.left)
            right_type = self.walk(node.right)
            op = node.op

            # Logic for Resulting Type
            # Comparison operators always return bool
            if op in ["==", ">", "<", ">=", "<=", "!="]:
                return "bool"

            # Math
            if left_type == "float" or right_type == "float":
                return "float"

            if left_type == "string" or right_type == "string":
                return "string"  # Concatenation

            return "int"  # Default fallback

        # If it's just a pass-through (the " | pb " part of the grammar rules)
        # TatSu model might just return the child, or we walk it.
        return self.walk(node)

    def walk_item(self, node):
        # Item has many options: id, int, float, paren, call...
        if node.id:
            return self.walk(node.id)
        if node.int:
            return "int"
        if node.float:
            return "float"
        if node.str:
            return "string"
        if node.paren:
            return self.walk(node.paren.expr)

        # If the node is just the wrapper, try walking children
        return self.walk(node.children()[0])
