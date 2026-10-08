# Repaired local fpocket candidate

This directory contains the repair recipe for fpocket 4.2.2 and the pinned molfile
source at `5f817f263b89e8420174bb4bf0d0875a6ebe6136`. The parent directory's original
release remains revoked. A build is **not** a release; enablement requires the new
acceptance receipt and final environment/agent checks.

Current enablement, reviewed fixes, test results and exact rollback path are in
the [2026-10-07 review-repair handover](review-fixes-20261007/REPORT.md). Earlier
reports in this directory describe historical releases and are retained unchanged.

## Changes and boundaries

- `reader_validation.h` validates a bounded snapshot of the input and supplies the
  legacy reader with a private normalized stream. This avoids a validation/use
  race, handles quoted CIF tokens and topology comments, and rejects incomplete
  records before the legacy conversion callbacks. Calculations and Qhull are
  unchanged. `patches/` adds destination capacities, full supported chain names,
  cleanup on failure, bounded AMBER reads, and direct filesystem operations.
- `make_patches.py` regenerates unified diffs against untouched pinned sources;
  `apply_patch.py` requires exact context, without fuzzy matching. `build.sh`
  checksum-verifies both archives and applies the diffs in a fresh directory.
- DDE changes live in `tools/dde/commands/pocket.py` and
  `tools/dde/core/pocket_runtime.py`: finite input validation, controlled temporary
  filenames, 120-second process-group timeout, bounded diagnostics, residue
  identity preservation, complete output checks, and new-destination publication.
- A same-name rerun now requires `--out`. No overwrite option is introduced.
  Cooperating writers lock the destination; the sidecar is published last.
  Interrupted bundles lack a valid completion sidecar and cannot be analyzed.
  New sidecars hash the complete fpocket output tree as well as the JSON record.
  Legacy records retain their existing read behaviour; no learning files are
  rewritten or retroactively recertified.

Supported reader limits are explicit: 128 MiB input, one million atoms, at most
31 atom-site columns, normalized atom rows shorter than 4095 bytes, chain names
up to 15 bytes, atom names up to 4 bytes, residue names up to 7 bytes, and one-byte
insertion/alternate-location codes. Coordinates must be finite and within
`+/-1e15` angstroms to avoid overflow in elementary float coordinate arithmetic;
output validation still rejects any non-finite calculated descriptor. Fields that
cannot fit the existing ABI/downstream structures are rejected, never truncated.
The CIF reader supports the atom-site structure path, not the experimental IHM
or VMD graphics paths. Quoted metadata can contain whitespace; atom fields that
cannot be represented by the legacy writer are rejected. AMBER supports the
existing reader's TITLE/POINTERS ordering and fixed-width A/I/E formats. It does
not add compressed topology or molecular-dynamics support.

The original `1UYD_wrote.cif` contains atom names in its element-symbol column
(e.g. OE1, CG1). Its bytes are preserved; rejection is independently checked and
reported as an expected malformed-fixture result. The other bundled CIFs must
agree with Gemmi's decoded atom records.

## Evidence and reproduction

All downloaded sources, candidate binaries, project outputs, and large logs stay
outside tracked source. In the existing offline candidate container:

```sh
PACKAGE=/host-repo/applications/drug-design-engine/local-platform/fpocket-arm64
INPUTS=/host-repo/.dde-local/fpocket-validation
WORK=/scion-volumes/fpocket-validation/new-qualification
mkdir "$WORK"
python3 "$PACKAGE/repair/tests/prepare.py" "$INPUTS/fpocket-4.2.2" "$WORK/fixtures"
python3 "$PACKAGE/repair/tests/column_boundaries.py" "$WORK/fixtures" "$WORK/columns"
bash "$PACKAGE/repair/build.sh" arm "$INPUTS" "$WORK/new-build"
python3 "$PACKAGE/repair/tests/qualify.py" "$WORK/new-build" "$WORK/new-acceptance" \
  "$WORK/fixtures" "$WORK/columns"
python3 "$PACKAGE/repair/tests/mutations.py" "$WORK/new-build/probe-sanitized" \
  "$WORK/fixtures" "$WORK/new-mutations"
```

Fixture preparation for a fresh workspace:

```sh
python3 "$PACKAGE/repair/tests/prepare.py" "$INPUTS/fpocket-4.2.2" "$INPUTS/repair-fixtures"
python3 "$PACKAGE/repair/tests/column_boundaries.py" "$INPUTS/repair-fixtures" "$INPUTS/repair-columns"
```

