from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OMNI_ROOT = ROOT.parent / "omnivoice-thai-studio"
MAP_PATH = OMNI_ROOT / "projects/triangle-strategy/voice_target_map.json"
TEXT_INDEX = ROOT / "work/full_game_text_index/english_thai_identifier_join.csv"
THAI_MAP = ROOT / "work/new_subtitle_switch/whole_game_unicode_preflight/whole_game_migration_map.csv"
BANK_DIR = ROOT / "work/opening_trace_phase3/cuesheet_packages"
RESOLVER = ROOT / "work/chapter1_voice_mapping/voice_runtime_timing_fix_v1/build_timing_fix.py"

HEADERS = [
    "line_no", "file_name", "self_id", "cue", "sequence", "waveform", "awb_stream",
    "character_name", "role", "gender", "voice_target", "reference_audio", "thai_text",
    "pronunciation_note", "prosody_note", "status", "tts_text", "voice_project",
]

BANKS = {
    11: ["MS11_EN"],
    12: ["MS12_EN"],
    13: ["MS13_EN"],
}

# Named speaker targets. Age is a casting-age bucket, not a canonical numeric age.
NAMED = {
    "ABR": ("avlora", "npc", "female", "adult", "Avlora"),
    "ANA": ("anna", "main", "female", "young adult", "Anna"),
    "BKR": ("booker", "npc", "male", "middle-aged", "Booker"),
    "BND": ("benedict", "main", "male", "middle-aged", "Benedict"),
    "CRD": ("cordelia", "npc", "female", "young adult", "Cordelia"),
    "EGS": ("exharme", "npc", "male", "adult", "Exharme"),
    "ELA": ("erador", "main", "male", "middle-aged", "Erador"),
    "ERK": ("erika", "npc", "female", "young adult", "Erika"),
    "FRE": ("frederica", "main", "female", "young adult", "Frederica"),
    "GST": ("gustadolph", "npc", "male", "young adult", "Gustadolph"),
    "HEW": ("hughette", "main", "female", "young adult", "Hughette"),
    "IDO": ("idore", "npc", "male", "elderly", "Idore"),
    "JRM": ("jerrom", "npc", "male", "adult", "Jerrom"),
    "KNS": ("kamsell", "npc", "male", "middle-aged", "Kamsell"),
    "LND": ("landroi", "npc", "male", "middle-aged", "Landroi"),
    "LYL": ("lyla", "npc", "female", "adult", "Lyla"),
    "NNN": ("narrator", "narrator", "female", "adult", "Narrator"),
    "RLN": ("roland", "main", "male", "young adult", "Roland"),
    "ROF": ("rufus", "npc", "male", "adult", "Rufus"),
    "SEL": ("serenoa", "main", "male", "young adult", "Serenoa"),
    "SLS": ("sorsley", "npc", "male", "middle-aged", "Sorsley"),
    "SLV": ("silvio", "npc", "male", "young adult", "Silvio"),
    "TRA": ("travis", "npc", "male", "middle-aged", "Travis"),
    "TRI": ("trish", "npc", "female", "young adult", "Trish"),
    "TRS": ("thalas", "npc", "male", "young adult", "Thalas"),
    "YRA": ("geela", "main", "female", "adult", "Geela"),
    "CLR": ("clarus", "npc", "male", "adult", "Clarus"),
    "SVR": ("svarog", "npc", "male", "older adult", "Svarog"),
    # Tenebris dialogue uses ENG in story scene banks.
    "ENG": ("tenebris", "npc", "male", "adult", "Tenebris"),
    "MIR": ("milo", "npc", "female", "young adult", "Milo"),
    "RDL": ("rudolph", "npc", "male", "young adult", "Rudolph"),
    "SEC": ("sycras", "npc", "male", "middle-aged", "Sycras"),
}

