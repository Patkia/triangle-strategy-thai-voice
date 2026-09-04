#!/usr/bin/env python3
"""อ่าน Lua 5.1 bytecode แบบ read-only และแสดง call sites ที่มีชื่อระบุ."""

import argparse
import struct
from pathlib import Path


OPNAMES = [
    'MOVE', 'LOADK', 'LOADBOOL', 'LOADNIL', 'GETUPVAL', 'GETGLOBAL', 'GETTABLE',
    'SETGLOBAL', 'SETUPVAL', 'SETTABLE', 'NEWTABLE', 'SELF', 'ADD', 'SUB', 'MUL',
    'DIV', 'MOD', 'POW', 'UNM', 'NOT', 'LEN', 'CONCAT', 'JMP', 'EQ', 'LT', 'LE',
    'TEST', 'TESTSET', 'CALL', 'TAILCALL', 'RETURN', 'FORLOOP', 'FORPREP',
    'TFORLOOP', 'SETLIST', 'CLOSE', 'CLOSURE', 'VARARG'
]


class Reader:
    def __init__(self, data): self.data, self.pos = data, 0
    def take(self, n):
        value = self.data[self.pos:self.pos+n]
        self.pos += n
        return value
    def byte(self): return self.take(1)[0]
    def integer(self): return struct.unpack('<I', self.take(4))[0]
    def size_t(self): return struct.unpack('<Q', self.take(8))[0]
    def number(self): return struct.unpack('<d', self.take(8))[0]
    def string(self):
        size = self.size_t()
        if size == 0: return None
        return self.take(size - 1).decode('utf-8', errors='replace') + self.take(1).decode('latin1')


def read_proto(r):
    source = r.string()
    linedefined, lastline = r.integer(), r.integer()
    nups, nparams, vararg, maxstack = r.byte(), r.byte(), r.byte(), r.byte()
    code = [struct.unpack('<I', r.take(4))[0] for _ in range(r.integer())]
    constants = []
    for _ in range(r.integer()):
        kind = r.byte()
        if kind == 0: constants.append(None)
        elif kind == 1: constants.append(bool(r.byte()))
        elif kind == 3: constants.append(r.number())
        elif kind == 4: constants.append(r.string())
        else: raise ValueError(f'unknown Lua constant kind {kind}')
    protos = [read_proto(r) for _ in range(r.integer())]
    r.take(r.integer() * 4)  # line info
    for _ in range(r.integer()):
        r.string(); r.integer(); r.integer()
    r.take(r.integer() * 8)  # upvalue names
    return {'source': source, 'line': linedefined, 'lastline': lastline, 'params': nparams,
            'maxstack': maxstack, 'code': code, 'constants': constants, 'protos': protos}


def fields(ins):
    op = ins & 0x3f
    a = (ins >> 6) & 0xff
    c = (ins >> 14) & 0x1ff
    b = (ins >> 23) & 0x1ff
    bx = (ins >> 14) & 0x3ffff
    return op, a, b, c, bx


def const(proto, index):
    if 0 <= index < len(proto['constants']): return repr(proto['constants'][index])
    return f'K?{index}'


def describe(proto, prefix='main'):
    names = {}
    for pc, ins in enumerate(proto['code']):
        op, a, b, c, bx = fields(ins)
        opname = OPNAMES[op] if op < len(OPNAMES) else f'OP{op}'
        if opname == 'CLOSURE' and pc + 1 < len(proto['code']):
            nextop, na, nb, nc, nbx = fields(proto['code'][pc + 1])
            if nextop == 7:
                name = proto['constants'][nbx] if nbx < len(proto['constants']) else None
                if isinstance(name, str): names[bx] = name
    print(f'FUNCTION {prefix} lines={proto["line"]}-{proto["lastline"]} params={proto["params"]}')
    registers = {}
    for pc, ins in enumerate(proto['code']):
        op, a, b, c, bx = fields(ins)
        opname = OPNAMES[op] if op < len(OPNAMES) else f'OP{op}'
        if opname == 'LOADK': registers[a] = const(proto, bx)
        elif opname == 'GETGLOBAL': registers[a] = const(proto, bx)
        elif opname == 'GETTABLE': registers[a] = f'{registers.get(b, "R"+str(b))}[{registers.get(c, "R"+str(c))}]'
        elif opname == 'MOVE': registers[a] = registers.get(b, f'R{b}')
        elif opname == 'SELF':
            registers[a] = f'{registers.get(b, "R"+str(b))}[{registers.get(c, "R"+str(c))}]'
            registers[a+1] = registers.get(b, f'R{b}')
        elif opname in ('CALL', 'TAILCALL'):
            count = b - 1 if b else 0
            args = [registers.get(a+i, f'R{a+i}') for i in range(1, count+1)]
            fn = registers.get(a, f'R{a}')
            print(f'  PC {pc:04d}: {opname} {fn}({", ".join(args)})')
        elif opname == 'CLOSURE':
            registers[a] = f'<closure {names.get(bx, bx)}>'
    for i, child in enumerate(proto['protos']):
        describe(child, f'{prefix}.{names.get(i, "proto"+str(i))}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=Path)
    args = parser.parse_args()
    raw = args.file.read_bytes()
    if raw[:5] != b'\x1bLuaQ': raise SystemExit('not Lua 5.1 bytecode')
    r = Reader(raw[12:])
    proto = read_proto(r)
    describe(proto)


if __name__ == '__main__': main()
