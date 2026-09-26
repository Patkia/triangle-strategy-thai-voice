from __future__ import annotations

import argparse
import csv
import os
import sys
import wave
import winsound
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "work" / "chapter0_voice_mapping" / "chapter0_omnivoice_studio.csv"
SAMPLE_RATE = 48_000
CHANNELS = 1
SAMPLE_WIDTH = 2  # PCM16


def load_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    required = {"file_name", "thai_text"}
    if not rows:
        raise RuntimeError(f"CSV has no rows: {csv_path}")
    missing = required - set(rows[0])
    if missing:
        raise RuntimeError(f"CSV missing columns: {', '.join(sorted(missing))}")
    return rows


def dependency_status() -> tuple[bool, str]:
    missing: list[str] = []
    try:
        import numpy  # noqa: F401
    except ImportError:
        missing.append("numpy")
    try:
        import sounddevice  # noqa: F401
    except ImportError:
        missing.append("sounddevice")
    if missing:
        return False, "Missing: " + ", ".join(missing)
    return True, "Recorder dependencies: OK"


def validate_wav(path: Path) -> str:
    with wave.open(str(path), "rb") as wav:
        rate = wav.getframerate()
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        frames = wav.getnframes()
    seconds = frames / rate if rate else 0.0
    if rate != SAMPLE_RATE or channels != CHANNELS or width != SAMPLE_WIDTH:
        raise RuntimeError(
            f"Unexpected WAV format: {rate} Hz, {channels} ch, {width * 8} bit"
        )
    return f"{seconds:.2f}s | {rate} Hz | mono | PCM16"


def run_check(csv_path: Path, output_dir: Path) -> int:
    rows = load_rows(csv_path)
    output_dir = output_dir.resolve()
    existing = sum((output_dir / row["file_name"]).exists() for row in rows)
    deps_ok, deps_text = dependency_status()
    print(f"CSV: {csv_path}")
    print(f"Rows: {len(rows)}")
    print(f"Output: {output_dir}")
    print(f"Existing: {existing}/{len(rows)}")
    print(deps_text)
    if not deps_ok:
        print(f"Install once: {sys.executable} -m pip install numpy sounddevice")
    return 0


