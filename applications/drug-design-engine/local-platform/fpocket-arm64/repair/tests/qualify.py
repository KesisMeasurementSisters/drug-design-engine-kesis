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

"""Run acceptance with immutable build/input bindings; never bind a failed run."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_checks import digest, implementation_files, require, write_binding

build, output, fixtures, columns = map(Path, sys.argv[1:])
package = Path(__file__).resolve().parents[1]
files = implementation_files(package)
files.update(
    {
        "binary": build / "fpocket-4.2.2/bin/fpocket",
        "probe": build / "probe",
        "sanitized-probe": build / "probe-sanitized",
        "library": build / "library/libmolfile_plugin.a",
    }
)
for label, folder in [("fixtures", fixtures), ("columns", columns)]:
    files.update({label + "/" + p.name: p for p in folder.iterdir() if p.is_file()})
for p in package.joinpath("tests").glob("*"):
    if p.is_file():
        files["test/" + p.name] = p
require(not sys.flags.optimize, "Do not disable acceptance assertions")
compiled_header = next(
    build.glob("molfile*/vmd/plugins/molfile_plugin/src/reader_validation.h")
)
require(
    digest(compiled_header) == digest(package / "reader_validation.h"),
    "Build used another reader validator",
)
before = {name: digest(path) for name, path in files.items()}
subprocess.run(
    [
        "bash",
        str(package / "tests/accept_build.sh"),
        str(build),
        str(output),
        str(fixtures),
        str(columns),
    ],
    check=True,
)
require(
    before == {name: digest(path) for name, path in files.items()},
    "inputs or implementation changed during acceptance",
)
files.update(
    {
        "result/" + str(p.relative_to(output)): p
        for p in output.rglob("*")
        if p.is_file()
        and p.name
        in ("report.json", "volumes.json", "repeat-cif.log", "repeat-parm7.log")
    }
)
write_binding(output / "binding.json", files)
(output / "binding-paths.json").write_text(
    json.dumps({name: str(path) for name, path in files.items()}, indent=2) + "\n"
)
