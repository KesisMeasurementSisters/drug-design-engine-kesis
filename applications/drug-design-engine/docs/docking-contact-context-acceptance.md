# Docking contact context: narrow acceptance

Decision date: 2026-10-11. The owner authorised promotion of implementation
`aef9806eac29fb2fb376163ae17dde3375df1472` for continued experimental use.
This explicitly supersedes the original plan's all-criteria adoption condition;
it does not change the recorded test outcomes.

Use `dde docking contacts --atom-context` when interpreting short-distance
warnings. The option remains off by default for compatibility. It adds atom
identities, heavy-atom distances and interpretation limits without changing
legacy warning flags, thresholds, contact counts, scores or rankings. No Pocket
code, docking algorithm or agent role template is changed by this promotion.

The bounded comparison supported the targeted distinction between hydrogen
warnings and heavy-atom overlap, while retaining a genuine heavy-atom concern in
an artificial control. This is limited case evidence, not general validation.
Original experiment records are retained privately outside tracked Git content.

## Separate limitation: overclaiming

The reviewed agent narrative still described proximity as established hydrogen
bonding and called a chemical feature indispensable without the supporting
analysis. The observation-versus-hypothesis requirement remains unmet. Acceptance
of the annotation does not certify those claims, binding affinity, biological
activity or clinical usefulness. Track this limitation independently; do not
silently modify role instructions or expand this repair to solve it.

## Rollback

Omit `--atom-context` for the legacy payload immediately. To remove the source
implementation, revert `aef9806eac29fb2fb376163ae17dde3375df1472` in a reviewed
commit. For the local shared runtime, retain its previous source identity and
environment records before promotion, restore that source and stamp/verify the
restored environment. Do not delete original run artifacts or restore unrelated
runtime state. Runtime receipts remain local.
