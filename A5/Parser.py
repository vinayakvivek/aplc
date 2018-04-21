import ply.yacc as yacc
from lexer import APLLexer
import logging
from ast import Token, BinOp, UnaryOp, Var, Const,\
    Decl, DeclList, If, While, Function, Param, Block,\
    FunctionCall, ReturnStmt
from cfg import CFG
from symtablev2 import mktable, Stack, get_width, print_procedures, print_variables
from asm import ASMCodeGenerator
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s]: %(message)s",
    datefmt='%I:%M:%S'
)
log = logging.getLogger()


def check_direct_access(p):
    if isinstance(p, Var):
        if p.entry['type'] != 'function' and p.entry['type'][1] == 0:
            print('[error] direct access of non-pointer %s.' % (p.value))
            sys.exit(0)


def print_op_error(op, lhs, rhs):
    _lhs = lhs[0] + '*' * lhs[1]
    _rhs = rhs[0] + '*' * rhs[1]
    print('invalid usage of operator %s' % (op))
    print('LHS is of type: ', _lhs, ', RHS is of type: ', _rhs)
    sys.exit(0)


class APLParser(object):
    tokens = APLLexer.tokens
    precedence = (
        ('left', 'BOOL_AND', 'BOOL_OR'),
        ('left', 'EQ', 'NE'),
        ('left', 'LT', 'LE', 'GT', 'GE'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'STAR', 'DIVIDE'),
        ('right', 'UMINUS'),
        ('right', 'BOOL_NOT'),
        ('nonassoc', 'IFX'),
        ('nonassoc', 'ELSE'),
    )

    def __init__(self, ast_filename, cfg_filename, sym_filename, asm_filename):
        self.lexer = APLLexer()
        # self.parser = yacc.yacc(module=self, debug=True, debuglog=log)
        self.parser = yacc.yacc(module=self, debug=True)
        self.ast_file = open(ast_filename, 'w')
        self.cfg_file = open(cfg_filename, 'w')
        self.sym_file = open(sym_filename, 'w')
        self.asm_file = open(asm_filename, 'w')

        self.offset = Stack()
        self.tableptr = Stack()
        self.nest_level = 1

        self.offset.push(0)
        self.tableptr.push(mktable(None, 'global'))

        self.last_id = None
        self.last_type = None
        self.last_stars = None
        self.block_id = 0

    def pop_tableptr(self):
        curr_symt = self.tableptr.top()
        curr_symt.addwidth(self.offset.top())
        self.tableptr.pop()
        self.offset.pop()
        self.nest_level -= 1

    def p_code(self, p):
        'code : global_statement_list'
        logging.debug('code: %s' % (p[1]))

        for node in p[1]:
            self.ast_file.write(str(node))

        self.ast_file.close()

        cfg = CFG(p[1])
        self.cfg_file.write(str(cfg))
        self.cfg_file.close()

        # print(self.tableptr.top())
        print_procedures(self.tableptr.top(), self.sym_file)
        print_variables(self.tableptr.top(), self.sym_file)

        ASMCodeGenerator(cfg, self.tableptr.top(), self.asm_file)

    def p_global_statement_list(self, p):
        '''global_statement_list : global_statement global_statement_list
                                 | empty'''
        if len(p) == 3:
            if isinstance(p[1], DeclList):
                p[0] = p[2]
            else:
                p[0] = [p[1]] + p[2]
        else:
            p[0] = []

    def p_global_statement(self, p):
        '''global_statement : declaration SEMICOLON
                            | function_def
                            | function_proto
                            | main_function_def'''
        p[0] = p[1]

    def p_main_function_def(self, p):
        '''main_function_def : void main LPAREN M RPAREN LBRACKET statement_list RBRACKET'''
        p[0] = Function((p[1], 0), p[2], [], p[7])
        self.pop_tableptr()

    def p_function_def(self, p):
        '''function_def : type stars id_d LPAREN M formal_params RPAREN LBRACKET statement_list RBRACKET'''
        p[0] = Function((p[1], len(p[2])), p[3].value, p[6], p[9])
        self.pop_tableptr()

    def p_function_proto(self, p):
        '''function_proto : type stars id_d LPAREN M formal_params RPAREN SEMICOLON'''
        p[0] = Function((p[1], len(p[2])), p[3].value, p[6], None)
        self.pop_tableptr()

    def p_void_function_def(self, p):
        '''function_def : void id_d LPAREN M formal_params RPAREN LBRACKET statement_list RBRACKET'''
        p[0] = Function((p[1], 0), p[2].value, p[5], p[8])
        self.pop_tableptr()

    def p_void_function_proto(self, p):
        '''function_def : void id_d LPAREN M formal_params RPAREN SEMICOLON'''
        p[0] = Function((p[1], 0), p[2].value, p[5], None)
        self.pop_tableptr()

    def p_M(self, p):
        '''M : empty'''
        p[0] = ''

        curr_symt = self.tableptr.top()
        func_name = self.last_id
        ret_type = (self.last_type, len(self.last_stars))

        # check if already exists
        if func_name in curr_symt.symbols:
            # print('prototype for function %s exists.' % (func_name))
            entry = curr_symt.symbols[func_name]
            if ret_type != entry['ret_type']:
                print('[function %s] return type mismatch with prototype.' % (func_name))
                sys.exit(0)

            table = entry['tableptr']
            self.tableptr.push(table)
            self.offset.push(0)
        else:
            new_table = mktable(curr_symt, func_name)
            new_table.num_params = 0
            curr_symt.enterfunc(func_name, new_table, ret_type)
            self.tableptr.push(new_table)
            self.offset.push(0)

        self.nest_level += 1

    def p_formal_params(self, p):
        '''formal_params : formal_param_list'''
        p[0] = p[1]

        # populate function symtable paramaters
        # type check prototype parameters

        curr_symt = self.tableptr.top()
        temp_param_len = curr_symt.num_params
        if temp_param_len > 0:
            if temp_param_len != len(p[1]):
                print('parameter mismatch with prototype')
                sys.exit(0)

            index = 0
            for k, v in curr_symt.symbols.items():
                param = p[1][index]
                if v['type'] != (param.dtype, param.pointer_level):
                    print('parameter #%d type mismatch with prototype.' % (index + 1))
                    sys.exit(0)
                index += 1
                if index == temp_param_len:
                    break

            curr_symt.symbols.clear()

        for param in p[1]:
            _type = (param.dtype, param.pointer_level)
            width = get_width(_type)
            curr_symt.enter(param.id, _type, width)
            self.offset.updateTop(self.offset.top() + width)

        curr_symt.num_params = len(p[1])

    def p_formal_param_list(self, p):
        '''formal_param_list : formal_param COMMA formal_param_list
                             | formal_param
                             | empty'''
        if len(p) == 4:
            p[0] = [p[1]] + p[3]
        elif len(p) == 2:
            if p[1]:
                p[0] = [p[1]]
            else:
                p[0] = []

    def p_formal_param(self, p):
        '''formal_param : type stars id_d'''
        p[0] = Param(p[3].value, p[1], len(p[2]))

    def p_type(self, p):
        '''type : INT
                | FLOAT'''
        p[0] = p[1]
        self.last_type = p[1]

    def p_void(self, p):
        '''void : VOID'''
        p[0] = p[1]
        self.last_type = p[1]
        self.last_stars = ''

    def p_main(self, p):
        '''main : MAIN'''
        p[0] = p[1]
        self.last_id = p[0]

    def p_stars(self, p):
        '''stars : STAR stars
                 | empty'''
        # zero or more STARS
        p[0] = p[1] + p[2] if len(p) > 2 else ''
        self.last_stars = p[0]

    def p_N(self, p):
        '''N : empty'''
        p[0] = ''

        curr_symt = self.tableptr.top()
        block_name = '@block_' + str(self.block_id)
        new_table = mktable(curr_symt, block_name)
        new_table.num_params = 0
        curr_symt.enterblock(block_name, new_table)
        self.tableptr.push(new_table)
        self.offset.push(0)

        self.nest_level += 1
        self.block_id += 1

    def p_block(self, p):
        '''block : N LBRACKET statement_list RBRACKET'''
        p[0] = Block(p[3])
        self.pop_tableptr()

    def p_statement_list(self, p):
        '''statement_list : statement statement_list
                          | block statement_list
                          | empty'''
        if len(p) == 3:
            if isinstance(p[1], DeclList):
                p[0] = p[2]
            else:
                p[0] = [p[1]] + p[2]
        else:
            p[0] = []

    def p_statement(self, p):
        '''statement : declaration SEMICOLON
                     | assignment SEMICOLON
                     | if_statement
                     | while_statement
                     | function_call SEMICOLON
                     | return_statement SEMICOLON'''
        p[0] = p[1]

    def p_return_statement(self, p):
        '''return_statement : RETURN expression
                            | RETURN'''

        f_symtable = self.tableptr.items[1]
        f_name = f_symtable.name
        ret_type = self.tableptr.items[0].symbols[f_name]['ret_type']

        if len(p) > 2:
            check_direct_access(p[2])

            p[0] = ReturnStmt(p[2])
            if p[2].dtype != ret_type:
                print('invalid return.')
                print('expected %s, got %s.' % (str(ret_type), str(p[2].dtype)))
                sys.exit(0)
        else:
            p[0] = ReturnStmt(None)
            if ret_type != ('void', 0):
                print('invalid return.')
                print('expected %s, got %s.' % (str(ret_type), 'void'))
                sys.exit(0)

    def p_block_statement(self, p):
        '''block_statement : block
                           | statement'''
        if isinstance(p[1], Block):
            p[0] = p[1].asts
        else:
            p[0] = [p[1]]

    def p_if_statement(self, p):
        '''if_statement : IF LPAREN logical_expression RPAREN block_statement %prec IFX'''
        p[0] = If(p[3], p[5], None)

    def p_ifelse_statement(self, p):
        '''if_statement : IF LPAREN logical_expression RPAREN block_statement ELSE block_statement %prec ELSE'''
        p[0] = If(p[3], p[5], p[7])

    def p_while_statement(self, p):
        '''while_statement : WHILE LPAREN logical_expression RPAREN block_statement'''
        p[0] = While(p[3], p[5])

    def p_function_call(self, p):
        '''function_call : id LPAREN expr_list RPAREN'''
        p[0] = FunctionCall(p[1].value, p[3])

        param_list = p[3]
        f_name = p[1].value

        entry = p[1].entry
        if entry['type'] != 'function':
            print('undefined function %s.' % (f_name))
            sys.exit(0)

        f_symtable = entry['tableptr']
        if f_symtable.num_params != len(param_list):
            print('function %s expected %d parameters, got %d.' % (f_name, f_symtable.num_params, len(param_list)))
            sys.exit(0)

        index = 0
        for k, v in f_symtable.symbols.items():
            if index == f_symtable.num_params:
                break

            if v['type'] != param_list[index].dtype:
                print('function %s expected %s as param #%d, got %s.' % (f_name, str(v['type']), index + 1, param_list[index].dtype))
                sys.exit(0)

            index += 1

        p[0].dtype = entry['ret_type']

    def p_expr_list(self, p):
        '''expr_list : expression COMMA expr_list
                     | expression
                     | empty'''
        if p[1] is not None:
            check_direct_access(p[1])

        if len(p) > 2:
            p[0] = [p[1]] + p[3]
        else:
            p[0] = [p[1]] if p[1] is not None else []

    def p_declaration(self, p):
        '''declaration : type list'''
        decl_vars = []
        curr_symt = self.tableptr.top()
        for v in p[2]:
            p_level = v[1]
            width = get_width((p[1], p_level))
            curr_symt.enter(v[0], (p[1], p_level), width)
            self.offset.updateTop(self.offset.top() + width)

            decl_vars.append(Decl(v[0], p[1], v[1]))

        p[0] = DeclList(decl_vars)

    def p_list_pointer(self, p):
        '''list : stars id_d COMMA list
                | stars id_d'''
        if len(p) > 3:
            p[0] = [(p[2].value, len(p[1]))] + p[4]
        else:
            p[0] = [(p[2].value, len(p[1]))]

    def p_id_nonuse(self, p):
        '''id_d : ID'''
        p[0] = Var(p[1])
        self.last_id = p[1]

    def p_assignment_lhs(self, p):
        '''assignment : lhs EQUALS expression'''
        t = Token('ASGN', '=')
        p[0] = BinOp(p[1], p[3], t)

        check_direct_access(p[1])
        check_direct_access(p[3])

        if p[1].dtype != p[3].dtype:
            print_op_error(p[2], p[1].dtype, p[3].dtype)

        p[0].dtype = p[1].dtype

    def p_lhs(self, p):
        '''lhs : STAR lhs'''
        t = Token('DEREF', p[1])
        p[0] = UnaryOp(p[2], t)

        dtype = p[2].dtype
        if dtype[1] <= 0:
            print('invalid usage of pointer.')
            sys.exit(0)

        p[0].dtype = (dtype[0], dtype[1]-1)

    def p_lhs_id(self, p):
        '''lhs : id'''
        p[0] = p[1]

    def p_expression_binop(self, p):
        '''expression : expression PLUS expression
                      | expression MINUS expression
                      | expression STAR expression
                      | expression DIVIDE expression'''
        t = None
        if p[2] == '+':
            t = Token('PLUS', '+')
        elif p[2] == '-':
            t = Token('MINUS', '-')
        elif p[2] == '*':
            t = Token('MUL', '*')
        elif p[2] == '/':
            t = Token('DIV', '/')

        p[0] = BinOp(p[1], p[3], t)

        check_direct_access(p[1])
        check_direct_access(p[3])

        if p[1].dtype != p[3].dtype or\
           p[1].dtype[1] != 0 or\
           p[1].dtype[0] == 'void':
            print_op_error(p[2], p[1].dtype, p[3].dtype)

        p[0].dtype = p[1].dtype

    def p_logical_expression_binop(self, p):
        '''logical_expression : expression LT expression
                              | expression LE expression
                              | expression GT expression
                              | expression GE expression
                              | expression EQ expression
                              | expression NE expression
                              | logical_expression BOOL_AND logical_expression
                              | logical_expression BOOL_OR logical_expression'''
        t = None
        if p[2] == '<':
            t = Token('LT', p[2])
        elif p[2] == '<=':
            t = Token('LE', p[2])
        elif p[2] == '>':
            t = Token('GT', p[2])
        elif p[2] == '>=':
            t = Token('GE', p[2])
        elif p[2] == '==':
            t = Token('EQ', p[2])
        elif p[2] == '!=':
            t = Token('NE', p[2])
        elif p[2] == '&&':
            t = Token('AND', p[2])
        elif p[2] == '||':
            t = Token('OR', p[2])

        p[0] = BinOp(p[1], p[3], t)

        check_direct_access(p[1])
        check_direct_access(p[3])

        if p[1].dtype != p[3].dtype or\
           p[1].dtype[1] != 0 or\
           p[1].dtype[0] == 'void':
            print_op_error(p[2], p[1].dtype, p[3].dtype)

        p[0].dtype = ('bool', 0)

    def p_logical_expression_not(self, p):
        '''logical_expression : BOOL_NOT logical_expression'''
        t = Token('NOT', '!')
        p[0] = UnaryOp(p[2], t)

        if p[2].dtype != ('bool', 0):
            print('invalid usage of operator logical NOT.')
            sys.exit(0)

        p[0].dtype = ('bool', 0)

    def p_expression_uminus(self, p):
        '''expression : MINUS expression %prec UMINUS'''
        t = Token('UMINUS', '-')
        p[0] = UnaryOp(p[2], t)

        check_direct_access(p[2])

        dtype = p[2].dtype
        if dtype[0] == 'void' or dtype[1] != 0:
            print('invalid use of operator unary minus on expression of type: ', dtype)
            sys.exit(0)

        p[0].dtype = dtype

    def p_expression_paren(self, p):
        '''expression : LPAREN expression RPAREN
           logical_expression : LPAREN logical_expression RPAREN'''
        p[0] = p[2]

    def p_expression_single(self, p):
        '''expression : number
                      | id
                      | addr
                      | function_call'''
        p[0] = p[1]

    def p_exression_deref(self, p):
        '''expression : STAR expression'''
        t = Token('DEREF', p[1])
        p[0] = UnaryOp(p[2], t)

        dtype = p[2].dtype
        if dtype[1] <= 0:
            print('invalid usage of pointer.')
            sys.exit(0)

        p[0].dtype = (dtype[0], dtype[1]-1)

    def p_addr(self, p):
        '''addr : AND id'''

        if p[2].entry['type'] == 'function':
            print('invalid usage of function %s.' % (p[2].value))
            sys.exit(0)

        t = Token('ADDR', p[1])
        p[0] = UnaryOp(p[2], t)

        dtype = p[2].entry['type']
        p[0].dtype = (dtype[0], dtype[1]+1)

    def p_id(self, p):
        '''id : ID'''
        curr_symt = self.tableptr.top()
        entry = curr_symt.look_up(p[1])
        if entry is None:
            print('undefined identifier %s.' % (p[1]))
            sys.exit(0)
        p[0] = Var(p[1], entry)

    def p_number_int(self, p):
        '''number : INTEGER'''
        p[0] = Const(p[1], ('int', 0))

    def p_number_real(self, p):
        '''number : REAL'''
        p[0] = Const(p[1], ('float', 0))

    def p_empty(self, p):
        'empty :'
        pass

    def p_error(self, p):
        if p:
            # stack_state_str = " ".join([symbol.type for symbol
            #                             in self.parser.symstack[1:]])
            print("Syntax error at '%s' line %d" %
                  (p.value, p.lineno))
        else:
            print("Syntax error at EOF")
        sys.exit(0)

    def parse(self, text):
        return self.parser.parse(text, self.lexer)


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print('Invalid arguments!')
        sys.exit(-1)

    data = None
    data_file = sys.argv[1]
    with open(data_file, 'r') as file:
        data = file.read()

    dirname = os.path.dirname(data_file)
    basename = os.path.basename(data_file)

    ast_filename = os.path.join(dirname, basename + '.ast')
    cfg_filename = os.path.join(dirname, basename + '.cfg')
    sym_filename = os.path.join(dirname, basename + '.sym')
    asm_filename = os.path.join(dirname, basename + '.s')

    # with open(out_file, 'w') as file:
    parser = APLParser(ast_filename, cfg_filename, sym_filename, asm_filename)
    parser.parse(data)

    print('Successfully Compiled.')