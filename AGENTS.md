# Public fork operating instructions

This is the public Kesis fork of GoogleCloudPlatform/LifeSciences. Read the
application README and controlling design documents before changing its code.
For the local DDE runtime, also read
`applications/drug-design-engine/docs/kesis-local-operations.md`; verify its dated
state against the live environment before acting.

- Treat commits, PRs, issues and build assets as public. Commit code, synthetic
  tests and sanitised technical documentation only. Keep credentials, OAuth
  material, personal paths, agent logs, private reports, runtime state and withheld
  benchmark answers out of Git. Never force-add `.dde-local/` or `.scion/`.
  Ignore rules are a convenience, not a substitute for reviewing the exact diff.
- Work on `codex/` branches; fetch the fork before integration. Review and commit
  explicit paths, preserving unrelated work. Never push to upstream by assumption.
  Experiment approval does not itself authorise publishing its raw records.
- Preserve frozen inputs, original reports, scoring rules and failed attempts.
  Record later acceptance decisions separately; do not rewrite a failed criterion
  into a pass. Keep withheld references inaccessible to evaluated agents.
- A tool measurement, scientific interpretation and experimental confirmation are
  different claims. Report known overclaiming separately from tool correctness.
- Promote only the authorised scope with a source identity, runtime verification
  and rollback. Do not start new runs or extend budgets without authorisation.
- Changes to DDE `tools/dde/commands/pocket.py` or `tools/dde/core/pocket_runtime.py`
  require the gate in `local-platform/fpocket-arm64/repair/README.md` relative to
  the DDE application. A different tool's promotion does not waive that gate.

The accepted opt-in docking contact annotation and its remaining interpretation
limitation are recorded in
`applications/drug-design-engine/docs/docking-contact-context-acceptance.md`.
