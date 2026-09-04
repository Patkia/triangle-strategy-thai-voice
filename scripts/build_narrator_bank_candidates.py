import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH_LIST = ROOT / "work/opening_voice_candidates/voice_en_paths.txt"
INVENTORY = ROOT / "work/en_voice_bank_inventory.csv"
CANDIDATES = ROOT / "work/narrator_cuesheet_candidates.csv"


def main():
    paths = [line.strip() for line in PATH_LIST.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    cue_paths = {
        Path(path).stem: path
        for path in paths
        if path.startswith("Newera/Content/Newera/Sound/VOICE/EN/") and path.endswith(".uasset")
    }
    awb_paths = {
        Path(path).stem: path
        for path in paths
        if path.startswith("Newera/Content/Newera/Sound/Stream/VOICE/EN/") and path.endswith(".awb")
    }
    banks = sorted(set(cue_paths) | set(awb_paths))
    rows = [{
        "bank": bank,
        "cue_sheet_path": cue_paths.get(bank, ""),
        "awb_path": awb_paths.get(bank, ""),
        "pair_status": "paired" if bank in cue_paths and bank in awb_paths else "missing counterpart",
    } for bank in banks]
    if len(rows) != 125:
        raise SystemExit(f"คาดหวัง 125 banks แต่พบ {len(rows)}")
    with INVENTORY.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    candidate_specs = [
        ("V_N_DEC_EN", 1, "ชื่อมี token V_N ซึ่งแตกต่างจาก bank ตัวละครแบบ V_M/V_F; เป็นเพียง naming hypothesis"),
        ("V_M_NAR_EN", 2, "ชื่อมี token NAR; เป็นเพียง naming hypothesis และ prefix V_M ทำให้ระบุบทบาทไม่ได้"),
    ]
    output = []
    for bank, rank, reason in candidate_specs:
        output.append({
            "rank": rank,
            "bank": bank,
            "cue_sheet_path": cue_paths[bank],
            "awb_path": awb_paths[bank],
            "verified_evidence": "PAK index มี CueSheet .uasset และ AWB .awb ชื่อเดียวกัน",
            "naming_hypothesis": reason,
            "confidence": "low — ยังไม่มี CueInfo/ข้อความหรือ waveform ยืนยัน",
        })
    with CANDIDATES.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    print(f"banks={len(rows)} paired={sum(row['pair_status'] == 'paired' for row in rows)} candidates={len(output)}")


if __name__ == "__main__":
    main()
