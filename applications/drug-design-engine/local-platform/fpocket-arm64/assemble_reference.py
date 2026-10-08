"""Combine unchanged Intel scientific checks with corrected ABI20 reader checks.

The original failing report is retained. Only its five ABI18 registration
assertions may be superseded; any other failure refuses an oracle.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys

def assemble(scientific, readers, out):
    report=json.loads((scientific/'report.json').read_text())
    corrected=json.loads((readers/'report.json').read_text())
    names={'water.parm7','water-missing.parm7','3VI4.cif','5RGF.cif','6TL9.cif'}
    assert {c['name'] for c in corrected}==names and len(corrected)==5
    assert all(c['passed'] for c in corrected)
    replacements={'reader-'+n for n in names}
    assert {c['name'] for c in report['checks'] if not c['passed']}==replacements
    assert all(c['passed'] for c in report['checks'] if c['name'] not in replacements)
    assert any(c['name']=='volume-repetitions' and c['passed'] for c in report['checks'])
    out.mkdir(exist_ok=False)
    shutil.copy2(scientific/'volumes.json',out/'volumes.json')
    for name in names:
        path=readers/(name+'.reader.json')
        assert json.loads(path.read_text())['abi']==20
        shutil.copy2(path,out/path.name)
    result={'passed':True,'scientific_report_sha256':hashlib.sha256((scientific/'report.json').read_bytes()).hexdigest(),
            'reader_report_sha256':hashlib.sha256((readers/'report.json').read_bytes()).hexdigest(),
            'superseded_checks':sorted(replacements),'reason':'Reference probe corrected to original bundled ABI20; candidate remains ABI18',
            'scientific_checks':[c for c in report['checks'] if c['name'] not in replacements], 'reader_checks':corrected}
    (out/'report.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':assemble(*map(Path,sys.argv[1:]))
