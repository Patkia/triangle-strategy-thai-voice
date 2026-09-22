from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OMNI_ROOT = Path(r"C:\Users\Pat\Workshop\omnivoice-thai-studio")
MAP_PATH = OMNI_ROOT / "projects/triangle-strategy/voice_target_map.json"
OUT_DIR = ROOT / "work/chapter6_voice_mapping"
OUT_CSV = OUT_DIR / "chapter6_omnivoice_studio.csv"
OUT_REPORT = OUT_DIR / "chapter6_build_report.json"
TEXT_INDEX = ROOT / "work/full_game_text_index/english_thai_identifier_join.csv"
THAI_MAP = ROOT / "work/new_subtitle_switch/whole_game_unicode_preflight/whole_game_migration_map.csv"
MS06_UEXP = ROOT / "work/opening_trace_phase3/cuesheet_packages/MS06_EN.uexp"
RESOLVER = ROOT / "work/chapter1_voice_mapping/voice_runtime_timing_fix_v1/build_timing_fix.py"

HEADERS = [
    "line_no", "file_name", "self_id", "cue", "sequence", "waveform", "awb_stream",
    "character_name", "role", "gender", "voice_target", "reference_audio", "thai_text",
    "pronunciation_note", "prosody_note", "status", "tts_text", "voice_project",
]

SPEAKERS = {
    "ABR": {"name": "อัฟโลร่า", "role": "npc", "gender": "female", "age": "adult", "target": "avlora"},
    "CRD": {"name": "คอร์เดเลีย", "role": "npc", "gender": "female", "age": "young adult", "target": "cordelia"},
    "FRE": {"name": "เฟรเดอริก้า", "role": "main", "gender": "female", "age": "young adult", "target": "frederica"},
    "BND": {"name": "เบเนดิกต์", "role": "main", "gender": "male", "age": "middle-aged", "target": "benedict"},
    "FRN": {"name": "แฟรนี่", "role": "npc", "gender": "male", "age": "young adult", "target": "frani"},
    "GST": {"name": "กุสตาดอล์ฟ", "role": "npc", "gender": "male", "age": "young adult", "target": "gustadolph"},
    "LGN": {"name": "เร็กน่า", "role": "npc", "gender": "male", "age": "elderly", "target": "regna"},
    "MAX": {"name": "แม็กซ์เวลล์", "role": "npc", "gender": "male", "age": "middle-aged", "target": "maxwell"},
    "RLN": {"name": "โรแลนด์", "role": "main", "gender": "male", "age": "young adult", "target": "roland"},
    "SEL": {"name": "เซเรโนอา", "role": "main", "gender": "male", "age": "young adult", "target": "serenoa"},
    "LND": {"name": "แลนดรอย", "role": "npc", "gender": "male", "age": "middle-aged", "target": "landroi"},
    "ELA": {"name": "เอราดอร์", "role": "main", "gender": "male", "age": "middle-aged", "target": "erador"},
    "ANA": {"name": "แอนนา", "role": "main", "gender": "female", "age": "young adult", "target": "anna"},
    "HEW": {"name": "ฮิวเอทท์", "role": "main", "gender": "female", "age": "young adult", "target": "hughette"},
    "YRA": {"name": "จีล่า", "role": "main", "gender": "female", "age": "adult", "target": "geela"},
    "NNN": {"name": "Narrator", "role": "narrator", "gender": "female", "age": "adult", "target": "narrator"},
    "M195": {"name": "ผู้ติดตามตระกูลฟอล์กส์", "role": "generic", "gender": "male", "age": "adult", "target": "MALE_ADULT_A"},
    "M196": {"name": "ทหารเอสฟรอสต์", "role": "generic", "gender": "male", "age": "young adult", "target": "MALE_YOUNG_A"},
    "M216": {"name": "ทหารเอสฟรอสต์", "role": "generic", "gender": "male", "age": "adult", "target": "MALE_ADULT_B"},
    "M02": {"name": "ทหารเอสฟรอสต์", "role": "generic", "gender": "male", "age": "young adult", "target": "MALE_YOUNG_B"},
    "M03": {"name": "ทหารเอสฟรอสต์", "role": "generic", "gender": "male", "age": "adult", "target": "MALE_ADULT_B"},
    "M04": {"name": "ทหารเอสฟรอสต์", "role": "generic", "gender": "male", "age": "adult", "target": "MALE_ADULT_C"},
    "MS06X07B01M01": {"name": "ทหารเอสฟรอสต์", "role": "generic", "gender": "male", "age": "adult", "target": "MALE_ADULT_A"},
    "MS06X07B01M02": {"name": "ทหารเอสฟรอสต์", "role": "generic", "gender": "male", "age": "young adult", "target": "MALE_YOUNG_B"},
    "MS06X07B01M03": {"name": "ทหารเอสฟรอสต์", "role": "generic", "gender": "male", "age": "adult", "target": "MALE_ADULT_C"},
}


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def punctuation_only(text: str) -> bool:
    value = (text or "").strip()
    return bool(value) and re.fullmatch(r"[.\u2026!?！？\s]+", value) is not None


def target_state(target: str, targets: dict) -> str:
    data = targets.get(target)
    if not isinstance(data, dict):
        return "NEEDS"
    if data.get("status") == "PENDING_REFERENCE_AUDIO":
        return "PENDING"
    if data.get("generation_mode") == "reference_first" and not (data.get("reference_conditioning") or {}).get("enabled"):
        return "PENDING"
    return "READY"


