def cid(x):
    return type(x), x


class Label(object):
    __slots__ = ['name']

    def __init__(self, name):
        self.name = name

    def __hash__(self):
        return hash(('Label', self.name))


def recursive_map(tree, func):
    if isinstance(tree, tuple):
        return tuple((recursive_map(x, func) for x in tree))
    else:
        return func(tree)


class ByteCompiler(object):
    COMMANDS = [
        'nop',

        'attribute',
        'get_exception',
        'index',
        'load_const',
        'name',

        'eager_unpack_list',
        'make_struct',
        'stack',
        'unpack',

        'binop',
        'call_function',
        'pseudo_call',
        'unop',

        'cjump',
        'end_finally',
        'end_try',
        'except',
        'except_all',
        'finally',
        'jump',
        'raise',
        'return',
        'try',

        'init_function',
        'make_class',
    ]

    @staticmethod
    def argument_attribute(arg):
        action, num = arg
        action_id = {
            'get': 0,
            'set': 1,
            'del': 2,
        }[action]
        return (num << 2) | action_id

    @staticmethod
    def argument_binop(arg):
        operator_id = [
            '+',
            '-',
            '*',
            '/',
            '//',
            '%',
            '**',
            '<<',
            '>>',
            '|',
            '^',
            '&',
            '@',
            'and',
            'or',
            '==',
            '!=',
            '<',
            '<=',
            '>',
            '>=',
            'is',
            'is_not',
            'in',
            'not_in',
        ].index(arg)
        return operator_id
    
    @staticmethod
    def argument_call_function(arg):
        function_argument_count = arg
        return function_argument_count

    @staticmethod
    def argument_cjump(arg):
        jump_if, pop_value, address = arg
        return (address << 2) | (pop_value << 1) | jump_if

    @staticmethod
    def argument_eager_unpack_list(arg):
        expected_elements_count = arg
        return expected_elements_count

    @staticmethod
    def argument_end_finally(arg):
        return 0

    @staticmethod
    def argument_end_try(arg):
        return 0

    @staticmethod
    def argument_except(arg):
        address = arg
        return address

    @staticmethod
    def argument_except_all(arg):
        address = arg
        return address

    @staticmethod
    def argument_finally(arg):
        is_handling_exception, address = arg
        return (address << 1) | is_handling_exception

    @staticmethod
    def argument_index(arg):
        action = arg
        action_id = [
            'get',
            'set',
            'del',
        ].index(arg)
        return action_id

    @staticmethod
    def argument_init_function(arg):
        return 0

    @staticmethod
    def argument_jump(arg):
        address = arg
        return address

    @staticmethod
    def argument_load_const(arg):
        const_id = arg
        return const_id
    
    @staticmethod
    def argument_make_class(arg):
        base_classes_count = arg
        return base_classes_count

    @staticmethod
    def argument_make_struct(arg):
        struct, elements_count = arg
        struct_id = [
            'list',
            'tuple',
            'dict',
            'set',
        ].index(struct)
        return (elements_count << 2) | struct_id

    @staticmethod
    def argument_name(arg):
        action, name_id = arg
        action_id = [
            'load',
            'store',
            'del',
        ].index(action)
        return (name_id << 2) | action_id

    @staticmethod
    def argument_nop(arg):
        return 0

    @staticmethod
    def argument_pseudo_call(arg):
        pseudo_function = arg
        pseudo_function_id = [
            'iter',
            'next',
        ].index(arg)
        return pseudo_function_id

    @staticmethod
    def argument_raise(arg):
        return 0

    @staticmethod
    def argument_get_exception(arg):
        return 0

    @staticmethod
    def argument_return(arg):
        return 0

    @staticmethod
    def argument_stack(arg):
        action = arg
        action_id = [
            'pop',
            'dup',
            'dupdown3',
            'swap2',
        ].index(arg)
        return action_id

    @staticmethod
    def argument_try(arg):
        address = arg
        return address

    @staticmethod
    def argument_unop(arg):
        unop = arg
        unop_id = [
            '+',
            '-',
            '!',
            '~',
        ].index(unop)
        return unop_id

    @staticmethod
    def argument_unpack(arg):
        unpack_type = arg
        unpack_type_id = [
            'dict',
            'iterable',
        ].index(unpack_type)
        return unpack_type_id

    def instructions(self, instructions):
        return b''.join(self.instruction(instr) for instr in instructions)

    def instruction(self, instruction):
        command, argument = instruction
        command_repr = self.COMMANDS.index(command)
        argument_repr = self.argument(command, argument)

        assert command_repr < 2**8
        assert argument_repr < 2**24
        
        instruction_repr = (argument_repr << 8) | command_repr
        return instruction_repr.to_bytes(4, 'little')

    def argument(self, command, argument):

        argmap = {
            'attribute':            self.argument_attribute,
            'binop':                self.argument_binop,
            'call_function':        self.argument_call_function,
            'cjump':                self.argument_cjump,
            'eager_unpack_list':    self.argument_eager_unpack_list,
            'end_finally':          self.argument_end_finally,
            'end_try':              self.argument_end_try,
            'except':               self.argument_except,
            'except_all':           self.argument_except_all,
            'finally':              self.argument_finally,
            'get_exception':        self.argument_get_exception,
            'index':                self.argument_index,
            'init_function':        self.argument_init_function,
            'jump':                 self.argument_jump,
            'load_const':           self.argument_load_const,
            'make_class':           self.argument_make_class,
            'make_struct':          self.argument_make_struct,
            'name':                 self.argument_name,
            'nop':                  self.argument_nop,
            'pseudo_call':          self.argument_pseudo_call,
            'raise':                self.argument_raise,
            'return':               self.argument_return,
            'stack':                self.argument_stack,
            'try':                  self.argument_try,
            'unop':                 self.argument_unop,
            'unpack':               self.argument_unpack,
        }
        assert set(argmap.keys()) == set(self.COMMANDS)
        return argmap[command](argument)
        

