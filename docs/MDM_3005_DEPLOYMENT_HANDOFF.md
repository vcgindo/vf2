# 3005 MDM deployment handoff

This delivery installs all eight families on the retained April7 fixture. It proves
supported UI requests, separate reviewer decisions and actual downloads; it does
not certify a daily calculation or application of queued changes. Status authority
remains `MIGRATION.md`. Execute [operator steps](MDM_3005_OPERATOR_STEPS.md).

## Runtime identity

| Item | Verified value |
|---|---|
| Address | localhost:3005 |
| Image | sha256:b3bc7ea3994db6967a590fb3d5d7b265d680d7bce205f9395643e7efd3582016 |
| Code | Base12a8e71 plus the target runtime changes in this delivery commit; all1111 packaged files verified against the running container |
| Schema | 0106_finalize_target_mdm_bootstrap |
| Fixture | bfd75b4b-a9df-4a08-82d3-852e3324b623 /2026-04-07 |
| Source | eccbec8cf5f61f87f80bdf65715dee350e616041e7957f27daead42bab4b975d |
| Fixture file SHA256 | a6b28597dc5ec7d5e013521f548da0f90512d64834d3c8e869225033fc2a3f3d |
| Permission SHA256 | 401029e3f583953a19bfb78be9bbc2487ec0f30e0685977e2480e9da383e0c82 |
| Owner receipt | 8716a82abfc30a85629d33367cd939a968329f69dbdd262451154812ca4251e7 |
| Selected BTR generation | e5bdac30-bbd9-45d8-a93d-84a645fad73c |
| Startup admission | 5c90ae58f6478f7b1805f534f95fbe0de241a5280c4422ec70f28467221bf3e7 |
| Limits | 4GiB,2CPU,restart=no,no MTA host-port mapping |

The single MTA container was restarted successfully. Image/configuration/container
identity remained exact; every other container retained identity/start time/status.
All family owners readmitted,97097 eligibility rows retained their full digest,
daily root/capture remained denied. The authenticated requester reloaded Task Status
and opened the persisted SOB approval after restart. No3006 change was made.

## Verified review and download evidence

Requester3 and reviewer2 used real password/CAPTCHA sessions. All ten tasks were
submitted, assigned, approved and downloaded through the unchanged frontend.

| Variant | Task | Download |
|---|---|---|
| SOB | 3_20261010010914 | SOB.xlsx |
| MOQ | 3_20261010011003 | MOQ.xlsx |
| Stop | 3_20261010011427 | StopPIPO.xlsx |
| Phase Out | 3_20261010011044 | AddPO.xlsx |
| PIPO | 3_20261010011133 | AddPIPO.xlsx |
| Target Norm | 3_20261010011208 | AddTargetNorm.xlsx |
| Seasonality Resume | 3_20261010011629 | SeasonalityStatus.xlsx |
| Absolute Seasonality | 3_20261010011239 | AbsoluteValueSeasonality.xlsx |
| Delta Seasonality | 3_20261010011315 | DeltaPercentageSeasonality.xlsx |
| Force | 3_20261010011756 | ForceNormChange.xlsx |

Complete typed task/history/revision rows and downloaded cells/hashes are retained.
Nine native details say DB Update Pending; Seasonality Status says DB Updated.
Parent headers remain Pending. Modification History excludes these headers under
the native completed-task/date rules. No fabricated history or business day was used.
The earlier broad self-requested tasks remain unassigned/pending and are not approval
proof. Seasonality ADD draft reopening retains the approved blank-projection limit;
Resume retains the native misleading Stop review label. XLSX upload succeeds; the
frontend CSV ZIP-reader failure remains recorded.

Existing SKU2189/Location234/current filtered SKU–Location103 reads and saved exports
passed. Retained BPR/BTR/RRR/Research/DBM/Planning/Guided/Buffer Trends rendered;
BOR rendered its empty grid. These are bounded deployment checks, not universal
report or matched-performance acceptance. Prior blocked routes remain blocked.

Seasonality graph now renders with its GIT control. The exact expression index
preserves all180 ordered source rows. The first20-minute concurrent build timeout
is retained; bounded concurrent recovery passed. No query/ranking/business rule
changed. Seven focused tests, real migrations, Django check/drift checks and runtime
file verification passed. Backup catalogue readability is not a restore rehearsal.

## Evidence and rollback

Evidence root: `D:/freshvcf-build/evidence/mdm3005-deployment-20261009-001/`.
Use `final-restart-*.json`, `final-restart-admission.log`, `final-fixture-selection.log`,
`restricted-approved-task-readback.json.gz`, `task-download-cell-evidence.json`,
`season-graph-index-recovery.log` and `post-restart-approved-task.png`.
Original failures and backup remain beside them. The exact guarded index helper is
`tools/ensure_mdm3005_graph_index.py`; it is host setup tooling, not runtime image code.

Use the numbered rollback section in the operator steps on an attributable
deployment regression. Retain additive schema; never restore over the database or
restart shared services. This handoff authorizes no further phase or business day.
