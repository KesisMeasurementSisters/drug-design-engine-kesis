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

"""Exercise the actual shutil callback path used to stage a release package."""

import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rollback import copy_file


class DeploymentCopy(unittest.TestCase):
    def test_copytree_callback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            script = source / "script.sh"
            script.write_bytes(b"#!/bin/sh\nexit 0\n")
            script.chmod(0o755)
            (source / "nested").mkdir()
            (source / "nested/receipt.json").write_text("{}\n")
            target = root / "target"
            shutil.copytree(source, target, copy_function=copy_file)
            self.assertEqual(script.read_bytes(), (target / "script.sh").read_bytes())
            self.assertEqual(stat.S_IMODE((target / "script.sh").stat().st_mode), 0o755)
            self.assertEqual((target / "nested/receipt.json").read_text(), "{}\n")

    def test_string_paths_and_new_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input"
            source.write_bytes(b"unchanged")
            target = root / "new/output"
            copy_file(str(source), str(target))
            self.assertEqual(target.read_bytes(), b"unchanged")


if __name__ == "__main__":
    unittest.main()
