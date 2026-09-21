from pathlib import Path
import struct,shutil
from generic_datatable_strproperty import resolve,export_serial_fields,ResolveError
def enc(s):
 if s.isascii():
  p=s.encode('utf-8')+b'\0';return struct.pack('<i',len(p))+p
 p=s.encode('utf-16le')+b'\0\0';return struct.pack('<i',-(len(p)//2))+p
def patch_pair(source_base:Path,out_base:Path,replacements:list[dict]):
 ua=source_base.with_suffix('.uasset').read_bytes(); ux=source_base.with_suffix('.uexp').read_bytes(); ss,so=export_serial_fields(ua,ux)
 table=resolve(ua,ux,replacements[0]['SelfId'],replacements[0]['rowkey'])
 index={(q['selfid'],q['rowkey']):q for q in table['rows']};targets=[]
 for r in replacements:
  q=index.get((r['SelfId'],r['rowkey']))
  if q is None:raise ResolveError('target missing from parsed table')
  targets.append((q,r['text']))
 if len({q['selfid'] for q,_ in targets})!=len(targets):raise ResolveError('duplicate patch target')
 b=bytearray(ux); delta=0
 for q,text in sorted(targets,key=lambda z:z[0]['text_size_offset'],reverse=True):
  v=enc(text); old=q['text_data_end']-q['text_data_start']; d=len(v)-old
  struct.pack_into('<i',b,q['text_size_offset'],len(v));b[q['text_data_start']:q['text_data_end']]=v;delta+=d
 pu=bytearray(ua);struct.pack_into('<q',pu,ss,struct.unpack_from('<q',ua,ss)[0]+delta)
 if struct.unpack_from('<q',pu,ss)[0]!=len(b)-4 or struct.unpack_from('<q',pu,so)[0]!=len(ua):raise ResolveError('serial metadata mismatch')
 out_base.parent.mkdir(parents=True,exist_ok=True);out_base.with_suffix('.uasset').write_bytes(pu);out_base.with_suffix('.uexp').write_bytes(b)
 return delta
