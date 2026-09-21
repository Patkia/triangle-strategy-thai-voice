"""Fail-closed resolver for the proven Switch DataTable serialization subset."""
from __future__ import annotations
import struct
from dataclasses import dataclass

class ResolveError(ValueError): pass
def i32(b,o): return struct.unpack_from('<i',b,o)[0]
def i64(b,o): return struct.unpack_from('<q',b,o)[0]
def fname(b,o,names):
    idx,num=struct.unpack_from('<II',b,o)
    if idx>=len(names) or num: raise ResolveError('invalid FName')
    return names[idx],o+8
def fstr(b,o):
    n=i32(b,o)
    if n==0:return '',o+4
    if n>0:
        q=o+4+n
        if q>len(b) or b[q-1]!=0:raise ResolveError('bad ansi FString')
        return b[o+4:q-1].decode('utf-8'),q
    q=o+4+(-n*2)
    if q>len(b) or b[q-2:q]!=b'\0\0':raise ResolveError('bad wide FString')
    return b[o+4:q-2].decode('utf-16le'),q
def names_from_uasset(b):
    starts=[]; needle=b'/Game/'
    p=0
    while True:
        p=b.find(needle,p)
        if p<0:break
        if p>=4 and 0<i32(b,p-4)<4096: starts.append(p-4)
        p+=1
    for start in starts:
        out=[]; o=start
        try:
            for _ in range(4096):
                s,q=fstr(b,o)
                if not s: raise ResolveError('empty name')
                if q+4>len(b): raise ResolveError('name hash out of range')
                out.append(s);o=q+4
        except (ResolveError,UnicodeDecodeError,struct.error):
            if len(out)>=17 and 'None' in out and 'SelfId' in out and 'Text' in out:return out
    raise ResolveError('unrecognized name map')
def prop(b,o,names):
    start=o; name,o=fname(b,o,names)
    if name=='None':return None,o
    typ,o=fname(b,o,names); sizeo=o; size=i32(b,o);o+=4; arr=i32(b,o);o+=4
    if o>=len(b):raise ResolveError('property tag EOF')
    guid=b[o];o+=1
    if arr or guid or size<0:raise ResolveError('unsupported property tag')
    end=o+size
    if end>len(b):raise ResolveError('property payload EOF')
    return {'name':name,'type':typ,'size':size,'start':start,'size_offset':sizeo,'data_start':o,'data_end':end},end
def resolve(uasset,uexp,selfid,rowkey=None,expected_text=None):
    names=names_from_uasset(uasset);o=0
    first,o=prop(uexp,o,names)
    if not first or first['name']!='RowStruct' or first['type']!='ObjectProperty':raise ResolveError('not proven DataTable RowStruct layout')
    term,o=fname(uexp,o,names)
    if term!='None':raise ResolveError('missing DataTable terminator')
    if o+8>len(uexp):raise ResolveError('missing row header')
    prefix=i32(uexp,o);o+=4; count=i32(uexp,o);o+=4
    if count<0 or count>100000:raise ResolveError('invalid row count')
    targets=[]; rows=[]
    for _ in range(count):
        rs=o; rn,o=fname(uexp,o,names); props=[]
        while True:
            p,o=prop(uexp,o,names)
            if p is None:break
            props.append(p)
        sidp=next((p for p in props if p['name']=='SelfId'),None); textp=next((p for p in props if p['name']=='Text'),None)
        if not sidp or not textp or sidp['type']!='NameProperty' or sidp['size']!=8 or textp['type']!='StrProperty':raise ResolveError('unsupported row properties')
        sid,_=fname(uexp,sidp['data_start'],names); text,te=fstr(uexp,textp['data_start'])
        if te!=textp['data_end'] or textp['size']!=te-textp['data_start']:raise ResolveError('Text FString size mismatch')
        rec={'rowkey':rn,'selfid':sid,'text':text,'row_start':rs,'row_end':o,'text_size_offset':textp['size_offset'],'text_data_start':textp['data_start'],'text_data_end':textp['data_end'],'text_size':textp['size']}
        rows.append(rec)
        if sid==selfid and (rowkey is None or rn==rowkey):targets.append(rec)
    if o!=len(uexp)-4:raise ResolveError('unexpected export footer/layout')
    if len(targets)!=1:raise ResolveError('target count '+str(len(targets)))
    t=targets[0]
    if expected_text is not None and t['text']!=expected_text:raise ResolveError('expected old text assertion failed')
    return {'names':len(names),'rows':rows,'target':t,'row_count':count,'prefix':prefix}
def export_serial_fields(uasset,uexp):
    a=len(uexp)-4;b=len(uasset); hits=[]
    for o in range(len(uasset)-16):
        if i64(uasset,o)==a and i64(uasset,o+8)==b:hits.append(o)
    if len(hits)!=1:raise ResolveError('unique Export.SerialSize/Offset pair not found: '+str(len(hits)))
    return hits[0],hits[0]+8
