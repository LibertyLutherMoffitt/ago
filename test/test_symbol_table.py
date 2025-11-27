# test_symbol_table.py

import pytest
from src.symbol_table import Symbol, SymbolTable


def test_symbol_defaults():
    s = Symbol(name="x", starting_type="int")

    assert s.name == "x"
    assert s.starting_type == "int"
    assert s.category == "var"
    assert s.scope == -1
    assert s.num_of_params == -1
    assert s.param_types is None
    assert s.return_type is None
    assert s.num_of_fields == -1
    assert s.field_types is None


def test_symbol_table_initial_state():
    st = SymbolTable()

    assert st.current_scope == 0
    assert 0 in st.scopes
    assert st.scopes[0] == {}


def test_increment_scope_creates_new_scope():
    st = SymbolTable()

    new_scope = st.increment_scope()

    assert new_scope == 1
    assert st.current_scope == 1
    assert 1 in st.scopes
    assert st.scopes[1] == {}


def test_add_symbol_success_and_retrieval():
    st = SymbolTable()
    sym = Symbol(name="x", starting_type="int")

    result = st.add_symbol(sym)

    assert result is True
    assert st.get_symbol("x") is sym


def test_add_symbol_duplicate_raises():
    st = SymbolTable()
    sym1 = Symbol(name="x", starting_type="int")
    sym2 = Symbol(name="x", starting_type="float")

    st.add_symbol(sym1)

    with pytest.raises(Exception, match="Variable name already exists"):
        st.add_symbol(sym2)


def test_get_symbol_nonexistent_returns_none():
    st = SymbolTable()

    assert st.get_symbol("does_not_exist") is None


def test_scopes_are_isolated():
    st = SymbolTable()
    sym_global = Symbol(name="x", starting_type="int")

    st.add_symbol(sym_global)
    assert st.get_symbol("x") is sym_global  # in scope 0

    st.increment_scope()
    # With your current implementation, lookups are only in current scope
    assert st.get_symbol("x") is None


def test_decrement_scope_raises_at_root():
    st = SymbolTable()

    with pytest.raises(Exception, match="Scope is -1. Unallowable."):
        st.decrement_scope()


def test_decrement_scope_moves_back_down():
    """
    This test encodes the *intended* behavior of decrement_scope:
    after incrementing to scope 1, decrement should bring us back to 0.
    """
    st = SymbolTable()
    st.increment_scope()
    assert st.current_scope == 1

    new_scope = st.decrement_scope()

    assert new_scope == 0
    assert st.current_scope == 0
