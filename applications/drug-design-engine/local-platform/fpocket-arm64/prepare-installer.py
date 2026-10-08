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
