#!/usr/bin/env python3
"""Bounded fixed-oracle execution of verified, inspected historical checkpoints.

The parent never imports participant modules. Each child runs in a macOS Seatbelt
sandbox with empty environment, denied network/fork, filesystem restrictions,
resource limits and a wall timeout. Raw source and hidden-suite bytes are copied.
"""
import argparse,csv,hashlib,json,os,shutil,signal,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
SAMPLE=ROOT/'runs/history_inventory_v1/sample.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def writecsv(p,rows):
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def profile(case):
 # Runtime directories contain installed libraries, not user document roots.
 reads=[('/',False),('/bin',True),('/sbin',True),('/usr',True),('/System',True),('/opt/homebrew',True),(sys.prefix,True),(str(case),True),('/dev/null',False),('/dev/urandom',False),('/dev/random',False),('/private/etc/localtime',False)]
 clauses='\n'.join(f'({"subpath" if sub else "literal"} {json.dumps(path)})' for path,sub in reads)
 return '(version 1)\n(allow default)\n(deny network*)\n(deny process-fork)\n(deny file-read-data (require-not (require-any\n'+clauses+'\n)))\n(deny file-write* (require-not (require-any (subpath '+json.dumps(str(case))+') (literal "/dev/null"))))\n'

LIMITS='''import resource
resource.setrlimit(resource.RLIMIT_CPU,(10,10))
resource.setrlimit(resource.RLIMIT_FSIZE,(8388608,8388608))
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
import os
from pathlib import Path
import json
allowed_environment={'PATH','HOME','TMPDIR','PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTHONDONTWRITEBYTECODE','LC_ALL','TZ'}
extra_environment_keys=sorted(set(os.environ)-allowed_environment)
Path('injected_environment_keys.json').write_text(json.dumps(extra_environment_keys))
for key in extra_environment_keys:del os.environ[key]
'''
WRAPPER=LIMITS+'''import os,sys,json
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
import pytest
class Capture:
    def __init__(self): self.reports=[]; self.collection=[]
    def pytest_runtest_logreport(self,report):
        self.reports.append(dict(nodeid=report.nodeid,when=report.when,outcome=report.outcome))
    def pytest_collectreport(self,report):
        if report.failed: self.collection.append(dict(nodeid=report.nodeid,outcome=report.outcome,longrepr=str(report.longrepr)))
c=Capture()
result=pytest.main(['hidden_tests.py','-q','-p','no:cacheprovider','--tb=short','--basetemp=tmp','--junitxml=results.xml'],plugins=[c])
Path('events.json').write_text(json.dumps(dict(exit_code=int(result),reports=c.reports,collection_errors=c.collection),indent=2)+'\\n')
raise SystemExit(result)
'''

