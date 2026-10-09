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

"""Promote a qualified coupled release while idle; restore the snapshot on failure.

Usage: promote.py PACKAGE_SOURCE RELEASE DESTINATION_PACKAGE BACKUP BEFORE_SNAPSHOT
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from release_checks import digest, require
from rollback import copy_file, restore


def promote(
    package_source,
    release,
    destination,
    backup,
    before_path,
    root=Path("/scion-volumes"),
):
    before = json.loads(before_path.read_text())
    tools = root / "tools"
    source = root / "source/applications/drug-design-engine/tools"
    require(
        not (tools / "bin/fpocket").exists(),
        "fpocket must remain disabled before promotion",
    )
    require(
        (tools / "ENV_VERSION").read_text().strip() == before["env_version"],
        "environment changed",
    )
    for category, folder in [("tools", tools / "bin"), ("learning", root / "learning")]:
        for name, expected in before[category].items():
            require(digest(folder / name) == expected, category + " changed: " + name)
    require(not destination.exists(), "use a new release package destination")
    backup.mkdir(exist_ok=False)
    names = [
        "tools/" + name
        for name in (
            "ENV_VERSION",
            "env-manifest.txt",
            "requirements.lock",
            "ENV_HISTORY",
            "bin/fpocket",
        )
    ]
    names += ["install-arm-learning.sh", "prepare-arm-installer.py"]
    names += [
        "source/applications/drug-design-engine/tools/dde/" + name
        for name in ("commands/pocket.py", "core/pocket_runtime.py")
    ]
    snapshot = {}
    for name in names:
        path = root / name
        snapshot[name] = digest(path) if path.exists() else None
        if path.exists():
            copy_file(path, backup / "files" / name)
    (backup / "snapshot.json").write_text(json.dumps(snapshot, indent=2) + "\n")
    try:
        shutil.copytree(
            package_source,
            destination,
            copy_function=copy_file,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        shutil.copytree(release, destination / "release", copy_function=copy_file)
        subprocess.run(
            [
                "bash",
                str(destination / "provision.sh"),
                str(destination / "release"),
                str(tools / "bin"),
                str(source),
            ],
            check=True,
        )
        subprocess.run(
            [
                "python3",
                str(destination / "prepare_installer.py"),
                str(source),
                str(root / "install-arm-learning.sh"),
                str(destination),
            ],
            check=True,
        )
        args = [
            str(destination / "prepare_installer.py"),
            str(source),
            str(root / "install-arm-learning.sh"),
            str(destination),
        ]
        (root / "prepare-arm-installer.py").write_text(
            "import runpy, sys\nsys.path.insert(0, "
            + repr(str(destination))
            + ")\nsys.argv = "
            + repr(args)
            + '\nrunpy.run_path(sys.argv[0], run_name="__main__")\n'
        )
    except BaseException:
        restore(backup, root)
        raise
    print(
        json.dumps(
            {
                "backup": str(backup),
                "release": str(destination / "release"),
                "binary_sha256": digest(tools / "bin/fpocket"),
            }
        )
    )


if __name__ == "__main__":
    promote(*map(Path, sys.argv[1:]))
