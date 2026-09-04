#!/usr/bin/env python3
"""Read-only exhaustive context validation for two proposed Thai PUA mappings."""

from __future__ import annotations

import argparse
import csv
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


TARGETS = {
    "U+F1B1": {"char": "\uf1b1", "candidate": "ด้"},
    "U+F24A": {"char": "\uf24a", "candidate": "ร์"},
}
# This is the already user-confirmed opening-local pair; it is not a global proof.
OPENING_SELF_ID = "TRIAL_01_MS06_X07_WD_0010_N_NNN_0010"


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def source_index(path: Path):
    if not path.exists():
        return {}
    return {r["self_id"]: r.get("text", "") for r in read_csv(path)}


def cp_name(ch: str) -> str:
    return f"U+{ord(ch):04X}" if ch else "<START/END>"


def category(ch: str) -> str:
    return unicodedata.category(ch) if ch else "<START/END>"


def local(text: str, pos: int, width: int = 18) -> tuple[str, str, str]:
    return text[max(0, pos - width):pos], text[max(0, pos - width):min(len(text), pos + 1 + width)], text[pos + 1:min(len(text), pos + 1 + width)]


def clean_context(text: str) -> str:
    return text.replace("\r", "\\r").replace("\n", "\\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="work/full_game_text_index/thai_text_raw_index.csv")
    ap.add_argument("--out-dir", default="work/new_subtitle_switch/pua_dictionary")
    ap.add_argument("--source-index-dir", default="work/new_subtitle_switch/pua_dictionary/source_indexes")
    args = ap.parse_args()

    corpus = read_csv(Path(args.corpus))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source_dir = Path(args.source_index_dir)
    sources = {
        "steam_text": source_index(source_dir / "steam_selfid_index.csv"),
        "update_text": source_index(source_dir / "update_selfid_index.csv"),
        "base_text": source_index(source_dir / "base_selfid_index.csv"),
    }
    occurrences = []
    grouped = {key: Counter() for key in TARGETS}
    rows_per_target = {key: set() for key in TARGETS}

    for row in corpus:
        text = row.get("ThaiTextRaw", "")
        self_id = row.get("SelfId", "")
        asset_path = row.get("DataTableAsset", "")
        for codepoint, target in TARGETS.items():
            start = 0
            occurrence_index = 0
            while True:
                pos = text.find(target["char"], start)
                if pos < 0:
                    break
                occurrence_index += 1
                previous, raw_context, following = local(text, pos)
                candidate_context = raw_context.replace(target["char"], target["candidate"])
                before = text[pos - 1] if pos else ""
                after = text[pos + 1] if pos + 1 < len(text) else ""
                pattern = f"{previous[-4:]}[{codepoint}]{following[:4]}"
                grouped[codepoint][pattern] += 1
                rows_per_target[codepoint].add((asset_path, self_id))
                # Only the user-confirmed opening pair is SUPPORTING. Other contexts
                # remain unresolved because PUA neighbours prevent semantic proof.
                if self_id == OPENING_SELF_ID:
                    classification = "SUPPORTING"
                    reason = "หลักฐาน runtime opening ที่ผู้ใช้ยืนยันแล้ว; ใช้สนับสนุนเฉพาะจุดนี้ ไม่ใช่การยืนยัน global mapping"
                else:
                    classification = "UNRESOLVED"
                    reason = "ยังไม่มีหลักฐาน semantic แบบ exact SelfId สำหรับการแทนค่านี้; ไม่ใช้ความคล้ายคำไทยเป็นหลักฐาน"
                item = {
                    "codepoint": codepoint,
                    "candidate": target["candidate"],
                    "self_id": self_id,
                    "asset_path": asset_path,
                    "raw_text": text,
                    "occurrence_index": occurrence_index,
                    "character_offset": pos,
                    "raw_context": clean_context(raw_context),
                    "candidate_context": clean_context(candidate_context),
                    "previous_context": clean_context(previous),
                    "next_context": clean_context(following),
                    "previous_visible_character": before,
                    "next_visible_character": after,
                    "previous_unicode_category": category(before),
                    "next_unicode_category": category(after),
                    "repeated_local_sequence": clean_context(pattern),
                    "position_in_string": "START" if pos == 0 else "END" if pos == len(text) - 1 else "MIDDLE",
                    "markup_adjacency": "YES" if before in "<>[]{}" or after in "<>[]{}" else "NO",
                    "classification": classification,
                    "reason": reason,
                    **{name: mapping.get(self_id, "") for name, mapping in sources.items()},
                }
                occurrences.append(item)
                start = pos + 1

    occurrence_fields = [
        "codepoint", "candidate", "self_id", "asset_path", "raw_text", "occurrence_index", "character_offset",
        "raw_context", "candidate_context", "previous_context", "next_context", "previous_visible_character",
        "next_visible_character", "previous_unicode_category", "next_unicode_category", "repeated_local_sequence",
        "position_in_string", "markup_adjacency", "classification", "reason", "steam_text", "update_text", "base_text",
    ]
    with (out_dir / "exhaustive_validation.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=occurrence_fields)
        w.writeheader(); w.writerows(occurrences)

    # Build ranked pattern summaries and a concise human review queue.
    pattern_rows, review_rows = [], []
    for codepoint, target in TARGETS.items():
        target_occurrences = [x for x in occurrences if x["codepoint"] == codepoint]
        by_pattern = defaultdict(list)
        for item in target_occurrences:
            by_pattern[item["repeated_local_sequence"]].append(item)
        ranked = sorted(by_pattern.items(), key=lambda kv: (-len(kv[1]), kv[0]))
        for rank, (pattern, items) in enumerate(ranked, 1):
            sample = items[0]
            pattern_rows.append({
                "codepoint": codepoint, "candidate": target["candidate"], "rank": rank,
                "pattern": pattern, "pattern_count": len(items), "representative_self_id": sample["self_id"],
                "representative_asset_path": sample["asset_path"], "raw_context": sample["raw_context"],
                "candidate_context": sample["candidate_context"], "steam_text": sample["steam_text"],
                "update_text": sample["update_text"], "base_text": sample["base_text"],
            })
        supporting = [x for x in target_occurrences if x["classification"] == "SUPPORTING"][:20]
        for item in supporting:
            review_rows.append({
                "codepoint": codepoint, "candidate": target["candidate"], "evidence_type": "SUPPORTING",
                "pattern_count": grouped[codepoint][item["repeated_local_sequence"]], "self_id": item["self_id"],
                "old_target": item["raw_context"], "candidate_decoded": item["candidate_context"],
                "steam_thai": item["steam_text"], "update_english": item["update_text"], "base_english": item["base_text"],
                "reason": item["reason"],
            })
        # Show the ten most frequent non-supporting patterns, one exact SelfId each.
        for pattern, items in ranked[:10]:
            item = next((x for x in items if x["classification"] != "SUPPORTING"), items[0])
            review_rows.append({
                "codepoint": codepoint, "candidate": target["candidate"], "evidence_type": "UNRESOLVED_REPEATED_PATTERN",
                "pattern_count": len(items), "self_id": item["self_id"], "old_target": item["raw_context"],
                "candidate_decoded": item["candidate_context"], "steam_thai": item["steam_text"],
                "update_english": item["update_text"], "base_english": item["base_text"],
                "reason": "ตัวอย่าง context ที่เกิดซ้ำสำหรับตรวจคน; ไม่มีการเทียบอักขระข้ามคำแปล",
            })

    with (out_dir / "exhaustive_validation_patterns.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(pattern_rows[0]) if pattern_rows else ["codepoint"])
        w.writeheader(); w.writerows(pattern_rows)
    review_fields = ["codepoint", "candidate", "evidence_type", "pattern_count", "self_id", "old_target", "candidate_decoded", "steam_thai", "update_english", "base_english", "reason"]
    with (out_dir / "exhaustive_validation_review.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=review_fields)
        w.writeheader(); w.writerows(review_rows)

    # Hypothetical impact only; writes no mapping state.
    all_pua = sum(sum(0xF000 <= ord(c) <= 0xF8FF for c in r.get("ThaiTextRaw", "")) for r in corpus)
    target_chars = {v["char"]: v["candidate"] for v in TARGETS.values()}
    impact_rows = []
    for row in corpus:
        raw = row.get("ThaiTextRaw", "")
        hit_count = sum(raw.count(ch) for ch in target_chars)
        if not hit_count:
            continue
        after = raw
        for ch, replacement in target_chars.items():
            after = after.replace(ch, replacement)
        before_pua = sum(0xF000 <= ord(c) <= 0xF8FF for c in raw)
        after_pua = sum(0xF000 <= ord(c) <= 0xF8FF for c in after)
        impact_rows.append({"self_id": row.get("SelfId", ""), "asset_path": row.get("DataTableAsset", ""), "target_occurrences": hit_count, "pua_before": before_pua, "pua_after": after_pua, "raw_before": raw, "candidate_after": after})
    impact_rows.sort(key=lambda x: (-x["target_occurrences"], x["pua_after"], x["self_id"]))
    with (out_dir / "exhaustive_validation_impact_preview.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(impact_rows[0]) if impact_rows else ["self_id"])
        w.writeheader(); w.writerows(impact_rows[:20])

    summary = []
    for codepoint, target in TARGETS.items():
        items = [x for x in occurrences if x["codepoint"] == codepoint]
        c = Counter(x["classification"] for x in items)
        summary.append({"codepoint": codepoint, "candidate": target["candidate"], "occurrences": len(items), "rows": len(rows_per_target[codepoint]), **{k: c.get(k, 0) for k in ["SUPPORTING", "NEUTRAL", "SUSPICIOUS", "CONTRADICTING", "UNRESOLVED"]}})
    with (out_dir / "exhaustive_validation_summary.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = list(summary[0]); w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(summary)
    print(f"total_pua={all_pua}; target_occurrences={sum(x['occurrences'] for x in summary)}; review_rows={len(review_rows)}")
    for item in summary:
        print(f"{item['codepoint']}: occurrences={item['occurrences']}; rows={item['rows']}; supporting={item['SUPPORTING']}; unresolved={item['UNRESOLVED']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
