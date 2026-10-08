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
