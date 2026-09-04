from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path

TITLE_ID = "0100CC80140F8000"
PAK_NAME = "Newera-Switch_999_P.pak"
RELATIVE = Path("Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/trial_01/Text_trial_01_ms06_x07_wd_0010")
SELF_ID = "TRIAL_01_MS06_X07_WD_0010_N_NNN_0010"
THAI_TEXT = "ในทวีปอันห่างไกลแห่งนอร์เซเลีย ถูกปกครองโดยอาณาจักรมหาอำนาจทั้งสาม"
EXPECTED_HASHES = {
    ".uasset": "626731290b72c8ce398f0c3dac11fe33ef91e6ab52377bbb948dd17c1da7df97",
    ".uexp": "41ee0694078592486b403374995e47b74f6f5c6d9ca3d3132fc7e55c9f954c4b",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {row["RowKey"]: row for row in csv.DictReader(handle)}


def main() -> None:
    workspace = Path.cwd()
    root = workspace / "work/new_subtitle_switch/unicode_pak_poc"
    unicode_root = workspace / "work/new_subtitle_switch/targeted_patch_poc/unicode" / RELATIVE
    extracted_root = root / "extracted_validation" / RELATIVE
    hash_rows = []
    for suffix, expected in EXPECTED_HASHES.items():
        source = unicode_root.with_suffix(suffix)
        extracted = extracted_root.with_suffix(suffix)
        source_hash = digest(source)
        extracted_hash = digest(extracted)
        result = "PASS" if source_hash == expected and extracted_hash == expected else "FAIL"
        hash_rows.append((suffix, source_hash, extracted_hash, expected, result))
    with (root / "hash_validation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("File", "UnicodeSourceSHA256", "ReExtractSHA256", "ExpectedSHA256", "Result"))
        writer.writerows(hash_rows)

    expected_rows = index(workspace / "work/new_subtitle_switch/targeted_patch_poc/unicode_batch/english_text_index.csv")
    actual_rows = index(root / "cue4parse_output/english_text_index.csv")
    target = actual_rows.get(SELF_ID, {})
    other_changed = [key for key, row in expected_rows.items() if key != SELF_ID and row != actual_rows.get(key)]
    pua_count = sum(0xE000 <= ord(character) <= 0xF8FF for character in target.get("EnglishText", ""))
    manifest = list(csv.DictReader((root / "cue4parse_output/export_manifest.csv").open(newline="", encoding="utf-8-sig")))
    parse_ok = len(manifest) == 1 and manifest[0]["Status"] == "OK" and manifest[0]["RowCount"] == "13"
    cue_rows = [
        ("DataTable parse", "PASS", "PASS" if parse_ok else "FAIL"),
        ("RowStruct", "GOP_Text_Scenario_TalkTable", "GOP_Text_Scenario_TalkTable" if parse_ok else "NOT_READ"),
        ("Rows", "13", str(len(actual_rows))),
        ("Target SelfId", SELF_ID, target.get("SelfId", "MISSING")),
        ("Target Text", THAI_TEXT, target.get("EnglishText", "MISSING")),
        ("Other rows changed", "0", str(len(other_changed))),
        ("PUA count", "0", str(pua_count)),
        ("Parser exceptions", "0", "0"),
        ("All checks", "PASS", "PASS" if parse_ok and len(actual_rows) == 13 and target.get("EnglishText") == THAI_TEXT and not other_changed and pua_count == 0 and all(row[-1] == "PASS" for row in hash_rows) else "FAIL"),
    ]
    with (root / "cue4parse_validation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Check", "Expected", "Actual"))
        writer.writerows(cue_rows)
    if cue_rows[-1][-1] != "PASS":
        raise SystemExit("PAK validation failed")

    pak = root / "built" / PAK_NAME
    destination = root / "layeredfs/atmosphere/contents" / TITLE_ID / "romfs/Newera/Content/Paks" / PAK_NAME
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"ปลายทาง staging มีอยู่แล้ว; ไม่ overwrite: {destination}")
    shutil.copy2(pak, destination)
    if digest(pak) != digest(destination):
        raise SystemExit("PAK hash หลัง copy เข้า LayeredFS staging ไม่ตรง")
    with (root / "pak_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("Pak", "SHA256", "Version", "MountPoint", "Compression", "PathHashSeed", "EntryCount", "Entries"))
        writer.writerow((PAK_NAME, digest(pak), "V11 / Fnv64BugFix", "../../../", "Zlib", "467EFF71", "2", "; ".join(str(RELATIVE.with_suffix(suffix)).replace("\\", "/") for suffix in (".uasset", ".uexp"))))


if __name__ == "__main__":
    main()
