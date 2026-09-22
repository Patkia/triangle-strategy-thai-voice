from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
OUT_CSV = OUT_DIR / "chapter2_omnivoice_studio.csv"
OUT_REPORT = OUT_DIR / "chapter2_build_report.json"
TEXT_INDEX = ROOT / "work/full_game_text_index/english_thai_identifier_join.csv"
THAI_MAP = ROOT / "work/new_subtitle_switch/whole_game_unicode_preflight/whole_game_migration_map.csv"
MS02_UEXP = ROOT / "work/opening_trace_phase3/cuesheet_packages/MS02_EN.uexp"
RESOLVER = ROOT / "work/chapter1_voice_mapping/voice_runtime_timing_fix_v1/build_timing_fix.py"
CH1_MASTER = ROOT / "work/chapter1_voice_mapping/chapter1_master_plan/chapter1_omnivoice_studio.csv"
CH1_REMAINING = ROOT / "work/chapter1_voice_mapping/chapter1_remaining_voice/chapter1_remaining_32.csv"

HEADERS = [
    "line_no", "file_name", "self_id", "cue", "sequence", "waveform", "awb_stream",
    "character_name", "role", "gender", "voice_target", "reference_audio", "thai_text",
    "pronunciation_note", "prosody_note", "status", "tts_text", "voice_project",
]

# Speaker-code resolution is evidence-backed by GOP_Unit_Master / ActionVoiceType and MS02 dialogue context.
# New named characters intentionally stay blocked until Pat adds/approves their dedicated OmniVoice targets.
SPEAKERS = {
    "SEL": {"name": "เซเรโนอา", "role": "main", "gender": "male", "target": "serenoa"},
    "DRG": {"name": "ดราแกน", "role": "npc", "gender": "male", "target": "NEEDS_VOICE_TARGET"},
    "SMN": {"name": "ซีมอน", "role": "npc", "gender": "male", "target": "symon"},
    "RLN": {"name": "โรแลนด์", "role": "main", "gender": "male", "target": "roland"},
    "LGN": {"name": "เร็กน่า", "role": "npc", "gender": "male", "target": "NEEDS_VOICE_TARGET"},
    "LYL": {"name": "ไลล่า", "role": "npc", "gender": "female", "target": "NEEDS_VOICE_TARGET"},
    "FRE": {"name": "เฟรเดอริก้า", "role": "main", "gender": "female", "target": "frederica"},
    "MAX": {"name": "แม็กซ์เวลล์", "role": "npc", "gender": "male", "target": "NEEDS_VOICE_TARGET"},
    "BND": {"name": "เบเนดิกต์", "role": "main", "gender": "male", "target": "benedict"},
    "EGS": {"name": "เอกซ์เฮม", "role": "npc", "gender": "male", "target": "NEEDS_VOICE_TARGET"},
    "FRN": {"name": "แฟรนี่", "role": "npc", "gender": "male", "target": "frani"},
    "TRS": {"name": "ธาลาส", "role": "npc", "gender": "male", "target": "NEEDS_VOICE_TARGET"},
    "SLS": {"name": "ซอสเลย์", "role": "npc", "gender": "male", "target": "NEEDS_VOICE_TARGET"},
    "NNN": {"name": "Narrator", "role": "narrator", "gender": "female", "target": "narrator"},
    "ABR": {"name": "อัฟโลร่า", "role": "npc", "gender": "female", "target": "NEEDS_VOICE_TARGET"},
    "CRD": {"name": "คอร์เดเลีย", "role": "npc", "gender": "female", "target": "NEEDS_VOICE_TARGET"},
    "ERK": {"name": "เอริก้า", "role": "npc", "gender": "female", "target": "NEEDS_VOICE_TARGET"},
    "HEW": {"name": "ฮิวเอทท์", "role": "main", "gender": "female", "target": "hughette"},
    "PTR": {"name": "พาทริเอ็ทท์", "role": "npc", "gender": "male", "target": "MALE_OLD_A"},
    "ELA": {"name": "เอราดอร์", "role": "main", "gender": "male", "target": "erador"},
    # Generic crowd / extras: reuse approved generic voices; no new dedicated target required.
    "M420": {"name": "ทหารวูล์ฟฟอร์ต", "role": "generic", "gender": "male", "target": "MALE_YOUNG_B"},
    "M421": {"name": "แขก", "role": "generic", "gender": "male", "target": "MALE_ADULT_B"},
    "M424": {"name": "แขก", "role": "generic", "gender": "male", "target": "MALE_ADULT_B"},
}


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def is_ellipsis_only(text: str) -> bool:
    value = (text or "").strip()
    return bool(value) and all(ch in ".…" for ch in value)


def load_reference_map() -> dict[str, str]:
    refs: dict[str, str] = {}
    for path in (CH1_MASTER, CH1_REMAINING):
        for row in read_csv(path):
            target = (row.get("voice_target") or "").strip()
            ref = (row.get("reference_audio") or "").strip()
            if target and ref and target not in refs:
                refs[target] = ref
    return refs


