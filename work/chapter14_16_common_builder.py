from __future__ import annotations
import csv, hashlib, importlib.util, json, re, sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OMNI_ROOT=ROOT.parent/'omnivoice-thai-studio'
MAP_PATH=OMNI_ROOT/'projects/triangle-strategy/voice_target_map.json'
TEXT_INDEX=ROOT/'work/full_game_text_index/english_thai_identifier_join.csv'
THAI_MAP=ROOT/'work/new_subtitle_switch/whole_game_unicode_preflight/whole_game_migration_map.csv'
BANK_DIR=ROOT/'work/opening_trace_phase3/cuesheet_packages'
RESOLVER=ROOT/'work/chapter1_voice_mapping/voice_runtime_timing_fix_v1/build_timing_fix.py'
HEADERS=['line_no','file_name','self_id','cue','sequence','waveform','awb_stream','character_name','role','gender','voice_target','reference_audio','thai_text','pronunciation_note','prosody_note','status','tts_text','voice_project']
BANKS={14:['MS14_EN'],15:['MS15_EN'],16:['MS16_EN']}

# Age = casting bucket, not canonical numeric age.
NAMED={
'ABR':('avlora','npc','female','adult','Avlora'),'ANA':('anna','main','female','young adult','Anna'),
'BND':('benedict','main','male','middle-aged','Benedict'),'CRD':('cordelia','npc','female','young adult','Cordelia'),
'EGS':('exharme','npc','male','adult','Exharme'),'ELA':('erador','main','male','middle-aged','Erador'),
'ERK':('erika','npc','female','young adult','Erika'),'FRE':('frederica','main','female','young adult','Frederica'),
'GST':('gustadolph','npc','male','young adult','Gustadolph'),'HEW':('hughette','main','female','young adult','Hughette'),
'IDO':('idore','npc','male','elderly','Idore'),'JRM':('jerrom','npc','male','adult','Jerrom'),
'KNS':('kamsell','npc','male','middle-aged','Kamsell'),'LYL':('lyla','npc','female','adult','Lyla'),
'MIR':('milo','npc','female','young adult','Milo'),'NNN':('narrator','narrator','female','adult','Narrator'),
'PTR':('patriatte','npc','male','middle-aged','Patriatte'),'RLN':('roland','main','male','young adult','Roland'),
'SEC':('sycras','npc','male','middle-aged','Sycras'),'SEL':('serenoa','main','male','young adult','Serenoa'),
'SMN':('symon','npc','male','older adult','Symon'),'SVR':('svarog','npc','male','older adult','Svarog'),
'TRA':('travis','npc','male','middle-aged','Travis'),'TRI':('trish','npc','female','young adult','Trish'),
'TRS':('thalas','npc','male','young adult','Thalas'),'YRA':('geela','main','female','adult','Geela'),
'ENG':('tenebris','npc','male','adult','Tenebris'),
'ORL':('orlaea','npc','female','adult / middle-aged','Orlaea'),
}

GENERIC_CODES={
14:['M213','M215'],
15:['M234','M235','M236','M237','M238','M239','M240','M241','M242','M243','M244','M245','M246','M247','M248','M250','M251','M252','M253','M255','M256','M257','M258','M259','M260','M261','M265','M266','M268','M270','M271','M274','M275','M325','M326','M328','M380','MS15X33B01M01'],
16:['M277','M336','M337','M338','M339','M341','M409','MB011T01','MS16X34B01M01','MS16X34B01M02'],
}
# Known child / female generic overrides. Everything else is adult male unless cue evidence says female.
CHILD_MALE={'M235','M246'}
CHILD_FEMALE={'M245','M259'}
FEMALE_GENERIC={'M234','M239','M241','M244','M245','M250','M257','M259','M380'}

def read_csv(path):
    with path.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def punctuation_only(text):
    v=(text or '').strip(); return bool(v) and re.fullmatch(r'[.\u2026!?！？\s]+',v) is not None

def target_state(target,targets):
    d=targets.get(target)
    if not isinstance(d,dict): return 'NEEDS'
    if d.get('status')=='PENDING_REFERENCE_AUDIO': return 'PENDING'
    if d.get('generation_mode')=='reference_first' and not (d.get('reference_conditioning') or {}).get('enabled'): return 'PENDING'
    return 'READY'

