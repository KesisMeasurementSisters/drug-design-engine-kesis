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
