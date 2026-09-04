#!/usr/bin/env python3
"""วิเคราะห์คู่ข้อความ raw/ข้อความที่ยืนยันแล้วโดยไม่สร้างคำแปลจาก English."""

from __future__ import annotations

import argparse
import csv
import difflib
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont


def pua_chars(text: str) -> list[str]:
    return [ch for ch in text if 0xE000 <= ord(ch) <= 0xF8FF]


def esc(text: str) -> str:
    return text.encode("unicode_escape").decode("ascii")


def crop_alpha(image: Image.Image) -> Image.Image:
    box = image.getbbox()
    return image.crop(box) if box else image.crop((0, 0, 1, 1))


def render(font: ImageFont.FreeTypeFont, text: str) -> Image.Image:
    image = Image.new("L", (800, 180), 0)
    ImageDraw.Draw(image).text((60, 30), text, fill=255, font=font)
    return crop_alpha(image)


def visual_evidence(font: ImageFont.FreeTypeFont, raw: str, expected: str, path: Path) -> tuple[str, float, int, int]:
    raw_img = render(font, raw)
    expected_img = render(font, expected)
    width = max(raw_img.width, expected_img.width)
    height = max(raw_img.height, expected_img.height)
    a = Image.new("L", (width, height), 0)
    b = Image.new("L", (width, height), 0)
    a.paste(raw_img, (0, 0))
    b.paste(expected_img, (0, 0))
    diff = ImageChops.difference(a, b)
    pixels = width * height
    score = 1.0 - (sum(diff.getdata()) / (255 * pixels))
    combined = Image.new("L", (width * 2 + 20, height), 0)
    combined.paste(a, (0, 0))
    combined.paste(b, (width + 20, 0))
    combined.save(path)
    status = "SUPPORTS" if score >= 0.995 and raw_img.size == expected_img.size else "NONCONTRADICTORY" if score >= 0.90 else "INCONCLUSIVE"
    return status, score, raw_img.width, expected_img.width


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--thai-index", required=True, type=Path)
    parser.add_argument("--english-index", required=True, type=Path)
    parser.add_argument("--self-id", required=True)
    parser.add_argument("--expected-file", required=True, type=Path)
    parser.add_argument("--font", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    font_dir = args.output_dir / "font_evidence"
    font_dir.mkdir(exist_ok=True)
    expected = args.expected_file.read_text(encoding="utf-8").rstrip("\r\n")

    with args.thai_index.open(encoding="utf-8-sig", newline="") as f:
        thai_rows = list(csv.DictReader(f))
    with args.english_index.open(encoding="utf-8-sig", newline="") as f:
        english_rows = list(csv.DictReader(f))
    row = next(r for r in thai_rows if r["SelfId"] == args.self_id)
    raw = row["ThaiTextRaw"]

    # SequenceMatcher ให้ anchor จาก Thai codepoint ที่คงอยู่ และเปิดให้ PUA/cluster แทนช่วงหลาย codepoint.
    opcodes = difflib.SequenceMatcher(a=list(raw), b=list(expected), autojunk=False).get_opcodes()
    align_rows = []
    candidates: dict[tuple[str, str], dict[str, object]] = {}
    for n, (tag, i1, i2, j1, j2) in enumerate(opcodes, 1):
        raw_part = raw[i1:i2]
        expected_part = expected[j1:j2]
        align_rows.append({
            "segment": n, "operation": tag, "raw_start": i1, "raw_end": i2,
            "raw_text": raw_part, "raw_codepoints": esc(raw_part),
            "expected_start": j1, "expected_end": j2, "expected_text": expected_part,
            "expected_codepoints": esc(expected_part),
        })
        if tag != "equal" and pua_chars(raw_part):
            for pua in pua_chars(raw_part):
                key = (pua, raw_part)
                item = candidates.setdefault(key, {
                    "PUACodepoint": f"U+{ord(pua):04X}", "RawCluster": raw_part,
                    "ExpectedUnicodeSequenceCandidate": expected_part,
                    "OccurrenceCountInOpening": 0,
                })
                item["OccurrenceCountInOpening"] = int(item["OccurrenceCountInOpening"]) + raw_part.count(pua)

    with (args.output_dir / "opening_alignment.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(align_rows[0]))
        writer.writeheader(); writer.writerows(align_rows)

    font = ImageFont.truetype(str(args.font), size=112, layout_engine=ImageFont.Layout.RAQM)
    corpus_by_pua: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for corpus_row in thai_rows:
        text = corpus_row["ThaiTextRaw"]
        for pua in set(pua_chars(text)):
            for index, ch in enumerate(text):
                if ch == pua:
                    corpus_by_pua[pua].append((corpus_row["SelfId"], text[max(0, index - 5): index + 6]))

    result_rows = []
    for number, item in enumerate(candidates.values(), 1):
        raw_cluster = str(item["RawCluster"])
        target_cluster = str(item["ExpectedUnicodeSequenceCandidate"])
        image_path = font_dir / f"cluster_{number:02d}_{item['PUACodepoint'].replace('+', '')}.png"
        visual_status, score, raw_width, expected_width = visual_evidence(font, raw_cluster, target_cluster, image_path)
        pua = chr(int(str(item["PUACodepoint"])[2:], 16))
        contexts = corpus_by_pua[pua]
        item.update({
            "FontEvidence": visual_status,
            "VisualSimilarity": f"{score:.6f}",
            "RawClusterWidth": raw_width,
            "ExpectedClusterWidth": expected_width,
            "CorpusOccurrenceCount": len(contexts),
            "DistinctRawContexts": len({context for _, context in contexts}),
            "CorpusConsistency": "INSUFFICIENT_NO_INDEPENDENT_TEXT",
            "RuleStatus": "CONFIRMED_OPENING_LOCAL" if visual_status in {"SUPPORTS", "NONCONTRADICTORY"} else "PROBABLE_OPENING_LOCAL",
        })
        result_rows.append(item)

    fields = ["PUACodepoint", "RawCluster", "ExpectedUnicodeSequenceCandidate", "OccurrenceCountInOpening", "FontEvidence", "VisualSimilarity", "RawClusterWidth", "ExpectedClusterWidth", "CorpusOccurrenceCount", "DistinctRawContexts", "CorpusConsistency", "RuleStatus"]
    with (args.output_dir / "cluster_mapping_candidates.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(result_rows)

    # Candidate สำหรับการตรวจ runtime ต่อเนื่อง: ใช้ asset เดียวกับ SelfId ที่ยืนยันแล้วเท่านั้น.
    asset = next(r["DataTableAsset"] for r in english_rows if r["SelfId"] == args.self_id)
    thai_by_id = {r["SelfId"]: r for r in thai_rows if r["DataTableAsset"] == asset}
    sequence_rows = []
    for r in english_rows:
        if r["DataTableAsset"] != asset:
            continue
        t = thai_by_id.get(r["SelfId"])
        text = t["ThaiTextRaw"] if t else ""
        sequence_rows.append({
            "SelfId": r["SelfId"], "EnglishText": r["EnglishText"], "ThaiTextRaw": text,
            "PUACount": len(pua_chars(text)),
            "NeedsHumanVerification": "NO" if r["SelfId"] == args.self_id else "YES",
        })
    with (args.output_dir / "opening_sequence_candidates.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["SelfId", "EnglishText", "ThaiTextRaw", "PUACount", "NeedsHumanVerification"])
        writer.writeheader(); writer.writerows(sequence_rows)

    # ความสำเร็จจำกัดเฉพาะคู่ที่ผู้ใช้ยืนยัน และต้องไม่มี operation ที่แก้ raw โดยไม่มี PUA.
    unexplained = [r for r in align_rows if r["operation"] != "equal" and not pua_chars(r["raw_text"])]
    exact = "YES" if not unexplained else "NO"
    print(f"OPENING_EXACT_DECODE={exact}")
    print(f"PUA_OCCURRENCES={sum(len(pua_chars(r['raw_text'])) for r in align_rows if r['operation'] != 'equal')}")
    print(f"RULES={len(result_rows)}")


if __name__ == "__main__":
    main()
