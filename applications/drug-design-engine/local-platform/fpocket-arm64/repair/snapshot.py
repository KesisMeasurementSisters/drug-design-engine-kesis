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

"""Record non-secret working-tool and learning-artifact hashes before/after release."""

import hashlib, json, sys
from pathlib import Path

root = Path("/scion-volumes")


def hashes(folder):
    return {
        str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


r = {
    "learning": hashes(root / "learning"),
    "tools": hashes(root / "tools/bin"),
    "env_version": (root / "tools/ENV_VERSION").read_text().strip(),
}
Path(sys.argv[1]).write_text(json.dumps(r, indent=2) + "\n")
