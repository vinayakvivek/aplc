from collections import OrderedDict
from ast import BinOp, UnaryOp, FunctionCall


class ASMCodeGenerator():

    def __init__(self, cfg, symtable):
        self.cfg = cfg
        self.symtable = symtable

        self.label_count = 0

        self.registers = OrderedDict({
            's0': True,
            's1': True,
            's2': True,
            's3': True,
            's4': True,
            's5': True,
            's6': True,
            's7': True,

            't0': True,
            't1': True,
            't2': True,
            't3': True,
            't4': True,
            't5': True,
            't6': True,
            't7': True,
            't8': True,
            't9': True,
        })

        self.data_part()
        self.text_part()

    def get_free_register(self):
        for k, v in self.registers.items():
            if v:
                return k
        return None

    def data_part(self):
        data_string = '\t.data\n'

        for k, v in self.symtable.symbols.items():
            if v['type'] not in ('function', 'block'):
                # variable
                data_string += 'global_' + k + ':\t'
                if v['type'][1] > 0 or v['type'][0] == 'int':
                    data_string += '.word\t0\n'
                else:
                    data_string += '.space\t8\n'

        print(data_string)

    def text_part(self):

        func_start = 0

        for i in range(1, self.cfg.node_count):
            node = self.cfg.nodes[i]
            if node.func is not None or node.end:
                self.func_code(self.cfg.nodes[func_start:i])
                func_start = i

    def func_code(self, cfg_nodes):
        assert cfg_nodes[0].func is not None

        func_name = cfg_nodes[0].func.name

        code_string = '\t.text\n\t.globl ' + func_name + '\n'
        code_string += func_name + ':\n'

        ##### PROLOGUE PART

        code_string += '# Prologue begins\n'
        code_string += '\tsw $ra, 0($sp)\t# Save the return address\n'
        code_string += '\tsw $fp, -4($sp)\t# Save the frame pointer\n'
        code_string += '\tsub $fp, $sp, 8\t# Update the frame pointer\n'

        f_entry = self.symtable.look_up(func_name)
        f_symtable = f_entry['tableptr']

        num_params = f_symtable.num_params
        local_vars = []
        params = []
        local_vars_size = 0

        i = 0
        for k, v in f_symtable.symbols.items():
            if i < num_params:
                params.append((k, v))
                i += 1
                continue

            if v['type'] not in ('block', ):
                local_vars.append((k, v))
                local_vars_size += v['width']

        local_vars = sorted(local_vars, key=lambda x: x[0])

        offset = 4
        for var in local_vars:
            var[1]['offset'] = offset
            offset += var[1]['width']

        offset = 8 + local_vars_size + 4
        for p in params:
            p[1]['offset'] = offset
            offset += p[1]['width']

        code_string += '\tsub $sp, $sp, %d\t# Make space for the locals\n' % (8 + local_vars_size)
        code_string += '# Prologue ends\n'

        ######

        # for node in cfg_nodes:

        #     code_string += 'label' + str(node.id) + ':\n'
        #     self.label_count += 1

        #     for item in node.body:





        print(code_string)
