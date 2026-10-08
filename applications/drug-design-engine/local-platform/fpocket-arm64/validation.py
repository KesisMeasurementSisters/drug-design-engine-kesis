"""Frozen acceptance harness. Never derive expected results from the ARM candidate."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import time

HERE = Path(__file__).resolve().parent
CONTRACT = json.loads((HERE / 'test_contract.json').read_text())
NONFINITE = re.compile(r'(?<![A-Za-z])(?:[-+]?nan|[-+]?inf(?:inity)?)(?![A-Za-z])', re.I)

def run(args, timeout=120, env=None):
    result = subprocess.run(list(map(str,args)), capture_output=True, text=True, timeout=timeout, env=env)
    if result.returncode:
        raise AssertionError(f'{args}: exit {result.returncode}\n{result.stdout[-3000:]}\n{result.stderr[-3000:]}')
    return result

def normalised(path):
    text = path.read_text()
    assert not NONFINITE.search(text), f'Non-finite output: {path}'
    return [x for x in text.splitlines() if 'olume' not in x]

def compare_tree(expected, actual):
    exp = {p.relative_to(expected) for p in expected.rglob('*') if p.is_file()}
    got = {p.relative_to(actual) for p in actual.rglob('*') if p.is_file()}
    assert exp, f'Empty reference: {expected}'
    assert exp == got, f'File set differs: missing={sorted(exp-got)} extra={sorted(got-exp)}'
    for rel in sorted(exp):
        assert len((expected/rel).read_text().splitlines())==len((actual/rel).read_text().splitlines()), f'Incomplete raw records: {rel}'
        a,b=normalised(expected/rel),normalised(actual/rel)
        assert len(a)==len(b), f'Truncated/extra lines: {rel}: {len(a)} != {len(b)}'
        assert a==b, f'Content differs: {rel}; first difference: '+str(next(((i,x,y) for i,(x,y) in enumerate(zip(a,b),1) if x!=y),None))

def probe(binary, kind, fixture, env=None, expected_abi=18):
    result=run([binary,kind,fixture],30,env)
    lines=[x[len('PROBE_JSON '):] for x in result.stdout.splitlines() if x.startswith('PROBE_JSON ')]
    assert len(lines)==1, 'Missing or duplicated probe JSON'
    obj=json.loads(lines[0],parse_constant=lambda x: (_ for _ in ()).throw(AssertionError(x)))
    assert obj['abi']==expected_abi and obj['reader']==kind
    assert obj['natoms']>0 and len(obj['atoms'])==obj['natoms']
    return obj

def check_parm(obj, missing=False):
    e=CONTRACT['parm7_expected']; assert obj['natoms']==e['natoms']
    for field,key in [('name','names'),('type','types'),('resname','resnames'),('resid','resids')]:
        # AMBER uses fixed-width 4-character identifiers. The original Intel
        # library also preserves padding. Raw reader JSON is still compared
        # exactly across architectures below; only the semantic check trims it.
        values=[a[field].rstrip() if isinstance(a[field],str) else a[field] for a in obj['atoms']]
        assert values==e[key], field
    for i,a in enumerate(obj['atoms']):
        assert a['xyz'] is None and a['chain']=='', 'Missingness lost'
        for field,key in [('mass','masses'),('charge','charges'),('atomicnumber','atomicnumbers')]:
            if missing: assert a[field] is None, field
            else: assert math.isclose(a[field],e[key][i],abs_tol=1e-5), (field,a[field],e[key][i])
    assert obj['bonds']==e['bonds']

def check_cif(obj, fixture):
    # Independent parser; use source atom-site records, not fpocket output.
    import gemmi
    block=gemmi.cif.read(str(fixture)).sole_block()
    table=block.find('_atom_site.', ['label_atom_id','label_comp_id','Cartn_x','Cartn_y','Cartn_z'])
    assert len(table)==obj['natoms']
    for row,a in zip(table,obj['atoms']):
        assert a['name']==gemmi.cif.as_string(row[0])
        assert a['resname']==gemmi.cif.as_string(row[1])
        for x,y in zip(a['xyz'],[row[i] for i in (2,3,4)]): assert math.isclose(x,float(y),abs_tol=1e-4)

def execute(binary, src, out, args=()):
    out.mkdir(parents=True,exist_ok=False)
    copied=out/src.name; shutil.copy2(src,copied)
    before=hashlib.sha256(copied.read_bytes()).hexdigest()
    result=run([binary,'-f',copied,*args])
    (out/'stdout.log').write_text(result.stdout);(out/'stderr.log').write_text(result.stderr)
    assert hashlib.sha256(copied.read_bytes()).hexdigest()==before
    tree=out/(src.stem+'_out')
    assert (tree/(src.stem+'_info.txt')).is_file(), 'No usable result'
    return tree

def volumes(tree,stem):
    return [float(x) for x in re.findall(r'^\s*Volume\s*:\s*([-+0-9.eE]+)',(tree/(stem+'_info.txt')).read_text(),re.M)]

def suite(binary, source, work, probe_bin=None, fixtures=None, oracle=None, architecture=None):
    work.mkdir(parents=True,exist_ok=False)
    report={'contract_sha256':hashlib.sha256((HERE/'test_contract.json').read_bytes()).hexdigest(),
            'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'checks':[]}
    def check(name,fn):
        try: detail=fn();record={'name':name,'passed':True,'detail':detail}
        except Exception as exc:record={'name':name,'passed':False,'error':str(exc)}
        report['checks'].append(record)
        (work/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(record),flush=True)
        return record['passed']
    if not check('candidate-present', lambda: run([binary,'-h']).returncode): return report
    if architecture:
        def arch():
            h=run(['readelf','-h',binary]).stdout; assert architecture in h,h
            p=run(['readelf','-l',binary]).stdout;assert 'INTERP' not in p
            d=run(['readelf','-d',binary]).stdout;assert '(NEEDED)' not in d
            if architecture=='AArch64':
                archive=binary.parents[2]/'library/libmolfile_plugin.a'
                h=run(['readelf','-h',archive]).stdout
                machines=re.findall(r'Machine:\s*(.+)',h)
                assert len(machines)==2 and all(m=='AArch64' for m in machines),machines
                symbols=run(['nm','-g','--defined-only',archive]).stdout
                for reader in ('pdbx','parm7'):
                    for operation in ('init','register','fini'):
                        assert f'molfile_{reader}plugin_{operation}' in symbols
        check('architecture-static',arch)
    if probe_bin:
        for name,kind in [('water.parm7','parm7'),('water-missing.parm7','parm7')]+[(s+'.cif','pdbx') for s in CONTRACT['default_cif']]:
            def reader_test(name=name,kind=kind):
                path=fixtures/name if kind=='parm7' else source/'data/sample'/name
                obj=probe(probe_bin,kind,path,expected_abi=20 if architecture=='Advanced Micro Devices X86-64' else 18)
                (work/(name+'.reader.json')).write_text(json.dumps(obj,indent=2)+'\n')
                if kind=='parm7':check_parm(obj,missing='missing' in name)
                else:check_cif(obj,path)
                if oracle:
                    expected=json.loads((oracle/(name+'.reader.json')).read_text())
                    assert expected['abi']==20 and obj['abi']==18
                    assert {k:v for k,v in obj.items() if k!='abi'}=={k:v for k,v in expected.items() if k!='abi'}, 'Reader differs from Intel library'
            check('reader-'+name,reader_test)
    cases=[{'name':s,'stem':s,'ext':ext,'args':[]} for ext,key in [('pdb','default_pdb'),('cif','default_cif')] for s in CONTRACT[key]]+CONTRACT['options']
    for case in cases:
        def reference_test(c=case):
            ref=source/'tests/reference_output'/c.get('reference_subdir','')/(c['stem']+'_out')
            tree=execute(binary,source/'data/sample'/(c['stem']+'.'+c['ext']),work/c['name'],c['args'])
            compare_tree(ref,tree)
        check('reference-'+case['name'],reference_test)
    for s in CONTRACT['default_pdb']:
        for i,args in enumerate(CONTRACT['changed_parameters']):
            def changed(s=s,i=i,args=args):
                tree=execute(binary,source/'data/sample'/(s+'.pdb'),work/f'changed-{s}-{i}',args)
                ref=source/'tests/reference_output'/(s+'_out')
                assert normalised(tree/(s+'_info.txt'))!=normalised(ref/(s+'_info.txt')), 'Parameters had no effect'
            check(f'changed-{s}-{i}',changed)
    def repetitions():
        samples=[]; times=[]
        for i in range(CONTRACT['volume_repetitions']):
            if times:
                while int(time.time())<=times[-1]:time.sleep(.1)
            times.append(int(time.time()))
            tree=execute(binary,source/'data/sample/1UYD.pdb',work/f'repeat-{i}')
            compare_tree(source/'tests/reference_output/1UYD_out',tree)
            values=volumes(tree,'1UYD');assert values and all(math.isfinite(v) and v>0 for v in values)
            samples.append(values)
        assert len({len(v) for v in samples})==1
        med=[statistics.median(v) for v in zip(*samples)]
        summary={'times':times,'samples':samples,'medians':med}
        (work/'volumes.json').write_text(json.dumps(summary,indent=2)+'\n')
        if oracle:
            baseline=json.loads((oracle/'volumes.json').read_text())['medians']
            assert len(baseline)==len(med)
            assert all(abs(a-b)/b<=.05 for a,b in zip(med,baseline)),(med,baseline)
        return summary
    check('volume-repetitions',repetitions)
    for name,contents in [('empty.pdb',''),('truncated.pdb','ATOM      1  CA')]:
        def invalid(name=name,contents=contents):
            folder=work/('invalid-'+name);folder.mkdir();f=folder/name;f.write_text(contents)
            r=subprocess.run([str(binary),'-f',str(f)],capture_output=True,text=True,timeout=120)
            info=folder/(f.stem+'_out')/(f.stem+'_info.txt')
            assert not info.exists(), 'Malformed input produced result'
            return {'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
        check('invalid-'+name,invalid)
    def missing():
        r=subprocess.run([str(binary),'-f',str(work/'missing.pdb')],capture_output=True,text=True,timeout=120)
        assert not (work/'missing_out').exists()
        return {'exit':r.returncode}
    check('missing-input',missing)
    report['passed']=all(c['passed'] for c in report['checks'])
    (work/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--probe',type=Path);p.add_argument('--fixtures',type=Path);p.add_argument('--oracle',type=Path);p.add_argument('--architecture');a=p.parse_args()
    r=suite(a.binary,a.source,a.work,a.probe,a.fixtures,a.oracle,a.architecture)
    raise SystemExit(0 if r.get('passed') else 1)
