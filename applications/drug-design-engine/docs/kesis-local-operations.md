# Kesis local Antigravity operations

Runtime baseline verified on 2026-11-14: **Antigravity CLI 1.5.9** and
**Gemini 4 Hydrogen, High reasoning** (`gemini-4-hydrogen-high`). This is a
sanitized operating guide, not an inventory of a particular workstation.
Recheck the live runtime before starting work.

## Configure a new local runtime

The [example configuration](../config/antigravity-local.example.yaml) selects
Hydrogen High explicitly in the model field, command arguments and environment.
It contains no credentials, project identifiers or experiment mounts. Copy it to
an ignored local directory and supply the authorized project's mounts there.
The versioned image name is a **locally built ARM64 image**, not a public image
that users can pull. Other platforms must build and verify their own image.

Use the official `agy update` command to update the host CLI and a disposable
build container based on the existing qualified DDE image. Record the reported
version and updater verification result. Build a new versioned image containing
the updated Linux binary; do not retag or modify an image used by a frozen run.
Keep credentials and runtime caches out of the build context and image layers.
Updating the macOS host CLI alone does not update the Linux agent image.

Scion can normalize local image names to a configured registry prefix. Confirm
that the runtime broker resolves the intended local image ID before launch. A
local registry-style alias does not require publishing the image.

## Verify before promotion

1. Confirm the host and actual agent-container CLI versions with `agy --version`.
2. List models with `agy models` in the authenticated environment; verify that
   `gemini-4-hydrogen-high` is available to the account. Do not assume that API
   availability implies subscription access.
3. Launch a fresh, bounded smoke agent using the private configuration, with no
   scientific inputs or prior-run mounts. Verify the actual model process flag
   and session display, a successful inference, and one harmless tool call.
4. Run `dde doctor --json` with the intended tools mounted read-only and a
   disposable project. Preserve warnings and failures as well as successful
   results. A passing doctor check is not validation of every scientific tool.
5. Stop the smoke agent. Promote the launch configuration only after the checks
   pass, retaining the previous configuration, image identity and host binary
   for rollback. Existing agents retain their original runtime until explicitly
   replaced; never resume a completed experiment to change its model.

This baseline passed authenticated inference and a terminal-tool smoke test,
plus the DDE health check. Optional credentials, external services and unresolved
thresholds can still produce warnings. A wrapper token-injection warning was
observed even though authenticated inference succeeded; a warning alone must not
be mistaken for either an authentication failure or a successful login.

## Authentication and publication boundary

Use the existing Scion/Antigravity authentication flow. Keep OAuth tokens, API
keys, development-auth tokens, account details and local logs in protected local
storage. Do not paste token-bearing server output into issues, PRs or reports.
Keep the local Scion control service on loopback unless a separately reviewed
network deployment is intended.

Private operating records belong under ignored `.dde-local/` and `.scion/`.
Never force-add those paths. Ignore rules do not protect files already tracked:
review the exact staged diff and scan committed history before public release.
Publish sanitized configuration examples and technical instructions only, not
binaries, agent homes, raw source libraries, experiment reports or withheld keys.
Use a GitHub-provided noreply commit address when avoiding personal author email
exposure. Removing a file in a new commit does not remove it from old commits.

## Scientific tools and frozen records

This model/harness update does not change or requalify scientific tools.
`tools/dde/commands/pocket.py` and `tools/dde/core/pocket_runtime.py` remain subject
to the gate in `local-platform/fpocket-arm64/repair/README.md`. Do not modify them
as part of a runtime upgrade. Preserve the accepted tool source identity and
rollback records.

Record each new experiment's model, reasoning setting, CLI version, image ID,
source identity, input hashes and bounded budget before launch. Compare model
changes using unchanged evidence and decision rules. Retain previous inputs,
results, failed attempts and acceptance decisions separately. Runtime readiness
does not establish scientific accuracy or authorize a new experiment.
