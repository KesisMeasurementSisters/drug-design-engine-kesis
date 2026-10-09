#!/usr/bin/env bash
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

# Coupled, verified DDE/fpocket release. Caller must keep the agent idle and save rollback.
set -euo pipefail
release=${1:?}; bin=${2:?}; source=${3:?}
test ! -e "$release/REVOKED.json"
test "$(uname -m)" = aarch64
readelf -h "$release/fpocket" | grep -q AArch64
if readelf -l "$release/fpocket" | grep -q INTERP; then exit 1; fi
if readelf -d "$release/fpocket" | grep -q '(NEEDED)'; then exit 1; fi
python3 - "$release" "$source" <<'PY'
import hashlib,json,os,sys,tempfile
from pathlib import Path
def require(ok, message):
    if not ok: raise ValueError(message)
release,source=map(Path,sys.argv[1:]);r=json.loads((release/'acceptance.json').read_text())
require(r['pre_enablement_passed'] is True, 'Release is not qualified')
require(r['architecture']=='AArch64' and r['candidate_abi']==18 and r['fpocket_version']=='4.2.2', 'Wrong release identity')
require(hashlib.sha256((release/'fpocket').read_bytes()).hexdigest()==r['binary_sha256'], 'Binary hash mismatch')
for name,expected in r['dde_source_files'].items():
    p=release/'dde'/name
    require(hashlib.sha256(p.read_bytes()).hexdigest()==expected, 'Source hash mismatch: '+name)
# Files have already been archived by promotion; replace each atomically while idle.
for name in r['dde_source_files']:
    target=source/'dde'/name
    fd,temp=tempfile.mkstemp(prefix='.fpocket-repair-',dir=target.parent)
    with os.fdopen(fd,'wb') as f:f.write((release/'dde'/name).read_bytes())
    os.chmod(temp,0o644);os.replace(temp,target)
PY
mkdir -p "$bin"
temporary=$(mktemp "$bin/.fpocket.XXXXXX")
trap 'rm -f "$temporary"' EXIT
install -m 755 "$release/fpocket" "$temporary"
mv "$temporary" "$bin/fpocket"
