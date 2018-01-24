import ply.yacc as yacc
from lexer import APLLexer


class APLParser(object):
    tokens = APLLexer.tokens

    def __init__(self):
        self.lexer = APLLexer()
        self.parser = yacc.yacc(module=self)

    def p_code(self, p):
        'code : VOID MAIN LPAREN RPAREN LBRACKET body RBRACKET'
        print('body: %s' % (p[6]))

    def p_body(self, p):
        '''body : statement SEMICOLON body
                | empty'''
        if len(p) > 2:
            p[0] = p[1] + p[2] + p[3]
        else:
            p[0] = ''

    def p_statement(self, p):
        '''statement : INT list'''
        p[0] = p[1] + ' ' + p[2]
        print(list(p))

    def p_list(self, p):
        '''list : ID COMMA list
                | pointer COMMA list
                | ID
                | pointer'''
        p[0] = ' '.join(p[1:])
        print(list(p))

    def p_pointer(self, p):
        '''pointer : STAR pointer
                   | STAR ID'''
        p[0] = ' '.join(p[1:])
        print('pointer', list(p))

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