Use new paths for every run. `qualify.py` records the binary, implementation,
fixtures, test code and result hashes before/after execution. `accept_build.sh` retains the original exact
scientific comparisons, exceptions for upstream volume fields, 30/120-second
limits, and repeated time seeds. `mutations.py` uses seeds 420218 and 420219 for
10,000 cases per reader; every case has a recorded input hash and every failure
retains input bytes and diagnostics. It tests safety, not an assumption that all
random mutations are invalid. Semantic acceptance/rejection is checked by the
separate frozen fixture corpus.

This block qualifies one build; it does not enable a release. Release assembly
also requires a second clean build, the Intel comparisons, complete DDE and
workflow reports, mutation results, and harness self-tests. The release gate
requires exact case inventories and rejects missing, failed, skipped or changed
evidence with explicit errors, including under optimized Python.

The reviewed regressions add mandatory completion-marker checks for renamed
records, explicit author/label fallback with source missingness preserved,
insertion-aware selectors with ambiguity errors, complete AMBER residue
assignment after section reordering, and retained timeout/partial-output
diagnostics. Chain classification shares one parsed input snapshot. Fixture
generation has one maintained implementation in `tests/fixture_base.py`.

The full DDE runner uses a fresh pytest process per module because some upstream
tests install global dependency stubs. No missing dependency is treated as a
successful skip. Test-only dependencies remain outside the working DDE environment.

## Finding ledger

| Finding | Repair and required evidence |
|---|---|
| Long author-chain heap overflow | Real destination sizes, bounded input fields; 1/14/15/16/64/1024-byte tests and sanitized probes |
| ABI18 label-chain truncation | Preserve the available 16-byte field; collision and full-workflow 15-character identity tests |
| Invalid/missing/non-finite coordinates | Strict reader and DDE checks; real CLI rejection without successful artifacts |
| AMBER hangs, truncated records, bad indices | EOF and count validation, unique sections, residue/bond bounds; invalid inputs terminate with errors |
| Filenames and advertised aliases | Controlled staged names, content-aware format choice, direct mkdir/chmod; real filename matrix |
| CIF quotes and malformed writer fixture | Lexical decoding, Gemmi comparisons, explicit malformed-fixture rejection |
| Additional mutation-discovered header overflow | Bounded header length and scanf widths; original failing inputs retained; identical mutation corpus rerun |
| Additional interleaved-column array overflow | Enforce actual 32-slot legacy boundary before parsing; retained UBSan reproduction and boundary cases |
| Insertion-code and publication defects | Distinct residue identities, lock, completion marker, output hashes; concurrency, corruption, and interrupted-publication tests |
| New output-check PQR parsing defect | Fixed-width coordinates rather than whitespace splitting; adjacent-negative-coordinate regression and real 3VI4 integration |
| 2026-10-08 review: screening runner crash, `repr` residue order, lock scoping | Click 8.5 runner reading `outputs.*` with `--out` forwarded; numeric residue order; lock taken outside the retained-failure block | Fake-CLI runner test, numeric-order and body-`BlockingIOError` unit cases; release v3 re-qualification |

## Baseline test corrections

The eight original DDE failures were retained before edits. The installer test
now requires `--require-hashes`. Normalization assertions check canonical keys and
preservation of invalid values for downstream validation, and separately verify
that the caller's input is unchanged. PubChem assertions retain CID in custom
slugs to prevent collisions. Click tests use the installed constructor API and
exercise a command callback (`pocket --help`), because eager `--version` exits
before the dirty-source warning. The preflight test checks the complete reported
verdict, including its genuine rejection of the original x86 installer on ARM;
it no longer mistakes Python.h plus gcc for all prerequisites. No installer
platform guard was weakened.

## Rollback

Before working-volume promotion, archive its current source files, environment
metadata, installer, and hashes into a new rollback directory. If final doctor,
agent integration, or live stamp verification fails, remove the newly installed
fpocket from the working bin directory, restore those archived files and the
fpocket-excluding installer, and verify the prior stamp. Preserve the failed new
release and diagnostic project. Never restore the earlier revoked executable.

Ordinary failed publications remain in `.NAME.failed-*` with `failure.json`.
A process killed during publication can leave `.NAME.pending-*` and incomplete
new output paths. Preserve those together for diagnosis and use a fresh `--out`;
do not remove any existing completed bundle to make a rerun fit.

## Instrumentation boundary

Both architectures compile instrumented readers. Native ARM ASan/UBSan executes
all required boundary, mutation, fixture and lifecycle checks. An additional
attempt to execute Intel ASan under QEMU fails inside sanitizer allocator
initialization (`sanitizer_allocator_primary32.h:292`) before reader execution.
A bounded reserved-address-space diagnostic also failed at emulator startup.
Those runs are retained as unavailable instrumentation, not reader passes. Intel
reader correctness and scientific comparisons use the normal executable; the
production ARM code receives native instrumentation. The runner now recognizes
sanitizer initialization failures and unexpected exit codes explicitly.
