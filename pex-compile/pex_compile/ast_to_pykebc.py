import ast

from pex_compile import pykebc


class Compiler(object):
    __slots__ = ['code']

    def visit_module(self, tree):
        assert isinstance(tree, ast.Module)
        for node in tree.body:
            self.visit_statement(node)

    def visit_statement(self, tree):
        type_table = [
            #(ast.AnnAssign,     self.visit_ann_assign),
            #(ast.Assert,        self.visit_assert),
            #(ast.Assign,        self.visit_assign),
            #(ast.AugAssign,     self.visit_aug_assign),
            #(ast.Break,         self.visit_break),
            #(ast.ClassDef,      self.visit_class_def),
            #(ast.Continue,      self.visit_continue),
            #(ast.Delete,        self.visit_delete),
            (ast.Expr,          self.visit_expr),
            #(ast.For,           self.visit_for),
            #(ast.FunctionDef,   self.visit_function_def),
            #(ast.Global,        self.visit_global),
            #(ast.If,            self.visit_if),
            #(ast.Import,        self.visit_import),
            #(ast.ImportFrom,    self.visit_import_from),
            #(ast.Nonlocal,      self.visit_nonlocal),
            #(ast.Pass,          self.visit_pass),
            #(ast.Raise,         self.visit_raise),
            #(ast.Return,        self.visit_return),
            #(ast.Try,           self.visit_try),
            #(ast.While,         self.visit_while),
            #(ast.With,          self.visit_with),
        ]

        for Type, func in type_table:
            if isinstance(tree, Type):
                func(tree)
                return
        raise Exception(f'Unimplemented statement type: {type(tree)}')

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

    def visit_if_exp(self, tree):
        assert isinstance(tree, ast.IfExp)
        self.visit_expr(tree.test)
        false_label = self.code.new_label()
        exit_label = self.code.new_label()
        self.code.add('cjump', (False, True, false_label))
        self.visit_expr(tree.body)
        self.code.add('jump', exit_label)
        self.code.add_label(false_label)
        self.visit_expr(tree.orelse)
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
        self.code.add('index', None)

    def visit_name_constant(self, tree):
        assert isinstance(tree, ast.NameConstant)
        self.code.add_const(tree.value)

    def visit_starred(self, tree):
        assert isinstance(tree, ast.Starred)
        self.visit_expr(tree.value)
        self.code.add('unpack', 'iterable')

    def visit_attribute(self, tree):
        assert isinstance(tree, ast.Attribute)
        self.visit_expr(tree.value)
        self.code.add('load_attribute', self.code.get_const_id(tree.attr))

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
        self.code.add('load_name', tree.id)

    def visit_num(self, tree):
        assert isinstance(tree, ast.Num)
        self.code.add_const(tree.n)

    def visit_bytes(self, tree):
        assert isinstance(tree, ast.Bytes)
        self.code.add_const(tree.s)

    def visit_tuple(self, tree):
        assert isinstance(tree, ast.Tuple)
        for element in tree.elts:
            self.visit_expr(element)
        self.code.add('make_struct', ('tuple', len(tree.elts)))

    def visit_list(self, tree):
        assert isinstance(tree, ast.List)
        for element in tree.elts:
            self.visit_expr(element)
        self.code.add('make_struct', ('list', len(tree.elts)))

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
        assert isinstance(tree, ast.Compare)
        # TODO: Optimize for simple comparisons
        label = self.code.new_label()
        self.code.add_const(True)
        self.visit_expr(tree.left)
        i = 0
        for op, value in zip(tree.ops, tree.comparators):
            self.visit_expr(value)
            self.code.add('stack', 'dupdown3')
            self.code.add('binop', self.get_comparison_operator(op))
            self.code.add('binop', 'and')
            self.code.add('cjump', (False, False, label))
            i += 1
            if i != len(tree.ops):
                self.code.add('stack', 'swap2')
        self.code.add_label(label)
        self.code.add('stack', 'swap2')
        self.code.add('stack', 'pop')


    def visit_bin_op(self, tree):
        assert isinstance(tree, ast.BinOp)
        self.visit_expr(tree.left)
        self.visit_expr(tree.right)
        if isinstance(tree.op, ast.Add):
            self.code.add('binary_op', '+')
        elif isinstance(tree.op, ast.Sub):
            self.code.add('binary_op', '-')
        elif isinstance(tree.op, ast.Mult):
            self.code.add('binary_op', '*')
        elif isinstance(tree.op, ast.Div):
            self.code.add('binary_op', '/')
        elif isinstance(tree.op, ast.FloorDiv):
            self.code.add('binary_op', '//')
        elif isinstance(tree.op, ast.Mod):
            self.code.add('binary_op', '%')
        elif isinstance(tree.op, ast.Pow):
            self.code.add('binary_op', '**')
        elif isinstance(tree.op, ast.LShift):
            self.code.add('binary_op', '<<')
        elif isinstance(tree.op, ast.RShift):
            self.code.add('binary_op', '>>')
        elif isinstance(tree.op, ast.BitOr):
            self.code.add('binary_op', '|')
        elif isinstance(tree.op, ast.BitXor):
            self.code.add('binary_op', '^')
        elif isinstance(tree.op, ast.BitAnd):
            self.code.add('binary_op', '&')
        elif isinstance(tree.op, ast.MatMult):
            self.code.add('binary_op', '@')
        else:
            raise Exception(f'Unsupported unary operator type: {type(tree)}')

    def visit_bool_op(self, tree):
        assert isinstance(tree, ast.BoolOp)
        if isinstance(tree.op, ast.And):
            op = 'and'
        elif isinstance(tree.op, ast.Or):
            op = 'or'
        else:
            raise Exception(f'Unsupported bool operator type: {type(tree)}')
        self.visit_expr(tree.values[0])
        label = self.code.new_label()
        for operand in tree.values[1:]:
            # Skip evaluating what is not needed
            self.code.add('cjump', ({'and': False, 'or': True}[op], False, label))
            self.visit_expr(operand)
            self.code.add('binary_op', op)
        self.code.add_label(label)

    def visit_unary_op(self, tree):
        assert isinstance(tree, ast.UnaryOp)
        self.visit_expr(tree.operand)
        if isinstance(tree.op, ast.UAdd):
            self.code.add('unary_op', '+')
        elif isinstance(tree.op, ast.USub):
            self.code.add('unary_op', '-')
        elif isinstance(tree.op, ast.Not):
            self.code.add('unary_op', '!')
        elif isinstance(tree.op, ast.Invert):
            self.code.add('unary_op', '~')
        else:
            raise Exception(f'Unsupported unary operator type: {type(tree)}')

    def visit(self, tree):
        self.code = pykebc.Code()
        self.visit_module(tree)
        return self.code


def translate(tree):
    gen = Compiler()
    return gen.visit(tree)
