from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "work/chapter4_voice_mapping"
OUT_CSV = OUT_DIR / "chapter4_omnivoice_studio.csv"
OUT_REPORT = OUT_DIR / "chapter4_build_report.json"
READY_CSV = OUT_DIR / "chapter4_ready_219.csv"
PENDING_CSV = OUT_DIR / "chapter4_pending_reference_22.csv"
PENDING_TARGETS_CSV = OUT_DIR / "chapter4_pending_voice_targets.csv"
TEXT_INDEX = ROOT / "work/full_game_text_index/english_thai_identifier_join.csv"
THAI_MAP = ROOT / "work/new_subtitle_switch/whole_game_unicode_preflight/whole_game_migration_map.csv"
MS04_UEXP = ROOT / "work/opening_trace_phase3/cuesheet_packages/MS04_EN.uexp"
RESOLVER = ROOT / "work/chapter1_voice_mapping/voice_runtime_timing_fix_v1/build_timing_fix.py"

HEADERS = [
    "line_no", "file_name", "self_id", "cue", "sequence", "waveform", "awb_stream",
    "character_name", "role", "gender", "voice_target", "reference_audio", "thai_text",
    "pronunciation_note", "prosody_note", "status", "tts_text", "voice_project",
]

READY_TARGETS = {
    "serenoa", "roland", "frederica", "geela", "benedict", "erador", "symon", "dragan",
    "hughette", "regna", "thalas", "narrator",
    "MALE_CHILD_A", "MALE_CHILD_B", "MALE_CHILD_C",
    "MALE_YOUNG_A", "MALE_YOUNG_B", "MALE_YOUNG_C",
    "MALE_ADULT_A", "MALE_ADULT_B", "MALE_ADULT_C",
    "MALE_OLD_A", "MALE_OLD_B", "MALE_OLD_C",
    "MALE_ANGER_STRONG_01", "MALE_ANGER_STRONG_02",
}

# These targets already exist in OmniVoice's voice_target_map.json as fail-closed placeholders.
PENDING_REFERENCE_TARGETS = {
    "patriatte", "jerrom", "gustadolph",
}

SPEAKERS = {
    "LGN": {"name": "เร็กน่า", "role": "npc", "gender": "male", "target": "regna"},
    "PTR": {"name": "พาทริเอ็ทท์", "role": "npc", "gender": "male", "target": "patriatte"},
    "RLN": {"name": "โรแลนด์", "role": "main", "gender": "male", "target": "roland"},
    "FRE": {"name": "เฟรเดอริก้า", "role": "main", "gender": "female", "target": "frederica"},
    "YRA": {"name": "จีล่า", "role": "main", "gender": "female", "target": "geela"},
    "BND": {"name": "เบเนดิกต์", "role": "main", "gender": "male", "target": "benedict"},
    "ELA": {"name": "เอราดอร์", "role": "main", "gender": "male", "target": "erador"},
    "SEL": {"name": "เซเรโนอา", "role": "main", "gender": "male", "target": "serenoa"},
    "SMN": {"name": "ซีมอน", "role": "npc", "gender": "male", "target": "symon"},
    "DRG": {"name": "ดราแกน", "role": "npc", "gender": "male", "target": "dragan"},
    "HEW": {"name": "ฮิวเอทท์", "role": "main", "gender": "female", "target": "hughette"},
    "JRM": {"name": "เจอร์รอม", "role": "npc", "gender": "male", "target": "jerrom"},
    "GST": {"name": "กุสตาดอล์ฟ", "role": "npc", "gender": "male", "target": "gustadolph"},
    "TRS": {"name": "ธาลาส", "role": "npc", "gender": "male", "target": "thalas"},
    "NNN": {"name": "Narrator", "role": "narrator", "gender": "female", "target": "narrator"},

    # Generic / extras: reuse approved Thai voice pools.
    "M221": {"name": "คนงานเหมือง", "role": "generic", "gender": "male", "target": "MALE_ADULT_A"},
    "M222": {"name": "ผู้ใต้บังคับบัญชาของดราแกน", "role": "generic", "gender": "male", "target": "MALE_ADULT_C"},
    "M033": {"name": "ผู้ส่งสารเกลนบรู๊ค", "role": "generic", "gender": "male", "target": "MALE_YOUNG_B"},
    "M034": {"name": "ทหารเอสฟรอสต์", "role": "generic", "gender": "male", "target": "MALE_ADULT_B"},
    "M224": {"name": "ยามเหมือง", "role": "generic", "gender": "male", "target": "MALE_ADULT_B"},
    "M225": {"name": "หัวหน้าหน่วยจู่โจม", "role": "generic", "gender": "male", "target": "MALE_ANGER_STRONG_01"},
    "M226": {"name": "ทหารหน่วยจู่โจม", "role": "generic", "gender": "male", "target": "MALE_YOUNG_C"},
    "MS04X05B01M01": {"name": "สายลับเอสฟรอสต์", "role": "generic", "gender": "male", "target": "MALE_YOUNG_A"},
    "M223": {"name": "ผู้ติดตามดราแกน", "role": "generic", "gender": "male", "target": "MALE_ADULT_A"},
}


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def is_ellipsis_only(text: str) -> bool:
    value = (text or "").strip()
    return bool(value) and all(ch in ".…" for ch in value)


