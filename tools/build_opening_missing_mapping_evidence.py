#!/usr/bin/env python3
"""Evidence-only review files for U+F082 -> วี and U+F282+า -> อำ."""
from __future__ import annotations
import csv
import json
from collections import Counter
from pathlib import Path

F082, F282 = "\uf082", "\uf282"
OPENING = "TRIAL_01_MS06_X07_WD_0010_N_NNN_0010"

def read(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))

def write(path: Path, rows: list[dict]):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["kind"]); w.writeheader(); w.writerows(rows)

def main():
    root = Path(__file__).resolve().parents[1]
    base = root / "work/new_subtitle_switch/pua_dictionary"
    mapping = read(base / "pua_mapping.csv")
    replacements = {chr(int(r["codepoint"][2:], 16)): r["replacement"] for r in mapping if r["status"] == "VERIFIED"}
    source_root = base / "opening_evidence_sources"
    source = {}
    for name in ("steam", "update", "base"):
        source[name] = {r["self_id"]: r["text"] for r in read(source_root / f"{name}_selfid_index.csv")}
    corpus = read(root / "work/full_game_text_index/thai_text_raw_index.csv")
    f082_rows, am_rows = [], []
    for row in corpus:
        raw, sid, asset = row["ThaiTextRaw"], row["SelfId"], row["DataTableAsset"]
        partial = "".join(replacements.get(c, c) for c in raw)
        for target, candidate, kind in ((F082, "วี", "I_CANDIDATE"),):
            offset = 0; occurrence = 0
            while (pos := raw.find(target, offset)) >= 0:
                occurrence += 1
                candidate_text = partial.replace(target, candidate)
                f082_rows.append({"kind": kind, "candidate": "U+F082 → วี", "asset_path": asset, "self_id": sid,
                    "occurrence_index": occurrence, "raw_context": raw[max(0,pos-28):pos+29],
                    "candidate_context": candidate_text[max(0,pos-28):pos+len(candidate)+28],
                    "classification": "SUPPORTING_EXACT_OPENING" if sid == OPENING else "AMBIGUOUS",
                    "reason": "opening runtime target ยืนยันตรง" if sid == OPENING else "ไม่มีหลักฐาน exact target สำหรับ context นี้; เก็บให้ human review",
                    "steam_thai": source["steam"].get(sid,""), "update_english": source["update"].get(sid,""), "base_english": source["base"].get(sid,"")})
                offset = pos + 1
        offset = 0; occurrence = 0
        sequence = F282 + "า"
        while (pos := raw.find(sequence, offset)) >= 0:
            occurrence += 1
            candidate_text = partial.replace(sequence, "อำ")
            am_rows.append({"kind": "AM_CLUSTER", "candidate": "U+F282 + U+0E32 → อำ", "asset_path": asset, "self_id": sid,
                "occurrence_index": occurrence, "raw_context": raw[max(0,pos-28):pos+30],
                "candidate_context": candidate_text[max(0,pos-28):pos+30],
                "classification": "SUPPORTING_EXACT_OPENING" if sid == OPENING else "STRUCTURAL_ONLY",
                "reason": "opening runtime target ยืนยันตรง" if sid == OPENING else "โครงสร้าง sequence ตรง candidate แต่ยังไม่มี human approval global",
                "steam_thai": source["steam"].get(sid,""), "update_english": source["update"].get(sid,""), "base_english": source["base"].get(sid,"")})
            offset = pos + len(sequence)
    # Distinct-asset review samples, leading with opening confirmation if present.
    review=[]
    for records in (f082_rows, am_rows):
        chosen=[]; assets=set()
        for r in sorted(records, key=lambda x: (0 if x['self_id']==OPENING else 1, x['asset_path'], x['self_id'])):
            if r['asset_path'] not in assets:
                chosen.append(r); assets.add(r['asset_path'])
            if len(chosen)==6: break
        review.extend(chosen)
    write(base / "opening_i_candidate_evidence.csv", f082_rows)
    write(base / "opening_am_cluster_evidence.csv", am_rows)
    write(base / "opening_missing_mapping_human_review.csv", review)
    raw_f282 = sum(r["ThaiTextRaw"].count(F282) for r in corpus)
    summary = {"f082_occurrences":len(f082_rows), "f082_rows":len({(r['asset_path'],r['self_id']) for r in f082_rows}),
               "f082_supporting":sum(r['classification']=='SUPPORTING_EXACT_OPENING' for r in f082_rows),
               "f282_total":raw_f282, "f282_followed_by_0e32":len(am_rows), "f282_not_followed_by_0e32":raw_f282-len(am_rows),
               "am_rows":len({(r['asset_path'],r['self_id']) for r in am_rows}),
               "am_opening_supporting":sum(r['classification']=='SUPPORTING_EXACT_OPENING' for r in am_rows)}
    (base / "opening_missing_mapping_evidence_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary))

if __name__ == "__main__": main()
