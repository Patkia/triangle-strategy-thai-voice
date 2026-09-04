#!/usr/bin/env python3
"""Mechanical checkpoint: persist 27 approved simple mappings and 2 cluster candidates."""
from __future__ import annotations
import csv
from pathlib import Path

NEW = {
    "U+F131": "พู", "U+F5B2": "มื่", "U+F107": "ยุ", "U+F173": "ค่",
    "U+F027": "ศั", "U+F29C": "นั้", "U+F23B": "ด์", "U+F249": "ย์",
    "U+F016": "ทั", "U+F1BE": "ม้", "U+F199": "ส่", "U+F072": "ที",
    "U+F1B7": "บ้", "U+F01F": "ภั", "U+F22B": "ค์", "U+F136": "รู",
    "U+F35D": "ยิ่", "U+F2D4": "รั้", "U+F01D": "พั", "U+F013": "ดั",
    "U+F787": "สู้", "U+F04E": "มิ", "U+F1B4": "ท้", "U+F04F": "ยิ",
    "U+F0FA": "ตุ", "U+F164": "ร็", "U+F1A1": "ค้",
}
CLUSTERS = {
    "U+F26E U+0E32": ("\uf26eา", "นำ"),
    "U+F25D U+0E32": ("\uf25dา", "จำ"),
}

def main() -> None:
    root = Path(__file__).resolve().parents[1]
    map_path = root / "work/new_subtitle_switch/pua_dictionary/pua_mapping.csv"
    with map_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f); fields = reader.fieldnames or []; rows = list(reader)
    before = {r["codepoint"]: (r.get("replacement", ""), r.get("status", "")) for r in rows}
    found = set()
    for row in rows:
        if row["codepoint"] in NEW:
            row["replacement"] = NEW[row["codepoint"]]; row["status"] = "VERIFIED"
            row["notes"] = "human reviewed; checkpoint round 4"; found.add(row["codepoint"])
    if found != set(NEW): raise RuntimeError(f"missing simple mappings: {sorted(set(NEW)-found)}")
    f438 = next(r for r in rows if r["codepoint"] == "U+F438")
    if f438.get("status", "").upper() == "VERIFIED" or f438.get("replacement", "-") not in {"", "-", "UNMAPPED"}:
        raise RuntimeError("U+F438 guard failed")
    changed = {r["codepoint"] for r in rows if before[r["codepoint"]] != (r.get("replacement", ""), r.get("status", ""))}
    if changed != set(NEW): raise RuntimeError(f"unexpected simple edits: {sorted(changed-set(NEW))}")
    with map_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)

    cluster_path = root / "work/new_subtitle_switch/pua_dictionary/pua_cluster_mapping.csv"
    with cluster_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f); cfields = reader.fieldnames or []; crows = list(reader)
    existing = {r["source_codepoints"] for r in crows}
    for codepoints, (sequence, replacement) in CLUSTERS.items():
        if codepoints not in existing:
            crows.append({"source_sequence": sequence, "source_codepoints": codepoints, "replacement": replacement,
                          "status": "CLUSTER_CANDIDATE", "evidence": "human review checkpoint; candidate only",
                          "notes": "ห้ามรวมกับ simple mapping และ decoder ปกติไม่ consume"})
    with cluster_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cfields); writer.writeheader(); writer.writerows(crows)
    print(f"ROUND4_APPLIED={len(changed)}; clusters_present={len(CLUSTERS)}; F438={f438.get('status')}")

if __name__ == "__main__": main()
