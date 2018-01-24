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
        # Check for reserved words
        t.type = APLLexer.reserved.get(t.value, 'ID')
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
