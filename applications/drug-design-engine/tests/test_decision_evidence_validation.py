# Copyright 2026 Kesis & Sisters Technologies Inc.
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

"""Synthetic regressions for source references and per-finding relay coverage."""

import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from dde.commands.validate import (
    _check_analysis_citations,
    _check_relay_coverage,
    _check_threshold_reference,
)
from dde.core.thresholds import declared_sets


def write(root, path, content):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content if isinstance(content, str) else json.dumps(content))
    return target


@pytest.fixture
def project(tmp_path):
    write(tmp_path, "raw/literature/source.txt", "Synthetic bounded evidence.")
    write(
        tmp_path,
        "raw/literature/sample.analysis.json",
        {
            "source": "raw/literature/source.txt",
            "threshold_set": "pubmed-search",
            "mandatory_relays": [{"code": "pubmed.search_not_exhaustive"}],
        },
    )
    return tmp_path, {
        "layer_0_classes": ["literature"],
        "layer_1": ["findings/decision.md"],
    }


@pytest.mark.parametrize("field", ["source", "threshold_set"])
@pytest.mark.parametrize("value", [None, "", "  ", [], {}, 0, False])
def test_empty_or_mistyped_references_fail(project, field, value):
    root, deliverables = project
    path = root / "raw/literature/sample.analysis.json"
    record = json.loads(path.read_text())
    record[field] = value
    path.write_text(json.dumps(record))
    result = _check_analysis_citations(root, deliverables)
    assert result["status"] == "fail"
    assert any(field in item["issue"] for item in result["detail"]["issues"])


@pytest.mark.parametrize(
    "source", ["raw/literature/missing.txt", "../outside.txt", "raw/literature"]
)
def test_source_must_resolve_to_confined_file(project, source):
    root, deliverables = project
    record = root / "raw/literature/sample.analysis.json"
    data = json.loads(record.read_text())
    data["source"] = source
    record.write_text(json.dumps(data))
    assert _check_analysis_citations(root, deliverables)["result"] == "fail"


def test_fabricated_threshold_name_fails(project):
    root, deliverables = project
    record = root / "raw/literature/sample.analysis.json"
    data = json.loads(record.read_text())
    data["threshold_set"] = "invented-cutoff@1.0"
    record.write_text(json.dumps(data))
    assert _check_analysis_citations(root, deliverables)["result"] == "fail"


def test_current_program_and_composite_threshold_tags_remain_valid():
    tags = [item.tag for item in declared_sets().values()]
    for tag in [
        *tags,
        *(tag + "+program" for tag in tags),
        "+".join(tags[:2]),
        "+program+".join(tags[:2]),
    ]:
        assert _check_threshold_reference(tag) == ([], [])


def test_historical_threshold_version_is_explicitly_unverified(project):
    root, deliverables = project
    name = next(iter(declared_sets()))
    record = root / "raw/literature/sample.analysis.json"
    data = json.loads(record.read_text())
    data["threshold_set"] = name + "@0.0"
    record.write_text(json.dumps(data))
    result = _check_analysis_citations(root, deliverables)
    assert result["status"] == "warn"
    assert "recorded runtime" in result["detail"]["warnings"][0]["issue"]


def test_existing_descriptive_analysis_identifier_passes(project):
    root, deliverables = project
    assert _check_analysis_citations(root, deliverables)["status"] == "ok"


def test_existing_literal_producer_identifiers_remain_valid():
    commands = Path(__file__).resolve().parents[1] / "tools/dde/commands"
    checked = []
    for path in commands.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if (
                isinstance(node, ast.keyword)
                and node.arg == "threshold_set"
                and isinstance(node.value, ast.Constant)
            ):
                assert _check_threshold_reference(node.value.value) == ([], []), (
                    path.name
                )
                checked.append(path.name)
    assert checked, "The compatibility check must inspect actual producer identifiers"


def test_other_work_order_is_not_invalidated(project):
    root, deliverables = project
    write(
        root,
        "raw/literature/other.analysis.json",
        {
            "work_order_id": "WO-002",
            "source": None,
            "threshold_set": None,
            "mandatory_relays": [{"code": "unrelated.code"}],
        },
    )
    assert _check_analysis_citations(root, deliverables, "WO-001")["status"] == "ok"
    write(root, "findings/decision.md", "**Relay: `pubmed.search_not_exhaustive`**")
    assert _check_relay_coverage(root, deliverables, "WO-001")["status"] == "ok"


