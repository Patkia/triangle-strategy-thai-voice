#!/usr/bin/env python3
"""ถอดเสียง WAV ภาษาอังกฤษแบบ local ด้วย Whisper และเก็บผลเป็น CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--model", default="base.en")
    parser.add_argument("--model-cache", required=True, type=Path)
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        print(f"ไม่พบ input directory: {args.input_dir}", file=sys.stderr)
        return 2

    wavs = sorted(args.input_dir.glob("*.wav"))
    if not wavs:
        print(f"ไม่พบไฟล์ WAV: {args.input_dir}", file=sys.stderr)
        return 2

    import whisper

    args.model_cache.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    model = whisper.load_model(args.model, download_root=str(args.model_cache))

    rows = []
    for index, wav in enumerate(wavs, start=1):
        print(f"[{index}/{len(wavs)}] {wav.name}", flush=True)
        try:
            result = model.transcribe(
                str(wav), language="en", task="transcribe", fp16=False,
                temperature=0, condition_on_previous_text=False, verbose=False,
            )
            text = " ".join(result.get("text", "").split())
            rows.append({"wav_path": str(wav), "transcription": text, "error": ""})
        except Exception as exc:  # สรุปข้อผิดพลาดรายไฟล์โดยไม่ทิ้งทั้งชุด
            rows.append({"wav_path": str(wav), "transcription": "", "error": repr(exc)})

    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["wav_path", "transcription", "error"])
        writer.writeheader()
        writer.writerows(rows)

    failures = sum(bool(row["error"]) for row in rows)
    print(f"saved {len(rows)} rows, errors {failures}: {args.output_csv}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
