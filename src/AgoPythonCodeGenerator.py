"""
Ago Python Code Generator - Generates Python code from parsed Ago AST.
"""
import ast
from typing import Any

class AgoPythonCodeGenerator:
    def generate(self, ago_ast):
        module_body = self._generate_program(ago_ast)
        module = ast.Module(body=module_body, type_ignores=[])
        ast.fix_missing_locations(module)
        return module

    def _get_stem(self, name: str) -> str:
        # Implementation from before
        suffixes = sorted(["aem", "arum", "erum", "uum", "as", "ae", "am", "es", "um", "a", "u", "e", "o", "i"], key=len, reverse=True)
        for suffix in suffixes:
            if name.endswith(suffix) and len(name) > len(suffix):
                return name[:-len(suffix)]
        return name

    def _generate_program(self, node):
        body = []
        for item in node:
            if not item: continue
            if isinstance(item, list):
                res = self._generate_program(item)
                if res: body.extend(res)
            else:
                res = self._generate_sub_principio(item)
                if res:
                    if isinstance(res, list):
                        body.extend(res)
                    else:
                        body.append(res)
        return [n for n in body if n is not None]

    def _generate_sub_principio(self, node):
        if 'statement' in node:
            return self._generate_statement(node['statement'])
        if 'method_decl' in node:
            return self._generate_method_decl(node['method_decl'])
        return None

    def _generate_statement(self, node):
        if 'declaration_stmt' in node:
            return self._generate_declaration_stmt(node['declaration_stmt'])
        if 'reassignment_stmt' in node:
            return self._generate_reassignment_stmt(node['reassignment_stmt'])
        if 'if_stmt' in node:
            return self._generate_if_stmt(node['if_stmt'])
        if 'while_stmt' in node:
            return self._generate_while_stmt(node['while_stmt'])
        if 'for_stmt' in node:
            return self._generate_for_stmt(node['for_stmt'])
        if 'return_stmt' in node:
            return self._generate_return_stmt(node['return_stmt'])
        if 'call_stmt' in node:
            return ast.Expr(value=self._generate_expr(node['call_stmt']))
        if 'PASS' in node: return ast.Pass()
        if 'BREAK' in node: return ast.Break()
        if 'CONTINUE' in node: return ast.Continue()
        # Fallback for expression as statement
        return ast.Expr(value=self._generate_expr(node))


    def _generate_declaration_stmt(self, node):
        name = self._get_stem(node['name'])
        value = self._generate_expr(node['value'])
        return ast.Assign(targets=[ast.Name(id=name, ctx=ast.Store())], value=value)

    def _generate_reassignment_stmt(self, node):
        target_name = self._get_stem(node['target'])
        value = self._generate_expr(node['value'])
        target = ast.Name(id=target_name, ctx=ast.Store())
        if 'index' in node and node['index']:
             target.ctx = ast.Load()
             for index_node in node['index']:
                 index_expr = self._generate_expr(index_node['expr'])
                 target = ast.Subscript(value=target, slice=index_expr, ctx=ast.Store())
        return ast.Assign(targets=[target], value=value)
        
    def _generate_if_stmt(self, node):
        test = self._generate_expr(node['cond'])
        body = self._generate_block(node['then'])
        orelse = []
        if 'elifs' in node:
            for elif_node in node['elifs']:
                orelse.append(self._generate_if_stmt({'cond': elif_node['elif_cond'], 'then': elif_node['elif_body'], 'elifs':[], 'else_frag': None}))
        if 'else_frag' in node and node['else_frag']:
            if orelse: orelse[-1].orelse = self._generate_block(node['else_frag']['else_body'])
            else: orelse = self._generate_block(node['else_frag']['else_body'])
        return ast.If(test=test, body=body, orelse=orelse)

    def _generate_while_stmt(self, node):
        return ast.While(test=self._generate_expr(node['cond']), body=self._generate_block(node['body']), orelse=[])

    def _generate_for_stmt(self, node):
        iterator_name = self._get_stem(node['iterator'])
        target = ast.Name(id=iterator_name, ctx=ast.Store())
        iterable_node = node['iterable']
        if 'op' in iterable_node and iterable_node['op'] in ('..', '.<'):
             start = self._generate_expr(iterable_node['left'])
             end = self._generate_expr(iterable_node['right'])
             if iterable_node['op'] == '..': end = ast.BinOp(left=end, op=ast.Add(), right=ast.Constant(value=1))
             iterable = ast.Call(func=ast.Name(id='range', ctx=ast.Load()), args=[start, end], keywords=[])
        else:
             iterable = self._generate_expr(iterable_node)
        return ast.For(target=target, iter=iterable, body=self._generate_block(node['body']), orelse=[])

    def _generate_return_stmt(self, node):
        return ast.Return(value=self._generate_expr(node['value']))
        
    def _generate_block(self, node):
        if 'stmts' in node:
            return [self._generate_statement(s) for s in self._flatten_statements(node['stmts'])]
        return [ast.Pass()]

    def _flatten_statements(self, stmts_node):
        flat_list = []
        if 'first' in stmts_node: flat_list.append(stmts_node['first'])
        if 'rest' in stmts_node:
            for item in stmts_node['rest']:
                flat_list.append(item[1]) # The statement is the second element
        return flat_list

    def _generate_method_decl(self, node):
        name = self._get_stem(node['name'])
        params = self._generate_params(node.get('params'))
        body = self._generate_block(node['body'])
        return ast.FunctionDef(name=name, args=params, body=body, decorator_list=[])

    def _generate_params(self, node):
        args = []
        if node and 'first' in node:
            args.append(ast.arg(arg=self._get_stem(node['first']['id'])))
            if 'rest' in node:
                for rest_node in node['rest']:
                    args.append(ast.arg(arg=self._get_stem(rest_node[1]['id'])))
        return ast.arguments(posonlyargs=[], args=args, kwonlyargs=[], kw_defaults=[], defaults=[])

    def _generate_expr(self, node):
        if isinstance(node, str):
            if node == 'verum': return ast.Constant(value=True)
            if node == 'falsus': return ast.Constant(value=False)
            if node == 'inanis': return ast.Constant(value=None)
            if node == 'id' and self._in_lambda_body: return ast.Name(id=self._lambda_param_name, ctx=ast.Load())
            return ast.Name(id=self._get_stem(node), ctx=ast.Load())
        
        if 'int' in node: return ast.Constant(value=int(node['int']))
        if 'float' in node: return ast.Constant(value=float(node['float']))
        if 'str' in node: return ast.Constant(value=node['str'][1:-1])
        if 'list' in node: return ast.List(elts=[self._generate_expr(e) for e in node['list'] if e not in (',', '[', ']') ], ctx=ast.Load())
        if 'mapstruct' in node:
            keys, values = [], []
            content = node['mapstruct']
            if content and 'mapcontent' in content:
                items = self._flatten_map(content['mapcontent'])
                for i in range(0, len(items), 2):
                    keys.append(self._generate_expr(items[i]))
                    values.append(self._generate_expr(items[i+1]))
            return ast.Dict(keys=keys, values=values)
            
        if 'op' in node:
            if 'left' in node: return self._generate_binary_op(node)
            return self._generate_unary_op(node)

        if 'postfix' in node: return self._generate_postfix(node['postfix'])
        if 'lambda_decl' in node: return self._generate_lambda_decl(node['lambda_decl'])
        if 'nodotcall_stmt' in node: return self._generate_call(node['nodotcall_stmt'])

        # Wrapper nodes
        for key in ['value', 'paren', 'base', 'item', 'ph', 'pg', 'pe', 'pd', 'pc', 'pb', 'pa', 'ternary', 'expr']:
             if key in node: return self._generate_expr(node[key])

        return ast.Constant(value=None)

    def _flatten_map(self, node):
        items = []
        if 'key' in node:
            items.append(node['key'])
            items.append(node['value'])
        if 'rest' in node and node['rest']:
            items.extend(self._flatten_map(node['rest']))
        return items

    def _generate_postfix(self, node):
        expr = self._generate_expr(node['base'])
        for op in node.get('ops', []):
            if 'meth' in op:
                call_node = op['meth']['call']
                func_name = self._get_stem(call_node['func'])
                args = [expr]
                if call_node.get('args'):
                    args.extend(self._generate_arg_list(call_node['args']))
                expr = ast.Call(func=ast.Name(id=func_name, ctx=ast.Load()), args=args, keywords=[])
            elif 'idx' in op:
                expr = ast.Subscript(value=expr, slice=self._generate_expr(op['idx']['expr']), ctx=ast.Load())
        return expr

    def _generate_call(self, node):
        func_name = self._get_stem(node['func'])
        args = []
        if node.get('args'):
             args = self._generate_arg_list(node['args'])
        return ast.Call(func=ast.Name(id=func_name, ctx=ast.Load()), args=args, keywords=[])

    def _generate_arg_list(self, node):
        args = [self._generate_expr(node['first'])]
        for rest_node in node.get('rest', []):
            args.append(self._generate_expr(rest_node[1]))
        return args

    def _generate_binary_op(self, d):
        op_map = {'+': ast.Add(), '-': ast.Sub(), '*': ast.Mult(), '/': ast.Div(), '%': ast.Mod(), '&': ast.BitAnd(), '|': ast.BitOr(), '^': ast.BitXor(), 'et': ast.And(), 'vel': ast.Or(), '==': ast.Eq(), '!=': ast.NotEq(), '<': ast.Lt(), '<=': ast.LtE(), '>': ast.Gt(), '>=': ast.GtE(), 'in': ast.In()}
        op_str = d['op']
        op = op_map.get(op_str)
        left, right = self._generate_expr(d['left']), self._generate_expr(d['right'])
        if op in [ast.And(), ast.Or()]: return ast.BoolOp(op=op, values=[left, right])
        if op:
            if isinstance(op, ast.In): return ast.Compare(left=left, ops=[op], comparators=[right])
            return ast.BinOp(left=left, op=op, right=right)
        if op_str in ('..', '.<'):
            end = right
            if op_str == '..': end = ast.BinOp(left=right, op=ast.Add(), right=ast.Constant(value=1))
            return ast.Slice(lower=left, upper=end)
        if d.get('condition'):
            return ast.IfExp(test=self._visit(d['condition']), body=self._visit(d['true_val']), orelse=self._visit(d['false_val']))
        return ast.Constant(value=None)
        
    def _generate_unary_op(self, d):
        op_map = {'-': ast.USub(), 'non': ast.Not()}
        op = op_map.get(d['op'])
        operand = self._generate_expr(d['right'])
        if op: return ast.UnaryOp(op=op, operand=operand)
        if d['op'] == '+': return operand
        return ast.Constant(value=None)

    def _generate_lambda_decl(self, n):
        old_in_lambda, old_param_name = self._in_lambda_body, self._lambda_param_name
        self._in_lambda_body = True
        if n.get('params'):
            args = self._generate_params(n['params'])
            if args.args: self._lambda_param_name = args.args[0].arg
        else:
            self._lambda_param_name, args = "id", ast.arguments(posonlyargs=[], args=[ast.arg(arg='id')], kwonlyargs=[], kw_defaults=[], defaults=[])
        
        body_nodes = self._generate_block(n['body'])
        if body_nodes and isinstance(body_nodes, list) and body_nodes:
            last_node = body_nodes[-1]
            if isinstance(last_node, ast.Return): body = last_node.value
            elif isinstance(last_node, ast.Expr): body = last_node.value
            else: body = ast.Constant(value=None)
        else: body = ast.Constant(value=None)
        
        self._in_lambda_body, self._lambda_param_name = old_in_lambda, old_param_name
        return ast.Lambda(args=args, body=body)

def generate_python_ast(ago_ast: Any) -> ast.Module:
    """Generate a Python AST from an Ago AST."""
    generator = AgoPythonCodeGenerator()
    return generator.generate(ago_ast)
