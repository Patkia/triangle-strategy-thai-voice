#!/usr/bin/env python3
"""สร้าง English ↔ Thai join แบบ exact SelfId และ asset เดียวกันเท่านั้น."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "work" / "full_game_text_index"


def thai_status(text: str) -> str:
    if not text:
        return "EMPTY"
    if any(0xE000 <= ord(char) <= 0xF8FF for char in text):
        return "PUA"
    return "READABLE"


def main() -> None:
    with (OUT / "english_text_index.csv").open(encoding="utf-8-sig", newline="") as handle:
        english = list(csv.DictReader(handle))
    with (OUT / "thai_text_raw_index.csv").open(encoding="utf-8-sig", newline="") as handle:
        thai = list(csv.DictReader(handle))

    thai_by_asset_and_id: dict[tuple[str, str], list[dict[str, str]]] = {}
    thai_ids = Counter()
    for row in thai:
        thai_by_asset_and_id.setdefault((row["DataTableAsset"], row["SelfId"]), []).append(row)
        thai_ids[row["SelfId"]] += 1

    joined: list[dict[str, str]] = []
    unmatched_english: list[dict[str, str]] = []
    for en in english:
        candidates = thai_by_asset_and_id.get((en["DataTableAsset"], en["SelfId"]), [])
        if len(candidates) == 1:
            th = candidates[0]
            joined.append({
                "SelfId": en["SelfId"], "DataTableAssetEN": en["DataTableAsset"], "EnglishText": en["EnglishText"],
                "DataTableAssetTH": th["DataTableAsset"], "ThaiTextRaw": th["ThaiTextRaw"],
                "ThaiRowPresent": "YES", "ThaiTextStatus": thai_status(th["ThaiTextRaw"]),
            })
        else:
            joined.append({
                "SelfId": en["SelfId"], "DataTableAssetEN": en["DataTableAsset"], "EnglishText": en["EnglishText"],
                "DataTableAssetTH": "", "ThaiTextRaw": "", "ThaiRowPresent": "NO", "ThaiTextStatus": "MISSING",
            })
            unmatched_english.append(en)

    matched_keys = {(row["DataTableAssetEN"], row["SelfId"]) for row in joined if row["ThaiRowPresent"] == "YES"}
    thai_without_english = [row for row in thai if (row["DataTableAsset"], row["SelfId"]) not in matched_keys]
    fieldnames = ["SelfId", "DataTableAssetEN", "EnglishText", "DataTableAssetTH", "ThaiTextRaw", "ThaiRowPresent", "ThaiTextStatus"]
    with (OUT / "english_thai_identifier_join.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(joined)

    print({
        "english_records": len(english), "thai_records": len(thai), "exact_asset_and_selfid_join": len(english) - len(unmatched_english),
        "english_without_thai": len(unmatched_english), "thai_without_english": len(thai_without_english),
        "unique_thai_selfids": len(thai_ids), "duplicate_thai_selfid_records": sum(count - 1 for count in thai_ids.values() if count > 1),
        "empty_thai": sum(not row["ThaiTextRaw"] for row in thai),
        "pua_thai": sum(thai_status(row["ThaiTextRaw"]) == "PUA" for row in thai),
        "readable_thai": sum(thai_status(row["ThaiTextRaw"]) == "READABLE" for row in thai),
    })


if __name__ == "__main__":
    main()
