#!/usr/bin/env python3
"""คัดลอกและคลาย LZ4 segments จาก Nintendo Switch NSO โดยไม่แก้ไฟล์ต้นฉบับ."""

import argparse
import struct
from pathlib import Path


def lz4_decompress_block(source: bytes, expected_size: int) -> bytes:
    out = bytearray()
    pos = 0
    while pos < len(source):
        token = source[pos]
        pos += 1
        literal_length = token >> 4
        if literal_length == 15:
            while True:
                add = source[pos]
                pos += 1
                literal_length += add
                if add != 255:
                    break
        out += source[pos:pos + literal_length]
        pos += literal_length
        if pos == len(source):
            break
        offset = source[pos] | (source[pos + 1] << 8)
        pos += 2
        if offset == 0 or offset > len(out):
            raise ValueError('invalid LZ4 offset')
        match_length = token & 0x0F
        if match_length == 15:
            while True:
                add = source[pos]
                pos += 1
                match_length += add
                if add != 255:
                    break
        match_length += 4
        start = len(out) - offset
        for _ in range(match_length):
            out.append(out[start])
            start += 1
    if len(out) != expected_size:
        raise ValueError(f'LZ4 output size {len(out):#x}; expected {expected_size:#x}')
    return bytes(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('nso', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raw = args.nso.read_bytes()
    if raw[:4] != b'NSO0':
        raise SystemExit('input is not NSO0')
    flags = struct.unpack_from('<I', raw, 0x0C)[0]
    compressed_sizes = struct.unpack_from('<III', raw, 0x60)
    segments = []
    for index, name in enumerate(('text', 'rodata', 'data')):
        file_offset, memory_offset, memory_size = struct.unpack_from('<III', raw, 0x10 + index * 0x10)
        stored_size = compressed_sizes[index] if flags & (1 << index) else memory_size
        payload = raw[file_offset:file_offset + stored_size]
        decoded = lz4_decompress_block(payload, memory_size) if flags & (1 << index) else payload
        target = args.output / f'{name}.bin'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(decoded)
        segments.append((name, memory_offset, len(decoded), target))
    for name, memory_offset, size, target in segments:
        print(f'{name}\tva={memory_offset:#x}\tsize={size:#x}\t{target}')


if __name__ == '__main__':
    main()
