import ply.lex as lex


class APLLexer(object):

    def __init__(self):
        self.lexer = lex.lex(module=self)
        self.lexer.linestart = 0

    def __iter__(self):
        return iter(self.lexer)

    def token(self):
        return self.lexer.token()

    def input(self, data):
        self.lexer.input(data)

    reserved = {
        'int': 'INT',
        'float': 'FLOAT',
        'void': 'VOID',
        'main': 'MAIN',
        'if': 'IF',
        'else': 'ELSE',
        'while': 'WHILE',
        'return': 'RETURN',
    }

    tokens = [
        'REAL', 'INTEGER', 'ID',
        'STAR', 'SEMICOLON', 'COMMA', 'AND',
        'LPAREN', 'RPAREN', 'LBRACKET', 'RBRACKET',
        'EQUALS', 'PLUS', 'MINUS', 'DIVIDE',
        'LT', 'LE', 'GT', 'GE', 'EQ', 'NE',
        'BOOL_AND', 'BOOL_OR', 'BOOL_NOT',
    ] + list(reserved.values())

    t_ignore = " \t"

    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_LBRACKET = r'\{'
    t_RBRACKET = r'\}'
    t_STAR = r'\*'
    t_SEMICOLON = r'\;'
    t_COMMA = r'\,'
    t_AND = r'\&'

    t_PLUS = r'\+'
    t_MINUS = r'\-'
    # t_TIMES = r'\*'
    t_DIVIDE = r'\/'
    t_EQUALS = r'\='

    t_LT = r'\<'
    t_LE = r'\<\='
    t_GT = r'\>'
    t_GE = r'\>\='
    t_EQ = r'\=\='
    t_NE = r'\!\='
    t_BOOL_AND = r'\&\&'
    t_BOOL_OR = r'\|\|'
    t_BOOL_NOT = r'\!'

    def t_ID(self, t):
        r'[_a-zA-Z][_a-zA-Z0-9]*'
        # Check for reserved words
        t.type = APLLexer.reserved.get(t.value, 'ID')
        return t

    def t_REAL(self, t):
        r'([0-9]+[.][0-9]*|[.][0-9]+)'
        try:
            val = float(t.value)
        except ValueError:
            print("float value too large %d", t.value)
            t.value = 0
        return t

    def t_INTEGER(self, t):
        r'\d+'
        try:
            val = int(t.value)
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