def run_gui(csv_path: Path, output_dir: Path) -> int:
    try:
        import tkinter as tk
        from tkinter import messagebox
    except ImportError as exc:
        print(f"Tkinter unavailable: {exc}")
        return 2

    deps_ok, deps_text = dependency_status()
    if not deps_ok:
        print(deps_text)
        print(f"Install once: {sys.executable} -m pip install numpy sounddevice")
        return 2

    import numpy as np
    import sounddevice as sd

    rows = load_rows(csv_path)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_path = output_dir / ".manual_recording_preview.wav"

    class RecorderApp:
        def __init__(self) -> None:
            self.root = tk.Tk()
            self.root.title("Triangle Strategy - Manual Voice Recorder")
            self.root.geometry("920x610")

            self.index = self.first_missing_index()
            self.stream = None
            self.chunks: list[np.ndarray] = []
            self.has_preview = False

            self.header = tk.Label(self.root, font=("Segoe UI", 14, "bold"), anchor="w")
            self.header.pack(fill="x", padx=18, pady=(16, 6))

            self.file_label = tk.Label(self.root, font=("Consolas", 10), anchor="w")
            self.file_label.pack(fill="x", padx=18, pady=4)

            self.text = tk.Text(self.root, wrap="word", height=10, font=("Tahoma", 20))
            self.text.pack(fill="both", expand=True, padx=18, pady=10)
            self.text.configure(state="disabled")

            self.status = tk.Label(self.root, font=("Segoe UI", 11, "bold"), anchor="w")
            self.status.pack(fill="x", padx=18, pady=6)

            controls = tk.Frame(self.root)
            controls.pack(fill="x", padx=18, pady=10)
            tk.Button(controls, text="◀ Back", command=self.back, width=11).pack(side="left", padx=3)
            tk.Button(controls, text="⏺ Start / Stop  [Space]", command=self.toggle_recording, width=22).pack(side="left", padx=3)
            tk.Button(controls, text="▶ Play  [P]", command=self.play, width=13).pack(side="left", padx=3)
            tk.Button(controls, text="✓ Approve + Next  [Enter]", command=self.approve, width=22).pack(side="left", padx=3)
            tk.Button(controls, text="Next ▶", command=self.next, width=11).pack(side="left", padx=3)

            help_text = (
                "Space = เริ่ม/หยุดอัด   P = ฟัง   Enter = ยืนยันแล้วไปบรรทัดถัดไป   "
                "←/→ = ก่อนหน้า/ถัดไป   Esc = ออกจากโปรแกรม"
            )
            tk.Label(self.root, text=help_text, anchor="w").pack(fill="x", padx=18, pady=(0, 12))

            self.root.bind("<space>", lambda _e: self.toggle_recording())
            self.root.bind("<p>", lambda _e: self.play())
            self.root.bind("<P>", lambda _e: self.play())
            self.root.bind("<Return>", lambda _e: self.approve())
            self.root.bind("<Left>", lambda _e: self.back())
            self.root.bind("<Right>", lambda _e: self.next())
            self.root.bind("<Escape>", lambda _e: self.close())
            self.root.protocol("WM_DELETE_WINDOW", self.close)

            self.refresh()

        def first_missing_index(self) -> int:
            for i, row in enumerate(rows):
                if not (output_dir / row["file_name"]).exists():
                    return i
            return 0

        @property
        def row(self) -> dict[str, str]:
            return rows[self.index]

        @property
        def target_path(self) -> Path:
            return output_dir / self.row["file_name"]

        def refresh(self) -> None:
            row = self.row
            completed = sum((output_dir / r["file_name"]).exists() for r in rows)
            who = row.get("character_name") or row.get("voice_target") or ""
            self.header.configure(text=f"[{self.index + 1}/{len(rows)}] {who}   |   completed {completed}/{len(rows)}")
            self.file_label.configure(text=row["file_name"])
            spoken = (row.get("tts_text") or row.get("thai_text") or "").strip()
            self.text.configure(state="normal")
            self.text.delete("1.0", "end")
            self.text.insert("1.0", spoken)
            self.text.configure(state="disabled")
            self.has_preview = preview_path.exists()
            if self.target_path.exists():
                try:
                    info = validate_wav(self.target_path)
                except Exception as exc:
                    info = f"existing WAV invalid: {exc}"
                self.status.configure(text=f"✓ มีไฟล์แล้ว | {info}")
            else:
                self.status.configure(text="ยังไม่ได้อัด | กด Space เพื่อเริ่ม")

        def audio_callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
            if status:
                print(status, file=sys.stderr)
            self.chunks.append(indata.copy())

        def toggle_recording(self) -> None:
            if self.stream is None:
                winsound.PlaySound(None, winsound.SND_PURGE)
                self.chunks = []
                preview_path.unlink(missing_ok=True)
                try:
                    self.stream = sd.InputStream(
                        samplerate=SAMPLE_RATE,
                        channels=CHANNELS,
                        dtype="float32",
                        callback=self.audio_callback,
                    )
                    self.stream.start()
                    self.status.configure(text="● กำลังอัด... กด Space อีกครั้งเพื่อหยุด")
                except Exception as exc:
                    self.stream = None
                    messagebox.showerror("Microphone error", str(exc))
                return

            self.stream.stop()
            self.stream.close()
            self.stream = None
            if not self.chunks:
                self.status.configure(text="ไม่ได้รับข้อมูลเสียง ลองอัดใหม่")
                return
            audio = np.concatenate(self.chunks, axis=0).reshape(-1)
            pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2")
            with wave.open(str(preview_path), "wb") as wav:
                wav.setnchannels(CHANNELS)
                wav.setsampwidth(SAMPLE_WIDTH)
                wav.setframerate(SAMPLE_RATE)
                wav.writeframes(pcm.tobytes())
            self.has_preview = True
            self.status.configure(text=f"อัดแล้ว {validate_wav(preview_path)} | กด P ฟัง หรือ Enter ยืนยัน")

        def play(self) -> None:
            path = preview_path if preview_path.exists() else self.target_path
            if not path.exists():
                self.status.configure(text="ยังไม่มีเสียงให้ฟัง")
                return
            winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)

        def approve(self) -> None:
            if self.stream is not None:
                self.toggle_recording()
                return
            if preview_path.exists():
                os.replace(preview_path, self.target_path)
                self.has_preview = False
            elif not self.target_path.exists():
                self.status.configure(text="ยังไม่ได้อัดเสียง")
                return
            validate_wav(self.target_path)
            self.goto_next_missing()

        def goto_next_missing(self) -> None:
            for step in range(1, len(rows) + 1):
                candidate = (self.index + step) % len(rows)
                if not (output_dir / rows[candidate]["file_name"]).exists():
                    self.index = candidate
                    self.refresh()
                    return
            self.refresh()
            messagebox.showinfo("เสร็จแล้ว", f"Chapter 0 ครบ {len(rows)}/{len(rows)} ไฟล์แล้ว")

        def back(self) -> None:
            if self.stream is not None:
                return
            preview_path.unlink(missing_ok=True)
            self.index = max(0, self.index - 1)
            self.refresh()

        def next(self) -> None:
            if self.stream is not None:
                return
            preview_path.unlink(missing_ok=True)
            self.index = min(len(rows) - 1, self.index + 1)
            self.refresh()

        def close(self) -> None:
            if self.stream is not None:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            winsound.PlaySound(None, winsound.SND_PURGE)
            preview_path.unlink(missing_ok=True)
            self.root.destroy()

        def run(self) -> None:
            self.root.mainloop()

    RecorderApp().run()
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manual Thai voice recorder for Triangle Strategy CSV rows")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Studio CSV to record")
    parser.add_argument("--output", type=Path, default=None, help="Recording output directory (default: <CSV folder>/manual_input_wav)")
    parser.add_argument("--check", action="store_true", help="Validate CSV/dependencies without opening the recorder")
    return parser.parse_args()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    csv_path = args.csv.resolve()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 2
    output_dir = (args.output.resolve() if args.output else (csv_path.parent / "manual_input_wav").resolve())
    if args.check:
        return run_check(csv_path, output_dir)
    return run_gui(csv_path, output_dir)


if __name__ == "__main__":
    raise SystemExit(main())
