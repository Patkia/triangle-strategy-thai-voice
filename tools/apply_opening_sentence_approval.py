#!/usr/bin/env python3
"""Mechanical persist of the two human-approved opening mappings only."""
import csv
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    base = root / "work/new_subtitle_switch/pua_dictionary"
    p = base / "pua_mapping.csv"
    with p.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f); fields = reader.fieldnames or []; rows = list(reader)
    before = {r["codepoint"]: (r.get("replacement", ""), r.get("status", "")) for r in rows}
    row = next(r for r in rows if r["codepoint"] == "U+F082")
    row["replacement"] = "วี"; row["status"] = "VERIFIED"; row["notes"] = "human-reviewed opening sentence POC"
    f438 = next(r for r in rows if r["codepoint"] == "U+F438")
    if f438["status"] == "VERIFIED" or f438["replacement"] not in {"", "-", "UNMAPPED"}: raise RuntimeError("F438 guard failed")
    changed = {r["codepoint"] for r in rows if before[r["codepoint"]] != (r.get("replacement", ""), r.get("status", ""))}
    if changed != {"U+F082"}: raise RuntimeError(f"unexpected simple changes: {changed}")
    with p.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)

    cp = base / "pua_cluster_mapping.csv"
    with cp.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f); cfields = reader.fieldnames or []; crows = list(reader)
    target = next((r for r in crows if r["source_codepoints"] == "U+F282 U+0E32"), None)
    if target is None: raise RuntimeError("opening cluster missing")
    target["replacement"] = "อำ"; target["status"] = "VERIFIED"; target["notes"] = "human-reviewed opening sentence POC; cluster-aware codec consumes U+F282 U+0E32 together"
    for r in crows:
        if r["source_codepoints"] in {"U+F26E U+0E32", "U+F25D U+0E32"} and r["status"] != "CLUSTER_CANDIDATE":
            raise RuntimeError(f"candidate cluster changed: {r['source_codepoints']}")
    with cp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=cfields); writer.writeheader(); writer.writerows(crows)
    print("OPENING_APPROVAL_APPLIED=U+F082,U+F282+U+0E32; F438=UNMAPPED; other clusters preserved")

if __name__ == "__main__": main()
