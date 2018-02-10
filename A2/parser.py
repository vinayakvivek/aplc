import ply.yacc as yacc
from lexer import APLLexer
import logging
from ast import Token, AST, BinOp, UnaryOp, Var, Const
import sys

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s]: %(message)s",
    datefmt='%I:%M:%S'
)
log = logging.getLogger()


class APLParser(object):
    tokens = APLLexer.tokens
    precedence = (
        ('left', 'PLUS', 'MINUS'),
        ('left', 'STAR', 'DIVIDE'),
        ('right', 'UMINUS'),
    )

    def __init__(self):
        self.lexer = APLLexer()
        # self.parser = yacc.yacc(module=self, debug=True, debuglog=log)
        self.parser = yacc.yacc(module=self, debug=True)
        self.num_pointers = 0
        self.num_static_vars = 0
        self.num_assignments = 0

    def p_code(self, p):
        'code : VOID MAIN LPAREN RPAREN LBRACKET body RBRACKET'
        logging.debug('body: %s' % (p[6]))

    def p_body(self, p):
        '''body : statement SEMICOLON body
                | empty'''
        p[0] = ' '.join([str(v) for v in p[1:]])

    def p_statement(self, p):
        '''statement : INT list
                     | assignment'''
        p[0] = ' '.join([str(v) for v in p[1:]])
        logging.debug('statement: ' + str(list(p)))

    def p_assignment_id(self, p):
        '''assignment : id EQUALS expression'''

        # check if expression has only const leaves
        if not p[3].const_leaves:
            t = Token('ASGN', '=')
            p[0] = BinOp(p[1], p[3], t)
            print(p[0])
        else:
            sys.stderr.write('Syntax error at %s =\n' % (p[1].token.value))
            sys.exit(0)

    def p_assignment_deref(self, p):
        '''assignment : deref EQUALS expression'''
        t = Token('ASGN', '=')
        p[0] = BinOp(p[1], p[3], t)
        print(p[0])

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
            t = Token('DIVIDE', '/')

        p[0] = BinOp(p[1], p[3], t)

    def p_expression_uminus(self, p):
        '''expression : MINUS expression %prec UMINUS'''
        t = Token('UMINUS', '-')
        p[0] = UnaryOp(p[2], t)

    def p_expression_paren(self, p):
        '''expression : LPAREN expression RPAREN'''
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
        t = Token('VAR', p[1])
        p[0] = Var(t)

    def p_int(self, p):
        '''int : INTEGER'''
        t = Token('CONST', p[1])
        p[0] = Const(t)

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
            sys.stderr.write("Syntax error at '%s', type %s, on line %d\n"
                             "Parser state: %s %s . %s\n" %
                             (p.value, p.type, p.lineno,
                              self.parser.state, stack_state_str, p))
        else:
            sys.stderr.write("Syntax error at EOF\n")

    def parse(self, text):
        return self.parser.parse(text, self.lexer)