def generic_speaker(code):
    if code in CHILD_FEMALE: return {'name':'เด็กหญิง','role':'generic','gender':'female','age':'child','target':'FEMALE_CHILD_A'}
    if code in CHILD_MALE: return {'name':'เด็กชาย','role':'generic','gender':'male','age':'child','target':'MALE_CHILD_A'}
    if code in FEMALE_GENERIC:
        pools=['FEMALE_YOUNG_A','FEMALE_ADULT_A','FEMALE_ADULT_B']; target=pools[sum(map(ord,code))%len(pools)]
        return {'name':'หญิงชาวเมือง/ผู้ติดตาม','role':'generic','gender':'female','age':'adult','target':target}
    pools=['MALE_YOUNG_A','MALE_ADULT_A','MALE_ADULT_B','MALE_ADULT_C']; target=pools[sum(map(ord,code))%len(pools)]
    return {'name':'ชายชาวเมือง/ทหาร/ผู้ติดตาม','role':'generic','gender':'male','age':'adult','target':target}

def speaker_for(chapter,code,targets):
    if code=='POP': return {'hierophant':True}
    if code in NAMED:
        target,role,gender,age,fallback=NAMED[code]; td=targets.get(target) or {}
        name=td.get('character_name_th') or td.get('character_name_en') or fallback
        return {'name':name,'role':role,'gender':gender,'age':age,'target':target}
    if code in GENERIC_CODES[chapter]: return generic_speaker(code)
    return None

