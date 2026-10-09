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

"""Verify DDE's documented non-clobber guard, not automatic reanalysis success."""
import hashlib,json,os,sys,time
from pathlib import Path
from reader_edges import invoke

project=Path(sys.argv[1]);source=Path(sys.argv[2]);out=Path(sys.argv[3])
assert invoke(['dde','init',project],30)['exit']==0
env=dict(os.environ,DDE_PROJECT=str(project));records=[]
def call(args):
    r=invoke(args,120,env);assert not r['timeout'];records.append({'command':list(map(str,args)),**r});return r
r=call(['dde','pocket','run',source,'--json']);assert r['exit']==0
p=Path(json.loads(r['stdout'])['outputs']['pockets'])
r=call(['dde','pocket','analyze',p,'--json']);assert r['exit']==0
analysis=Path(json.loads(r['stdout'])['outputs']['analysis']);before=hashlib.sha256(analysis.read_bytes()).hexdigest()
# Ensure a new timestamp / Monte Carlo seed; do not edit any expected output.
time.sleep(1.1)
r=call(['dde','pocket','run',source,'--json']);assert r['exit']==0
r=call(['dde','pocket','analyze',p,'--json']);assert r['exit']!=0 and 'already holds a different analysis' in r['stderr']
assert hashlib.sha256(analysis.read_bytes()).hexdigest()==before
r=call(['dde','pocket','analyze',p,'--out','raw/reanalysis/second','--json']);assert r['exit']==0
assert Path(json.loads(r['stdout'])['outputs']['analysis'])!=analysis
assert hashlib.sha256(analysis.read_bytes()).hexdigest()==before
out.write_text(json.dumps({'passed':True,'description':'Existing analysis preserved; explicit alternate output succeeds. Initial workflow test incorrectly expected automatic overwrite.','records':records},indent=2)+'\n')
