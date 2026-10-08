"""Regression contracts from the 2026-10-07 review, specified before repairs."""

import json
import sys
from pathlib import Path

import pytest
from dde.core.errors import ArtifactError, UsageError
from dde.core import pocket_runtime as runtime
from dde.commands import pocket


def test_renamed_record_cannot_supply_its_own_marker(tmp_path):
    path = tmp_path / "orphan.json"
    path.write_text(json.dumps({"publication_version": 1}))
    with pytest.raises(ArtifactError):
        runtime.read_bundle_metadata(path, {"publication_version": 1})


@pytest.mark.parametrize("marker", [None, {}, {"outputs": []}])
def test_complete_marker_required(tmp_path, marker):
    path = tmp_path / "sample.pockets.json"
    path.write_text("{}")
    if marker is not None:
        path.with_name("sample.pockets.meta.json").write_text(json.dumps(marker))
    with pytest.raises(ArtifactError):
        runtime.read_bundle_metadata(path, {"publication_version": 1})


def test_timeout_retains_diagnostics(tmp_path):
    with pytest.raises(ArtifactError) as caught:
        runtime.run_bounded(
            [
                sys.executable,
                "-c",
                'import sys,time; print("BEFORE_HANG",file=sys.stderr,flush=True); time.sleep(10)',
            ],
            tmp_path,
            timeout=0.2,
        )
    assert "BEFORE_HANG" in caught.value.detail


def test_insertion_selector_is_distinct():
    assert pocket._parse_near("A:145A") != pocket._parse_near("A:145B")


def test_ambiguous_selector_refused():
    pockets = [
        {"rank": 1, "residues": [{"chain": "A", "resnum": 145, "insertion_code": "A"}]},
        {"rank": 2, "residues": [{"chain": "A", "resnum": 145, "insertion_code": "B"}]},
    ]
    with pytest.raises(UsageError, match="ambiguous"):
        runtime.resolve_selectors(pocket._parse_near("A:145"), pockets)


def test_explicit_selector_matches_one_residue():
    pockets = [
        {"rank": 1, "residues": [{"chain": "A", "resnum": 145, "insertion_code": "A"}]},
        {"rank": 2, "residues": [{"chain": "A", "resnum": 145, "insertion_code": "B"}]},
    ]
    wanted = runtime.resolve_selectors(pocket._parse_near("A:145B"), pockets)
    assert len(wanted) == 1
    assert runtime.residue_key(pockets[1]["residues"][0]) in wanted
    assert runtime.residue_key(pockets[0]["residues"][0]) not in wanted


CIF = """data_test
loop_
_atom_site.group_PDB
_atom_site.id
_atom_site.type_symbol
_atom_site.label_atom_id
_atom_site.label_comp_id
_atom_site.label_asym_id
_atom_site.label_seq_id
_atom_site.auth_asym_id
_atom_site.auth_seq_id
_atom_site.Cartn_x
_atom_site.Cartn_y
_atom_site.Cartn_z
ATOM 1 C CA ALA L 42 A ? 1 2 3
"""


def test_stage_identity_fallback_preserves_missingness(tmp_path):
    source = tmp_path / "original.cif"
    source.write_text(CIF)
    work = tmp_path / "input.cif"
    identities = runtime.stage_structure(source, work, "cif")
    assert source.read_text() == CIF
    row = next(runtime.atom_rows(work.read_text(), "cif"))
    assert row["auth_seq_id"] == "42"
    records = runtime.residue_records(work.read_text(), "cif", identities=identities)
    assert records[0]["resnum"] == 42
    assert records[0]["auth_resnum"] is None
    assert records[0]["identity_namespace"] == "label"


def test_stage_rejects_unrepresentable_identity(tmp_path):
    source = tmp_path / "original.cif"
    source.write_text(CIF.replace("L 42 A ?", "L ? A ?"))
    with pytest.raises(ArtifactError):
        runtime.stage_structure(source, tmp_path / "input.cif", "cif")


def test_actual_zero_is_not_missing(tmp_path):
    source = tmp_path / "zero.cif"
    source.write_text(CIF.replace("L 42 A ?", "L 42 A 0"))
    staged = tmp_path / "input.cif"
    mapping = runtime.stage_structure(source, staged, "cif")
    record = runtime.residue_records(staged.read_text(), "cif", identities=mapping)[0]
    assert record["resnum"] == 0
    assert "identity_namespace" not in record


def test_staging_refuses_identity_collision(tmp_path):
    source = tmp_path / "collision.cif"
    source.write_text(CIF + "ATOM 2 C CA ALA L 42 L 42 4 5 6\n")
    with pytest.raises(ArtifactError, match="ambiguous"):
        runtime.stage_structure(source, tmp_path / "input.cif", "cif")


def test_stripping_uses_fallback_chain(tmp_path):
    source = tmp_path / "original.cif"
    source.write_text(CIF)
    target = tmp_path / "stripped.cif"
    result = pocket._strip_chains(source, {"L"}, target)
    assert result["removed_atom_count"] == 1


def test_failed_calculation_preserves_partial_output(tmp_path):
    with pytest.raises(ArtifactError):
        with runtime.publication(tmp_path, "sample") as stage:
            with runtime.calculation_workspace(stage) as work:
                (work / "partial-output").write_text("evidence")
                raise ArtifactError("failure", detail="diagnostics")
    failed = next(tmp_path.glob(".sample.failed-*"))
    assert (failed / "calculation/partial-output").read_text() == "evidence"
    assert json.loads((failed / "failure.json").read_text())["detail"] == "diagnostics"
