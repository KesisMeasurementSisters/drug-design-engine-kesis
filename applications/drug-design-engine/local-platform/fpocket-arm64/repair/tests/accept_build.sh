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

# Offline candidate acceptance. Each output path must be new.
set -euo pipefail
build=${1:?}; output=${2:?}
fixtures=${3:-/host-repo/.dde-local/fpocket-validation/repair-fixtures}
columns=${4:-/host-repo/.dde-local/fpocket-validation/repair-columns}
package=/host-repo/applications/drug-design-engine/local-platform/fpocket-arm64
python=/scion-volumes/tools/.venv/bin/python
source="$build/fpocket-4.2.2"
mkdir "$output"
python3 "$package/repair/tests/readers.py" run "$build/probe-sanitized" "$fixtures" "$output/boundaries" 18 > "$output/boundaries.log" 2>&1
python3 "$package/repair/tests/readers.py" run "$build/probe-sanitized" "$columns" "$output/columns" 18 > "$output/columns.log" 2>&1
"$python" "$package/validation.py" --binary "$source/bin/fpocket" --source "$source" --work "$output/science" --probe "$build/probe" --fixtures "$package/fixtures" --architecture AArch64 > "$output/science.log" 2>&1
"$python" "$package/repair/tests/all_cif.py" "$build/probe-sanitized" "$source" "$output/all-cif"
"$python" "$package/extended-20261007/additional_structures.py" structures "$source/bin/fpocket" "$source" "$output/additional" /host-repo/.dde-local/fpocket-validation/extended-intel-structures > "$output/additional.log" 2>&1
"$python" "$package/sanitizers.py" "$build/probe-sanitized" "$source" "$package/fixtures" "$output/sanitizers"
g++ -O1 -g -std=c++14 -fsanitize=address,undefined -fno-omit-frame-pointer -I"$source/plugins/include" "$package/repair/tests/repeat_probe.cpp" "$build/sanitized/pdbx.o" "$build/sanitized/parm7.o" -o "$output/repeat-probe"
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 timeout 30 "$output/repeat-probe" pdbx /host-repo/.dde-local/fpocket-validation/repair-fixtures/minimal.cif > "$output/repeat-cif.log" 2>&1
ASAN_OPTIONS=detect_leaks=1:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 timeout 30 "$output/repeat-probe" parm7 "$package/fixtures/water.parm7" > "$output/repeat-parm7.log" 2>&1
