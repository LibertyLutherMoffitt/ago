# Ago LLVM Backend Migration Plan

## Overview
This document outlines the plan to migrate the Ago compiler from generating Rust code to generating LLVM IR directly. This enables direct compilation to machine code without the Rust toolchain dependency.

## Current Status: ✅ Basic Implementation Complete

### ✅ Completed Components

#### 1. Core Architecture
- **AgoLLVMGenerator class** ([`src/AgoLLVMGenerator.py`](src/AgoLLVMGenerator.py:132)): Main code generator
- **LLVMContext class** ([`src/AgoLLVMGenerator.py`](src/AgoLLVMGenerator.py:70)): IR emission and temp variable management
- **Type system mappings** ([`src/AgoLLVMGenerator.py`](src/AgoLLVMGenerator.py:24-39)): Ago types → LLVM types

#### 2. Type Mappings
```python
AGO_TYPE_TO_LLVM = {
    "int": "i64",                    # 64-bit integer
    "float": "double",               # Double precision float
    "bool": "i1",                    # 1-bit boolean
    "string": "{i64, i8*}",         # {length, data pointer}
    "int_list": "{i64, i64*}",      # {length, data pointer}
    "float_list": "{i64, double*}",  # {length, data pointer}
    "struct": "i8*",                 # Opaque pointer
    "function": "i8*",               # Function pointer
    "null": "i8*",                   # Null pointer
}
```

#### 3. Working Features
- ✅ **Function definitions** with typed parameters
- ✅ **Variable declarations** with type inference from name suffixes
- ✅ **Binary operations** (arithmetic: +, -, *, /)
- ✅ **Function calls** (both stdlib and user-defined)
- ✅ **Return statements**
- ✅ **Control flow**: if/else, while loops, for loops
- ✅ **Expression evaluation** with value wrapper unwrapping
- ✅ **Parameter passing** by value

#### 4. Test Results
Current test program:
```ago
des scribia(xa) {
    redeo xa + 1
}

xa := 5
scribi(xa)
```

Generates correct LLVM IR:
```llvm
define i64 @scribia(i64 %xa) {
  %0 = call i64 @ago_add(i64 %xa, i64 1)
  ret i64 %0
}

define i32 @main() {
  %xa = alloca i64
  store i64 5, i64* %xa
  %1 = load i64, i64* %xa
  call void @ago_print_int(i64 %1)
  ret i32 0
}
```

---

## 🔄 Remaining Work

### ✅ Phase 1.5: Operators Complete (Just Completed)

#### Comparison Operators - DONE ✅
- [x] Implemented `>`, `>=`, `<=`, `!=` operators
- [x] Added stdlib function declarations
- [x] All comparison operators now working

#### Logical Operators - DONE ✅
- [x] Implemented `et` (and) operator
- [x] Implemented `vel` (or) operator
- [x] Added `non` (not) operator support
- [x] Added stdlib function declarations

#### Arithmetic Operators - DONE ✅
- [x] Added modulo `%` operator
- [x] All basic arithmetic now complete

### Phase 1: Complete Expression System (High Priority)

#### 1.1 Method Chains & Postfix Operations
**Status**: Partially implemented  
**Files**: [`src/AgoLLVMGenerator.py`](src/AgoLLVMGenerator.py:376-386)

**Tasks**:
- [ ] Implement indexing operations (`list[0]`, `struct.field`)
- [ ] Implement method chaining (`value.method1().method2()`)
- [ ] Handle field access on structs
- [ ] Support chained indexing (`grid[x][y]`)

**Example**:
```ago
listum := [1, 2, 3]
xa := listum[0]           # Indexing
resulta := xa.addium(5)   # Method call
```

#### 1.2 Lambda Functions
**Status**: Not started  
**Reference**: [`src/AgoCodeGenerator.py`](src/AgoCodeGenerator.py:391-443)

**Tasks**:
- [ ] Generate LLVM function pointers for lambdas
- [ ] Implement closure capture (if needed)
- [ ] Handle `id` parameter in lambdas
- [ ] Support lambda calls with argument arrays

