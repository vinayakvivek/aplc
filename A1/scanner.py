#!/usr/bin/python3

import sys
import ply.lex as lex
import ply.yacc as yacc


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


def t_ID(t):
    r'[_a-zA-Z][_a-zA-Z0-9]*'
    t.type = reserved.get(t.value, 'ID')    # Check for reserved words
    return t


def t_NUMBER(t):
    r'\d+'
    try:
        t.value = int(t.value)
    except ValueError:
        print("Integer value too large %d", t.value)
        t.value = 0
    return t


def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)


# end lex rules -------------------------------


# start parsing rules -------------------------

def p_code(p):
    'code : VOID MAIN LPAREN RPAREN LBRACKET body RBRACKET'
    print('body: %s' % (p[6]))


def p_body(p):
    '''body : statement SEMICOLON body
            | empty'''
    if len(p) > 2:
        p[0] = p[1] + p[2] + p[3]
    else:
        p[0] = ''


def p_statement(p):
    '''statement : INT list'''
    p[0] = p[1] + ' ' + p[2]
    print(list(p))


def p_list(p):
    '''list : ID COMMA list
            | pointer COMMA list
            | ID
            | pointer'''
    p[0] = ' '.join(p[1:])
    print(list(p))


def p_pointer(p):
    '''pointer : STAR pointer
               | STAR ID'''
    p[0] = ' '.join(p[1:])
    print('pointer', list(p))


def p_empty(p):
    'empty :'
    pass


def p_error(p):
    if p:
        print("syntax error at {0}".format(p.value))
    else:
        print("syntax error at EOF")


def process(data):
    lex.lex()
    yacc.yacc()
    yacc.parse(data)


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print('Invalid arguments!')
        sys.exit(-1)

    data = None
    with open(sys.argv[1], 'r') as file:
        data = file.read()

    process(data)
