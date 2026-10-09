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

"""The preserved Intel oracle has separate scientific and reader inventories."""

import copy
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assemble_release import validate_original_reference


class OriginalReference(unittest.TestCase):
    def setUp(self):
        self.inventory = {
            "intel-science": {"expected": ["science"]},
            "sanitizers": {"expected": ["reader"]},
        }
        self.report = {
            "passed": True,
            "scientific_checks": [
                {"name": "science", "passed": True},
                {"name": "architecture-static", "passed": True},
            ],
            "reader_checks": [{"name": "reader", "passed": True}],
        }

    def test_valid_split_report(self):
        validate_original_reference(self.report, self.inventory)

    def test_empty_partial_or_unsplit(self):
        for value in ({}, [], {"passed": True, "checks": []}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_original_reference(value, self.inventory)
        for field in ("scientific_checks", "reader_checks"):
            value = copy.deepcopy(self.report)
            value[field] = []
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_original_reference(value, self.inventory)

    def test_duplicate(self):
        self.report["reader_checks"] *= 2
        with self.assertRaises(ValueError):
            validate_original_reference(self.report, self.inventory)

    def test_failed_or_skipped(self):
        for key, value in (("passed", False), ("skipped", True), ("timeout", True)):
            report = copy.deepcopy(self.report)
            report["reader_checks"][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_original_reference(report, self.inventory)

    def test_wrong_identity(self):
        self.report["scientific_checks"][0]["name"] = "unexpected"
        with self.assertRaises(ValueError):
            validate_original_reference(self.report, self.inventory)

    def test_optimized_python(self):
        code = (
            "from assemble_release import validate_original_reference; validate_original_reference({'passed':True}, "
            + repr(self.inventory)
            + ")"
        )
        result = subprocess.run(
            [sys.executable, "-O", "-c", code],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
