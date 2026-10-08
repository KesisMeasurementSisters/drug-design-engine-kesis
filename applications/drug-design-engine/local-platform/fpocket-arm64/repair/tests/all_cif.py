"""Separate valid bundled CIFs from the retained malformed writer fixture."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from validation import probe,check_cif
import gemmi
binary,source,out=map(Path,sys.argv[1:]);out.mkdir(exist_ok=False);results=[]
for path in sorted((source/'data/sample').glob('*.cif')):
    try:
        if path.name=='1UYD_wrote.cif':
            # Its type_symbol column contains atom names (OE1, CG1, etc.),
            # including values longer than any chemical element symbol.
            block=gemmi.cif.read(str(path)).sole_block()
            invalid=[x for x in block.find_values('_atom_site.type_symbol') if len(gemmi.cif.as_string(x))>2]
            assert invalid,'Retained malformed fixture changed'
            r=subprocess.run([str(binary),'pdbx',str(path)],capture_output=True,text=True,timeout=30,
                             env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
            assert r.returncode>0 and 'AddressSanitizer' not in r.stderr and 'runtime error:' not in r.stderr
            detail={'expected_rejection':'invalid element symbols','examples':sorted(set(invalid))[:8]}
        else:
            obj=probe(binary,'pdbx',path,dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
            check_cif(obj,path);detail={'atoms':obj['natoms']}
        result={'fixture':path.name,'passed':True,'detail':detail}
    except Exception as e:result={'fixture':path.name,'passed':False,'error':str(e)}
    result['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();results.append(result)
    (out/'report.json').write_text(json.dumps(results,indent=2)+'\n')
raise SystemExit(not all(x['passed'] for x in results))
