#!/usr/bin/env python3
"""Exhaustive, non-promoting validation of U+F438 -> ที่."""
from __future__ import annotations
import csv
from collections import Counter
from pathlib import Path

TARGET = "\uf438"
CANDIDATE = "ที่"

def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def main():
    root = Path(__file__).resolve().parents[1]
    base = root / "work/new_subtitle_switch/pua_dictionary"
    corpus = rows(root / "work/full_game_text_index/thai_text_raw_index.csv")
    indexes = {}
    for name in ("steam", "update", "base"):
        p = base / "source_indexes" / f"{name}_selfid_index.csv"
        indexes[name] = {r["self_id"]: r.get("text", "") for r in rows(p)} if p.exists() else {}
    out = []
    patterns = Counter()
    for row in corpus:
        text = row.get("ThaiTextRaw", "")
        start = 0; idx = 0
        while True:
            pos = text.find(TARGET, start)
            if pos < 0: break
            idx += 1
            before = text[max(0, pos-24):pos]
            after = text[pos+1:min(len(text), pos+25)]
            raw_context = before + TARGET + after
            candidate_context = before + CANDIDATE + after
            pattern = before[-8:] + "[U+F438]" + after[:8]
            patterns[pattern] += 1
            # No automatic semantic claim is made: source translations are support
            # material, not character-alignment proof. Every occurrence remains ambiguous.
            out.append({
                "codepoint": "U+F438", "candidate": CANDIDATE, "asset_path": row.get("DataTableAsset", ""),
                "self_id": row.get("SelfId", ""), "occurrence_index": idx, "raw_text": text,
                "raw_context": raw_context.replace("\r", "\\r").replace("\n", "\\n"),
                "candidate_context": candidate_context.replace("\r", "\\r").replace("\n", "\\n"),
                "previous_context": before.replace("\r", "\\r").replace("\n", "\\n"),
                "next_context": after.replace("\r", "\\r").replace("\n", "\\n"),
                "steam_text": indexes["steam"].get(row.get("SelfId", ""), ""),
                "update_text": indexes["update"].get(row.get("SelfId", ""), ""),
                "base_text": indexes["base"].get(row.get("SelfId", ""), ""),
                "source_lookup": "FULL" if all(row.get("SelfId", "") in indexes[n] for n in indexes) else "PARTIAL_OR_MISSING",
                "classification": "AMBIGUOUS",
                "reason": "ยังไม่มีหลักฐาน semantic ที่แยกได้โดยไม่ align คำแปลหรือเดาความหมาย; ไม่ promote อัตโนมัติ",
            })
            start = pos + 1
    fields = list(out[0]) if out else ["codepoint"]
    with (base / "f438_candidate_exhaustive.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(out)
    # Human queue: most frequent contexts, with one representative SelfId each.
    seen = set(); review = []
    for item in sorted(out, key=lambda x: (x["raw_context"], x["self_id"])):
        key = item["raw_context"]
        if key in seen: continue
        seen.add(key)
        review.append({"evidence_type": "AMBIGUOUS", "pattern_count": patterns[item["previous_context"][-8:] + "[U+F438]" + item["next_context"][:8]], **item})
    review = sorted(review, key=lambda x: (-int(x["pattern_count"]), x["self_id"]))[:30]
    rf = ["evidence_type", "pattern_count"] + fields
    with (base / "f438_candidate_review.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rf); w.writeheader(); w.writerows(review)
    print(f"occurrences={len(out)}; compatible=0; contradictory=0; ambiguous={len(out)}; review_examples={len(review)}")

if __name__ == "__main__": main()
