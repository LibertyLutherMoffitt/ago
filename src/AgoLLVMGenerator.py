"""
Ago LLVM Code Generator - Generates LLVM IR from parsed Ago AST.

This module walks the AST produced by the parser and generates
equivalent LLVM IR that can be compiled directly to machine code.
"""

from typing import Any, Optional, Dict, List, Set
import re


def to_dict(node: Any) -> dict:
    """Convert an AST node to a dict for easier access."""
    if isinstance(node, dict):
        return node
    if hasattr(node, "items"):
        return dict(node)
    if hasattr(node, "__dict__"):
        return node.__dict__
    return {}


# LLVM Type mappings for Ago types
AGO_TYPE_TO_LLVM = {
    "int": "i64",
    "float": "double",
    "bool": "i1",
    "string": "{i64, i8*}",  # {length, data}
    "int_list": "{i64, i64*}",  # {length, data}
    "float_list": "{i64, double*}",  # {length, data}
    "bool_list": "{i64, i1*}",  # {length, data}
    "string_list": "{i64, {i64, i8*}*}",  # {length, data} where data is array of strings
    "struct": "i8*",  # Pointer to struct data
    "list_any": "{i64, i8*}",  # {length, data} where data is array of pointers
    "range": "{i64, i64, i1}",  # {start, end, inclusive}
    "function": "i8*",  # Function pointer (simplified)
    "null": "i8*",  # Null pointer
    "any": "i8*",  # Generic pointer
}

# Type suffix to Ago type mapping (same as original)
ENDING_TO_TYPE = {
    "a": "int",
    "ae": "float",
    "am": "bool",
    "aem": "int_list",
    "arum": "float_list",
    "as": "bool_list",
    "es": "string",
    "erum": "string_list",
    "u": "struct",
    "uum": "list_any",
    "e": "range",
    "o": "function",
    "i": "null",
    "ium": "any",
}

ENDINGS_BY_LENGTH = sorted(ENDING_TO_TYPE.keys(), key=len, reverse=True)


def get_suffix_and_stem(name: str) -> tuple[Optional[str], Optional[str]]:
    """Get the type suffix and stem from a variable name."""
    for ending in ENDINGS_BY_LENGTH:
        if name.endswith(ending) and len(name) > len(ending):
            return ending, name[:-len(ending)]
    return None, None


class LLVMContext:
    """Context for LLVM IR generation."""

    def __init__(self):
        self.indent_level = 0
        self.output_lines: List[str] = []
        self.temp_counter = 0
        self.label_counter = 0
        self.function_counter = 0
        self.string_counter = 0
        self.strings: Dict[str, str] = {}  # content -> global name

    def indent(self) -> str:
        return "  " * self.indent_level

    def emit(self, line: str) -> None:
        """Emit a line of LLVM IR."""
        self.output_lines.append(f"{self.indent()}{line}")

    def emit_raw(self, line: str) -> None:
        """Emit a line without indentation."""
        self.output_lines.append(line)

    def new_temp(self) -> str:
        """Generate a new temporary variable name."""
        temp = f"%{self.temp_counter}"
        self.temp_counter += 1
        return temp

    def new_label(self) -> str:
        """Generate a new label name."""
        label = f"label_{self.label_counter}"
        self.label_counter += 1
        return label

    def new_function_name(self) -> str:
        """Generate a new function name."""
        func = f"func_{self.function_counter}"
        self.function_counter += 1
        return func

    def get_string_global(self, content: str) -> str:
        """Get or create a global string constant."""
        if content in self.strings:
            return self.strings[content]

        global_name = f"@.str.{self.string_counter}"
        self.string_counter += 1
        self.strings[content] = global_name

        # Emit the global string constant
        # Remove surrounding quotes if present
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]
        # LLVM string constants need to be escaped
        escaped = content.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\0A').replace('\t', '\\09')
        length = len(content.encode('utf-8'))  # Byte length for UTF-8
        self.emit_raw(f'{global_name} = private unnamed_addr constant [{length + 1} x i8] c"{escaped}\\00"')

        return global_name


