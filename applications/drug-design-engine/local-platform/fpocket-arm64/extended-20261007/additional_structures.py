"""Broader bundled-fixture coverage; never modify original reference results."""
import json, sys, hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]))
from validation import probe, check_cif, execute, compare_tree

mode,binary,source,out=sys.argv[1:5];binary=Path(binary);source=Path(source);out=Path(out);out.mkdir(exist_ok=False)
results=[]
names=['1UYD.cif','1g50.pdb','1g50.cif','1orc.pdb','1orc.cif','4bdf.pdb','4bdf.cif','4gfo.cif','6a5k.cif','7z9t.cif']
paths=sorted((source/'data/sample').glob('*.cif')) if mode=='readers' else [source/'data/sample'/n for n in names]
for path in paths:
    try:
        if mode=='readers':
            obj=probe(binary,'pdbx',path);check_cif(obj,path)
            detail={'atoms':obj['natoms']}
        else:
            tree=execute(binary,path,out/path.name)
            if len(sys.argv)>5:compare_tree(Path(sys.argv[5])/path.name/(path.stem+'_out'),tree)
            detail={'output_files':sum(p.is_file() for p in tree.rglob('*'))}
        record={'fixture':path.name,'passed':True,'detail':detail}
    except Exception as e:record={'fixture':path.name,'passed':False,'error':str(e)}
    record['fixture_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    results.append(record);print(json.dumps(record),flush=True)
    (out/'report.json').write_text(json.dumps(results,indent=2)+'\n')
raise SystemExit(not all(r['passed'] for r in results))
