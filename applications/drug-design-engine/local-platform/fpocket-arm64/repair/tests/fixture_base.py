"""Maintained independent reader fixture definitions."""

import copy, hashlib, json
from pathlib import Path


def prepare(source, out):
    out.mkdir(exist_ok=False)
    lines = (source / "data/sample/1UYD.cif").read_text().splitlines()
    tags = [x.strip() for x in lines if x.startswith("_atom_site.")]
    rows = [x.split() for x in lines if x.startswith("ATOM ")][:3]
    cases = []

    def cif(name, changes=None, drop=(), reverse=False, ending="\n", valid=True):
        t = tags[:]
        r = copy.deepcopy(rows)
        if changes:
            for i, field, value in changes:
                r[i][t.index("_atom_site." + field)] = value
        if drop:
            keep = [
                i for i, v in enumerate(t) if v not in ["_atom_site." + d for d in drop]
            ]
            t = [t[i] for i in keep]
            r = [[row[i] for i in keep] for row in r]
        if reverse:
            t = t[::-1]
            r = [row[::-1] for row in r]
        text = (
            "data_edge\n#\nloop_\n"
            + "\n".join(t)
            + "\n"
            + "\n".join(" ".join(row) for row in r)
            + "\n#"
            + ending
        )
        path = out / (name + ".cif")
        path.write_text(text)
        expected = []
        for row in r:
            d = dict(zip(t, row))
            expected.append(
                {
                    "name": d["_atom_site.label_atom_id"].strip("'\""),
                    "resname": d["_atom_site.label_comp_id"],
                    "chain": d["_atom_site.label_asym_id"],
                    "resid": int(d["_atom_site.label_seq_id"]),
                    "xyz": (
                        [float(d["_atom_site.Cartn_" + v]) for v in "xyz"]
                        if valid
                        else None
                    ),
                }
            )
        cases.append(
            {
                "name": name,
                "file": path.name,
                "reader": "pdbx",
                "valid": valid,
                "atoms": expected,
            }
        )

    cif("minimal")
    for name, chain in [
        ("chain-two", "AB"),
        ("chain-three", "ABC"),
        ("chain-fifteen", "ABCDEFGHIJKLMNO"),
    ]:
        cif(
            name,
            [
                (i, key, chain)
                for i in range(3)
                for key in ("label_asym_id", "auth_asym_id")
            ],
        )
    cif(
        "chain-collision",
        [
            (i, key, chain)
            for i, chain in enumerate(("AAA", "AAB", "AAC"))
            for key in ("label_asym_id", "auth_asym_id")
        ],
    )
    cif("quoted-atom", [(1, "label_atom_id", "'CA'"), (1, "auth_atom_id", "'CA'")])
    cif("reordered-columns", reverse=True)
    cif("optional-omitted", drop=("occupancy", "B_iso_or_equiv", "pdbx_formal_charge"))
    cif("negative-residue", [(i, "label_seq_id", "-3") for i in range(3)])
    cif("no-final-newline", ending="")
    cif("missing-coordinate", [(0, "Cartn_x", "?")], valid=False)
    cif("nonfinite-coordinate", [(0, "Cartn_x", "nan")], valid=False)
    # Textual truncation, wrong record type, and empty inputs are invalid.
    for name, data in [
        ("empty", ""),
        ("missing-loop", "data_edge\n_entry.id edge\n"),
        (
            "truncated-row",
            (out / "minimal.cif").read_text().rsplit("ATOM", 1)[0] + "ATOM 3 C\n",
        ),
    ]:
        (out / (name + ".cif")).write_text(data)
        cases.append(
            {"name": name, "file": name + ".cif", "reader": "pdbx", "valid": False}
        )
    water = (Path(__file__).parents[2] / "fixtures/water.parm7").read_text()
    variants = {
        "water": (water, True),
        "water-comments": (
            water.replace("%FORMAT", "%COMMENT allowed comment\n%FORMAT"),
            True,
        ),
        "water-crlf": (water.replace("\n", "\r\n"), True),
        "water-empty": ("", False),
        "water-truncated-pointers": (water.split("%FLAG ATOM_NAME")[0][:260], False),
        "water-truncated-atoms": (
            water.split("%FLAG AMBER_ATOM_TYPE")[0].replace("O   H1  H2  ", "O   "),
            False,
        ),
        "water-missing-format": (water + "%FLAG MASS\n", False),
        "water-out-of-range-bond": (
            water.replace("       0       6       1", "       0      99       1"),
            False,
        ),
    }
    for name, (text, valid) in variants.items():
        (out / (name + ".parm7")).write_bytes(text.encode())
        cases.append(
            {"name": name, "file": name + ".parm7", "reader": "parm7", "valid": valid}
        )
    (out / "cases.json").write_text(json.dumps(cases, indent=2) + "\n")
    (out / "hashes.json").write_text(
        json.dumps(
            {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                for p in out.iterdir()
                if p.is_file()
            },
            indent=2,
        )
        + "\n"
    )