def main() -> None:
    text_rows = read_csv(TEXT_INDEX)
    thai_rows = read_csv(THAI_MAP)
    text_by_id = {r["SelfId"]: r for r in text_rows}
    thai_by_id = {
        r["SelfId"]: r
        for r in thai_rows
        if r.get("join_status") == "MATCH_EXACT_ONE" and r.get("confidence") == "HIGH"
    }
    refs = load_reference_map()

    spec = importlib.util.spec_from_file_location("chapter2_cri_resolver", RESOLVER)
    if not spec or not spec.loader:
        raise RuntimeError("Could not load CRI resolver")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    _, tables = mod.parse_tables(MS02_UEXP)

    cue_names = [r["CueName"] for r in tables["CueName"].rows()]
    if len(cue_names) != 376:
        raise RuntimeError(f"Expected 376 MS02_EN cues, got {len(cue_names)}")
    if len(set(cue_names)) != len(cue_names):
        raise RuntimeError("Duplicate CueName found in MS02_EN")
    if any(not sid.startswith("MS02_") for sid in cue_names):
        raise RuntimeError("Non-MS02 cue found in MS02_EN")

    output_rows: list[dict] = []
    nonverbal_rows: list[dict] = []
    unknown_speakers: list[str] = []

    for sid in cue_names:
        source = text_by_id.get(sid)
        thai = thai_by_id.get(sid)
        if not source:
            raise RuntimeError(f"Missing text-index row: {sid}")
        if not thai or not (thai.get("steam_thai") or "").strip():
            raise RuntimeError(f"Missing exact/high Thai row: {sid}")

        code = sid.split("_")[-2]
        speaker = SPEAKERS.get(code)
        if not speaker:
            unknown_speakers.append(code)
            continue

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
        blocked = target == "NEEDS_VOICE_TARGET"
        reference_audio = "" if blocked else refs.get(target, "")
        if not blocked and not reference_audio:
            raise RuntimeError(f"Missing reusable reference_audio for target {target}: {sid}")

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
            "reference_audio": reference_audio,
            "thai_text": thai["steam_thai"],
            "pronunciation_note": "",
            "prosody_note": "",
            "status": "BLOCKED_NEW_VOICE_TARGET" if blocked else "PENDING_MANUAL_GENERATION",
            "tts_text": "",
            "voice_project": "triangle-strategy",
        })

    if unknown_speakers:
        raise RuntimeError(f"Unresolved speaker codes: {sorted(set(unknown_speakers))}")
    if len(output_rows) != 371:
        raise RuntimeError(f"Expected 371 spoken/TTS rows, got {len(output_rows)}")
    if len(nonverbal_rows) != 5:
        raise RuntimeError(f"Expected 5 ellipsis/nonverbal rows, got {len(nonverbal_rows)}")
    if len({r["self_id"] for r in output_rows}) != 371:
        raise RuntimeError("Duplicate self_id in output")
    if len({r["file_name"].casefold() for r in output_rows}) != 371:
        raise RuntimeError("Duplicate file_name in output")
    if any(not r["thai_text"].strip() for r in output_rows):
        raise RuntimeError("Blank Thai text in output")

    blocked_rows = [r for r in output_rows if r["voice_target"] == "NEEDS_VOICE_TARGET"]
    blocked_by_character = Counter(r["character_name"] for r in blocked_rows)
    blocked_gender = {r["character_name"]: r["gender"] for r in blocked_rows}
    blocked_code = {
        speaker["name"]: code
        for code, speaker in SPEAKERS.items()
        if speaker["target"] == "NEEDS_VOICE_TARGET"
    }
    if len(blocked_by_character) != 10:
        raise RuntimeError(f"Expected 10 missing named character voices, got {len(blocked_by_character)}")
    if len(blocked_rows) != 161:
        raise RuntimeError(f"Expected 161 blocked rows, got {len(blocked_rows)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(output_rows)

    assigned_counts = Counter(r["voice_target"] for r in output_rows)
    speaker_counts = Counter(r["character_name"] for r in output_rows)
    report = {
        "chapter": 2,
        "bank": "MS02_EN",
        "bank_audio_cues": len(cue_names),
        "spoken_tts_rows": len(output_rows),
        "nonverbal_ellipsis_keep_original": len(nonverbal_rows),
        "coverage_equation": f"{len(output_rows)} TTS + {len(nonverbal_rows)} original nonverbal = {len(cue_names)}/{len(cue_names)}",
        "thai_exact_high_coverage": len(cue_names),
        "missing_voice_target_characters": len(blocked_by_character),
        "missing_voice_target_rows": len(blocked_rows),
        "ready_reused_rows": len(output_rows) - len(blocked_rows),
        "missing_voice_targets": [
            {
                "speaker_code": blocked_code[name],
                "character_name": name,
                "gender": blocked_gender[name],
                "spoken_lines": count,
                "voice_target": "NEEDS_VOICE_TARGET",
            }
            for name, count in sorted(blocked_by_character.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "nonverbal_rows": nonverbal_rows,
        "voice_target_counts": dict(sorted(assigned_counts.items())),
        "character_spoken_counts": dict(sorted(speaker_counts.items())),
        "canonical_csv": str(OUT_CSV),
        "generation_performed": False,
        "safe_to_import_now": False,
        "import_gate": "Add/approve the 10 missing dedicated voice targets first; then replace NEEDS_VOICE_TARGET and validate references before OmniVoice import.",
    }
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    sha = hashlib.sha256(OUT_CSV.read_bytes()).hexdigest()
    print(f"PASS MS02_AUDIO_CUES={len(cue_names)}")
    print(f"TTS_ROWS={len(output_rows)}")
    print(f"NONVERBAL_KEEP_ORIGINAL={len(nonverbal_rows)}")
    print(f"READY_REUSED_ROWS={len(output_rows) - len(blocked_rows)}")
    print(f"BLOCKED_ROWS={len(blocked_rows)}")
    print(f"MISSING_CHARACTERS={len(blocked_by_character)}")
    for name, count in sorted(blocked_by_character.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"NEEDS {blocked_code[name]} | {name} | {blocked_gender[name]} | {count}")
    print(f"CSV={OUT_CSV}")
    print(f"REPORT={OUT_REPORT}")
    print(f"SHA256={sha}")
    print("GENERATION_PERFORMED=False")
    print("SAFE_TO_IMPORT_NOW=False")


if __name__ == "__main__":
    main()
