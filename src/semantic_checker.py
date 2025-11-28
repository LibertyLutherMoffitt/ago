from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from tatsu.semantics import Semantics

from symbol_table import Symbol, SymbolTable


# ---------- Error types ----------

@dataclass
class SemanticError:
    message: str
    line: Optional[int] = None
    col: Optional[int] = None
    node: Any = None

    def __str__(self) -> str:
        location = ""
        if self.line is not None and self.col is not None:
            location = f"(line {self.line}, col {self.col}) "
        return f"{location}{self.message}"


class AgoSemanticException(Exception):
    """Use this if you ever want to abort immediately on first semantic error."""
    pass

# --------- Helper functs ---------

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
    return endings_to_str[ending]

def type_to_type_check(current: str, to: str) -> True:
    acceptables = {
        "int": ["float", "bool", "string"],
        "float": ["int", "bool", "string"],
        "bool": ["int", "float", "string"],
        "int_list": ["int", "string", "float_list", "bool_list", "string_list"],
        "float_list": ["int", "string", "int_list", "bool_list", "string_list"],
        "bool_list": ["int", "string", "int_list", "float_list", "string_list"],
        "string_list": ["int", "string", "int_list", "float_list", "bool_list"],
        "string": ["int", "float", "bool", "string_list"],
        "struct": ["string", "int"],
        "list_list": ["int"],
    }

    if current not in acceptables:
        raise AgoSemanticException(f"{current} is not an acceptable type ({','.join(acceptables.keys())})")
    
    if to not in acceptables:
        raise AgoSemanticException(f"{to} is not an acceptable type ({','.join(acceptables.keys())})")

    if to not in acceptables[current]:
        raise AgoSemanticException(f"{to} is not a valid conversion for {current}. Acceptable conversion: [{','.join(acceptables[current])}]")

    return True

# ---------- Semantics class ----------

