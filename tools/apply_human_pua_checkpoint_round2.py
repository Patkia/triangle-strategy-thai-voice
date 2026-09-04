#!/usr/bin/env python3
"""Mechanical application of Human Review Checkpoint round 2 only."""
from __future__ import annotations
import csv
from pathlib import Path

NEW = {
    "U+F19F": "ข้", "U+F186": "ท่", "U+F190": "ม่", "U+F184": "ต่",
    "U+F000": "กั", "U+F751": "ยู่", "U+F188": "น่", "U+F0D8": "มื",
    "U+F026": "วั", "U+F365": "สิ่", "U+F042": "ติ", "U+F5AF": "พื่",
    "U+F0BB": "คื", "U+F1C0": "ร้", "U+F1B6": "น้", "U+F09F": "ถึ",
    "U+F07E": "รี", "U+F780": "รู้", "U+F029": "สั", "U+F10F": "สุ",
    "U+F256": "กำ", "U+F021": "ยั", "U+F054": "วิ", "U+F079": "พี",
    "U+F014": "ตั", "U+F23C": "ต์", "U+F057": "สิ", "U+F0FC": "ทุ",
    "U+F02C": "อั",
}

def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "work/new_subtitle_switch/pua_dictionary/pua_mapping.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f); fields = reader.fieldnames or []; rows = list(reader)
    before = {r["codepoint"]: (r.get("replacement", ""), r.get("status", "")) for r in rows}
    found = set()
    for row in rows:
        if row["codepoint"] in NEW:
            row["replacement"] = NEW[row["codepoint"]]
            row["status"] = "VERIFIED"
            found.add(row["codepoint"])
    if found != set(NEW):
        raise RuntimeError(f"checkpoint codepoints missing: {sorted(set(NEW)-found)}")
    f438 = next(r for r in rows if r["codepoint"] == "U+F438")
    if f438.get("status", "").upper() == "VERIFIED" or f438.get("replacement", "-") not in {"", "-", "UNMAPPED"}:
        raise RuntimeError("U+F438 guard failed")
    changed = {r["codepoint"] for r in rows if before[r["codepoint"]] != (r.get("replacement", ""), r.get("status", ""))}
    if changed != set(NEW):
        raise RuntimeError(f"unexpected changes: {sorted(changed-set(NEW))}")
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    print(f"ROUND2_APPLIED={len(changed)}; F438={f438.get('status')}")

if __name__ == "__main__":
    main()
