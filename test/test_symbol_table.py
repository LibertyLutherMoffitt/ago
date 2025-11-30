# test_symbol_table.py

import pytest

from src.AgoSymbolTable import Symbol, SymbolTable, SymbolTableError


def test_symbol_defaults():
    s = Symbol(name="x", type_t="int")

    assert s.name == "x"
    assert s.type_t == "int"
    assert s.category == "var"
    assert s.scope is None  # Updated: default is None until added to table
    assert s.num_of_params == 0
    assert s.param_types == []
    assert s.return_type is None
    assert s.num_of_fields == 0
    assert s.field_types == []


def test_symbol_table_initial_state():
    st = SymbolTable()

    assert st.current_scope == 0
    assert 0 in st.scopes


def test_increment_scope_creates_new_scope():
    st = SymbolTable()

    new_scope = st.increment_scope()

    assert new_scope == 1
    assert st.current_scope == 1
    assert 1 in st.scopes
    assert st.scopes[1] == {}


def test_add_symbol_success_and_retrieval():
    st = SymbolTable()
    sym = Symbol(name="x", type_t="int")

    st.add_symbol(sym)

    assert st.get_symbol("x") is sym
    assert sym.scope == 0  # Symbol should have scope set when added


def test_add_symbol_duplicate_raises():
    st = SymbolTable()
    sym1 = Symbol(name="x", type_t="int")
    sym2 = Symbol(name="x", type_t="float")

    st.add_symbol(sym1)

    with pytest.raises(SymbolTableError, match="Variable name already exists"):
        st.add_symbol(sym2)


def test_get_symbol_nonexistent_returns_none():
    st = SymbolTable()

    assert st.get_symbol("does_not_exist") is None


def test_scopes_lookup_finds_parent_scope():
    """
    Symbols from parent scopes should be accessible in child scopes.
    This is standard lexical scoping behavior.
    """
    st = SymbolTable()
    sym_global = Symbol(name="x", type_t="int")

    st.add_symbol(sym_global)
    assert st.get_symbol("x") is sym_global  # in scope 0

    st.increment_scope()
    # Symbol from parent scope should still be accessible
    assert st.get_symbol("x") is sym_global


def test_scope_shadowing():
    """
    A symbol in a child scope shadows a symbol with the same name in parent scope.
    """
    st = SymbolTable()
    sym_global = Symbol(name="x", type_t="int")
    st.add_symbol(sym_global)

    st.increment_scope()
    sym_local = Symbol(name="x", type_t="float")
    st.add_symbol(sym_local)

    # Should get the local symbol, not the global one
    local_lookup = st.get_symbol("x")
    assert local_lookup is not None
    assert local_lookup is sym_local
    assert local_lookup.type_t == "float"

    # After leaving scope, should get global again
    st.decrement_scope()
    global_lookup = st.get_symbol("x")
    assert global_lookup is not None
    assert global_lookup is sym_global
    assert global_lookup.type_t == "int"


def test_decrement_scope_raises_at_root():
    st = SymbolTable()

    with pytest.raises(SymbolTableError, match="Cannot decrement scope below 0"):
        st.decrement_scope()


def test_decrement_scope_moves_back_down():
    """
    After incrementing to scope 1, decrement should bring us back to 0.
    """
    st = SymbolTable()
    st.increment_scope()
    assert st.current_scope == 1

    new_scope = st.decrement_scope()

    assert new_scope == 0
    assert st.current_scope == 0


def test_decrement_scope_clears_symbols():
    """
    When leaving a scope, symbols from that scope should be cleared.
    """
    st = SymbolTable()
    st.increment_scope()
    sym = Symbol(name="local_var", type_t="int")
    st.add_symbol(sym)

    assert st.get_symbol("local_var") is sym

    st.decrement_scope()

    # Symbol should no longer be accessible
    assert st.get_symbol("local_var") is None


def test_get_symbol_current_scope_only():
    """
    Test the current-scope-only lookup method.
    """
    st = SymbolTable()
    sym_global = Symbol(name="x", type_t="int")
    st.add_symbol(sym_global)

    st.increment_scope()

    # get_symbol finds it in parent
    assert st.get_symbol("x") is sym_global
    # get_symbol_current_scope_only does not
    assert st.get_symbol_current_scope_only("x") is None


def test_symbol_exists_methods():
    """
    Test the existence check methods.
    """
    st = SymbolTable()
    sym = Symbol(name="x", type_t="int")
    st.add_symbol(sym)

    assert st.symbol_exists("x") is True
    assert st.symbol_exists("y") is False
    assert st.symbol_exists_in_current_scope("x") is True

    st.increment_scope()
    assert st.symbol_exists("x") is True  # Parent scope
    assert st.symbol_exists_in_current_scope("x") is False  # Not in current scope


def test_nested_scopes():
    """
    Test multiple levels of nested scopes.
    """
    st = SymbolTable()

    # Global scope
    st.add_symbol(Symbol(name="global_var", type_t="int"))
    assert st.current_scope == 0

    # First nested scope
    st.increment_scope()
    st.add_symbol(Symbol(name="level1_var", type_t="float"))
    assert st.current_scope == 1
    assert st.get_symbol("global_var") is not None
    assert st.get_symbol("level1_var") is not None

    # Second nested scope
    st.increment_scope()
    st.add_symbol(Symbol(name="level2_var", type_t="bool"))
    assert st.current_scope == 2
    assert st.get_symbol("global_var") is not None
    assert st.get_symbol("level1_var") is not None
    assert st.get_symbol("level2_var") is not None

    # Exit second scope
    st.decrement_scope()
    assert st.current_scope == 1
    assert st.get_symbol("global_var") is not None
    assert st.get_symbol("level1_var") is not None
    assert st.get_symbol("level2_var") is None  # No longer accessible

    # Exit first scope
    st.decrement_scope()
    assert st.current_scope == 0
    assert st.get_symbol("global_var") is not None
    assert st.get_symbol("level1_var") is None
    assert st.get_symbol("level2_var") is None