**Example**:
```ago
mapo := des { id + 1 }
resulta := mapo(5)  # Should return 6
```

#### 1.3 Type Casting
**Status**: Not started  
**Reference**: [`src/AgoCodeGenerator.py`](src/AgoCodeGenerator.py:135-164)

**Tasks**:
- [ ] Implement `.as_type()` equivalent in LLVM
- [ ] Handle stem-based variable casting (`xa` → `xes` for int→string)
- [ ] Support all cast combinations from Rust implementation

**Example**:
```ago
xa := 42
xes := xa  # Cast int to string via name suffix
```

---

### Phase 2: Memory Management (High Priority)

#### 2.1 Heap Allocation
**Status**: malloc/free declared but not used  
**Files**: [`src/AgoLLVMGenerator.py`](src/AgoLLVMGenerator.py:804-805)

**Tasks**:
- [ ] Implement string allocation and deallocation
- [ ] Implement list allocation (dynamic arrays)
- [ ] Implement struct allocation (hash maps)
- [ ] Add reference counting or garbage collection strategy

**Approach**:
```llvm
; String allocation example
%str_data = call i8* @malloc(i64 %length)
; ... copy data ...
%str = insertvalue {i64, i8*} undef, i64 %length, 0
%str = insertvalue {i64, i8*} %str, i8* %str_data, 1
```

#### 2.2 String Operations
**Status**: Basic string literals work  
**Reference**: [`src/AgoLLVMGenerator.py`](src/AgoLLVMGenerator.py:231-245)

**Tasks**:
- [ ] String concatenation
- [ ] String indexing (character access)
- [ ] String slicing
- [ ] String to char list conversion

---

### Phase 3: Collection Types (Medium Priority)

#### 3.1 List Operations
**Status**: Not started  
**Reference**: [`src/rust/src/collections.rs`](src/rust/src/collections.rs)

**Tasks**:
- [ ] List literal creation
- [ ] List indexing (get/set)
- [ ] List append/insert/remove
- [ ] List iteration
- [ ] Typed list validation

**LLVM Structure**:
```llvm
; List: {i64 length, T* data}
%list = type {i64, i64*}  ; For int_list
```

#### 3.2 Struct/Map Operations
**Status**: Not started

**Tasks**:
- [ ] Struct literal creation
- [ ] Field access by name
- [ ] Field assignment
- [ ] Key iteration
- [ ] Hash map implementation or use external library

---

### Phase 4: Standard Library (High Priority) - ✅ MOSTLY COMPLETE

#### 4.1 Core Stdlib Functions
**Status**: ✅ C Implementation Complete
**Files**:
- [`src/llvm/ago_stdlib.c`](src/llvm/ago_stdlib.c) - C implementation
- [`src/llvm/ago_stdlib.h`](src/llvm/ago_stdlib.h) - Header file
- [`src/llvm/Makefile`](src/llvm/Makefile) - Build system

**Implemented in C**: ✅
- ✅ `ago_add`, `ago_subtract`, `ago_multiply`, `ago_divide`, `ago_modulo`
- ✅ `ago_equal`, `ago_not_equal`, `ago_less_than`, `ago_greater_than`, `ago_less_equal`, `ago_greater_equal`
- ✅ `ago_logical_and`, `ago_logical_or`, `ago_logical_not`
- ✅ `ago_print_int`, `ago_print_float`, `ago_print_bool`, `ago_print_string`
- ✅ `ago_string_concat`, `ago_string_length`, `ago_string_get`
- ✅ `ago_list_int_new`, `ago_list_int_get`, `ago_list_int_set`, `ago_list_int_append`, `ago_list_int_free`
- ✅ `ago_read_line`, `ago_exit`, `ago_type_name`

**Still Needed**:
- [ ] `ago_struct_get` - Get field from struct (hash map)
- [ ] `ago_struct_set` - Set field in struct (hash map)
- [ ] `ago_file_open` - Open file
- [ ] `ago_file_write` - Write to file
- [ ] Float list operations
- [ ] String list operations

#### 4.2 Implementation Choice: ✅ C Implementation Selected

