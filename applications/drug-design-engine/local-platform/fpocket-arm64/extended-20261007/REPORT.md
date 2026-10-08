# Extended validation: release withdrawn

This report supersedes the original fpocket enablement decision. The original
fixture tests remain valid historical results, but the expanded tests found
memory-safety and input-handling defects. fpocket is now quarantined and its
installer exclusion is restored. Other tools, model settings, authentication,
and existing learning artifacts are unchanged.

## Coverage and results

| Checks | Result |
| --- | --- |
| All 42 upstream DDE test modules, in separate pytest processes | 684/692 pass; 8 failures; no skips |
| Synthetic valid/malformed reader fixtures under ARM ASan/UBSan | 12/23 pass; 11 failures |
| Same reader fixtures against original Intel archive | 15/23 pass; 8 failures |
| Every bundled mmCIF file, independently checked with Gemmi | 19/20 pass |
| Ten additional complete pocket calculations vs Intel | 10/10 match, using original exact comparison rules |
| Real DDE workflow edge cases | 12 initially pass, 8 confirmed failures, 1 expected protective refusal |
| Follow-up analysis preservation/alternate-output check | Pass |
| Four concurrent calculations in separate projects | All pass; each finds 13 pockets with the expected score |

No tolerance was widened. Unexpected failures were retained. Ordinary fixtures
still work, but that is insufficient for general readiness.

## Findings

**F1 — blocking: heap-buffer overflow on a valid mmCIF.** A three-atom fixture
with the author chain ID `ABCDEFGHIJKLMNO` causes an instrumented write beyond a
12-byte allocation in `getNextWord`, called from `parseStructure`. The allocation
is `numberAtoms * CHAIN_SIZE`, with `CHAIN_SIZE=4`; the writer uses a larger generic
column limit. Gemmi independently reads this fixture and preserves the full chain
identifier. A diagnostic with only the author identifier extended reproduces the
overflow. See `reports/asan-chain-overflow.log`.

The original Intel probe returns successfully, but its archive is not instrumented.
That result **does not establish Intel memory safety**, and the overflow must not
be described as proven ARM-exclusive. It is confirmed in the exact pinned source
built for ARM. This finding alone fails the original acceptance requirement.

**F2 — blocking: chain identities can silently merge.** The ABI18 reader truncates
label chain IDs to two characters. `AAA`, `AAB`, and `AAC` become `AA`; `ABC` becomes
`AB`. The original Intel ABI20 reader preserves these label IDs. Label-only long
identifiers reproduce truncation independently of the author-field overflow.

**F3 — high: malformed coordinates can become successful results.** Real
`dde pocket run` accepts a PDB with an invalid coordinate token, and one containing
`nan`, and writes pocket artifacts. These cases require input validation before
the scientific executable is invoked. Empty, truncated, missing, and wrong-extension
inputs are rejected, so those earlier checks did not cover this defect.

**F4 — high: malformed AMBER topology handling is unsafe or permissive.** Both
tested readers accept truncated topology content and an out-of-range bond index.
A topology ending with a `%FLAG` but no `%FORMAT` hangs until the 30-second test
timeout kills its process group. The supplied comment-decorated topology is also
rejected by both readers; this is recorded as a format-support limitation, without
claiming formal AMBER standards conformance.

**F5 — medium: filenames and advertised extensions are not handled consistently.**
Spaces and apostrophes fail; a semicolon reaches fpocket's shell command parsing.
Uppercase `.PDB`, `.ent`, and `.mmcif` pass DDE's extension guard but fail in fpocket.
Lowercase `.pdb`/`.cif`, Unicode filenames, a leading hyphen, CRLF input, read-only
input, and four independent concurrent runs pass. An unwritable output directory
fails without a success artifact. A repair should stage inputs under controlled,
normalised temporary names and avoid shell interpretation of user filenames.

**F6 — medium: CIF field interpretation limitations.** Both readers retain quote
characters around quoted atom names and accept missing coordinate values as
numeric output. Non-finite coordinates are returned to the probe, whose own check
throws; that abort is not evidence of a library-originated crash. The bundled
`1UYD_wrote.cif` is rejected by both readers for bad element indices; the other
19 bundled CIF files pass the tested atom-record and coordinate checks.

**F7 — broader baseline test inconsistencies.** The eight failures in unchanged
DDE tests are: one preflight test assuming a ready x86/network environment; one
installer text assertion that omits the current `--require-hashes` flag; two
normalisation expectations inconsistent with the current canonical-key mapping;
one PubChem slug expectation that omits the CID now appended by the implementation;
and three Click test calls using the unsupported `mix_stderr` constructor argument.
They do not exercise fpocket and were not introduced by the ARM binary. No source
changes or relaxed assertions were used to make them pass. Logs are in `reports/`.

## Harness corrections and boundaries

The first broad attempt used unittest discovery without pytest and encountered
module-level stub interference. The final 692-test count comes from pytest with
each original module in its own process. Test dependencies were installed in a
separate directory, not in the DDE environment. Tests ran with container networking
disabled. A dedicated diagnostic container allowed access to shared test-volume
files across SELinux labels; host security settings were not changed.

The first repeated-analysis check incorrectly expected DDE to overwrite an existing
analysis. DDE correctly refused. A separate follow-up verified that the original
analysis bytes remain unchanged and explicit `--out` succeeds. The unsuccessful
initial test remains in the evidence. Phase-one reruns still replace same-stem raw
results, so distinct output/project directories are necessary to preserve runs.

The binaries and scientific algorithms were not modified in this test pass.
The only implementation change is a provisioning guard that rejects a release
with `REVOKED.json`, preventing accidental reinstallation of this withdrawn build.

## Current environment and evidence

- fpocket executable: removed from the working tools path, retained at
  `/scion-volumes/fpocket-quarantine-20261007/fpocket`.
- Restored environment: `sha256:67718829910277cc16be681e50142f22e12efc186ba8fd031b79faf9b19eee6b`.
- Doctor passes with fpocket unavailable; all six other tool hashes and all 28
  existing learning-file hashes remain unchanged.
- Original model and subscription authentication were not changed. No paid cloud
  services were used.
- Machine-readable findings and counts: `summary.json`.
- Evidence archive: `.dde-local/fpocket-validation/extended-20261007/evidence.tar.gz`.
- Original Intel comparisons: `.dde-local/fpocket-validation/extended-intel-readers`
  and `.dde-local/fpocket-validation/extended-intel-structures`.
- Complete failed logs, timeouts, and representative artifacts remain in the
  archive and isolated volumes. Original acceptance reports were not overwritten.

## Repair order before re-enablement

1. Bound reader writes and preserve complete supported chain identifiers without
   silently merging chains. Keep ABI expectations explicit and rerun the original
   numerical acceptance suite plus all new reader/sanitizer cases.
2. Validate finite, present coordinates and complete topology records, valid bond
   indices, and required format sections before accepting output. Bound execution
   in the application, not just the external test runner.
3. Normalise temporary filenames/extensions and remove shell interpretation of
   input names; rerun the workflow and failure-artifact checks.
4. Resolve upstream test/API inconsistencies separately. Re-enable only after the
   relevant expanded acceptance gates pass, retaining the existing scientific
   tolerances and an independently checked Intel reference.
