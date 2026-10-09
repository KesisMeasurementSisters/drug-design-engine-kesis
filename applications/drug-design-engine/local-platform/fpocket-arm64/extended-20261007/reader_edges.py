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

"""Generate independently defined edge fixtures, then test real reader callbacks.

Usage: reader_edges.py prepare FPOCKET_SOURCE FIXTURES
       reader_edges.py run PROBE FIXTURES OUTPUT ABI [sanitized]
"""
import copy, hashlib, json, math, os, signal, subprocess, sys, time
from pathlib import Path

def invoke(args, limit, env=None):
    start=time.monotonic()
    p=subprocess.Popen(list(map(str,args)),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                       errors='replace',env=env,start_new_session=True)
    try: stdout,stderr=p.communicate(timeout=limit); timed=False
    except subprocess.TimeoutExpired:
        os.killpg(p.pid,signal.SIGKILL);stdout,stderr=p.communicate();timed=True
    return {'exit':p.returncode,'timeout':timed,'seconds':round(time.monotonic()-start,3),'stdout':stdout,'stderr':stderr}

def prepare(source,out):
    out.mkdir(exist_ok=False)
    lines=(source/'data/sample/1UYD.cif').read_text().splitlines()
    tags=[x.strip() for x in lines if x.startswith('_atom_site.')]
    rows=[x.split() for x in lines if x.startswith('ATOM ')][:3]
    cases=[]
    def cif(name,changes=None,drop=(),reverse=False,ending='\n',valid=True):
        t=tags[:];r=copy.deepcopy(rows)
        if changes:
            for i,field,value in changes:r[i][t.index('_atom_site.'+field)]=value
        if drop:
            keep=[i for i,v in enumerate(t) if v not in ['_atom_site.'+d for d in drop]]
            t=[t[i] for i in keep];r=[[row[i] for i in keep] for row in r]
        if reverse:t=t[::-1];r=[row[::-1] for row in r]
        text='data_edge\n#\nloop_\n'+'\n'.join(t)+'\n'+'\n'.join(' '.join(row) for row in r)+'\n#'+ending
        path=out/(name+'.cif');path.write_text(text)
        expected=[]
        for row in r:
            d=dict(zip(t,row))
            expected.append({'name':d['_atom_site.label_atom_id'].strip("'\""),'resname':d['_atom_site.label_comp_id'],
                             'chain':d['_atom_site.label_asym_id'], 'resid':int(d['_atom_site.label_seq_id']),
                             'xyz':[float(d['_atom_site.Cartn_'+v]) for v in 'xyz'] if valid else None})
        cases.append({'name':name,'file':path.name,'reader':'pdbx','valid':valid,'atoms':expected})
    cif('minimal')
    for name,chain in [('chain-two','AB'),('chain-three','ABC'),('chain-fifteen','ABCDEFGHIJKLMNO')]:
        cif(name,[(i,key,chain) for i in range(3) for key in ('label_asym_id','auth_asym_id')])
    cif('chain-collision',[(i,key,chain) for i,chain in enumerate(('AAA','AAB','AAC')) for key in ('label_asym_id','auth_asym_id')])
    cif('quoted-atom',[(1,'label_atom_id',"'CA'"),(1,'auth_atom_id',"'CA'")])
    cif('reordered-columns',reverse=True)
    cif('optional-omitted',drop=('occupancy','B_iso_or_equiv','pdbx_formal_charge'))
    cif('negative-residue',[(i,'label_seq_id','-3') for i in range(3)])
    cif('no-final-newline',ending='')
    cif('missing-coordinate',[(0,'Cartn_x','?')],valid=False)
    cif('nonfinite-coordinate',[(0,'Cartn_x','nan')],valid=False)
    # Textual truncation, wrong record type, and empty inputs are invalid.
    for name,data in [('empty',''),('missing-loop','data_edge\n_entry.id edge\n'),
                      ('truncated-row',(out/'minimal.cif').read_text().rsplit('ATOM',1)[0]+'ATOM 3 C\n')]:
        (out/(name+'.cif')).write_text(data)
        cases.append({'name':name,'file':name+'.cif','reader':'pdbx','valid':False})
    water=(Path(__file__).parents[1]/'fixtures/water.parm7').read_text()
    variants={'water':(water,True),'water-comments':(water.replace('%FORMAT','%COMMENT allowed comment\n%FORMAT'),True),
              'water-crlf':(water.replace('\n','\r\n'),True),
              'water-empty':('',False),'water-truncated-pointers':(water.split('%FLAG ATOM_NAME')[0][:260],False),
              'water-truncated-atoms':(water.split('%FLAG AMBER_ATOM_TYPE')[0].replace('O   H1  H2  ','O   '),False),
              'water-missing-format':(water+'%FLAG MASS\n',False),
              'water-out-of-range-bond':(water.replace('       0       6       1','       0      99       1'),False)}
    for name,(text,valid) in variants.items():
        (out/(name+'.parm7')).write_bytes(text.encode())
        cases.append({'name':name,'file':name+'.parm7','reader':'parm7','valid':valid})
    (out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    (out/'hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()},indent=2)+'\n')

def run(probe,fixtures,out,abi,sanitized=False):
    out.mkdir(exist_ok=False);results=[]
    env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    for case in json.loads((fixtures/'cases.json').read_text()):
        r=invoke([probe,case['reader'],fixtures/case['file']],30,env)
        (out/(case['name']+'.log')).write_text(r['stdout']+'\n'+r['stderr'])
        record={k:v for k,v in r.items() if k not in ('stdout','stderr')};record.update(name=case['name'],valid_input=case['valid'])
        memory_error=any(x in r['stderr'] for x in ('ERROR: AddressSanitizer','runtime error:','AddressSanitizer:DEADLYSIGNAL'))
        try:
            assert not r['timeout'],'timeout'
            assert not memory_error,'memory-safety failure'
            if not case['valid']:
                assert r['exit']>0,'invalid input accepted or crashed'
            else:
                assert r['exit']==0,'valid input rejected or crashed'
                obj=json.loads(next(x[11:] for x in r['stdout'].splitlines() if x.startswith('PROBE_JSON ')))
                (out/(case['name']+'.json')).write_text(json.dumps(obj,indent=2)+'\n')
                assert obj['abi']==abi
                if case['reader']=='pdbx':
                    assert len(obj['atoms'])==len(case['atoms'])
                    for actual,expected in zip(obj['atoms'],case['atoms']):
                        for key in ('name','resname','chain','resid'):assert actual[key]==expected[key],(key,actual[key],expected[key])
                        assert all(math.isclose(x,y,abs_tol=1e-4) for x,y in zip(actual['xyz'],expected['xyz']))
                else:
                    assert obj['natoms']==3 and [a['name'].rstrip() for a in obj['atoms']]==['O','H1','H2']
                    assert obj['bonds']==[[1,2],[1,3]]
            record['passed']=True
        except Exception as e:record.update(passed=False,error=str(e))
        results.append(record);print(json.dumps(record),flush=True)
        (out/'report.json').write_text(json.dumps(results,indent=2)+'\n')
    return all(x['passed'] for x in results)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare(*map(Path,sys.argv[2:]))
    else:raise SystemExit(not run(Path(sys.argv[2]),Path(sys.argv[3]),Path(sys.argv[4]),int(sys.argv[5]),len(sys.argv)>6))
