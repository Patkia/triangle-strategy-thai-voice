from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "work/chapter3_voice_mapping"
OUT_CSV = OUT_DIR / "chapter3_omnivoice_studio.csv"
OUT_REPORT = OUT_DIR / "chapter3_build_report.json"
READY_CSV = OUT_DIR / "chapter3_ready_377.csv"
MISSING_CSV = OUT_DIR / "chapter3_pending_reference_210.csv"
MISSING_TARGETS_CSV = OUT_DIR / "chapter3_pending_voice_targets.csv"
TEXT_INDEX = ROOT / "work/full_game_text_index/english_thai_identifier_join.csv"
THAI_MAP = ROOT / "work/new_subtitle_switch/whole_game_unicode_preflight/whole_game_migration_map.csv"
MS03_UEXP = ROOT / "work/opening_trace_phase3/cuesheet_packages/MS03_EN.uexp"
RESOLVER = ROOT / "work/chapter1_voice_mapping/voice_runtime_timing_fix_v1/build_timing_fix.py"

HEADERS = [
    "line_no", "file_name", "self_id", "cue", "sequence", "waveform", "awb_stream",
    "character_name", "role", "gender", "voice_target", "reference_audio", "thai_text",
    "pronunciation_note", "prosody_note", "status", "tts_text", "voice_project",
]

# Existing targets are already present in OmniVoice projects/triangle-strategy/voice_target_map.json.
EXISTING_TARGETS = {
    "serenoa", "frederica", "benedict", "anna", "hughette", "geela", "roland", "erador",
    "avlora", "erika", "lyla", "dragan", "exharme", "maxwell", "sorsley", "thalas", "cordelia", "frani",
    "narrator",
    "MALE_ADULT_A", "MALE_ADULT_B", "MALE_ADULT_C", "MALE_YOUNG_A", "MALE_YOUNG_B", "MALE_YOUNG_C",
    "MALE_OLD_A", "MALE_OLD_B", "MALE_OLD_C", "MALE_ANGER_STRONG_01", "MALE_ANGER_STRONG_02",
    "FEMALE_ADULT_A", "FEMALE_ADULT_B", "FEMALE_ADULT_C", "FEMALE_YOUNG_A", "FEMALE_YOUNG_B", "FEMALE_YOUNG_C",
    "FEMALE_OLD_A", "FEMALE_OLD_B", "FEMALE_OLD_C", "FEMALE_CHILD_A", "FEMALE_CHILD_B", "FEMALE_CHILD_C",
}

# Named characters use their intended final target names now. Targets in PENDING_REFERENCE_TARGETS
# already exist in OmniVoice's map as fail-closed placeholders and remain blocked until reference audio is added.
PENDING_REFERENCE_TARGETS = {
    "patriatte", "silvio", "rufus", "landroi", "jerrom", "gustadolph", "svarog", "sycras",
    "hierophant", "booker", "kamsell", "idore", "tenebris", "clarus", "rudolph", "corentin",
    "julio", "milo", "hossabara", "narve", "medina", "jens", "archibald", "flanagan", "ezana",
    "lionel", "groma", "piccoletta", "decimal", "quahaug", "giovanna",
}