def test_relay_in_unrelated_finding_cannot_cover_decision(project):
    root, deliverables = project
    write(
        root,
        "findings/decision.md",
        "[Evidence](../raw/literature/sample.analysis.json)\nNo publications exist.",
    )
    write(
        root,
        "findings/other.md",
        "**Relay: `pubmed.search_not_exhaustive`** Search is incomplete.",
    )
    deliverables["layer_1"].append("findings/other.md")
    result = _check_relay_coverage(root, deliverables)
    assert result["result"] == "fail"
    assert result["detail"]["missing_by_finding"] == [
        {
            "file": "findings/decision.md",
            "codes": ["pubmed.search_not_exhaustive"],
        }
    ]


@pytest.mark.parametrize(
    "citation",
    [
        "[Evidence](../raw/literature/sample.analysis.json)",
        "[Evidence](raw/literature/sample.analysis.json)",
        "{source: raw/literature/source.txt:1}",
        "{source-table: raw/literature/sample.analysis.json $.metrics}",
        "[raw/literature/source.txt]",
        "No source link supplied.",
    ],
)
def test_each_citation_form_requires_its_own_relay(project, citation):
    root, deliverables = project
    path = write(root, "findings/decision.md", citation)
    assert _check_relay_coverage(root, deliverables)["result"] == "fail"
    path.write_text(
        citation + "\n**Relay: `pubmed.search_not_exhaustive`** Search is incomplete."
    )
    assert _check_relay_coverage(root, deliverables)["status"] == "ok"


def test_independent_sources_do_not_require_each_others_relays(project):
    root, deliverables = project
    write(root, "raw/literature/other.txt", "Other synthetic evidence.")
    write(
        root,
        "raw/literature/other.meta.json",
        {
            "outputs": [{"path": "other.txt"}],
            "mandatory_relays": [{"code": "litref.resolved_not_verified"}],
        },
    )
    write(
        root,
        "findings/decision.md",
        "[Source](../raw/literature/source.txt)\n**Relay: `pubmed.search_not_exhaustive`**",
    )
    write(
        root,
        "findings/other.md",
        "[Source](../raw/literature/other.txt)\n**Relay: `litref.resolved_not_verified`**",
    )
    deliverables["layer_1"].append("findings/other.md")
    assert _check_relay_coverage(root, deliverables)["status"] == "ok"


def test_source_chain_preserves_sidecar_relays(project):
    root, deliverables = project
    write(
        root,
        "raw/literature/sample.meta.json",
        {
            "outputs": [{"path": "source.txt"}],
            "mandatory_relays": [{"code": "litref.resolved_not_verified"}],
        },
    )
    write(
        root,
        "raw/literature/sample.analysis.json",
        {
            "source": "raw/literature/sample.meta.json",
            "threshold_set": "pubmed-search",
        },
    )
    path = write(
        root,
        "findings/decision.md",
        "[Analysis](../raw/literature/sample.analysis.json)",
    )
    assert _check_relay_coverage(root, deliverables)["result"] == "fail"
    path.write_text(path.read_text() + "\n**Relay: `litref.resolved_not_verified`**")
    assert _check_relay_coverage(root, deliverables)["result"] == "pass"


def test_similar_code_is_not_the_required_code(project):
    root, deliverables = project
    write(
        root, "findings/decision.md", "**Relay: `pubmed.search_not_exhaustive_extra`**"
    )
    assert _check_relay_coverage(root, deliverables)["result"] == "fail"


def test_labels_do_not_certify_scientific_meaning(project):
    root, deliverables = project
    write(
        root,
        "findings/decision.md",
        "No relevant publications exist.\n\n**Relay: `pubmed.search_not_exhaustive`** Search is incomplete.",
    )
    # Deliberately still passes mechanically: the independent reviewer must
    # reject the unsupported claim. Do not advertise a semantic detector.
    assert _check_relay_coverage(root, deliverables)["status"] == "ok"


def test_literature_only_work_order_stays_skipped(tmp_path):
    deliverables = {"layer_0_classes": [], "layer_1": []}
    assert _check_relay_coverage(tmp_path, deliverables)["result"] == "skip"
    assert _check_analysis_citations(tmp_path, deliverables)["result"] == "skip"
