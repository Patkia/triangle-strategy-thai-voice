import csv
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "work/narrator_listening"
VGM = ROOT / "vgmstream-win64/vgmstream-cli.exe"
DEC_JSON = ROOT / "Output/Exports/Newera/Content/Newera/Sound/VOICE/EN/V_N_DEC_EN.json"
BANKS = ("V_N_DEC_EN", "V_M_NAR_EN")


def metadata(bank, index=1):
    text = subprocess.run(
        [str(VGM), "-m", "-s", str(index), str(BASE / f"{bank}.awb")],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout
    value = lambda pattern: re.search(pattern, text).group(1)
    return {
        "stream_count": int(value(r"stream count: (\d+)")),
        "sample_rate": int(value(r"sample rate: (\d+) Hz")),
        "channels": int(value(r"channels: (\d+)")),
        "total_samples": int(value(r"play duration: (\d+) samples")),
        "encoding": value(r"encoding: (.+)"),
    }


def main():
    BASE.mkdir(parents=True, exist_ok=True)
    bank_rows = []
    for bank in BANKS:
        data = metadata(bank)
        bank_rows.append({"bank": bank, **data, "awb_file": f"{bank}.awb"})
    with (BASE / "bank_metadata.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(bank_rows[0]))
        writer.writeheader(); writer.writerows(bank_rows)

    raw = json.loads(DEC_JSON.read_text(encoding="utf-8"))
    sheet = raw[0] if isinstance(raw, list) else raw
    cues = sheet["Properties"]["CueInfos"]
    dec_rows = []
    for cue in cues:
        index = int(cue["Id"]) + 1
        audio = metadata("V_N_DEC_EN", index)
        duration = audio["total_samples"] / audio["sample_rate"]
        expected = int(cue["Duration"]["Ticks"]) / 10_000_000
        dec_rows.append({
            "cue_id": cue["Id"], "cue_name": cue["Name"], "awb_stream_index": index,
            "cue_duration_seconds": f"{expected:.6f}", "audio_duration_seconds": f"{duration:.6f}",
            "duration_delta_seconds": f"{abs(expected-duration):.6f}",
            "categories": " | ".join(cue.get("CategoryNames", [])),
        })
    with (BASE / "v_n_dec_cue_inventory.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dec_rows[0]))
        writer.writeheader(); writer.writerows(dec_rows)

    stream_rows = []
    for index in range(1, bank_rows[1]["stream_count"] + 1):
        info = metadata("V_M_NAR_EN", index)
        stream_rows.append({
            "bank": "V_M_NAR_EN", "awb_stream_index": index,
            "duration_seconds": info["total_samples"] / info["sample_rate"],
            "sample_count": info["total_samples"],
        })
    with (BASE / "v_m_nar_stream_inventory.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(stream_rows[0]))
        writer.writeheader(); writer.writerows(stream_rows)

    wav_dir = BASE / "V_M_NAR_EN_WAV"
    wav_dir.mkdir(exist_ok=True)
    listening = []
    for priority, stream in enumerate(sorted(stream_rows, key=lambda row: row["duration_seconds"], reverse=True)[:5], start=1):
        index = stream["awb_stream_index"]
        output = wav_dir / f"V_M_NAR_EN__stream{index:03d}.wav"
        subprocess.run([str(VGM), "-s", str(index), "-o", str(output), str(BASE / "V_M_NAR_EN.awb")], check=True)
        listening.append({
            "priority": priority, "bank": "V_M_NAR_EN", "cue_id": "",
            "awb_stream_index": index, "wav_file": str(output.relative_to(ROOT)).replace("\\", "/"),
            "duration_seconds": f"{stream['duration_seconds']:.6f}",
            "evidence": "bank ชื่อมี NAR; เลือกจาก 5 streams ที่ยาวที่สุดเพราะ target เป็นประโยคเต็ม; ไม่มี CueSheet JSON",
            "confidence": "low — ฟังเพื่อคัดกรองเท่านั้น",
        })
    with (BASE / "listening_candidates.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(listening[0]))
        writer.writeheader(); writer.writerows(listening)
    print(f"v_n_dec_cues={len(cues)} v_m_nar_listening_wavs={len(listening)}")


if __name__ == "__main__":
    main()
