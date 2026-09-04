#!/usr/bin/env python3
"""ใช้เฉพาะกฎที่ยืนยันในขอบเขต opening-local; ไม่ใช่ full-corpus decoder."""

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scope", choices=["opening-local"], required=True)
    args = parser.parse_args()

    with args.rules.open(encoding="utf-8", newline="") as f:
        rules = [r for r in csv.DictReader(f) if r["RuleStatus"] == "CONFIRMED_OPENING_LOCAL"]
    substitutions = sorted(
        ((r["RawCluster"], r["ExpectedUnicodeSequenceCandidate"]) for r in rules),
        key=lambda item: len(item[0]), reverse=True,
    )
    text = args.input.read_text(encoding="utf-8").rstrip("\r\n")
    for raw, expected in substitutions:
        text = text.replace(raw, expected)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
