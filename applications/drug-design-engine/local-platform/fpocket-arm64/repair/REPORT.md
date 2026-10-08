# Repaired ARM64 fpocket: enabled after verification

The new local release is installed and verified. The original release remains
permanently revoked. Both `dde doctor` and live environment-stamp comparison pass.

| Required check | Result |
| --- | --- |
| Complete DDE suite | **710 passed; 0 failed; 0 skipped** |
| Frozen original acceptance, each clean ARM build | **45/45**, twice |
| Reader boundary cases | **62/62**, plus **6/6** column/line cases, both clean ARM builds and normal Intel readers |
| Native ASan/UBSan mutation corpus | **20,000 cases; no failures or timeouts** |
| Bundled CIF readers | **19 valid fixtures pass; 1 independently malformed fixture correctly rejected** |
| Additional complete scientific outputs | **10/10 match original Intel output** |
| Repaired Intel scientific suite | **All 39 checks pass** |
| Repeated reader lifecycle | **100 open/read/close cycles per reader per ARM build; clean sanitizer/leak logs** |
| Volume comparisons | 10 distinct time seeds per architecture/build; maximum median difference **1.76%**, below unchanged **5%** limit |
| Test-runner self-checks | 11 original comparator tests and 4 sanitizer/runtime-failure tests pass |
| Scion user integration | 7/7 checks pass, with actual UID/GID and user namespace |
| Working-tool regression | Vina, MUSCLE, compound properties, Hypex all pass |
| Existing artifacts | All **28 learning files** and **6 other tool binaries** unchanged |

The existing Scion/Antigravity agent, still using Gemini 3.8 Flash High and the
existing subscription login, ran the bounded local calculation and analysis.
Both exited 0: **13 pockets**, best score **0.664**, druggability score **0.855**.
No paid cloud service was used.

## What was repaired

Reader writes and counts are bounded; supported chain identifiers retain their
full identity; CIF quoting and optional numeric missingness are handled before
conversion; malformed topology records, indices and EOF are rejected. DDE
validates coordinate syntax and finiteness, normalizes staged filenames, enforces
a process-group timeout, checks complete output, and preserves insertion codes.
Repeat runs require a new `--out` destination. Publication is locked, the sidecar
is the completion marker, and subsequent analysis checks the record/tree hashes.
New provenance includes the executable and both DDE source-file hashes.

The expanded work also found and repaired an AMBER header overflow, an interleaved
CIF-column array overflow, and permissive Python numeric tokens. Failed inputs,
pre-fix logs, and unsuccessful builds remain preserved. The eight unrelated
baseline test failures were resolved against their documented contracts; details
and the complete finding ledger are in [README.md](README.md).

## Limits and provenance

An additional **Intel ASan run is unavailable under QEMU**: sanitizer allocator
initialization fails before reader execution. It is not counted as a reader pass.
The production ARM build has native ASan/UBSan coverage; normal Intel reader and
scientific comparisons pass. Explicit format/resource limits are in the README.

This establishes verified native ARM64 pocket detection for the tested formats
and DDE workflow. It does not establish experimental binding, drug efficacy, or
general scientific validity of fpocket.

- Installed binary SHA256: `99394e525e4a93f9d95dddc4a7d7ddcb4e10d4a4a5a650c26792fbf28bbf9c65`.
- Environment: `sha256:0339c6fecf8fe875d1bfdc2ba675ffe306d6da79d06551f9f95781839bb4d277`.
- Clean libraries are byte-identical. Runtime ELF bytes are identical after
  removing debug-path sections and GNU build IDs. Installed binary is the exact
  tested, unstripped second build.
- [Machine-readable verification](verification-report.json) and
  [pre-enablement acceptance receipt](reports/acceptance.json).
- Local evidence archive: `.dde-local/fpocket-validation/repair-evidence.tar.gz`;
  independent Intel evidence: `.dde-local/fpocket-validation/repair-intel-final/`.
- Working rollback snapshot: `/scion-volumes/fpocket-repair-rollback-20261007-v2`.
  `rollback.py` restores the fpocket-disabled binary/source/metadata state.
  A first backup attempt hit a container-label xattr permission before live files
  changed; its partial snapshot is preserved separately. No host security policy
  was relaxed.
- Upstream commit and learning branch are preserved. Local source repairs remain
  reviewable, uncommitted changes; nothing was pushed or published. The expected
  dirty-source doctor advisory is backed by exact source hashes in each result.
