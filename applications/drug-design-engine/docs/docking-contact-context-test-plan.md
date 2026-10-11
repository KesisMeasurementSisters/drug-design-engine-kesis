> Historical test plan. The later narrow acceptance decision is in
> [docking-contact-context-acceptance.md](docking-contact-context-acceptance.md).
> The original criteria below remain unchanged.

# Contact-warning repair and two comparison tests

Status: reversible candidate implemented on `codex/docking-contact-context`; shared tools are not promoted. Henry requested two concurrent comparison runs. The proposed comparison is original versus candidate on each of the two cases below: four fresh reviews, at most two active at once. The choice between that comparison and two candidate-only reviews is pending Henry's clarification. No research-agent review has started.

The baseline is fork `main` at `5b0a925fc7aa7945ca160cb65d77a81030289dbe`, freshly fetched on 2026-10-11. The original oncology run and its frozen scorer remain unchanged. The host evidence package is `.dde-local/docking-contact-context-01/`; original evidence is `.dde-local/docking-oncology-01/`.

The change adds `dde docking contacts --atom-context`. It identifies the closest atom pair and the closest heavy-atom pair for each existing short-distance warning, states whether a heavy-atom pair also falls below the threshold, and attaches an interpretation limit to the sidecar and CLI output. Missing atom types stay unresolved. A known heavy-atom overlap is still flagged even when an even closer hydrogen pair is present.

