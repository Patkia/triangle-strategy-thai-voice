#!/usr/bin/env python3
"""Create a reproducible, read-only inventory for the CS02 English AWB.

The input AWB and extracted WAVs are never modified.  The only output is the
CSV path passed with --output (docs/cs02_voice_inventory.csv by default).
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def rel_or_default(value: str, default: str) -> Path:
    return (ROOT / (value or default)).resolve()


def read_metadata(cli: Path, awb: Path, index: int) -> dict:
    result = subprocess.run(
        [str(cli), "-m", "-I", "-s", str(index), str(awb)],
        check=True, capture_output=True, text=True, encoding="utf-8",
    )
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--awb", default="vgmstream-win64/CS02_EN.awb")
    parser.add_argument("--cli", default="vgmstream-win64/vgmstream-cli.exe")
    parser.add_argument("--output", default="docs/cs02_voice_inventory.csv")
    args = parser.parse_args()

    awb, cli, output = (rel_or_default(args.awb, args.awb),
                        rel_or_default(args.cli, args.cli),
                        rel_or_default(args.output, args.output))
    for item, label in ((awb, "AWB"), (cli, "vgmstream CLI")):
        if not item.is_file():
            parser.error(f"{label} not found: {item.relative_to(ROOT)}")

    first = read_metadata(cli, awb, 1)
    total = first["streamInfo"]["total"]
    rows = []
    for index in range(1, total + 1):
        info = first if index == 1 else read_metadata(cli, awb, index)
        samples = info["numberOfSamples"]
        rate = info["sampleRate"]
        rows.append({
            "stream_index": index,
            "filename": f"CS02_EN_{index}.wav",
            "duration_seconds": f"{samples / rate:.6f}",
            "sample_rate": rate,
            "channels": info["channels"],
            "codec": info["encoding"],
            "notes": "AWB index; no embedded stream name reported by vgmstream",
            "character": "",
            "dialogue_id": "",
            "scene": "CS02 (inferred from asset basename only)",
            "event": "",
            "source_asset": "Sound/Stream/VOICE/EN/CS02_EN.awb",
            "confidence": "format: high; dialogue mapping: unverified",
        })

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows: {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
