import ast
import copy

from pex_compile import pykebc


class LoopFrame(object):
    __slots__ = ['start_label', 'else_label', 'end_label']

    def __init__(self, start_label, else_label, end_label):
        self.start_label = start_label
        self.else_label = else_label
        self.end_label = end_label


class TryFinallyFrame(object):
    __slots__ = ['finally_label']

    def __init__(self, finally_label):
        self.finally_label = finally_label


class ContextManager(object):
    __slots__ = ['enter', 'exit']

    def __init__(self, enter, exit):
        self.enter = enter
        self.exit = exit

    def __enter__(self):
        self.enter()
        return self

    def __exit__(self, *args):
        self.exit(*args)


class TryExcept(object):
    def __init__(self, body, handlers):
        self.body = body
        self.handlers = handlers


class TryFinally(object):
    def __init__(self, body, finalbody):
        self.body = body
        self.finalbody = finalbody


class Compiler(object):
    __slots__ = ['code', 'frames']

    def __init__(self):
        self.code = None
        self.frames = None

    def visit_body(self, body):
        assert isinstance(body, list)
        for tree in body:
            self.visit_statement(tree)

    def visit_statement(self, tree):
        type_table = [
            #(ast.AnnAssign,     self.visit_ann_assign),
            #(ast.Assert,        self.visit_assert),
            (ast.Assign,        self.visit_assign),
            #(ast.AugAssign,     self.visit_aug_assign),
            (ast.Break,         self.visit_break),
            (ast.ClassDef,      self.visit_class_def),
            (ast.Continue,      self.visit_continue),
            (ast.Delete,        self.visit_delete),
            (ast.Expr,          self.visit_expr),
            (ast.For,           self.visit_for),
            (ast.FunctionDef,   self.visit_function_def),
            #(ast.Global,        self.visit_global),
            (ast.If,            self.visit_if),
            #(ast.Import,        self.visit_import),
            #(ast.ImportFrom,    self.visit_import_from),
            #(ast.Nonlocal,      self.visit_nonlocal),
            (ast.Pass,          self.visit_pass),
            (ast.Raise,         self.visit_raise),
            (ast.Return,        self.visit_return),
            (ast.Try,           self.visit_try),
            (ast.While,         self.visit_while),
            #(ast.With,          self.visit_with),
            (TryExcept,         self.visit_try_except),
            (TryFinally,        self.visit_try_finally),
        ]

        for Type, func in type_table:
            if isinstance(tree, Type):
                func(tree)
                return
        raise Exception(f'Unimplemented statement type: {type(tree)}')

    def visit_class_def(self, tree):
        assert isinstance(tree, ast.ClassDef)
        for base in tree.bases:
            self.visit_expr(base)
        # TODO: support keyword args (i.e. metaclasses and their kwargs)
        #
        comp = Compiler()
        class_code = comp.visit(tree, type='class')
        linked_class_code = class_code.link()
        self.code.add_const(linked_class_code)

        self.code.add('make_class', len(tree.bases))
        self.code.add('name', ('store', tree.name))

    
    def visit_raise(self, tree):
        assert isinstance(tree, ast.Raise)
        if tree.exc is None:
            self.code.add('get_exception', None)
        else:
            self.visit_expr(tree.exc)

        if tree.cause is not None:
            self.code.add_const(None)
            self.code.add('attribute', ('set', self.code.get_const_id('__context__')))
            self.visit_expr(tree.cause)
            self.code.add('attribute', ('set', self.code.get_const_id('__cause__')))
        self.code.add('raise', None)
    
    def visit_return(self, tree):
        assert isinstance(tree, ast.Return)
        if tree.value is None:
            self.code.add_const(None)
        else:
            self.visit_expr(tree.value)
        self.code.add('return', None)

    def visit_function_def(self, tree):
        assert isinstance(tree, ast.FunctionDef)
        comp = Compiler()
        function_code = comp.visit(tree, type='function')
        linked_function_code = function_code.link()
        self.code.add_const(linked_function_code)
        self.code.add('name', ('store', tree.name))

    def visit_delete(self, tree):
        assert isinstance(tree, ast.Delete)
        for target in tree.targets:
            self.visit_expr(target)

    def visit_continue(self, tree):
        assert isinstance(tree, ast.Continue)
        frames = copy.copy(self.frames)
        while frames:
            frame = frames.pop()
            if isinstance(frame, TryFinallyFrame):
                self.code.add('finally', (False, frame.finally_label))
            elif isinstance(frame, LoopFrame):
                self.code.add('jump', frame.start_label)
                return
            else:
                raise Exception(f'Unimplemented frame type: {type(frame)}')
        raise Exception('Continue outside of loop is not allowed')

    def visit_break(self, tree):
        assert isinstance(tree, ast.Break)
        frames = copy.copy(self.frames)
        while frames:
            frame = frames.pop()
            if isinstance(frame, TryFinallyFrame):
                self.code.add('finally', (False, frame.finally_label))
            elif isinstance(frame, LoopFrame):
                self.code.add('jump', frame.end_label)
                return
            else:
                raise Exception(f'Unimplemented frame type: {type(frame)}')
        raise Exception('Break outside of loop is not allowed')
    
    def visit_try_finally(self, tree):
        assert isinstance(tree, TryFinally)
        try_label = self.code.new_label('try-finally_try')
        finally_label = self.code.new_label('try-finally_finally')
        exit_label = self.code.new_label('try-finally_exit')
        
        self.code.add('try', try_label)
        with self.enter_try_finally(finally_label):
            self.visit_body(tree.body)
        self.code.add('end_try', None)
        self.code.add('finally', (False, finally_label))
        self.code.add('jump', exit_label)

        self.code.add_label(try_label)
        self.code.add('finally', (True, finally_label))
        self.code.add('raise', None)
        
        self.code.add_label(finally_label)
        self.visit_body(tree.finalbody)
        self.code.add('end_finally', None)

        self.code.add_label(exit_label)

    def visit_try_except(self, tree):
        assert isinstance(tree, TryExcept)
        try_label = self.code.new_label('try-except_try')
        exit_label = self.code.new_label('try-except_exit')

        self.code.add('try', try_label)
        self.visit_body(tree.body)
        self.code.add('end_try', None)
        self.code.add('jump', exit_label)
        
        self.code.add_label(try_label)
        except_labels = [self.code.new_label('try-except_handler') for _ in tree.handlers]
        for handler, label in zip(tree.handlers, except_labels):
            if handler.type is None:
                self.code.add('except_all', label)
            else:
                self.visit_expr(handler.type)
                self.code.add('except', label)
        self.code.add('raise', None)

        for handler, label in zip(tree.handlers, except_labels):
            self.code.add_label(label)
            if handler.name is None:
                self.code.add('stack', 'pop')
            else:
                self.code.add('name', ('store', handler.name))
            self.visit_body(handler.body)
            self.code.add('jump', exit_label)

        self.code.add_label(exit_label)

    def visit_try(self, tree):
        assert isinstance(tree, ast.Try)
        transformed_tree = TryFinally(
            body = [
                TryExcept(
                    body=tree.body,
                    handlers=tree.handlers,
                ),
                *tree.orelse,
            ],
            finalbody = tree.finalbody,
        )
        self.visit_try_finally(transformed_tree)

    def visit_pass(self, tree):
        assert isinstance(tree, ast.Pass)
        self.code.add('nop', None)

    def visit_for(self, tree):
        assert isinstance(tree, ast.For)
        start_label = self.code.new_label('for_start')
        try_label = self.code.new_label('for_try')
        except_label = self.code.new_label('for_except')
        else_label = self.code.new_label('for_else')
        end_label = self.code.new_label('for_end')
        bogus_label = self.code.new_label('for_bogus')

        # Stack: ...
        self.visit_expr(tree.iter)
        # Stack: ... expr
        self.code.add('pseudo_call', 'iter')
        # Stack: ... iter

        self.code.add_label(start_label)
        # === REPEATED ===
        with self.enter_loop(start_label, else_label, end_label):
            self.code.add('try', try_label)
            # Stack: ... iter
            self.code.add('stack', 'dup')
            # Stack: ... iter iter

            self.code.add('pseudo_call', 'next')
            # Stack: ... iter element
            self.code.add('end_try', None)

            # Save the current value into the specified variable/tuple/etc.
            self.visit_expr(tree.target)
            # Stack: ... iter
            
            self.visit_body(tree.body)
            self.code.add('jump', start_label)

        self.code.add_label(else_label)
        # Stack: ... iter
        self.code.add('stack', 'pop')
        # Stack: ...
        self.visit_body(tree.orelse)
        # Stack: ...
        self.code.add('jump', end_label)
    
        self.code.add_label(try_label)
        # Stack: ... iter iter exc
        self.code.add('name', ('load_global', 'StopIteration'))
        self.code.add('except', except_label)
        self.code.add('raise', None)

        self.code.add_label(except_label)
        # Stack: ... iter exc
        self.code.add('stack', 'pop')
        # Stack: ... iter
        self.code.add('jump', else_label)

        self.code.add_label(end_label)
        # Stack: ...

    def enter_loop(self, start_label, else_label, end_label):
        def enter():
            self.frames.append(LoopFrame(start_label, else_label, end_label))
        def exit(*args):
            self.frames.pop()
        return ContextManager(enter, exit)

    def enter_try_finally(self, finally_label):
        def enter():
            self.frames.append(TryFinallyFrame(finally_label))
        def exit(*args):
            self.frames.pop()
        return ContextManager(enter, exit)

    def visit_while(self, tree):
        assert isinstance(tree, ast.While)
        start_label = self.code.new_label('while_start')
        else_label = self.code.new_label('while_else')
        end_label = self.code.new_label('while_end')

        self.code.add_label(start_label)
        self.visit_expr(tree.test)
        self.code.add('cjump', (False, True, else_label))

        with self.enter_loop(start_label, else_label, end_label):
            self.visit_body(tree.body)
            self.code.add('jump', start_label)

        self.code.add_label(else_label)
        self.visit_body(tree.orelse)
        
        self.code.add_label(end_label)

    def visit_if(self, tree):
        assert isinstance(tree, ast.If)
        false_label = self.code.new_label('if_false')
        exit_label = self.code.new_label('if_exit')

        # Test
        self.visit_expr(tree.test)
        self.code.add('cjump', (False, True, false_label))

        # True branch
        self.visit_body(tree.body)
        self.code.add('jump', exit_label)

        # False branch
        self.code.add_label(false_label)
        self.visit_body(tree.orelse)

        # Exit
        self.code.add_label(exit_label)

    def visit_assign(self, tree):
        assert isinstance(tree, ast.Assign)
        self.visit_expr(tree.value)
        for i, target in enumerate(tree.targets):
            if i < len(tree.targets) - 1:
                self.code.add('stack', 'dup')
            self.visit_expr(target)

    def visit_expr(self, tree):
        if type(tree) is ast.Expr:
            self.visit_expr(tree.value)
            self.code.add('stack', 'pop')
            return

        type_table = [
            (ast.Attribute,     self.visit_attribute),
            (ast.BinOp,         self.visit_bin_op),
            (ast.BoolOp,        self.visit_bool_op),
            (ast.Bytes,         self.visit_bytes),
            (ast.Call,          self.visit_call),
            (ast.Compare,       self.visit_compare),
            (ast.Dict,          self.visit_dict),
            #(ast.DictComp,      self.visit_dict_comp),
            #(ast.Ellipsis,      self.visit_ellipsis),
            #(ast.FormattedStr,  self.visit_formatted_str),
            #(ast.GeneratorExp,  self.visit_generator_exp),
            (ast.IfExp,         self.visit_if_exp),
            #(ast.JoinedStr,     self.visit_joined_str),
            (ast.List,          self.visit_list),
            #(ast.ListComp,      self.visit_list_comp),
            (ast.Name,          self.visit_name),
            (ast.NameConstant,  self.visit_name_constant),
            (ast.Num,           self.visit_num),
            (ast.Set,           self.visit_set),
            #(ast.SetComp,       self.visit_set_comp),
            (ast.Starred,       self.visit_starred),
            (ast.Str,           self.visit_str),
            (ast.Subscript,     self.visit_subscript),
            (ast.Tuple,         self.visit_tuple),
            (ast.UnaryOp,       self.visit_unary_op),
        ]

        for Type, func in type_table:
            if isinstance(tree, Type):
                func(tree)
                return
        raise Exception(f'Unimplemented expression type: {type(tree)}')

    def visit_dict(self, tree):
        assert isinstance(tree, ast.Dict)
        for key, value in zip(tree.keys, tree.values):
            if key is None:
                self.visit_expr(value)
                self.code.add('unpack', 'dict')
            else:
                self.visit_expr(key)
                self.visit_expr(value)
        self.code.add('make_struct', ('dict', len(tree.keys)))

    def visit_if_exp(self, tree):
        assert isinstance(tree, ast.IfExp)
        false_label = self.code.new_label('if_exp_false')
        exit_label = self.code.new_label('if_exp_exit')

        # Test
        self.visit_expr(tree.test)
        self.code.add('cjump', (False, True, false_label))

        # True branch
        self.visit_expr(tree.body)
        self.code.add('jump', exit_label)

        # False branch
        self.code.add_label(false_label)
        self.visit_expr(tree.orelse)

        # Exit
        self.code.add_label(exit_label)

    def visit_subscript(self, tree):
        assert isinstance(tree, ast.Subscript)
        if isinstance(tree.slice, ast.Index):
            self.visit_subscript_index(tree)
        elif isinstance(tree.slice, ast.Slice):
            self.visit_subscript_slice(tree)
        elif isinstance(tree.slice, ast.ExtSlice):
            self.visit_subscript_ext_slice(tree)
        else:
            raise Exception(f'Unimplemented slice type: {type(tree.slice)}')

    visit_subscript_slice = NotImplemented
    visit_subscript_ext_slice = NotImplemented

    def visit_subscript_index(self, tree):
        assert isinstance(tree, ast.Subscript)
        assert isinstance(tree.slice, ast.Index)
        self.visit_expr(tree.value)
        self.visit_expr(tree.slice.value)
        if isinstance(tree.ctx, ast.Load):
            self.code.add('index', 'get')
        elif isinstance(tree.ctx, ast.Store):
            self.code.add('index', 'set')
        elif isinstance(tree.ctx, ast.Del):
            self.code.add('index', 'del')
        else:
            raise Exception(f'Unimplemented context: {type(tree.ctx)}')

    def visit_name_constant(self, tree):
        assert isinstance(tree, ast.NameConstant)
        self.code.add_const(tree.value)

    def visit_starred(self, tree):
        assert isinstance(tree, ast.Starred)
        if isinstance(tree.ctx, ast.Load):
            self.visit_expr(tree.value)
            self.code.add('unpack', 'iterable')
        elif isinstance(tree.ctx, ast.Store):
            self.visit_name(tree.value)
        else:
            raise Exception(f'Unimplemented context: {type(tree.ctx)}')

    def visit_attribute(self, tree):
        assert isinstance(tree, ast.Attribute)
        self.visit_expr(tree.value)
        if isinstance(tree.ctx, ast.Load):
            self.code.add('attribute', ('get', self.code.get_const_id(tree.attr)))
        elif isinstance(tree.ctx, ast.Store):
            self.code.add('attribute', ('set', self.code.get_const_id(tree.attr)))
        elif isinstance(tree.ctx, ast.Del):
            self.code.add('attribute', ('del', self.code.get_const_id(tree.attr)))
        else:
            raise Exception(f'Unimplemented context: {type(tree.ctx)}')

    visit_extended_call = NotImplemented

    def visit_call(self, tree):
        assert isinstance(tree, ast.Call)
        if tree.keywords:
            self.visit_extended_call()
            return
        self.visit_expr(tree.func)
        for argument in tree.args:
            self.visit_expr(argument)
        self.code.add('call_function', len(tree.args))

    def visit_name(self, tree):
        assert isinstance(tree, ast.Name)
        if isinstance(tree.ctx, ast.Load):
            self.code.add('name', ('load', tree.id))
        elif isinstance(tree.ctx, ast.Store):
            self.code.add('name', ('store', tree.id))
        elif isinstance(tree.ctx, ast.Del):
            self.code.add('name', ('del', tree.id))
        else:
            raise Exception(f'Unimplemented context: {type(tree.ctx)}')

    def visit_num(self, tree):
        assert isinstance(tree, ast.Num)
        self.code.add_const(tree.n)

    def visit_bytes(self, tree):
        assert isinstance(tree, ast.Bytes)
        self.code.add_const(tree.s)

    def visit_tuple(self, tree):
        assert isinstance(tree, ast.Tuple)
        if isinstance(tree.ctx, ast.Load):
            for element in tree.elts:
                self.visit_expr(element)
            self.code.add('make_struct', ('tuple', len(tree.elts)))
        elif isinstance(tree.ctx, ast.Store):
            self.code.add('eager_unpack_list', len(tree.elts))
            for element in reversed(tree.elts):
                self.visit_expr(element)
        elif isinstance(tree.ctx, ast.Del):
            self.code.add('eager_unpack_list', len(tree.elts))
            for element in reversed(tree.elts):
                self.visit_expr(element)
        else:
            raise Exception(f'Unimplemented context: {type(tree.ctx)}')

    def visit_list(self, tree):
        assert isinstance(tree, ast.List)
        if isinstance(tree.ctx, ast.Load):
            for element in tree.elts:
                self.visit_expr(element)
            self.code.add('make_struct', ('list', len(tree.elts)))
        elif isinstance(tree.ctx, ast.Store):
            self.code.add('eager_unpack_list', len(tree.elts))
            for element in reversed(tree.elts):
                self.visit_expr(element)
        elif isinstance(tree.ctx, ast.Del):
            self.code.add('eager_unpack_list', len(tree.elts))
            for element in reversed(tree.elts):
                self.visit_expr(element)

    def visit_set(self, tree):
        assert isinstance(tree, ast.Set)
        for element in tree.elts:
            self.visit_expr(element)
        self.code.add('make_struct', ('set', len(tree.elts)))

    def visit_str(self, tree):
        assert isinstance(tree, ast.Str)
        self.code.add_const(tree.s)

    @staticmethod
    def get_comparison_operator(op):
        return {
            ast.Eq:     '==',
            ast.NotEq:  '!=',
            ast.Lt:     '<',
            ast.LtE:    '<=',
            ast.Gt:     '>',
            ast.GtE:    '>=',
            ast.Is:     'is',
            ast.IsNot:  'is_not',
            ast.In:     'in',
            ast.NotIn:  'not_in',
        }[type(op)]

    def visit_compare(self, tree):
        # TODO: Optimize for simple comparisons
        assert isinstance(tree, ast.Compare)

        # Comparisons are lazy-evaluated. `1 < 2 < 3` is semantically equivalent to `1 < 2 and 2 < 3`.
        # When a comparison evaluates to False, other comparison are not evaluated and the overall result is
        # False. To achive this, the following is being done:
        #
        # 1. An accumulator with the initial value `True` is stored on the stack
        # 2. For each comparison:
        # 2.1. It is evaluated
        # 2.2. The result is being `and`ed with the accumulator (and stored in the accumulator)
        # 2.3. If the value of the accumulator is False, the loop is stopped and False is returned
        # 3. If all comparisons evaluated to True, True is returned
        #
        # Notation: v0, v1, v2, ... -- compared values (operands)
        # op1, op2, ... -- comparison operators
        # acc -- accumulator
        # lhs, rhs -- operands of the current comparison
        # result -- result of the current comparison
        #
        # The comparison is written in the code this way: `v0 op1 v1 op2 v2 op3 v3 ...`,
        # e.g. `0 < 1 >= 2 is not 3`

        # Define exit label
        exit_label = self.code.new_label('comp_exit')

        # Initialize the accumulator.
        self.code.add_const(True)
        # Stack: ... accum

        # Place the first operand on the stack.
        self.visit_expr(tree.left)
        # Stack: ... accum v0   (equiv. to: ... accum lhs)

        # Comparison index (from 0 inclusively to len(tree.comparators) not inclusively)
        # Will be used later
        i = 0
        for op, value in zip(tree.ops, tree.comparators):
            # Stack: ... accum lhs
    
            # Place the right operand of the current comparison
            self.visit_expr(value)
            # Stack: ... accum lhs rhs

            # Save the current rhs value to use it in the next comparison
            self.code.add('stack', 'dupdown3')
            # Stack: ... rhs accum lhs rhs
            
            # Evaluate the comparison
            self.code.add('binop', self.get_comparison_operator(op))
            # Stack: ... rhs accum result
            
            # `and` the result with the accumulator
            self.code.add('binop', 'and')
            # Stack: ... rhs accum

            # (see 2.3) if the value of accumulator is False, terminate the loop and return False
            self.code.add('cjump', (False, False, exit_label))

            i += 1
            # If the current comparison is the last one, then we don't need to do anything with the stack
            # because the exit label expects the values on the stack to have the following
            # layout: ... some_value accum (which is what we have now). However, the loop beginning
            # expects the stack to be: ... accum lhs. Thus, if the current comparison is not the last one,
            # we need to swap the two top values on the stack
            if i != len(tree.ops):
                self.code.add('stack', 'swap2')
                # Stack: ... accum rhs

                # If the current comparison was not the last one, current one's `rhs` becomes the next one's `lhs`
                # Stack: ... accum lhs
            # Stack [if last]:      ... rhs accum
            # Stack [if not last]:  ... accum lhs

        # If the loop terminates, code execution will jump here
        self.code.add_label(exit_label)
        # Stack: ... some_value accum

        # Del the second top value, which is unneeded
        self.code.add('stack', 'swap2')
        # Stack: ... accum some_value
        self.code.add('stack', 'pop')
        # Stack: ... accum
        # The value of `accum` is the result of the whole Compare node


    def visit_bin_op(self, tree):
        assert isinstance(tree, ast.BinOp)
        self.visit_expr(tree.left)
        self.visit_expr(tree.right)
        if isinstance(tree.op, ast.Add):
            self.code.add('binop', '+')
        elif isinstance(tree.op, ast.Sub):
            self.code.add('binop', '-')
        elif isinstance(tree.op, ast.Mult):
            self.code.add('binop', '*')
        elif isinstance(tree.op, ast.Div):
            self.code.add('binop', '/')
        elif isinstance(tree.op, ast.FloorDiv):
            self.code.add('binop', '//')
        elif isinstance(tree.op, ast.Mod):
            self.code.add('binop', '%')
        elif isinstance(tree.op, ast.Pow):
            self.code.add('binop', '**')
        elif isinstance(tree.op, ast.LShift):
            self.code.add('binop', '<<')
        elif isinstance(tree.op, ast.RShift):
            self.code.add('binop', '>>')
        elif isinstance(tree.op, ast.BitOr):
            self.code.add('binop', '|')
        elif isinstance(tree.op, ast.BitXor):
            self.code.add('binop', '^')
        elif isinstance(tree.op, ast.BitAnd):
            self.code.add('binop', '&')
        elif isinstance(tree.op, ast.MatMult):
            self.code.add('binop', '@')
        else:
            raise Exception(f'Unsupported binary operator type: {type(tree)}')

    def visit_bool_op(self, tree):
        assert isinstance(tree, ast.BoolOp)
        if isinstance(tree.op, ast.And):
            op = 'and'
        elif isinstance(tree.op, ast.Or):
            op = 'or'
        else:
            raise Exception(f'Unsupported bool operator type: {type(tree)}')
        self.visit_expr(tree.values[0])
        label = self.code.new_label('bool_op_exit')
        for operand in tree.values[1:]:
            # Skip evaluating what is not needed
            self.code.add('cjump', ({'and': False, 'or': True}[op], False, label))
            self.visit_expr(operand)
            self.code.add('binop', op)
        self.code.add_label(label)

    def visit_unary_op(self, tree):
        assert isinstance(tree, ast.UnaryOp)
        self.visit_expr(tree.operand)
        if isinstance(tree.op, ast.UAdd):
            self.code.add('unop', '+')
        elif isinstance(tree.op, ast.USub):
            self.code.add('unop', '-')
        elif isinstance(tree.op, ast.Not):
            self.code.add('unop', '!')
        elif isinstance(tree.op, ast.Invert):
            self.code.add('unop', '~')
        else:
            raise Exception(f'Unsupported unary operator type: {type(tree)}')

    def emit_function_prologue(self, tree):
        assert isinstance(tree, ast.FunctionDef)
        for arg in tree.args.args:
            self.code.add_const(arg.arg)
        self.code.add_const(len(tree.args.args))
        for arg in tree.args.defaults:
            self.visit_expr(arg)
        self.code.add_const(len(tree.args.defaults))
        
        for kwarg, default in zip(tree.args.kwonlyargs, tree.args.kw_defaults):
            self.code.add_const(kwarg.arg)
            if default is None:
                self.code.add_const(False)
            else:
                self.code.add_const(True)
                self.visit_expr(default)
        self.code.add_const(len(tree.args.kwonlyargs))
        self.code.add('init_function', None)
        

    def visit(self, tree, type='module'):
        self.code = pykebc.Code(type=type)
        if type == 'function':
            self.emit_function_prologue(tree)
        self.frames = []
        self.visit_body(tree.body)
        return self.code


def translate(tree):
    gen = Compiler()
    return gen.visit(tree)
