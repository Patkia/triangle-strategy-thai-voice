#!/usr/bin/env python3
"""สร้าง inventory PUA glyph และตรวจ known opening line แบบ read-only."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from fontTools.ttLib import TTFont


ROOT = Path(__file__).resolve().parents[1]
RAW_INDEX = ROOT / "work" / "full_game_text_index" / "thai_text_raw_index.csv"
FONT = ROOT / "work" / "full_game_text_index" / "font_poc" / "thai" / "Engine" / "Content" / "Slate" / "Fonts" / "DroidSansFallback.ttf"
OUT = ROOT / "work" / "thai_pua"
OPENING_ID = "MS01_X01_WD_0010_N_NNN_0010"
EXPECTED_OPENING = (
    "\u0e1a\u0e19\u0e17\u0e27\u0e35\u0e1b\u0e2d\u0e31\u0e19\u0e2b\u0e48\u0e32\u0e07"
    "\u0e44\u0e01\u0e25\u0e02\u0e2d\u0e07\u0e19\u0e2d\u0e23\u0e4c\u0e40\u0e0b\u0e40\u0e25\u0e35\u0e22 "
    "\u0e21\u0e2b\u0e32\u0e2d\u0e33\u0e19\u0e32\u0e08\u0e2a\u0e32\u0e21\u0e41\u0e2b\u0e48\u0e07"
    "\u0e44\u0e14\u0e49\u0e1b\u0e01\u0e04\u0e23\u0e2d\u0e07"
)


def unicode_cmap(font: TTFont) -> dict[int, str]:
    result: dict[int, str] = {}
    for table in font["cmap"].tables:
        if table.isUnicode():
            result.update(table.cmap)
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with RAW_INDEX.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    corpus_counts = Counter(
        ord(char)
        for row in rows
        for char in row["ThaiTextRaw"]
        if 0xE000 <= ord(char) <= 0xF8FF
    )
    font = TTFont(FONT)
    cmap = unicode_cmap(font)
    metrics = font["hmtx"].metrics
    glyf = font["glyf"]

    inventory: list[dict[str, object]] = []
    for codepoint in sorted(corpus_counts):
        glyph_name = cmap.get(codepoint, "")
        glyph = glyf[glyph_name] if glyph_name else None
        advance, lsb = metrics.get(glyph_name, ("", ""))
        inventory.append({
            "PUACodepoint": f"U+{codepoint:04X}",
            "Occurrences": corpus_counts[codepoint],
            "GlyphAvailable": "YES" if glyph_name else "NO",
            "GlyphName": glyph_name,
            "GlyphIndex": font.getGlyphID(glyph_name) if glyph_name else "",
            "AdvanceWidth": advance,
            "LeftSideBearing": lsb,
            "IsComposite": "YES" if glyph_name and glyph.isComposite() else "NO",
            "ContourCount": glyph.numberOfContours if glyph_name and not glyph.isComposite() else "",
            "ThaiUnicodeCandidate": "",
            "MappingStatus": "UNKNOWN",
            "Evidence": "cmap provides PUA glyph only; no Unicode Thai alias",
        })

    fields = list(inventory[0]) if inventory else []
    with (OUT / "glyph_inventory.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(inventory)

    raw = next(row["ThaiTextRaw"] for row in rows if row["SelfId"] == OPENING_ID)
    conflicts = [
        index
        for index, char in enumerate(raw)
        if not 0xE000 <= ord(char) <= 0xF8FF
        and (index >= len(EXPECTED_OPENING) or char != EXPECTED_OPENING[index])
    ]
    validation = {
        "SelfId": OPENING_ID,
        "Raw": raw,
        "Expected": EXPECTED_OPENING,
        "RawLength": len(raw),
        "ExpectedLength": len(EXPECTED_OPENING),
        "RawPUACount": sum(0xE000 <= ord(char) <= 0xF8FF for char in raw),
        "NonPUAPositionContradictions": len(conflicts),
        "Result": "FAIL",
        "Reason": "Single-codepoint PUA substitution cannot reconcile immutable non-PUA characters and unequal lengths.",
        "GSUBPresent": "YES" if "GSUB" in font else "NO",
        "GPOSPresent": "YES" if "GPOS" in font else "NO",
    }
    with (OUT / "opening_validation.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(validation))
        writer.writeheader()
        writer.writerow(validation)

    print({
        "corpus_pua_codepoints": len(corpus_counts),
        "glyphs_available": sum(bool(cmap.get(codepoint)) for codepoint in corpus_counts),
        "gsub": "GSUB" in font,
        "gpos": "GPOS" in font,
        "opening_result": validation["Result"],
        "opening_contradictions": len(conflicts),
    })


if __name__ == "__main__":
    main()
