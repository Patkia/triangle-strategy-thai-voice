#!/usr/bin/env python3
"""Apply only the third human-approved checkpoint; preserve prior VERIFIED rows."""
from __future__ import annotations
import csv
from pathlib import Path

NEW = {
    "U+F129": "ถู", "U+F170": "ก่", "U+F085": "สี", "U+F031": "คิ",
    "U+F018": "นั", "U+F16C": "ห็", "U+F114": "กู", "U+F5B4": "รื่",
    "U+F43A": "นี่", "U+F19A": "ห่", "U+F041": "ดิ", "U+F080": "ลี",
    "U+F27F": "สำ", "U+F007": "จั", "U+F1C4": "ว้", "U+F13A": "วู",
    "U+F1A7": "ช้", "U+F088": "อี", "U+F259": "คำ", "U+F065": "ชี",
    "U+F0E9": "คุ", "U+F24C": "ล์", "U+F509": "ขึ้", "U+F192": "ร่",
    "U+F2C8": "ทั้", "U+F02E": "กิ", "U+F019": "บั", "U+F127": "ดู",
    "U+F59B": "ชื่",
}

def main() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "work/new_subtitle_switch/pua_dictionary/pua_mapping.csv"
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f); fields = reader.fieldnames or []; rows = list(reader)
    before = {r["codepoint"]: (r.get("replacement", ""), r.get("status", "")) for r in rows}
    previous_verified = {k for k, v in before.items() if v[1].upper() == "VERIFIED"}
    if len(previous_verified) != 53:
        raise RuntimeError(f"expected 53 prior VERIFIED, found {len(previous_verified)}")
    found = set()
    for row in rows:
        if row["codepoint"] in NEW:
            row["replacement"] = NEW[row["codepoint"]]
            row["status"] = "VERIFIED"
            found.add(row["codepoint"])
    if found != set(NEW):
        raise RuntimeError(f"missing checkpoint entries: {sorted(set(NEW)-found)}")
    f438 = next(r for r in rows if r["codepoint"] == "U+F438")
    if f438.get("status", "").upper() == "VERIFIED" or f438.get("replacement", "-") not in {"", "-", "UNMAPPED"}:
        raise RuntimeError("U+F438 guard failed")
    changed = {r["codepoint"] for r in rows if before[r["codepoint"]] != (r.get("replacement", ""), r.get("status", ""))}
    if changed != set(NEW):
        raise RuntimeError(f"unexpected edits: {sorted(changed-set(NEW))}")
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    print(f"ROUND3_APPLIED={len(changed)}; previous_verified_preserved={len(previous_verified)}; F438={f438.get('status')}")

if __name__ == "__main__":
    main()
