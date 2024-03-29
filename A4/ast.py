
class Token(object):

    def __init__(self, type, value):
        self.type = type
        self.value = value


class AST(object):

    def __init__(self, token, const_leaves=False):
        self.token = token
        # self.const_leaves = const_leaves

class BinOp(AST):

    def __init__(self, left_child, right_child, token):
        AST.__init__(self, token)
        self.left_child = left_child
        self.right_child = right_child
        self.op = token.type
        # self.const_leaves = left_child.const_leaves and right_child.const_leaves
        self.dtype = None

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        name = self.token.type
        tab = '\t' * depth
        return tab + name + '\n' + tab + '(\n' + self.left_child.as_string(depth + 1) +\
               tab + '\t,\n' + self.right_child.as_string(depth + 1) + tab + ')\n'

    def as_line(self):
        return self.left_child.as_line() + ' ' + str(self.token.value) + ' ' + self.right_child.as_line()


class UnaryOp(AST):

    def __init__(self, child, token):
        AST.__init__(self, token)
        self.child = child
        self.op = token.type
        # self.const_leaves = child.const_leaves
        self.dtype = None

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        name = self.token.type
        tab = '\t' * depth
        return tab + name + '\n' + tab + '(\n' +\
               self.child.as_string(depth + 1) + tab + ')\n'

    def as_line(self):
        return str(self.token.value) + self.child.as_line()


class Decl(AST):

    def __init__(self, _id, dtype, pointer_level=0):
        AST.__init__(self, Token('DECL', dtype))
        self.dtype = dtype
        self.id = _id
        self.pointer_level = pointer_level

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        tab = '\t' * depth
        return tab + self.dtype + '*'*self.pointer_level + ' ' + self.id + '\n'


class DeclList(AST):

    def __init__(self, _vars):
        AST.__init__(self, Token('DECLLIST', 'dlist'))
        self.vars = _vars

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        ret_string = ''
        for v in self.vars:
            ret_string += v.as_string(depth)
        return ret_string


class Var(AST):

    def __init__(self, value, symt_entry=None):
        AST.__init__(self, Token('VAR', value))
        self.value = value
        self.entry = symt_entry
        self.dtype = None
        if symt_entry is not None:
            self.dtype = symt_entry['type']

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        name = self.value
        return '\t'*depth + 'VAR(%s)\n' % (name)

    def as_line(self):
        return str(self.token.value)


class Const(AST):

    def __init__(self, value, dtype=None):
        AST.__init__(self, Token('CONST', value), True)
        self.dtype = dtype

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        name = self.token.value
        return '\t'*depth + 'CONST(%s)\n' % (name)

    def as_line(self):
        return str(self.token.value)


class If(AST):

    def __init__(self, cond, body, else_body):
        '''
        Args:
            cond (AST): ast of logical condition
            body (list of ASTs): asts of body statements
            else_body (AST): ast of else part
        '''
        AST.__init__(self, Token('IF', 'if'))
        self.cond = cond
        self.body = body

        if else_body is None:
            else_body = []

        self.else_body = else_body

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        name = 'IF'
        tab = '\t' * depth

        body_string = tab + name + '\n' + tab + '(\n' + self.cond.as_string(depth + 1) + tab + '\t,\n'

        for stmt in self.body:
            body_string += stmt.as_string(depth + 1)

        if len(self.else_body) > 0:
            body_string += tab + '\t,\n'

        for stmt in self.else_body:
            body_string += stmt.as_string(depth + 1)

        return body_string + tab + ')\n'


class While(AST):

    def __init__(self, cond, body):
        '''
        Args:
            cond (AST): ast of logical condition
            body (list of ASTs): asts of body statements
        '''
        AST.__init__(self, Token('WHILE', 'while'))
        self.cond = cond
        self.body = body

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        name = 'WHILE'
        tab = '\t' * depth

        body_string = tab + name + '\n' + tab + '(\n' + self.cond.as_string(depth + 1) + tab + '\t,\n'

        for stmt in self.body:
            body_string += stmt.as_string(depth + 1)

        return body_string + tab + ')\n'


class Function(AST):

    def __init__(self, ret_type, name, params, body):
        AST.__init__(self, Token('FUNC', name))
        self.name = name
        self.params = params
        self.ret_type = ret_type
        self.body = body
        self.has_def = True

        if self.body is None:
            self.body = []
            self.has_def = False

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        if not self.has_def:
            return ''

        signature = 'FUNCTION ' + str(self.name) + '\nPARAMS ('

        if len(self.params) > 0:
            for i in range(len(self.params) - 1):
                signature += str(self.params[i]) + ', '
            signature += str(self.params[len(self.params) - 1])

        signature += ')\nRETURNS ' + '*'*self.ret_type[1] + self.ret_type[0]


        tab = '\t' * depth

        body_string = tab + signature + '\n'
        for stmt in self.body:
            body_string += stmt.as_string(depth + 1)

        return body_string + '\n'


class Param(AST):

    def __init__(self, _id, dtype, pointer_level=0):
        AST.__init__(self, Token('PARAM', dtype))
        self.dtype = dtype
        self.id = _id
        self.pointer_level = pointer_level

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        tab = '\t' * depth
        return tab + self.dtype + '*'*self.pointer_level + ' ' + (self.id if self.id is not None else '')


class Block(AST):

    def __init__(self, ast_list):
        AST.__init__(self, Token('BLOCK', 'block'))
        self.asts = ast_list

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        name = 'BLOCK'
        tab = '\t' * depth

        body_string = tab + name + '\n' + tab + '(\n'

        for ast in self.asts:
            body_string += ast.as_string(depth + 1)

        return body_string + tab + ')\n'


class FunctionCall(AST):

    def __init__(self, _id, actual_params):
        """
        Args:
            _id (str)
            actual_params (list of asts)
        """
        AST.__init__(self, Token('FUNC_CALL', _id))
        self.id = _id
        self.actual_params = actual_params
        self.dtype = None

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        tab = '\t' * depth
        body_string = tab + 'CALL ' + self.id + '(\n'
        for i, p in enumerate(self.actual_params):
            body_string += p.as_string(depth + 1)
            if i != len(self.actual_params) - 1:
                body_string += tab + '\t,\n'

        body_string += tab + ')\n'
        return body_string

    def as_line(self):
        line_string = self.id + '('
        n = len(self.actual_params)
        if n > 0:
            for p in self.actual_params[:-1]:
                line_string += p.as_line() + ', '
            line_string += self.actual_params[n - 1].as_line()
        line_string += ')'
        return line_string


class ReturnStmt(AST):

    def __init__(self, expression):
        '''
        Args:
            expression (AST) - ast of return expression
        '''
        AST.__init__(self, Token('RETURN', ''))
        self.expression = expression

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        # tab = '\t' * depth
        body_string = 'RETURN\n(\n'
        if self.expression is not None:
            body_string += self.expression.as_string(depth)
        return body_string + ')\n'


if __name__ == '__main__':
    t1 = Token('PLUS', '+')
    t2 = Token('VAR', 'a')
    t3 = Token('VAR', 'b')
    t4 = Token('DEREF', '*')
    t5 = Token('CONST', '5')

    tree = BinOp(UnaryOp(BinOp(Var(t2), Var(t3), t1), t4), Const(t5), t1)
    print(tree)