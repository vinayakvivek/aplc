from collections import OrderedDict
from ast import BinOp, UnaryOp, FunctionCall, ReturnStmt,\
    Var, Const
from symtablev2 import get_width
from copy import deepcopy

def code_string(code):
    temp_string = ''
    for line in code:
        if line[0] == '@':
            temp_string += line[1:] + '\n'
        else:
            temp_string += '\t' + line + '\n'
    return temp_string


class ASMCodeGenerator():

    def __init__(self, cfg, symtable, asm_file):
        self.cfg = cfg
        self.symtable = symtable
        self.asm_file = asm_file

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

        self.float_registers = OrderedDict({
            'f10': True,
            'f12': True,
            'f14': True,
            'f16': True,
            'f18': True,
            'f2': True,
            'f20': True,
            'f22': True,
            'f24': True,
            'f26': True,
            'f28': True,
            'f30': True,
            'f4': True,
            'f6': True,
            'f8': True,
        })

        self.fcmp_count = 0

        self.data_part()
        self.text_part()

    def get_register(self, freg=False):

        if not freg:
            for k, v in self.registers.items():
                if v:
                    return k
        else:
            for k, v in self.float_registers.items():
                if v:
                    return k
        return None

    def use_register(self, reg):
        if reg in self.float_registers:
            self.float_registers[reg] = False
        elif reg in self.registers:
            self.registers[reg] = False

    def free_register(self, reg):
        if reg in self.float_registers:
            self.float_registers[reg] = True
        elif reg in self.registers:
            self.registers[reg] = True

    def data_part(self):
        data_string = '\t.data\n'

        global_vars = []
        for k, v in self.symtable.symbols.items():
            if v['type'] not in ('function', 'block'):
                # variable
                global_vars.append((k, v))

        global_vars = sorted(global_vars, key=lambda x: x[0])
        for (k, v) in global_vars:
            data_string += 'global_' + k + ':\t'
            if v['type'][1] > 0 or v['type'][0] == 'int':
                data_string += '.word\t0\n'
            else:
                data_string += '.space\t8\n'

        self.global_vars = global_vars
        self.asm_file.write(data_string + '\n')

    def text_part(self):

        func_start = 0

        for i in range(1, self.cfg.node_count):
            node = self.cfg.nodes[i]
            if node.func is not None or node.end:
                self.func_code(self.cfg.nodes[func_start:i])
                func_start = i

    def get_variable_offset(self, name, local_vars, params):
        '''
        return ('<offset>' or 'global_<id>', is_global)
        '''
        for (k, v) in local_vars:
            if name == k:
                return (v['offset'], False)

        for (k, v) in params:
            if name == k:
                return (v['offset'], False)

        for (k, v) in self.global_vars:
            if name == k:
                return ('global_%s' % k, True)

        return None

    def simple_expression_code(self, ast, local_vars, params, code=[]):
        '''
        generate code for a simple ast
            : *a
            : t0 + t1
            : a - t0
            : expr op expr
            : func(expr, expr)

        return register which contains the value
        '''
        def move_reg(reg, freg=False):
            t_reg = self.get_register(freg)
            if not freg:
                code.append('move $%s, $%s' % (t_reg, reg))
            else:
                code.append('mov.s $%s, $%s' % (t_reg, reg))

            self.use_register(t_reg)
            self.free_register(reg)
            return t_reg

        if isinstance(ast, Const):
            if ast.dtype[0] == 'int':
                reg = self.get_register()
                code.append('li $%s, %s' % (reg, ast.value))
                self.use_register(reg)
                return reg
            elif ast.dtype[0] == 'float':
                '''li.s $f10, <const>'''
                reg = self.get_register(freg=True)
                code.append('li.s $%s, %s' % (reg, ast.value))
                self.use_register(reg)
                return reg

        elif isinstance(ast, Var):
            '''lw $<reg>, <c_offset>($sp)'''
            reg = self.get_register()
            loc, is_global = self.get_variable_offset(ast.value, local_vars, params)
            if is_global:
                code.append('lw $%s, %s' % (reg, loc))
            else:
                code.append('lw $%s, %d($sp)' % (reg, loc))
            self.use_register(reg)
            return reg

        elif isinstance(ast, UnaryOp):
            if ast.op == 'DEREF':
                '''
                s0 <= c_reg
                lw $s1, 0($s0)
                free s0
                '''
                # check for `*&c` case
                if isinstance(ast.child, UnaryOp) and\
                   ast.child.op == 'ADDR' and isinstance(ast.child.child, Var):
                    return self.simple_expression_code(ast.child.child, local_vars, params, code)

                reg1 = self.simple_expression_code(ast.child, local_vars, params, code)

                if ast.dtype[1] > 0 or ast.dtype[0] == 'int':
                    reg2 = self.get_register()
                    code.append('lw $%s, 0($%s)' % (reg2, reg1))
                    self.free_register(reg1)
                    self.use_register(reg2)
                    return reg2
                elif ast.dtype == ('float', 0):
                    reg2 = self.get_register(freg=True)
                    code.append('l.s $%s, 0($%s)' % (reg2, reg1))
                    self.free_register(reg1)
                    self.use_register(reg2)
                    return reg2

            elif ast.op == 'ADDR':
                '''
                la $s0, global_<id>
                OR
                addi $s0, $sp, <a_offset>
                '''
                assert isinstance(ast.child, Var)
                loc, is_global = self.get_variable_offset(ast.child.value, local_vars, params)
                reg = self.get_register()
                if is_global:
                    code.append('la $%s, %s' % (reg, loc))
                else:
                    code.append('addi $%s, $sp, %d' % (reg, loc))
                self.use_register(reg)
                return reg

            elif ast.op == 'UMINUS':
                if ast.dtype == ('int', 0):
                    '''
                    negu $s1, $s0
                    move $s0, $s1
                    '''
                    reg1 = self.simple_expression_code(ast.child, local_vars, params, code)
                    reg2 = self.get_register()
                    code.append('negu $%s, $%s' % (reg2, reg1))
                    self.use_register(reg2)
                    self.free_register(reg1)
                    return move_reg(reg2)
                elif ast.dtype == ('float', 0):
                    '''
                    neg.s $f12, $f10
                    mov.s $f10, $f12
                    '''
                    reg1 = self.simple_expression_code(ast.child, local_vars, params, code)
                    reg2 = self.get_register(freg=True)
                    code.append('neg.s $%s, $%s' % (reg2, reg1))
                    self.use_register(reg2)
                    self.free_register(reg1)
                    return move_reg(reg2, freg=True)

            elif ast.op == 'NOT':
                reg1 = self.simple_expression_code(ast.child, local_vars, params, code)
                reg2 = self.get_register()
                code.append('xori $%s, $%s, 1' % (reg2, reg1))
                self.use_register(reg2)
                self.free_register(reg1)
                return move_reg(reg2)

        elif isinstance(ast, BinOp):

            if ast.left_child.dtype == ('int', 0):
                '''integer operations'''

                reg1 = self.simple_expression_code(ast.left_child, local_vars, params, code)
                reg2 = self.simple_expression_code(ast.right_child, local_vars, params, code)
                reg = self.get_register()

                if ast.op == 'PLUS':
                    '''add $s1, $<reg1>, $<reg2>'''
                    code.append('add $%s, $%s, $%s' % (reg, reg1, reg2))

                elif ast.op == 'MINUS':
                    '''sub $s1, $<reg1>, $<reg2>'''
                    code.append('sub $%s, $%s, $%s' % (reg, reg1, reg2))

                elif ast.op == 'MUL':
                    '''mul $s1, $<reg1>, $<reg2>'''
                    code.append('mul $%s, $%s, $%s' % (reg, reg1, reg2))

                elif ast.op == 'DIV':
                    '''
                    div $s0, $s1
                    mflo $s2
                    '''
                    code.append('div $%s, $%s' % (reg1, reg2))
                    code.append('mflo %s' % (reg))

                elif ast.op == 'LT':
                    '''slt $s2, $s1, $s0'''
                    code.append('slt $%s, $%s, $%s' % (reg, reg1, reg2))

                elif ast.op == 'GT':
                    '''slt $s2, $s0, $s1'''
                    code.append('slt $%s, $%s, $%s' % (reg, reg2, reg1))

                elif ast.op == 'LE':
                    '''sle $s2, $s1, $s0'''
                    code.append('sle $%s, $%s, $%s' % (reg, reg1, reg2))

                elif ast.op == 'GE':
                    '''sle $s2, $s0, $s1'''
                    code.append('sle $%s, $%s, $%s' % (reg, reg2, reg1))

                elif ast.op == 'EQ':
                    '''seq $s2, $s1, $s0'''
                    code.append('seq $%s, $%s, $%s' % (reg, reg1, reg2))

                elif ast.op == 'NE':
                    '''sne $s2, $s1, $s0'''
                    code.append('sne $%s, $%s, $%s' % (reg, reg1, reg2))

                self.use_register(reg)
                self.free_register(reg1)
                self.free_register(reg2)
                return move_reg(reg)

            elif ast.left_child.dtype == ('bool', 0):

                reg1 = self.simple_expression_code(ast.left_child, local_vars, params, code)
                reg2 = self.simple_expression_code(ast.right_child, local_vars, params, code)
                reg = self.get_register()

                if ast.op == 'OR':
                    '''or $s2, $s1, $s0'''
                    code.append('or $%s, $%s, $%s' % (reg, reg1, reg2))

                elif ast.op == 'AND':
                    '''or $s2, $s1, $s0'''
                    code.append('and $%s, $%s, $%s' % (reg, reg1, reg2))

                self.use_register(reg)
                self.free_register(reg1)
                self.free_register(reg2)
                return move_reg(reg)

            elif ast.left_child.dtype == ('float', 0):
                '''float operations'''

                reg1 = self.simple_expression_code(ast.left_child, local_vars, params, code)
                reg2 = self.simple_expression_code(ast.right_child, local_vars, params, code)

                if ast.op in ('PLUS', 'MINUS', 'MUL', 'DIV'):

                    reg = self.get_register(freg=True)

                    if ast.op == 'PLUS':
                        '''add.s $f14, $f10, $f12'''
                        code.append('add.s $%s, $%s, $%s' % (reg, reg1, reg2))

                    elif ast.op == 'MINUS':
                        '''sub.s $f14, $<reg1>, $<reg2>'''
                        code.append('sub.s $%s, $%s, $%s' % (reg, reg1, reg2))

                    elif ast.op == 'MUL':
                        '''mul.s $f14, $<reg1>, $<reg2>'''
                        code.append('mul.s $%s, $%s, $%s' % (reg, reg1, reg2))

                    elif ast.op == 'DIV':
                        '''div.s $f14, $<reg1>, $<reg2>'''
                        code.append('div.s $%s, $%s, $%s' % (reg, reg1, reg2))

                    self.use_register(reg)
                    self.free_register(reg1)
                    self.free_register(reg2)
                    return move_reg(reg, freg=True)

                elif ast.op in ('LT', 'GT', 'LE', 'GE', 'EQ'):
                    '''
                        c.lt.s $f10, $f12
                        bc1f L_CondFalse_0
                        li $s0, 1
                        j L_CondEnd_0
                    L_CondFalse_0:
                        li $s0, 0
                    L_CondEnd_0:
                        move $s1, $s0
                    '''
                    cond_label = self.fcmp_count
                    self.fcmp_count += 1

                    reg = self.get_register()
                    self.use_register(reg)

                    if ast.op == 'LT':
                        code.append('c.lt.s $%s, $%s' % (reg1, reg2))

                    elif ast.op == 'GT':
                        code.append('c.lt.s $%s, $%s' % (reg2, reg1))

                    elif ast.op == 'LE':
                        code.append('c.le.s $%s, $%s' % (reg1, reg2))

                    elif ast.op == 'GE':
                        code.append('c.le.s $%s, $%s' % (reg2, reg1))

                    elif ast.op == 'EQ':
                        code.append('c.eq.s $%s, $%s' % (reg2, reg1))

                    code.append('bc1f L_CondFalse_%d' % (cond_label))
                    code.append('li $%s, 1' % (reg))
                    code.append('j L_CondEnd_%d' % (cond_label))
                    code.append('@L_CondFalse_%d:' % (cond_label))
                    code.append('li $%s, 0' % (reg))
                    code.append('@L_CondEnd_%d:' % (cond_label))

                    self.free_register(reg1)
                    self.free_register(reg2)
                    return move_reg(reg)

                elif ast.op == 'NE':
                    cond_label = self.fcmp_count
                    self.fcmp_count += 1

                    reg = self.get_register()
                    self.use_register(reg)

                    code.append('c.eq.s $%s, $%s' % (reg2, reg1))
                    code.append('bc1f L_CondTrue_%d' % (cond_label))
                    code.append('li $%s, 0' % (reg))
                    code.append('j L_CondEnd_%d' % (cond_label))
                    code.append('@L_CondTrue_%d:' % (cond_label))
                    code.append('li $%s, 1' % (reg))
                    code.append('@L_CondEnd_%d:' % (cond_label))

                    self.free_register(reg1)
                    self.free_register(reg2)
                    return move_reg(reg)

        elif isinstance(ast, FunctionCall):
            num_params = len(ast.actual_params)
            regs = {}
            param_widths = []

            for i, p in enumerate(ast.actual_params):
                if not isinstance(p, (Var, Const, UnaryOp)):
                    regs[i] = self.simple_expression_code(p, local_vars, params, code)

                param_widths.append(get_width(p.dtype))

            params_offsets = [0] * num_params
            offset = 0

            for i, w in enumerate(reversed(param_widths)):
                params_offsets[num_params - i - 1] = offset
                offset -= w

            code.append('# setting up activation record for called function')

            for i, p in enumerate(ast.actual_params):

                if p.dtype[1] > 0 or p.dtype[0] == 'int':
                    if isinstance(p, (Var, Const, UnaryOp)):
                        reg = self.simple_expression_code(p, local_vars, params, code)
                        code.append('sw $%s, %d($sp)' % (reg, params_offsets[i]))
                        self.free_register(reg)
                    else:
                        code.append('sw $%s, %d($sp)' % (regs[i], params_offsets[i]))
                        self.free_register(regs[i])
                elif p.dtype == ('float', 0):
                    if isinstance(p, (Var, Const, UnaryOp)):
                        reg = self.simple_expression_code(p, local_vars, params, code)
                        code.append('s.s $%s, %d($sp)' % (reg, params_offsets[i]))
                        self.free_register(reg)
                    else:
                        code.append('s.s $%s, %d($sp)' % (regs[i], params_offsets[i]))
                        self.free_register(regs[i])

            code.append('sub $sp, $sp, %d' % (-offset))
            code.append('jal %s' % (ast.id) + ' # function call')
            code.append('add $sp, $sp, %d' % (-offset) + ' # destroying activation record of called function')
            return 'v1'

    def return_code(self, ast, local_vars, params):
        code = []
        reg = self.simple_expression_code(ast, local_vars, params, code)

        if not isinstance(ast, (Var, Const)):
            move_reg = self.get_register()
            code.append('move $%s, $%s' % (move_reg, reg))
            self.use_register(move_reg)
            self.free_register(reg)

            code.append('move $v1, $%s' % (move_reg) + ' # move return value to $v1')
            self.free_register(move_reg)
        else:
            code.append('move $v1, $%s' % (reg) + ' # move return value to $v1')
            self.free_register(reg)

        return code_string(code)

    def assignment_code(self, ast, local_vars, params):

        code = []
        rhs_reg = self.simple_expression_code(ast.right_child, local_vars, params, code)

        if isinstance(ast.right_child, FunctionCall):
            reg = self.get_register()
            code.append('move $%s, $v1' % (reg) + ' # using the return value of called function')
            self.use_register(reg)
            rhs_reg = reg

        if isinstance(ast.left_child, Var):
            loc, is_global = self.get_variable_offset(ast.left_child.value, local_vars, params)
            if is_global:
                code.append('sw $%s, %s' % (rhs_reg, loc))
            else:
                code.append('sw $%s, %d($sp)' % (rhs_reg, loc))

        elif isinstance(ast.left_child, UnaryOp) :
            lhs_ast = ast.left_child
            lhs_reg = self.simple_expression_code(lhs_ast.child, local_vars, params, code)

            if lhs_ast.op == 'DEREF':
                if ast.dtype == ('float', 0):
                    code.append('s.s $%s, 0($%s)' % (rhs_reg, lhs_reg))
                else:
                    code.append('sw $%s, 0($%s)' % (rhs_reg, lhs_reg))

            self.free_register(lhs_reg)

        self.free_register(rhs_reg)

        return code_string(code)

    def logical_code(self, ast, local_vars, params, goto_t, goto_f):
        code = []

        '''
        move $s0, $s2
        bne $s0, $0, <node.goto_t>
        j <node.goto_f>
        '''
        reg = self.simple_expression_code(ast, local_vars, params, code)
        code.append('bne $%s, $0, label%d' % (reg, goto_t))
        code.append('j label%d' % (goto_f))

        self.free_register(reg)
        return code_string(code)

    def node_code(self, node, local_vars, params, func_name):

        code = ''

        if node.is_return:
            # return node
            if node.old_body[0] is not None:
                code += self.return_code(node.old_body[0], local_vars, params)

            code += '\tj epilogue_' + func_name + '\n\n'
            return code

        if node.logical:
            code += self.logical_code(node.old_body[0], local_vars, params, node.goto_t, node.goto_f)
            return code

        for line_ast in node.old_body:
            if isinstance(line_ast, BinOp):
                assert line_ast.token.type == 'ASGN'
                # code += '\t' + line_ast.as_line() + '\n'
                code += self.assignment_code(line_ast, local_vars, params)
            elif isinstance(line_ast, FunctionCall):
                f_code = []
                self.simple_expression_code(line_ast, local_vars, params, f_code)
                code += code_string(f_code)

        code += '\tj label' + str(node.goto) + '\n'
        return code

    def func_code(self, cfg_nodes):
        assert cfg_nodes[0].func is not None

        func_name = cfg_nodes[0].func.name

        code_string = '\t.text\t# The .text assembler directive indicates\n'
        code_string += '\t.globl ' + func_name + '\t# The following is the code\n'
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

        ###### BODY

        for node in cfg_nodes:

            code_string += 'label' + str(node.id) + ':\n'
            self.label_count += 1

            code_string += self.node_code(node, local_vars, params, func_name)

        ###### EPILOGUE

        code_string += '# Epilogue begins\n'
        code_string += 'epilogue_' + func_name + ':\n'
        code_string += '\tadd $sp, $sp, %d\n' % (8 + local_vars_size)
        code_string += '\tlw $fp, -4($sp)\n'
        code_string += '\tlw $ra, 0($sp)\n'
        code_string += '\tjr $ra\t# Jump back to the called procedure\n'
        code_string += '# Epilogue ends\n'

        print(code_string)
        self.asm_file.write(code_string)
