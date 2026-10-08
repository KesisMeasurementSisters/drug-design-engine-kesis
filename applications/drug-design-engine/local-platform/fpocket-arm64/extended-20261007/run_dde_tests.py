"""Run each unmodified upstream module in a fresh process; retain all failures."""
import json, os, subprocess, sys, time
from pathlib import Path
import xml.etree.ElementTree as ET

out=Path(sys.argv[1]);out.mkdir(exist_ok=False)
source=Path('/scion-volumes/source/applications/drug-design-engine/tools/tests')
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
env['PATH']='/usr/local/go/bin:'+env['PATH']
reports=[]
for path in sorted(source.glob('test_*.py')):
    start=time.monotonic(); xml=out/(path.stem+'.xml')
    try:
        r=subprocess.run([sys.executable,'-m','pytest',str(path),'-q','-p','no:cacheprovider','--junitxml='+str(xml)],
                         capture_output=True,text=True,timeout=150,env=env)
        (out/(path.stem+'.log')).write_text(r.stdout+r.stderr)
        result={'module':path.name,'exit':r.returncode,'seconds':round(time.monotonic()-start,2)}
        if xml.exists():
            suites=ET.parse(xml).getroot().findall('testsuite')
            result.update({k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')})
    except subprocess.TimeoutExpired as e:
        result={'module':path.name,'exit':'timeout','seconds':150}
    reports.append(result);print(json.dumps(result),flush=True)
    (out/'report.json').write_text(json.dumps(reports,indent=2)+'\n')
raise SystemExit(not all(r['exit']==0 for r in reports))
