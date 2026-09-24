from __future__ import annotations

import csv
import os
import subprocess
import sys
import tempfile
import time
import winsound
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "work" / "battle_voice_mapping" / "battle_voice_cues_with_text.csv"
VGMSTREAM = ROOT / "vgmstream-win64" / "vgmstream-cli.exe"

CLASS_CHOICES = {
    "a": ("ATTACK_CRY", ["ย๊าก!", "ฮ่า!", "ฮึ่ย!", "ฮ้า!", "เอ้า!"]),
    "h": ("HURT_CRY", ["อึก!", "อั่ก!", "โอ๊ย!", "อ๊าก!", "อึ่ก!"]),
    "e": ("EVADE_GUARD", ["ฮึบ!", "หึ!", "ฮ่า!"]),
    "s": ("STATUS_REACTION", ["อึก...", "อูย...", "อั่ก..."]),
}


def read_csv() -> tuple[list[dict[str, str]], list[str]]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        fields = list(reader.fieldnames or [])
    return rows, fields


def write_csv(rows: list[dict[str, str]], fields: list[str]) -> None:
    temp = CSV_PATH.with_suffix(CSV_PATH.suffix + f".{os.getpid()}.tmp")
    try:
        with temp.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        for attempt in range(5):
            try:
                os.replace(temp, CSV_PATH)
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.15)
    finally:
        temp.unlink(missing_ok=True)


def decode_wav(row: dict[str, str], out_wav: Path) -> None:
    awb = ROOT / row["awb_path"]
    stream = row["awb_stream"]
    if not awb.exists():
        raise FileNotFoundError(f"AWB not found: {awb}")
    subprocess.run(
        [str(VGMSTREAM), "-i", "-W", "1", "-s", str(stream), "-o", str(out_wav), str(awb)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def play_wav(path: Path) -> None:
    winsound.PlaySound(str(path), winsound.SND_FILENAME)


def print_row(row: dict[str, str], pos: int, total: int) -> None:
    print("\n" + "=" * 72)
    print(f"[{pos}/{total}] {row.get('cue_name', '')}")
    print(f"Character : {row.get('character_name', '')} ({row.get('voice_target', '')})")
    print(f"Cue ID    : {row.get('battle_cue_id', '')}")
    print(f"Duration  : {row.get('audio_duration_sec', '')} sec")
    print(f"Current   : {row.get('battle_cry_class', '')} | {row.get('thai_battle_cry', '')}")
    print(f"AWB       : {row.get('awb_path', '')}")
    print(f"Stream    : {row.get('awb_stream', '')}")


def choose_phrase(class_key: str) -> tuple[str, str] | None:
    class_name, phrases = CLASS_CHOICES[class_key]
    print(f"\n{class_name}")
    for i, phrase in enumerate(phrases, start=1):
        print(f"  {i}. {phrase}")
    print("  c. พิมพ์คำเอง")
    print("  x. ยกเลิก")
    while True:
        choice = input("เลือกคำ: ").strip().lower()
        if choice == "x":
            return None
        if choice == "c":
            text = input("คำอุทานไทย: ").strip()
            if text:
                return class_name, text
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(phrases):
            return class_name, phrases[int(choice) - 1]
        print("เลือกไม่ถูกต้อง")


def main() -> int:
    # Force UTF-8 for Thai prompts on Windows CMD and redirected output.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")
    if not CSV_PATH.exists():
        print(f"CSV not found: {CSV_PATH}")
        return 2
    if not VGMSTREAM.exists():
        print(f"vgmstream-cli not found: {VGMSTREAM}")
        return 2

    rows, fields = read_csv()
    required = {"battle_cry_class", "thai_battle_cry", "awb_path", "awb_stream"}
    missing = sorted(required - set(fields))
    if missing:
        print(f"CSV missing columns: {', '.join(missing)}")
        return 2

    pending_indices = [
        i
        for i, row in enumerate(rows)
        if row.get("transcript_status") == "NONVERBAL_BATTLE_CRY"
        and row.get("battle_cry_class") == "SPECIAL_REVIEW"
    ]

    if not pending_indices:
        print("No SPECIAL_REVIEW battle cries remaining.")
        return 0

    print(f"SPECIAL_REVIEW remaining: {len(pending_indices)}")
    print("Commands: Enter/p=play, a=attack, h=hurt, e=evade/guard, s=status, c=custom, n=next, b=back, q=save+quit")

    cursor = 0
    dirty = False
    with tempfile.TemporaryDirectory(prefix="battle_cry_review_") as tmp_dir:
        tmp = Path(tmp_dir)
        cached: dict[int, Path] = {}

        while 0 <= cursor < len(pending_indices):
            row_index = pending_indices[cursor]
            row = rows[row_index]
            print_row(row, cursor + 1, len(pending_indices))

            def ensure_audio() -> Path:
                if row_index not in cached:
                    wav = tmp / f"{cursor:03d}_{row.get('cue_name', 'review')}.wav"
                    print("Decoding audio...")
                    decode_wav(row, wav)
                    cached[row_index] = wav
                return cached[row_index]

            command = input("\nคำสั่ง [Enter=play]: ").strip().lower()
            if command in {"", "p"}:
                try:
                    play_wav(ensure_audio())
                except Exception as exc:
                    print(f"PLAY ERROR: {exc}")
                continue

            if command in CLASS_CHOICES:
                result = choose_phrase(command)
                if result is not None:
                    row["battle_cry_class"], row["thai_battle_cry"] = result
                    dirty = True
                    print(f"Saved: {row['battle_cry_class']} | {row['thai_battle_cry']}")
                    cursor += 1
                continue

            if command == "c":
                class_name = input("battle_cry_class: ").strip()
                thai_text = input("thai_battle_cry: ").strip()
                if class_name and thai_text:
                    row["battle_cry_class"] = class_name
                    row["thai_battle_cry"] = thai_text
                    dirty = True
                    print(f"Saved: {class_name} | {thai_text}")
                    cursor += 1
                else:
                    print("ยกเลิก: ต้องกรอกทั้ง class และข้อความ")
                continue

            if command == "n":
                cursor += 1
                continue
            if command == "b":
                cursor = max(0, cursor - 1)
                continue
            if command == "q":
                break

            print("คำสั่งไม่ถูกต้อง")

    if dirty:
        write_csv(rows, fields)
        print(f"\nSaved changes to: {CSV_PATH}")
    else:
        print("\nNo changes made.")

    remaining = sum(
        1
        for row in rows
        if row.get("transcript_status") == "NONVERBAL_BATTLE_CRY"
        and row.get("battle_cry_class") == "SPECIAL_REVIEW"
    )
    print(f"SPECIAL_REVIEW remaining: {remaining}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
