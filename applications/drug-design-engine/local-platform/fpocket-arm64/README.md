> **Current status: repaired release enabled after expanded verification.** See [repair/REPORT.md](repair/REPORT.md). The original release record below is historical and revoked.

# Historical first ARM64 release (withdrawn)

Verified and enabled on 2026-10-06 (Toronto). The runtime is Linux AArch64 in
the local M4 Pro Podman VM. DDE remains at
`45f7f26b10592183956cbb35d11b02c0651e6d24`. Scion, Gemini 3.8 Flash High, and
subscription authentication are unchanged. No paid cloud services were used.

Read `verification-report.json` for results, hashes, limitations, and evidence
locations. `dependency-manifest.json` records the exact sources and build settings.
The `reports/` directory contains the acceptance reports. Downloaded sources,
executables, complete output trees, and failed-run evidence are outside tracked
source in `.dde-local/fpocket-validation/` and the isolated Podman volumes.

## Results and the portability fix

- Two clean ARM builds each passed all 45 architecture, reader, scientific,
  option, parameter-change, repeated-volume, and failure checks.
- Each build passed five ASan/UBSan reader cases, with no reported leaks.
- Each build passed seven DDE checks in Scion's actual user namespace, including
  the existing 22 pocket/peptide tests, unchanged.
- All 13 median pocket volumes met the existing 5% tolerance over ten distinct
  time seeds per architecture. Maximum differences were 1.8313% and 1.0254% for
  the two ARM runs. Per-pocket ranges and variability are in the report.
- The existing agent ran and analysed `1UYD`: 13 pockets; best score 0.664;
  best druggability score 0.855. Both commands exited zero.
- Doctor, Vina, MUSCLE, compound descriptors, and Hypex checks passed.

The initial ARM build compiled and linked but **failed scientific comparisons**.
Default fused floating-point arithmetic changed surface areas, scores, and pocket
ranking. Adding `-ffp-contract=off` to fpocket C compilation restored every frozen
reference. Optimisation (`-O2`), hardening, Qhull's build, and scientific source
algorithms remain unchanged. There are no source patches or stub functions.
`diagnose-fp-contraction.sh` preserves the diagnostic method.

The original Intel archive reports ABI20 despite fpocket shipping ABI18 headers.
Only the Intel probe's expected registration version is 20. ARM is built against
fpocket's own ABI18 headers and must register ABI18. All returned reader data
are compared exactly across architectures. `test-amendments.json` documents this
reference correction and the AMBER fixed-width padding correction. Original
pre-build hashes and unsuccessful reports were retained.

Reader archive hashes are identical between clean builds. Executable hashes
differ because bundled Qhull embeds the absolute build path in debug information.
After excluding debug sections and the GNU build ID, complete runtime ELF bytes
are identical. The installed binary is the original, unstripped, tested second
build, identified by its recorded SHA256.

## Files and reproducible sequence

`source-lock.json` is the original pre-build freeze: source archives, headers,
fixtures, reference outputs, and initial tests. Do not regenerate expected output
from an ARM result. `test_contract.json` fixes the comparison rules and timeouts.

1. Obtain the two archives from `dependency-manifest.json` into an ignored input
   directory as `fpocket.tar.gz` and `molfile.tar.gz`. `build.sh` verifies their
   pinned SHA256 hashes before extraction. Use the recorded GCC toolchain and
   Python with Gemmi 0.7.5. All output directories must be new.
2. Run the comparator tests **before building**:

   ```sh
   PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s "$PACKAGE" -p test_validation.py -v
   ```

   Missing binaries, timeout, non-finite values, deleted pockets, changed residues
   and scores, and truncated output must be rejected. Dependencies never produce
   successful skips.
3. Build the original Intel reference in an isolated x86_64 Linux container:

   ```sh
   bash "$PACKAGE/build.sh" intel "$INPUTS" "$INTEL_BUILD"
   python3 "$PACKAGE/validation.py" \
     --binary "$INTEL_BUILD/fpocket-4.2.2/bin/fpocket" \
     --source "$INTEL_BUILD/fpocket-4.2.2" --probe "$INTEL_BUILD/probe" \
     --fixtures "$PACKAGE/fixtures" --work "$ORACLE" \
     --architecture 'Advanced Micro Devices X86-64'
   ```

   A fresh run uses the corrected reference probe and should pass directly.
   `assemble_reference.py` is only for auditing this implementation's original
   five ABI-registration failures and their separate successful rerun; it refuses
   unrelated failures. It was not used to replace scientific expected results.
