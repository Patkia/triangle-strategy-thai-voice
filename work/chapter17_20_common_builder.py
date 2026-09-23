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
OMNI_ROOT = ROOT.parent / 'omnivoice-thai-studio'
MAP_PATH = OMNI_ROOT / 'projects/triangle-strategy/voice_target_map.json'
TEXT_INDEX = ROOT / 'work/full_game_text_index/english_thai_identifier_join.csv'
THAI_MAP = ROOT / 'work/new_subtitle_switch/whole_game_unicode_preflight/whole_game_migration_map.csv'
BANK_DIR = ROOT / 'work/opening_trace_phase3/cuesheet_packages'
RESOLVER = ROOT / 'work/chapter1_voice_mapping/voice_runtime_timing_fix_v1/build_timing_fix.py'

HEADERS = [
    'line_no','file_name','self_id','cue','sequence','waveform','awb_stream',
    'character_name','role','gender','voice_target','reference_audio','thai_text',
    'pronunciation_note','prosody_note','status','tts_text','voice_project'
]

BANKS = {
    17: ['MS17_EN','MS17B_EN','MS17F_EN','MS17R_EN','MS17S_EN'],
    18: ['MS18B_EN','MS18F_EN','MS18R_EN','MS18S_EN'],
    19: ['MS19B_EN','MS19F_EN','MS19R_EN','MS19S_EN'],
    20: ['MS20S_EN'],
    21: ['MS21S_EN'],
}

# Age is a casting bucket, not a canonical numeric age.
NAMED = {
    'ABR': ('avlora','npc','female','adult','Avlora'),
    'ANA': ('anna','main','female','young adult','Anna'),
    'ARC': ('archibald','npc','male','elderly','Archibald'),
    'BND': ('benedict','main','male','middle-aged','Benedict'),
    'CLR': ('clarus','npc','male','adult','Clarus'),
    'COR': ('corentin','npc','male','young adult','Corentin'),
    'CRD': ('cordelia','npc','female','young adult','Cordelia'),
    'DEC': ('decimal','npc','male','child','Decimal'),
    'EGS': ('exharme','npc','male','adult','Exharme'),
    'ELA': ('erador','main','male','middle-aged','Erador'),
    'ENG': ('tenebris','npc','male','adult','Tenebris'),
    'ERK': ('erika','npc','female','young adult','Erika'),
    'EZA': ('ezana','npc','female','adult','Ezana'),
    'FLA': ('flanagan','npc','male','adult','Flanagan'),
    'FRE': ('frederica','main','female','young adult','Frederica'),
    'GIB': ('giovanna','npc','female','adult','Giovanna'),
    'GST': ('gustadolph','npc','male','young adult','Gustadolph'),
    'GUR': ('groma','npc','female','elderly','Groma'),
    'HEW': ('hughette','main','female','young adult','Hughette'),
    'HOS': ('hossabara','npc','female','middle-aged / older adult','Hossabara'),
    'IDO': ('idore','npc','male','elderly','Idore'),
    'JRM': ('jerrom','npc','male','adult','Jerrom'),
    'JUL': ('julio','npc','male','young adult','Julio'),
    'KNS': ('kamsell','npc','male','middle-aged','Kamsell'),
    'KOH': ('quahaug','npc','male','child','Quahaug'),
    'LIO': ('lionel','npc','male','middle-aged','Lionel'),
    'LYL': ('lyla','npc','female','adult','Lyla'),
    'MAX': ('maxwell','npc','male','adult','Maxwell'),
    'MED': ('medina','npc','female','young adult','Medina'),
    'MIR': ('milo','npc','female','young adult','Milo'),
    'NAR': ('narve','npc','male','child / teen','Narve'),
    'NNN': ('narrator','narrator','female','adult','Narrator'),
    'PIC': ('piccoletta','npc','female','child','Piccoletta'),
    'PTR': ('patriatte','npc','male','middle-aged','Patriatte'),
    'RDL': ('rudolph','npc','male','young adult','Rudolph'),
    'RLN': ('roland','main','male','young adult','Roland'),
    'ROF': ('rufus','npc','male','adult','Rufus'),
    'SEC': ('sycras','npc','male','middle-aged','Sycras'),
    'SEL': ('serenoa','main','male','young adult','Serenoa'),
    'SMN': ('symon','npc','male','older adult','Symon'),
    'SVR': ('svarog','npc','male','older adult','Svarog'),
    'TRA': ('travis','npc','male','middle-aged','Travis'),
    'TRI': ('trish','npc','female','young adult','Trish'),
    'TRS': ('thalas','npc','male','young adult','Thalas'),
    'YEN': ('jens','npc','male','young adult','Jens'),
    'YRA': ('geela','main','female','adult','Geela'),
}