SPEAKERS = {
    "ABR": {"name": "อัฟโลร่า", "role": "npc", "gender": "female", "target": "avlora"},
    "ERK": {"name": "เอริก้า", "role": "npc", "gender": "female", "target": "erika"},
    "FRE": {"name": "เฟรเดอริก้า", "role": "main", "gender": "female", "target": "frederica"},
    "LYL": {"name": "ไลล่า", "role": "npc", "gender": "female", "target": "lyla"},
    "BND": {"name": "เบเนดิกต์", "role": "main", "gender": "male", "target": "benedict"},
    "DRG": {"name": "ดราแกน", "role": "npc", "gender": "male", "target": "dragan"},
    "EGS": {"name": "เอกซ์เฮม", "role": "npc", "gender": "male", "target": "exharme"},
    "LND": {"name": "แลนดรอย", "role": "npc", "gender": "male", "target": "landroi"},
    "MAX": {"name": "แม็กซ์เวลล์", "role": "npc", "gender": "male", "target": "maxwell"},
    "PTR": {"name": "พาทริเอ็ทท์", "role": "npc", "gender": "male", "target": "patriatte"},
    "SEL": {"name": "เซเรโนอา", "role": "main", "gender": "male", "target": "serenoa"},
    "SLS": {"name": "ซอสเลย์", "role": "npc", "gender": "male", "target": "sorsley"},
    "SLV": {"name": "ซิลวิโอ้", "role": "npc", "gender": "male", "target": "silvio"},
    "TRS": {"name": "ธาลาส", "role": "npc", "gender": "male", "target": "thalas"},
    "ANA": {"name": "แอนนา", "role": "main", "gender": "female", "target": "anna"},
    "HEW": {"name": "ฮิวเอทท์", "role": "main", "gender": "female", "target": "hughette"},
    "YRA": {"name": "จีล่า", "role": "main", "gender": "female", "target": "geela"},
    "RLN": {"name": "โรแลนด์", "role": "main", "gender": "male", "target": "roland"},
    "NNN": {"name": "Narrator", "role": "narrator", "gender": "female", "target": "narrator"},
    "CRD": {"name": "คอร์เดเลีย", "role": "npc", "gender": "female", "target": "cordelia"},
    "FRN": {"name": "แฟรนี่", "role": "npc", "gender": "male", "target": "frani"},
    "SVR": {"name": "สวาร็อค", "role": "npc", "gender": "male", "target": "svarog"},
    "GST": {"name": "กุสตาดอล์ฟ", "role": "npc", "gender": "male", "target": "gustadolph"},
    "ELA": {"name": "เอราดอร์", "role": "main", "gender": "male", "target": "erador"},
    "SEC": {"name": "ซิคราส", "role": "npc", "gender": "male", "target": "sycras"},
    "RDL": {"name": "รูดอล์ฟ", "role": "main", "gender": "male", "target": "rudolph"},
    "COR": {"name": "คอเรนติน", "role": "main", "gender": "male", "target": "corentin"},
    "POP": {"name": "หัวหน้านักบวช", "role": "npc", "gender": "female", "target": "hierophant"},
    "IDO": {"name": "อีดอร์", "role": "npc", "gender": "male", "target": "idore"},
    "KNS": {"name": "แคมเซลล์", "role": "npc", "gender": "male", "target": "kamsell"},
    # Generic/extras reuse approved Thai pools.
    "M206": {"name": "พ่อค้าตลาดมืด", "role": "generic", "gender": "male", "target": "MALE_ADULT_B"},
    "M207": {"name": "พ่อค้าตลาดมืด", "role": "generic", "gender": "male", "target": "MALE_ADULT_C"},
    "M208": {"name": "ผู้ร้าย", "role": "generic", "gender": "male", "target": "MALE_YOUNG_A"},
    "M209": {"name": "หัวหน้าผู้ร้าย", "role": "generic", "gender": "male", "target": "MALE_ANGER_STRONG_01"},
    "MB103": {"name": "นักวิจัยไฮแซนต์", "role": "generic", "gender": "male", "target": "MALE_ADULT_C"},
    "M379": {"name": "หญิงชาวไฮแซนต์", "role": "generic", "gender": "female", "target": "FEMALE_YOUNG_A"},
    "M217": {"name": "ชาวไฮแซนต์", "role": "generic", "gender": "male", "target": "MALE_ADULT_A"},
}

AUDIO_ONLY_KEEP_ORIGINAL = {
    "MS03_H01_WD_0010_N_NNN_0030",
    "MS03_H01_WD_0010_N_NNN_0040",
}


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def is_ellipsis_only(text: str) -> bool:
    value = (text or "").strip()
    return bool(value) and all(ch in ".…" for ch in value)


