#!/bin/bash
# Ago LLVM Compilation Script
# Usage: ./compile_ago.sh <input.ago> [output_binary]

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <input.ago> [output_binary]"
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_BINARY="${2:-a.out}"
TEMP_DIR=$(mktemp -d)

echo "==> Compiling Ago program: $INPUT_FILE"

# Step 1: Generate LLVM IR
echo "  [1/4] Generating LLVM IR..."
python3 main.py "$INPUT_FILE" > "$TEMP_DIR/program.ll"

# Step 2: Compile LLVM IR to object file
echo "  [2/4] Compiling LLVM IR to object file..."
llc "$TEMP_DIR/program.ll" -filetype=obj -o "$TEMP_DIR/program.o" 2>/dev/null || {
    echo "Error: llc not found. Trying with gcc assembly..."
    llc "$TEMP_DIR/program.ll" -o "$TEMP_DIR/program.s" 2>/dev/null || {
        echo "Error: Could not compile LLVM IR. Is LLVM installed?"
        exit 1
    }
    gcc -c "$TEMP_DIR/program.s" -o "$TEMP_DIR/program.o"
}

# Step 3: Ensure stdlib is compiled
echo "  [3/4] Compiling standard library..."
if [ ! -f "src/llvm/ago_stdlib.o" ]; then
    (cd src/llvm && gcc -O2 -Wall -Wextra -std=c11 -c ago_stdlib.c -o ago_stdlib.o)
fi

# Step 4: Link everything
echo "  [4/4] Linking..."
gcc "$TEMP_DIR/program.o" src/llvm/ago_stdlib.o -o "$OUTPUT_BINARY"

# Cleanup
rm -rf "$TEMP_DIR"

echo "==> Success! Binary created: $OUTPUT_BINARY"
echo "    Run with: ./$OUTPUT_BINARY"