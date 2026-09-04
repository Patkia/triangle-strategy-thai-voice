#!/usr/bin/env python3
"""สร้าง inventory และ preview decoder แบบไม่เดาความหมายของ PUA.

ใช้ Thai raw corpus ที่ extract จาก THAI-Newera-Switch_P.pak แบบ read-only เท่านั้น
และเก็บ replacement/status/notes ที่ผู้ใช้กรอกไว้ใน pua_mapping.csv เมื่อรันซ้ำ.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

COMBINING_MARKS = [
    0x0E31, 0x0E34, 0x0E35, 0x0E36, 0x0E37, 0x0E38, 0x0E39, 0x0E3A,
    0x0E47, 0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C, 0x0E4D, 0x0E4E,
]
MAP_COLUMNS = [
    "glyph", "codepoint", "replacement", "status", "occurrence_count", "row_count",
    "review_rank",
    "sample_1_self_id", "sample_1_asset_path", "sample_1", "decoded_sample_1", "target_sample_1",
    "sample_2_self_id", "sample_2_asset_path", "sample_2", "decoded_sample_2", "target_sample_2",
    "sample_3_self_id", "sample_3_asset_path", "sample_3", "decoded_sample_3", "target_sample_3",
    "sample_4_self_id", "sample_4_asset_path", "sample_4", "decoded_sample_4", "target_sample_4",
    "sample_5_self_id", "sample_5_asset_path", "sample_5", "decoded_sample_5", "target_sample_5", "notes",
]
CLUSTER_COLUMNS = ["source_sequence", "source_codepoints", "replacement", "status", "evidence", "notes"]


def is_private_use(character: str) -> bool:
    point = ord(character)
    return 0xE000 <= point <= 0xF8FF or 0xF0000 <= point <= 0xFFFFD or 0x100000 <= point <= 0x10FFFD


def context(text: str, index: int, width: int = 18) -> str:
    return text[max(0, index - width):min(len(text), index + width + 1)].replace("\r", "\\r").replace("\n", "\\n")


def category(character: str | None) -> str:
    if character is None:
        return "BOUNDARY"
    if is_private_use(character):
        return "PUA"
    return unicodedata.category(character)


def load_existing(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row["codepoint"]: row for row in csv.DictReader(handle) if row.get("codepoint")}


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"DataTableAsset", "SelfId", "ThaiTextRaw"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Input CSV is missing columns: {sorted(required)}")
        return list(reader)


def usable_replacement(row: dict[str, str], accepted_statuses: set[str]) -> bool:
    return row.get("status", "").strip().upper() in accepted_statuses and row.get("replacement", "").strip() not in {"", "-", "UNMAPPED"}


def substitute_literal(text: str, replacements: dict[str, str]) -> str:
    return "".join(replacements.get(character, character) for character in text)


def target_visible_context(raw: str, target: str, replacements: dict[str, str]) -> str:
    """แสดง target เป็น token ที่อ่านได้ โดยยังคงตัวอื่นและไม่แตะ raw sample."""
    token = f"[U+{ord(target):04X}]"
    return "".join(token if character == target else replacements.get(character, character) for character in raw)


def ensure_cluster_schema(path: Path) -> None:
    if path.exists():
        return
    # หลักฐานเดียวที่มีอยู่แล้ว; schema นี้ยังไม่ถูก decoder ใช้.
    known = {
        "source_sequence": chr(0xF282) + "า",
        "source_codepoints": "U+F282 U+0E32",
        "replacement": "อำ",
        "status": "VERIFIED",
        "evidence": "คู่ opening runtime ที่ผู้ใช้ยืนยัน; documented in docs/thai-pua-decoding.md",
        "notes": "เก็บเป็นหลักฐาน cluster เท่านั้น; decoder preview ยังไม่ consume cluster rules",
    }
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CLUSTER_COLUMNS)
        writer.writeheader()
        writer.writerow(known)


def load_source_index(path: Path) -> dict[str, list[dict[str, str]]]:
    index: dict[str, list[dict[str, str]]] = defaultdict(list)
    if not path.exists():
        return index
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("self_id"):
                index[row["self_id"]].append(row)
    return index


def source_lookup(index: dict[str, list[dict[str, str]]], self_id: str, missing_label: str) -> tuple[str, str]:
    records = index.get(self_id, [])
    if len(records) == 1:
        return records[0].get("text", ""), ""
    return "", "MULTIPLE_MATCH" if len(records) > 1 else missing_label


def run_self_test(test_root: Path) -> None:
    """ทดสอบ isolated fixture โดยไม่แตะ persistent manual mapping."""
    glyph = chr(0xF000)
    test_root.mkdir(parents=True, exist_ok=True)
    mapping = test_root / "pua_mapping.csv"
    original = {"codepoint": "U+F000", "replacement": "ข้", "status": "VERIFIED", "notes": "temporary validation"}
    with mapping.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MAP_COLUMNS)
        writer.writeheader()
        writer.writerow(original)
    preserved = load_existing(mapping)["U+F000"]
    assert preserved["replacement"] == "ข้" and preserved["status"] == "VERIFIED" and preserved["notes"] == "temporary validation"
    raw = "ก" + glyph + "ข"
    decoded = substitute_literal(raw, {glyph: preserved["replacement"]})
    assert raw == "ก" + glyph + "ข" and decoded == "กข้ข"
    assert target_visible_context(raw, glyph, {glyph: preserved["replacement"]}) == "ก[U+F000]ข"
    print("SELF-TEST: PASS (isolated mapping preservation, literal decode, visible target; persistent mapping untouched)")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="สร้าง old Switch Thai PUA manual dictionary และ decoded preview")
    parser.add_argument("--input", type=Path, default=root / "work/full_game_text_index/thai_text_raw_index.csv")
    parser.add_argument("--output-dir", type=Path, default=root / "work/new_subtitle_switch/pua_dictionary")
    parser.add_argument("--include-provisional", action="store_true", help="ใช้ PROVISIONAL ใน decoded preview เท่านั้น; coverage verified ไม่เปลี่ยน")
    parser.add_argument("--self-test", action="store_true", help="รัน isolated validation โดยไม่แก้ persistent mapping")
    args = parser.parse_args()

    if args.self_test:
        run_self_test(args.output_dir / "_validation_temp")

    source_rows = load_rows(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    mapping_path = args.output_dir / "pua_mapping.csv"
    existing = load_existing(mapping_path)

    occurrences: Counter[str] = Counter()
    row_sets: dict[str, set[tuple[str, str]]] = defaultdict(set)
    samples: dict[str, list[str]] = defaultdict(list)
    neighbor_pairs: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
    raw_mark_counts: Counter[int] = Counter()
    pua_rows = 0

    for row in source_rows:
        text = row["ThaiTextRaw"]
        found_here = set()
        for char in text:
            if ord(char) in COMBINING_MARKS:
                raw_mark_counts[ord(char)] += 1
        for index, char in enumerate(text):
            if not is_private_use(char):
                continue
            key = f"U+{ord(char):04X}"
            occurrences[key] += 1
            found_here.add(key)
            row_sets[key].add((row["DataTableAsset"], row["SelfId"]))
            # Keep review examples independent at DataTable level.  The first five
            # occurrences can otherwise be neighbouring fragments from one asset.
            sampled_assets = {sample["asset_path"] for sample in samples[key]}
            if len(samples[key]) < 5 and row["DataTableAsset"] not in sampled_assets:
                samples[key].append({
                    "asset_path": row["DataTableAsset"],
                    "self_id": row["SelfId"],
                    "raw_text": context(text, index),
                })
            previous = text[index - 1] if index else None
            following = text[index + 1] if index + 1 < len(text) else None
            neighbor_pairs[key][(category(previous), category(following))] += 1
        if found_here:
            pua_rows += 1

    mapping_rows = []
    for key in sorted(occurrences, key=lambda item: int(item[2:], 16)):
        old = existing.get(key, {})
        distributions = neighbor_pairs[key]
        # Context-only flag: a single Unicode-category pair across all uses is merely a review hint.
        risk = "LIKELY_SIMPLE" if len(distributions) == 1 else "NEEDS_REVIEW"
        old_notes = old.get("notes", "")
        generated_note = f"context_risk={risk}; neighbor_category_pairs={len(distributions)}"
        notes = old_notes if old_notes else generated_note
        mapping_rows.append({
            "glyph": chr(int(key[2:], 16)),
            "codepoint": key,
            "replacement": old.get("replacement", "-") or "-",
            "status": old.get("status", "UNMAPPED") or "UNMAPPED",
            "occurrence_count": str(occurrences[key]),
            "row_count": str(len(row_sets[key])),
            "notes": notes,
        })
        for sample_index in range(1, 6):
            sample = samples[key][sample_index - 1] if len(samples[key]) >= sample_index else {"asset_path": "", "self_id": "", "raw_text": ""}
            mapping_rows[-1][f"sample_{sample_index}_asset_path"] = sample["asset_path"]
            mapping_rows[-1][f"sample_{sample_index}_self_id"] = sample["self_id"]
            mapping_rows[-1][f"sample_{sample_index}"] = sample["raw_text"]

    # สถานะ/ค่าจากผู้ใช้เป็น source of truth; sorting มีหน้าที่เพียงจัด review view ในไฟล์เดียวกัน.
    mapping_rows.sort(key=lambda row: (0 if row["status"].strip().upper() == "UNMAPPED" else 1, -int(row["occurrence_count"]), int(row["codepoint"][2:], 16)))
    verified_replacements = {
        row["glyph"]: row["replacement"] for row in mapping_rows if usable_replacement(row, {"VERIFIED"})
    }
    preview_statuses = {"VERIFIED", "PROVISIONAL"} if args.include_provisional else {"VERIFIED"}
    preview_replacements = {
        row["glyph"]: row["replacement"] for row in mapping_rows if usable_replacement(row, preview_statuses)
    }
    review_rank = 0
    for row in mapping_rows:
        if row["status"].strip().upper() == "UNMAPPED":
            review_rank += 1
            row["review_rank"] = str(review_rank)
        else:
            row["review_rank"] = ""
        for index in range(1, 6):
            raw = row.get(f"sample_{index}", "")
            row[f"decoded_sample_{index}"] = substitute_literal(raw, preview_replacements)
            row[f"target_sample_{index}"] = target_visible_context(raw, row["glyph"], preview_replacements)

    with mapping_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MAP_COLUMNS)
        writer.writeheader()
        writer.writerows(mapping_rows)

    decoded_path = args.output_dir / "decoded_rows.csv"
    decoded_columns = ["asset_path", "self_id", "raw_text", "decoded_text", "pua_total", "pua_mapped", "pua_unmapped", "fully_decoded"]
    decoded_stats = Counter()
    verified_decoded_stats = Counter()
    with decoded_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=decoded_columns)
        writer.writeheader()
        for row in source_rows:
            text = row["ThaiTextRaw"]
            pua_chars = [char for char in text if is_private_use(char)]
            mapped = sum(char in preview_replacements for char in pua_chars)
            unmapped = len(pua_chars) - mapped
            decoded = substitute_literal(text, preview_replacements)
            full = len(pua_chars) == 0 or unmapped == 0
            decoded_stats["fully" if full else "partial"] += 1
            if unmapped:
                decoded_stats["rows_unmapped"] += 1
            verified_unmapped = sum(char not in verified_replacements for char in pua_chars)
            verified_full = len(pua_chars) == 0 or verified_unmapped == 0
            verified_decoded_stats["fully" if verified_full else "partial"] += 1
            if verified_unmapped:
                verified_decoded_stats["rows_unmapped"] += 1
            writer.writerow({
                "asset_path": row["DataTableAsset"], "self_id": row["SelfId"], "raw_text": text,
                "decoded_text": decoded, "pua_total": len(pua_chars), "pua_mapped": mapped,
                "pua_unmapped": unmapped, "fully_decoded": "TRUE" if full else "FALSE",
            })

    verified_keys = {row["codepoint"] for row in mapping_rows if usable_replacement(row, {"VERIFIED"})}
    provisional_keys = {row["codepoint"] for row in mapping_rows if usable_replacement(row, {"PROVISIONAL"})}
    mapped_occurrences = sum(occurrences[key] for key in verified_keys)
    provisional_occurrences = sum(occurrences[key] for key in provisional_keys)
    total_occurrences = sum(occurrences.values())
    other_private = [key for key in occurrences if not (0xE000 <= int(key[2:], 16) <= 0xF8FF)]
    status_counts = Counter(row["status"].strip().upper() or "UNMAPPED" for row in mapping_rows)
    unmapped_rows = [row for row in mapping_rows if row["status"].strip().upper() == "UNMAPPED"]
    # Rebuild only the exact-SelfId cache needed by the current Top-30 human review view.
    # The helper reads PAKs read-only and never derives a PUA replacement.
    source_builder = root / "tools/build_pua_review_source_indexes.py"
    result = subprocess.run([sys.executable, str(source_builder)], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("source index build failed: " + (result.stderr.strip() or result.stdout.strip()))
    source_root = args.output_dir / "source_indexes"
    source_indexes = {
        "steam": load_source_index(source_root / "steam_selfid_index.csv"),
        "update": load_source_index(source_root / "update_selfid_index.csv"),
        "base": load_source_index(source_root / "base_selfid_index.csv"),
    }
    source_stats = Counter()
    for row in unmapped_rows[:30]:
        for sample_index in range(1, 6):
            self_id = row.get(f"sample_{sample_index}_self_id", "")
            if not self_id:
                continue
            source_stats["sample_contexts_total"] += 1
            failures = []
            for source, missing in (("steam", "STEAM_NOT_FOUND"), ("update", "UPDATE_NOT_FOUND"), ("base", "BASE_NOT_FOUND")):
                text, failure = source_lookup(source_indexes[source], self_id, missing)
                column_prefix = {"steam": "steam_thai", "update": "update_english", "base": "base_english"}[source]
                row[f"{column_prefix}_{sample_index}"] = text
                if failure:
                    failures.append(failure)
                    source_stats[failure] += 1
                else:
                    source_stats[f"{source}_found"] += 1
            row[f"sample_{sample_index}_match_status"] = "FULL" if not failures else ";".join(failures)
            source_stats["full_matches" if not failures else "non_full_matches"] += 1
    coverage = args.output_dir / "coverage.txt"
    lines = [
        "OLD SWITCH THAI PUA DICTIONARY — COVERAGE",
        f"Input corpus: {args.input}",
        f"Total text rows: {len(source_rows)}",
        f"Rows containing PUA: {pua_rows}",
        f"Unique PUA glyphs: {len(occurrences)}",
        f"Total PUA occurrences: {total_occurrences}",
        f"Verified unique glyphs: {len(verified_keys)}",
        f"Provisional unique glyphs: {len(provisional_keys)}",
        f"Unmapped unique glyphs: {status_counts['UNMAPPED']}",
        f"Cluster-required glyphs: {status_counts['CLUSTER_REQUIRED']}",
        f"Conflict glyphs: {status_counts['CONFLICT']}",
        f"Verified occurrences: {mapped_occurrences}",
        f"Provisional occurrences: {provisional_occurrences}",
        f"Verified occurrence coverage: {(100 * mapped_occurrences / total_occurrences) if total_occurrences else 0:.2f}%",
        f"Provisional occurrence coverage: {(100 * provisional_occurrences / total_occurrences) if total_occurrences else 0:.2f}%",
        f"Rows fully decoded using VERIFIED only: {verified_decoded_stats['fully']} / {len(source_rows)}",
        f"Partially decoded rows using VERIFIED only: {verified_decoded_stats['partial']}",
        f"Rows with unmapped PUA using VERIFIED only: {verified_decoded_stats['rows_unmapped']}",
        f"Other private-use codepoints outside U+E000-U+F8FF: {len(other_private)}",
        "",
        "Source coverage for review queue (exact SelfId only):",
        f"Review sample contexts total: {source_stats['sample_contexts_total']}",
        f"Steam exact SelfId found: {source_stats['steam_found']}",
        f"Steam not found: {source_stats['STEAM_NOT_FOUND']}",
        f"Update exact SelfId found: {source_stats['update_found']}",
        f"Update not found: {source_stats['UPDATE_NOT_FOUND']}",
        f"Base exact SelfId found: {source_stats['base_found']}",
        f"Base not found: {source_stats['BASE_NOT_FOUND']}",
        f"All-source FULL matches: {source_stats['full_matches']}",
        f"Duplicate/Ambiguous SelfIds: {source_stats['MULTIPLE_MATCH']}",
        "",
        "Thai combining marks in raw corpus:",
    ]
    lines.extend(f"U+{point:04X} {chr(point)}: {raw_mark_counts[point]}" for point in COMBINING_MARKS)
    lines.extend(["", "TOP 20 UNMAPPED BY OCCURRENCE"])
    for rank, row in enumerate(unmapped_rows[:20], start=1):
        lines.append(f"{rank}. {row['codepoint']} {row['glyph']}: {row['occurrence_count']} occurrences; {row['row_count']} rows")
    coverage.write_text("\n".join(lines) + "\n", encoding="utf-8")

    queue_columns = ["review_rank", "glyph", "codepoint", "occurrence_count", "row_count"]
    for sample_index in range(1, 6):
        queue_columns.extend([
            f"sample_{sample_index}_self_id", f"target_sample_{sample_index}",
            f"steam_thai_{sample_index}", f"update_english_{sample_index}", f"base_english_{sample_index}",
            f"sample_{sample_index}_match_status",
        ])
    queue_columns.extend(["replacement", "status", "notes"])
    with (args.output_dir / "review_queue.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=queue_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(unmapped_rows[:30])

    lookup_columns = ["target_codepoint", "target_glyph", "occurrence_count", "self_id", "asset_path", "raw_text", "decoded_text", "target_text"]
    lookup_rows = []
    for row in mapping_rows:
        for sample_index in range(1, 6):
            raw = row.get(f"sample_{sample_index}", "")
            if not raw:
                continue
            lookup_rows.append({
                "target_codepoint": row["codepoint"], "target_glyph": row["glyph"], "occurrence_count": row["occurrence_count"],
                "self_id": row.get(f"sample_{sample_index}_self_id", ""),
                "asset_path": row.get(f"sample_{sample_index}_asset_path", ""), "raw_text": raw,
                "decoded_text": row.get(f"decoded_sample_{sample_index}", ""),
                "target_text": row.get(f"target_sample_{sample_index}", ""),
            })
    lookup_rows.sort(key=lambda row: (-int(row["occurrence_count"]), int(row["target_codepoint"][2:], 16), row["self_id"]))
    with (args.output_dir / "manual_lookup.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=lookup_columns)
        writer.writeheader()
        writer.writerows(lookup_rows)

    ensure_cluster_schema(args.output_dir / "pua_cluster_mapping.csv")

    print("PUA REVIEW SUMMARY")
    print(f"Verified: {len(verified_keys)} / {len(occurrences)}; Provisional: {len(provisional_keys)}; Unmapped: {status_counts['UNMAPPED']}; Cluster required: {status_counts['CLUSTER_REQUIRED']}")
    print(f"Verified occurrence coverage: {(100 * mapped_occurrences / total_occurrences) if total_occurrences else 0:.2f}%")
    print(f"Fully decoded rows using {'VERIFIED+PROVISIONAL' if args.include_provisional else 'VERIFIED'} preview: {decoded_stats['fully']} / {len(source_rows)}")
    if unmapped_rows:
        print("Next review: " + "; ".join(f"{row['codepoint']} ({row['occurrence_count']})" for row in unmapped_rows[:3]))
    print(f"mapping={mapping_path}")
    print(f"decoded={decoded_path}")
    print(f"coverage={coverage}")


if __name__ == "__main__":
    main()
