#!/usr/bin/env python3
"""Apply only the explicitly human-approved PUA replacement/status pairs."""

from __future__ import annotations

import csv
from pathlib import Path


APPROVED = {
    "U+F1B1": "ด้", "U+F24A": "ร์", "U+F196": "ว่", "U+F15C": "ป็",
    "U+F1B2": "ต้", "U+F1C8": "ห้", "U+F179": "ช่", "U+F1A5": "จ้",
    "U+F07C": "มี", "U+F022": "รั", "U+F468": "นี้", "U+F1C2": "ล้",
    "U+F2CA": "นั้", "U+F191": "ย่", "U+F142": "ก็", "U+F024": "ลั",
    "U+F26C": "ทำ", "U+F06F": "ดี", "U+F194": "ล่", "U+F050": "ริ",
    "U+F020": "มั", "U+F779": "ผู้", "U+F0DA": "รื", "U+F0DC": "ลื",
}


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "work/new_subtitle_switch/pua_dictionary/pua_mapping.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)
    before = {row["codepoint"]: (row.get("replacement", ""), row.get("status", "")) for row in rows}
    found = set()
    for row in rows:
        codepoint = row["codepoint"]
        if codepoint in APPROVED:
            row["replacement"] = APPROVED[codepoint]
            row["status"] = "VERIFIED"
            found.add(codepoint)
    missing = sorted(set(APPROVED) - found)
    if missing:
        raise RuntimeError(f"Missing approved codepoints: {missing}")
    # Guardrails required by the checkpoint.
    f438 = next(row for row in rows if row["codepoint"] == "U+F438")
    if f438.get("status") == "VERIFIED" or f438.get("replacement") not in {"", "-", "UNMAPPED"}:
        raise RuntimeError("U+F438 guard failed")
    changed = [row["codepoint"] for row in rows if before[row["codepoint"]] != (row.get("replacement", ""), row.get("status", ""))]
    if set(changed) != set(APPROVED):
        raise RuntimeError(f"Unexpected mapping edits: {sorted(set(changed) - set(APPROVED))}")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    print(f"CHECKPOINT_APPLIED: {len(changed)} verified mappings; U+F438 remains {f438.get('status')}")


if __name__ == "__main__":
    main()