def main() -> None:
    text_by_id = {r["SelfId"]: r for r in read_csv(TEXT_INDEX)}
    thai_by_id = {r["SelfId"]: r for r in read_csv(THAI_MAP) if r.get("join_status") == "MATCH_EXACT_ONE" and r.get("confidence") == "HIGH"}
    targets = json.loads(MAP_PATH.read_text(encoding="utf-8"))["targets"]

    spec = importlib.util.spec_from_file_location("chapter6_cri", RESOLVER)
    if not spec or not spec.loader:
        raise RuntimeError("Could not load CRI resolver")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    _, tables = mod.parse_tables(MS06_UEXP)
    cue_names = [r["CueName"] for r in tables["CueName"].rows()]
    if len(cue_names) != 183 or len(set(cue_names)) != 183:
        raise RuntimeError(f"Unexpected MS06 cue count: {len(cue_names)}")

    rows: list[dict] = []
    keep_original: list[dict] = []
    needs = Counter()
    pending = Counter()

    for sid in cue_names:
        code = sid.split("_")[-2]
        speaker = SPEAKERS.get(code)
        if not speaker:
            raise RuntimeError(f"Unresolved speaker code: {code} ({sid})")
        chain = mod.resolve_chain(tables, sid)
        awb_stream = int(chain["waveform"]["StreamAwbId"]) + 1
        source = text_by_id.get(sid)
        if not source:
            keep_original.append({"self_id": sid, "speaker_code": code, "classification": "AUDIO_ONLY_NO_TEXT_INDEX", "action": "KEEP_ORIGINAL_GAME_AUDIO", "awb_stream": awb_stream})
            continue
        english = source.get("EnglishText", "")
        if punctuation_only(english):
            keep_original.append({"self_id": sid, "speaker_code": code, "classification": "NONVERBAL_PUNCTUATION_ONLY", "action": "KEEP_ORIGINAL_GAME_AUDIO", "awb_stream": awb_stream, "english_text": english})
            continue
        thai = thai_by_id.get(sid)
        if not thai or not (thai.get("steam_thai") or "").strip():
            raise RuntimeError(f"Missing exact/high Thai row: {sid}")

        desired = speaker["target"]
        state = target_state(desired, targets)
        target = desired
        status = "PENDING_MANUAL_GENERATION"
        ref = ""
        if state == "READY":
            ref = ((targets[desired].get("reference_conditioning") or {}).get("reference_audio") or "")
        elif state == "PENDING":
            status = "BLOCKED_PENDING_REFERENCE_AUDIO"
            if speaker["role"] != "generic":
                pending[(code, speaker["name"], speaker["gender"], speaker["age"], desired)] += 1
        else:
            if speaker["role"] == "generic":
                raise RuntimeError(f"Generic target missing from live map: {desired}")
            target = "NEEDS_VOICE_TARGET"
            status = "BLOCKED_NEEDS_VOICE_TARGET"
            needs[(code, speaker["name"], speaker["gender"], speaker["age"], desired)] += 1

        rows.append({
            "line_no": len(rows) + 1, "file_name": sid + ".wav", "self_id": sid,
            "cue": chain["cue_index"], "sequence": chain["sequence_index"], "waveform": chain["waveform_index"], "awb_stream": awb_stream,
            "character_name": speaker["name"], "role": speaker["role"], "gender": speaker["gender"], "voice_target": target,
            "reference_audio": ref, "thai_text": thai["steam_thai"], "pronunciation_note": "", "prosody_note": "",
            "status": status, "tts_text": "", "voice_project": "triangle-strategy",
        })

    if len(rows) + len(keep_original) != 183:
        raise RuntimeError("Coverage mismatch")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    status_counts = Counter(r["status"] for r in rows)
    report = {
        "chapter": 6, "bank": "MS06_EN", "bank_audio_cues": 183,
        "tts_rows": len(rows), "keep_original_rows": len(keep_original),
        "coverage_equation": f"{len(rows)} TTS + {len(keep_original)} original = 183/183",
        "status_counts": dict(status_counts),
        "pending_reference_characters": [{"code": k[0], "character_name": k[1], "gender": k[2], "age": k[3], "voice_target": k[4], "spoken_lines": v} for k, v in sorted(pending.items())],
        "needs_voice_target_characters": [{"code": k[0], "character_name": k[1], "gender": k[2], "age": k[3], "desired_target": k[4], "spoken_lines": v} for k, v in sorted(needs.items())],
        "keep_original_detail": keep_original,
        "canonical_csv": str(OUT_CSV),
    }
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"CH6 CUES=183 TTS={len(rows)} KEEP={len(keep_original)} READY={status_counts.get('PENDING_MANUAL_GENERATION',0)} PENDING={status_counts.get('BLOCKED_PENDING_REFERENCE_AUDIO',0)} NEEDS={status_counts.get('BLOCKED_NEEDS_VOICE_TARGET',0)}")
    for item in report["pending_reference_characters"]:
        print(f"PENDING {item['code']} {item['voice_target']} {item['gender']} {item['age']} {item['spoken_lines']}")
    for item in report["needs_voice_target_characters"]:
        print(f"NEEDS {item['code']} {item['gender']} {item['age']} {item['spoken_lines']}")
    print(f"SHA256={hashlib.sha256(OUT_CSV.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