We chose **Option A: C Implementation** because:
- ✅ Easier to write and maintain
- ✅ Can use existing C libraries (libc)
- ✅ GCC generates optimized code
- ✅ Successfully compiled with gcc

---

### Phase 5: Advanced Features (Lower Priority)

#### 5.1 Ranges
**Status**: Type defined but not implemented  
**Type**: `{i64, i64, i1}` (start, end, inclusive)

**Tasks**:
- [ ] Range literal creation (`0..10`, `0.<10`)
- [ ] Range iteration in for loops
- [ ] Range to list conversion

#### 5.2 Comparison Operations
**Status**: Partial (only `==` and `<`)

**Tasks**:
- [ ] `>`, `>=`, `<=`, `!=`
- [ ] Type equality (`est` operator)
- [ ] Membership (`in` operator)

#### 5.3 Logical Operations
**Status**: Not started

**Tasks**:
- [ ] `et` (and) with short-circuit evaluation
- [ ] `vel` (or) with short-circuit evaluation
- [ ] `non` (not)
- [ ] Bitwise operations (`&`, `|`, `^`)

#### 5.4 Ternary Operator
**Status**: Not started  
**Reference**: [`src/AgoCodeGenerator.py`](src/AgoCodeGenerator.py:1483-1491)

**Task**:
- [ ] Implement `condition ? true_val : false_val`

---

### Phase 6: Build System Integration

#### 6.1 Compilation Pipeline
**Current**: Python → Rust → Binary  
**Target**: Python → LLVM IR → Binary

**Tasks**:
- [ ] Create `agoc` compiler driver script
- [ ] Integrate LLVM toolchain (llc, clang)
- [ ] Handle linking with stdlib
- [ ] Add optimization passes

**Example Pipeline**:
```bash
# Generate LLVM IR
python main.py program.ago > program.ll

# Compile stdlib to object file
clang -c ago_stdlib.c -o ago_stdlib.o

# Compile LLVM IR to object file
llc program.ll -filetype=obj -o program.o

# Link
clang program.o ago_stdlib.o -o program
```

#### 6.2 Update main.py
**File**: [`main.py`](main.py)

**Tasks**:
- [ ] Add `--backend` flag (rust/llvm)
- [ ] Import and use AgoLLVMGenerator
- [ ] Add LLVM IR output option
- [ ] Add compilation option

---

## Implementation Priority

### Immediate (Week 1-2) - ✅ COMPLETE
1. ✅ Basic expression evaluation
2. ✅ Function calls and parameters
3. ✅ Variable declarations
4. ✅ Complete stdlib function declarations
5. ✅ Implement C stdlib for core functions
6. ✅ All comparison operators (>, >=, <=, !=, ==, <)
7. ✅ All logical operators (et/and, vel/or, non/not)
8. ✅ Modulo operator (%)

### Short-term (Week 3-4)
6. Method chains and indexing
7. String operations
8. List operations
9. Comparison and logical operators

### Medium-term (Month 2)
10. Lambda functions
11. Struct/map operations
12. Type casting system
13. Memory management (GC or ref counting)

### Long-term (Month 3+)
14. Optimization passes
15. Debug information generation
16. Error handling improvements
17. Full test suite for LLVM backend

---

## Technical Decisions

### Memory Management Strategy
**Decision**: Manual malloc/free with optional reference counting

**Rationale**:
- LLVM doesn't have built-in GC
- Reference counting adds overhead but prevents leaks
- Manual management gives users control
- Can add GC later if needed

**Implementation**:
- Strings: malloc on creation, free when out of scope
- Lists: malloc for data array, free when out of scope
- Structs: malloc for hash table, free when out of scope
- Reference counting for shared ownership

### Stdlib Implementation
**Decision**: C implementation compiled to LLVM IR

**Rationale**:
- Easier to write and maintain than raw LLVM IR
- Can use existing C libraries (libc)
- Clang generates optimized LLVM IR
- Familiar to most developers

**Structure**:
```c
// ago_stdlib.c
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int64_t ago_add(int64_t a, int64_t b) {
    return a + b;
}

void ago_print_int(int64_t value) {
    printf("%lld\n", value);
}
// ... more functions
```

