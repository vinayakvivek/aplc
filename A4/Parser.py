import ply.yacc as yacc
from lexer import APLLexer
import logging
from ast import Token, BinOp, UnaryOp, Var, Const,\
    Decl, DeclList, If, While, Function, Param, Block
from cfg import CFG
from symbol_table import Type, SymbolTable
import sys
import os

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s]: %(message)s",
    datefmt='%I:%M:%S'
)
log = logging.getLogger()


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

    def __init__(self, ast_filename, cfg_filename):
        self.lexer = APLLexer()
        # self.parser = yacc.yacc(module=self, debug=True, debuglog=log)
        self.parser = yacc.yacc(module=self, debug=True)
        self.ast_file = open(ast_filename, 'w')
        self.cfg_file = open(cfg_filename, 'w')

        # self.global_symtable = SymbolTable()
        # self.curr_symtable = self.global_symtable

        # print(self.global_symtable)

    def p_code(self, p):
        'code : global_statement_list'
        logging.debug('code: %s' % (p[1]))

        for node in p[1]:
            self.ast_file.write(str(node))

        self.ast_file.close()

        cfg = CFG(p[1])
        self.cfg_file.write(str(cfg))
        self.cfg_file.close()

        # print(self.global_symtable)

    def p_global_statement_list(self, p):
        '''global_statement_list : global_statement global_statement_list
                                 | empty'''
        if p[1] is not None:
            # if isinstance(p[1], Decl):
            #     # ignore declaration statements
            #     p[0] = p[2]
            # else:
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
        '''main_function_def : VOID MAIN LPAREN RPAREN block'''
        p[0] = Function(p[1], p[2], [], p[5].asts)

    def p_function_def(self, p):
        '''function_def : type ID LPAREN formal_param_list RPAREN block
                        | type stars ID LPAREN formal_param_list RPAREN block'''
        if len(p) == 7:
            p[0] = Function(p[1], p[2], p[4], p[6].asts)
            # self.curr_symtable = self.curr_symtable.add_function(p[2], Type(p[1], 0), p[4], is_proto=False)
        elif len(p) == 8:
            p[0] = Function(p[1] + p[2], p[3], p[5], p[7].asts)
            # self.curr_symtable = self.curr_symtable.add_function(p[3], Type(p[1], len(p[2])), p[5], is_proto=True)

    def p_function_proto(self, p):
        '''function_proto : type ID LPAREN formal_param_list RPAREN SEMICOLON
                          | type stars ID LPAREN formal_param_list RPAREN SEMICOLON'''
        if len(p) == 7:
            p[0] = Function(p[1], p[2], p[4], None)
            # self.curr_symtable.add_function(p[2], Type(p[1], 0), p[4], is_proto=True)
        elif len(p) == 8:
            p[0] = Function(p[1] + p[2], p[3], p[5], None)
            # self.curr_symtable.add_function(p[3], Type(p[1], len(p[2])), p[5], is_proto=True)

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
        '''formal_param : type ID
                        | type stars ID'''
        if len(p) > 3:
            p[0] = Param(p[3], p[1], len(p[2]))
        else:
            p[0] = Param(p[2], p[1], 0)

    def p_type(self, p):
        '''type : INT
                | FLOAT'''
        p[0] = p[1]

    def p_stars(self, p):
        '''stars : STAR stars
                 | STAR'''
        # one or more STARS
        if len(p) > 2:
            p[0] = p[1] + p[2]
        else:
            p[0] = p[1]

    def p_block(self, p):
        '''block : LBRACKET statement_list RBRACKET'''
        p[0] = Block(p[2])
        # self.curr_symtable = self.curr_symtable.parent

    def p_statement_list(self, p):
        '''statement_list : statement statement_list
                          | block statement_list
                          | empty'''
        if p[1] is not None:
            # if isinstance(p[1], list):
            #     # p[1] is a block
            #     p[0] = p[1] + p[2]
            # else:
                # if isinstance(p[1], Decl):
                #     # ignore declaration statements
                #     p[0] = p[2]
                # else:
            p[0] = [p[1]] + p[2]
        else:
            p[0] = []

    def p_statement(self, p):
        '''statement : declaration SEMICOLON
                     | assignment SEMICOLON
                     | if_statement
                     | while_statement'''
        p[0] = p[1]

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

    def p_declaration(self, p):
        '''declaration : type list'''
        decl_vars = []
        for v in p[2]:
            decl_vars.append(Decl(v[0], p[1], v[1]))

        p[0] = DeclList(decl_vars)
        # for v in p[2]:
        #     # v <- (id, pointer_level)
        #     self.curr_symtable.add_var(v[0], Type(p[1], v[1]))

    def p_assignment_id(self, p):
        '''assignment : id EQUALS expression'''

        # check if expression has only const leaves
        if not p[3].const_leaves:
            t = Token('ASGN', '=')
            p[0] = BinOp(p[1], p[3], t)
        else:
            print('Syntax error at %s =\n' % (p[1].token.value))
            sys.exit(0)

    def p_assignment_deref(self, p):
        '''assignment : deref EQUALS expression'''
        t = Token('ASGN', '=')
        p[0] = BinOp(p[1], p[3], t)

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

    def p_logical_expression_not(self, p):
        '''logical_expression : BOOL_NOT logical_expression'''
        t = Token('NOT', '!')
        p[0] = UnaryOp(p[2], t)

    def p_expression_uminus(self, p):
        '''expression : MINUS expression %prec UMINUS'''
        t = Token('UMINUS', '-')
        p[0] = UnaryOp(p[2], t)

    def p_expression_paren(self, p):
        '''expression : LPAREN expression RPAREN
           logical_expression : LPAREN logical_expression RPAREN'''
        p[0] = p[2]

    def p_expression_single(self, p):
        '''expression : int
                      | id
                      | deref_addr'''
        p[0] = p[1]

    def p_deref_addr(self, p):
        '''deref_addr : deref
                      | addr'''
        p[0] = p[1]

    def p_deref(self, p):
        '''deref : STAR deref_addr
                 | STAR id'''
        t = Token('DEREF', p[1])
        p[0] = UnaryOp(p[2], t)

    def p_addr(self, p):
        '''addr : AND deref_addr
                | AND id'''
        t = Token('ADDR', p[1])
        p[0] = UnaryOp(p[2], t)

    def p_id(self, p):
        '''id : ID'''
        p[0] = Var(p[1])

    def p_int(self, p):
        '''int : INTEGER'''
        p[0] = Const(p[1])

    # list:-------
    def p_list_id(self, p):
        '''list : ID COMMA list
                | ID'''
        if len(p) > 2:
            p[0] = [(p[1], 0)] + p[3]
        else:
            p[0] = [(p[1], 0)]

    def p_list_pointer(self, p):
        '''list : stars ID COMMA list
                | stars ID'''
        if len(p) > 3:
            p[0] = [(p[2], len(p[1]))] + p[3]
        else:
            p[0] = [(p[2], len(p[1]))]

    # def p_pointer(self, p):
    #     '''pointer : stars ID'''
    #     p[0] = ''.join(p[1:])

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

    # with open(out_file, 'w') as file:
    parser = APLParser(ast_filename, cfg_filename)
    parser.parse(data)

    print('Successfully Parsed')