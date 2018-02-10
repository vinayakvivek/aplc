#!/usr/bin/python3

import sys
from parser import APLParser
import os

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print('Invalid arguments!')
        sys.exit(-1)

    data = None
    data_file = sys.argv[1]
    with open(data_file, 'r') as file:
        data = file.read()

    dirname = os.path.dirname(data_file)
    basename = os.path.basename(data_file)

    out_file = os.path.join(dirname, 'Parser_ast_' + basename + '.txt')
    with open(out_file, 'w') as file:
        parser = APLParser(file)
        parser.parse(data)

    print('Successfully Parsed')