def build(chapter):
    out_dir=ROOT/f'work/chapter{chapter}_voice_mapping'; out_csv=out_dir/f'chapter{chapter}_omnivoice_studio.csv'; out_report=out_dir/f'chapter{chapter}_build_report.json'
    text_by={r['SelfId']:r for r in read_csv(TEXT_INDEX)}
    thai_by={r['SelfId']:r for r in read_csv(THAI_MAP) if r.get('join_status')=='MATCH_EXACT_ONE' and r.get('confidence')=='HIGH'}
    targets=json.loads(MAP_PATH.read_text(encoding='utf-8'))['targets']
    spec=importlib.util.spec_from_file_location(f'ch{chapter}_cri',RESOLVER)
    if spec is None or spec.loader is None:
        raise RuntimeError('Could not load CRI resolver')
    mod=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=mod
    spec.loader.exec_module(mod)
    cue_names=[]; cue_bank={}; tables_by={}; bank_counts={}
    for bank in BANKS[chapter]:
        _,tables=mod.parse_tables(BANK_DIR/f'{bank}.uexp'); tables_by[bank]=tables; cues=[r['CueName'] for r in tables['CueName'].rows()]; bank_counts[bank]=len(cues)
        for sid in cues:
            if sid in cue_bank: raise RuntimeError(f'duplicate cue across banks {sid}')
            cue_bank[sid]=bank; cue_names.append(sid)
    rows=[]; keep=[]; pending=Counter(); needs=Counter()
    for sid in cue_names:
        code=sid.split('_')[-2]; speaker=speaker_for(chapter,code,targets)
        if speaker is None: raise RuntimeError(f'Unresolved speaker code CH{chapter}: {code} {sid}')
        bank=cue_bank[sid]; tables=tables_by[bank]; chain=mod.resolve_chain(tables,sid); awb=int(chain['waveform']['StreamAwbId'])+1
        source=text_by.get(sid)
        if not source:
            keep.append({'self_id':sid,'speaker_code':code,'bank':bank,'classification':'AUDIO_ONLY_NO_TEXT_INDEX','action':'KEEP_ORIGINAL_GAME_AUDIO','awb_stream':awb}); continue
        english=source.get('EnglishText','')
        if code=='POP':
            keep.append({'self_id':sid,'speaker_code':code,'bank':bank,'classification':'HIEROPHANT_KEEP_ORIGINAL','action':'KEEP_ORIGINAL_GAME_AUDIO','awb_stream':awb,'english_text':english}); continue
        if punctuation_only(english):
            keep.append({'self_id':sid,'speaker_code':code,'bank':bank,'classification':'NONVERBAL_PUNCTUATION_ONLY','action':'KEEP_ORIGINAL_GAME_AUDIO','awb_stream':awb,'english_text':english}); continue
        thai=thai_by.get(sid)
        if not thai or not (thai.get('steam_thai') or '').strip(): raise RuntimeError(f'Missing exact/high Thai: {sid}')
        desired=speaker['target']; state=target_state(desired,targets); target=desired; status='PENDING_MANUAL_GENERATION'; ref=''
        if state=='READY': ref=((targets[desired].get('reference_conditioning') or {}).get('reference_audio') or '')
        elif state=='PENDING':
            status='BLOCKED_PENDING_REFERENCE_AUDIO'
            if speaker['role']!='generic': pending[(code,speaker['name'],speaker['gender'],speaker['age'],desired)]+=1
        else:
            if speaker['role']=='generic': raise RuntimeError(f'Generic target missing from map: {desired}')
            target='NEEDS_VOICE_TARGET'; status='BLOCKED_NEEDS_VOICE_TARGET'; needs[(code,speaker['name'],speaker['gender'],speaker['age'],desired)]+=1
        rows.append({'line_no':len(rows)+1,'file_name':sid+'.wav','self_id':sid,'cue':chain['cue_index'],'sequence':chain['sequence_index'],'waveform':chain['waveform_index'],'awb_stream':awb,'character_name':speaker['name'],'role':speaker['role'],'gender':speaker['gender'],'voice_target':target,'reference_audio':ref,'thai_text':thai['steam_thai'],'pronunciation_note':'','prosody_note':'','status':status,'tts_text':'','voice_project':'triangle-strategy'})
    if len(rows)+len(keep)!=len(cue_names): raise RuntimeError('coverage mismatch')
    if len({r['self_id'] for r in rows})!=len(rows): raise RuntimeError('duplicate self_id')
    if any(not r['thai_text'].strip() for r in rows): raise RuntimeError('blank thai')
    if any(r['voice_target']=='hierophant' for r in rows): raise RuntimeError('hierophant leaked')
    out_dir.mkdir(parents=True,exist_ok=True)
    with out_csv.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=HEADERS); w.writeheader(); w.writerows(rows)
    sc=Counter(r['status'] for r in rows)
    report={'chapter':chapter,'banks':bank_counts,'bank_audio_cues':len(cue_names),'tts_rows':len(rows),'keep_original_rows':len(keep),'coverage_equation':f'{len(rows)} TTS + {len(keep)} original = {len(cue_names)}/{len(cue_names)}','status_counts':dict(sc),'pending_reference_characters':[{'code':k[0],'character_name':k[1],'gender':k[2],'age':k[3],'voice_target':k[4],'spoken_lines':v} for k,v in sorted(pending.items())],'needs_voice_target_characters':[{'code':k[0],'character_name':k[1],'gender':k[2],'age':k[3],'desired_target':k[4],'spoken_lines':v} for k,v in sorted(needs.items())],'keep_original_detail':keep,'hierophant_policy':'Always keep original game audio; never include POP in Thai TTS CSV.','canonical_csv':str(out_csv)}
    report['sha256']=hashlib.sha256(out_csv.read_bytes()).hexdigest(); out_report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f"CH{chapter} CUES={len(cue_names)} TTS={len(rows)} KEEP={len(keep)} READY={sc.get('PENDING_MANUAL_GENERATION',0)} PENDING={sc.get('BLOCKED_PENDING_REFERENCE_AUDIO',0)} NEEDS={sc.get('BLOCKED_NEEDS_VOICE_TARGET',0)}")
    for i in report['pending_reference_characters']: print(f"PENDING {i['code']} {i['voice_target']} {i['gender']} {i['age']} {i['spoken_lines']}")
    for i in report['needs_voice_target_characters']: print(f"NEEDS {i['code']} {i['character_name']} {i['gender']} {i['age']} {i['spoken_lines']}")
    print('SHA256='+report['sha256'])
    return report
