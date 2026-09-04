from __future__ import annotations

import argparse
import csv
from pathlib import Path

SELF_ID = "TRIAL_01_MS06_X07_WD_0010_N_NNN_0010"
THAI_TEXT = "ในทวีปอันห่างไกลแห่งนอร์เซเลีย ถูกปกครองโดยอาณาจักรมหาอำนาจทั้งสาม"
CONTROL_TEXT = "A" * 66


def read_index(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    return {row["RowKey"]: row for row in rows}


def status_from_manifest(path: Path) -> tuple[bool, int]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    return len(rows) == 1 and rows[0]["Status"] == "OK", int(rows[0]["RowCount"]) if rows else 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("control", "unicode", "deploy"))
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.workspace.resolve() / "work/new_subtitle_switch/targeted_patch_poc"
    original = read_index(root / "original_batch/english_text_index.csv")
    variant = read_index(root / f"{args.mode}_batch/english_text_index.csv")
    parse_ok, manifest_rows = status_from_manifest(root / f"{args.mode}_batch/export_manifest.csv")
    expected_text = CONTROL_TEXT if args.mode == "control" else THAI_TEXT
    target = variant.get(SELF_ID, {})
    other_changed = [key for key in original if key != SELF_ID and original[key] != variant.get(key)]
    target_only = set(original) == set(variant) and target.get("EnglishText") == expected_text and not other_changed
    validation_rows = [
        ("DataTable parse", "PASS", "PASS" if parse_ok else "FAIL"),
        ("Rows", "13", str(manifest_rows)),
        ("Target SelfId", SELF_ID, target.get("SelfId", "MISSING")),
        ("Target Text", expected_text, target.get("EnglishText", "MISSING")),
        ("Other rows changed", "0", str(len(other_changed))),
        ("Parser exceptions", "0", str(sum(1 for _ in csv.DictReader((root / f"{args.mode}_batch/exceptions.csv").open(newline="", encoding="utf-8-sig"))))),
        ("Semantic target-only diff", "PASS", "PASS" if target_only else "FAIL"),
    ]
    destination = root / f"{args.mode}_validation.csv"
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Check", "Expected", "Actual"))
        writer.writerows(validation_rows)
    if args.mode == "unicode":
        with (root / "semantic_diff.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(("RowKey", "Field", "Original", "Modified", "Status"))
            for key in sorted(set(original) | set(variant)):
                before = original.get(key, {})
                after = variant.get(key, {})
                for field in ("SelfId", "EnglishText"):
                    if before.get(field) != after.get(field):
                        writer.writerow((key, field, before.get(field, ""), after.get(field, ""), "ALLOWED_TARGET_TEXT" if key == SELF_ID and field == "EnglishText" else "UNEXPECTED"))
    if not (parse_ok and manifest_rows == 13 and target_only):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
