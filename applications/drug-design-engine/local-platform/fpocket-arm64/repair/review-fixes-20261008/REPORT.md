# Release v3: 2026-10-08 review fixes

Date: 2026-10-08. Upstream remains `45f7f26b10592183956cbb35d11b02c0651e6d24`; the
verified 2026-10-07 state is now committed on `kesis/learning-sandbox` (`75650b0`,
`69dbe65`). This report supersedes the 2026-10-07 enablement claim and leaves that
report, manifest and evidence unchanged.

**Status: enabled and verified.** Binary unchanged (`d6a779e6e4932805…`);
environment stamp returns to `sha256:1e9d67ba…`. See [verification.json](verification.json)
and the immutable [release manifest](release-manifest.json).

## What changed

| Finding (2026-10-08 review) | Repair | Evidence |
|---|---|---|
| `structure-screen run` crashed on Click 8.5 (`mix_stderr`), scanned JSON output for a path that could never match, hand-built `raw/structures` paths, and could not re-screen under the no-overwrite rule | One `_invoke` helper reads `outputs.*` from `--json` stdout; `--out` forwarded to both pocket commands; nested refusal text surfaces in the assessment | Fake-CLI end-to-end test; live screen, refused re-screen, and `--out` re-screen in the promoted environment |
| Residues ordered by `repr()` (10 before 9) | `residue_order` numeric key in records and `matched_residues` | Unit case; agent run shows ascending lining residues |
| Body-raised `BlockingIOError` misreported as lock contention | `flock` taken outside the retained-failure block | Unit case: failure directory retained, original exception propagates |
| Skill text implied overwrite; `--near` lacked insertion codes | `pocket-druggability` and `structure-screening` skills updated | Doc change; agent templates still pin skill URIs to the upstream commit |

## Gate rerun

Both existing clean ARM builds were re-qualified against the new source without
recompiling: 67 boundary and 6 column reader cases, 45 scientific checks, 20 bundled CIF,
10 additional structures, 5 sanitizer fixtures and 100-cycle lifecycle probes per build;
the mutation corpus and Intel evidence were reused under their own bindings. DDE: 44
modules, 726 pytest-passed tests (813 junit-counted including subtests), no
skips; 21 workflow, 6 review-workflow, 4 smoke, identity and 7 Scion-namespace checks;
five harness self-test logs. `assemble_release.py` passed and bound the exact host file
hashes. Largest median volume differences from the original Intel oracle:
patched_intel 1.47%, arm_a 1.09%, arm_b 1.13% (limit 5%).

## Promotion

Rollback to the fpocket-disabled snapshot, before-snapshot, `promote.py`, then
`structure_screening.py` copied into `/scion-volumes/source` (not covered by
`provision.sh`), then `dde env stamp`. All 28 learning files and the six other tool
binaries retain their hashes. The agent-namespace verification found 13 pockets,
pocket 1 scoring 0.664 with druggability 0.855, input hash unchanged.

Rollback: `python3 /scion-volumes/fpocket-arm64/repair-reviewed-20261008/rollback.py
/scion-volumes/fpocket-v3-rollback-20261008` restores the disabled state. The 2026-10-07
backup remains at `/scion-volumes/fpocket-review-fixes-rollback-20261007-v2`.

Host evidence: `.dde-local/fpocket-validation/review-fixes-v3-20261008-evidence.tar.gz`,
`review-fixes-v3-working/`, `review-fixes-v3-agent/`. Candidate root:
`/scion-volumes/fpocket-validation/review-fixes-v3-20261008`.
