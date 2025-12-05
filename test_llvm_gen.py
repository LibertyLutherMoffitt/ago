#!/usr/bin/env python3
"""
Test script for Ago LLVM Generator.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from AgoParser import AgoParser
from AgoLLVMGenerator import generate as generate_llvm

def test_simple_program():
    """Test generating LLVM IR for a simple Ago program."""
    ago_code = """
    des scribia(xa) {
        redeo xa + 1
    }

    xa := 5
    scribi(xa)
    """

    # Parse the code
    parser = AgoParser()
    ast = parser.parse(ago_code)

    print("AST:")
    print(ast)
    print()

    # Generate LLVM IR
    llvm_ir = generate_llvm(ast)

    print("Generated LLVM IR:")
    print(llvm_ir)

    # Save to file
    with open("test_output.ll", "w") as f:
        f.write(llvm_ir)

    print("\nSaved to test_output.ll")

if __name__ == "__main__":
    test_simple_program()