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

"""Run each candidate module in a fresh process; retain all failures."""

import json, os, subprocess, sys, time
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_checks import (
    digest,
    implementation_files,
    require,
    validate_dde,
    write_binding,
)

require(
    not sys.flags.optimize, "Acceptance tests must not run with disabled assertions"
)
package = Path(__file__).resolve().parents[1]
bound = implementation_files(package)
bound.update(
    {
        "test/" + p.name: p
        for p in (package.parents[2] / "tools/tests").glob("test_*.py")
    }
)
before = {name: digest(p) for name, p in bound.items()}
out = Path(sys.argv[1])
out.mkdir(exist_ok=False)
source = Path("/host-repo/applications/drug-design-engine/tools/tests")
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
env["PATH"] = "/usr/local/go/bin:" + env["PATH"]
reports = []
for path in sorted(source.glob("test_*.py")):
    start = time.monotonic()
    xml = out / (path.stem + ".xml")
    try:
        r = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(path),
                "-q",
                "-p",
                "no:cacheprovider",
                "--junitxml=" + str(xml),
            ],
            capture_output=True,
            text=True,
            timeout=150,
            env=env,
        )
        (out / (path.stem + ".log")).write_text(r.stdout + r.stderr)
        result = {
            "module": path.name,
            "exit": r.returncode,
            "seconds": round(time.monotonic() - start, 2),
        }
        if xml.exists():
            suites = ET.parse(xml).getroot().findall("testsuite")
            result.update(
                {
                    k: sum(int(s.attrib.get(k, 0)) for s in suites)
                    for k in ("tests", "failures", "errors", "skipped")
                }
            )
    except subprocess.TimeoutExpired as e:
        result = {"module": path.name, "exit": "timeout", "seconds": 150}
    reports.append(result)
    print(json.dumps(result), flush=True)
    (out / "report.json").write_text(json.dumps(reports, indent=2) + "\n")
validate_dde(reports, {p.name for p in source.glob("test_*.py")})
require(
    before == {name: digest(p) for name, p in bound.items()},
    "DDE source changed during testing",
)
bound["result/report.json"] = out / "report.json"
write_binding(out / "binding.json", bound)
(out / "binding-paths.json").write_text(
    json.dumps({name: str(p) for name, p in bound.items()}, indent=2) + "\n"
)
