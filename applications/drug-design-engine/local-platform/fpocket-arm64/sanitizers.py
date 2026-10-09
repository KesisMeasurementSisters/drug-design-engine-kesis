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

"""Instrumented reader checks; invalid access/UB blocks acceptance; leaks reported separately."""
import json
import os
from pathlib import Path
import subprocess
import sys
from validation import probe, check_parm, check_cif

binary,source,fixtures,output=map(Path,sys.argv[1:]);output.mkdir(parents=True,exist_ok=False)
checks=[]
cases=[('parm7',fixtures/'water.parm7'),('parm7',fixtures/'water-missing.parm7')]+[('pdbx',source/'data/sample'/f'{s}.cif') for s in ('3VI4','5RGF','6TL9')]
for kind,path in cases:
    env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    try:
        obj=probe(binary,kind,path,env)
        if kind=='parm7':check_parm(obj,missing='missing' in path.name)
        else:check_cif(obj,path)
        checks.append({'name':path.name,'passed':True})
    except Exception as exc:checks.append({'name':path.name,'passed':False,'error':str(exc)})
    leak=subprocess.run([str(binary),kind,str(path)],capture_output=True,text=True,timeout=30,env=dict(env,ASAN_OPTIONS='detect_leaks=1:halt_on_error=1'))
    (output/(path.name+'.leaks.log')).write_text(leak.stdout+'\n'+leak.stderr)
(output/'report.json').write_text(json.dumps({'passed':all(c['passed'] for c in checks),'checks':checks},indent=2)+'\n')
raise SystemExit(0 if all(c['passed'] for c in checks) else 1)
