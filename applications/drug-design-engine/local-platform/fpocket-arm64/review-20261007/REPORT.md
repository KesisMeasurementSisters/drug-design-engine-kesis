# Review of the fpocket repair: changes required

Date: 2026-10-07. Reviewed local changes over upstream
`45f7f26b10592183956cbb35d11b02c0651e6d24`, branch `kesis/learning-sandbox`.
This is a new review record; previous reports, manifests, and source remain untouched.

**Verdict:** six reproducible correctness/verification gaps remain. The previous
710 passing tests and 20,000 mutation results remain historical observations,
but do not establish the full repair contract: these cases were not covered.
Correct these findings before relying on the workflow for further learning work.
This review made no installed-code, binary, authentication, or model changes.

## Findings

### R1 — P1: renamed records bypass the new completion check

Location: [pocket.py:781](applications/drug-design-engine/tools/dde/commands/pocket.py:781), and conditional validation at line 792.

When a new-format record is named `orphan.json`, replacing `.pockets.json` in its
name changes nothing. `commit_marker` therefore points to the record itself.
The second sidecar path is absent, so its conditional block skips both record
and tree integrity checks. In the disposable project, an unchanged
`publication_version: 1` record with neither its sidecar nor output tree was
accepted by `dde pocket analyze` (exit 0; 13 pockets).

This is introduced by the new publication check. Derive the marker once, require
it unconditionally for new-format records, and reject unsupported filenames or
resolve them through an explicit manifest. Test copied/renamed records, absent
markers, and renamed complete bundles according to the intended contract.
Evidence: `analysis-report.json`, `orphan`.

### R2 — P1: accepted missing mmCIF identifiers become invented zeroes

Location: [reader_validation.h:91](applications/drug-design-engine/local-platform/fpocket-arm64/repair/reader_validation.h:91).

The new validator admits missing sequence identifiers, but the legacy conversion
still uses `atoi` on them. DDE understands author-to-label fallback before the
calculation, while the native reader/writer emits numeric zero and DDE then treats
that zero as an actual author identifier.

Reproduction: in bundled 1UYD, set author sequence IDs to `?` only where valid
label sequence IDs exist, leaving other rows unchanged. `dde pocket run` succeeds
with 13 pockets; every reported primary residue number is 0. The input contains
valid protein label numbers 16–224. A direct reader probe also accepts missing
label sequence IDs and reports `resid: 0`.

This is an incomplete repair of upstream conversion behaviour, exposed through
the new accepted-input boundary. Define identity and missingness through the
whole native/Python path. Use valid fallback explicitly, retain its namespace,
and reject values that ABI18 cannot faithfully represent. Never publish an
invented zero. Test missing author IDs, missing label IDs, actual zero, and mixed
missingness end to end. Evidence: `dde-report.json`, `missing-author-identifiers`,
and `report.json`, `cif-label_seq_id`.

### R3 — P2: analysis discards the identities the new parser preserves

Location: [pocket.py:821](applications/drug-design-engine/tools/dde/commands/pocket.py:821); selector parsing at line 719.

New records preserve insertion and label identities, but `analyze --near` still
matches only `(chain, resnum)`. `A:145A` is rejected by the selector, while a query
for `A:145` matches both insertion variants A and B, reports both as `A:145`, and
selects the higher-scoring pocket without identifying the ambiguity. The synthetic
reproduction returns site-druggable at 0.9 despite the distinct B site scoring 0.1.

This unchanged upstream analysis path was missed when adding richer identities.
Extend selector/matching/serialization together, or explicitly reject ambiguous
queries. Keep existing unambiguous selectors compatible. Repeat the test with a
properly named complete bundle after fixing R1; this reproduction isolates the
matching behaviour with a renamed synthetic record.
Evidence: `analysis-report.json`, `identities`, and `dde-report.json`,
`selector-insertion-code`.

### R4 — P2: AMBER can report success without assigning residues

Location: [reader_validation.h:135](applications/drug-design-engine/local-platform/fpocket-arm64/repair/reader_validation.h:135), together
with the preserved `RESIDUE_POINTER` branch of `read_parm7_structure`.

Swap the complete RESIDUE_POINTER and RESIDUE_LABEL sections of the independently
defined water fixture. The new validator accepts their presence/counts, then the
legacy reader prints that it cannot parse pointers before labels, continues, and
returns success. All three atoms have empty residue names and residue number 0.
The native sanitized probe exits 0; no sanitizer error is needed to expose this
semantic failure.

