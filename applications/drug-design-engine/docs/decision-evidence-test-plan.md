# Decision evidence: implementation and test plan

Status: experiments closed. Mechanical validation fixes and review traceability
are retained; the comparisons did not demonstrate improved detection of causal
overclaims. The additional reviewer paragraph was removed after the final clean
comparison failed. No further experiments are authorised. Shared tools and imported
role templates have not been promoted. Private experiment records remain archived.

Baseline: `a9cf6836d14a8973a2287eedd4344c79f6f04a93` from the fork's fetched
`origin/main`. Bind the candidate to the commit containing this plan and record its
full SHA in the launch manifest. The plan is not permission to start a run.

## What changed

The lead must give a short, source-backed explanation of the claims that determine
its recommendation. The independent reviewer checks those claims in the proposed
final narrative and machine-readable decision, records the reviewed hashes, and
identifies supported, contradicted or insufficient claims. The lead records how it
resolves the challenges. Materially changed conclusions need a focused recheck within the
existing budget or remain explicitly unreviewed.

Literature-only review checks the supplied source spans without inventing a tool
re-analysis. Missing evidence, proposed policy and measured failure stay distinct.
The output is a concise, inspectable rationale grounded in cited observations.

The validator rejects empty or invalid analysis references and unknown threshold
names. It checks mandatory relays in each relevant finding; a label in another
finding cannot satisfy the requirement. A different version of a recognised threshold
name produces a warning, not proof that the version exists or policy is correct. Relay
presence still does not establish that the conclusion respects the limitation.

## Software checks

The synthetic regressions in `tests/test_decision_evidence_validation.py` cover:

| Change or risk | Check |
| --- | --- |
| Empty or fabricated analysis references | Reject null, empty and mistyped fields, absent or out-of-root source files, directories and invented threshold names. |
| Compatibility | Accept current registered tags, program overrides, composite tags and existing descriptive analyzer identifiers; warn on a different version. |
| Relay in the wrong finding | Fail the source-citing finding even if another finding carries the required label. |
| Attribution | Recognise supported local citation forms and sidecar/source chains; keep independent source obligations separate. |
| Work-order boundary | Ignore records assigned to another work order; keep literature-only checks explicitly skipped. |
| Limits | A similarly named code fails; a correct label with an unsupported conclusion still passes mechanically and needs scientific review. |

Run the new module plus the existing phase-3, provenance/source, source-tag, dry-run
and work-order governance tests, one pytest process per module. Run lint and the
invocation, artifact-path, skill-URI and threshold-name documentation checkers.
These are software and instruction checks, not scientific validation.

## Original comparison protocol (closed)

The following preserves the original protocol, not an instruction to launch a run.

Use one fresh, small synthetic literature packet and the same neutral decision
question twice: once with the baseline instructions and once with the candidate.
This exercises the final-decision review path that the validator cannot assess.
There is no fresh scientific computation or external literature search.

Before launch, freeze the packet, starter specialist finding, draft recommendation,
machine-readable draft, task brief and separate scoring key. Include both warranted
and unwarranted claims so blanket refusal cannot pass. The material should exercise:

- a limited observation being used to support a broader mechanistic conclusion;
- information absent from the packet being treated as a measured negative;
- a proposed resource or numerical rule being presented as an established result;
- a decisive inconsistency between the draft narrative and decision fields;
- at least one supported conclusion that should survive review.

The public plan describes test categories only. Exact expected answers, labels and
the scoring key stay outside Git and inaccessible to the evaluated agents. Use new
synthetic material; do not repair or rescore the old pilots for this test. Give both
arms identical input bytes and a neutral request to assess the evidence and finalise
the recommendation. Do not identify the planted errors in the task brief.

Each arm uses fresh lead and reviewer sessions. The lead prepares its decision;
the reviewer independently checks the supplied sources and that draft; the lead
resolves challenges. Allow at most one additional reviewer session for a focused
recheck of materially changed claims, within the same time ceiling. Preserve both
reviewed and final versions, including unresolved differences.
Do not give either arm the other arm's output or scoring feedback.

Proposed ceiling: 30 minutes per arm including startup and report writing, arms
sequential, at most two active agents, no replacement of failed sessions, automatic
retries or budget extensions. Keep the model, harness, tools, input bytes and budget the
same; only the approved candidate source and role instructions differ. Record the
actual model/runtime identities rather than assuming their configured names prove
what was loaded.

Load each version in an isolated test snapshot and verify the actual instructions
and tool source by hash. A branch edit does not update an imported Scion template.
Check that the mounts exclude the scoring key, this operator plan, previous runs
and the other arm. Do not update shared tools or globally import templates as part
of test preparation. Stop if source identity or isolation cannot be established.

## How to judge the comparison

Score the untouched outputs against the frozen key, recording baseline and
candidate side by side. The candidate passes this case only when:

1. Every decisive factual claim has a correct source location and an explanation
   of how the observation supports the choice, with its material limits.
2. Unsupported decisive claims are corrected or explicitly left unresolved; a
   caveat elsewhere does not excuse an unsupported final assertion.
3. Supported conclusions survive. A provisional hold or resource choice remains
   possible when accurately labelled and justified.
4. The reviewer assesses the actual decision draft and decision fields. The final
   narrative, ranking, confidence and machine-readable output agree; any material
   change has a recorded recheck or is clearly unreviewed.
5. Source files stay intact and no citations, measurements, tool runs or approved
   thresholds are invented.

Report individual failures as well as the overall result. A timeout, missing final
artifact, leaked key or wrong instruction snapshot is incomplete or invalid, never
a pass. Preserve all failed attempts and timing. Baseline failure with candidate
success supports improvement on this case; both passing shows compatibility without
demonstrated improvement. Candidate failure prevents acceptance of this case.
One pair cannot estimate reliability or attribute an improvement to one individual
change. Any later adoption or expanded experiment is a separate decision.

## Verification record

The focused seven-module run produced **130 passed and two failed**. All 35 new
regressions passed. The remaining failures, `test_missing_sidecar` and
`test_sha256_mismatch` in the provenance/source module, also fail against the
baseline implementation: those direct helper tests expect JSON records to reach a
provenance check that currently defers unmatched records to another validator
check. They were not suppressed or repaired in this change. Existing source-path
fixtures were updated to use real threshold tags and assert the current diagnostic.

Lint, formatting, diff whitespace and the artifact-path checker pass. The other
documentation checkers report issues in unchanged material: two invocation-parser
complaints in the literature-search
skill, ten threshold-name/declaration issues, and nine skills with no template
grant. These are not a clean release gate. Resolve or explicitly disposition
outstanding release checks before any shared-runtime promotion.
