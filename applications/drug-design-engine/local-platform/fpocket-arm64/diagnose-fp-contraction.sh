#!/usr/bin/env bash
# Diagnostic only: isolate GCC's fused multiply/add behaviour without editing
# scientific source, the accepted recipe, or frozen reference outputs.
set -euo pipefail
original=${1:?original ARM build}; work=${2:?new diagnostic directory}
test ! -e "$work"
mkdir "$work"
cp -a "$original/fpocket-4.2.2" "$work/"
fp="$work/fpocket-4.2.2"
# Only these copied products are removed; retain the original failed build.
rm "$fp/obj/"*.o "$fp/bin/fpocket"
cflags='-W -Wextra -Wwrite-strings -Wstrict-prototypes -DM_OS_LINUX -DMNO_MEM_DEBUG -O2 -fstack-protector-strong -D_FORTIFY_SOURCE=2 -std=gnu99 -Iplugins/include -Iplugins/LINUXAMD64/molfile -ffp-contract=off'
(cd "$fp" && make bin/fpocket CFLAGS="$cflags" LFLAGS="-static -lm $original/library/libmolfile_plugin.a -lstdc++" > "$work/build.log" 2>&1)
mkdir "$work/test"
cp "$fp/data/sample/1UYD.pdb" "$work/test/"
timeout 120 "$fp/bin/fpocket" -f "$work/test/1UYD.pdb" > "$work/run.log" 2>&1
PYTHONPATH="$(dirname "$0")" python3 - "$fp/tests/reference_output/1UYD_out" "$work/test/1UYD_out" <<'PY'
import sys
from pathlib import Path
from validation import compare_tree
compare_tree(*map(Path,sys.argv[1:]))
print('Exact deterministic 1UYD comparison passed')
PY
