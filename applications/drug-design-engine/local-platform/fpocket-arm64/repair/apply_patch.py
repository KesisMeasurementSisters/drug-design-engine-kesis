"""Apply this package's unified diffs with exact context; no fuzz or offset search."""

import re, sys
from pathlib import Path

from release_checks import require

root = Path(sys.argv[1])
for patch in sorted((Path(__file__).parent / "patches").glob("*.patch")):
    lines = patch.read_text().splitlines(True)
    target = root / lines[1][6:].strip()
    old = target.read_text().splitlines(True)
    new = []
    pos = 0
    i = 2
    while i < len(lines):
        m = re.match(r"@@ -(\d+)(?:,\d+)? \+\d+(?:,\d+)? @@", lines[i])
        require(m is not None, "Invalid patch header: " + lines[i])
        start = int(m[1]) - 1
        require(start >= pos, "Overlapping patch hunks")
        new.extend(old[pos:start])
        pos = start
        i += 1
        while i < len(lines) and not lines[i].startswith("@@ "):
            line = lines[i]
            i += 1
            if line[0] in " -":
                require(
                    pos < len(old) and old[pos] == line[1:],
                    f"Patch context mismatch: {target}:{pos}",
                )
                pos += 1
            if line[0] in " +":
                new.append(line[1:])
    new.extend(old[pos:])
    target.write_text("".join(new))
