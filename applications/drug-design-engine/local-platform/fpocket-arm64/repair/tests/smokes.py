"""Bounded local regression checks. All new artifacts go into a fresh directory."""
import json
import os
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from validation import run

out=Path(sys.argv[1]);out.mkdir(exist_ok=False)
run(['dde','init',out/'project'])
os.environ['DDE_PROJECT']=str(out/'project')
checks=[]
def check(name,fn):
    try:detail=fn();r={'name':name,'passed':True,'detail':detail}
    except Exception as e:r={'name':name,'passed':False,'error':str(e)}
    checks.append(r)
def vina():
    source=Path('/scion-volumes/build/vina/example/basic_docking/solution')
    r=run(['vina','--receptor',source/'1iep_receptor.pdbqt','--ligand',source/'1iep_ligand.pdbqt',
           '--center_x','15.19','--center_y','53.903','--center_z','16.917',
           '--size_x','20','--size_y','20','--size_z','20','--score_only','--cpu','2'])
    (out/'vina.log').write_text(r.stdout+r.stderr)
    score=float(re.search(r'Estimated Free Energy of Binding\s*:\s*([-0-9.]+)',r.stdout)[1])
    assert score==-12.513,score
    return {'score':score}
def fasta(path):
    records={};key=None
    for line in path.read_text().splitlines():
        if line.startswith('>'):key=line;records[key]=''
        elif line:records[key]+=line.replace('-','')
    return records
def muscle():
    source=Path('/scion-volumes/build/muscle/test_data/fa/BB11001')
    r=run(['muscle','-align',source,'-output',out/'alignment.afa','-threads','2'])
    (out/'muscle.log').write_text(r.stdout+r.stderr)
    assert fasta(source)==fasta(out/'alignment.afa')
    return {'sequences':len(fasta(source))}
def compound():
    r=json.loads(run(['dde','compound','descriptors','CCO','--name','ethanol-fpocket-regression','--json']).stdout)
    assert r['descriptors']['molecular_weight']==46.07
    return r
def hypex():
    r=run(['hypex','init-run','fpocket-regression','--run-dir',out/'hypex','--goal','Local datastore smoke test; no model calls'])
    s=run(['hypex','status','--run','fpocket-regression','--run-dir',out/'hypex'])
    (out/'hypex.log').write_text(r.stdout+r.stderr+s.stdout+s.stderr)
    assert (out/'hypex/fpocket-regression/run.yaml').is_file()
    return {'init_exit':r.returncode,'status_exit':s.returncode}
for name,fn in [('vina',vina),('muscle',muscle),('compound',compound),('hypex',hypex)]:check(name,fn)
result={'passed':all(c['passed'] for c in checks),'checks':checks}
(out/'report.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(not result['passed'])
