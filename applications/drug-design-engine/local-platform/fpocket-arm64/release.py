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

"""Create a local release receipt only from completed, passing acceptance runs."""
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import sys

base,oracle,out=map(Path,sys.argv[1:])
reports={}
for name in ('arm-unfused-results/report.json','arm-unfused-repeat-results/report.json',
             'sanitizers-unfused/report.json','sanitizers-unfused-repeat/report.json',
             'scion-user-integration.json','scion-repeat-integration.json'):
    path=base/name; report=json.loads(path.read_text())
    assert report['passed'] is True and all(c['passed'] for c in report['checks']), name
    reports[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'checks':len(report['checks'])}
reference=json.loads((oracle/'report.json').read_text());assert reference['passed'] is True
reports['intel-oracle/report.json']={'sha256':hashlib.sha256((oracle/'report.json').read_bytes()).hexdigest(),
                                   'checks':len(reference['checks']) if 'checks' in reference else len(reference['scientific_checks'])+len(reference['reader_checks'])}
binary=base/'arm-unfused-repeat/fpocket-4.2.2/bin/fpocket'
archive=base/'arm-unfused-repeat/library/libmolfile_plugin.a'
summary={}
for name,path in [('intel',oracle/'volumes.json'),('arm',base/'arm-unfused-results/volumes.json'),
                  ('arm_repeat',base/'arm-unfused-repeat-results/volumes.json')]:
    r=json.loads(path.read_text());assert len(r['samples'])==10 and len(set(r['times']))==10
    summary[name]={'medians':r['medians'], 'ranges':[[min(v),max(v)] for v in zip(*r['samples'])],
                   'relative_standard_deviation':[statistics.pstdev(v)/statistics.mean(v) for v in zip(*r['samples'])]}
for name in ('arm','arm_repeat'):
    a=summary[name]['medians'];b=summary['intel']['medians'];assert len(a)==len(b)==13
    delta=[abs(x-y)/y for x,y in zip(a,b)];assert max(delta)<=.05
    summary[name]['maximum_relative_median_difference']=max(delta)
out.mkdir(exist_ok=False)
shutil.copy2(binary,out/'fpocket')
receipt={'pre_enablement_passed':True,'fpocket_version':'4.2.2','architecture':'AArch64','candidate_abi':18,
         'reference_abi':20,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
         'library_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
         'fpocket_source_sha256':'4042125e7243e03465200bee787e55a54c16c1a10908718af75275c46bfafaad',
         'molfile_source_sha256':'5af0805b7fb106652895e4132f9fe0d11e02ef85042b65f700e69ffe94bc316c',
         'molfile_commit':'5f817f263b89e8420174bb4bf0d0875a6ebe6136',
         'compiler':(base/'arm-unfused-repeat/compiler.txt').read_text(),
         'fpocket_cflags':(base/'arm-unfused-repeat/fpocket-cflags.txt').read_text().strip(),
         'reports':reports,'volume_variability':summary,'volume_tolerance':.05,
         'production_enablement':'pending doctor and bounded agent test'}
(out/'acceptance.json').write_text(json.dumps(receipt,indent=2)+'\n')
