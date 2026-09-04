#!/usr/bin/env python3
"""decode streams จาก AWB เป็น WAV ภายใต้ work โดยไม่แก้ AWB ต้นทาง."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vgmstream", required=True, type=Path)
    parser.add_argument("--awb", required=True, type=Path)
    parser.add_argument("--stream-count", required=True, type=int)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()

    if not args.vgmstream.is_file() or not args.awb.is_file() or args.stream_count < 1:
        print("ตรวจ path ของ vgmstream/AWB หรือจำนวน stream ไม่ผ่าน", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for index in range(1, args.stream_count + 1):
        output = args.output_dir / f"{args.prefix}__stream{index:03d}.wav"
        if output.is_file() and output.stat().st_size > 44:
            continue
        print(f"[{index}/{args.stream_count}] {output.name}", flush=True)
        result = subprocess.run(
            [str(args.vgmstream), "-s", str(index), "-o", str(output), str(args.awb)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(result.stderr or result.stdout, file=sys.stderr)
            return result.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
