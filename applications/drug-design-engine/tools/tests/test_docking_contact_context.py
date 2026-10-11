# Copyright 2026 Kesis & Sisters Technologies Inc.
# SPDX-License-Identifier: Apache-2.0

"""Opt-in contact context must explain hydrogen warnings without hiding overlap.

Small geometric controls are deliberately artificial, not docking predictions.
The real oncology replay is recorded separately with its frozen input hashes.
"""

import json
import tempfile
import unittest
from pathlib import Path

from click.testing import CliRunner

from dde.commands.docking import (
    _compute_contacts,
    _contact_atom_context,
    _parse_pdbqt_atoms,
    docking,
)
from dde.common import AppState
from dde.core import provenance


def atom(serial, name, kind, x, *, chain="A", resnum=1):
    line = (
        f"ATOM  {serial:5d} {name:>4s} LIG {chain}{resnum:4d}    "
        f"{x:8.3f}{0.0:8.3f}{0.0:8.3f}"
    )
    return line.ljust(77) + kind + "\n"


class TestContactAtomContext(unittest.TestCase):
    def context(self, pose, receptor, threshold=2.0):
        pa = _parse_pdbqt_atoms(pose, atom_context=True)
        ra = _parse_pdbqt_atoms(receptor, atom_context=True)
        contact = _compute_contacts(pa, ra, 4.0)[0]
        return _contact_atom_context(pa, ra, contact, threshold)

    def test_hydrogen_warning_does_not_imply_heavy_atom_overlap(self):
        context = self.context(
            atom(1, "H", "HD", 0) + atom(2, "O", "OA", -1),
            atom(3, "HH22", "HD", 1.3) + atom(4, "NH2", "N", 2),
        )
        self.assertEqual(context["short_distance_basis"], "hydrogen_involving_only")
        self.assertEqual(context["nearest_pair"]["distance"], 1.3)
        self.assertEqual(context["nearest_heavy_atom_pair"]["distance"], 3.0)
        self.assertEqual(context["nearest_pair"]["receptor_atom"]["name"], "HH22")

    def test_even_closer_hydrogens_do_not_hide_heavy_atom_overlap(self):
        context = self.context(
            atom(1, "H", "HD", 0) + atom(2, "CA", "C", 1),
            atom(3, "H", "HD", 0.2) + atom(4, "C", "C", 2.2),
        )
        self.assertEqual(context["short_distance_basis"], "heavy_atom_below_threshold")
        self.assertEqual(context["nearest_pair"]["distance"], 0.2)
        self.assertEqual(context["nearest_heavy_atom_pair"]["distance"], 1.2)
        self.assertEqual(
            context["nearest_heavy_atom_pair"]["ligand_atom"]["name"], "CA"
        )

    def test_missing_types_are_unknown_not_a_clearance(self):
        context = self.context(atom(1, "H", "", 0), atom(2, "H", "HD", 1))
        self.assertFalse(context["atom_types_complete"])
        self.assertIsNone(context["nearest_heavy_atom_pair"])
        self.assertEqual(context["short_distance_basis"], "unknown_atom_types")

    def test_known_heavy_overlap_survives_other_missing_types(self):
        context = self.context(
            atom(1, "C", "C", 0) + atom(2, "X", "", 8),
            atom(3, "C", "C", 1),
        )
        self.assertFalse(context["atom_types_complete"])
        self.assertEqual(context["short_distance_basis"], "heavy_atom_below_threshold")

    def test_threshold_is_strict_and_uses_existing_rounding(self):
        for distance, expected in [
            (1.999, "heavy_atom_below_threshold"),
            (2.0, "none_below_threshold"),
            (2.001, "none_below_threshold"),
        ]:
            with self.subTest(distance=distance):
                context = self.context(
                    atom(1, "C", "C", 0), atom(2, "C", "C", distance)
                )
                self.assertEqual(context["short_distance_basis"], expected)

    def test_parser_default_shape_is_unchanged(self):
        self.assertEqual(
            _parse_pdbqt_atoms(atom(1, "CA", "C", 1)),
            [
                {
                    "chain": "A",
                    "res_name": "LIG",
                    "res_num": 1,
                    "x": 1.0,
                    "y": 0.0,
                    "z": 0.0,
                }
            ],
        )


