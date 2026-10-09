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

"""Generate the local ARM overlay for the coupled, accepted repair release."""

from pathlib import Path
import sys
from release_checks import require

source, destination, package = map(Path, sys.argv[1:])
text = (source / "install.sh").read_text()
original = 'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"'
require(original in text, "Installer SCRIPT_DIR context changed")
text = text.replace(original, f'SCRIPT_DIR="{source}"', 1)
anchor = (
    'BINARY_STATUS=""\nfor tool in vina fpocket rate4site muscle hypex elo prox; do'
)
require(anchor in text, "Installer binary-loop context changed")
override = f"""# Local verified ARM fpocket and DDE repair; no rebuild or cloud call.
install_fpocket() {{
    bash "{package}/provision.sh" "{package}/release" "$BIN_DIR" "{source}"
}}
"""
destination.write_text(text.replace(anchor, override + anchor, 1))
