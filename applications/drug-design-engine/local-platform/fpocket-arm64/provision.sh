#!/usr/bin/env bash
# Provision only the exact validated release. No network or implicit rebuild.
# Usage: provision.sh RELEASE_DIRECTORY BIN_DIRECTORY
set -euo pipefail
release=${1:?}; bin=${2:?}
if [ -f "$release/REVOKED.json" ]; then
    echo 'fpocket release revoked after extended validation; see REVOKED.json' >&2
    exit 2
fi
test "$(uname -m)" = aarch64
python3 - "$release" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]); r=json.loads((p/'acceptance.json').read_text())
assert r['pre_enablement_passed'] is True, 'Release has not passed acceptance'
assert r['candidate_abi']==18 and r['architecture']=='AArch64'
assert r['fpocket_version']=='4.2.2'
assert hashlib.sha256((p/'fpocket').read_bytes()).hexdigest()==r['binary_sha256'], 'Binary hash mismatch'
PY
readelf -h "$release/fpocket" | grep -q 'AArch64'
if readelf -l "$release/fpocket" | grep -q INTERP; then exit 1; fi
if readelf -d "$release/fpocket" | grep -q '(NEEDED)'; then exit 1; fi
mkdir -p "$bin"
if [ -f "$bin/fpocket" ] && cmp -s "$release/fpocket" "$bin/fpocket"; then exit 0; fi
temporary=$(mktemp "$bin/.fpocket.XXXXXX")
trap 'rm -f "$temporary"' EXIT
install -m 755 "$release/fpocket" "$temporary"
mv "$temporary" "$bin/fpocket"
