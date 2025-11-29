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
    # For functions
    num_of_params: Optional[int] = -1
    param_types: Optional[list[str]] = None
    return_type: Optional[str] = None
    # For structs
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
        self.loop_depth = 0
        self.current_function: Optional[Symbol] = None

    def _infer_type_from_name(self, name: str) -> str:
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

    # --- Scope & Context Management ---

    def walk_method_decl(self, node):
        func_name = node.name
        return_type = self._infer_type_from_name(func_name)
        param_symbols = self._get_params_as_symbols(node.params)
        param_types = [p.type_t for p in param_symbols]

        func_symbol = Symbol(
            name=func_name,
            type_t="function",
            category="func",
            return_type=return_type,
            param_types=param_types,
            num_of_params=len(param_symbols),
        )
        self.sym_table.add_symbol(func_symbol)

        previous_function = self.current_function
        self.current_function = func_symbol
        self.sym_table.increment_scope()

        for p_sym in param_symbols:
            self.sym_table.add_symbol(p_sym)

        self.walk(node.body)

        self.sym_table.decrement_scope()
        self.current_function = previous_function

    def _get_params_as_symbols(self, params_node) -> list[Symbol]:
        if not params_node:
            return []
        items = []
        if hasattr(params_node, "first"):
            items.append(params_node.first)
        if hasattr(params_node, "rest"):
            for item in params_node.rest:
                items.append(item.expr)
        symbols = []
        for item in items:
            name = item.id if hasattr(item, "id") else str(item)
            t_type = self._infer_type_from_name(name)
            symbols.append(Symbol(name=name, type_t=t_type))
        return symbols

    def walk_if_stmt(self, node):
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

        self.loop_depth += 1
        self.sym_table.increment_scope()
        self.walk(node.body)
        self.sym_table.decrement_scope()
        self.loop_depth -= 1

    def walk_for_stmt(self, node):
        iterable_type = self.walk(node.iterable)
        if "list" not in iterable_type:
            raise AgoSemanticException(
                f"Cannot iterate over non-list type '{iterable_type}'."
            )

        iterator_type = (
            "list"
            if iterable_type == "list_list"
            else iterable_type.replace("_list", "")
        )

        self.loop_depth += 1
        self.sym_table.increment_scope()

        iterator_name = (
            node.iterator.id if hasattr(node.iterator, "id") else str(node.iterator)
        )
        expected_iterator_type = self._infer_type_from_name(iterator_name)
        if expected_iterator_type != iterator_type:
            raise AgoSemanticException(
                f"Iterator '{iterator_name}' suffix implies type '{expected_iterator_type}', but iterable is type '{iterator_type}'."
            )
        self.sym_table.add_symbol(Symbol(name=iterator_name, type_t=iterator_type))

        self.walk(node.body)

        self.sym_table.decrement_scope()
        self.loop_depth -= 1

    # --- Statements ---

    def walk_declaration_stmt(self, node):
        var_name = node.name
        expected_type = self._infer_type_from_name(var_name)
        actual_type = self.walk(node.value)
        type_to_type_check(actual_type, expected_type)
        self.sym_table.add_symbol(Symbol(name=var_name, type_t=expected_type))

    def walk_reassignment_stmt(self, node):
        var_name = node.target
        sym = self.sym_table.get_symbol(var_name)
        if not sym:
            raise AgoSemanticException(f"Variable '{var_name}' not defined.")

        target_type = sym.type_t
        if node.index:
            if "_list" in target_type:
                target_type = target_type.replace("_list", "")
            else:
                raise AgoSemanticException(
                    f"Cannot index non-list type '{sym.type_t}'."
                )

        rhs_type = self.walk(node.value)
        type_to_type_check(rhs_type, target_type)

    def walk_return_stmt(self, node):
        if self.current_function is None:
            raise AgoSemanticException(
                "'redeo' (return) cannot be used outside a function."
            )

        if node.value:
            returned_type = self.walk(node.value)
            expected_type = self.current_function.return_type
            assert expected_type is not None
            type_to_type_check(returned_type, expected_type)
        elif (
            self.current_function.return_type != "void"
        ):  # Assuming 'void' type for functions with no return value
            raise AgoSemanticException(
                f"Function '{self.current_function.name}' expects return type '{self.current_function.return_type}', but got no value."
            )

    def walk_BREAK(self, _):
        if self.loop_depth <= 0:
            raise AgoSemanticException("'frio' (break) cannot be used outside a loop.")

    def walk_CONTINUE(self, _):
        if self.loop_depth <= 0:
            raise AgoSemanticException(
                "'pergo' (continue) cannot be used outside a loop."
            )

    # --- Expressions & Types (MUST return a type string) ---

    def walk_identifier(self, node):
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

    def walk_list(self, node):
        if not node.items:
            return "list_list"
        elem_types = {self.walk(it) for it in node.items}
        return f"{elem_types.pop()}_list" if len(elem_types) == 1 else "list_list"

    def walk_nodotcall_stmt(self, node):
        func_name = node.func
        func_sym = self.sym_table.get_symbol(func_name)
        if not func_sym or func_sym.category != "func":
            raise AgoSemanticException(f"'{func_name}' is not a function.")

        arg_types = []
        if node.args:
            arg_nodes = [node.args.first] + [
                item.expr for item in (node.args.rest or [])
            ]
            arg_types = [self.walk(arg_node) for arg_node in arg_nodes]

        if len(arg_types) != func_sym.num_of_params:
            raise AgoSemanticException(
                f"Function '{func_name}' expects {func_sym.num_of_params} arguments, but got {len(arg_types)}."
            )

        for arg_t, param_t in zip(arg_types, func_sym.param_types or []):
            type_to_type_check(arg_t, param_t)

        return func_sym.return_type

    def _walk_binop(self, node, valid_ops, next_level, type_rule):
        if not hasattr(node, "op"):
            return self.walk(getattr(node, next_level))

        left_type = self.walk(node.left)
        right_type = self.walk(node.right)
        return type_rule(left_type, right_type, node.op)

    def walk_pa(self, node):  # et, vel
        return self._walk_binop(
            node,
            ["et", "vel"],
            "pb",
            lambda left, right, op: "bool"
            if left == "bool" and right == "bool"
            else AgoSemanticException(
                f"Boolean op '{op}' requires bools, got '{left}' and '{right}'."
            ),
        )

    def walk_pb(self, node):  # Comparisons
        return self._walk_binop(
            node,
            ["==", "!=", "<", ">", "<=", ">="],
            "pc",
            lambda left, right, op: "bool"
            if (left in ["int", "float"] and right in ["int", "float"]) or left == right
            else AgoSemanticException(f"Cannot compare '{left}' and '{right}'."),
        )

    def walk_pc(self, node):  # +, -
        def rule(left, right, op):
            if op == "+" and ("string" in left or "string" in right):
                return "string"
            if left in ["int", "float"] and right in ["int", "float"]:
                return "float" if "float" in left or "float" in right else "int"
            raise AgoSemanticException(f"Cannot use '{op}' on '{left}' and '{right}'.")

        return self._walk_binop(node, ["+", "-"], "pd", rule)

    def walk_pd(self, node):  # *, /, %
        def rule(left, right, op):
            if left in ["int", "float"] and right in ["int", "float"]:
                return "float" if "float" in left or "float" in right else "int"
            raise AgoSemanticException(f"Cannot use '{op}' on '{left}' and '{right}'.")

        return self._walk_binop(node, ["*", "/", "%"], "pe", rule)

    def walk_pe(self, node):  # Unary
        if node.op:
            right_type = self.walk(node.right)
            if node.op == "non" and right_type == "bool":
                return "bool"
            if node.op in ["+", "-"] and right_type in ["int", "float"]:
                return right_type
            raise AgoSemanticException(
                f"Cannot apply unary '{node.op}' to '{right_type}'."
            )
        return self.walk(node.pf)

    def walk_pf(self, node):  # item, call, index
        # This level is more complex, might not be a simple binop
        # Assuming grammar is `item (call_op | index_op)*`
        # For now, just walk the item
        return self.walk(node.item)

    def walk_item(self, node):
        if hasattr(node, "id"):
            return self.walk_identifier(node.id)
        if hasattr(node, "int"):
            return "int"
        if hasattr(node, "float"):
            return "float"
        if hasattr(node, "str"):
            return "string"
        if hasattr(node, "paren"):
            return self.walk(node.paren.expr)
        if hasattr(node, "list"):
            return self.walk_list(node.list)
        if hasattr(node, "call"):
            return self.walk_nodotcall_stmt(node.call)

        # Fallback for simple literals wrapped in item
        if hasattr(node, "TRUE"):
            return "bool"
        if hasattr(node, "FALSE"):
            return "bool"

        # Default walk if structure is unknown
        if node.children:
            return self.walk(node.children[0])
        return "Any"

