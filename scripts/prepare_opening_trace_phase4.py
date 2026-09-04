import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "Output/Exports"
OUT = ROOT / "work/opening_trace_phase4"


def find_exact(filename):
    matches = list(EXPORTS.rglob(filename))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {filename}, found {len(matches)}")
    return matches[0]


def load(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    return value[0] if isinstance(value, list) else value


def main():
    text_path = find_exact("Text_ms01_x01_wd_0010.json")
    nar_path = find_exact("V_M_NAR_EN.json")
    text_data = load(text_path)
    nar_data = load(nar_path)
    rows = []
    for order, (row_key, row) in enumerate(text_data["Rows"].items(), 1):
        rows.append({
            "order": order,
            "row_key": row_key,
            "self_id": row.get("SelfId", ""),
            "text": row.get("Text", ""),
            "event": "MS01_X01_WD_0010",
            "cue_name": row.get("SelfId", ""),
        })
    props = nar_data["Properties"]
    cue_rows = []
    categories = Counter()
    for cue in props["CueInfos"]:
        cats = " | ".join(cue.get("CategoryNames", []))
        categories[cats] += 1
        cue_rows.append({
            "cue_id": cue["Id"],
            "cue_name": cue["Name"],
            "duration_ticks": cue["Duration"]["Ticks"],
            "duration_seconds": f"{cue['Duration']['Ticks'] / 10_000_000:.6f}",
            "categories": cats,
            "looping": cue.get("bLooping", ""),
            "min_distance": cue.get("AttenuationDistance", {}).get("MinDistance", ""),
            "max_distance": cue.get("AttenuationDistance", {}).get("MaxDistance", ""),
        })
    OUT.mkdir(parents=True, exist_ok=True)
    for path, data in [(OUT / "opening_text_rows.csv", rows), (OUT / "v_m_nar_inventory.csv", cue_rows)]:
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    target_prefix = "MS01_X01_WD_0010"
    target_cues = [x for x in cue_rows if target_prefix in x["cue_name"]]
    summary = {
        "text_json": str(text_path.relative_to(ROOT)).replace("\\", "/"),
        "v_m_nar_json": str(nar_path.relative_to(ROOT)).replace("\\", "/"),
        "text_rows": len(rows),
        "v_m_nar_cue_count": len(cue_rows),
        "v_m_nar_awb_directory": props.get("AwbDirectory", {}).get("Path"),
        "v_m_nar_categories": dict(categories),
        "v_m_nar_target_cue_matches": target_cues,
    }
    (OUT / "phase4_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    main()
