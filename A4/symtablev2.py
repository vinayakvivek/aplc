from collections import OrderedDict


TYPE_SIZES = {
    'int': 4,
    'float': 4,
    'pointer': 8,
}


class SymbolTable(object):

    def __init__(self, parent, name):
        self.parent = parent
        self.size = 0
        self.symbols = OrderedDict()
        self.name = name

        # applicable for function symbol tables
        self.num_params = None

    def enter(self, name, _type, width):
        '''
        Args:
            name (str): id
            _type (tuple (base_type(str), pointer_level(int))),
            width (int): size of data type
            offset (int): current offset
        '''
        if name in self.symbols:
            print('redeclaration of variable %s.' % (name))
            return

        self.symbols[name] = {
            'type': _type,
            'width': width,
        }

    def enterfunc(self, name, new_table, ret_type):
        if name in self.symbols:
            entry = self.symbols[name]
            if entry['tableptr'] is not None:
                # curr entry is function not a prototype
                print('redefinition of function %s' % (name))
                return
            else:
                # check if prototype params match definition params
                if entry['ret_type'] != ret_type:
                    print('[function %s] return type mismatch with prototype.' % (name))
                    return

                # if len(entry['params']) != len(params):
                #     print('[function %s] parameter list mismatch with prototype.' % (name))
                #     return

                # for index, (p1, p2) in enumerate(zip(entry['params'], params)):
                #     if p1[1] != p2[1]:
                #         print('[function %s] param #%d type mismatch with prototype.' % (name, index))
                #         return

        self.symbols[name] = {
            'ret_type': ret_type,
            'tableptr': new_table,
        }

    def enterblock(self, name, new_table):
        self.symbols[name] = {
            'tableptr': new_table,
        }

    def addwidth(self, width):
        self.size = width

    def __repr__(self):
        return self.as_string(0)

    def as_string(self, depth=0):
        tab = '\t' * depth
        parent_name = self.parent.name if self.parent is not None else 'none'
        temp = '\n' + tab + 'table: ' + self.name + '\n' + tab + 'parent: ' + parent_name + '\n' + tab + '---\n'
        for k, v in self.symbols.items():
            temp += tab + str(k) + '\n'
            if 'tableptr' in v.keys():
                temp += v['tableptr'].as_string(depth + 1)
        return temp


def mktable(curr_symtable, name):
    st = SymbolTable(curr_symtable, name)
    return st


def get_width(_type):
    '''type <- tuple (<basetype>, <pointer_level>)'''
    p_level = _type[1]
    width = TYPE_SIZES[_type[0]] if p_level == 0 else TYPE_SIZES['pointer']
    return width


class Stack:
    def __init__(self):
        self.items = []

    def isEmpty(self):
        return self.items == []

    def push(self, item):
        self.items.append(item)

    def pop(self):
        if len(self.items) > 0:
            return self.items.pop()

        print('[error] pop from empty list.')
        return None

    def top(self):
        if len(self.items) > 0:
            return self.items[len(self.items)-1]

        print('[error] empty stack.')
        return None

    def updateTop(self, new_val):
        self.items[len(self.items) - 1] = new_val

    def size(self):
        return len(self.items)
