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
