# Review repairs and technical-debt reduction

Date: 2026-10-07. Upstream remains `45f7f26b10592183956cbb35d11b02c0651e6d24`
on `kesis/learning-sandbox`. This report supersedes the reviewed release's
enablement claim; it does not replace or rewrite its historical reports.

**Status: repaired native ARM64 pocket detection is enabled and verified.**
All six reviewed findings are repaired. The strict release gate and final working
environment/Scion checks passed. See [verification.json](verification.json) and
the immutable [release manifest](release-manifest.json).

## Repair ledger

| Review finding | Implemented repair | Regression evidence |
|---|---|---|
| R1: renamed results bypass integrity checks | New records require the canonical `.pockets.json` name, one mandatory completion sidecar, matching record hash, and complete matching output tree. | Renamed/missing/invalid marker unit cases and real analysis refusal. |
| R2: missing identifiers become zero | DDE stages explicit author-to-label fallback and maps native results back to the original identity and missingness. Genuine zero stays zero. Unrepresentable or colliding identities are rejected. Native handling supports a completely absent author-number column through explicit label fallback, while rejecting missing values that the legacy interface cannot represent. | Missing author/label, actual zero, collision, chain stripping, and real calculation/analysis cases. |
| R3: analysis merges distinct residues | Full residue keys include insertion and label identifiers. Explicit insertion selectors work; ambiguous unqualified selectors fail. | A:145A/A:145B unit cases and a complete, hash-valid bundle selecting B separately. |
| R4: reordered AMBER sections lose residues | The validated snapshot orders residue labels before pointers. The reader returns an error if mandatory residue assignment is unavailable. | Independently specified water topology checks names, residue names/numbers, masses, atomic numbers and bonds, including reordered sections. |
| R5: incomplete evidence passes release gate | Shared explicit checks require nonempty exact case/module inventories, complete successful outcomes and no skips/timeouts. Before/after bindings connect tests, fixtures, implementation, binaries and reports. | Empty, partial, duplicate, failed, skipped, wrong-schema and wrong-build negative tests, including optimized Python. |
| R6: failures discard diagnostics | Timeout exceptions retain bounded stdout/stderr tails. Failed calculations retain staged input and partial output beside `failure.json`. | Emitted diagnostic followed by timeout, plus failure after writing partial output. |

The regressions were first exercised against the reviewed implementation. Its
failing results, pre-change source snapshot and withdrawn binaries are retained
outside tracked source. No expected scientific output was replaced with candidate
output and the 5% median-volume tolerance is unchanged.

## Deduplication and size

- Chain classification shares a parsed structure snapshot. Deliberate validation
  after chain stripping remains.
- `tests/fixture_base.py` is the single maintained fixture generator. Removed the
  duplicate 51-line preparation function and unused runner parameter.
- Removed dead build assignments, the unconditional shell wrapper, and unused
  imports. Expanded dense validator/release code for reviewability.
- Shared report/hash checks across qualification and release assembly. Promotion
  and rollback use explicit snapshots, validate backups before touching live
  files, and retain failed candidate files.
- Replaced an intermediate C++ regex implementation with a small decimal-token
  checker: the reader archive is **170,276 bytes**, versus 684 KB for the
  intermediate implementation. No new runtime dependency was introduced.

Code length increased where identity handling and readable validation needed
explicit logic. Historical reports, failed cases, manifests and reference outputs
were retained deliberately; they are evidence, not deployed runtime code.

## Final-build acceptance

The two final clean ARM builds passed:

- 67 reader semantic/boundary cases and 6 column-limit cases per build.
- 45 scientific/reference/option checks per build, 20 bundled CIF outcomes,
  10 additional structures, and 5 instrumented fixture checks.
- 100 repeated open/read/close cycles per reader per build.
- A reproducible sanitizer corpus of 10,000 cases per reader, seeds 420218 and
  420219, with no invalid-memory/undefined-behaviour finding or timeout.
- All **724 DDE tests across 44 modules**, with no missing-dependency skips.
- Scion-user integration (7), workflow edge cases (21), full-identity integration,
  reviewed workflow regressions (6), and Vina/MUSCLE/compound/Hypex smoke checks (4).
- Runner/comparator/release-gate self-tests (4/11/6). Rollback tests separately
  confirmed successful restoration and refusal of a corrupt backup before mutation.

The repaired Intel build passed all 67 reader cases, 6 column cases and 39
scientific checks. The retained original Intel oracle's 40 scientific and 5
reader checks were also explicitly validated. Across ten distinct time seeds,
the largest pocket-volume median differences from that original oracle were
**1.47% (repaired Intel), 1.56% (ARM A), and 1.77% (ARM B)**, all below the
unchanged 5% limit. Per-pocket medians and ranges are in the release manifest.