def reference_for_target(target: str) -> str:
    if target not in READY_TARGETS:
        return ""
    return f"assets/triangle-strategy/approved_voice_references/{target}.wav"


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    text_by_id = {r["SelfId"]: r for r in read_csv(TEXT_INDEX)}
    thai_by_id = {
        r["SelfId"]: r
        for r in read_csv(THAI_MAP)
        if r.get("join_status") == "MATCH_EXACT_ONE" and r.get("confidence") == "HIGH"
    }

    spec = importlib.util.spec_from_file_location("chapter4_cri_resolver", RESOLVER)
    if not spec or not spec.loader:
        raise RuntimeError("Could not load CRI resolver")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    _, tables = mod.parse_tables(MS04_UEXP)

    cue_names = [r["CueName"] for r in tables["CueName"].rows()]
    if len(cue_names) != 242:
        raise RuntimeError(f"Expected 242 MS04_EN cues, got {len(cue_names)}")
    if len(set(cue_names)) != len(cue_names):
        raise RuntimeError("Duplicate CueName found in MS04_EN")
    if any(not sid.startswith("MS04_") for sid in cue_names):
        raise RuntimeError("Non-MS04 cue found in MS04_EN")

    output_rows: list[dict] = []
    nonverbal_rows: list[dict] = []
    unknown_speakers: list[str] = []

    for sid in cue_names:
        code = sid.split("_")[-2]
        speaker = SPEAKERS.get(code)
        if not speaker:
            unknown_speakers.append(code)
            continue

        source = text_by_id.get(sid)
        thai = thai_by_id.get(sid)
        if not source:
            raise RuntimeError(f"Missing text-index row: {sid}")
        if not thai or not (thai.get("steam_thai") or "").strip():
            raise RuntimeError(f"Missing exact/high Thai row: {sid}")

        chain = mod.resolve_chain(tables, sid)
        waveform = chain["waveform"]
        awb_stream = int(waveform["StreamAwbId"]) + 1

        if is_ellipsis_only(source.get("EnglishText", "")):
            nonverbal_rows.append({
                "self_id": sid,
                "speaker_code": code,
                "character_name": speaker["name"],
                "english_text": source.get("EnglishText", ""),
                "thai_text": thai.get("steam_thai", ""),
                "awb_stream": awb_stream,
                "classification": "NONVERBAL_ELLIPSIS_NOT_TTS",
                "action": "KEEP_ORIGINAL_GAME_AUDIO",
            })
            continue

        target = speaker["target"]
        target_ready = target in READY_TARGETS
        target_pending = target in PENDING_REFERENCE_TARGETS
        if not target_ready and not target_pending:
            raise RuntimeError(f"Target is neither ready nor registered as pending: {target}")

        output_rows.append({
            "line_no": len(output_rows) + 1,
            "file_name": sid + ".wav",
            "self_id": sid,
            "cue": chain["cue_index"],
            "sequence": chain["sequence_index"],
            "waveform": chain["waveform_index"],
            "awb_stream": awb_stream,
            "character_name": speaker["name"],
            "role": speaker["role"],
            "gender": speaker["gender"],
            "voice_target": target,
            "reference_audio": reference_for_target(target),
            "thai_text": thai["steam_thai"],
            "pronunciation_note": "",
            "prosody_note": "",
            "status": "PENDING_MANUAL_GENERATION" if target_ready else "BLOCKED_PENDING_REFERENCE_AUDIO",
            "tts_text": "",
            "voice_project": "triangle-strategy",
        })

    if unknown_speakers:
        raise RuntimeError(f"Unresolved speaker codes: {sorted(set(unknown_speakers))}")
    if len(output_rows) != 241:
        raise RuntimeError(f"Expected 241 spoken/TTS rows, got {len(output_rows)}")
    if len(nonverbal_rows) != 1:
        raise RuntimeError(f"Expected 1 ellipsis/nonverbal row, got {len(nonverbal_rows)}")
    if len(output_rows) + len(nonverbal_rows) != len(cue_names):
        raise RuntimeError("Coverage mismatch")
    if len({r["self_id"] for r in output_rows}) != len(output_rows):
        raise RuntimeError("Duplicate self_id in output")
    if len({r["file_name"].casefold() for r in output_rows}) != len(output_rows):
        raise RuntimeError("Duplicate file_name in output")
    if any(not r["thai_text"].strip() for r in output_rows):
        raise RuntimeError("Blank Thai text in output")

    ready_rows = [r for r in output_rows if r["status"] == "PENDING_MANUAL_GENERATION"]
    pending_rows = [r for r in output_rows if r["status"] == "BLOCKED_PENDING_REFERENCE_AUDIO"]
    pending_counts = Counter((r["voice_target"], r["character_name"], r["gender"]) for r in pending_rows)

    if len(ready_rows) != 219:
        raise RuntimeError(f"Expected 219 ready rows, got {len(ready_rows)}")
    if len(pending_rows) != 22:
        raise RuntimeError(f"Expected 22 pending-reference rows, got {len(pending_rows)}")
    if len(pending_counts) != 3:
        raise RuntimeError(f"Expected 3 pending-reference targets, got {len(pending_counts)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_rows(OUT_CSV, output_rows)
    write_rows(READY_CSV, ready_rows)
    write_rows(PENDING_CSV, pending_rows)

    with PENDING_TARGETS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["voice_target", "character_name", "gender", "spoken_lines", "planned_reference_audio", "status"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for (target, name, gender), count in sorted(pending_counts.items(), key=lambda kv: (-kv[1], kv[0][0])):
            writer.writerow({
                "voice_target": target,
                "character_name": name,
                "gender": gender,
                "spoken_lines": count,
                "planned_reference_audio": f"work/chapter4_voice_mapping/chapter4_voice_references/approved/{target}.wav",
                "status": "PENDING_REFERENCE_AUDIO",
            })

    report = {
        "chapter": 4,
        "bank": "MS04_EN",
        "bank_audio_cues": len(cue_names),
        "spoken_tts_rows": len(output_rows),
        "nonverbal_ellipsis_keep_original": len(nonverbal_rows),
        "coverage_equation": f"{len(output_rows)} TTS + {len(nonverbal_rows)} ellipsis original = {len(cue_names)}/{len(cue_names)}",
        "thai_exact_high_coverage": len(cue_names),
        "ready_existing_voice_rows": len(ready_rows),
        "pending_reference_rows": len(pending_rows),
        "pending_reference_targets": len(pending_counts),
        "pending_voice_targets": [
            {
                "voice_target": target,
                "character_name": name,
                "gender": gender,
                "spoken_lines": count,
                "planned_reference_audio": f"work/chapter4_voice_mapping/chapter4_voice_references/approved/{target}.wav",
            }
            for (target, name, gender), count in sorted(pending_counts.items(), key=lambda kv: (-kv[1], kv[0][0]))
        ],
        "nonverbal_rows": nonverbal_rows,
        "voice_target_counts": dict(sorted(Counter(r["voice_target"] for r in output_rows).items())),
        "character_spoken_counts": dict(sorted(Counter(r["character_name"] for r in output_rows).items())),
        "canonical_csv": str(OUT_CSV),
        "ready_csv": str(READY_CSV),
        "pending_reference_csv": str(PENDING_CSV),
        "pending_targets_csv": str(PENDING_TARGETS_CSV),
        "generation_performed": False,
        "safe_to_import_ready_csv": True,
        "safe_to_import_canonical_now": False,
        "import_gate": "Canonical CSV is complete, but rows using fail-closed pending targets must wait until their approved reference WAV/config is added to OmniVoice. Ready CSV can be generated now.",
    }
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    sha = hashlib.sha256(OUT_CSV.read_bytes()).hexdigest()
    print(f"PASS MS04_AUDIO_CUES={len(cue_names)}")
    print(f"TTS_ROWS={len(output_rows)}")
    print(f"NONVERBAL_KEEP_ORIGINAL={len(nonverbal_rows)}")
    print(f"READY_EXISTING_VOICE_ROWS={len(ready_rows)}")
    print(f"PENDING_REFERENCE_ROWS={len(pending_rows)}")
    print(f"PENDING_REFERENCE_TARGETS={len(pending_counts)}")
    for (target, _name, gender), count in sorted(pending_counts.items(), key=lambda kv: (-kv[1], kv[0][0])):
        print(f"NEEDS_REFERENCE {target} | {gender} | {count}")
    print(f"CSV={OUT_CSV}")
    print(f"READY={READY_CSV}")
    print(f"PENDING={PENDING_CSV}")
    print(f"PENDING_TARGETS_CSV={PENDING_TARGETS_CSV}")
    print(f"REPORT={OUT_REPORT}")
    print(f"SHA256={sha}")
    print("GENERATION_PERFORMED=False")


if __name__ == "__main__":
    main()
