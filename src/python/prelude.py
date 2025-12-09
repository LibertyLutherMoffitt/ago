"""
Python prelude for transpiled Ago code.
This file provides runtime support for Ago's features that don't map
directly to Python, such as method chaining and built-in functions.
"""
import sys

# --- Built-in Functions ---

def dici(obj):
    """The Ago 'dici' function, which prints its argument."""
    print(obj)

def audies():
    """The Ago 'audies' function, which reads a line from stdin."""
    return input()

def apertu(filename):
    """The Ago 'apertu' function, which opens a file and returns a handle."""
    # In a real implementation, this would return a custom file handle object
    # with methods like 'read', 'write', etc.
    try:
        return open(filename, 'r+')
    except FileNotFoundError:
        return open(filename, 'w+')


def scribi(handle, content):
    """The Ago 'scribi' function, which writes content to a file handle."""
    if hasattr(handle, 'write'):
        handle.write(str(content))
    else:
        # Fallback for writing to a file by name
        with open(handle, 'w') as f:
            f.write(str(content))

def exei(code=0):
    """The Ago 'exei' function, which exits the program."""
    sys.exit(code)


# --- Method Chaining Support ---

class AgoMethodProxy:
    """
    A proxy object to intercept attribute access and reverse the call
    to achieve Ago's method chaining (`obj.method(args)` -> `method(obj, args)`).
    """
    def __init__(self, obj, func):
        self._obj = obj
        self._func = func
    
    def __call__(self, *args):
        # The actual call: func(obj, *args)
        return self._func(self._obj, *args)

def ago_getattr(obj, name):
    """
    Custom getattr to handle Ago's method chaining.
    If the attribute is a callable function in the global scope, it
    wraps it in a proxy. Otherwise, it returns the object's real attribute.
    """
    # Check globals for a function with that name
    if name in globals() and callable(globals()[name]):
        return AgoMethodProxy(obj, globals()[name])
        
    # Default attribute access for built-in methods of list, dict, str, etc.
    return getattr(obj, name)

# To make this work, the code generator transforms `obj.attr` into `ago_getattr(obj, 'attr')`
# and `obj.method(args)` into `ago_getattr(obj, 'method')(args)`.
# However, a simpler transformation is done directly in the generator for now:
# `obj.method(args)` becomes `method(obj, *args)`.

