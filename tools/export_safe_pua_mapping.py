#!/usr/bin/env python3
"""สร้าง metadata PUA ที่ปลอด dialogue จาก source-of-truth local แบบ read-only."""
from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "work/new_subtitle_switch/pua_dictionary"
OUT = ROOT / "data"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    """Export only machine-rule fields; never copy source samples, IDs, or corpus text."""
    OUT.mkdir(exist_ok=True)
    simple = read_csv(SOURCE / "pua_mapping.csv")
    safe_simple = []
    for row in simple:
        status = row.get("status", "").upper()
        # Keep proven rules and explicit unknown state only; no review corpus is exported.
        if status not in {"VERIFIED", "UNMAPPED"}:
            continue
        replacement = row.get("replacement", "") if status == "VERIFIED" else ""
        safe_simple.append({
            "codepoint": row["codepoint"],
            "replacement": replacement,
            "status": status,
            "rule_type": "SIMPLE",
            "notes_safe": "human-reviewed" if status == "VERIFIED" else "unmapped; human review required",
        })
    safe_simple.sort(key=lambda row: int(row["codepoint"][2:], 16))
    with (OUT / "pua_mapping.safe.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["codepoint", "replacement", "status", "rule_type", "notes_safe"])
        writer.writeheader(); writer.writerows(safe_simple)

    clusters = read_csv(SOURCE / "pua_cluster_mapping.csv")
    safe_clusters = [{
        "input_codepoints": row["source_codepoints"],
        "output_sequence": row["replacement"],
        "status": row["status"].upper(),
        "rule_type": "CLUSTER",
        "notes_safe": "human-reviewed" if row["status"].upper() == "VERIFIED" else "candidate; human review required",
    } for row in clusters]
    with (OUT / "pua_cluster_mapping.safe.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["input_codepoints", "output_sequence", "status", "rule_type", "notes_safe"])
        writer.writeheader(); writer.writerows(safe_clusters)
    print(f"simple={len(safe_simple)}; verified={sum(r['status'] == 'VERIFIED' for r in safe_simple)}; clusters={len(safe_clusters)}")


if __name__ == "__main__":
    main()