class AgoLLVMGenerator:
    """
    Generates LLVM IR from an Ago AST.
    """

    def __init__(self):
        self.ctx = LLVMContext()
        # Track declared variables: name -> (llvm_type, is_pointer)
        self.declared_vars: Dict[str, tuple[str, bool]] = {}
        # Track functions: name -> (return_type, param_types)
        self.functions: Dict[str, tuple[str, List[str]]] = {}
        # Track user-defined function names
        self.user_functions: Set[str] = set()
        # Track lambdas
        self.lambdas: List[str] = []
        self.lambda_counter = 0
        # Current function context
        self.current_function: Optional[str] = None
        self.current_return_type: Optional[str] = None

    def get_llvm_type(self, ago_type: str) -> str:
        """Convert Ago type to LLVM type."""
        return AGO_TYPE_TO_LLVM.get(ago_type, "i8*")

    def infer_expr_type(self, expr: Any) -> str:
        """Infer the Ago type of an expression."""
        if expr is None:
            return "null"

        if isinstance(expr, str):
            if expr == "verum" or expr == "falsus":
                return "bool"
            if expr == "inanis":
                return "null"
            # Variable reference
            if expr in self.declared_vars:
                llvm_type, _ = self.declared_vars[expr]
                # Convert back from LLVM type to Ago type
                for ago_t, llvm_t in AGO_TYPE_TO_LLVM.items():
                    if llvm_t == llvm_type:
                        return ago_t
            return "any"

        d = to_dict(expr)

        # Literals
        if d.get("int") is not None:
            return "int"
        if d.get("float") is not None:
            return "float"
        if d.get("str") is not None:
            return "string"
        if d.get("roman") is not None:
            return "int"
        if d.get("TRUE") or d.get("FALSE"):
            return "bool"
        if d.get("NULL"):
            return "null"

        # Binary operations
        if d.get("op") and d.get("left"):
            left_type = self.infer_expr_type(d["left"])
            right_type = self.infer_expr_type(d["right"])
            op = d["op"]

            if op in ("+", "-", "*", "/", "%"):
                if left_type == "float" or right_type == "float":
                    return "float"
                return "int"
            if op in ("et", "vel"):
                return "bool"
            if op in ("==", "!=", "<", ">", "<=", ">="):
                return "bool"
            if op == "in":
                return "bool"

        # Function call
        if d.get("call"):
            call_d = to_dict(d["call"])
            if call_d.get("func"):
                func_name = str(call_d["func"])
                if func_name in self.functions:
                    return_type, _ = self.functions[func_name]
                    return return_type

        return "any"

    def generate_literal(self, expr: Any) -> tuple[str, str]:
        """Generate LLVM IR for a literal value. Returns (value, type)."""
        d = to_dict(expr)

        if d.get("int") is not None:
            val = str(d["int"])
            return (val, "i64")

        if d.get("float") is not None:
            val = str(d["float"])
            return (f"0x{val.encode('utf-8').hex()}", "double")  # LLVM hex float format

        if d.get("str") is not None:
            content = d["str"]
            global_name = self.ctx.get_string_global(content)
            # Calculate string length (without quotes)
            if content.startswith('"') and content.endswith('"'):
                content = content[1:-1]
            length = len(content.encode('utf-8'))

            # Create string struct: {i64, i8*}
            temp = self.ctx.new_temp()
            self.ctx.emit(f"{temp} = insertvalue {{i64, i8*}} undef, i64 {length}, 0")
            temp2 = self.ctx.new_temp()
            str_ptr = f"getelementptr inbounds [{length + 1} x i8], [{length + 1} x i8]* {global_name}, i64 0, i64 0"
            self.ctx.emit(f"{temp2} = insertvalue {{i64, i8*}} {temp}, i8* {str_ptr}, 1")
            return (temp2, "{i64, i8*}")

        if d.get("TRUE"):
            return ("true", "i1")

        if d.get("FALSE"):
            return ("false", "i1")

        if d.get("NULL"):
            return ("null", "i8*")

        # Default
        return ("null", "i8*")

    def generate_expr(self, expr: Any) -> tuple[str, str]:
        """Generate LLVM IR for an expression. Returns (result_reg, type)."""
        if expr is None:
            return ("null", "i8*")

        if isinstance(expr, str):
            if expr == "verum":
                return ("true", "i1")
            if expr == "falsus":
                return ("false", "i1")
            if expr == "inanis":
                return ("null", "i8*")
            # Variable reference
            if expr in self.declared_vars:
                llvm_type, is_pointer = self.declared_vars[expr]
                if is_pointer:
                    # Load from pointer
                    temp = self.ctx.new_temp()
                    self.ctx.emit(f"{temp} = load {llvm_type}, {llvm_type}* %{expr}")
                    return (temp, llvm_type)
                else:
                    # Parameter or SSA value
                    return (f"%{expr}", llvm_type)
            return ("null", "i8*")

        d = to_dict(expr)

        # Unwrap value wrapper
        if "value" in d and d.get("value") is not None:
            inner = d["value"]
            if isinstance(inner, dict) or hasattr(inner, "parseinfo"):
                return self.generate_expr(inner)

        # Literals
        if any(key in d for key in ["int", "float", "str", "roman", "TRUE", "FALSE", "NULL"]):
            return self.generate_literal(expr)

        # Binary operations
        if d.get("op") and d.get("left"):
            return self.generate_binary_op(d)

        # Variable reference with casting
        if d.get("id"):
            name = str(d["id"])
            return self.generate_variable_ref(name)

        # New postfix structure (base + ops)
        if d.get("base") is not None:
            return self.generate_postfix_expr(d)

        # Function call
        if d.get("call"):
            return self.generate_call(d["call"])

        return ("null", "i8*")

    def generate_binary_op(self, d: dict) -> tuple[str, str]:
        """Generate LLVM IR for binary operations."""
        op = d.get("op")
        left_reg, left_type = self.generate_expr(d.get("left"))
        right_reg, right_type = self.generate_expr(d.get("right"))

        # Use stdlib functions for operations
        if op == "+":
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i64 @ago_add(i64 {left_reg}, i64 {right_reg})")
            return (result, "i64")

        if op == "-":
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i64 @ago_subtract(i64 {left_reg}, i64 {right_reg})")
            return (result, "i64")

        if op == "*":
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i64 @ago_multiply(i64 {left_reg}, i64 {right_reg})")
            return (result, "i64")

        if op == "/":
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i64 @ago_divide(i64 {left_reg}, i64 {right_reg})")
            return (result, "i64")

        if op == "%":
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i64 @ago_modulo(i64 {left_reg}, i64 {right_reg})")
            return (result, "i64")

        if op == "==":
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i1 @ago_equal(i64 {left_reg}, i64 {right_reg})")
            return (result, "i1")

        if op == "!=":
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i1 @ago_not_equal(i64 {left_reg}, i64 {right_reg})")
            return (result, "i1")

        if op == "<":
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i1 @ago_less_than(i64 {left_reg}, i64 {right_reg})")
            return (result, "i1")

        if op == ">":
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i1 @ago_greater_than(i64 {left_reg}, i64 {right_reg})")
            return (result, "i1")

        if op == "<=":
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i1 @ago_less_equal(i64 {left_reg}, i64 {right_reg})")
            return (result, "i1")

        if op == ">=":
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i1 @ago_greater_equal(i64 {left_reg}, i64 {right_reg})")
            return (result, "i1")

        # Logical operators with short-circuit evaluation
        if op == "et":
            # Short-circuit AND: if left is false, don't evaluate right
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i1 @ago_logical_and(i1 {left_reg}, i1 {right_reg})")
            return (result, "i1")

        if op == "vel":
            # Short-circuit OR: if left is true, don't evaluate right
            result = self.ctx.new_temp()
            self.ctx.emit(f"{result} = call i1 @ago_logical_or(i1 {left_reg}, i1 {right_reg})")
            return (result, "i1")

        # Default
        return ("null", "i8*")

    def generate_variable_ref(self, name: str) -> tuple[str, str]:
        """Generate variable reference with possible casting."""
        if name in self.declared_vars:
            llvm_type, is_pointer = self.declared_vars[name]
            if is_pointer:
                temp = self.ctx.new_temp()
                self.ctx.emit(f"{temp} = load {llvm_type}, {llvm_type}* %{name}")
                return (temp, llvm_type)
            return (f"%{name}", llvm_type)

        # Check for casting via suffix
        suffix, stem = get_suffix_and_stem(name)
        if stem and suffix:
            ago_type = ENDING_TO_TYPE.get(suffix)
            if ago_type and stem in self.declared_vars:
                # For now, just return the base variable (casting not implemented yet)
                return self.generate_variable_ref(stem)

        return ("null", "i8*")

    def generate_postfix_expr(self, d: dict) -> tuple[str, str]:
        """Generate expression from postfix structure (base + ops)."""
        base = d.get("base")
        ops = d.get("ops", [])

        # Start with base expression
        result_reg, result_type = self.generate_expr(base)

        # For now, ignore ops (indexing, method calls) - just return base
        # This handles simple variable references
        return (result_reg, result_type)

    def generate_call(self, call_node: Any) -> tuple[str, str]:
        """Generate function call."""
        d = to_dict(call_node)

        func_name = None
        if d.get("func"):
            func_name = str(d["func"])

        if func_name:
            # Handle special stdlib functions
            if func_name == "scribi":
                # Print function - handle arguments
                args = []
                args_node = d.get("args")
                if args_node:
                    args_d = to_dict(args_node)
                    first = args_d.get("first")
                    if first:
                        arg_reg, arg_type = self.generate_expr(first)
                        if arg_type == "i64":
                            self.ctx.emit(f"call void @ago_print_int(i64 {arg_reg})")
                        elif arg_type == "{i64, i8*}":
                            self.ctx.emit(f"call void @ago_print_string(i8* {arg_reg})")
                        return ("null", "i8*")  # Print returns void

            # Regular function calls
            if func_name in self.functions:
                return_type, param_types = self.functions[func_name]

                # Generate arguments
                args = []
                args_node = d.get("args")
                if args_node:
                    args_d = to_dict(args_node)
                    first = args_d.get("first")
                    if first:
                        arg_reg, _ = self.generate_expr(first)
                        args.append(arg_reg)

                # Generate call
                result = self.ctx.new_temp()
                args_str = ", ".join(f"i64 {arg}" for arg in args)  # Assume i64 for now
                llvm_return_type = self.get_llvm_type(return_type)
                self.ctx.emit(f"{result} = call {llvm_return_type} @{func_name}({args_str})")
                return (result, llvm_return_type)

        return ("null", "i8*")

    def generate_declaration(self, stmt: Any) -> None:
        """Generate variable declaration."""
        d = to_dict(stmt)
        var_name = str(d["name"])
        value = d.get("value")

        # Infer type from name suffix
        suffix, _ = get_suffix_and_stem(var_name)
        ago_type = "any"
        if suffix:
            ago_type = ENDING_TO_TYPE.get(suffix, "any")

        llvm_type = self.get_llvm_type(ago_type)

        # Generate RHS
        rhs_reg, rhs_type = self.generate_expr(value)

        # Allocate variable
        self.ctx.emit(f"%{var_name} = alloca {llvm_type}")

        # Store value
        if rhs_type == llvm_type:
            self.ctx.emit(f"store {llvm_type} {rhs_reg}, {llvm_type}* %{var_name}")
        else:
            # Type mismatch - for now, just store (casting not implemented)
            self.ctx.emit(f"store {llvm_type} {rhs_reg}, {llvm_type}* %{var_name}")

        # Track variable
        self.declared_vars[var_name] = (llvm_type, True)  # All variables are pointers for now

    def generate_return(self, stmt: Any) -> None:
        """Generate return statement."""
        d = to_dict(stmt)
        value = d.get("value")

        if value:
            ret_reg, ret_type = self.generate_expr(value)
            llvm_ret_type = self.get_llvm_type(self.current_return_type or "any")
            if ret_type == llvm_ret_type:
                self.ctx.emit(f"ret {llvm_ret_type} {ret_reg}")
            else:
                # Type mismatch - cast or handle
                self.ctx.emit(f"ret {llvm_ret_type} {ret_reg}")
        else:
            self.ctx.emit("ret void")

        # Mark that we had an explicit return
        self._had_explicit_return = True

    def generate_if(self, stmt: Any) -> None:
        """Generate if statement with LLVM branches."""
        d = to_dict(stmt)

        cond_reg, cond_type = self.generate_expr(d.get("cond"))

        # Convert to i1 if needed
        if cond_type != "i1":
            bool_reg = self.ctx.new_temp()
            if cond_type == "i64":
                self.ctx.emit(f"{bool_reg} = icmp ne i64 {cond_reg}, 0")
            else:
                # For other types, assume truthy conversion
                self.ctx.emit(f"{bool_reg} = icmp ne i8* {cond_reg}, null")
            cond_reg = bool_reg

        then_label = self.ctx.new_label()
        else_label = self.ctx.new_label()
        end_label = self.ctx.new_label()

        self.ctx.emit(f"br i1 {cond_reg}, label %{then_label}, label %{else_label}")

        # Then block
        self.ctx.emit_raw(f"{then_label}:")
        self.generate_block(d.get("then"))
        self.ctx.emit(f"br label %{end_label}")

        # Else block
        self.ctx.emit_raw(f"{else_label}:")
        else_frag = d.get("else_frag") or d.get("else_fragment")
        if else_frag:
            else_d = to_dict(else_frag)
            self.generate_block(else_d.get("else_body"))
        self.ctx.emit(f"br label %{end_label}")

        # End
        self.ctx.emit_raw(f"{end_label}:")

    def generate_while(self, stmt: Any) -> None:
        """Generate while loop with LLVM branches."""
        d = to_dict(stmt)

        loop_label = self.ctx.new_label()
        body_label = self.ctx.new_label()
        end_label = self.ctx.new_label()

        self.ctx.emit(f"br label %{loop_label}")

        # Loop condition
        self.ctx.emit_raw(f"{loop_label}:")
        cond_reg, cond_type = self.generate_expr(d.get("cond"))

        # Convert to i1 if needed
        if cond_type != "i1":
            bool_reg = self.ctx.new_temp()
            if cond_type == "i64":
                self.ctx.emit(f"{bool_reg} = icmp ne i64 {cond_reg}, 0")
            else:
                self.ctx.emit(f"{bool_reg} = icmp ne i8* {cond_reg}, null")
            cond_reg = bool_reg

        self.ctx.emit(f"br i1 {cond_reg}, label %{body_label}, label %{end_label}")

        # Loop body
        self.ctx.emit_raw(f"{body_label}:")
        self.generate_block(d.get("body"))
        self.ctx.emit(f"br label %{loop_label}")

        # End
        self.ctx.emit_raw(f"{end_label}:")

    def generate_for(self, stmt: Any) -> None:
        """Generate for loop (simplified version)."""
        d = to_dict(stmt)

        iterator = self.extract_identifier(d.get("iterator"))
        iterable = d.get("iterable")

        if not iterator:
            return

        # For now, assume simple range iteration
        # This is a simplified implementation
        loop_label = self.ctx.new_label()
        body_label = self.ctx.new_label()
        end_label = self.ctx.new_label()

        # Initialize iterator variable
        iter_llvm_type = "i64"  # Assume int for now
        self.ctx.emit(f"%{iterator} = alloca {iter_llvm_type}")

        # Get range start (simplified)
        start_reg = self.ctx.new_temp()
        self.ctx.emit(f"{start_reg} = add i64 0, 0")  # Start from 0

        # Get range end from iterable (simplified)
        iter_expr_reg, _ = self.generate_expr(iterable)
        end_reg = iter_expr_reg  # Assume iterable is the end value

        # Store initial value
        self.ctx.emit(f"store {iter_llvm_type} {start_reg}, {iter_llvm_type}* %{iterator}")

        self.ctx.emit(f"br label %{loop_label}")

        # Loop condition
        self.ctx.emit_raw(f"{loop_label}:")
        current_val = self.ctx.new_temp()
        self.ctx.emit(f"{current_val} = load {iter_llvm_type}, {iter_llvm_type}* %{iterator}")
        cond_reg = self.ctx.new_temp()
        self.ctx.emit(f"{cond_reg} = icmp slt i64 {current_val}, {end_reg}")
        self.ctx.emit(f"br i1 {cond_reg}, label %{body_label}, label %{end_label}")

        # Loop body
        self.ctx.emit_raw(f"{body_label}:")
        self.generate_block(d.get("body"))

        # Increment iterator
        next_val = self.ctx.new_temp()
        self.ctx.emit(f"{next_val} = add i64 {current_val}, 1")
        self.ctx.emit(f"store {iter_llvm_type} {next_val}, {iter_llvm_type}* %{iterator}")
        self.ctx.emit(f"br label %{loop_label}")

        # End
        self.ctx.emit_raw(f"{end_label}:")

    def generate_function(self, ast: Any) -> None:
        """Generate LLVM function from method declaration."""
        d = to_dict(ast)
        func_name = str(d["name"])

        # Infer return type from name
        suffix, _ = get_suffix_and_stem(func_name)
        return_type = "any"
        if suffix:
            return_type = ENDING_TO_TYPE.get(suffix, "any")

        # Parse parameters
        params = []
        params_node = d.get("params")
        if params_node:
            d_params = to_dict(params_node)
            first = d_params.get("first")
            if first:
                # Parameters are wrapped in value structure
                first_d = to_dict(first)
                value = first_d.get("value")
                if value:
                    param_name = self.extract_identifier(value)
                    if param_name:
                        suffix, _ = get_suffix_and_stem(param_name)
                        param_type = "any"
                        if suffix:
                            param_type = ENDING_TO_TYPE.get(suffix, "any")
                        params.append((param_name, param_type))

            # Handle rest parameters
            rest = d_params.get("rest")
            if rest:
                for item in rest:
                    if isinstance(item, list) and len(item) >= 2:
                        param_expr = item[1]
                        param_expr_d = to_dict(param_expr)
                        value = param_expr_d.get("value")
                        if value:
                            param_name = self.extract_identifier(value)
                            if param_name:
                                suffix, _ = get_suffix_and_stem(param_name)
                                param_type = "any"
                                if suffix:
                                    param_type = ENDING_TO_TYPE.get(suffix, "any")
                                params.append((param_name, param_type))

        # Generate function signature
        llvm_return_type = self.get_llvm_type(return_type)
        param_strs = []
        for param_name, param_type in params:
            llvm_param_type = self.get_llvm_type(param_type)
            param_strs.append(f"{llvm_param_type} %{param_name}")

        param_list = ", ".join(param_strs) if param_strs else ""
        self.ctx.emit_raw("")
        self.ctx.emit_raw(f"define {llvm_return_type} @{func_name}({param_list}) {{")

        # Set up function context
        old_function = self.current_function
        old_return_type = self.current_return_type
        self.current_function = func_name
        self.current_return_type = return_type

        # Track parameters as variables
        for param_name, param_type in params:
            llvm_type = self.get_llvm_type(param_type)
            self.declared_vars[param_name] = (llvm_type, False)  # Parameters are not pointers

        # Track if we had an explicit return
        self._had_explicit_return = False

        # Process function body
        self.ctx.indent_level += 1
        body = d.get("body")
        if body:
            self.generate_block(body)

        # Default return if no explicit return
        if not getattr(self, '_had_explicit_return', False):
            if return_type == "null":
                self.ctx.emit("ret void")
            else:
                # Return default value
                if return_type == "int":
                    self.ctx.emit("ret i64 0")
                elif return_type == "float":
                    self.ctx.emit("ret double 0.0")
                elif return_type == "bool":
                    self.ctx.emit("ret i1 false")
                else:
                    self.ctx.emit("ret i8* null")

        self.ctx.indent_level -= 1
        self.ctx.emit_raw("}")

        # Track function
        param_types = [pt for _, pt in params]
        self.functions[func_name] = (return_type, param_types)
        self.user_functions.add(func_name)

        # Restore context
        self.current_function = old_function
        self.current_return_type = old_return_type
        self.declared_vars.clear()

    def generate_block(self, block: Any) -> None:
        """Generate code for a block of statements."""
        if block is None:
            return

        d = to_dict(block)
        stmts = d.get("stmts")
        if stmts is None:
            return

        stmts_d = to_dict(stmts)
        first = stmts_d.get("first")
        if first:
            self.generate_statement(first)

        rest = stmts_d.get("rest")
        if rest:
            for item in rest:
                if isinstance(item, list):
                    for sub in item:
                        if sub and sub != "\n":
                            self.generate_statement(sub)
                elif item and item != "\n":
                    self.generate_statement(item)

    def generate_statement(self, stmt: Any) -> None:
        """Generate code for a statement."""
        if stmt is None:
            return

        if isinstance(stmt, str):
            return  # Skip strings

        if isinstance(stmt, list):
            for sub in stmt:
                self.generate_statement(sub)
            return

        d = to_dict(stmt)

        if "name" in d and "value" in d and "target" not in d:
            self.generate_declaration(stmt)
        elif "return_stmt" in d or ("value" in d and d.get("return_stmt") is not None):
            self.generate_return(stmt)
        elif "if_stmt" in d:
            self.generate_if(d["if_stmt"])
        elif "cond" in d and "then" in d:
            self.generate_if(stmt)
        elif "while_stmt" in d:
            self.generate_while(d["while_stmt"])
        elif "cond" in d and "body" in d and "iterator" not in d:
            self.generate_while(stmt)
        elif "for_stmt" in d:
            self.generate_for(d["for_stmt"])
        elif "iterator" in d and "iterable" in d:
            self.generate_for(stmt)
        elif "call" in d:
            # Call statement - handle new expr wrapper
            call_data = d["call"]
            call_d = to_dict(call_data)
            
            # New structure: call has 'expr' which contains postfix with base.call
            if call_d.get("expr"):
                expr_d = to_dict(call_d["expr"])
                base = expr_d.get("base")
                if base:
                    base_d = to_dict(base)
                    if base_d.get("call"):
                        # This is the actual function call
                        self.generate_call(base_d["call"])
                    else:
                        # Fallback - generate as expression
                        self.generate_expr(call_data)
            else:
                # Old structure - direct call
                self.generate_call(call_data)
        else:
            # Expression statement
            expr_reg, _ = self.generate_expr(stmt)
            # In LLVM, expressions need to be used or they might be optimized away
            # For now, just generate the expression

    def extract_identifier(self, node: Any) -> Optional[str]:
        """Extract identifier name from node."""
        if isinstance(node, str):
            return node
        d = to_dict(node)
        if "id" in d:
            return str(d["id"])
        # Check value wrapper
        if "value" in d:
            inner = d["value"]
            if isinstance(inner, dict) or hasattr(inner, "parseinfo"):
                return self.extract_identifier(inner)
        # Check base wrapper (new postfix structure)
        if "base" in d:
            base = d["base"]
            if isinstance(base, dict) or hasattr(base, "parseinfo"):
                return self.extract_identifier(base)
        return None

    def generate(self, ast: Any) -> str:
        """Generate LLVM IR from the AST and return as string."""
        # Emit LLVM header
        self.ctx.emit_raw("; ModuleID = 'ago_program'")
        self.ctx.emit_raw('target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"')
        self.ctx.emit_raw('target triple = "x86_64-unknown-linux-gnu"')
        self.ctx.emit_raw("")

        # Declare external functions (malloc, free, etc.)
        self.ctx.emit_raw("declare i8* @malloc(i64)")
        self.ctx.emit_raw("declare void @free(i8*)")

        # Declare stdlib functions
        self.ctx.emit_raw("declare i64 @ago_add(i64, i64)")
        self.ctx.emit_raw("declare i64 @ago_subtract(i64, i64)")
        self.ctx.emit_raw("declare i64 @ago_multiply(i64, i64)")
        self.ctx.emit_raw("declare i64 @ago_divide(i64, i64)")
        self.ctx.emit_raw("declare i64 @ago_modulo(i64, i64)")
        self.ctx.emit_raw("declare i1 @ago_equal(i64, i64)")
        self.ctx.emit_raw("declare i1 @ago_not_equal(i64, i64)")
        self.ctx.emit_raw("declare i1 @ago_less_than(i64, i64)")
        self.ctx.emit_raw("declare i1 @ago_greater_than(i64, i64)")
        self.ctx.emit_raw("declare i1 @ago_less_equal(i64, i64)")
        self.ctx.emit_raw("declare i1 @ago_greater_equal(i64, i64)")
        self.ctx.emit_raw("declare i1 @ago_logical_and(i1, i1)")
        self.ctx.emit_raw("declare i1 @ago_logical_or(i1, i1)")
        self.ctx.emit_raw("declare i1 @ago_logical_not(i1)")
        self.ctx.emit_raw("declare i8* @ago_string_concat(i8*, i8*)")
        self.ctx.emit_raw("declare void @ago_print_int(i64)")
        self.ctx.emit_raw("declare void @ago_print_string(i8*)")
        self.ctx.emit_raw("")

        # Collect and generate user functions
        self.collect_functions(ast)
        for func_ast in self.function_asts:
            self.generate_function(func_ast)

        # Generate main function
        self.ctx.emit_raw("")
        self.ctx.emit_raw("define i32 @main() {")
        self.ctx.indent_level += 1

        # Process top-level statements
        self.process_principio(ast)

        # Return 0
        self.ctx.emit("ret i32 0")

        self.ctx.indent_level -= 1
        self.ctx.emit_raw("}")

        return "\n".join(self.ctx.output_lines)

    def collect_functions(self, ast: Any) -> None:
        """Collect all function definitions."""
        self.function_asts = []

        def visit(node: Any) -> None:
            if node is None:
                return
            if isinstance(node, (list, tuple)):
                for item in node:
                    visit(item)
                return

            d = to_dict(node)
            if "name" in d and "body" in d and "params" in d:
                self.function_asts.append(node)

        visit(ast)

    def process_principio(self, ast: Any) -> None:
        """Process top-level statements."""
        if ast is None:
            return
        if isinstance(ast, (list, tuple)):
            for item in ast:
                self.process_top_level(item)
            return
        self.process_top_level(ast)

    def process_top_level(self, item: Any) -> None:
        """Process a top-level item."""
        if item is None:
            return
        if isinstance(item, str):
            return  # Skip strings

        d = to_dict(item)
        if "name" in d and "body" in d and "params" in d:
            return  # Skip function declarations (already processed)

        # Process as statement
        self.generate_statement(item)


def generate(ast: Any) -> str:
    """Generate LLVM IR from an Ago AST."""
    generator = AgoLLVMGenerator()
    return generator.generate(ast)