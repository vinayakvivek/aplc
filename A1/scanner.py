#!/usr/bin/python3

import sys
import ply.lex as lex
import ply.yacc as yacc


class APLLexer(object):

    def __init__(self):
        self.lexer = lex.lex(module=self)
        self.lexer.linestart = 0
        self.num_pointers = 0

    def __iter__(self):
        return iter(self.lexer)

    def token(self):
        return self.lexer.token()

    def input(self, data):
        self.lexer.input(data)

    reserved = {
        'int': 'INT',
        'void': 'VOID',
        'main': 'MAIN',
    }

    tokens = [
        'INTEGER', 'ID', 'STAR', 'SEMICOLON', 'COMMA',
        'LPAREN', 'RPAREN', 'LBRACKET', 'RBRACKET',
    ] + list(reserved.values())

    t_ignore = " \t\n"

    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_LBRACKET = r'\{'
    t_RBRACKET = r'\}'
    t_STAR = r'\*'
    t_SEMICOLON = r'\;'
    t_COMMA = r'\,'

    def t_ID(self, t):
        r'[_a-zA-Z][_a-zA-Z0-9]*'
        t.type = APLLexer.reserved.get(t.value, 'ID')    # Check for reserved words
        return t

    def t_NUMBER(self, t):
        r'\d+'
        try:
            t.value = int(t.value)
        except ValueError:
            print("Integer value too large %d", t.value)
            t.value = 0
        return t

    def t_error(self, t):
        print("Illegal character '%s'" % t.value[0])
        t.lexer.skip(1)

    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)
        t.lexer.linestart = t.lexer.lexpos


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


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print('Invalid arguments!')
        sys.exit(-1)

    data = None
    with open(sys.argv[1], 'r') as file:
        data = file.read()

    parser = APLParser()
    parser.parse(data)