def reference_for_target(target: str) -> str:
    if target not in EXISTING_TARGETS:
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

    spec = importlib.util.spec_from_file_location("chapter3_cri_resolver", RESOLVER)
    if not spec or not spec.loader:
        raise RuntimeError("Could not load CRI resolver")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    _, tables = mod.parse_tables(MS03_UEXP)

    cue_names = [r["CueName"] for r in tables["CueName"].rows()]
    if len(cue_names) != 604:
        raise RuntimeError(f"Expected 604 MS03_EN cues, got {len(cue_names)}")
    if len(set(cue_names)) != len(cue_names):
        raise RuntimeError("Duplicate CueName found in MS03_EN")
    if any(not sid.startswith("MS03_") for sid in cue_names):
        raise RuntimeError("Non-MS03 cue found in MS03_EN")

    output_rows: list[dict] = []
    nonverbal_rows: list[dict] = []
    audio_only_rows: list[dict] = []
    unknown_speakers: list[str] = []

    for sid in cue_names:
        code = sid.split("_")[-2]
        speaker = SPEAKERS.get(code)
        if not speaker:
            unknown_speakers.append(code)
            continue

        chain = mod.resolve_chain(tables, sid)
        waveform = chain["waveform"]
        awb_stream = int(waveform["StreamAwbId"]) + 1

        if sid in AUDIO_ONLY_KEEP_ORIGINAL:
            audio_only_rows.append({
                "self_id": sid,
                "speaker_code": code,
                "character_name": speaker["name"],
                "awb_stream": awb_stream,
                "classification": "AUDIO_ONLY_NO_TEXT_INDEX",
                "action": "KEEP_ORIGINAL_GAME_AUDIO",
            })
            continue

        source = text_by_id.get(sid)
        thai = thai_by_id.get(sid)
        if not source:
            raise RuntimeError(f"Missing text-index row outside approved audio-only exceptions: {sid}")
        if not thai or not (thai.get("steam_thai") or "").strip():
            raise RuntimeError(f"Missing exact/high Thai row: {sid}")

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
        target_ready = target in EXISTING_TARGETS
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
    if len(output_rows) != 587:
        raise RuntimeError(f"Expected 587 spoken/TTS rows, got {len(output_rows)}")
    if len(nonverbal_rows) != 15:
        raise RuntimeError(f"Expected 15 ellipsis/nonverbal rows, got {len(nonverbal_rows)}")
    if len(audio_only_rows) != 2:
        raise RuntimeError(f"Expected 2 audio-only/text-missing rows, got {len(audio_only_rows)}")
    if len(output_rows) + len(nonverbal_rows) + len(audio_only_rows) != len(cue_names):
        raise RuntimeError("Coverage mismatch")
    if len({r["self_id"] for r in output_rows}) != len(output_rows):
        raise RuntimeError("Duplicate self_id in output")
    if len({r["file_name"].casefold() for r in output_rows}) != len(output_rows):
        raise RuntimeError("Duplicate file_name in output")
    if any(not r["thai_text"].strip() for r in output_rows):
        raise RuntimeError("Blank Thai text in output")

    ready_rows = [r for r in output_rows if r["status"] == "PENDING_MANUAL_GENERATION"]
    blocked_rows = [r for r in output_rows if r["status"] == "BLOCKED_PENDING_REFERENCE_AUDIO"]
    blocked_counts = Counter((r["voice_target"], r["character_name"], r["gender"]) for r in blocked_rows)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_rows(OUT_CSV, output_rows)
    write_rows(READY_CSV, ready_rows)
    write_rows(MISSING_CSV, blocked_rows)

    with MISSING_TARGETS_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["voice_target", "character_name", "gender", "spoken_lines", "planned_reference_audio", "status"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for (target, name, gender), count in sorted(blocked_counts.items(), key=lambda kv: (-kv[1], kv[0][0])):
            writer.writerow({
                "voice_target": target,
                "character_name": name,
                "gender": gender,
                "spoken_lines": count,
                "planned_reference_audio": f"work/chapter3_voice_mapping/chapter3_voice_references/approved/{target}.wav",
                "status": "WAITING_FOR_REFERENCE_AUDIO",
            })

    assigned_counts = Counter(r["voice_target"] for r in output_rows)
    character_counts = Counter(r["character_name"] for r in output_rows)
    report = {
        "chapter": 3,
        "bank": "MS03_EN",
        "bank_audio_cues": len(cue_names),
        "spoken_tts_rows": len(output_rows),
        "nonverbal_ellipsis_keep_original": len(nonverbal_rows),
        "audio_only_no_text_keep_original": len(audio_only_rows),
        "coverage_equation": f"{len(output_rows)} TTS + {len(nonverbal_rows)} ellipsis original + {len(audio_only_rows)} audio-only original = {len(cue_names)}/{len(cue_names)}",
        "ready_existing_voice_rows": len(ready_rows),
        "blocked_pending_reference_audio_rows": len(blocked_rows),
        "pending_reference_target_characters": len(blocked_counts),
        "pending_reference_targets": [
            {
                "voice_target": target,
                "character_name": name,
                "gender": gender,
                "spoken_lines": count,
                "planned_reference_audio": f"work/chapter3_voice_mapping/chapter3_voice_references/approved/{target}.wav",
            }
            for (target, name, gender), count in sorted(blocked_counts.items(), key=lambda kv: (-kv[1], kv[0][0]))
        ],
        "nonverbal_rows": nonverbal_rows,
        "audio_only_rows": audio_only_rows,
        "voice_target_counts": dict(sorted(assigned_counts.items())),
        "character_spoken_counts": dict(sorted(character_counts.items())),
        "canonical_csv": str(OUT_CSV),
        "ready_csv": str(READY_CSV),
        "pending_reference_csv": str(MISSING_CSV),
        "pending_targets_csv": str(MISSING_TARGETS_CSV),
        "generation_performed": False,
        "safe_to_import_ready_csv": True,
        "safe_to_import_canonical_now": not blocked_rows,
        "import_gate": "Ready CSV can be generated now. Pending targets already exist in the OmniVoice map as fail-closed placeholders; add/approve each reference WAV and update that target's reference conditioning, then rebuild/validate before generating those rows.",
    }
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    sha = hashlib.sha256(OUT_CSV.read_bytes()).hexdigest()
    print(f"PASS MS03_AUDIO_CUES={len(cue_names)}")
    print(f"TTS_ROWS={len(output_rows)}")
    print(f"NONVERBAL_KEEP_ORIGINAL={len(nonverbal_rows)}")
    print(f"AUDIO_ONLY_KEEP_ORIGINAL={len(audio_only_rows)}")
    print(f"READY_EXISTING_VOICE_ROWS={len(ready_rows)}")
    print(f"PENDING_REFERENCE_ROWS={len(blocked_rows)}")
    print(f"PENDING_REFERENCE_TARGETS={len(blocked_counts)}")
    for (target, name, gender), count in sorted(blocked_counts.items(), key=lambda kv: (-kv[1], kv[0][0])):
        print(f"NEEDS_REFERENCE {target} | {gender} | {count}")
    print(f"CSV={OUT_CSV}")
    print(f"READY={READY_CSV}")
    print(f"MISSING={MISSING_CSV}")
    print(f"PENDING_TARGETS_CSV={MISSING_TARGETS_CSV}")
    print(f"REPORT={OUT_REPORT}")
    print(f"SHA256={sha}")
    print("GENERATION_PERFORMED=False")


if __name__ == "__main__":
    main()
