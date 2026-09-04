#!/usr/bin/env python3
"""Add provenance notes only to the 29 round-3 human-approved rows."""
import csv
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_human_pua_checkpoint_round3 import NEW

root = Path(__file__).resolve().parents[1]
path = root / "work/new_subtitle_switch/pua_dictionary/pua_mapping.csv"
with path.open(encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f); fields = reader.fieldnames or []; rows = list(reader)
for row in rows:
    if row["codepoint"] in NEW:
        row["notes"] = "human reviewed; checkpoint round 3"
with path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
print("ROUND3_NOTES_UPDATED=29")
