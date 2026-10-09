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

# Usage: build.sh {arm|intel} INPUT_ARCHIVES OUTPUT_DIRECTORY
# Outputs stay outside tracked source. Refuse to reuse a build directory.
set -euo pipefail
mode=${1:?}; inputs=${2:?}; work=${3:?}
repair=$(cd "$(dirname "$0")" && pwd)
package=$(dirname "$repair")
case "$mode:$(uname -m)" in arm:aarch64|intel:x86_64) ;; *) echo 'Wrong build architecture/mode' >&2; exit 2;; esac
test ! -e "$work"
mkdir -p "$work"
printf '%s  %s\n' 4042125e7243e03465200bee787e55a54c16c1a10908718af75275c46bfafaad "$inputs/fpocket.tar.gz" | sha256sum -c -
printf '%s  %s\n' 5af0805b7fb106652895e4132f9fe0d11e02ef85042b65f700e69ffe94bc316c "$inputs/molfile.tar.gz" | sha256sum -c -
tar -xzf "$inputs/fpocket.tar.gz" -C "$work"
tar -xzf "$inputs/molfile.tar.gz" -C "$work"
fp="$work/fpocket-4.2.2"
plugin="$work/molfile_plugin-5f817f263b89e8420174bb4bf0d0875a6ebe6136/vmd/plugins/molfile_plugin/src"
python3 "$repair/apply_patch.py" "$work"
cp "$repair/reader_validation.h" "$plugin/reader_validation.h"
g++ --version > "$work/compiler.txt"
mkdir "$work/library" "$work/sanitized"
for name in pdbx parm7; do
    g++ -O2 -std=c++11 -fstack-protector-strong -D_FORTIFY_SOURCE=2 -DSTATIC_PLUGIN \
      -DVMDPLUGIN="molfile_${name}plugin" -I"$fp/plugins/include" -I"$plugin" \
      -c "$plugin/${name}plugin.C" -o "$work/library/${name}.o"
    g++ -O1 -g -std=c++11 -fsanitize=address,undefined -fno-omit-frame-pointer -DSTATIC_PLUGIN \
      -DVMDPLUGIN="molfile_${name}plugin" -I"$fp/plugins/include" -I"$plugin" \
      -c "$plugin/${name}plugin.C" -o "$work/sanitized/${name}.o"
done
ar rcs "$work/library/libmolfile_plugin.a" "$work/library/pdbx.o" "$work/library/parm7.o"
archive="$work/library/libmolfile_plugin.a"
g++ -O1 -g -std=c++14 -fsanitize=address,undefined -fno-omit-frame-pointer -I"$fp/plugins/include" \
  "$package/probe.cpp" "$work/sanitized/pdbx.o" "$work/sanitized/parm7.o" -o "$work/probe-sanitized"
readelf -h "$work/library/"*.o > "$work/library-architecture.txt"
nm -g --defined-only "$archive" > "$work/library-symbols.txt"
probe_abi=18

g++ -O2 -std=c++14 -DEXPECTED_PLUGIN_ABI="$probe_abi" -I"$fp/plugins/include" "$package/probe.cpp" "$archive" -o "$work/probe"
# Preserve DDE's static build settings, changing only the ARM archive path.
cflags='-W -Wextra -Wwrite-strings -Wstrict-prototypes -DM_OS_LINUX -DMNO_MEM_DEBUG -O2 -fstack-protector-strong -D_FORTIFY_SOURCE=2 -std=gnu99 -Iplugins/include -Iplugins/LINUXAMD64/molfile'
# Match the unfused arithmetic of the original x86 baseline. AArch64 GCC
# contracts expressions by default, changing surface areas and pocket ranking.
# Keep O2, hardening, source algorithms, and bundled Qhull settings unchanged.
if [ "$mode" = arm ]; then cflags="$cflags -ffp-contract=off"; fi
printf '%s\n' "$cflags" > "$work/fpocket-cflags.txt"
(cd "$fp" && make qhull > "$work/qhull.log" 2>&1)
(cd "$fp" && make bin/fpocket CFLAGS="$cflags" LFLAGS="-static -lm $archive -lstdc++" > "$work/fpocket-build.log" 2>&1)
readelf -h "$fp/bin/fpocket" > "$work/executable-architecture.txt"
sha256sum "$archive" "$fp/bin/fpocket" "$work/probe" > "$work/binaries.sha256"
printf 'Build complete: %s\n' "$work"
