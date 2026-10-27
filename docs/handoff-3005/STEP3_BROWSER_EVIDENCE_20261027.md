# Step3 browser evidence: 27 October 2026

This is an evidence checkpoint, not Step3 acceptance or a second tracker.
The sole status authority remains `F:/freshvcf/docs/handoff-3005/TRACKER.md`.
Candidate source: `18b9da4d5b1333d6f8409884e452bf12a7b0258f`.
Evidence root: `D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/runtime-step3-20261027`.

## Observed results

The first window was restored after real PostgreSQL ordinary-connection
exhaustion. The human approved one replacement window and a temporary,
exclusive same-volume PG16 container under the original 384 MiB / 0.5 CPU
limits. No frontend design, MTO, calculation, accepted input or publication
change was made. Original containers were retained for restoration.

In the replacement window, using Chrome browser controls only:

- OWN-ROOT7 signed in and saw its two supplier allocations. SKU filtering
  produced one row, a nonmatching SKU produced zero rows, and clearing restored
  two. The user confirmed the existing Excel export arrived.
- The administrator signed in using the current authorized CAPTCHA. Planning's
  four quadrants, Research pair/parent histories and all five Guided tabs
  rendered. The two approved NULL-amount/type-label fixture limitations remain.
- BPR showed eight current rows; BTR showed eight inherited rows. This does not
  claim a new terminal BTR calculation. Seasonality resolved to the existing
  "No Rows To Show" state without a lingering spinner.
- Eight downloads returned HTTP200 and created browser blob links: four Pick
  reports, InputData, DailyDataUnavailabilityReport, Spike_Order_Dump and Total
  Requirement. The human confirmed all eight arrived. Native byte/custody proof
  remains separate from this browser arrival evidence.
- The not-yet-produced InvalidDataReport returned503 and displayed the existing
  download error. An absent optional upload log also displayed the existing
  error. Neither is claimed as positive-file coverage.

The APIRequestFactory supplier identity/entitlement checks use actual owned
users and the live MTA handler, but are not JWT/browser sign-in evidence.
Observed screen times containing tool gaps are not matched latency acceptance.

## Real blocker: positive Sleep at UptoBPR

The browser submitted Sleep for PHASE/WH8's inherited recommendation. It returned
HTTP500: `Registered read requires its accepted placement chain`. The dialog was
cancelled without retry. Read-only database inspection then proved zero
committed commands and action revision, the sole original report generation at
revision0, and the original reference:

- run `7e0999fb-ce04-457b-865e-5bfab1bc4fdb`
- reference `66e9676a-6b29-4ecc-873b-fa8c6b6c27ff`
- reference digest `b23879cc7dc2e17057ddc87afbf74aadc9331005c2873e6fde7e97aaba70ea58`

The source cause is migration0235's registered-placement check:
`BPR.action_revision=H.action_revision`. PostBPR publication BPR is immutable at
its original accepted scope-attempt cut. UptoBPR's action writer records the
command and prepares a current report generation H at the new action cut.
Equality conflates these different owners and rejects the new read reference.
The enclosing transaction correctly rolls the command and derived writes back.

The recommended correction is one exact-body guarded forward migration,
separating the two revisions while retaining all phase/run/registration,
configuration, locator and source-custody checks. Migration0231 already binds
the publication revision to its original scope attempt; migration0228 owns the
live read/action checks. Do not edit applied0235, republish accepted files or
substitute UptoDBM's retained-reference path for UptoBPR refresh.

Before deployment, the correction needs finite reader/recipe compatibility and
an exact consumed0237 schema transition preserving original rows, certificates,
phases, files and action state. The existing transition explicitly qualifies
only unused0232-to0237 namespaces and cannot be used for this consumed fixture.
Prove atomic failure rollback, positive Apply/Sleep and current readback, stale
action/actor and altered-locator denial, plus affected UptoDBM and remark paths.
These are pending proof requirements, not completed tests or a released new
resource/window. No correction was installed during the temporary window.

Because the BPR action exit remains unresolved, PostBPR26, invalid27 and the
independent DBM browser journey were not started. Their prepared scripts remain
inert. Successful reads/downloads do not waive those exits.

## Restoration and bounded resource observation

Replacement window began `2026-10-27T02:32:57.026Z`, with expiry03:32:57.026Z.
It was ended early. Exact original gateway/HBA/PG/MTA restoration completed at
`02:55:02.654959Z`; original MTA readiness returned true. Only the two approved
PG/MTA start times changed. Candidate containers are stopped, original auth and
frontend remained unchanged, and Chrome shows the restored application's
landing page. No further test window is inferred.

Native PG cgroup peak was245,907,456 bytes (about234.5 MiB), with zero observed
OOM events. Maximum sampled ordinary connections was9; sampling does not prove
the absolute connection peak. This is bounded functional evidence, not capacity
or performance acceptance.

## Evidence anchors

`window2-browser-observations.json` records the exact partial-proof boundary.
`browser-sleep-rollback-proof.json` and `browser-sleep-failure-backend.log`
retain the real action failure and typed readback. `window2-auth-browser.log`
and `window2-mta-browser.log` retain request outcomes. Guided/BPR/BTR/MDM PNGs
retain actual screens. `pg16-live-capacity.jsonl`, `window2-restored.json` and
`pg16-restored.json` retain resource/restoration observations. Their SHA256 pins
are in the adjacent `STEP3_BROWSER_EVIDENCE_20261027.json`.
