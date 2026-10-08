"""Assemble a new release only from complete, build-bound acceptance evidence."""

import json
import math
import shutil
import sys
from pathlib import Path
from release_checks import (
    checked_report,
    digest,
    implementation_files,
    require,
    validate_dde,
    validate_rows,
    verify_binding,
)


def validate_original_reference(oracle, inventory):
    require(
        isinstance(oracle, dict) and oracle.get("passed") is True,
        "original Intel reference is not qualified",
    )
    scientific = set(inventory["intel-science"]["expected"]) | {"architecture-static"}
    readers = set(inventory["sanitizers"]["expected"])
    validate_rows(oracle.get("scientific_checks"), scientific, "name")
    validate_rows(oracle.get("reader_checks"), readers, "name")


def assemble(base, intel, original, output):
    package = Path(__file__).resolve().parent
    inventory = json.loads((package / "acceptance-inventory.json").read_text())
    reports = {}

    def check(path, contract):
        spec = inventory[contract]
        rows = checked_report(path, set(spec["expected"]), spec["identity"])
        reports[str(path)] = {"sha256": digest(path), "checks": len(rows)}
        return rows

    def bind(folder):
        paths = json.loads((folder / "binding-paths.json").read_text())
        verify_binding(
            folder / "binding.json",
            {
                k: Path(v) if Path(v).is_absolute() else folder / v
                for k, v in paths.items()
            },
        )
        reports[str(folder / "binding.json")] = {
            "sha256": digest(folder / "binding.json")
        }
        return json.loads((folder / "binding.json").read_text())

    case_names = {
        c["name"] for c in json.loads((base / "fixtures/cases.json").read_text())
    }
    column_names = {
        c["name"] for c in json.loads((base / "columns/cases.json").read_text())
    }
    for name in ("a", "b"):
        folder = base / f"accept-{name}"
        binding = bind(folder)
        require(
            binding["binary"]
            == digest(base / f"build-{name}/fpocket-4.2.2/bin/fpocket"),
            "wrong tested binary",
        )
        for key, path in implementation_files(package).items():
            require(
                binding[key] == digest(path), "implementation differs from tested build"
            )
        check(folder / "science/report.json", "science")
        for kind, expected in [("boundaries", case_names), ("columns", column_names)]:
            path = folder / kind / "report.json"
            rows = checked_report(path, expected)
            reports[str(path)] = {"sha256": digest(path), "checks": len(rows)}
        for part in ("all-cif", "additional", "sanitizers"):
            check(folder / part / "report.json", part)
        for name in ("repeat-cif.log", "repeat-parm7.log"):
            text = (folder / name).read_text()
            require(
                text.count("PROBE_JSON ") == 100
                and "AddressSanitizer:" not in text
                and "runtime error:" not in text,
                "reader lifecycle check incomplete or failed",
            )
    for part in ("science", "boundaries", "columns"):
        path = intel / part / "report.json"
        if part == "science":
            check(path, "intel-science")
        else:
            rows = checked_report(
                path, case_names if part == "boundaries" else column_names
            )
            reports[str(path)] = {"sha256": digest(path), "checks": len(rows)}
    bind(intel)
    mutation_binding = bind(base / "mutations")
    require(
        mutation_binding["sanitized-probe"] == digest(base / "build-b/probe-sanitized"),
        "mutations tested another build",
    )
    mutation = json.loads((base / "mutations/report.json").read_text())
    rows = mutation.get("results")
    require(isinstance(rows, list) and len(rows) == 2, "missing mutation results")
    require(
        {(r["reader"], r["seed"]) for r in rows}
        == {("pdbx", 420218), ("parm7", 420219)},
        "wrong mutation corpus",
    )
    require(
        all(r["cases"] == 10000 and r["failures"] == [] for r in rows),
        "mutation failure or incomplete corpus",
    )
    reports["mutations"] = {
        "sha256": digest(base / "mutations/report.json"),
        "cases": 20000,
    }
    dde_binding = bind(base / "dde-tests")
    for key, path in implementation_files(package).items():
        require(
            dde_binding[key] == digest(path),
            "DDE evidence belongs to another implementation",
        )
    dde = json.loads((base / "dde-tests/report.json").read_text())
    modules = {p.name for p in (package.parents[2] / "tools/tests").glob("test_*.py")}
    total = validate_dde(dde, modules)
    reports["dde"] = {"sha256": digest(base / "dde-tests/report.json"), "tests": total}
    for label, count in [
        ("runner", 4),
        ("comparator", 11),
        ("release", 6),
        ("original-reference", 6),
        ("deployment-copy", 2),
    ]:
        path = base / f"{label}-tests.log"
        text = path.read_text()
        require(
            f"Ran {count} tests" in text and "\nOK" in text,
            "test harness self-check failed: " + label,
        )
        reports[label] = {"sha256": digest(path), "tests": count}
    check(base / "scion.json", "scion")
    check(base / "workflow/report.json", "workflow")
    check(base / "smokes/report.json", "smokes")
    identity = json.loads((base / "identity/report.json").read_text())
    for key in (
        "passed",
        "missing_marker_rejected",
        "corruption_rejected",
        "same_destination_single_winner",
        "all_protein_removed_rejected",
    ):
        require(identity.get(key) is True, "identity integration failed: " + key)
    require(identity.get("pockets") == 13, "identity integration incomplete")
    # New regressions must be exercised with the actual calculation and analysis.
    check(base / "review-workflow/report.json", "review-workflow")
    oracle = json.loads((original / "report.json").read_text())
    validate_original_reference(oracle, inventory)
    reports["original-intel"] = {
        "sha256": digest(original / "report.json"),
        "scientific_checks": len(oracle["scientific_checks"]),
        "reader_checks": len(oracle["reader_checks"]),
    }
    volumes = {}
    for name, path in [
        ("original_intel", original / "volumes.json"),
        ("patched_intel", intel / "science/volumes.json"),
        ("arm_a", base / "accept-a/science/volumes.json"),
        ("arm_b", base / "accept-b/science/volumes.json"),
    ]:
        value = json.loads(path.read_text())
        require(
            len(value["samples"]) == 10
            and len(set(value["times"])) == 10
            and len(value["medians"]) == 13,
            "incomplete volume repetitions",
        )
        require(
            all(
                len(row) == 13
                and all(
                    isinstance(x, (int, float)) and math.isfinite(x) and x > 0
                    for x in row
                )
                for row in value["samples"]
            ),
            "invalid volume samples",
        )
        require(
            all(math.isfinite(x) and x > 0 for x in value["medians"]),
            "invalid volume medians",
        )
        volumes[name] = {
            "medians": value["medians"],
            "ranges": [[min(x), max(x)] for x in zip(*value["samples"])],
        }
    for name in ("patched_intel", "arm_a", "arm_b"):
        delta = [
            abs(a - b) / b
            for a, b in zip(
                volumes[name]["medians"], volumes["original_intel"]["medians"]
            )
        ]
        require(max(delta) <= 0.05, "median volume difference exceeds 5%")
        volumes[name]["maximum_relative_median_difference"] = max(delta)
    library = base / "build-b/library/libmolfile_plugin.a"
    require(
        digest(library) == digest(base / "build-a/library/libmolfile_plugin.a"),
        "clean library builds differ",
    )
    require(
        digest(base / "runtime-a") == digest(base / "runtime-b"),
        "clean runtime builds differ",
    )
    binary = base / "build-b/fpocket-4.2.2/bin/fpocket"
    output.mkdir(exist_ok=False)
    shutil.copyfile(binary, output / "fpocket")
    source = package.parents[2] / "tools/dde"
    source_files = {}
    for name in ("commands/pocket.py", "core/pocket_runtime.py"):
        target = output / "dde" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
        source_files[name] = digest(target)
    receipt = {
        "pre_enablement_passed": True,
        "fpocket_version": "4.2.2",
        "candidate_abi": 18,
        "architecture": "AArch64",
        "binary_sha256": digest(binary),
        "library_sha256": digest(library),
        "compiler": (base / "build-b/compiler.txt").read_text(),
        "flags": (base / "build-b/fpocket-cflags.txt").read_text(),
        "molfile_commit": "5f817f263b89e8420174bb4bf0d0875a6ebe6136",
        "source_archive_hashes": json.loads(
            (package / "reports/acceptance.json").read_text()
        )["source_archive_hashes"],
        "patches": {p.name: digest(p) for p in (package / "patches").glob("*.patch")},
        "reader_validation_sha256": digest(package / "reader_validation.h"),
        "dde_source_files": source_files,
        "qualification_code_sha256": {
            p.name: digest(p)
            for p in (
                package / "assemble_release.py",
                package / "release_checks.py",
                package / "acceptance-inventory.json",
                package / "promote.py",
                package / "rollback.py",
                package / "provision.sh",
                package / "prepare_installer.py",
                package / "tests/test_original_reference.py",
                package / "tests/test_deployment_copy.py",
            )
        },
        "reports": reports,
        "volume_variability": volumes,
        "volume_tolerance": 0.05,
        "additional_intel_sanitizer_status": "unavailable under QEMU; native ARM ASan/UBSan required and passed",
        "working_environment_enablement": "pending",
    }
    (output / "acceptance.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps(
            {
                "passed": True,
                "binary_sha256": receipt["binary_sha256"],
                "dde_tests": total,
            }
        )
    )


if __name__ == "__main__":
    assemble(*map(Path, sys.argv[1:]))