# Generic scene speakers reuse existing approved Thai voice pools.
GENERIC = {
    11: {
        "ELD": ("ผู้อาวุโสชาวโรเซลล์", "male", "older adult", "MALE_OLD_A"),
        "M087": ("เจ้าหน้าที่ไฮแซนต์", "male", "adult", "MALE_ADULT_B"),
        "M088": ("ชาวโรเซลล์", "male", "adult", "MALE_ADULT_A"),
        "M090": ("ชาวโรเซลล์", "male", "adult", "MALE_ADULT_C"),
        "M318": ("ผู้คุมไฮแซนต์", "male", "adult", "MALE_ADULT_C"),
        "M319": ("ชาวโรเซลล์", "male", "adult", "MALE_ADULT_A"),
        "M320": ("ชาวโรเซลล์", "male", "adult", "MALE_ADULT_B"),
        "M321": ("หญิงชาวโรเซลล์", "female", "adult", "FEMALE_ADULT_A"),
        "MS11X21B01M01": ("ทหารสมทบ", "male", "adult", "MALE_ADULT_B"),
    },
    12: {
        "ELD": ("ผู้อาวุโสชาวโรเซลล์", "male", "older adult", "MALE_OLD_A"),
        "M098": ("ชาวโรเซลล์", "male", "adult", "MALE_ADULT_A"),
        "M099": ("ชาวโรเซลล์", "male", "adult", "MALE_ADULT_B"),
        "M419": ("ชาวโรเซลล์", "male", "adult", "MALE_ADULT_C"),
    },
    13: {
        "M169": ("ผู้ส่งสาร", "male", "adult", "MALE_ADULT_A"),
        "M170": ("เจ้าหน้าที่ชายแดน", "male", "adult", "MALE_ADULT_B"),
        "M171": ("ทหารเอสฟรอสต์", "male", "adult", "MALE_ADULT_C"),
        "M176": ("หญิง", "female", "adult", "FEMALE_ADULT_A"),
        "M177": ("ชาย", "male", "adult", "MALE_ADULT_A"),
        "M178": ("หญิง", "female", "adult", "FEMALE_ADULT_A"),
        "M180": ("ชาวเมือง", "male", "adult", "MALE_ADULT_A"),
        "M181": ("หญิงชาวเมือง", "female", "adult", "FEMALE_ADULT_A"),
        "M182": ("ทหารเอสฟรอสต์", "male", "adult", "MALE_ADULT_B"),
        "M183": ("ทหารเอสฟรอสต์", "male", "adult", "MALE_ADULT_C"),
        "M184": ("ผู้ส่งสาร", "male", "young adult", "MALE_YOUNG_A"),
        "M185": ("ทหารเอสฟรอสต์", "male", "adult", "MALE_ADULT_A"),
        "M186": ("ทหารเอสฟรอสต์", "male", "adult", "MALE_ADULT_B"),
        "M187": ("ทหารเอสฟรอสต์", "male", "adult", "MALE_ADULT_C"),
        "M188": ("ทหารเอสฟรอสต์", "male", "adult", "MALE_ADULT_A"),
        "M189": ("ทหารเอสฟรอสต์", "male", "young adult", "MALE_YOUNG_B"),
        "M192": ("ผู้ส่งสารเอสฟรอสต์", "male", "adult", "MALE_ADULT_B"),
        "M193": ("ทหาร", "male", "adult", "MALE_ADULT_C"),
        "M322": ("ชาวเมือง", "male", "adult", "MALE_ADULT_A"),
        "MS13X24B01M01": ("ทหาร", "male", "adult", "MALE_ADULT_A"),
        "MS13X24B01M02": ("ทหาร", "male", "young adult", "MALE_YOUNG_B"),
        "MS13X24B01M03": ("ทหาร", "male", "adult", "MALE_ADULT_C"),
    },
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


def speaker_for(chapter: int, code: str, targets: dict) -> dict | None:
    if code == "POP":
        return {"hierophant": True}
    if code in NAMED:
        target, role, gender, age, fallback_name = NAMED[code]
        td = targets.get(target) or {}
        name = td.get("character_name_th") or td.get("character_name_en") or fallback_name
        return {"name": name, "role": role, "gender": gender, "age": age, "target": target}
    g = GENERIC[chapter].get(code)
    if g:
        name, gender, age, target = g
        return {"name": name, "role": "generic", "gender": gender, "age": age, "target": target}
    return None


def build(chapter: int) -> dict:
    if chapter not in BANKS:
        raise ValueError(chapter)
    out_dir = ROOT / f"work/chapter{chapter}_voice_mapping"
    out_csv = out_dir / f"chapter{chapter}_omnivoice_studio.csv"
    out_report = out_dir / f"chapter{chapter}_build_report.json"

    text_by_id = {r["SelfId"]: r for r in read_csv(TEXT_INDEX)}
    thai_by_id = {r["SelfId"]: r for r in read_csv(THAI_MAP) if r.get("join_status") == "MATCH_EXACT_ONE" and r.get("confidence") == "HIGH"}
    targets = json.loads(MAP_PATH.read_text(encoding="utf-8"))["targets"]

    spec = importlib.util.spec_from_file_location(f"chapter{chapter}_cri", RESOLVER)
    if not spec or not spec.loader:
        raise RuntimeError("Could not load CRI resolver")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    bank_tables = {}
    cue_bank = {}
    cue_names = []
    bank_counts = {}
    for bank in BANKS[chapter]:
        path = BANK_DIR / f"{bank}.uexp"
        _, tables = mod.parse_tables(path)
        bank_tables[bank] = tables
        cues = [r["CueName"] for r in tables["CueName"].rows()]
        bank_counts[bank] = len(cues)
        for sid in cues:
            if sid in cue_bank:
                raise RuntimeError(f"Duplicate cue across banks: {sid}")
            cue_bank[sid] = bank
            cue_names.append(sid)

    rows = []
    keep_original = []
    pending = Counter()
    needs = Counter()

    for sid in cue_names:
        bank = cue_bank[sid]
        tables = bank_tables[bank]
        code = sid.split("_")[-2]
        speaker = speaker_for(chapter, code, targets)
        if speaker is None:
            raise RuntimeError(f"Unresolved speaker code CH{chapter}: {code} ({sid})")
        chain = mod.resolve_chain(tables, sid)
        awb_stream = int(chain["waveform"]["StreamAwbId"]) + 1
        source = text_by_id.get(sid)
        if not source:
            keep_original.append({"self_id": sid, "speaker_code": code, "bank": bank, "classification": "AUDIO_ONLY_NO_TEXT_INDEX", "action": "KEEP_ORIGINAL_GAME_AUDIO", "awb_stream": awb_stream})
            continue
        english = source.get("EnglishText", "")
        if code == "POP":
            keep_original.append({"self_id": sid, "speaker_code": code, "bank": bank, "classification": "HIEROPHANT_KEEP_ORIGINAL", "action": "KEEP_ORIGINAL_GAME_AUDIO", "awb_stream": awb_stream, "english_text": english})
            continue
        if punctuation_only(english):
            keep_original.append({"self_id": sid, "speaker_code": code, "bank": bank, "classification": "NONVERBAL_PUNCTUATION_ONLY", "action": "KEEP_ORIGINAL_GAME_AUDIO", "awb_stream": awb_stream, "english_text": english})
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
            "line_no": len(rows) + 1,
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
            "reference_audio": ref,
            "thai_text": thai["steam_thai"],
            "pronunciation_note": "",
            "prosody_note": "",
            "status": status,
            "tts_text": "",
            "voice_project": "triangle-strategy",
        })

    if len(rows) + len(keep_original) != len(cue_names):
        raise RuntimeError(f"Coverage mismatch CH{chapter}")
    if len({r["self_id"] for r in rows}) != len(rows):
        raise RuntimeError(f"Duplicate self_id CH{chapter}")
    if any(not r["thai_text"].strip() for r in rows):
        raise RuntimeError(f"Blank Thai CH{chapter}")
    if any(r["voice_target"] == "hierophant" for r in rows):
        raise RuntimeError(f"Hierophant leaked into TTS CSV CH{chapter}")

    out_dir.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    status_counts = Counter(r["status"] for r in rows)
    report = {
        "chapter": chapter,
        "banks": bank_counts,
        "bank_audio_cues": len(cue_names),
        "tts_rows": len(rows),
        "keep_original_rows": len(keep_original),
        "coverage_equation": f"{len(rows)} TTS + {len(keep_original)} original = {len(cue_names)}/{len(cue_names)}",
        "status_counts": dict(status_counts),
        "pending_reference_characters": [
            {"code": k[0], "character_name": k[1], "gender": k[2], "age": k[3], "voice_target": k[4], "spoken_lines": v}
            for k, v in sorted(pending.items())
        ],
        "needs_voice_target_characters": [
            {"code": k[0], "character_name": k[1], "gender": k[2], "age": k[3], "desired_target": k[4], "spoken_lines": v}
            for k, v in sorted(needs.items())
        ],
        "keep_original_detail": keep_original,
        "hierophant_policy": "Always keep original game audio; never include POP in Thai TTS CSV.",
        "canonical_csv": str(out_csv),
        "sha256": hashlib.sha256(out_csv.read_bytes()).hexdigest(),
    }
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"CH{chapter} CUES={len(cue_names)} TTS={len(rows)} KEEP={len(keep_original)} READY={status_counts.get('PENDING_MANUAL_GENERATION',0)} PENDING={status_counts.get('BLOCKED_PENDING_REFERENCE_AUDIO',0)} NEEDS={status_counts.get('BLOCKED_NEEDS_VOICE_TARGET',0)}")
    for item in report["pending_reference_characters"]:
        print(f"PENDING {item['code']} {item['voice_target']} {item['gender']} {item['age']} {item['spoken_lines']}")
    for item in report["needs_voice_target_characters"]:
        print(f"NEEDS {item['code']} {item['character_name']} {item['gender']} {item['age']} {item['spoken_lines']}")
    print(f"SHA256={report['sha256']}")
    return report