class AgoSemantics(Semantics):
    """
    TatSu semantics class that performs semantic checking while the parse runs.

    - Manages a SymbolTable with scopes.
    - Collects SemanticError instances in self.errors.
    - Provides hooks for rule-specific checks (declaration, assignment, calls, etc).

    This is meant to be extended and filled in as your language spec solidifies.
    """

    def __init__(self, symtab: Optional[SymbolTable] = None, fail_fast: bool = False):
        super().__init__()
        self.symtab: SymbolTable = symtab or SymbolTable()
        self.errors: List[SemanticError] = []
        self.fail_fast: bool = fail_fast

        # optional: track context
        self.current_function: Optional[str] = None
        self.loop_depth: int = 0  # to validate BREAK/CONTINUE

    # ---------- helper methods ----------

    def location_of(self, node: Any) -> tuple[Optional[int], Optional[int]]:
        """Extract (line, col) from TatSu's parseinfo if available."""
        parseinfo = getattr(node, 'parseinfo', None)
        if parseinfo is None:
            return None, None
        return getattr(parseinfo, 'line', None), getattr(parseinfo, 'col', None)

    def report_error(self, message: str, node: Any) -> None:
        line, col = self.location_of(node)
        err = SemanticError(message=message, line=line, col=col, node=node)
        self.errors.append(err)
        if self.fail_fast:
            raise AgoSemanticException(str(err))

    # --- scope management ---

    def enter_scope(self) -> None:
        self.symtab.increment_scope()

    def exit_scope(self) -> None:
        # You might want to do additional checks on exiting scope later
        self.symtab.decrement_scope()

    # --- symbol helpers ---

    def declare_symbol(
        self,
        name: str,
        type_t: str = "unknown",
        category: str = "var",
        node: Any = None,
    ) -> None:
        """Declare a new symbol in the current scope, recording errors for duplicates."""
        try:
            sym = Symbol(
                name=name,
                type_t=type_t,
                category=category,
                scope=self.symtab.current_scope,
            )
            self.symtab.add_symbol(sym)
        except Exception as ex:
            # SymbolTable should already raise on duplicates
            self.report_error(str(ex), node or name)

    def require_symbol(self, name: str, node: Any) -> Optional[Symbol]:
        """Ensure a symbol exists in the current scope (or possibly outer scopes if you extend)."""
        # Right now SymbolTable.get_symbol only checks current scope.
        # If you implement outer-scope lookup, call that here instead.
        sym = self.symtab.get_symbol(name)
        if sym is None:
            self.report_error(f"Use of undeclared identifier '{name}'", node)
        return sym

    # ---------- top-level rule ----------

    def principio(self, ast):
        """
        Entry point for the program.

        TatSu will already walk subrules; here you can:
        - reset semantic state
        - perform post-pass checks if needed
        """
        # Optionally reset state each parse:
        self.symtab = self.symtab or SymbolTable()
        self.current_function = None
        self.loop_depth = 0

        # Let default walker handle children
        return self.walk(ast)

    # ---------- declarations & assignments ----------

    def declaration_stmt(self, ast):
        """
        name:identifier ASSIGNMENT_OP value:expression

        Here we:
        - declare the name in the current scope

                """
        name = ast.name

        
        
        # TODO: infer type from ast.value later
        self.declare_symbol(name=name, type_t="unknown", category="var", node=ast)
        self.walk(ast.value)
        return ast

    def reassignment_stmt(self, ast):
        """
        target:identifier [ index:indexing ] REASSIGNMENT_OP value:expression

        Here we:
        - ensure the identifier was declared
        - eventually do type compatibility checks (TODO)
        """
        target_name = ast.target
        self.require_symbol(target_name, node=ast)
        if ast.index is not None:
            self.walk(ast.index)
        self.walk(ast.value)
        return ast

    # ---------- control flow ----------

    def if_stmt(self, ast):
        """
        IF cond:expression then:block
            elifs:{ ELSE elif_cond:expression elif_body:block }*
            [ ELSE else_body:block ]
        """
        # condition
        self.walk(ast.cond)

        # then branch (new block)
        self.walk(ast.then)

        # elif branches
        for elif_pair in ast.elifs or []:
            # each element is something like {'elif_cond': ..., 'elif_body': ...}
            self.walk(elif_pair.elif_cond)
            self.walk(elif_pair.elif_body)

        # else branch
        if ast.else_body is not None:
            self.walk(ast.else_body)

        return ast

    def while_stmt(self, ast):
        """
        WHILE cond:expression body:block

        We:
        - check condition
        - enter a loop context for break/continue validation
        """
        self.walk(ast.cond)
        self.loop_depth += 1
        try:
            self.walk(ast.body)
        finally:
            self.loop_depth -= 1
        return ast

    def for_stmt(self, ast):
        """
        FOR iterator:expression IN iterable:expression body:block

        Common pattern:
        - treat `iterator` as a declaration (if it's an identifier)
        - check iterable expression
        """
        # If iterator is a bare identifier, you might treat it as a new loop var.
        iterator = ast.iterator
        # Very simple heuristic: TatSu 'expression' node might be just an identifier string
        if hasattr(iterator, 'id'):  # if you later normalize AST nodes
            self.declare_symbol(iterator.id, type_t="unknown", category="var", node=iterator)

        self.walk(ast.iterable)

        self.loop_depth += 1
        try:
            self.walk(ast.body)
        finally:
            self.loop_depth -= 1
        return ast

    # ---------- function & lambda declarations ----------

    def method_decl(self, ast):
        """
        DEF name:identifier LPAREN [ params:expression_list ] RPAREN body:block

        Here we:
        - declare the function name in the current (outer) scope
        - open a new scope for parameters + body
        - register parameters as symbols
        """
        func_name = ast.name
        self.declare_symbol(
            name=func_name,
            type_t="func",
            category="function",
            node=ast,
        )

        # Enter function scope
        prev_function = self.current_function
        self.current_function = func_name
        self.enter_scope()
        try:
            # register parameters (TODO: a real param node instead of expression_list)
            if ast.params is not None:
                self._declare_params_from_expression_list(ast.params)

            # walk the body
            self.walk(ast.body)
        finally:
            self.exit_scope()
            self.current_function = prev_function

        return ast

    def lambda_decl(self, ast):
        """
        DEF [ LPAREN [ params:expression_list ] RPAREN ] body:block

        Similar to method_decl but anonymous.
        Usually creates a new scope for params + body.
        """
        self.enter_scope()
        try:
            if getattr(ast, 'params', None) is not None:
                self._declare_params_from_expression_list(ast.params)
            self.walk(ast.body)
        finally:
            self.exit_scope()
        return ast

    def _declare_params_from_expression_list(self, expr_list):
        """
        Helper: your grammar uses `expression_list` for params, but in practice,
        you'll probably restrict it to identifiers. For now, we just try to register
        plain identifiers and ignore more complex expressions.
        """
        # expr_list has .first and .rest according to grammar
        to_visit = [expr_list.first]
        to_visit.extend(rest.expr for rest in (expr_list.rest or []))

        for expr in to_visit:
            # TODO: tighten this: treat only identifiers as params, error otherwise.
            if hasattr(expr, 'id'):  # if you normalize AST items
                param_name = expr.id
                self.declare_symbol(param_name, type_t="unknown", category="param", node=expr)
            # else: you might want to emit an error for non-identifier params

    # ---------- calls ----------

    def call_stmt(self, ast):
        """
        [ recv:(receiver:item) PERIOD ]
        first:nodotcall_stmt
        chain:{ PERIOD more:nodotcall_stmt }*
        """
        # receiver may be something like an identifier or more complex expression
        if ast.recv is not None:
            self.walk(ast.recv)

        self.walk(ast.first)

        for c in ast.chain or []:
            self.walk(c.more)

        return ast

    def nodotcall_stmt(self, ast):
        """
        func:identifier LPAREN [ args:expression_list ] RPAREN
        """
        func_name = ast.func
        self.require_symbol(func_name, node=ast)

        if ast.args is not None:
            self.walk(ast.args)

        # TODO: add arity/type checks when you track function signatures in Symbol
        return ast

    # ---------- blocks & statement lists ----------

    def block(self, ast):
        """
        LBRACE [ nl ] [ stmts:statement_list ] [ nl ] RBRACE

        You can choose whether a block implies a new scope or not.
        In this framework, we *do not* automatically open a new scope here,
        because functions already do it in method_decl/lambda_decl/loops/etc.
        If you want block scope (like C), you can uncomment scope handling.
        """
        # If you want every block to have its own scope, uncomment:
        # self.enter_scope()
        # try:
        #     if ast.stmts is not None:
        #         self.walk(ast.stmts)
        # finally:
        #     self.exit_scope()

        if ast.stmts is not None:
            self.walk(ast.stmts)
        return ast

    def statement_list(self, ast):
        """
        first:statement
        rest:{ { nl }+ statement }*
        """
        self.walk(ast.first)
        for r in ast.rest or []:
            self.walk(r)
        return ast

    # ---------- simple statements ----------

    def PASS(self, ast):
        # 'omitto' – usually no semantic effect.
        return ast

    def BREAK(self, ast):
        # 'frio' – must be inside a loop.
        if self.loop_depth <= 0:
            self.report_error("'frio' (break) outside of loop", ast)
        return ast

    def CONTINUE(self, ast):
        # 'pergo' – must be inside a loop.
        if self.loop_depth <= 0:
            self.report_error("'pergo' (continue) outside of loop", ast)
        return ast

    def return_stmt(self, ast):
        """
        RETURN value:expression

        Optionally verify we're inside a function/lambda.
        """
        if self.current_function is None:
            self.report_error("'redeo' (return) outside of function", ast)
        self.walk(ast.value)
        # TODO: record return type / check against function signature
        return ast

    # ---------- expressions ----------

    # You can override specific expression-level rules if you want to do
    # type propagation; for now we just walk them so child semantics run.

    def expression(self, ast):
        return self.walk(ast)

    def pa(self, ast):
        return self.walk(ast)

    def pb(self, ast):
        return self.walk(ast)

    def pc(self, ast):
        return self.walk(ast)

    def pd(self, ast):
        return self.walk(ast)

    def pe(self, ast):
        return self.walk(ast)

    def pf(self, ast):
        return self.walk(ast)

    def pg(self, ast):
        return self.walk(ast)

    def ph(self, ast):
        return self.walk(ast)

    def list(self, ast):
        # List literal – walk items for their semantics.
        for it in ast:
            self.walk(it)
        return ast

    def mapstruct(self, ast):
        self.walk(ast.mapcontent)
        return ast

    def mapcontent(self, ast):
        """
        | (STR_LIT | identifier) COLON item COMMA mapcontent
        | (STR_LIT | identifier) COLON item
        """
        # KEY: ast[0], VALUE: ast[1] in TatSu's default AST, or named attributes if you define them.
        # For now, just walk value and recurse if present.
        # Exact field names depend on how TatSu built the AST; adjust as needed.
        # This is just a framework placeholder.
        for v in ast.values() if isinstance(ast, dict) else []:
            self.walk(v)
        return ast

    def item(self, ast):
        # Default: walk everything inside. Fill in special cases as needed.
        return self.walk(ast)
