from collections import OrderedDict


TYPE_SIZES = {
    'int': 4,
    'float': 8,
    'pointer': 4,
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

        self.symbols[name] = {
            'type': 'function',
            'ret_type': ret_type,
            'tableptr': new_table,
        }

    def enterblock(self, name, new_table):
        self.symbols[name] = {
            'type': 'block',
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

    def look_up(self, name):
        if name in self.symbols:
            return self.symbols[name]

        if self.parent is not None:
            return self.parent.look_up(name)

        return None


def mktable(curr_symtable, name):
    st = SymbolTable(curr_symtable, name)
    return st


def get_width(_type):
    '''type <- tuple (<basetype>, <pointer_level>)'''
    p_level = _type[1]
    width = TYPE_SIZES[_type[0]] if p_level == 0 else TYPE_SIZES['pointer']
    return width


def print_procedures(symtable, file):
    file.write('Procedure table :-\n')
    file.write('-----------------------------------------------------------------\n')
    file.write('Name\t\t|\tReturn Type  |  Parameter List\n')

    for k, v in symtable.symbols.items():
        if v['type'] == 'function':
            if k == 'main':
                continue
            file.write(k + '\t\t|\t')
            ret_type = v['ret_type']
            file.write(ret_type[0] + '*'*ret_type[1] + '\t\t|\t')
            table = v['tableptr']
            num_params = table.num_params
            params = []
            for pk, pv in table.symbols.items():
                if num_params == 0:
                    break
                params.append(pv['type'][0] + ' ' + '*' * pv['type'][1] + pk)
                num_params -= 1

            param_string = ''
            num_params = table.num_params

            if num_params > 1:
                for i in range(num_params - 1):
                    param_string += params[i] + ', '
            if num_params > 0:
                param_string += params[num_params - 1]

            file.write(param_string + '\n')

    file.write('-----------------------------------------------------------------\n')


def print_variables_recursive(symtable, scope, file):
    for k, v in symtable.symbols.items():
        if v['type'] in ('function', 'block'):
            print_variables_recursive(v['tableptr'], scope + [k], file)
        else:
            file.write(k + '\t\t|\t')
            if len(scope) > 1:
                file.write('procedure ' + scope[1] + '\t|\t')
            else:
                file.write('global\t\t|\t')
            file.write(v['type'][0] + '\t   |\t' + '*' * v['type'][1] + '\n')


def print_variables(symtable, file):
    file.write('''Variable table :- \n-----------------------------------------------------------------
Name\t|\tScope\t\t|\tBase Type  |  Derived Type
-----------------------------------------------------------------\n''')
    print_variables_recursive(symtable, ['global'], file)
    file.write('''-----------------------------------------------------------------
-----------------------------------------------------------------\n''')


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
