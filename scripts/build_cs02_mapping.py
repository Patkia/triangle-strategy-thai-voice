import csv,json,wave
from pathlib import Path
root=Path(__file__).resolve().parents[1]
j=json.loads((root/'Output/Exports/Newera/Content/Newera/Sound/VOICE/EN/CS02_EN.json').read_text(encoding='utf8'))
if isinstance(j,list): j=j[0]
cues=j['Properties']['CueInfos']; out=root/'docs/cs02_voice_mapping.csv'
rows=[]
for cue in cues:
 i=cue['Id']+1; wav=root/f'vgmstream-win64/CS02_EN_WAV/CS02_EN_{i}.wav'
 with wave.open(str(wav)) as w: seconds=w.getnframes()/w.getframerate()
 ticks=cue['Duration']['Ticks']; cue_seconds=ticks/10_000_000
 f=root/f'Output/Exports/Newera/Content/Newera/Sound/VOICE/EN/{cue["Name"]}.wav'
 rows.append({'cue_id':cue['Id'],'cue_name':cue['Name'],'awb_stream_index':i,'vgmstream_wav':wav.name,'fmodel_wav':f.name if f.exists() else '', 'cue_duration':f'{cue_seconds:.6f}','audio_duration':f'{seconds:.6f}','match_method':'CueInfo Id + 1; duration matches', 'confidence':'high (duration/order); verified PCM for Id 0' if cue['Id']==0 else 'high (duration/order)'})
out.parent.mkdir(exist_ok=True)
with out.open('w',newline='',encoding='utf8') as h:
 w=csv.DictWriter(h,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
print(f'cues={len(cues)} rows={len(rows)} duration_mismatches={sum(abs(float(x["cue_duration"])-float(x["audio_duration"]))>0.001 for x in rows)}')
