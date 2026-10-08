"""End-to-end namespace preservation, commit-marker enforcement, same-path concurrency."""
import concurrent.futures,hashlib,json,os,subprocess,sys
from pathlib import Path
import gemmi
source,out=map(Path,sys.argv[1:]);out.mkdir(exist_ok=False)
def run(args,env=None):return subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120,env=env)
assert run(['dde','init',out/'project']).returncode==0
env=dict(os.environ,DDE_PROJECT=str(out/'project'))
chain='ABCDEFGHIJKLMNO';doc=gemmi.cif.read(str(source/'data/sample/1UYD.cif'));block=doc.sole_block()
for key in ('auth_asym_id','label_asym_id'):
    col=block.find_values('_atom_site.'+key)
    for i in range(len(col)):
        if col[i]=='A':col[i]=chain
path=out/'long identifiers.mmcif';doc.write_file(str(path));before=hashlib.sha256(path.read_bytes()).hexdigest()
r=run(['dde','pocket','run',path,'--json'],env);(out/'run.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
outputs=json.loads(r.stdout)['outputs'];record=Path(outputs['pockets']);meta=Path(outputs['sidecar']);tree=Path(outputs['fpocket_tree'])
pockets=json.loads(record.read_text())['pockets'];assert len(pockets)==13
assert all(x['chain']==chain for pocket in pockets for x in pocket['residues'])
assert hashlib.sha256(path.read_bytes()).hexdigest()==before
assert run(['dde','pocket','analyze',record,'--json'],env).returncode==0
# Missing marker and altered output must be rejected, even if valid JSON remains.
meta.rename(meta.with_suffix('.saved'))
a=run(['dde','pocket','analyze',record,'--out','analysis/missing-marker','--json'],env);assert a.returncode!=0
meta.with_suffix('.saved').rename(meta)
atom=next((tree/'pockets').glob('*_atm.cif'));old=atom.read_bytes();atom.write_bytes(old+b'# modified\n')
a=run(['dde','pocket','analyze',record,'--out','analysis/corrupt','--json'],env);assert a.returncode!=0
atom.write_bytes(old)
# Same namespace: one succeeds; one must refuse instead of replacing.
def job(_):return run(['dde','pocket','run',path,'--out','raw/concurrent','--json'],env)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rs=list(pool.map(job,range(2)))
assert sum(r.returncode==0 for r in rs)==1,[(r.returncode,r.stderr) for r in rs]
# Removing the sole protein chain must not leave a successful output.
r=run(['dde','pocket','run',path,'--ignore-chain',chain,'--out','raw/stripped','--json'],env)
assert r.returncode!=0
(out/'report.json').write_text(json.dumps({'passed':True,'long_chain':chain,'pockets':13,'missing_marker_rejected':True,'corruption_rejected':True,'same_destination_single_winner':True,'all_protein_removed_rejected':True},indent=2)+'\n')
