#!/usr/bin/env bash
# Run once, in a new disposable project; no network or model calls inside this script.
set -euo pipefail
project=${1:?}; source_input=${2:?}
source /scion-volumes/tools/env.sh
export DDE_PROJECT="$project"
test ! -e "$project"
dde init "$project"
cp "$source_input" "$project/1UYD.pdb"
sha256sum "$project/1UYD.pdb" > "$project/input-before.sha256"
timeout 150 dde pocket run "$project/1UYD.pdb" --json > "$project/run.json"
timeout 120 dde pocket analyze "$project/raw/structures/1UYD.pockets.json" --json > "$project/analyze.json"
sha256sum -c "$project/input-before.sha256"
python - "$project" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);r=json.loads((p/'run.json').read_text());a=json.loads((p/'analyze.json').read_text())
result={'run_exit':0,'analyze_exit':0,'n_pockets':r['n_pockets'],'best_pocket':a['metrics']['best_pocket'],'outputs':r['outputs']}
(p/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
PY