### Type System
**Decision**: Keep Ago's dynamic typing with runtime type tags

**Options Considered**:
1. **Static typing in LLVM** - Rejected (loses Ago's flexibility)
2. **Tagged unions** - Selected (matches Rust implementation)
3. **Boxed values** - Rejected (too much overhead)

**Implementation**:
```llvm
; Tagged union type (similar to Rust AgoType)
%AgoValue = type {
    i8,      ; Type tag (0=int, 1=float, 2=bool, etc.)
    i64      ; Data (or pointer for complex types)
}
```

---

## File Structure

### New Files Created
- ✅ [`src/AgoLLVMGenerator.py`](src/AgoLLVMGenerator.py) - LLVM IR generator
- ✅ [`test_llvm_gen.py`](test_llvm_gen.py) - Test script
- ✅ [`test_output.ll`](test_output.ll) - Generated LLVM IR output
- ✅ [`src/llvm/ago_stdlib.c`](src/llvm/ago_stdlib.c) - C stdlib implementation
- ✅ [`src/llvm/ago_stdlib.h`](src/llvm/ago_stdlib.h) - C stdlib header
- ✅ [`src/llvm/Makefile`](src/llvm/Makefile) - Build system for stdlib
- ✅ [`src/llvm/ago_stdlib.o`](src/llvm/ago_stdlib.o) - Compiled stdlib object file
- ✅ [`compile_ago.sh`](compile_ago.sh) - Compilation script

### Modified Files
- ✅ [`main.py`](main.py) - Added LLVM backend option (--backend=llvm, --emit=llvm)
- 🔄 `README.md` - Update with LLVM backend docs (to be modified)

### Preserved Files
- ✅ [`src/AgoCodeGenerator.py`](src/AgoCodeGenerator.py) - Rust backend (kept for comparison)
- ✅ [`src/rust/`](src/rust/) - Rust stdlib (kept as reference)

---

## Testing Strategy

### Unit Tests
- [ ] Test each LLVM IR generation function
- [ ] Test type inference
- [ ] Test expression evaluation
- [ ] Test control flow generation

### Integration Tests
- [ ] Compile and run simple programs
- [ ] Test stdlib function calls
- [ ] Test complex expressions
- [ ] Test memory management

### Comparison Tests
- [ ] Compare LLVM output with Rust output
- [ ] Verify semantic equivalence
- [ ] Performance benchmarks

---

## Migration Checklist

### Phase 1: Foundation ✅
- [x] Create AgoLLVMGenerator class
- [x] Implement basic type mappings
- [x] Generate function signatures
- [x] Generate variable declarations
- [x] Generate simple expressions
- [x] Generate function calls
- [x] Generate control flow (if/while/for)
- [x] Test basic programs

### Phase 2: Expressions 🔄
- [x] Binary operations (arithmetic) - ALL DONE ✅
- [x] Binary operations (comparison) - ALL DONE ✅
- [x] Binary operations (logical) - ALL DONE ✅
- [ ] Binary operations (bitwise)
- [ ] Unary operations (partially done - need unary minus, etc.)
- [ ] Ternary operator
- [ ] Method chains
- [ ] Indexing operations
- [ ] Type casting

### Phase 3: Collections 📋
- [ ] List literals
- [ ] List indexing
- [ ] List methods (append, insert, remove)
- [ ] Struct literals
- [ ] Struct field access
- [ ] Struct methods
- [ ] Range literals and iteration

### Phase 4: Advanced Features 📋
- [ ] Lambda functions
- [ ] Closures
- [ ] Higher-order functions
- [ ] Recursive functions
- [ ] Mutual recursion

### Phase 5: Stdlib ✅ MOSTLY DONE
- [x] Implement C stdlib - DONE ✅
- [x] Compile stdlib to object file - DONE ✅
- [ ] Link stdlib with generated code - BLOCKED (need LLVM tools)
- [ ] Test all stdlib functions - BLOCKED (need LLVM tools)

### Phase 6: Build System 📋
- [ ] Create compiler driver script
- [ ] Integrate LLVM toolchain
- [ ] Add optimization options
- [ ] Add debug information generation

### Phase 7: Documentation 📋
- [ ] Update README with LLVM backend
- [ ] Document compilation process
- [ ] Add LLVM IR examples
- [ ] Create migration guide

---

## Key Differences from Rust Backend

### 1. Memory Model
- **Rust**: Ownership and borrowing (compile-time safety)
- **LLVM**: Manual malloc/free (runtime management)

### 2. Type System
- **Rust**: `AgoType` enum with pattern matching
- **LLVM**: Tagged unions or separate types per value

### 3. Function Calls
- **Rust**: Pass by reference (`&AgoType`)
- **LLVM**: Pass by value or pointer

### 4. Error Handling
- **Rust**: `Result<T, E>` and `panic!`
- **LLVM**: Return codes or exceptions (to be decided)

### 5. Standard Library
- **Rust**: Implemented in Rust with `ago_stdlib` crate
- **LLVM**: Implemented in C, compiled to LLVM IR

---

## Performance Considerations

### Optimization Opportunities
1. **Inline small functions** - LLVM can inline aggressively
2. **Constant folding** - LLVM optimizes constant expressions
3. **Dead code elimination** - LLVM removes unused code
4. **Loop optimizations** - LLVM has powerful loop optimizers

### Potential Bottlenecks
1. **Dynamic typing overhead** - Type tags add runtime cost
2. **Memory allocation** - malloc/free can be slow
3. **Lack of move semantics** - More copying than Rust

### Mitigation Strategies
1. Use LLVM optimization passes (`-O2`, `-O3`)
2. Implement object pooling for common allocations
3. Add type specialization for hot paths
4. Profile and optimize critical sections

---

## Next Steps

### Immediate Actions
1. Remove debug print statements from working code
2. Implement remaining comparison operators
3. Add logical operators with short-circuit evaluation
4. Create C stdlib implementation file

### This Week
1. Implement method chains and indexing
2. Add all comparison and logical operators
3. Create basic C stdlib with core functions
4. Test compilation of stdlib + generated code

### This Month
1. Implement lambda functions
2. Complete collection operations
3. Add type casting system
4. Create comprehensive test suite
5. Update build system and documentation

---

## Success Criteria

### Minimum Viable Product (MVP) - ✅ ACHIEVED
- ✅ Generate valid LLVM IR for basic programs
- ✅ Support functions, variables, expressions
- ✅ Support control flow (if/while/for)
- ✅ Implement core stdlib functions
- ⚠️ Successfully compile and run test programs - BLOCKED (LLVM tools not available in environment)

### Full Feature Parity
- [ ] All Ago language features work in LLVM backend
- [ ] Performance comparable to Rust backend
- [ ] Complete stdlib implementation
- [ ] Comprehensive test coverage
- [ ] Documentation and examples

### Stretch Goals
- [ ] Better performance than Rust backend
- [ ] Debug information for debuggers
- [ ] LLVM optimization passes integration
- [ ] Cross-compilation support
- [ ] WebAssembly target support

---

## Resources

### LLVM Documentation
- [LLVM Language Reference](https://llvm.org/docs/LangRef.html)
- [LLVM Programmer's Manual](https://llvm.org/docs/ProgrammersManual.html)
- [LLVM IR Tutorial](https://llvm.org/docs/tutorial/)

### Reference Implementations
- [`src/AgoCodeGenerator.py`](src/AgoCodeGenerator.py) - Rust backend (reference)
- [`src/rust/src/`](src/rust/src/) - Rust stdlib (reference)
- LLVM Kaleidoscope tutorial - Similar language implementation

### Tools
- `llc` - LLVM static compiler
- `lli` - LLVM interpreter (for testing)
- `opt` - LLVM optimizer
- `clang` - C compiler (for stdlib)

---

## Conclusion

The LLVM backend for Ago is now functional for basic programs. The foundation is solid with working function generation, variable management, expressions, and control flow. The next phase focuses on completing the expression system (method chains, indexing, lambdas) and implementing the C stdlib. With these additions, the LLVM backend will reach feature parity with the Rust backend while offering direct compilation to machine code.