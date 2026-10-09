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

"""A release requires complete evidence even under python -O."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import release_checks as gate


class ReleaseChecks(unittest.TestCase):
    def check(self, value):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "report.json"
            p.write_text(json.dumps(value))
            return gate.checked_report(p, {"a", "b"}, "name")

    def test_valid(self):
        self.check([{"name": "a", "passed": True}, {"name": "b", "passed": True}])

    def test_empty_partial_and_bad_schema(self):
        for value in (
            [],
            {},
            {"wrong": []},
            [{"name": "a", "passed": True}],
            [{"name": "a", "passed": True}, {"name": "a", "passed": True}],
            [{"name": "a", "passed": True}, {"name": "b", "passed": False}],
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.check(value)

    def test_empty_inventory(self):
        with self.assertRaises(ValueError):
            gate.validate_rows([], set(), "name")

    def test_skipped_module(self):
        with self.assertRaises(ValueError):
            gate.validate_dde(
                [
                    {
                        "module": "a",
                        "tests": 1,
                        "exit": 0,
                        "skipped": 1,
                        "errors": 0,
                        "failures": 0,
                    }
                ],
                {"a"},
            )

    def test_wrong_build_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "binary"
            binary.write_bytes(b"old")
            gate.write_binding(root / "binding.json", {"binary": binary})
            binary.write_bytes(b"new")
            with self.assertRaises(ValueError):
                gate.verify_binding(root / "binding.json", {"binary": binary})

    def test_optimized_python(self):
        code = 'import release_checks as g;g.validate_rows([], {"a"}, "name")'
        r = subprocess.run(
            [sys.executable, "-O", "-c", code],
            cwd=Path(gate.__file__).parent,
            capture_output=True,
        )
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
