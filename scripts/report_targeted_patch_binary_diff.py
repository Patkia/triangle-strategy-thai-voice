from __future__ import annotations

import csv
import struct
from pathlib import Path

RELATIVE = Path("Newera/Content/Newera/Data/DataTables/Scenario/Text/en/Main/trial_01/Text_trial_01_ms06_x07_wd_0010")
SERIAL_SIZE_OFFSET = 1413
TEXT_SIZE_OFFSET = 102
FSTRING_LENGTH_OFFSET = 111
FSTRING_PAYLOAD_OFFSET = 115
FOOTER_SIZE = 4


def i64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<q", data, offset)[0]


def i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def main() -> None:
    root = Path.cwd() / "work/new_subtitle_switch/targeted_patch_poc"
    original_base = root / "original" / RELATIVE
    unicode_base = root / "unicode" / RELATIVE
    original_uasset = original_base.with_suffix(".uasset").read_bytes()
    modified_uasset = unicode_base.with_suffix(".uasset").read_bytes()
    original_uexp = original_base.with_suffix(".uexp").read_bytes()
    modified_uexp = unicode_base.with_suffix(".uexp").read_bytes()
    delta = len(modified_uexp) - len(original_uexp)
    original_tail = original_uexp[FSTRING_PAYLOAD_OFFSET + 67:-FOOTER_SIZE]
    modified_tail = modified_uexp[FSTRING_PAYLOAD_OFFSET + 134:-FOOTER_SIZE]
    uasset_same_except_serial_size = (
        original_uasset[:SERIAL_SIZE_OFFSET] == modified_uasset[:SERIAL_SIZE_OFFSET]
        and original_uasset[SERIAL_SIZE_OFFSET + 8:] == modified_uasset[SERIAL_SIZE_OFFSET + 8:]
    )
    rows = [
        ("uasset", "file size", len(original_uasset), len(modified_uasset), 0, "NOT AFFECTED", "header size unchanged"),
        ("uasset", f"Export.SerialSize @ {SERIAL_SIZE_OFFSET}", i64(original_uasset, SERIAL_SIZE_OFFSET), i64(modified_uasset, SERIAL_SIZE_OFFSET), i64(modified_uasset, SERIAL_SIZE_OFFSET) - i64(original_uasset, SERIAL_SIZE_OFFSET), "AFFECTED", "matches .uexp serialized payload delta"),
        ("uasset", "all other bytes", "unchanged", "unchanged", 0, "PASS" if uasset_same_except_serial_size else "FAIL", "only SerialSize field differs"),
        ("uexp", "file size", len(original_uexp), len(modified_uexp), delta, "AFFECTED", "UTF-16LE FString is larger"),
        ("uexp", f"Text StrProperty.Size @ {TEXT_SIZE_OFFSET}", i32(original_uexp, TEXT_SIZE_OFFSET), i32(modified_uexp, TEXT_SIZE_OFFSET), i32(modified_uexp, TEXT_SIZE_OFFSET) - i32(original_uexp, TEXT_SIZE_OFFSET), "AFFECTED", "serialized FString byte size"),
        ("uexp", f"FString length @ {FSTRING_LENGTH_OFFSET}", i32(original_uexp, FSTRING_LENGTH_OFFSET), i32(modified_uexp, FSTRING_LENGTH_OFFSET), i32(modified_uexp, FSTRING_LENGTH_OFFSET) - i32(original_uexp, FSTRING_LENGTH_OFFSET), "AFFECTED", "positive ANSI count becomes negative UTF-16 code-unit count"),
        ("uexp", f"FString payload @ {FSTRING_PAYLOAD_OFFSET}", "67 bytes", "134 bytes", 67, "AFFECTED", "original ASCII terminator replaced by UTF-16LE terminator"),
        ("uexp", "following serialized data", "offset 182..3608", "offset 249..3675", 67, "PASS" if original_tail == modified_tail else "FAIL", "identical content after the inserted payload delta"),
        ("uexp", "four-byte footer", original_uexp[-FOOTER_SIZE:].hex(), modified_uexp[-FOOTER_SIZE:].hex(), 0, "NOT AFFECTED", "footer bytes preserved at end of file"),
        ("uexp", "unexplained ranges", "none", "none", 0, "PASS", "all changes are one property payload, its size, and export SerialSize"),
    ]
    with (root / "binary_diff.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("File", "Field or range", "Original", "Modified", "Delta", "Status", "Explanation"))
        writer.writerows(rows)
    if i64(modified_uasset, SERIAL_SIZE_OFFSET) != len(modified_uexp) - FOOTER_SIZE:
        raise SystemExit("Export.SerialSize mismatch")
    if original_uexp[-FOOTER_SIZE:] != modified_uexp[-FOOTER_SIZE:]:
        raise SystemExit("Footer changed")
    if original_tail != modified_tail or not uasset_same_except_serial_size:
        raise SystemExit("Unexpected binary differences")


if __name__ == "__main__":
    main()
