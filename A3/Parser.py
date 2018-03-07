#!/usr/bin/python3

import ply.yacc as yacc
from lexer import APLLexer
import logging
from ast import Token, BinOp, UnaryOp, Var, Const,\
    Decl, If, While
from cfg import CFG
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
        self.num_pointers = 0
        self.num_static_vars = 0
        self.num_assignments = 0
        self.ast_file = open(ast_filename, 'w')
        self.cfg_file = open(cfg_filename, 'w')

    def p_code(self, p):
        'code : VOID MAIN LPAREN RPAREN block'
        logging.debug('body: %s' % (p[5]))

        for node in p[5]:
            self.ast_file.write(str(node) + '\n')

        cfg = CFG(p[5])
        self.cfg_file.write(str(cfg))

    def p_block(self, p):
        '''block : LBRACKET statement_list RBRACKET'''
        p[0] = p[2]

    def p_statement_list(self, p):
        '''statement_list : statement statement_list
                          | block statement_list
                          | empty'''
        if p[1] is not None:
            if isinstance(p[1], list):
                # p[1] is a block
                p[0] = p[1] + p[2]
            else:
                if isinstance(p[1], Decl):
                    # ignore declaration statements
                    p[0] = p[2]
                else:
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
        if isinstance(p[1], list):
            p[0] = p[1]
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
        '''declaration : INT list'''
        p[0] = Decl()

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
        p[0] = ' '.join(p[1:])
        self.num_static_vars += 1

    def p_list_pointer(self, p):
        '''list : pointer COMMA list
                | pointer'''
        p[0] = ' '.join(p[1:])
        self.num_pointers += 1

    def p_pointer(self, p):
        '''pointer : STAR pointer
                   | STAR ID'''
        p[0] = ''.join(p[1:])

    def p_empty(self, p):
        'empty :'
        pass

    def p_error(self, p):
        if p:
            stack_state_str = " ".join([symbol.type for symbol
                                        in self.parser.symstack[1:]])
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