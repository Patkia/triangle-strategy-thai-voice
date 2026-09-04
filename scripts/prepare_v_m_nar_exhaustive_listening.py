import csv
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "work/narrator_listening"
AWB = BASE / "V_M_NAR_EN.awb"
VGM = ROOT / "vgmstream-win64/vgmstream-cli.exe"
OUT = BASE / "V_M_NAR_EN_ALL_WAV"
INDEX = BASE / "v_m_nar_all_streams.csv"
ORDER = BASE / "listening_order.txt"
PLAYLIST = BASE / "listening_order.m3u"
TESTED = {73, 44, 45, 70, 3}


def get_duration(index):
    result = subprocess.run(
        [str(VGM), "-m", "-s", str(index), str(AWB)],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout
    samples = int(re.search(r"play duration: (\d+) samples", result).group(1))
    rate = int(re.search(r"sample rate: (\d+) Hz", result).group(1))
    count = int(re.search(r"stream count: (\d+)", result).group(1))
    return samples / rate, count


def main():
    if not AWB.is_file():
        raise SystemExit(f"ไม่พบ AWB: {AWB}")
    OUT.mkdir(parents=True, exist_ok=True)
    _, stream_count = get_duration(1)
    rows = []
    for index in range(1, stream_count + 1):
        duration, _ = get_duration(index)
        wav = OUT / f"V_M_NAR_EN__stream{index:03d}.wav"
        if not wav.exists() or wav.stat().st_size == 0:
            subprocess.run([str(VGM), "-s", str(index), "-o", str(wav), str(AWB)], check=True)
        tested = index in TESTED
        rows.append({
            "stream_index": index,
            "duration": f"{duration:.6f}",
            "wav_path": str(wav.relative_to(ROOT)).replace("\\", "/"),
            "already_tested": "YES" if tested else "NO",
            "human_result": "NONE_MATCH" if tested else "",
        })
    with INDEX.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    untested = [row for row in rows if row["already_tested"] == "NO"]
    ordered = sorted(untested, key=lambda row: float(row["duration"]), reverse=True)
    ORDER.write_text(
        "# ลำดับที่แนะนำ: streams ที่ยังไม่ฟัง เรียง duration มากไปน้อย\n"
        "# 5 streams ที่ฟังแล้วและไม่ตรง: 073, 044, 045, 070, 003\n\n"
        + "\n".join(row["wav_path"] for row in ordered)
        + "\n",
        encoding="utf-8",
    )
    PLAYLIST.write_text("\n".join(str(ROOT / row["wav_path"]) for row in ordered) + "\n", encoding="utf-8")
    print(f"streams={stream_count} decoded={sum((OUT / f'V_M_NAR_EN__stream{i:03d}.wav').is_file() for i in range(1, stream_count + 1))} tested={len(TESTED)} remaining={len(untested)}")


if __name__ == "__main__":
    main()
