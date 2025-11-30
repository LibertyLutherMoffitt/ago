"""
Ago Symbol Table - Manages symbols across scopes for semantic analysis.
"""

from dataclasses import dataclass, field
from typing import Optional


class SymbolTableError(Exception):
    """Raised when a symbol table operation fails."""

    pass


@dataclass
class Symbol:
    """Represents a symbol (variable, function, parameter) in the symbol table."""

    name: str
    type_t: str
    category: str = "var"  # "var", "func", "param"
    scope: Optional[int] = None
    # For functions
    num_of_params: int = 0
    param_types: list[str] = field(default_factory=list)
    return_type: Optional[str] = None
    # For structs
    num_of_fields: int = 0
    field_types: list[str] = field(default_factory=list)
    field_names: list[str] = field(default_factory=list)


class SymbolTable:
    """
    A hierarchical symbol table supporting nested scopes.

    Scopes are tracked by depth level. When entering a new scope (e.g., function body,
    loop body, if block), increment_scope() is called. When exiting, decrement_scope()
    is called and the scope's symbols are cleared.

    Symbol lookup searches from current scope up to global scope (0).
    """

    def __init__(self):
        # Each scope level maps to a dict of {name: Symbol}
        self.scopes: dict[int, dict[str, Symbol]] = {0: {}}
        self.current_scope: int = 0

    def increment_scope(self) -> int:
        """Enter a new nested scope. Returns the new scope level."""
        self.current_scope += 1
        if self.current_scope not in self.scopes:
            self.scopes[self.current_scope] = {}
        return self.current_scope

    def decrement_scope(self) -> int:
        """
        Exit the current scope, clearing its symbols.
        Returns the new (outer) scope level.
        Raises SymbolTableError if already at global scope.
        """
        if self.current_scope == 0:
            raise SymbolTableError("Cannot decrement scope below 0 (global scope).")
        # Clear symbols from the scope we're leaving
        self.scopes[self.current_scope] = {}
        self.current_scope -= 1
        return self.current_scope

    def add_symbol(self, symbol: Symbol) -> None:
        """
        Add a symbol to the current scope.
        Raises SymbolTableError if a symbol with the same name already exists
        in the current scope.
        """
        if symbol.name in self.scopes[self.current_scope]:
            raise SymbolTableError(
                f"Variable name already exists in this scope: '{symbol.name}'"
            )
        symbol.scope = self.current_scope
        self.scopes[self.current_scope][symbol.name] = symbol

    def get_symbol(self, name: str) -> Optional[Symbol]:
        """
        Look up a symbol by name, searching from current scope up to global scope.
        Returns None if not found in any accessible scope.
        """
        search_scope = self.current_scope
        while search_scope >= 0:
            if search_scope in self.scopes and name in self.scopes[search_scope]:
                return self.scopes[search_scope][name]
            search_scope -= 1
        return None

    def get_symbol_current_scope_only(self, name: str) -> Optional[Symbol]:
        """
        Look up a symbol only in the current scope (not parent scopes).
        Useful for checking re-declarations.
        """
        return self.scopes.get(self.current_scope, {}).get(name)

    def get_all_visible_symbols(self) -> dict[str, Symbol]:
        """
        Get all symbols visible from the current scope up to global.
        Symbols in inner scopes shadow those in outer scopes.
        """
        visible_symbols = {}
        search_scope = 0
        while search_scope <= self.current_scope:
            if search_scope in self.scopes:
                visible_symbols.update(self.scopes[search_scope])
            search_scope += 1
        return visible_symbols

    def update_symbol(self, symbol: Symbol) -> None:
        """
        Update an existing symbol. Searches all scopes.
        Raises SymbolTableError if symbol doesn't exist.
        """
        search_scope = self.current_scope
        while search_scope >= 0:
            if search_scope in self.scopes and symbol.name in self.scopes[search_scope]:
                self.scopes[search_scope][symbol.name] = symbol
                return
            search_scope -= 1
        raise SymbolTableError(f"Cannot update non-existent symbol: '{symbol.name}'")

    def symbol_exists(self, name: str) -> bool:
        """Check if a symbol exists in any accessible scope."""
        return self.get_symbol(name) is not None

    def symbol_exists_in_current_scope(self, name: str) -> bool:
        """Check if a symbol exists in the current scope only."""
        return self.get_symbol_current_scope_only(name) is not None

    def remove_symbol_from_current_scope(self, name: str) -> bool:
        """Remove a symbol from the current scope. Returns True if removed."""
        if name in self.scopes.get(self.current_scope, {}):
            del self.scopes[self.current_scope][name]
            return True
        return False