Two further deployment defects were caught and repaired during the final checks:
the assembler initially expected a single check array in the historical Intel
report, and the new file-copy callback expected Path objects although `copytree`
supplies strings. The original reference report was not changed. Six additional
schema regressions and two copy-callback regressions now pass and are required by
the release gate. The first installation attempt automatically restored the
disabled snapshot; its partial package and diagnostics remain preserved.

The clean static reader archives are byte-identical. Executables match after
removing debug sections and build IDs; the resulting SHA-256 is
`f8ea17f9ad332dd4e42c35e761fda8ed38ff9706b87bfaf3bda1905c856bf9fe`.
The installed release retains the tested executable, including its debug data.

## Working environment and rollback

The existing Scion agent, still using Antigravity with Gemini 3.8 Flash High,
executed one bounded calculation and analysis in a new disposable project.
Both exited 0, finding 13 pockets; pocket 1 scored 0.664 with druggability 0.855.
The input hash was unchanged. Provenance matches the new binary, coupled DDE
source, ARM interpreter and environment stamp.

`dde doctor` returned `ok: true`; live/stored environment stamps match. Its
development-source, historical-environment and unavailable optional-service
warnings remain visible. No old artifact was re-stamped. All 28 existing learning
files and six other tool binaries retain their prior hashes. Vina, MUSCLE,
compound-property and Hypex smoke checks also passed in the installed environment.

- Binary SHA-256: `d6a779e6e4932805fa775200f17d23e8dbbfe63dc145848b3570b6fc7c156cb0`.
- Environment: `sha256:1e9d67baf4c5b750d099d55666a896512bc61abd04d52057aa48eb216e08a20b`.
- Installed release: `/scion-volumes/fpocket-arm64/repair-reviewed-20261007/release`.
- Disabled-state backup: `/scion-volumes/fpocket-review-fixes-rollback-20261007-v2`.

If rollback is needed, first leave the agent idle, then run in `dde-tools-arm64`:

```sh
python3 /scion-volumes/fpocket-arm64/repair-reviewed-20261007/rollback.py \
  /scion-volumes/fpocket-review-fixes-rollback-20261007-v2
```

This verifies backup checksums, retains the withdrawn current files, restores the
fpocket-disabled source/installer/metadata, and removes only the newly introduced
binary/runtime files recorded as previously absent. Confirm fpocket is absent and
the stamp is `sha256:67718829910277cc16be681e50142f22e12efc186ba8fd031b79faf9b19eee6b`.
Never reinstall either earlier revoked release. The immutable acceptance manifest
records pre-enablement qualification; `verification.json` records completed live
enablement separately.

Intel sanitizer execution remains unavailable under local QEMU because its
allocator fails before reader execution. This is not counted as a passing or
skipped parser test. Production ARM safety checks execute ASan/UBSan natively.
Leak-enabled fixture/lifecycle runs passed; the mutation corpus does not measure
leaks. Intel correctness/scientific checks use the normal executable.

## Reproduction and retained evidence

See [the maintained recipe](../README.md#evidence-and-reproduction). The exact
final candidate root is
`/scion-volumes/fpocket-validation/review-fixes-final-20261007` in the isolated
candidate tools volume. It contains both builds, frozen fixture inventories,
per-case logs, output trees and hash bindings. Each rerun requires fresh paths.

Host evidence lives under `.dde-local/fpocket-validation/`. The pre-change archive
is `pre-review-fixes-20261007.tar.gz`; failed/intermediate attempts are under
`review-fixes-20261007/`. Final ARM evidence is archived separately from downloaded
source/build trees. The review's original reproductions remain under
`review-20261007/`.

Final host evidence: `review-fixes-final-arm-evidence-v2.tar.gz`,
`review-fixes-final-intel/`, `review-fixes-final-working/`,
`review-fixes-final-agent/`, and `review-fixes-final-release-v2/`.
Archive and manifest checksums are recorded in `verification.json`. The temporary
validation containers can be restarted with
`podman start dde-fpocket-edge-offline dde-fpocket-intel`; their volumes and both
clean build trees are retained.

Supported-format limits and failure recovery are documented in
[the repair README](../README.md). Unrepresentable identities are explicit errors;
repeat calculations require a new destination via `--out`.

Completion is limited to this tested coverage and workflow. It does not establish
universal parser safety, experimental binding, drug efficacy, or general scientific
validation of fpocket.