This is an incomplete upstream-reader repair. Normalize section order or reject
unsupported ordering, and require successful assignment of every mandatory field
before returning success. Current AMBER boundary assertions only check atom names,
atom count, and bonds; extend them to independently specified residue identities
and available optional fields. Evidence: `report.json`, `amber-reordered-residues`.

### R5 — P1: release evidence validation is not fail-closed

Location: [assemble_release.py:7](applications/drug-design-engine/local-platform/fpocket-arm64/repair/assemble_release.py:7), plus DDE
aggregation at line 26.

The new `report()` helper accepts `[]`, `{}`, and an object with an unrecognized
checks key. The DDE aggregation also accepts an empty module list through
`all([])`. Isolating and executing the exact unchanged helper confirmed all three
malformed/empty reports are accepted. Many safety gates additionally use Python
`assert`, which disappears under optimized Python execution.

Require explicit report schemas, exact expected case/module identities and
nonzero counts, completed status, and explicit exceptions for failed gates.
Bind each report to the tested binary and fixture inventory. Add negative tests
for empty, partial, wrong-schema, wrong-build, and skipped reports and optimized
interpreter execution. This finding concerns the gate's behaviour; it does not
mean the saved 710-test report was empty. Evidence: `report.json`, `release-*`.

### R6 — P2: timeout diagnostics are discarded

Location: [pocket_runtime.py:101](applications/drug-design-engine/tools/dde/core/pocket_runtime.py:101).

A process prints `DIAGNOSTIC_BEFORE_HANG` to stderr and then sleeps. The wrapper
kills it, but raises before reading either bounded diagnostic tail. Both temporary
log files close and disappear; the exception retains only the timeout value.
The outer publication failure record cannot recover those diagnostics, and the
calculation temporary directory is also removed on failure.

This is introduced by the new bounded runner. Preserve bounded stdout/stderr tails
and failure context before raising; retain necessary failed input/output evidence
inside the failed bundle. Test timeout after emitted diagnostics and partial
output. Evidence: `dde-report.json`, `timeout-diagnostics`.

## Redundancy and maintainability

- Runtime size is modest: upstream `pocket.py` was 1,202 lines; current `pocket.py`
  (1,047) plus `pocket_runtime.py` (166) totals 1,213, a net increase of 11 lines.
  Consolidating repeated CIF parsing into one helper was useful.
- The two chain-detection helpers nevertheless decode the entire input independently
  back-to-back. Parse a single validated snapshot and share its residue records;
  retain deliberate revalidation after chain stripping.
- `repair/tests/readers.py` carries a second 51-line fixture-preparation function,
  while the active `prepare.py` imports the historical implementation. There are
  two fixture-generation entry points to keep consistent. Select one maintained
  implementation; preserve historical evidence unchanged.
- Remove the unconditional `if true` wrapper and overwritten initial archive
  assignment in `repair/build.sh`; the unused `sanitized` parameter in the reader
  runner; unused imports `subprocess`, `statistics`, and `os` in the reviewed files.
- The new C++ validator and several release scripts pack many independent operations
  into single lines. Expand them and split lexical parsing, semantic validation,
  and serialization into named functions. Compact source is making correctness
  review harder, particularly at the validator/legacy-reader boundary.
- The local-platform package has 132 files and roughly 1 MiB allocated before this
  review. Much of this is frozen expectations and retained reports, not runtime
  bloat. Do not delete manifests, failed cases, or historical releases as cleanup.

## Review method and preserved evidence

Reviewed the runtime diff, C++ validator and reader patches, release/provisioning
scripts, new tests, baseline test corrections, and maintained/historical helper
relationships. Ran targeted native ARM sanitized probes, real local DDE commands,
and direct execution of the unchanged release-report helper in an offline
candidate container. No full 710-test rerun was necessary because no product code
was changed; the added cases expose coverage gaps rather than regressions caused
by this review. This was a targeted code review, not exhaustive proof of safety.

Evidence and exact reproduction scripts are retained at:
`<repo>/.dde-local/fpocket-validation/review-20261007/`.
Raw result JSON files are in its `evidence/` subdirectory. The corresponding
persistent candidate-volume directory is
`/scion-volumes/fpocket-validation/repair/review-20261007`.
Earlier failed reproduction attempts are preserved; `analysis-report.json`
contains the corrected in-project analysis reproductions.

The installed release remains as it was at review start. Existing learning
artifacts were not used as output destinations. The temporary validation container
is stopped after evidence capture. All computation was local.
