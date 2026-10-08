"""Exercise the reviewed failures through real DDE calculation and analysis."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import gemmi
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from release_checks import require

source,output=map(Path,sys.argv[1:]);output.mkdir(exist_ok=False)
project=output/'project'
subprocess.run(['dde','init',str(project)],check=True,capture_output=True)
env=dict(os.environ,DDE_PROJECT=str(project),DDE_NO_DIRTY_WARNING='1')
checks=[]
def run(args):
    return subprocess.run(['dde',*map(str,args)],env=env,capture_output=True,text=True,timeout=130)
def check(name,condition):
    checks.append({'name':name,'passed':bool(condition)})
    (output/'report.json').write_text(json.dumps(checks,indent=2)+'\n')
    require(condition,name)

# Preserve label identity and source missingness through the real native workflow.
doc=gemmi.cif.read(str(source/'data/sample/1UYD.cif'));block=doc.sole_block()
author=block.find_values('_atom_site.auth_seq_id');label=block.find_values('_atom_site.label_seq_id')
for i in range(len(author)):
    if label[i] not in ('.','?'):author[i]='?'
path=project/'raw/missing-author.cif';doc.write_file(str(path));before=hashlib.sha256(path.read_bytes()).hexdigest()
r=run(['pocket','run',path,'--json']);(output/'run.log').write_text(r.stdout+r.stderr)
require(r.returncode==0,r.stderr)
paths=json.loads(r.stdout)['outputs'];record=Path(paths['pockets']);meta=Path(paths['sidecar']);tree=Path(paths['fpocket_tree'])
result=json.loads(record.read_text());residues=[r for p in result['pockets'] for r in p['residues']]
check('missing-author-preserved',bool(residues) and all(r['resnum']!=0 and r.get('auth_resnum') is None and r.get('identity_namespace')=='label' for r in residues))
check('source-unchanged',hashlib.sha256(path.read_bytes()).hexdigest()==before)
check('complete-analysis',run(['pocket','analyze',record,'--json']).returncode==0)
renamed=project/'raw/orphan.json';shutil.copyfile(record,renamed)
check('renamed-incomplete-rejected',run(['pocket','analyze',renamed,'--json']).returncode!=0)
# Use a genuine complete bundle and correct hashes to isolate selector behaviour.
result['pockets']=[{'rank':1,'score':1,'druggability_score':.9,'volume':100,'residues':[{'chain':'A','resnum':145,'resname':'ALA','insertion_code':'A'}]},
                   {'rank':2,'score':1,'druggability_score':.1,'volume':100,'residues':[{'chain':'A','resnum':145,'resname':'GLY','insertion_code':'B'}]}]
result['n_pockets']=2
record.write_text(json.dumps(result));metadata=json.loads(meta.read_text())
for item in metadata['outputs']:
    if item['path']==record.name:item['sha256']=hashlib.sha256(record.read_bytes()).hexdigest()
meta.write_text(json.dumps(metadata))
check('ambiguous-site-rejected',run(['pocket','analyze',record,'--near','A:145','--json']).returncode!=0)
r=run(['pocket','analyze',record,'--near','A:145B','--out','raw/explicit','--json'])
check('explicit-site-selects-b',r.returncode==0 and [x['rank'] for x in json.loads(r.stdout)['metrics']['site']['pockets_at_site']]==[2])