def spawn(case,script,timeout=30):
 (case/'sandbox.sb').write_text(profile(case));(case/'runner.py').write_text(script)
 env={'PATH':'/usr/bin:/bin','HOME':str(case),'TMPDIR':str(case/'tmp'),'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONDONTWRITEBYTECODE':'1','LC_ALL':'C','TZ':'UTC'}
 (case/'tmp').mkdir(exist_ok=True)
 command=['/usr/bin/sandbox-exec','-f',str(case/'sandbox.sb'),sys.executable,'-I','-B',str(case/'runner.py')]
 start=time.monotonic();timed_out=False
 with (case/'stdout.txt').open('w') as stdout,(case/'stderr.txt').open('w') as stderr:
  process=subprocess.Popen(command,cwd=case,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
  try:code=process.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   timed_out=True;os.killpg(process.pid,signal.SIGKILL);code=process.wait()
 meta=dict(returncode=code,timed_out=timed_out,elapsed_seconds=round(time.monotonic()-start,3),command=command,environment=env,cpu_seconds=10,wall_seconds=timeout,max_file_bytes=8388608)
 (case/'execution.json').write_text(json.dumps(meta,indent=2)+'\n');return meta

def probe(out):
 case=out/'isolation_probe';case.mkdir()
 sentinel=out/'denied_sentinel.txt';sentinel.write_text('non-sensitive isolation probe')
 script=LIMITS+'''import os,json,socket,errno
from pathlib import Path
checks={}
Path('allowed.txt').write_text('ok');checks['allowed_read_write']=Path('allowed.txt').read_text()=='ok'
for name,path,mode in [('outside_read',SENTINEL,'r'),('outside_write',SENTINEL,'w')]:
    try:
        with open(path,mode):pass
        checks[name]=False
    except PermissionError:checks[name]=True
s=socket.socket()
try:s.connect(('127.0.0.1',9));checks['network_denied']=False
except OSError as e:checks['network_denied']=e.errno in (errno.EACCES,errno.EPERM)
finally:s.close()
try:
    pid=os.fork()
    if pid==0:os._exit(0)
    os.waitpid(pid,0);checks['fork_denied']=False
except PermissionError:checks['fork_denied']=True
checks['environment_clean']=set(os.environ)<=set(['PATH','HOME','TMPDIR','PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTHONDONTWRITEBYTECODE','LC_ALL','TZ'])
Path('checks.json').write_text(json.dumps(checks,indent=2)+'\\n')
assert all(checks.values()),checks
'''.replace('SENTINEL',repr(str(sentinel)))
 result=spawn(case,script)
 checks=json.loads((case/'checks.json').read_text()) if (case/'checks.json').exists() else {}
 if result['returncode']!=0 or not checks or not all(checks.values()):raise RuntimeError(f'Isolation probe failed; inspect {case}')
 return checks

def parse_events(data,expected):
 """Every expected case must have setup/call/teardown, otherwise unobserved."""
 grouped={}
 for r in data.get('reports',[]):
  name=r['nodeid'].split('::')[-1];grouped.setdefault(name,[]).append(r)
 extra=set(grouped)-set(expected)
 if extra:raise ValueError(f'Unexpected collected tests: {extra}')
 results={}
 for name in expected:
  events=grouped.get(name,[]);stages={r['when']:r['outcome'] for r in events}
  if len(events)!=len(stages):raise ValueError('Duplicate report stage')
  if any(v=='failed' for k,v in stages.items() if k!='call'):status='error'
  elif stages.get('call')=='failed':status='F'
  elif stages.get('call')=='passed' and stages.get('setup')=='passed' and stages.get('teardown')=='passed':status='P'
  elif 'skipped' in stages.values():status='skipped'
  else:status='unobserved'
  results[name]=status
 return results

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--probe-only',action='store_true');a=ap.parse_args()
 out=(ROOT/a.out).resolve();assert out.is_relative_to(ROOT) and not out.exists(),'Use new project output path'
 out.mkdir(parents=True);checks=probe(out)
 if a.probe_only:print(json.dumps(checks));return
 sample=json.loads(SAMPLE.read_text());manifest=json.loads((ROOT/'sources/history/acquisition_manifest.json').read_text());verified={r['path']:r['sha256'] for r in manifest['selected_files']}
 assert sha(ROOT/sample['protocol'])==sample['protocol_sha256']
 transition_path=ROOT/'runs/pilot_v1_final/transitions.csv'
 table_manifest_path=ROOT/'runs/pilot_v1_final/manifest.json'
 table_manifest=json.loads(table_manifest_path.read_text())
 assert sha(transition_path)==table_manifest['outputs']['transitions.csv'], 'Released transition input changed'
 with transition_path.open(newline='') as f:tables=list(csv.DictReader(f))
 assert len(tables)==len({(r['anon_id'],r['test_id']) for r in tables})==72*33, 'Duplicate or missing transition rows'
 tables={pid:{r['test_id']:r for r in tables if r['anon_id']==pid} for pid in sample['selected_union_ids']}
 rows=[];summaries=[]
 dependencies=[SAMPLE,transition_path,table_manifest_path,ROOT/'sources/history/acquisition_manifest.json',ROOT/sample['protocol'],ROOT/'planning/code_pilot_freeze_v1.json']
 inputs={str(p.relative_to(ROOT)):sha(p) for p in dependencies}
 for selected in sample['selected_paths']:
  pid=selected['anon_id'];task=selected['task'];expected=tables[pid];assert len(expected)==33
  for phase in [1,2]:
   case=out/'cases'/f'{pid}_phase{phase}';case.mkdir(parents=True)
   source=ROOT/selected['sources'][str(phase)][0]
   suite=ROOT/f'data/raw/history_69e000a/files/Hidden_tests/hidden_tests_Task{task}.py'
   current=ROOT/f'data/raw/replication_snapshot/Hidden_tests/hidden_tests_Task{task}.py'
   for p in [source,suite]:
    rel=str(p.relative_to(ROOT));assert sha(p)==verified[rel];inputs[rel]=sha(p)
   assert suite.read_bytes()==current.read_bytes(),'Historical/current suite differs: requires protocol revision'
   shutil.copyfile(source,case/'solution.py');shutil.copyfile(suite,case/'hidden_tests.py')
   result=spawn(case,WRAPPER)
   events=json.loads((case/'events.json').read_text()) if (case/'events.json').exists() else {}
   statuses=parse_events(events,expected)
   for test,status in sorted(statuses.items()):
    released=expected[test][f'phase{phase}'];rows.append(dict(anon_id=pid,task=task,condition=selected['condition'],phase=phase,primary=int(selected['primary']),diagnostic=int(selected['known_pf_diagnostic']),test_id=test,fixed_oracle_status=status,released_status=released,exact_match=int(status==released)))
   summary=dict(anon_id=pid,task=task,condition=selected['condition'],phase=phase,primary=int(selected['primary']),diagnostic=int(selected['known_pf_diagnostic']),P=sum(s=='P' for s in statuses.values()),F=sum(s=='F' for s in statuses.values()),other=sum(s not in ['P','F'] for s in statuses.values()),released_matches=sum(statuses[t]==expected[t][f'phase{phase}'] for t in expected),total_tests=33,returncode=result['returncode'],timed_out=int(result['timed_out']),source_sha256=sha(source),suite_sha256=sha(suite));summaries.append(summary)
   print(json.dumps({k:summary[k] for k in ['anon_id','phase','P','F','other','released_matches','timed_out']}),flush=True)
 writecsv(out/'test_results.csv',rows);writecsv(out/'execution_summary.csv',summaries)
 transitions=[]
 for pid in sample['selected_union_ids']:
  first={r['test_id']:r for r in rows if r['anon_id']==pid and r['phase']==1};second={r['test_id']:r for r in rows if r['anon_id']==pid and r['phase']==2}
  for test in sorted(first):
   x,y=first[test],second[test];transitions.append(dict(anon_id=pid,task=x['task'],condition=x['condition'],primary=x['primary'],diagnostic=x['diagnostic'],test_id=test,fixed_phase1=x['fixed_oracle_status'],fixed_phase2=y['fixed_oracle_status'],fixed_transition=x['fixed_oracle_status']+y['fixed_oracle_status'],released_transition=x['released_status']+y['released_status']))
 writecsv(out/'fixed_transitions.csv',transitions)
 (out/'runtime_code.py').write_bytes(Path(__file__).read_bytes())
 metadata=dict(time_utc=datetime.now(timezone.utc).isoformat(),python=sys.version,pytest_version=__import__('importlib.metadata',fromlist=['version']).version('pytest'),sample_sha256=sha(SAMPLE),inputs=inputs,isolation_checks=checks,outputs={name:sha(out/name) for name in ['test_results.csv','execution_summary.csv','fixed_transitions.csv','runtime_code.py']},inference='Phase 1 uses a fixed current oracle; only phase 2 is compared as a potential reproduction. Checkpoint provenance is separate from exact executed lineage.')
 (out/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
if __name__=='__main__':main()