class LinkedCode(object):
    def __init__(self, type, instructions, constants):
        self.type = type
        self.instructions = instructions
        self.constants = constants
    
    def __hash__(self):
        return hash(('LinkedCode', self.type, self.instructions))

    def __repr__(self):
        return self.asm()

    def asm(self):
        cmds = '\n'.join([
            str(opname) + ('' if arg is None else (' '+str(arg)))
            for opname, arg in self.instructions
        ])
        consts = '\n'.join([str(x) for x in enumerate(self.constants)])
        return cmds + '\n\n' + consts


class Code(object):
    def __init__(self, type='module'):
        self.reverse_constants = {}
        self.constants = []
        self.instructions = []
        self.label_counter = 0
        self.type = type

    def new_label(self, comment=None):
        label_name = f'L{self.label_counter}{"_" + comment if comment is not None else ""}'
        self.label_counter += 1
        return Label(label_name)

    def get_const_id(self, const):
        if cid(const) not in self.reverse_constants:
            self.reverse_constants[cid(const)] = len(self.constants)
            self.constants.append(const)
        return self.reverse_constants[cid(const)]
    
    def add_const(self, const):     # const is the constant itself! Not its ID
        self.add('load_const', self.get_const_id(const))

    def add(self, command, argument):
        self.instructions.append((command, argument))

    def __repr__(self):
        return f'Code(instructions: {repr(self.instructions)}, constants: {repr(self.constants)})'

    def asm(self):
        cmds = '\n'.join([
            str(opname) + ('' if arg is None else (' '+str(arg)))
            for opname, arg in self.instructions
        ])
        consts = '\n'.join([str(x) for x in enumerate(self.constants)])
        return cmds + '\n\n' + consts

    def add_label(self, label):
        self.add('DEFINE_LABEL', label)

    def link(self):
        label_values = {}
        names_values = {}
        instructions = []
        address = 0
        for command, argument in self.instructions:
            if command == 'DEFINE_LABEL':
                assert argument not in label_values
                label_values[argument] = address
            else:
                instructions.append((command, argument))
                address += 1
        
        map_function = lambda x: label_values[x] if isinstance(x, Label) else x

        for i, instruction in enumerate(instructions):
            instructions[i] = recursive_map(instruction, map_function)
            command, argument = instructions[i]
            if command == 'name':
                action, name = argument
                name_id = self.get_const_id(name)
                instructions[i] = command, (action, name_id)

        return LinkedCode(type=self.type, instructions=tuple(instructions), constants=self.constants)
