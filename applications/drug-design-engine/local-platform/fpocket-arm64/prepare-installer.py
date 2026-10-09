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

"""Create a local installer overlay; the frozen upstream checkout is untouched."""
from pathlib import Path
import sys

source=Path(sys.argv[1])
destination=Path(sys.argv[2])
package=Path(sys.argv[3])
text=(source/'install.sh').read_text()
original='SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"'
assert original in text
text=text.replace(original,f'SCRIPT_DIR="{source}"',1)
anchor='BINARY_STATUS=""\nfor tool in vina fpocket rate4site muscle hypex elo prox; do'
assert anchor in text
override=f'''# Local ARM overlay. Provision the hash-verified, tested fpocket release.
install_fpocket() {{
    bash "{package}/provision.sh" "{package}/release" "$BIN_DIR"
}}
'''
destination.write_text(text.replace(anchor,override+anchor,1))
