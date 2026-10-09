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

"""Restore an explicit deployment snapshot, retaining failed files for diagnosis."""

import json
import shutil
import sys
from pathlib import Path
from release_checks import digest, require


def copy_file(source, target):
    source, target = Path(source), Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    shutil.copymode(source, target)


def restore(backup, root=Path("/scion-volumes")):
    backup, root = Path(backup), Path(root)
    manifest = json.loads((backup / "snapshot.json").read_text())
    # Validate the complete backup before touching the live files.
    for name, expected in manifest.items():
        require(
            not Path(name).is_absolute() and ".." not in Path(name).parts,
            "invalid snapshot path",
        )
        if expected is not None:
            require(
                digest(backup / "files" / name) == expected,
                "backup checksum mismatch: " + name,
            )
    failed = backup / "failed-promotion"
    failed.mkdir(exist_ok=False)
    for name, expected in manifest.items():
        target = root / name
        if target.exists():
            copy_file(target, failed / name)
        if expected is None:
            target.unlink(missing_ok=True)
        else:
            copy_file(backup / "files" / name, target)
    print("Restored fpocket-disabled snapshot; failed promotion files retained.")


if __name__ == "__main__":
    restore(Path(sys.argv[1]))
