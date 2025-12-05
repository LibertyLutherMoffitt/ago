# Makefile for Ago Standard Library

CC = clang
CFLAGS = -O2 -Wall -Wextra -std=c11
LLVM_FLAGS = -S -emit-llvm

# Source files
SOURCES = ago_stdlib.c
OBJECTS = ago_stdlib.o
LLVM_IR = ago_stdlib.ll

# Default target: build object file
all: $(OBJECTS)

# Build object file from C source
$(OBJECTS): $(SOURCES) ago_stdlib.h
	$(CC) $(CFLAGS) -c $(SOURCES) -o $(OBJECTS)

# Generate LLVM IR (for inspection/debugging)
llvm: $(LLVM_IR)

$(LLVM_IR): $(SOURCES) ago_stdlib.h
	$(CC) $(CFLAGS) $(LLVM_FLAGS) $(SOURCES) -o $(LLVM_IR)

# Clean build artifacts
clean:
	rm -f $(OBJECTS) $(LLVM_IR)

# Install (copy to a standard location - optional)
install: $(OBJECTS)
	@echo "Standard library built successfully"
	@echo "Object file: $(OBJECTS)"

.PHONY: all llvm clean install