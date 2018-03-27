from ast import *


class CFGNode(object):

    def __init__(self, _id, body, temp_start, logical=False, end=False):
        self.id = _id
        self.body = body
        self.logical = logical
        self.end = end

        if self.logical:
            self.goto_t = None
            self.goto_f = None
        else:
            self.goto = None

        self.temp_start = temp_start
        self.temp_count = 0
        self.temp_body = []

        self.process_body()
        self.body = self.temp_body

        self.parents = []

    def process_body(self):
        for ast in self.body:
            self.split_expr(ast)

    def split_expr(self, expr_ast):
        if not isinstance(expr_ast, (BinOp, UnaryOp)):
            return expr_ast

        if isinstance(expr_ast, BinOp):
            tl = self.split_expr(expr_ast.left_child)
            tr = self.split_expr(expr_ast.right_child)

            if expr_ast.token.type == 'ASGN':
                self.temp_body.append(BinOp(tl, tr, expr_ast.token))
                return None

            temp_var = Var('t' + str(self.temp_count + self.temp_start))
            self.temp_count += 1
            self.temp_body.append(BinOp(temp_var, BinOp(tl, tr, expr_ast.token), Token('ASGN', '=')))
            return temp_var

        elif isinstance(expr_ast, UnaryOp):
            # if expr_ast.token.type != 'DEREF':
            #     t = self.split_expr(expr_ast.child)
            #     temp_var = Var('t' + str(self.temp_count + self.temp_start))
            #     self.temp_count += 1
            #     self.temp_body.append(BinOp(temp_var, UnaryOp(t, expr_ast.token), Token('ASGN', '=')))
            #     return temp_var
            # else:
            t = self.split_expr(expr_ast.child)
            return UnaryOp(t, expr_ast.token)

    def __repr__(self):
        string = '<bb ' + str(self.id + 1) + '>\n'

        if self.end:
            string += 'End'
            return string

        for ast in self.body:
            string += ast.as_line() + '\n'

        if self.logical and self.goto_t and self.goto_f:
            string += 'if(t' + str(self.temp_start + self.temp_count - 1) + ') goto <bb ' + str(self.goto_t + 1) + '>\n'
            string += 'else goto <bb ' + str(self.goto_f + 1) + '>\n'
        elif self.goto:
            string += 'goto <bb ' + str(self.goto + 1) + '>\n'

        return string


class CFG(object):

    def __init__(self, asts):
        """
        Args:
            asts (list of AST objs):
        """
        self.asts = asts
        self.node_count = 0
        self.nodes = []
        self.temp_count = 0

        self.create_nodes(self.asts)
        end_node = CFGNode(self.node_count, [], self.temp_count, end=True)
        self.nodes.append(end_node)
        self.node_count += 1

        self.clean_up()

    def addNode(self, node):
        self.node_count += 1
        self.temp_count += node.temp_count
        self.nodes.append(node)

    def create_nodes(self, ast_list):

        n = len(ast_list)
        i = 0

        while (i < n):
            j = i
            while j < n and ast_list[j].token.type == 'ASGN':
                j += 1

            if i != j:
                node = CFGNode(self.node_count, list(ast_list[i:j]), self.temp_count)
                self.addNode(node)
                node.goto = self.node_count

            if j < n:
                if isinstance(ast_list[j], If):
                    self.create_if_node(ast_list[j])
                    j += 1
                elif isinstance(ast_list[j], While):
                    self.create_while_node(ast_list[j])
                    j += 1
                else:
                    j += 1

            i = j

        # create a blank CFG node
        node = CFGNode(self.node_count, [], self.temp_count)
        self.addNode(node)
        node.goto = self.node_count

    def create_if_node(self, ast):

        assert isinstance(ast, If)

        cond_node = CFGNode(self.node_count, [ast.cond], self.temp_count, True)
        self.addNode(cond_node)

        cond_node.goto_t = self.node_count
        self.create_nodes(ast.body)
        last_if_node = self.nodes[self.node_count - 1]

        cond_node.goto_f = self.node_count
        self.create_nodes(ast.else_body)
        last_else_node = self.nodes[self.node_count - 1]

        assert not last_if_node.logical
        assert not last_else_node.logical

        last_if_node.goto = self.node_count
        last_else_node.goto = self.node_count

    def create_while_node(self, ast):

        assert isinstance(ast, While)

        cond_node = CFGNode(self.node_count, [ast.cond], self.temp_count, True)
        self.addNode(cond_node)

        cond_node.goto_t = self.node_count
        self.create_nodes(ast.body)
        last_node = self.nodes[self.node_count - 1]
        cond_node.goto_f = self.node_count

        assert not last_node.logical

        last_node.goto = cond_node.id

    def create_function_node(self, ast):

        assert isinstance(ast, Function)



    def clean_up(self):
        '''removes blank nodes'''
        for node in self.nodes:
            if node.logical:
                if node.goto_t is not None:
                    self.nodes[node.goto_t].parents.append((node.id, 1))
                if node.goto_f is not None:
                    self.nodes[node.goto_f].parents.append((node.id, 2))
            else:
                if node.goto is not None:
                    self.nodes[node.goto].parents.append((node.id, 0))

        num_proper_nodes = 0

        # find empty nodes, redirect parents
        for node in self.nodes:
            if not node.body and not node.end:
                for p in node.parents:
                    if p[1] == 0:
                        self.nodes[p[0]].goto = node.goto
                    elif p[1] == 1:
                        self.nodes[p[0]].goto_t = node.goto
                    elif p[1] == 2:
                        self.nodes[p[0]].goto_f = node.goto

                if node.goto is not None:
                    self.nodes[node.goto].parents += node.parents
            else:
                num_proper_nodes += 1

        # rename node ids, update gotos
        for index, node in enumerate(self.nodes[::-1]):
            if node.body or node.end:
                node.id = num_proper_nodes - 1
                num_proper_nodes -= 1

                for p in node.parents:
                    if p[1] == 0:
                        self.nodes[p[0]].goto = node.id
                    elif p[1] == 1:
                        self.nodes[p[0]].goto_t = node.id
                    elif p[1] == 2:
                        self.nodes[p[0]].goto_f = node.id

        # remove blank nodes
        self.nodes = [x for x in self.nodes if x.body or x.end]
        self.node_count = len(self.nodes)


    def __repr__(self):

        string = ''

        for node in self.nodes:
            string += '\n' + str(node)

        return string
