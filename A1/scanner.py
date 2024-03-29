#!/usr/bin/python3

import sys
from parser import APLParser


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print('Invalid arguments!')
        sys.exit(-1)

    data = None
    with open(sys.argv[1], 'r') as file:
        data = file.read()

    parser = APLParser()
    parser.parse(data)

    print(parser.num_static_vars)
    print(parser.num_pointers)
    print(parser.num_assignments)
