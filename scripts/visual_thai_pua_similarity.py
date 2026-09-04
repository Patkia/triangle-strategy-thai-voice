#!/usr/bin/env python3
"""สร้าง visual candidates จาก glyph raster; output ไม่ใช่ semantic mapping."""

from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path

from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
RAW_INDEX = ROOT / "work" / "full_game_text_index" / "thai_text_raw_index.csv"
FONT_PATH = ROOT / "work" / "full_game_text_index" / "font_poc" / "thai" / "Engine" / "Content" / "Slate" / "Fonts" / "DroidSansFallback.ttf"
OUT = ROOT / "work" / "thai_pua"


def cmap(font: TTFont) -> dict[int, str]:
    result: dict[int, str] = {}
    for table in font["cmap"].tables:
        if table.isUnicode():
            result.update(table.cmap)
    return result


def rasterize(font: ImageFont.FreeTypeFont, codepoint: int) -> Image.Image:
    canvas = Image.new("L", (256, 256), 0)
    draw = ImageDraw.Draw(canvas)
    draw.text((128, 128), chr(codepoint), font=font, fill=255, anchor="mm")
    bbox = canvas.getbbox()
    if bbox is None:
        return Image.new("L", (64, 64), 0)
    glyph = canvas.crop(bbox)
    glyph.thumbnail((56, 56), Image.Resampling.LANCZOS)
    result = Image.new("L", (64, 64), 0)
    result.paste(glyph, ((64 - glyph.width) // 2, (64 - glyph.height) // 2))
    return result


def similarity(first: Image.Image, second: Image.Image) -> float:
    histogram = ImageChops.difference(first, second).histogram()
    mse = sum(value * value * count for value, count in enumerate(histogram)) / (first.width * first.height)
    return 1.0 - math.sqrt(mse) / 255.0


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with RAW_INDEX.open(encoding="utf-8-sig", newline="") as handle:
        corpus_counts = Counter(
            ord(character)
            for row in csv.DictReader(handle)
            for character in row["ThaiTextRaw"]
            if 0xE000 <= ord(character) <= 0xF8FF
        )
    font_data = TTFont(FONT_PATH, lazy=True)
    characters = cmap(font_data)
    pua = [codepoint for codepoint in sorted(corpus_counts) if codepoint in characters]
    thai_unicode = sorted(codepoint for codepoint in characters if 0x0E00 <= codepoint <= 0x0E7F)
    image_font = ImageFont.truetype(str(FONT_PATH), size=180)
    thai_images = {codepoint: rasterize(image_font, codepoint) for codepoint in thai_unicode}

    candidates = []
    for codepoint in pua:
        source = rasterize(image_font, codepoint)
        ranked = sorted(((similarity(source, image), target) for target, image in thai_images.items()), reverse=True)
        top_score, top_codepoint = ranked[0]
        next_score = ranked[1][0] if len(ranked) > 1 else 0.0
        candidates.append({
            "PUACodepoint": f"U+{codepoint:04X}",
            "Occurrences": corpus_counts[codepoint],
            "VisualCandidateThaiUnicode": f"U+{top_codepoint:04X}",
            "VisualSimilarity": f"{top_score:.6f}",
            "SecondSimilarity": f"{next_score:.6f}",
            "Margin": f"{top_score - next_score:.6f}",
            "CandidateStatus": "UNCONFIRMED_VISUAL",
            "MappingStatus": "UNKNOWN",
            "Evidence": "same-font raster similarity only; not semantic evidence",
        })
    with (OUT / "candidate_mapping.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(candidates[0]))
        writer.writeheader()
        writer.writerows(candidates)

    # Contact sheet แสดง glyph PUA และ candidate ที่ score สูงสุด 32 รายการ; ใช้เพื่อ review เท่านั้น.
    best = sorted(candidates, key=lambda row: float(row["VisualSimilarity"]), reverse=True)[:32]
    sheet = Image.new("L", (8 * 160, 4 * 96), 255)
    draw = ImageDraw.Draw(sheet)
    label_font = ImageFont.load_default()
    for index, row in enumerate(best):
        x = (index % 8) * 160
        y = (index // 8) * 96
        pua_image = rasterize(image_font, int(row["PUACodepoint"][2:], 16))
        thai_image = rasterize(image_font, int(row["VisualCandidateThaiUnicode"][2:], 16))
        sheet.paste(ImageOps.invert(pua_image), (x + 8, y + 4))
        sheet.paste(ImageOps.invert(thai_image), (x + 88, y + 4))
        draw.text((x + 2, y + 70), row["PUACodepoint"] + " / " + row["VisualCandidateThaiUnicode"], fill=0, font=label_font)
    sheet.save(OUT / "visual_similarity_contact_sheet.png")

    print({
        "pua_rendered": len(candidates),
        "thai_reference_glyphs": len(thai_unicode),
        "confirmed": 0,
        "probable": 0,
        "unknown": len(candidates),
        "best_similarity": max(float(row["VisualSimilarity"]) for row in candidates),
    })


if __name__ == "__main__":
    main()
