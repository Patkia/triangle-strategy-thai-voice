import csv
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "Output/Exports/Newera/Content/Newera/Sound/VOICE/EN/MS01_EN.json"
AWB_PATH = ROOT / "work/opening_voice_candidates/MS01_EN.awb"
VGMSTREAM = ROOT / "vgmstream-win64/vgmstream-cli.exe"
OUT_DIR = ROOT / "work/opening_voice_candidates"
WAV_DIR = OUT_DIR / "wav"
INVENTORY = OUT_DIR / "ms01_cue_inventory.csv"
CANDIDATES = OUT_DIR / "opening_candidates.csv"
REPORT = OUT_DIR / "analysis_report.json"


def run_vgmstream(*args):
    return subprocess.run(
        [str(VGMSTREAM), *map(str, args)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout


def stream_metadata(index):
    output = run_vgmstream("-m", "-s", index, AWB_PATH)
    samples = int(re.search(r"play duration: (\d+) samples", output).group(1))
    rate = int(re.search(r"sample rate: (\d+) Hz", output).group(1))
    channels = int(re.search(r"channels: (\d+)", output).group(1))
    return samples, rate, channels


def main():
    if not JSON_PATH.is_file() or not AWB_PATH.is_file() or not VGMSTREAM.is_file():
        raise SystemExit("ไม่พบ JSON, AWB หรือ vgmstream-cli ที่ต้องใช้")
    raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    sheet = raw[0] if isinstance(raw, list) else raw
    properties = sheet["Properties"]
    cues = properties["CueInfos"]
    total_metadata = run_vgmstream("-m", AWB_PATH)
    stream_count = int(re.search(r"stream count: (\d+)", total_metadata).group(1))
    if len(cues) != stream_count:
        raise SystemExit(f"CueInfos={len(cues)} แต่ AWB streams={stream_count}")

    rows = []
    for cue in cues:
        stream_index = int(cue["Id"]) + 1
        samples, rate, channels = stream_metadata(stream_index)
        audio_seconds = samples / rate
        ticks = int(cue["Duration"]["Ticks"])
        cue_seconds = ticks / 10_000_000
        delta = abs(cue_seconds - audio_seconds)
        duration_status = (
            "duration สอดคล้องภายใน 1 ms; ลำดับสมมติ Id+1 ยังไม่มี waveform ยืนยัน"
            if delta <= 0.001
            else "duration ไม่สอดคล้อง; ห้ามถือว่า Id+1 เป็น mapping ที่ยืนยันแล้ว"
        )
        rows.append({
            "cue_id": cue["Id"],
            "cue_name": cue["Name"],
            "awb_stream_index": stream_index,
            "cue_duration_seconds": f"{cue_seconds:.6f}",
            "audio_duration_seconds": f"{audio_seconds:.6f}",
            "duration_delta_seconds": f"{delta:.6f}",
            "audio_samples": samples,
            "sample_rate": rate,
            "channels": channels,
            "categories": " | ".join(cue.get("CategoryNames", [])),
            "mapping_status": duration_status,
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    WAV_DIR.mkdir(parents=True, exist_ok=True)
    with INVENTORY.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    listening_rows = []
    for row in rows[:10]:
        filename = f"candidate_{row['awb_stream_index']:03d}_id{int(row['cue_id']):03d}_{row['cue_name']}.wav"
        output = WAV_DIR / filename
        run_vgmstream("-s", row["awb_stream_index"], "-o", output, AWB_PATH)
        listening_rows.append({
            "rank": len(listening_rows) + 1,
            "cue_id": row["cue_id"],
            "cue_name": row["cue_name"],
            "awb_stream_index": row["awb_stream_index"],
            "wav_file": str(output.relative_to(ROOT)).replace("\\", "/"),
            "duration_seconds": row["audio_duration_seconds"],
            "selection_basis": "10 CueInfo แรกของ MS01_X01_A0_0020 ตามลำดับ cue ID; ต้องฟังเทียบในเกม",
            "mapping_confidence": "provisional — duration/order only",
        })
    with CANDIDATES.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(listening_rows[0]))
        writer.writeheader()
        writer.writerows(listening_rows)

    mismatches = sum(float(row["duration_delta_seconds"]) > 0.001 for row in rows)
    REPORT.write_text(json.dumps({
        "cue_sheet": properties.get("CueSheetName"),
        "cue_infos": len(cues),
        "awb_streams": stream_count,
        "awb_directory": properties.get("AwbDirectory"),
        "duration_mismatches_over_1ms": mismatches,
        "duration_matches_within_1ms": len(rows) - mismatches,
        "listening_candidates": len(listening_rows),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(json.loads(REPORT.read_text(encoding="utf-8")), ensure_ascii=False))


if __name__ == "__main__":
    main()
