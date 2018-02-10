
class Token(object):

    def __init__(self, type, value):
        self.type = type
        self.value = value


class AST(object):

    def __init__(self, token):
        self.token = token


class BinOp(AST):

    def __init__(self, left_child, right_child, token):
        AST.__init__(self, token)
        self.left_child = left_child
        self.right_child = right_child
        self.op = token.type

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        name = self.token.type
        tab = '\t' * depth
        return tab + name + '\n' + tab + '(\n' + self.left_child.as_string(depth + 1) +\
               tab + '\t,\n' + self.right_child.as_string(depth + 1) + tab + ')\n'


class UnaryOp(AST):

    def __init__(self, child, token):
        AST.__init__(self, token)
        self.child = child
        self.op = token.type

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        name = self.token.type
        tab = '\t' * depth
        return tab + name + '\n' + tab + '(\n' +\
               self.child.as_string(depth + 1) + tab + ')\n'


class Var(AST):

    def __init__(self, token):
        AST.__init__(self, token)

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        name = self.token.value
        return '\t'*depth + 'VAR(%s)\n' % (name)


class Const(AST):

    def __init__(self, token):
        AST.__init__(self, token)

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        name = self.token.value
        return '\t'*depth + 'CONST(%s)\n' % (name)


if __name__ == '__main__':
    t1 = Token('PLUS', '+')
    t2 = Token('VAR', 'a')
    t3 = Token('VAR', 'b')
    t4 = Token('DEREF', '*')
    t5 = Token('CONST', '5')

    tree = BinOp(UnaryOp(BinOp(Var(t2), Var(t3), t1), t4), Const(t5), t1)
    print(tree)