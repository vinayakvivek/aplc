import ply.yacc as yacc
from lexer import APLLexer
import logging

logging.basicConfig(
    level=logging.ERROR,
    format="[%(levelname)s]: %(message)s",
    datefmt='%I:%M:%S'
)
log = logging.getLogger()


class APLParser(object):
    tokens = APLLexer.tokens

    def __init__(self):
        self.lexer = APLLexer()
        self.parser = yacc.yacc(module=self, debug=True, debuglog=log)
        self.num_pointers = 0
        self.num_static_vars = 0
        self.num_assignments = 0

    def p_code(self, p):
        'code : VOID MAIN LPAREN RPAREN LBRACKET body RBRACKET'
        logging.debug('body: %s' % (p[6]))

    def p_body(self, p):
        '''body : statement SEMICOLON body
                | empty'''
        if len(p) > 2:
            p[0] = p[1] + p[2] + p[3]
        else:
            p[0] = ''

    def p_statement(self, p):
        '''statement : INT list
                     | assignment_list'''
        p[0] = ' '.join(p[1:])
        logging.debug('statement: ' + str(list(p)))

    def p_assignment_list(self, p):
        '''assignment_list : assignment COMMA assignment_list
                           | assignment'''
        p[0] = ' '.join(p[1:])
        logging.debug('assignment_list: ' + str(list(p)))

    def p_assignment(self, p):
        '''assignment : ID EQUALS assignment
                      | pointer EQUALS assignment
                      | ID EQUALS ID
                      | ID EQUALS AND ID
                      | pointer EQUALS INTEGER
                      | pointer EQUALS ID
                      | pointer EQUALS pointer'''
        p[0] = ' '.join([str(v) for v in p[1:]])
        self.num_assignments += 1
        logging.debug('assignment: ' + str(list(p)))

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
            raise Exception("Syntax error at '%s', type %s, on line %d\n"
                            "Parser state: %s %s . %s" %
                            (p.value, p.type, p.lineno,
                             self.parser.state, stack_state_str, p))
        else:
            raise Exception("Syntax error at EOF")

    def parse(self, text):
        return self.parser.parse(text, self.lexer)