4. Build ARM in a clone of the tools volume at the same internal paths:

   ```sh
   bash "$PACKAGE/build.sh" arm "$INPUTS" "$ARM_BUILD"
   python3 "$PACKAGE/validation.py" \
     --binary "$ARM_BUILD/fpocket-4.2.2/bin/fpocket" \
     --source "$ARM_BUILD/fpocket-4.2.2" --probe "$ARM_BUILD/probe" \
     --fixtures "$PACKAGE/fixtures" --work "$RESULTS" \
     --architecture AArch64 --oracle "$ORACLE"
   python3 "$PACKAGE/sanitizers.py" "$ARM_BUILD/probe-sanitized" \
     "$ARM_BUILD/fpocket-4.2.2" "$PACKAGE/fixtures" "$SANITIZER_RESULTS"
   ```

   The archive contains only `pdbx.o` and `parm7.o`. Probes use real callbacks.
   Reader timeout is 30 seconds; structure timeout is 120 seconds. Full file
   sets and complete raw line counts are checked before exact comparisons with
   upstream's existing volume-line exclusions. Timeouts fail.
5. Install into the **candidate volume only**, stamp that isolated environment,
   and run `integration.py SOURCE NEW_PROJECT REPORT`. Source `tools/env.sh`
   first. Repeat under a container sharing the existing agent's user namespace
   (`--userns=container:drug-design-engine--subscription-smoke --user scion`).
   Repeat the build in a clean directory and run the complete suite again.
6. Package passing reports with `release.py`, preserve production metadata and
   verify the agent is idle. `provision.sh RELEASE BIN_DIRECTORY` installs only
   the hash-matched, accepted static ARM executable. `prepare-installer.py`
   creates the local installer overlay. Neither edits upstream DDE source.
7. Stamp the live environment, run doctor with `DDE_PROJECT` set, execute one
   bounded agent calculation, and run `regression.py NEW_OUTPUT_DIRECTORY`.

`release.py` uses the directory names retained by this implementation; see its
explicit input list when reproducing in a fresh validation root. It records a
pre-enablement receipt. Final doctor and agent verification are recorded separately
in `verification-report.json`; an intermediate receipt is not a completion claim.

## Installed locations and learning artifacts

- Tools volume: `dde-tools-arm64`; executable: `/scion-volumes/tools/bin/fpocket`.
- Local provisioning package: `/scion-volumes/fpocket-arm64`.
- Environment stamp: `sha256:befbee9638683c52ce6460c889902e26b967e05a4d30207ec1169d3dbc15f3a0`.
- Disposable agent project: `/scion-volumes/fpocket-agent-verification`.
- Host copy: `.dde-local/fpocket-validation/agent-project/raw/structures/`.
- Full evidence: `.dde-local/fpocket-validation/validation-evidence.tar.gz`.
- Isolated builds and failed diagnostics: volume `dde-fpocket-candidate` at
  `/scion-volumes/fpocket-validation`; Intel volume `dde-fpocket-intel` at `/validation`.

The three isolated validation containers are stopped; their volumes and evidence
are retained. Start them with `podman start dde-fpocket-candidate
dde-fpocket-intel dde-fpocket-scion-check` when needed. The working toolbox and
Scion agent remain running.

All 28 pre-existing learning files and all six pre-existing tool binaries retain
their original hashes. No existing learning artifact was rewritten.

## Rollback

The original environment had no fpocket executable. The untouched snapshot is
`/scion-volumes/fpocket-rollback-20261007` in the tools volume, also copied to
`.dde-local/fpocket-validation/production-backup`. The original host setup manifest
and overlay generator are in `.dde-local/fpocket-validation/host-backup`.

1. Ensure `subscription-smoke` is idle. Preserve the current stamp, manifests,
   installer, and any new results in a separate rollback-event directory.
2. Check the installed fpocket hash against `verification-report.json`. Move that
   binary out of `tools/bin` into the rollback-event directory; retain it for audit.
3. Restore `ENV_VERSION`, `ENV_SOURCE`, `ENV_HISTORY`, `env-manifest.txt`,
   `requirements.lock`, `HOST_REQUIREMENTS`, and the installer overlay/generator
   from the snapshot. Preserve newer archived manifests as historical evidence.
   Restore the two host files from `host-backup` if reverting host setup records.
4. Run `dde env show --json` with the usual environment. It must report no drift
   and the previous stamp
   `sha256:67718829910277cc16be681e50142f22e12efc186ba8fd031b79faf9b19eee6b`.
   Run doctor with the learning project set; pocket detection should again be
   unavailable. Recheck the saved existing-tool and learning-file hashes.

Do not rewrite existing artifact sidecars or delete verification results during
rollback. Their environment stamps describe the environment that produced them.

## Limits

This qualifies the listed structures, reader fields, options, and DDE workflow.
It does not establish experimental binding, drug efficacy, or general scientific
validation of fpocket. ABI18's reader path can truncate mmCIF chain IDs longer
than two characters; the tested fixtures match Intel exactly, but this is not
qualification for arbitrary extended chain IDs. The small water topology tests
AMBER reader semantics and is not a molecular-dynamics parameter set. VMD and
broader molecular-dynamics applications were not built. Unrelated pre-existing
doctor warnings remain, including unavailable cloud capabilities.
