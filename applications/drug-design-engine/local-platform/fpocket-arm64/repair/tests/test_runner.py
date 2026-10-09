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

"""Infrastructure failures must not count as successful malformed-input rejection."""

import contextlib, io, json, tempfile, unittest
from pathlib import Path
from readers import run, invoke


class RunnerFailures(unittest.TestCase):
    def rejected_runtime(self, diagnostic, code):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fixtures = root / "fixtures"
            fixtures.mkdir()
            (fixtures / "bad.cif").write_text("invalid")
            (fixtures / "cases.json").write_text(
                json.dumps(
                    [
                        {
                            "name": "bad",
                            "file": "bad.cif",
                            "reader": "pdbx",
                            "valid": False,
                        }
                    ]
                )
            )
            executable = root / "probe"
            executable.write_text(
                '#!/bin/sh\nprintf "%s\\n" "'
                + diagnostic
                + '" >&2\nexit '
                + str(code)
                + "\n"
            )
            executable.chmod(0o755)
            with contextlib.redirect_stdout(io.StringIO()):
                accepted = run(executable, fixtures, root / "results", 18)
            self.assertFalse(accepted)

    def test_sanitizer_startup(self):
        self.rejected_runtime("AddressSanitizer: CHECK failed", 1)

    def test_unknown_failure(self):
        self.rejected_runtime("runtime could not start", 1)

    def test_undefined_behaviour(self):
        self.rejected_runtime("runtime error: integer overflow", 66)

    def test_timeout(self):
        result = invoke(["/bin/sh", "-c", "sleep 10"], 0.02)
        self.assertTrue(result["timeout"])


if __name__ == "__main__":
    unittest.main()
