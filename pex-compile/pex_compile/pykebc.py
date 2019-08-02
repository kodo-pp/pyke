def cid(x):
    return type(x), x


class Code(object):
    def __init__(self):
        self.reverse_constants = {}
        self.constants = []
        self.commands = []
        self.label_counter = 0

    def new_label(self, comment=None):
        label_name = f'L{self.label_counter}{"_" + comment if comment is not None else ""}'
        self.label_counter += 1
        return label_name

    def get_const_id(self, const):
        if cid(const) not in self.reverse_constants:
            self.reverse_constants[cid(const)] = len(self.constants)
            self.constants.append(const)
        return self.reverse_constants[cid(const)]
    
    def add_const(self, const):     # const is the constant itself! Not its ID
        self.add('load_const', self.get_const_id(const))

    def add(self, command, argument):
        self.commands.append((command, argument))

    def __repr__(self):
        return f'Code(commands: {repr(self.commands)}, constants: {repr(self.constants)})'

    def asm(self):
        cmds = '\n'.join([str(opname) + ('' if arg is None else (' '+str(arg))) for opname, arg in self.commands])
        consts = '\n'.join([str(x) for x in enumerate(self.constants)])
        return cmds + '\n\n' + consts

    def add_label(self, label):
        self.add('DEFINE_LABEL', label)