# Known generic codes whose age/gender is clearer than the normal marker-based fallback.
# Values are (gender, age bucket).
GENERIC_OVERRIDES = {
    'ELD': ('male','old'),
    'MB154T01': ('male','child'),
    'MB155T01': ('female','child'),
    'M375': ('female','child'),
    'M376': ('male','child'),
    'M390': ('female','child'),
    'M367': ('male','child'),
    'M368': ('male','child'),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def punctuation_only(text: str) -> bool:
    value = (text or '').strip()
    return bool(value) and re.fullmatch(r'[.\u2026!?！？\s]+', value) is not None


def target_state(target: str, targets: dict) -> str:
    data = targets.get(target)
    if not isinstance(data, dict):
        return 'NEEDS'
    if data.get('status') == 'PENDING_REFERENCE_AUDIO':
        return 'PENDING'
    if data.get('generation_mode') == 'reference_first' and not (data.get('reference_conditioning') or {}).get('enabled'):
        return 'PENDING'
    return 'READY'


def parse_marker(sid: str, code: str) -> str:
    parts = sid.split('_')
    for i in range(len(parts) - 1):
        if parts[i] in {'M','F','N'} and i + 1 < len(parts) and parts[i + 1] == code:
            return parts[i]
    # All current Ch17-20 cue names put the record marker immediately before the speaker code.
    if len(parts) >= 3 and parts[-2] == code and parts[-3] in {'M','F','N'}:
        return parts[-3]
    return ''


def generic_code_allowed(code: str) -> bool:
    return code == 'ELD' or bool(re.fullmatch(r'M\d+', code)) or bool(re.fullmatch(r'MB\d+T\d+', code)) or code.startswith('MS')


def generic_speaker(code: str, marker: str) -> dict[str, str]:
    if code in GENERIC_OVERRIDES:
        gender, age = GENERIC_OVERRIDES[code]
    else:
        gender = 'female' if marker == 'F' else 'male'
        age = 'adult'

    if gender == 'female' and age == 'child':
        target = 'FEMALE_CHILD_A'
        name = 'เด็กหญิง / NPC'
    elif gender == 'male' and age == 'child':
        target = 'MALE_CHILD_A'
        name = 'เด็กชาย / NPC'
    elif gender == 'female' and age == 'old':
        target = 'FEMALE_OLD_A'
        name = 'หญิงสูงวัย / NPC'
    elif gender == 'male' and age == 'old':
        target = 'MALE_OLD_A'
        name = 'ชายสูงวัย / NPC'
    elif gender == 'female':
        pools = ['FEMALE_YOUNG_A','FEMALE_ADULT_A','FEMALE_ADULT_B']
        target = pools[sum(map(ord, code)) % len(pools)]
        name = 'หญิงชาวเมือง / ทหาร / ผู้ติดตาม'
    else:
        pools = ['MALE_YOUNG_A','MALE_ADULT_A','MALE_ADULT_B','MALE_ADULT_C']
        target = pools[sum(map(ord, code)) % len(pools)]
        name = 'ชายชาวเมือง / ทหาร / ผู้ติดตาม'
    return {'name': name, 'role': 'generic', 'gender': gender, 'age': age, 'target': target}


def speaker_for(code: str, sid: str, targets: dict) -> dict[str, str] | None:
    if code == 'POP':
        return {'hierophant': 'true'}
    if code in NAMED:
        target, role, gender, age, fallback = NAMED[code]
        data = targets.get(target) or {}
        name = data.get('character_name_th') or data.get('character_name_en') or fallback
        return {'name': name, 'role': role, 'gender': gender, 'age': age, 'target': target}
    if generic_code_allowed(code):
        return generic_speaker(code, parse_marker(sid, code))
    return None


def build(chapter: int) -> dict:
    if chapter not in BANKS:
        raise ValueError(f'Unsupported chapter {chapter}')

    out_dir = ROOT / f'work/chapter{chapter}_voice_mapping'
    out_csv = out_dir / f'chapter{chapter}_omnivoice_studio.csv'
    out_report = out_dir / f'chapter{chapter}_build_report.json'
    input_wav = out_dir / 'input_wav'

    text_by = {r['SelfId']: r for r in read_csv(TEXT_INDEX)}
    thai_by = {
        r['SelfId']: r for r in read_csv(THAI_MAP)
        if r.get('join_status') == 'MATCH_EXACT_ONE' and r.get('confidence') == 'HIGH'
    }
    targets = json.loads(MAP_PATH.read_text(encoding='utf-8'))['targets']

    spec = importlib.util.spec_from_file_location(f'ch{chapter}_cri', RESOLVER)
    if spec is None or spec.loader is None:
        raise RuntimeError('Could not load CRI resolver')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    cue_names: list[str] = []
    cue_bank: dict[str, str] = {}
    tables_by: dict[str, dict] = {}
    bank_counts: dict[str, int] = {}
    for bank in BANKS[chapter]:
        bank_file = BANK_DIR / f'{bank}.uexp'
        if not bank_file.is_file():
            raise RuntimeError(f'Missing bank package: {bank_file}')
        _, tables = mod.parse_tables(bank_file)
        tables_by[bank] = tables
        cues = [r['CueName'] for r in tables['CueName'].rows()]
        bank_counts[bank] = len(cues)
        for sid in cues:
            if sid in cue_bank:
                raise RuntimeError(f'Duplicate cue across banks: {sid}')
            cue_bank[sid] = bank
            cue_names.append(sid)

    rows: list[dict] = []
    keep: list[dict] = []
    pending: Counter = Counter()
    needs: Counter = Counter()
    generic_counts: Counter = Counter()

    for sid in cue_names:
        code = sid.split('_')[-2]
        speaker = speaker_for(code, sid, targets)
        if speaker is None:
            raise RuntimeError(f'Unresolved speaker code CH{chapter}: {code} {sid}')

        bank = cue_bank[sid]
        tables = tables_by[bank]
        chain = mod.resolve_chain(tables, sid)
        awb = int(chain['waveform']['StreamAwbId']) + 1
        source = text_by.get(sid)

        if not source:
            keep.append({
                'self_id': sid, 'speaker_code': code, 'bank': bank,
                'classification': 'AUDIO_ONLY_NO_TEXT_INDEX',
                'action': 'KEEP_ORIGINAL_GAME_AUDIO', 'awb_stream': awb,
            })
            continue

        english = source.get('EnglishText', '')
        if code == 'POP':
            keep.append({
                'self_id': sid, 'speaker_code': code, 'bank': bank,
                'classification': 'HIEROPHANT_KEEP_ORIGINAL',
                'action': 'KEEP_ORIGINAL_GAME_AUDIO', 'awb_stream': awb,
                'english_text': english,
            })
            continue

        if punctuation_only(english):
            keep.append({
                'self_id': sid, 'speaker_code': code, 'bank': bank,
                'classification': 'NONVERBAL_PUNCTUATION_ONLY',
                'action': 'KEEP_ORIGINAL_GAME_AUDIO', 'awb_stream': awb,
                'english_text': english,
            })
            continue

        thai = thai_by.get(sid)
        if not thai or not (thai.get('steam_thai') or '').strip():
            raise RuntimeError(f'Missing exact/high Thai: {sid}')

        desired = speaker['target']
        state = target_state(desired, targets)
        target = desired
        status = 'PENDING_MANUAL_GENERATION'
        ref = ''
        if state == 'READY':
            ref = ((targets[desired].get('reference_conditioning') or {}).get('reference_audio') or '')
        elif state == 'PENDING':
            status = 'BLOCKED_PENDING_REFERENCE_AUDIO'
            if speaker['role'] != 'generic':
                pending[(code, speaker['name'], speaker['gender'], speaker['age'], desired)] += 1
        else:
            if speaker['role'] == 'generic':
                raise RuntimeError(f'Generic target missing from map: {desired}')
            target = 'NEEDS_VOICE_TARGET'
            status = 'BLOCKED_NEEDS_VOICE_TARGET'
            needs[(code, speaker['name'], speaker['gender'], speaker['age'], desired)] += 1

        if speaker['role'] == 'generic':
            generic_counts[(code, speaker['gender'], speaker['age'], desired)] += 1

        rows.append({
            'line_no': len(rows) + 1,
            'file_name': sid + '.wav',
            'self_id': sid,
            'cue': chain['cue_index'],
            'sequence': chain['sequence_index'],
            'waveform': chain['waveform_index'],
            'awb_stream': awb,
            'character_name': speaker['name'],
            'role': speaker['role'],
            'gender': speaker['gender'],
            'voice_target': target,
            'reference_audio': ref,
            'thai_text': thai['steam_thai'],
            'pronunciation_note': '',
            'prosody_note': '',
            'status': status,
            'tts_text': '',
            'voice_project': 'triangle-strategy',
        })

    if len(rows) + len(keep) != len(cue_names):
        raise RuntimeError('Coverage mismatch')
    if len({r['self_id'] for r in rows}) != len(rows):
        raise RuntimeError('Duplicate self_id')
    if any(not r['thai_text'].strip() for r in rows):
        raise RuntimeError('Blank Thai text')
    if any(r['voice_target'] == 'hierophant' for r in rows):
        raise RuntimeError('Hierophant leaked into TTS rows')

    out_dir.mkdir(parents=True, exist_ok=True)
    input_wav.mkdir(parents=True, exist_ok=True)
    for old_csv in out_dir.glob('*.csv'):
        if old_csv != out_csv:
            raise RuntimeError(f'Unexpected extra CSV already exists: {old_csv}')

    with out_csv.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    status_counts = Counter(r['status'] for r in rows)
    report = {
        'chapter': chapter,
        'banks': bank_counts,
        'bank_audio_cues': len(cue_names),
        'tts_rows': len(rows),
        'keep_original_rows': len(keep),
        'coverage_equation': f'{len(rows)} TTS + {len(keep)} original = {len(cue_names)}/{len(cue_names)}',
        'status_counts': dict(status_counts),
        'pending_reference_characters': [
            {'code': k[0], 'character_name': k[1], 'gender': k[2], 'age': k[3], 'voice_target': k[4], 'spoken_lines': v}
            for k, v in sorted(pending.items())
        ],
        'needs_voice_target_characters': [
            {'code': k[0], 'character_name': k[1], 'gender': k[2], 'age': k[3], 'desired_target': k[4], 'spoken_lines': v}
            for k, v in sorted(needs.items())
        ],
        'generic_assignments': [
            {'code': k[0], 'gender': k[1], 'age': k[2], 'voice_target': k[3], 'spoken_lines': v}
            for k, v in sorted(generic_counts.items())
        ],
        'keep_original_detail': keep,
        'hierophant_policy': 'POP / Hierophant is always kept as original game audio and never included in Thai TTS CSV.',
        'canonical_csv': str(out_csv),
    }
    report['sha256'] = hashlib.sha256(out_csv.read_bytes()).hexdigest()
    out_report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    print(
        f"CH{chapter} CUES={len(cue_names)} TTS={len(rows)} KEEP={len(keep)} "
        f"READY={status_counts.get('PENDING_MANUAL_GENERATION', 0)} "
        f"PENDING={status_counts.get('BLOCKED_PENDING_REFERENCE_AUDIO', 0)} "
        f"NEEDS={status_counts.get('BLOCKED_NEEDS_VOICE_TARGET', 0)}"
    )
    for item in report['pending_reference_characters']:
        print(f"PENDING {item['code']} {item['voice_target']} {item['gender']} {item['age']} {item['spoken_lines']}")
    for item in report['needs_voice_target_characters']:
        print(f"NEEDS {item['code']} {item['character_name']} {item['gender']} {item['age']} {item['spoken_lines']}")
    print('SHA256=' + report['sha256'])
    return report
