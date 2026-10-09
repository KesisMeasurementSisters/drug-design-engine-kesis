# Copyright 2026 Technologies Kesis & Sisters Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Bounded real-DDE edge tests, including concurrent independent projects."""
import concurrent.futures, hashlib, json, os, shutil, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"extended-20261007"))
from reader_edges import invoke

source,out=map(Path,sys.argv[1:]);out.mkdir(exist_ok=False)
results=[]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(name,fn):
    try:detail=fn();r={'name':name,'passed':True,'detail':detail}
    except Exception as e:r={'name':name,'passed':False,'error':str(e)}
    results.append(r);(out/'report.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(r),flush=True)
def project(name):
    p=out/name;r=invoke(['dde','init',p],30);assert r['exit']==0,r['stderr']
    return p
def calculate(p,path,extra=()):
    before=digest(path);env=dict(os.environ,DDE_PROJECT=str(p))
    r=invoke(['dde','pocket','run',path,'--json',*extra],120,env)
    (p/'run.stdout').write_text(r['stdout']);(p/'run.stderr').write_text(r['stderr'])
    assert digest(path)==before,'Input changed'
    assert not r['timeout'],'Timeout (process group terminated)'
    assert r['exit']==0,(r['exit'],r['stderr'][-900:])
    d=json.loads(r['stdout']);assert d['n_pockets']>0
    record=Path(d['outputs']['pockets']);meta=Path(d['outputs']['sidecar'])
    assert before in meta.read_text()
    a=invoke(['dde','pocket','analyze',record,'--json'],120,env)
    assert a['exit']==0 and not a['timeout'],a['stderr']
    analysis=json.loads(a['stdout']);assert analysis['metrics']['n_pockets']==d['n_pockets']
    assert json.loads(meta.read_text())['env_version']==Path('/scion-volumes/tools/ENV_VERSION').read_text().strip()
    return {'pockets':d['n_pockets'],'metrics':analysis['metrics'],'source_sha256':before,'outputs':d['outputs']}
for filename,original in [('simple.pdb','1UYD.pdb'),('space name.pdb','1UYD.pdb'),
    ("quote'name.pdb",'1UYD.pdb'),('unicode_é.pdb','1UYD.pdb'),('semi;colon.pdb','1UYD.pdb'),
    ('-leading.pdb','1UYD.pdb'),('upper.PDB','1UYD.pdb'),('alias.ent','1UYD.pdb'),
    ('alias.mmcif','1UYD.cif'),('standard.cif','1UYD.cif')]:
    def test(filename=filename,original=original):
        p=project('filename-'+str(len(results)));path=p/filename;shutil.copy2(source/'data/sample'/original,path)
        return calculate(p,path)
    check('filename-'+filename,test)
def readonly():
    p=project('readonly');path=p/'readonly.pdb';shutil.copy2(source/'data/sample/1UYD.pdb',path);path.chmod(0o444)
    return calculate(p,path)
check('read-only-input',readonly)
def crlf():
    p=project('crlf');path=p/'crlf.pdb';path.write_bytes((source/'data/sample/1UYD.pdb').read_bytes().replace(b'\n',b'\r\n'))
    return calculate(p,path)
check('crlf-pdb',crlf)
base=(source/'data/sample/1UYD.pdb').read_text();lines=base.splitlines();first=next(i for i,x in enumerate(lines) if x.startswith('ATOM'))
badcoord=lines[:];badcoord[first]=badcoord[first][:30]+' INVALID'+badcoord[first][38:]
nan=lines[:];nan[first]=nan[first][:30]+'     nan'+nan[first][38:]
for name,text in [('empty.pdb',''),('truncated.pdb','ATOM      1  CA'),('invalid-coordinate.pdb','\n'.join(badcoord)+'\n'),
                  ('nan-coordinate.pdb','\n'.join(nan)+'\n'),('wrong.txt',base)]:
    def malformed(name=name,text=text):
        p=project('invalid-'+str(len(results)));path=p/name;path.write_text(text)
        r=invoke(['dde','pocket','run',path,'--json'],120,dict(os.environ,DDE_PROJECT=str(p)))
        (p/'stdout.log').write_text(r['stdout']);(p/'stderr.log').write_text(r['stderr'])
        assert not r['timeout'],'timeout'
        assert r['exit']!=0,'Malformed structure accepted'
        assert not list((p/'raw').rglob('*.pockets.json')),'Success artifact left after failure'
        return {'exit':r['exit']}
    check('reject-'+name,malformed)
def missing():
    p=project('missing');r=invoke(['dde','pocket','run',p/'absent.pdb','--json'],120,dict(os.environ,DDE_PROJECT=str(p)))
    assert r['exit']!=0 and not r['timeout'];return {'exit':r['exit']}
check('reject-missing-path',missing)
def wrong_permissions():
    p=project('not-writable');path=p/'input.pdb';shutil.copy2(source/'data/sample/1UYD.pdb',path)
    target=p/'raw/structures';target.chmod(0o555)
    try:
        r=invoke(['dde','pocket','run',path,'--json'],120,dict(os.environ,DDE_PROJECT=str(p)))
        (p/'stderr.log').write_text(r['stderr']);assert r['exit']!=0 and not r['timeout']
        assert not list(target.rglob('*.pockets.json'));return {'exit':r['exit']}
    finally:target.chmod(0o755)
check('reject-unwritable-output',wrong_permissions)
def concurrency():
    jobs=[]
    for i in range(4):
        p=project('parallel-'+str(i));path=p/'same-name.pdb';shutil.copy2(source/'data/sample/1UYD.pdb',path);jobs.append((p,path))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        data=list(pool.map(lambda x:calculate(*x),jobs))
    assert all(d['pockets']==13 and d['metrics']['best_pocket']['score']==.664 for d in data)
    return {'independent_projects':4,'pockets_each':[d['pockets'] for d in data]}
check('four-concurrent-isolated-runs',concurrency)
def reuse():
    p=project('repeat-project');path=p/'same.pdb';shutil.copy2(source/'data/sample/1UYD.pdb',path)
    first=calculate(p,path);before=digest(Path(first['outputs']['sidecar']))
    r=invoke(['dde','pocket','run',path,'--json'],120,dict(os.environ,DDE_PROJECT=str(p)))
    assert r['exit']!=0 and not r['timeout']
    assert digest(Path(first['outputs']['sidecar']))==before
    second=calculate(p,path,('--out','raw/repeated'))
    assert first['pockets']==second['pockets']==13
    return {'refused_collision':True,'alternate_output_passed':True}
check('repeat-in-same-project',reuse)
raise SystemExit(not all(r['passed'] for r in results))
