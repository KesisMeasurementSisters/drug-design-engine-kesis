"""Freeze boundary expectations before compiling repaired readers."""

import hashlib, json, sys
from pathlib import Path

package = Path(__file__).resolve().parents[2]
import fixture_base as edges

out = Path(sys.argv[2])
edges.prepare(Path(sys.argv[1]), out)
cases = json.loads((out / "cases.json").read_text())
base = (out / "minimal.cif").read_text()
tags = [x for x in base.splitlines() if x.startswith("_atom_site.")]


def change(name, field, value, valid):
    lines = base.splitlines()
    idx = tags.index("_atom_site." + field)
    for n, line in enumerate(lines):
        if line.startswith("ATOM "):
            row = line.split()
            row[idx] = value
            lines[n] = " ".join(row)
    path = out / (name + ".cif")
    path.write_text("\n".join(lines) + "\n")
    case = {"name": name, "file": path.name, "reader": "pdbx", "valid": valid}
    if valid:
        case["atoms"] = json.loads(json.dumps(cases[0]["atoms"]))
        if field == "label_asym_id":
            for atom in case["atoms"]:
                atom["chain"] = value
    cases.append(case)


for field in ("label_asym_id", "auth_asym_id"):
    for length in (1, 14, 15, 16, 64, 1024):
        change(field + str(length), field, "A" * length, length <= 15)
for field in ("Cartn_x", "Cartn_y", "Cartn_z"):
    for value in ("?", ".", "nan", "inf", "1e999", "1.2junk"):
        change(field + value.replace(".", "dot"), field, value, False)
change("overlong-atom", "label_atom_id", "ABCDE", False)
change("overlong-residue", "label_comp_id", "ABCDEFGH", False)
change("overlong-insertion", "pdbx_PDB_ins_code", "AB", False)
water = (out / "water.parm7").read_text()
for name, text in {
    "negative-respointer": water.replace(
        "       1\n%FLAG BONDS", "      -1\n%FLAG BONDS"
    ),
    "zero-respointer": water.replace("       1\n%FLAG BONDS", "       0\n%FLAG BONDS"),
    "nonmultiple-bond": water.replace(
        "       0       6       1", "       0       5       1"
    ),
    "negative-bond": water.replace(
        "       0       6       1", "       0      -3       1"
    ),
    "duplicate-section": water + "%FLAG ATOM_NAME\n%FORMAT(20a4)\nO   H1  H2  \n",
    "missing-atoms": water[: water.index("%FLAG ATOM_NAME")],
}.items():
    path = out / (name + ".parm7")
    path.write_text(text)
    cases.append({"name": name, "file": path.name, "reader": "parm7", "valid": False})
(out / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")
(out / "hashes.json").write_text(
    json.dumps(
        {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in out.iterdir()
            if p.is_file() and p.name != "hashes.json"
        },
        indent=2,
    )
    + "\n"
)
print(len(cases), "frozen cases")

# Independently defined semantic cases from the review, before the next build.
for field in ("auth_seq_id", "label_seq_id"):
    change("missing-" + field, field, "?", False)
change("hex-coordinate", "Cartn_x", "0x1p2", False)
change("quoted-missing-number", "auth_seq_id", "'?'", False)
parts = water.split("%FLAG ")
a = next(i for i, part in enumerate(parts) if part.startswith("RESIDUE_LABEL"))
b = next(i for i, part in enumerate(parts) if part.startswith("RESIDUE_POINTER"))
parts[a], parts[b] = parts[b], parts[a]
(out / "water-reordered.parm7").write_text("%FLAG ".join(parts))
cases.append(
    {
        "name": "water-reordered",
        "file": "water-reordered.parm7",
        "reader": "parm7",
        "valid": True,
    }
)
(out / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")
(out / "hashes.json").write_text(
    json.dumps(
        {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in out.iterdir()
            if p.is_file() and p.name != "hashes.json"
        },
        indent=2,
    )
    + "\n"
)
