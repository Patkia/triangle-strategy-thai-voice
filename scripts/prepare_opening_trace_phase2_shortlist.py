import csv
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "Output/Exports/Newera/Content/Newera/Sound/VOICE/EN/MS01_EN.json"
STREAM_CSV = ROOT / "work/opening_trace_phase2/en_voice_stream_metadata.csv"
AWB_PATH = ROOT / "work/opening_voice_candidates/MS01_EN.awb"
VGMSTREAM = ROOT / "vgmstream-win64/vgmstream-cli.exe"
OUT = ROOT / "work/opening_trace_phase2"
WAV_DIR = OUT / "wav"


def load_json(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return data[0] if isinstance(data, list) else data


def main():
    sheet = load_json(JSON_PATH)
    cues = [x for x in sheet["Properties"]["CueInfos"] if "MS01_X01_WD_0020" in x.get("Name", "")]
    streams = list(csv.DictReader(STREAM_CSV.open(encoding="utf-8-sig")))
    streams = [x for x in streams if x["bank_name"] == "MS01_EN"]
    rows = []
    WAV_DIR.mkdir(parents=True, exist_ok=True)
    for priority, cue in enumerate(cues, 1):
        cue_seconds = int(cue["Duration"]["Ticks"]) / 10_000_000
        matches = [x for x in streams if abs(float(x["duration_seconds"]) - cue_seconds) <= 0.001]
        if len(matches) != 1:
            raise RuntimeError(f"ไม่พบ stream ที่ตรงแบบหนึ่งต่อหนึ่งสำหรับ {cue['Name']}: {len(matches)} รายการ")
        stream = matches[0]
        index = int(stream["stream_index"])
        filename = f"MS01_EN__cue{int(cue['Id']):03d}__stream{index:03d}__{cue['Name']}.wav"
        output = WAV_DIR / filename
        if not output.is_file() or output.stat().st_size == 0:
            subprocess.run([str(VGMSTREAM), "-s", str(index), "-o", str(output), str(AWB_PATH)], check=True)
        rows.append({
            "priority": priority,
            "bank": "MS01_EN",
            "cue_id": cue["Id"],
            "cue_name": cue["Name"],
            "stream_index": index,
            "cue_duration_seconds": f"{cue_seconds:.6f}",
            "audio_duration_seconds": f"{float(stream['duration_seconds']):.6f}",
            "duration_delta_seconds": f"{abs(float(stream['duration_seconds']) - cue_seconds):.6f}",
            "wav_path": str(output.relative_to(ROOT)).replace("\\", "/"),
            "related_assets": "Sequence/WorldMap/Story/ms01_x01/LS_WM_ms01_x01_wd_0020; DataTables/Scenario/Main/ms01_x01/ms01_x01_wd_0020",
            "evidence": "cue prefix ตรงกับ sequence และ scenario asset; มี stream ที่ duration ตรงหนึ่งต่อหนึ่งภายใน 1 ms",
            "confidence": "สูงสำหรับ Human Listening; ยังไม่ยืนยันข้อความจนกว่าจะฟัง",
        })
    with (OUT / "opening_shortlist.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Prepared WAV and CSV for {len(rows)} candidates")


if __name__ == "__main__":
    main()
