#!/usr/bin/env python3
"""Analyze frozen provisional contract labels; no model calls or code execution."""
import argparse,csv,hashlib,json,sys
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from contract_validate import A,B,SHARED,read_labels,validate
ROOT=Path(__file__).resolve().parents[1]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csvread(p):
 with p.open(newline='') as f:return list(csv.DictReader(f))
def csvwrite(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def atom_state(record,atom):
 if atom in record.get('unresolved_atoms',[]):return 'unresolved'
 return 'expressed' if atom in record['atoms'] else 'not_expressed'

def transition(before,after,atom):
 return ('present' if atom in before else 'not_expressed')+'__'+('present' if atom in after else 'not_expressed')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--labels',required=True);ap.add_argument('--coder1',required=True);ap.add_argument('--coder2',required=True);ap.add_argument('--out',required=True);ap.add_argument('--join-outcomes',action='store_true');a=ap.parse_args()
 out=(ROOT/a.out).resolve()
 if not out.is_relative_to(ROOT) or out.exists():raise SystemExit('Use new project directory')
 prep=ROOT/'runs/contract_inputs_v1';packets={p.stem:json.loads(p.read_text()) for p in (prep/'packets').glob('*.json')}
 files=[ROOT/a.labels,ROOT/a.coder1,ROOT/a.coder2];sets=[read_labels(p) for p in files]
 for labels in sets:
  errors=validate(labels,packets);assert not errors,errors
 final,c1,c2=[{(r['packet_id'],r['phase']):r for r in labels} for labels in sets]
 key_rows=csvread(prep/'PRIVATE_packet_key.csv')
 key={r['packet_id']:r for r in key_rows}
 assert len(key_rows)==len(key)==48 and len({r['anon_id'] for r in key_rows})==48, 'Duplicate or missing key rows'
 assert set(key)==set(packets), 'Packet-key mismatch'
 for pid,r in key.items():
  assert r['task']==packets[pid]['task'] and r['task'] in ['A','B'], 'Task-map mismatch'
  assert r['condition'] in ['G2','G3'] and r['calibration'] in ['0','1'] and r['prior_text_exposure'] in ['0','1'], 'Invalid group metadata'
 assert Counter((r['task'],r['condition']) for r in key_rows)=={(t,g):12 for t in ['A','B'] for g in ['G2','G3']}, 'Cell count mismatch'
 assert sum(int(r['calibration']) for r in key_rows)==8, 'Calibration count mismatch'
 assert all(r['availability']=='text_present' for labels in sets for r in labels), 'Current analysis requires observed nonempty text; revise protocol for missing text'
 # Require frozen label bytes before the optional exploratory join.
 freeze_path=ROOT/'annotations/contract/label_freeze.json';freeze=json.loads(freeze_path.read_text())
 for p in files:assert freeze['sha256'][str(p.relative_to(ROOT))]==sha(p),'Labels changed after freeze'
 cb=ROOT/'annotations/contract/CODEBOOK_v3.md'
 cbfreeze=json.loads((ROOT/'planning/contract_codebook_v3_freeze.json').read_text())
 assert cbfreeze['sha256'][str(cb.relative_to(ROOT))]==sha(cb)
 out.mkdir(parents=True)
 summaries=[];trajectories=[];agreements=[];disagreements=[];participant=[]
 for task,allowed in [('A',A|SHARED),('B',B|SHARED)]:
  task_ids=sorted(k for k,r in key.items() if r['task']==task);assert len(task_ids)==24
  for phase in [1,2]:
   for group_type,groups in [('task',['all']),('condition',['G2','G3']),('calibration',['0','1']),('prior_exposure',['0','1'])]:
    for group in groups:
     ids=[pid for pid in task_ids if group_type=='task' or key[pid][{'condition':'condition','calibration':'calibration','prior_exposure':'prior_text_exposure'}[group_type]]==group]
     for atom in sorted(allowed):
      present=sum(atom in final[(pid,phase)]['atoms'] for pid in ids)
      unknown=sum(atom in final[(pid,phase)].get('unresolved_atoms',[]) for pid in ids)
      summaries.append(dict(task=task,phase=phase,group_type=group_type,group=group,atom=atom,participants=len(ids),text_present=sum(final[(pid,phase)]['availability']=='text_present' for pid in ids),expressed=present,unresolved=unknown,not_expressed=len(ids)-present-unknown))
   for atom in sorted(allowed):
    counts=Counter((atom_state(c1[(pid,phase)],atom),atom_state(c2[(pid,phase)],atom)) for pid in task_ids)
    state_counts={f'coder1_{x}__coder2_{y}':counts[x,y] for x in ['expressed','not_expressed','unresolved'] for y in ['expressed','not_expressed','unresolved']}
    agreements.append(dict(task=task,phase=phase,atom=atom,participants=len(task_ids),**state_counts))
  for atom in sorted(allowed):
   counts=Counter('unresolved' if atom in final[(pid,1)].get('unresolved_atoms',[])+final[(pid,2)].get('unresolved_atoms',[]) else transition(final[(pid,1)]['atoms'],final[(pid,2)]['atoms'],atom) for pid in task_ids)
   for label in ['not_expressed__not_expressed','not_expressed__present','present__not_expressed','present__present','unresolved']:
    trajectories.append(dict(task=task,atom=atom,trajectory=label,participants=counts[label],denominator=len(task_ids)))
 for pid in sorted(key):
  for phase in [1,2]:
   r=final[(pid,phase)];x=c1[(pid,phase)];y=c2[(pid,phase)]
   participant.append(dict(packet_id=pid,anon_id=key[pid]['anon_id'],condition=key[pid]['condition'],task=key[pid]['task'],phase=phase,calibration=key[pid]['calibration'],prior_text_exposure=key[pid]['prior_text_exposure'],availability=r['availability'],atoms=';'.join(sorted(r['atoms'])),conflict=r['conflict'],unresolved_atoms=';'.join(sorted(r.get('unresolved_atoms',[])))))
   if set(x['atoms'])!=set(y['atoms']) or set(x.get('unresolved_atoms',[]))!=set(y.get('unresolved_atoms',[])) or x['conflict']!=y['conflict']:
    disagreements.append(dict(packet_id=pid,phase=phase,task=key[pid]['task'],coder1_atoms=';'.join(sorted(x['atoms'])),coder2_atoms=';'.join(sorted(y['atoms'])),coder1_unresolved=';'.join(sorted(x.get('unresolved_atoms',[]))),coder2_unresolved=';'.join(sorted(y.get('unresolved_atoms',[]))),final_unresolved=';'.join(sorted(r.get('unresolved_atoms',[]))),coder1_conflict=x['conflict'],coder2_conflict=y['conflict'],final_atoms=';'.join(sorted(r['atoms'])),final_conflict=r['conflict'],resolution=r.get('adjudication','')))
 csvwrite(out/'atom_counts.csv',summaries);csvwrite(out/'atom_trajectories.csv',trajectories);csvwrite(out/'coder_agreement.csv',agreements);csvwrite(out/'participant_labels.csv',participant)
 if disagreements:csvwrite(out/'disagreements.csv',disagreements)
 conflict=[]
 for task in ['A','B']:
  for phase in [1,2]:
   rs=[r for r in participant if r['task']==task and r['phase']==phase]
   for label in ['none_seen','possible','explicit']:conflict.append(dict(task=task,phase=phase,conflict=label,participants=sum(r['conflict']==label for r in rs),denominator=len(rs)))
 csvwrite(out/'conflict_counts.csv',conflict)
 overall={'participants':48,'phase_records':96,'calibration_participants':sum(int(r['calibration']) for r in key_rows),'full_atom_set_agreement':sum(set(c1[k]['atoms'])==set(c2[k]['atoms']) for k in final),'full_atom_state_agreement':sum(set(c1[k]['atoms'])==set(c2[k]['atoms']) and set(c1[k].get('unresolved_atoms',[]))==set(c2[k].get('unresolved_atoms',[])) for k in final),'conflict_agreement':sum(c1[k]['conflict']==c2[k]['conflict'] for k in final),'any_disagreement_records':len(disagreements),'agent_review_only':True,'human_validation':False,'outcome_joined':a.join_outcomes}
 (out/'summary.json').write_text(json.dumps(overall,indent=2)+'\n')
 outcome_inputs=[]
 if a.join_outcomes:
  op=ROOT/'runs/pilot_v1_final/participant_metrics.csv';outcome_inputs=[op]
  outcome_rows=[r for r in csvread(op) if r['mapping']=='primary' and r['scope']=='all']
  outcomes={r['anon_id']:r for r in outcome_rows}
  assert len(outcomes)==len(outcome_rows)==72, 'Duplicate or missing outcome rows'
  for r in key_rows:
   assert r['anon_id'] in outcomes and (outcomes[r['anon_id']]['task'],outcomes[r['anon_id']]['condition'])==(r['task'],r['condition']), 'Outcome-key metadata mismatch'
  o=[]
  for task,allowed in [('A',A|SHARED),('B',B|SHARED)]:
   ids=[pid for pid in key if key[pid]['task']==task]
   for atom in sorted(allowed):
    for status in ['expressed','not_expressed','unresolved']:
     selected=[pid for pid in ids if ('unresolved' if atom in final[(pid,2)].get('unresolved_atoms',[]) else 'expressed' if atom in final[(pid,2)]['atoms'] else 'not_expressed')==status]
     ms=[outcomes[key[pid]['anon_id']] for pid in selected]
     o.append(dict(task=task,atom=atom,text_status=status,participants=len(ms),participants_with_PF=sum(int(r['any_pf']) for r in ms),participants_at_PF_risk=sum(int(r['baseline_passes'])>0 for r in ms),PF_instances=sum(int(r['PF']) for r in ms),FP_instances=sum(int(r['FP']) for r in ms),participant_ids=';'.join(key[pid]['anon_id'] for pid in selected)))
  csvwrite(out/'exploratory_outcome_join.csv',o)
 (out/'analyze_code.py').write_bytes(Path(__file__).read_bytes())
 inputs=files+[prep/'PRIVATE_packet_key.csv',cb,freeze_path]+outcome_inputs+list((prep/'packets').glob('*.json'))
 manifest={'time_utc':datetime.now(timezone.utc).isoformat(),'python':sys.version,'labels_frozen_before_join':True,'inputs':{str(p.relative_to(ROOT)):sha(p) for p in sorted(inputs)},'code':{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__)), 'code/contract_validate.py':sha(ROOT/'code/contract_validate.py')},'outputs':{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()},'inference':'descriptive local arithmetic on provisional model-assisted text labels; no causal or human-validation claim'}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(overall))
if __name__=='__main__':main()
