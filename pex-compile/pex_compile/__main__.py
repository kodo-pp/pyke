#!/usr/bin/env python3

from pex_compile import ast_to_pykebc
#from pex_compile import build_pex

import ast
import dis
from argparse import ArgumentParser


def parse_args():
    ap = ArgumentParser(description='Compile Python file to PEX format')
    ap.add_argument('--output', '-o', required=True, help='Created PEX file name')
    ap.add_argument('source', help='Input file name')
    return ap.parse_args()


def main():
    options = parse_args()
    with open(options.source, 'r') as f:
        code = f.read()
    tree = ast.parse(code)
    pyke_bytecode = ast_to_pykebc.translate(tree)
    print(pyke_bytecode.asm())
    #pex_file = build_pex.build(pyke_bytecode)
    #with open(options.output, 'wb') as f:
    #    f.write(pex_file.to_bytes())


if __name__ == '__main__':
    main()
