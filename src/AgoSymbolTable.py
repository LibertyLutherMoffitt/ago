from dataclasses import dataclass
from typing import Optional


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
            raise Exception("Variable name already exists in this scope. Unallowable.")
        self.scopes[self.current_scope][s.name] = s
        return True

    def get_symbol(self, n: str) -> Symbol | None:
        return self.scopes.get(self.current_scope).get(n)

    def change_symbol_type(self, n: str, new_type: str, scope: int = None):
        self.scopes.get(self.current_scope if scope is None else scope).get(
            n
        ).type_t = new_type
