from enum import Enum
from collections import OrderedDict


class Type(object):

    size = {
        'int': 4,
        'float': 4,
        'to_set': 0,
    }

    def __init__(self, _type, pointer_level):
        print(Type.size.keys())
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
        type_string += ' (' + str(self.size) + ')'
        return type_string


class SymbolTable(object):

    def __init__(self, parent=None):
        print('creating symtable..')

        self.parent = parent

        # items <- dict with ids as keys
        self.items = OrderedDict()
        self.next_offset = 0

    def add_var(self, _id, _type):
        """
        Args:
            _id (string)
            _type (Type)
        """
        if _id in self.items.keys():
            print('multiple declarations of %s.' % (_id))
            return

        print('adding variable %s to symtable.' % (_id))

        item = {
            'type': _type,
            'offset': self.next_offset
        }

        self.next_offset += _type.size
        self.items[_id] = item

    def add_function(self, _id, ret_type, args, is_proto=False):
        """
        Args:
            _id (string)
            ret_type (Type)
            args (list of tuples (<id>, <type>))
        """
        if _id in self.items.keys():
            if self.items[_id]['has_def']:
                print('multiple definitions of function %s().' % (_id))
                return

        print('adding function %s to symtable.' % (_id))

        st = SymbolTable(self)
        item = {
            'type': 'function',
            'ret_type': ret_type,
            'has_def': not is_proto,
            'table_ptr': st,
        }
        self.items[_id] = item

        for arg in args:
            st.add_var(arg[0], arg[1])

        return st

        # TODO: take care of function protos after definition

    def _get_offset(self):
        return self.next_offset

    def __repr__(self):
        sym_string = ''
        for k, v in self.items.items():
            sym_string += str(k) + ': ' + str(v['type']) + '\n'
            if v['type'] == 'function':
                sym_string += '\n\n' + str(v['table_ptr']) + '\n'
        return sym_string
