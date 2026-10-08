"""Real DDE integration checks; run only against an isolated candidate project."""
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
from validation import run

def main(source, project, report_path):
    assert not project.exists(), 'Refuse to reuse or overwrite an existing project'
    run(['dde','init',project]);os.environ['DDE_PROJECT']=str(project)
    result={'checks':[], 'runtime':{'uid':os.getuid(),'gid':os.getgid(),'machine':platform.machine()}}
    def check(name,fn):
        try: detail=fn();r={'name':name,'passed':True,'detail':detail}
        except Exception as exc:r={'name':name,'passed':False,'error':str(exc)}
        result['checks'].append(r);report_path.write_text(json.dumps(result,indent=2)+'\n')
    def identity():
        state=json.loads(run(['dde','env','show','--json']).stdout)
        assert state['provisioned'] and not state['drifted']
        assert state['env_version']==state['live_env_version']
        return state
    check('environment-identity',identity)
    expected_stamp=(Path(os.environ['DDE_TOOLS_HOME'])/'ENV_VERSION').read_text().strip()
    for fixture in ('1UYD.pdb','3VI4.cif'):
        def valid(fixture=fixture):
            path=source/'data/sample'/fixture;before=hashlib.sha256(path.read_bytes()).hexdigest()
            output=json.loads(run(['dde','pocket','run',path,'--json']).stdout)
            assert output['n_pockets']>0
            record=Path(output['outputs']['pockets']);sidecar=Path(output['outputs']['sidecar'])
            assert record.is_file() and sidecar.is_file()
            meta=json.loads(sidecar.read_text());assert meta['env_version']==expected_stamp
            assert record.stat().st_uid==os.getuid() and sidecar.stat().st_uid==os.getuid()
            assert os.access(record,os.R_OK|os.W_OK) and os.access(sidecar,os.R_OK|os.W_OK)
            assert before in sidecar.read_text(), 'Input hash missing from provenance'
            analysis=json.loads(run(['dde','pocket','analyze',record,'--json']).stdout)
            assert analysis['metrics']['n_pockets']==output['n_pockets']
            assert analysis['metrics']['volume_estimate_tolerance']==.05
            assert hashlib.sha256(path.read_bytes()).hexdigest()==before
            return {'outputs':output['outputs'],'analysis':analysis,'env_version':meta['env_version']}
        check(fixture,valid)
    for name,content in [('invalid.txt','hello'),('empty.pdb',''),('truncated.pdb','ATOM      1  CA')]:
        def bad(name=name,content=content):
            path=project/name;path.write_text(content)
            r=subprocess.run(['dde','pocket','run',str(path),'--json'],capture_output=True,text=True,timeout=120)
            assert r.returncode!=0, 'Malformed input accepted'
            assert not list((project/'raw').rglob(path.stem+'.pockets.json'))
            return {'exit':r.returncode,'stderr':r.stderr}
        check('invalid-'+name,bad)
    check('existing-pocket-tests',lambda:run([sys.executable,'-m','unittest','discover','-s','/scion-volumes/source/applications/drug-design-engine/tools/tests','-p','test_pocket_peptide_occlusion.py'],120).stderr)
    result['passed']=all(c['passed'] for c in result['checks']);report_path.write_text(json.dumps(result,indent=2)+'\n')
    return result['passed']

if __name__=='__main__':raise SystemExit(0 if main(*map(Path,sys.argv[1:])) else 1)
