#!/usr/bin/env python3
"""สร้าง candidate-only PUA mapping และ sentence preview โดยไม่แก้ mapping จริง.

Candidate ที่ seed ไว้ต้องมาจากหลักฐาน runtime ที่ยืนยันก่อนหน้าเท่านั้น;
ข้อความ Steam/English ใช้แสดงให้มนุษย์ตรวจ ไม่ใช้ align/translate เพื่อเติม mapping.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

SEEDS = {
    "U+F1B1": {
        "candidate_replacement": "ด้", "candidate_type": "SEQUENCE", "confidence": "MEDIUM", "evidence_count": "1",
        "reason": "หลักฐาน opening-local ที่ผู้ใช้ยืนยันก่อนหน้า; ยังไม่มี independent global validation",
        "supporting_self_ids": "TRIAL_01_MS06_X07_WD_0010_N_NNN_0010", "conflicting_self_ids": "", "notes": "CANDIDATE ONLY; ไม่ promote เป็น VERIFIED",
    },
    "U+F24A": {
        "candidate_replacement": "ร์", "candidate_type": "SEQUENCE", "confidence": "MEDIUM", "evidence_count": "1",
        "reason": "หลักฐาน opening-local ที่ผู้ใช้ยืนยันก่อนหน้า; ยังไม่มี independent global validation",
        "supporting_self_ids": "TRIAL_01_MS06_X07_WD_0010_N_NNN_0010", "conflicting_self_ids": "", "notes": "CANDIDATE ONLY; ไม่ promote เป็น VERIFIED",
    },
}
CLUSTER_SEEDS = [{
    "source_sequence": chr(0xF282) + "า", "source_codepoints": "U+F282 U+0E32", "candidate_replacement": "อำ",
    "confidence": "MEDIUM", "evidence_count": "1", "reason": "หลักฐาน opening-local ที่ผู้ใช้ยืนยันก่อนหน้า", "supporting_self_ids": "TRIAL_01_MS06_X07_WD_0010_N_NNN_0010",
}]


def pua_count(text: str) -> int:
    return sum(0xE000 <= ord(ch) <= 0xF8FF for ch in text)


def load_unique(path: Path) -> dict[str, dict[str, str]]:
    found: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            found[row["self_id"]].append(row)
    return {key: rows[0] for key, rows in found.items() if len(rows) == 1}


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    directory = root / "work/new_subtitle_switch/pua_dictionary"
    review = list(csv.DictReader((directory / "review_queue.csv").open(encoding="utf-8-sig", newline="")))
    mapping_rows = []
    replacements = {}
    for row in review:
        seed = SEEDS.get(row["codepoint"])
        result = {"review_rank": row["review_rank"], "codepoint": row["codepoint"], "occurrence_count": row["occurrence_count"]}
        if seed:
            result.update(seed); replacements[chr(int(row["codepoint"][2:], 16))] = seed["candidate_replacement"]
        else:
            result.update({"candidate_replacement": "", "candidate_type": "UNKNOWN", "confidence": "UNKNOWN", "evidence_count": "0", "reason": "ไม่มีหลักฐาน independent เพียงพอสำหรับเสนอ replacement", "supporting_self_ids": "", "conflicting_self_ids": "", "notes": "ไม่เดาจาก Steam/English หรือ character alignment"})
        mapping_rows.append(result)
    mapping_columns = ["review_rank", "codepoint", "occurrence_count", "candidate_replacement", "candidate_type", "confidence", "evidence_count", "reason", "supporting_self_ids", "conflicting_self_ids", "notes"]
    with (directory / "candidate_mapping.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=mapping_columns); writer.writeheader(); writer.writerows(mapping_rows)
    cluster_columns = ["source_sequence", "source_codepoints", "candidate_replacement", "confidence", "evidence_count", "reason", "supporting_self_ids"]
    with (directory / "candidate_cluster_mapping.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cluster_columns); writer.writeheader(); writer.writerows(CLUSTER_SEEDS)

    sources = directory / "source_indexes"
    steam, update, base = (load_unique(sources / f"{name}_selfid_index.csv") for name in ("steam", "update", "base"))
    corpus = list(csv.DictReader((root / "work/full_game_text_index/thai_text_raw_index.csv").open(encoding="utf-8-sig", newline="")))
    candidates = []
    for row in corpus:
        raw = row["ThaiTextRaw"]
        used = [code for code in SEEDS if chr(int(code[2:], 16)) in raw]
        if not used or row["SelfId"] not in steam or row["SelfId"] not in update or row["SelfId"] not in base:
            continue
        decoded = "".join(replacements.get(ch, ch) for ch in raw)
        remaining = pua_count(decoded)
        marks = sum(0x0E31 <= ord(ch) <= 0x0E4E for ch in decoded)
        candidates.append({
            "self_id": row["SelfId"], "old_switch_raw": raw, "candidate_decoded": decoded, "remaining_pua_count": remaining,
            "candidate_mappings_used": "; ".join(f"{code}→{SEEDS[code]['candidate_replacement']}" for code in used),
            "steam_thai": steam[row["SelfId"]]["text"], "update_english": update[row["SelfId"]]["text"], "base_english": base[row["SelfId"]]["text"],
            "preview_confidence": "MEDIUM", "notes": f"structural only: Thai_mark_count={marks}; candidate PUA left={remaining}; cluster candidates not consumed",
            "_score": (-sum(raw.count(chr(int(code[2:], 16))) for code in used), remaining, row["SelfId"]),
        })
    candidates.sort(key=lambda row: row["_score"])
    previews, used_ids = [], set()
    for row in candidates:
        if row["self_id"] in used_ids:
            continue
        used_ids.add(row["self_id"]); row.pop("_score"); previews.append(row)
        if len(previews) == 30:
            break
    preview_columns = ["self_id", "old_switch_raw", "candidate_decoded", "remaining_pua_count", "candidate_mappings_used", "steam_thai", "update_english", "base_english", "preview_confidence", "notes"]
    with (directory / "candidate_sentence_preview.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=preview_columns); writer.writeheader(); writer.writerows(previews)
    blocks = []
    for row in previews[:10]:
        blocks.append("\n".join([
            "=" * 64, f"SELF ID\n{row['self_id']}", f"OLD SWITCH RAW\n{row['old_switch_raw']}",
            f"CANDIDATE DECODED\n{row['candidate_decoded']}", f"STEAM THAI\n{row['steam_thai']}",
            f"UPDATE ENGLISH\n{row['update_english']}", f"BASE ENGLISH\n{row['base_english']}",
            f"MAPPINGS USED\n{row['candidate_mappings_used']}", f"REMAINING PUA\n{row['remaining_pua_count']}", f"CONFIDENCE\n{row['preview_confidence']}",
        ]))
    (directory / "candidate_preview.txt").write_text("\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8")
    print(f"top30={len(review)} medium={len(replacements)} unknown={len(review)-len(replacements)} previews={len(previews)} fully_decoded={sum(row['remaining_pua_count'] == 0 for row in previews)}")


if __name__ == "__main__":
    main()
