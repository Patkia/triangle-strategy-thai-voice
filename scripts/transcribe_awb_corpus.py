#!/usr/bin/env python3
"""สแกน AWB ภาษาอังกฤษด้วย Whisper แบบ resumable โดยเก็บผล transcript ราย stream."""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

TARGET_WORDS = ("norzelia", "faraway", "continent", "three", "mighty", "powers", "reigned")


def score_text(text: str) -> tuple[int, list[str]]:
    normalized = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    hits = [word for word in TARGET_WORDS if word in normalized]
    score = sum(5 if word == "norzelia" else 3 if word in {"faraway", "continent"} else 1 for word in hits)
    return score, hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank-metadata", required=True, type=Path)
    parser.add_argument("--awb-dir", required=True, type=Path)
    parser.add_argument("--vgmstream", required=True, type=Path)
    parser.add_argument("--model-cache", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--temp-dir", required=True, type=Path)
    parser.add_argument("--final-wav", required=True, type=Path)
    parser.add_argument("--model", default="tiny.en")
    args = parser.parse_args()
    if not args.bank_metadata.is_file() or not args.vgmstream.is_file():
        print("missing metadata or vgmstream", file=sys.stderr)
        return 2

    with args.bank_metadata.open(encoding="utf-8-sig", newline="") as handle:
        banks = list(csv.DictReader(handle))
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.temp_dir.mkdir(parents=True, exist_ok=True)
    args.model_cache.mkdir(parents=True, exist_ok=True)

    completed: set[tuple[str, str]] = set()
    if args.output_csv.exists():
        with args.output_csv.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                completed.add((row["bank"], row["stream_index"]))

    import whisper
    model = whisper.load_model(args.model, download_root=str(args.model_cache))
    write_header = not args.output_csv.exists()
    with args.output_csv.open("a", encoding="utf-8", newline="") as result_file:
        fields = ["bank", "stream_index", "awb_path", "transcription", "score", "hits", "error"]
        writer = csv.DictWriter(result_file, fieldnames=fields)
        if write_header:
            writer.writeheader()
        for bank in banks:
            name = bank["bank_name"]
            if name in {"MS01_EN", "V_M_NAR_EN", "V_N_DEC_EN"}:
                continue
            awb = args.awb_dir / (name + ".awb")
            count = int(bank["awb_stream_count"])
            if not awb.is_file():
                print("MISSING " + str(awb), flush=True)
                continue
            for index in range(1, count + 1):
                key = (name, str(index))
                if key in completed:
                    continue
                wav = args.temp_dir / (name + "__stream%03d.wav" % index)
                print(name + " stream " + str(index), flush=True)
                transcription = ""
                error = ""
                try:
                    decoded = subprocess.run([str(args.vgmstream), "-s", str(index), "-o", str(wav), str(awb)], capture_output=True, text=True)
                    if decoded.returncode != 0:
                        raise RuntimeError(decoded.stderr or decoded.stdout)
                    transcription = " ".join(model.transcribe(str(wav), language="en", task="transcribe", fp16=False, temperature=0, condition_on_previous_text=False, verbose=False).get("text", "").split())
                except Exception as exc:
                    error = repr(exc)
                finally:
                    score, hits = score_text(transcription)
                    writer.writerow({"bank": name, "stream_index": index, "awb_path": str(awb), "transcription": transcription, "score": score, "hits": ",".join(hits), "error": error})
                    result_file.flush()
                    if not error and "norzelia" in hits and len(hits) >= 5:
                        args.final_wav.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(wav, args.final_wav)
                        print("STRONG_MATCH " + name + " stream " + str(index), flush=True)
                        return 0
                    wav.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