The option is off by default. Existing contact fields, distances, residue counts, mode order, thresholds and warning flags retain their meaning. The new fields annotate an existing warning; they do not suppress it or certify a pose as safe. Context is added only to flagged contacts to bound output growth. The scientific basis is the [Vina FAQ](https://autodock-vina.readthedocs.io/en/latest/faq.html): output hydrogen positions are arbitrary, although correct input protonation remains important.

No docking algorithm, score, input preparation, ranking rule, Pocket code, model, role instruction or validator policy changes. This is not a general chemistry-aware clash detector. Existing consumers that ignore the added context continue to see the original warning, so downstream interpretation must be tested rather than assumed.

The immediate fallback is to omit `--atom-context`, which restores the original contact payload. The code is also isolated in a single repair commit; revert that commit to remove the implementation and its tests. The local evidence package records the exact repair commit and source patch. A rollback rehearsal applies that patch in reverse to a disposable copy, compares both source files byte-for-byte with the baseline, reapplies it, and checks the candidate bytes. It never resets a shared checkout or removes historical evidence.

## The two cases

| Case | Input and question | Success | Failure |
| --- | --- | --- | --- |
| 1. Replay the original atom problem | Use the nine original Vina poses and receptor unchanged. Produce either original contact output or annotated output, then ask a fresh team to assess the poses, explain warnings and recommend up to three. Withhold the original finding, decision, experimental coordinates and this rubric. | Recognises that the ARG394 short distances involve hydrogens and do not establish heavy-atom interpenetration or required protein movement; distinguishes measured distances from hypotheses. Final choice and alternatives are stated consistently and supported by the supplied evidence. | Again asserts a severe protein collision or required protein movement from those distances alone; treats absence of a warning as proof of physical correctness; or gives an unresolved contradictory first choice. |
| 2. A new, real heavy-atom overlap | Supply an explicitly artificial geometry control, not a new docking prediction: one ligand/receptor pair has an extremely close hydrogen contact and a separate 1.2 Å carbon–carbon distance. A matched separated control has no distance below the unchanged 2 Å threshold. No Vina energies or affinity claims are attached to these invented coordinates. | Identifies the carbon–carbon overlap and retains the concern despite the hydrogen caveat; distinguishes it from the separated control; scopes conclusions to the supplied geometry. | Dismisses all short contacts as a hydrogen artefact, misses the heavy-atom overlap, calls the separated control proven physically/biologically valid, or invents binding scores. |

Case 2 deliberately checks the feared downstream consequence: solving a misleading warning must not teach the team to ignore a genuine problem. It is not evidence of generalisation to a second oncology target. A new protein–drug experiment would require its own plan after this narrow repair has been assessed.

For case 1, the independent geometric endpoint remains a secondary check: compare the final first choice with the original reference using the preserved symmetry-aware scorer and strict RMSD <2 Å criterion. Modes 1 and 2 are known hits to the operator only. Do not require a particular mode number in agent instructions or supply the answer. A sound interpretation with a different ranking is recorded separately from a geometric miss; prose does not change the frozen score.

For case 2, generate the control deterministically from explicit atom types and Cartesian coordinates, save it in a new project, and freeze the bytes before any agent starts. Keep the expected atom pairs and distances host-only. Both variants get identical control coordinates and the same statement that these are artificial geometry checks without binding energies. They do not get labels such as “bad pose” or the pass criteria.

## Comparison and launch boundaries

The recommended four-review comparison uses the same two cases with both versions. Wave 1 reviews both cases concurrently with original output; wave 2 reviews both concurrently with annotated output. Each review gets fresh controller, science-lead and computational-chemist sessions. Keep model, role templates, neutral question, input bytes and budget identical within each case. No team sees another team's reports, the patch rationale, old conclusions or the scoring key. Do not give scientific feedback between waves.

These are reviews of saved geometry and tool output. Generate the original and candidate contacts deterministically before launch, save exact source identities and hashes, and have agents review those supplied outputs. No fresh Vina calculation, docking repeat, preparation change, relaxation, alternate seed or parameter search is needed. The original variant must be generated with baseline source; candidate output uses the opt-in option. The baseline team must not encounter the candidate's explanatory help or source.

Before launch, freeze the two input packages, neutral role briefs, original and candidate outputs, rubric, source/patch hashes and actual runtime versions. Give each team read-only access to its assigned inputs and installed tools plus a writable case directory. Verify actual mounts: no old-project directories, other variants, host reference, operator plan or full shared-volume root. A prompt alone did not enforce this restriction in the original run. If the installed Scion mount behaviour prevents that separation, report the specific limitation before launch rather than claim isolation.

At most two teams are active concurrently. Each has a maximum 60-minute window from its recorded start, including startup and report writing, and seals early after complete submission. A local guard stops only the case-owned agents and hashes the snapshot. No automatic extension, quota retry or replacement session. Preserve failed/incomplete work and exact timing. Collect the original specialist finding and lead decision for every review. Use a bounded heartbeat for collection only after a launch actually occurs, then pause it after the last pair.

For each case, record the original and candidate outcomes side by side:

| Original | Candidate | Interpretation |
| --- | --- | --- |
| Fails interpretation | Passes | Evidence of improvement on this case; one paired observation is not a general reliability estimate. |
| Passes | Passes | Compatible result, but no demonstrated behavioural improvement. |
| Passes | Fails | Regression: withdraw the candidate from further use and investigate. |
| Fails | Fails | The change was insufficient; do not promote it. |
| Invalid or incomplete | Any | Comparison is unresolved, not a success. Preserve the attempt. |

The candidate is eligible for further use only if both candidate cases pass their respective interpretation criteria, the genuine-overlap concern survives, input and source integrity hold, and compatibility checks show no regression. A repeat of case 1 alone is insufficient. A good agent answer also cannot override a broken downstream consumer or provenance record.

## Verification before agent runs

Local checks cover the warning distinction, hidden heavy-atom overlap, missing atom types, threshold boundary, unchanged default parser/payload, sidecar hash and relay propagation, separate chains, and contact-matrix behaviour. The real saved oncology replay checks exact equality with its original contact record, unchanged legacy fields with annotation enabled, identical matrices, and the existing viewer's plot data and labels. Viewer data testing is not a full browser rendering test.

The two affected source files are `tools/dde/commands/docking.py` and `tools/dde/core/provenance.py`; tests are in `tools/tests/test_docking_contact_context.py`. The shared Podman environment and existing skill pins are not updated by the candidate. Runtime verification is recorded separately from host tests. The broader relay-registry check has two pre-existing findings (`hypothesis.strategy_fallback` and `provenance.cross_wo_overwrite`); the same findings were reproduced on baseline source. The new relay is registered and has an emission site.

After comparison, retain the original reports, an expected-versus-observed table, all failures and the repair/rollback identities. Decide whether to adopt, revise or revert this small change before adding a new scientific experiment.
