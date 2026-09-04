#!/usr/bin/env python3
"""ประกอบ decoded NSO segments เป็น flat image ตาม virtual addresses สำหรับ Ghidra."""

from pathlib import Path
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('segments', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    layout = [('text.bin', 0x00000000), ('rodata.bin', 0x03FD6000), ('data.bin', 0x05F6B000)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('wb') as image:
        for name, address in layout:
            current = image.tell()
            if current > address:
                raise ValueError(f'{name} overlaps previous segment')
            image.write(b'\0' * (address - current))
            image.write((args.segments / name).read_bytes())
    print(f'{args.output}\t{args.output.stat().st_size:#x} bytes')


if __name__ == '__main__': main()
