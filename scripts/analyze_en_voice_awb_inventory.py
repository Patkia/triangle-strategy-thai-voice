import csv
import json
import struct
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH_LIST = ROOT / "work/opening_voice_candidates/voice_en_paths.txt"
AWB_DIR = ROOT / "work/opening_trace_phase2/awb"
OUT_DIR = ROOT / "work/opening_trace_phase2"


def read_u24_be(data, offset):
    return int.from_bytes(data[offset:offset + 3], "big")


def parse_awb(path):
    data = path.read_bytes()
    if data[:4] != b"AFS2":
        raise ValueError("not AFS2/AWB")
    offset_size, id_size = data[5], data[6]
    count = struct.unpack_from("<I", data, 8)[0]
    alignment = struct.unpack_from("<H", data, 12)[0]
    ids_start = 16
    offsets_start = ids_start + count * id_size
    stream_ids = [int.from_bytes(data[ids_start + i * id_size:ids_start + (i + 1) * id_size], "little") for i in range(count)]
    offsets = [int.from_bytes(data[offsets_start + i * offset_size:offsets_start + (i + 1) * offset_size], "little") for i in range(count + 1)]
    streams = []
    for index, (stream_id, raw_start, end) in enumerate(zip(stream_ids, offsets, offsets[1:]), start=1):
        start = ((raw_start + alignment - 1) // alignment) * alignment
        if data[start:start + 4] != b"HCA\x00" or data[start + 8:start + 12] != b"fmt\x00":
            streams.append({"stream_index": index, "stream_id": stream_id, "container_span_bytes": end - start, "parse_status": "non-HCA-or-unparsed"})
            continue
        channels = data[start + 12]
        sample_rate = read_u24_be(data, start + 13)
        blocks = struct.unpack_from(">I", data, start + 16)[0]
        delay = struct.unpack_from(">H", data, start + 20)[0]
        padding = struct.unpack_from(">H", data, start + 22)[0]
        samples = blocks * 1024 - delay - padding
        streams.append({
            "stream_index": index, "stream_id": stream_id, "container_span_bytes": end - start,
            "parse_status": "HCA", "sample_rate": sample_rate, "channels": channels,
            "block_count": blocks, "encoder_delay": delay, "padding": padding,
            "sample_count": samples, "duration_seconds": samples / sample_rate,
        })
    return streams


def load_json_metadata():
    metadata = {}
    for path in (ROOT / "Output/Exports").rglob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            sheet = raw[0] if isinstance(raw, list) else raw
            props = sheet.get("Properties", {})
            name = props.get("CueSheetName")
            cues = props.get("CueInfos")
            if not name or not isinstance(cues, list):
                continue
            categories = sorted({category for cue in cues for category in cue.get("CategoryNames", [])})
            patterns = sorted({"_".join(cue.get("Name", "").split("_")[:4]) for cue in cues})
            metadata[name] = {"cue_count": len(cues), "cue_categories": " | ".join(categories), "cue_name_patterns": " | ".join(patterns[:12])}
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
    return metadata


def main():
    paths = [line.strip() for line in PATH_LIST.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    cue_paths = {Path(path).stem: path for path in paths if path.startswith("Newera/Content/Newera/Sound/VOICE/EN/") and path.endswith(".uasset")}
    awb_paths = {Path(path).stem: path for path in paths if path.startswith("Newera/Content/Newera/Sound/Stream/VOICE/EN/") and path.endswith(".awb")}
    cue_metadata = load_json_metadata()
    bank_rows, stream_rows = [], []
    for bank in sorted(awb_paths):
        streams = parse_awb(AWB_DIR / f"{bank}.awb")
        hca = [row for row in streams if row["parse_status"] == "HCA"]
        for row in streams:
            stream_rows.append({"bank_name": bank, **row})
        durations = [row["duration_seconds"] for row in hca]
        meta = cue_metadata.get(bank, {})
        bank_rows.append({
            "bank_name": bank, "uasset_path": cue_paths.get(bank, ""), "awb_path": awb_paths[bank],
            "awb_stream_count": len(streams), "hca_stream_count": len(hca),
            "total_audio_duration": f"{sum(durations):.6f}" if durations else "",
            "min_duration": f"{min(durations):.6f}" if durations else "", "max_duration": f"{max(durations):.6f}" if durations else "",
            "average_duration": f"{sum(durations) / len(durations):.6f}" if durations else "",
            "streams_3_to_10_seconds": sum(3 <= value <= 10 for value in durations),
            "cue_count": meta.get("cue_count", ""), "cue_categories": meta.get("cue_categories", ""),
            "cue_name_patterns": meta.get("cue_name_patterns", ""),
        })
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "en_voice_bank_metadata.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(bank_rows[0])); writer.writeheader(); writer.writerows(bank_rows)
    fields = ["bank_name", "stream_index", "stream_id", "container_span_bytes", "parse_status", "sample_rate", "channels", "block_count", "encoder_delay", "padding", "sample_count", "duration_seconds"]
    with (OUT_DIR / "en_voice_stream_metadata.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(stream_rows)
    print(f"banks={len(bank_rows)} streams={len(stream_rows)} hca_streams={sum(row['hca_stream_count'] for row in bank_rows)} json_metadata_banks={len(cue_metadata)}")


if __name__ == "__main__":
    main()
