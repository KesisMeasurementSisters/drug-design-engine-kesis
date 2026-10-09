# Kesis local operations: handoff for a new session

State as of 2026-10-08. Read this before touching the environment. Nothing here
contains a credential; the Gemini login lives only inside agent containers.

## What exists

| Thing | Where | State |
|---|---|---|
| Trunk | `https://github.com/KesisMeasurementSisters/drug-design-engine-kesis`, branch `main` (default), public | `ed5d60d` and later. Upstream GoogleCloudPlatform/LifeSciences is remote `upstream`; sync with `git merge upstream/main` on `main`. |
| Local checkout | `~/Code/KesisMeasurementSisters/drug-design-engine` | `origin` = fork, `upstream` = Google. |
| Scion server | workstation mode, loopback only: Hub + broker + web on `http://127.0.0.1:8080` | `scion server status` / `start` / `stop`. Dev-auth token is printed in `~/.scion/server.log`; export it as `SCION_DEV_TOKEN` for CLI calls. Project is linked to the Hub. |
| Templates | 22 role templates imported into `.scion/templates/` and synced to the Hub | Skill URIs pinned to fork commit `86b340f`. Bump when skills change (see below). |
| Tools volume | Podman volume `dde-tools-arm64`, mounted at `/scion-volumes` in every DDE container | venv at `/scion-volumes/tools/.venv`, binaries in `tools/bin` (fpocket, vina, muscle, rate4site, hypex, elo, prox), editable DDE source at `/scion-volumes/source` checked out at the fork tip. `source /scion-volumes/tools/env.sh` first. |
| Learning project | `/scion-volumes/learning` (28 files, compound artifacts only) | `DDE_PROJECT` for agents. |
| Agents | `controller` (research-operations-controller, created, not started); `subscription-smoke` (default template, running, has the Gemini login) | `scion list` |
| Containers | `dde-tools-arm64` (running; host repo read-only at `/baseline`), `drug-design-engine--subscription-smoke` (running), qualification containers `dde-fpocket-edge-offline` / `dde-fpocket-scion-check` / `dde-fpocket-intel` (stopped; volumes retained) | |
| fpocket release | v3, binary `d6a779e6…c156cb0`, env stamp `sha256:1e9d67ba…` | `local-platform/fpocket-arm64/repair/review-fixes-20261008/` holds the handover, manifest and verification record. Rollback snapshot `/scion-volumes/fpocket-v3-rollback-20261008`. |

`dde doctor` inside the tools container exits 0. Remaining warnings are credentials
not set (GCP ADC, AlphaGenome, NCBI key) and threshold sets with unresolved names.

## Launching the controller

```bash
export SCION_DEV_TOKEN=$(grep -o 'scion_dev_[0-9a-f]*' ~/.scion/server.log | tail -1)
scion start controller        # created from research-operations-controller with .dde-local/scion-arm-learning.yaml
scion attach controller       # complete the agy (Gemini subscription) login once
# inside the agent, after login:
python3 /home/scion/.scion/harness/capture_auth.py
```

`capture_auth.py` stores the Gemini credential as a Scion secret (`AGY_TOKEN`) so
specialists the controller spawns inherit it. Then send the program directive from
`docs/quickstart-pilot.md`. Role agents use image
`localhost/dde-antigravity-arm64:learning`, model `gemini-3.8-flash-high`, and the
env in `.dde-local/scion-arm-learning.yaml`; pass that file with `--config` when
creating further agents by hand.

## Rules that keep the evidence chain intact

- `tools/dde/commands/pocket.py` and `tools/dde/core/pocket_runtime.py` are hash-bound
  into the release manifest. Any edit forces the gate rerun documented in
  `local-platform/fpocket-arm64/repair/README.md` (qualify a+b, run_dde, workflow
  scripts, assemble_release, rollback + promote). Do not edit them casually.
- `structure_screening.py` is not provisioned by the release scripts; after changing it,
  copy it into `/scion-volumes/source/...` by hand or `git fetch && git checkout` there.
- `dde pocket run` never overwrites; rerun with `--out`. Failed runs leave
  `.<stem>.failed-*/` and a lock file; keep them.
- Files moved into the tools volume with `podman cp` carry an SELinux label that
  `shutil.copytree` cannot re-apply; recreate the tree with `tar` inside the container.
- Pytest is deliberately absent from the DDE venv; install it to a side directory and
  use `PYTHONPATH`, one pytest process per module.

## When skills or templates change

1. Commit and push to `main`.
2. Replace the pinned SHA in every `templates/*/scion-agent.yaml` with the commit that
   carries the skills; run `python3 tools/check_skill_uris.py` (expects 32 of 41 skills
   reachable; nine upstream skills are granted by no template).
3. `scion template import applications/drug-design-engine/templates --all --force`
   then `scion templates sync --all`. Agents provisioned earlier keep the old pin.

The fork must stay public: Scion downloads `SKILL.md` from raw.githubusercontent.com
without authentication, so a private repo cannot provision role agents.
