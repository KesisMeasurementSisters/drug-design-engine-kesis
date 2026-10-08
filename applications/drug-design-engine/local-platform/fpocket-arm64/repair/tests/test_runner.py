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
