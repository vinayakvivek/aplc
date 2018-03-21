from enum import Enum
from collections import OrderedDict
from ast import Decl, DeclList, Function, Block, If, While


class Type(object):

    size = {
        'int': 4,
        'float': 4,
        'void': 0,
        'to_set': 0,
    }

    def __init__(self, _type, pointer_level):
        assert _type in Type.size.keys()
        self.type = _type
        self.pointer_level = pointer_level
        self.size = Type.size[_type] if pointer_level == 0 else 8

    def set_type(self, _type):
        self.type = _type
        self.size = Type.size[_type] if self.pointer_level == 0 else 8

    def __repr__(self):
        type_string = str(self.type)
        for i in range(self.pointer_level):
            type_string += '*'
        # type_string += ' (' + str(self.size) + ')'
        return type_string

    def __eq__(self, other):
        if isinstance(other, Type):
            return (self.type == other.type and self.pointer_level == other.pointer_level)
        return False


class SymbolTable(object):

    table_list = []

    def __init__(self, name='global', _type=None, parent=None):
        # print('creating symtable..')

        self.parent = parent
        self.name = name
        self.type = _type

        # entries <- dict with ids as keys
        self.entries = OrderedDict()
        self.next_offset = 0
        self.num_blocks = 0
        self.id = len(SymbolTable.table_list)

        SymbolTable.table_list.append(self)

    def add_var(self, _id, _type):
        """
        Args:
            _id (string)
            _type (Type)
        """
        if _id in self.entries:
            print('multiple declarations of %s.' % (_id))
            return

        # print('adding variable %s to symtable.' % (_id))

        item = {
            'type': 'var',
            'dtype': _type,
            'offset': self.next_offset,
        }

        self.next_offset += _type.size
        self.entries[_id] = item

    def add_function(self, _id, ret_type, args, f_st, is_proto=False):
        """
        Args:
            _id (string)
            ret_type (Type)
            args (list of tuples (<id(str)>, <type(Type)>))
        """
        if _id in self.entries:
            if self.entries[_id]['has_def']:
                print('multiple definitions of function %s().' % (_id))
                return

        # print('adding function %s to symtable.' % (_id))

        item = {
            'type': 'function',
            'ret_type': ret_type,
            'params': args,
            'has_def': not is_proto,
            'table_ptr': f_st,
        }
        self.entries[_id] = item

        # return st

        # TODO: take care of function protos after definition

    def add_block(self, symtable):
        _id = 'block_' + str(self.num_blocks)
        self.num_blocks += 1

        self.entries[_id] = {
            'type': 'block',
            'table_ptr': symtable,
        }

    def _get_offset(self):
        return self.next_offset

    def __repr__(self):
        sym_string = '[' + str(self.id) + ', ' + self.name + ']\n'
        for k, v in self.entries.items():
            sym_string += str(k) + ': ' + str(v['type']) + '\n'
            # if v['type'] in ('function', 'block'):
            #     sym_string += '\n\n' + str(v['table_ptr']) + '\n'
        return sym_string

    def get_ret_type(self):
        if self.type != 'function':
            return None
        return self.parent.look_up(self.name)[0]['ret_type']

    def look_up(self, _id):
        if _id in self.entries:
            return (self.entries[_id], self.id)

        if self.parent is None:
            # print('key not found.')
            return None

        return self.parent.look_up(_id)


def print_symbol_tables():
    print('\n------------\n')
    for t in SymbolTable.table_list:
        print(t)
        print('------------\n')
    return

    print('Procedure table :-')
    print('------------------')
    print('Name\t\t|\tReturn Type  |  Parameter List')
    for t in SymbolTable.table_list:
        if t.type == 'function':
            entry = t.parent.look_up(t.name)[0]
            ret_type = entry['ret_type']
            params = entry['params']
            print(t.name + '\t\t|\t' + str(ret_type) + '\t|\t', end='')
            print(params)

    print('Variable table :- ')
    print('------------------')
    print('Name\t|\tScope\t\t|\tBase Type  |  Derived Type')
    # for t in SymbolTable.table_list:
    #     # scope =
    #     for k, e in t.entries.items():
    #         if e['type'] == 'var':
    #             print(k + '\t\t|\t', end='')


def parse_ast(ast, symtable):
    if isinstance(ast, DeclList):
        for v in ast.vars:
            symtable.add_var(v.id, Type(v.dtype, v.pointer_level))

    elif isinstance(ast, Function):
        entry = symtable.look_up(ast.name)
        entry = entry[0] if entry is not None else None
        f_symtable = SymbolTable(ast.name, 'function', symtable) if entry is None else entry['table_ptr']
        populate_function_symtable(ast, f_symtable, entry is None)

        symtable.add_function(ast.name, ast.ret_type, ast.params, f_symtable, not ast.has_def)

    elif isinstance(ast, Block):
        block_st = create_symtable('block-' + str(symtable.num_blocks), 'block', ast.asts, symtable)
        symtable.add_block(block_st)

    elif isinstance(ast, If):
        block_st = create_symtable('if-block-' + str(symtable.num_blocks), 'block', ast.body, symtable)
        symtable.add_block(block_st)
        block_st = create_symtable('else-block-' + str(symtable.num_blocks), 'block', ast.else_body, symtable)
        symtable.add_block(block_st)


def create_symtable(name, _type, ast_list, parent=None):

    curr_symtable = SymbolTable(name, _type, parent)

    for ast in ast_list:
        parse_ast(ast, curr_symtable)

    return curr_symtable


def populate_function_symtable(f_ast, symtable, is_new=False):

    if not is_new:
        if len(symtable.entries) != len(f_ast.params):
            print('signature mismatch [wrong number of params]')
            return

        # check if return type is same
        ret_type = symtable.get_ret_type()
        if f_ast.ret_type != ret_type:
            print('signature mismatch [different return types]')
            return

        p_index = 0
        for k, v in symtable.entries.items():
            t = v['dtype']
            p = f_ast.params[p_index]
            if t.type != p.dtype or t.pointer_level != p.pointer_level:
                print('signature mismatch with function prototype.')
                return
            p_index += 1

    symtable.entries.clear()

    for p in f_ast.params:
        symtable.add_var(p.id, Type(p.dtype, p.pointer_level))

    for ast in f_ast.body:
        parse_ast(ast, symtable)
