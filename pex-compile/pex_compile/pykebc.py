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