class TestContactContextCLI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".dde").mkdir()
        (self.root / "pose.pdbqt").write_text(
            "MODEL 1\n" + atom(1, "H", "HD", 0) + atom(2, "O", "OA", -1) + "ENDMDL\n"
        )
        (self.root / "receptor.pdbqt").write_text(
            atom(3, "H", "HD", 1.3)
            + atom(4, "N", "N", 2)
            + atom(5, "C", "C", 1, chain="B")
        )

    def invoke(self, *args):
        result = CliRunner().invoke(
            docking, list(args), obj=AppState(project_override=str(self.root))
        )
        self.assertEqual(result.exit_code, 0, result.output + repr(result.exception))
        return result

    def test_opt_in_preserves_old_fields_and_default_payload(self):
        self.invoke("contacts", "pose.pdbqt", "receptor.pdbqt", "--out", "raw/old")
        self.invoke(
            "contacts",
            "pose.pdbqt",
            "receptor.pdbqt",
            "--out",
            "raw/new",
            "--atom-context",
        )
        old = json.loads((self.root / "raw/old/pose.contacts.json").read_text())
        new = json.loads((self.root / "raw/new/pose.contacts.json").read_text())
        self.assertNotIn("atom_context_version", old)
        self.assertEqual(new.pop("atom_context_version"), 1)
        for pose in new["contacts"]:
            for residue in pose["residues"]:
                residue.pop("atom_context", None)
        for warning in new["steric_clashes"]:
            warning.pop("chain")
            warning.pop("atom_context")
        self.assertEqual(old, new)

    def test_context_reaches_json_sidecar_and_terminal_without_losing_warnings(self):
        result = self.invoke(
            "contacts",
            "pose.pdbqt",
            "receptor.pdbqt",
            "--atom-context",
            "--out",
            "raw/context",
            "--json",
        )
        record = json.loads((self.root / "raw/context/pose.contacts.json").read_text())
        warnings = record["steric_clashes"]
        self.assertEqual(len(warnings), 2)
        self.assertEqual({w["chain"] for w in warnings}, {"A", "B"})
        self.assertEqual(
            warnings[0]["atom_context"]["short_distance_basis"],
            "hydrogen_involving_only",
        )
        sidecar = json.loads(
            (self.root / "raw/context/pose.contacts.meta.json").read_text()
        )
        code = "docking.short_distance_requires_atom_context"
        self.assertIn(code, provenance.RELAY_CODES)
        self.assertIn(code, [x["code"] for x in sidecar["mandatory_relays"]])
        self.assertTrue(sidecar["parameters"]["atom_context"])
        self.assertIn(code, result.output)
        self.assertEqual(
            sidecar["outputs"][0]["sha256"],
            provenance.sha256_file(self.root / "raw/context/pose.contacts.json"),
        )

    def test_context_relay_is_absent_without_short_distances(self):
        (self.root / "receptor.pdbqt").write_text(atom(3, "C", "C", 3))
        result = self.invoke(
            "contacts", "pose.pdbqt", "receptor.pdbqt", "--atom-context"
        )
        self.assertNotIn("docking.short_distance_requires_atom_context", result.output)

    def test_matrix_remains_all_atom_distance_based(self):
        self.invoke("contacts-matrix", "pose.pdbqt", "--receptor", "receptor.pdbqt")
        record = json.loads(
            (self.root / "raw/docking/matrix.contacts-matrix.json").read_text()
        )
        self.assertNotIn("atom_context", json.dumps(record))
        self.assertIn("1.3", json.dumps(record))


if __name__ == "__main__":
    unittest.main()
