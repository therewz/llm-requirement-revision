#!/usr/bin/env python3
"""Prepare local masked specification packets without executing participant content."""
import argparse,csv,hashlib,json,random,re,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/replication_snapshot/Data'
SEED=20261027
PRIOR={'S0001','S0013','S0037','S0025','S0049','S0050','S0014','S0027','S0036','S0067'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read_rows(p):
 out=[]
 with p.open(newline='',encoding='utf-8-sig') as f:
  reader=csv.DictReader(f);reader.fieldnames;previous=reader.line_num
  for number,row in enumerate(reader,2):
   row['_record']=number;row['_line_start']=previous+1;row['_line_end']=reader.line_num;previous=reader.line_num;out.append(row)
 return out

def redact(text):
 patterns=[('email',r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),('long_numeric_identifier',r'\b\d{7,12}\b'),('labeled_identity',r'(?im)^\s*(?:student name|participant name|full name|student id|student number|name)\s*:\s*[^\n;,]+')]
 notes=[]
 for kind,pattern in patterns:
  def sub(m):
   notes.append({'kind':kind,'start':m.start(),'length':len(m.group())});return '[REDACTED_METADATA]'
  text=re.sub(pattern,sub,text)
 return text,notes

def write_csv(path,rows):
 with path.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();out=(ROOT/a.out).resolve()
 if not out.is_relative_to(ROOT) or out.exists():raise SystemExit('Use new directory inside project')
 freeze=json.loads((ROOT/'planning/contract_freeze_v1.json').read_text())
 for p,h in freeze['sha256'].items():assert sha(ROOT/p)==h,'Frozen contract protocol/codebook changed'
 phases=[read_rows(RAW/f'dataset_phase{n}.csv') for n in (1,2)]
 keyed=[]
 for rows in phases:
  d={r['anon_id']:r for r in rows};assert len(d)==len(rows)==72;keyed.append(d)
 assert set(keyed[0])==set(keyed[1]);p1,p2=keyed
 ids=sorted(i for i,r in p1.items() if r['specification'] in ['G2','G3'])
 assert len(ids)==48
 shuffled=ids.copy();random.Random(SEED).shuffle(shuffled);aliases={pid:f'C{i:03}' for i,pid in enumerate(shuffled,1)}
 calibration=[];rng=random.Random(SEED)
 for cond in ['G2','G3']:
  for task in ['A','B']:
   cell=[i for i in ids if p1[i]['specification']==cond and p1[i]['Task']==task]
   assert len(cell)==12
   calibration.extend(rng.sample([i for i in cell if i not in PRIOR],2))
 out.mkdir(parents=True);(out/'packets').mkdir();(out/'calibration').mkdir()
 keys=[];lineage=[];redactions=[];eligibility=[];packets=[]
 for pid in sorted(p1):
  included=pid in aliases
  eligibility.append(dict(anon_id=pid,included=int(included),reason='required structured specification' if included else 'G1: separate specification not required',condition=p1[pid]['specification'],task=p1[pid]['Task']))
 for pid in ids:
  packet={'packet_id':aliases[pid],'task':p1[pid]['Task'],'phase1':[],'phase2':[]}
  for n,rows in enumerate(keyed,1):
   row=rows[pid];assert row['version']==p1[pid]['version']
   fields=[k for k in row if (k.startswith('before_g') if n==1 else k.startswith('after_g') or k.startswith('afterg'))]
   nonblank=[(k,row[k]) for k in fields if row[k].strip()]
   for j,(field,value) in enumerate(nonblank,1):
    block=f'B{j:02}';text,notes=redact(value)
    packet[f'phase{n}'].append({'block':block,'text':text})
    lineage.append(dict(packet_id=aliases[pid],phase=n,block=block,anon_id=pid,field=field,source=f'data/raw/replication_snapshot/Data/dataset_phase{n}.csv',record=row['_record'],physical_line_start=row['_line_start'],physical_line_end=row['_line_end'],raw_field_sha256=hashlib.sha256(value.encode()).hexdigest(),sanitized_field_sha256=hashlib.sha256(text.encode()).hexdigest()))
    redactions.extend(dict(packet_id=aliases[pid],phase=n,block=block,**note) for note in notes)
  packets.append(packet)
  keys.append(dict(packet_id=aliases[pid],anon_id=pid,condition=p1[pid]['specification'],task=p1[pid]['Task'],prior_text_exposure=int(pid in PRIOR),calibration=int(pid in calibration),phase1_blocks=len(packet['phase1']),phase2_blocks=len(packet['phase2'])))
 for packet in sorted(packets,key=lambda r:r['packet_id']):
  data=json.dumps(packet,ensure_ascii=False,indent=2)+'\n';(out/'packets'/f"{packet['packet_id']}.json").write_text(data)
  if next(k for k in keys if k['packet_id']==packet['packet_id'])['calibration']:(out/'calibration'/f"{packet['packet_id']}.json").write_text(data)
 write_csv(out/'PRIVATE_packet_key.csv',sorted(keys,key=lambda r:r['packet_id']))
 write_csv(out/'PRIVATE_source_map.csv',lineage)
 write_csv(out/'eligibility.csv',eligibility)
 (out/'redaction_log.json').write_text(json.dumps(redactions,indent=2)+'\n')
 (out/'calibration_ids.json').write_text(json.dumps(sorted(aliases[i] for i in calibration),indent=2)+'\n')
 (out/'preparation_summary.json').write_text(json.dumps({'participants':72,'eligible':48,'inapplicable':24,'packets':len(packets),'calibration':8,'specification_blocks':len(lineage),'characters':sum(len(b['text']) for p in packets for n in [1,2] for b in p[f'phase{n}']),'redactions':len(redactions),'outcomes_in_packets':False,'condition_names_in_packet_metadata':False,'masking_limit':'Text and field counts can imply condition; residual identity not exhaustively excluded.'},indent=2)+'\n')
 (out/'prepare_code.py').write_bytes(Path(__file__).read_bytes())
 manifest={'time_utc':datetime.now(timezone.utc).isoformat(),'seed':SEED,'python':sys.version,'protocol_hashes':freeze['sha256'],'inputs':{str((RAW/f'dataset_phase{n}.csv').relative_to(ROOT)):sha(RAW/f'dataset_phase{n}.csv') for n in [1,2]},'outputs':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print((out/'preparation_summary.json').read_text())
if __name__=='__main__':main()
