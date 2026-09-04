#!/usr/bin/env python3
"""เพิ่มผลเปรียบเทียบ raster จาก Windows GDI complex-script renderer ลง CSV."""

import argparse
import csv
from pathlib import Path

from PIL import Image, ImageChops


def crop(path: Path) -> Image.Image:
    image = Image.open(path).convert("L")
    box = image.getbbox()
    return image.crop(box) if box else image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--gdi-dir", required=True, type=Path)
    args = parser.parse_args()

    with args.csv.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0])
    for field in ["GdiFontEvidence", "GdiVisualSimilarity", "GdiRawWidth", "GdiExpectedWidth"]:
        if field not in fields:
            fields.append(field)

    for number, row in enumerate(rows, 1):
        tag = f"{number:02d}_{row['PUACodepoint'].replace('+', '')}"
        raw = crop(args.gdi_dir / f"{tag}_raw.png")
        expected = crop(args.gdi_dir / f"{tag}_expected.png")
        width, height = max(raw.width, expected.width), max(raw.height, expected.height)
        a, b = Image.new("L", (width, height)), Image.new("L", (width, height))
        a.paste(raw); b.paste(expected)
        difference = ImageChops.difference(a, b)
        score = 1.0 - sum(difference.getdata()) / (255 * width * height)
        size_close = abs(raw.width - expected.width) <= 2 and abs(raw.height - expected.height) <= 2
        row["GdiFontEvidence"] = "SUPPORTS_GDI" if score >= 0.95 and size_close else "INCONCLUSIVE_GDI"
        row["GdiVisualSimilarity"] = f"{score:.6f}"
        row["GdiRawWidth"] = raw.width
        row["GdiExpectedWidth"] = expected.width
        # กฎยืนยันเฉพาะคู่ opening ที่มนุษย์ตรวจแล้ว ไม่อ้างว่าใช้ได้ทั่ว corpus.
        row["RuleStatus"] = "CONFIRMED_OPENING_LOCAL" if row["GdiFontEvidence"] == "SUPPORTS_GDI" else "PROBABLE_OPENING_LOCAL"

    with args.csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    main()
