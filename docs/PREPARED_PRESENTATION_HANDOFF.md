# Retained dataset presentation handoff

The scope is the read-only reporting batch in
[the reporting contract](PREPARED_PRESENTATION_ROLLOUT_PLAN.md).
[MIGRATION.md](MIGRATION.md) is the sole status tracker. This document records
implementation and operational evidence, not acceptance of all F3 workflows.

## Research / RRR / Buffer Trends operations — 5 October 2026

This bounded reader batch uses the retained April7 fixture run
`bfd75b4b-a9df-4a08-82d3-852e3324b623`, source digest
`4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73`.
Full response/CSV evidence and owned build/deploy scripts are outside Git at
`D:/freshvcf-build/evidence/research-rrr-buffer-trends-20261005-001`.
Deployment/acceptance status belongs exclusively to MIGRATION.md.

RRR stores exact rationed/Pick/standard/dimension occurrence references. Research
stores selected-owner/master/history references and a separate physical-history
availability grain. Buffer charts store physical/dispatch graph memberships with
their original LEFT pair multiplicity. Ninety-day values remain in the retained
typed source rows. Normalized owner keys support indexed selection; ordinal joins
retrieve original values without rewriting them. Live scopes, filters, ordering,
UNION-distinct assembly and permission multiplicities remain consumer-specific.

Use the existing owned compose bindings and normal resource caps. The schema
commands permit only their exact additive reporting migration after the earlier
reporting chain:

```text
python manage.py migrate_btr_fixture --rrr-preparation
python manage.py migrate_btr_fixture --history-report-preparation
python manage.py migrate_btr_fixture --research-availability-index
python manage.py migrate_btr_fixture --research-critical-path
python manage.py prepare_rrr
python manage.py prepare_history_reports
python manage.py prepare_rrr --verify-only
python manage.py prepare_history_reports --verify-only
python manage.py prepare_research_availability
python manage.py prepare_research_availability --verify-only
```

Preparation creates absent populations atomically or verifies existing sealed
populations; it never replaces them. The batch's `prepare-compare-batch.py` wraps
both preparations and the strict full-response/CSV check in one transaction,
rolling back the new memberships on failure. Immutable receipts bind source,
dimensions, recipe, row counts and streaming reconstruction digests. A recipe or
source mismatch requires investigation; do not delete a seal or regenerate data.
The independent history-family path is `prepare-history-compare.py`: it validates
all23 frozen Research/Buffer responses before committing that family independently.
`prepare-rrr-ordinal.py` uses the human-approved final occurrence-ordinal tie-break
and proves complete equal-key bags and the global sequence/page partition before
committing RRR. Both harnesses restore the connection's default
transaction mode before the post-commit verifier acquires its validation lock.
Preparation collects statistics on its own membership tables after insertion;
source tables and resource limits are unchanged.

`VF_RRR_PREPARED`, `VF_HISTORY_REPORTS_PREPARED` and
`VF_RESEARCH_AVAILABILITY_PREPARED` are explicit fixture serving flags in the
owned `compose.batch.json`. Preserve the existing RRR activation; its delivery
status remains separate from Research. Defaults are false; unrelated
runs retain native readers. Enabled fixture readers fail closed without their
matching sealed receipt. These flags neither enable business actions nor alter
authentication. Ready-only Research modal loading reuses the existing shared
request identity and response RunDate behavior.

Research's initial grid uses the existing BPR normalized-key index for bounded
page reconstruction. A lateral lookup with OFFSET0 prevents flattening into a
second wide whole-estate scan; it retains every matching occurrence and selected
copy. Availability fields still come from the original physical-history rows,
and live scopes, filters, remarks and final ordering remain unchanged. This SQL
access-path correction adds no schema or calculation state.
Migration0039 adds a covering index for the original physical-history lookup
keys, source ordinal and three availability fields. It avoids loading the wide
90-day history heap for each page occurrence. It changes no values or row grain;
the allowlisted fixture migration verifies unchanged source/admission guards.

Migrations0040–0042 add sealed per-occurrence availability bands, the partial
BPR count-key index and the exact native SKU/location/ordinal Norm Change history
index. Band preparation stores six integer counts per existing availability
membership, preserving97,299 occurrences and exact case-sensitive source codes.
Live permission weights are applied at read time. Full streaming source/prepared
readback is required before sealing; repeat execution verifies without replacing
rows. Separate immutable guards and receipt bind the accepted membership digest,
fixture source and recipe. `research-critical-proof.log` and
`research-modal-index-proof.log` retain migration/source/response and denied-write
proofs. This supplement does not rewrite the existing history receipt or facts.
Research passes requestId, status and response runDate through its shared modal;
the modal opens only after all data is ready and does not refetch the run date.

Before admitting a new image, run Django check, migration drift check/plan, the
allowlisted schema operations and complete comparisons. `batch.ps1 -Action admit`
checks candidate startup; `-Action deploy` replaces only owned3005 MTA/frontend
services at existing caps. Restore any temporary nginx timing configuration
byte-exact after the bounded browser pass. Never use this script to cut over3004,
reload sources, run calculations or change auth services.

## Planning report correction deployment — 5 October 2026

3005 serves backend `freshvcf-preview-mta:planning-report-corrections-20261005-001`
with the existing `planning-grid-latency-20261005-003` frontend. The owned compose
override and build/admit/deploy script are under
`D:/freshvcf-build/evidence/planning-prepared-20261005-001/report-corrections/`.
Startup admission and readyz retain the April7 fixture and admission digest;
deployment receipt verifies22 other containers unchanged and normal backend caps.
No data reload, schema migration, credential or permission change is needed.

GIT To Child Grid View now shows1627 location rows with separately empty
transporter/shipment details. Parent unpaged HTTP reads return complete1030/1443
branches; browser/export continue to use their existing paged requests. Child
receiving chart and expanded103-row table use each receiving location's own label.
Eight broad/restricted authenticated API captures preserve complete reader output.
34 focused tests, complete source/reference checks, browser screenshots and
ordering inspection are retained alongside the deployment receipts.

This is a corrected retained-fixture contract, not legacy failed-query parity.
Nonempty shipment inputs remain unavailable; no positive shipment facts were
invented. Independent full SQL ordering and matched performance dispositions
remain as recorded in MIGRATION.md. Prior passing graph/export/performance proofs
are reused, and the historical modal baseline gate stays deferred/unaccepted.

## Daily Data Graph checkpoint — 5 October 2026

Latest authorized replacement: modern completed modal2.788s versus legacy10.443s.
Both charts and horizon interactions pass with the corrected observer, and all
resource limits restored/errors[]. The2.097s retained modern baseline gate is
not met. Unrelated DBM requests occurred during the window; quiet application
load is not proved. No code/deployment change or further sample. See
`replacement-validation.json` in the evidence root below; MIGRATION.md records
the current disposition. Earlier incomplete observations remain historical.


Scope: DBM Norm Suggestions and BTR row icons only, under
[DAILY_DATA_GRAPH_MODAL_PLAN.md](DAILY_DATA_GRAPH_MODAL_PLAN.md). The implementation
is deployed; **BTR performance acceptance remains open**. MIGRATION.md owns status.

Following the user amendment5October, the handlers clear the prior graph and
keep the dialog closed during the fetch. The full modal opens with response data
and RunDate available; the early loading strip is removed. Existing Redux
modal state carries a request identity; close invalidates it and a newer selection
supersedes it. Completion never reopens a closed modal. Errors remain explicit.
RunDate is formatted from the response's local calendar date; these two flows no
longer request GetLastRunDate on modal mount. Other callers retain that fallback.
The90-day chart inputs are derived once and horizon changes slice the retained
values. First-match duplicates, the inherited year predicate, norm ties, rounding,
suspension bits, tooltips and boundary points remain unchanged.

The fixture-only history reader batches validated receipts within one request,
preserving source/policy checks and ordinary/command-bearing readers. No cache,
index, schema, prepared table, source reload or calculation change was introduced.
The shared modal now has a viewport-bounded panel, a flexible chart and340px
details column, a panel-sized slider, and a bounded scrolling body. Its local
breakpoint zoom is removed. Optional modal/slider props leave other callers' sizing
unchanged. At1280x720 the content scrolls vertically; close remains visible. At
1680x971 and1713x971 all details fit. The original desktop overflow was reproduced
at CSS1713/visual scale1: slider right1395.56 vs panel right1225.25. Screenshot
pixels alone did not establish the user's browser zoom.

Evidence root: `D:/freshvcf-build/evidence/daily-graph-modal-20261004-001`.
`validation.json` consolidates exact comparisons, timings, six layout checks and
five restored resource windows. `backend/native-postdeploy.json.gz` retains full
responses for both selected pairs and restricted scope:58→15 SQL calls and the
same hashes/bytes. Backend21 tests, frontend10 tests and TypeScript pass. Production
build passes with retained lint/Browserslist warnings; the layout detector's ten
Roboto warnings were retained under the unchanged visual-contract requirement.
The old modal tests needed their fixture's actual SKU/location keys and a stable
mock date; earlier failed build/test/observer outputs remain in evidence.

The following timed observations belong to frontend002, before the user
removed early loading. Frontend003 was initially functionally checked; both first-visible modal observations had the eight-series
graph and details, with no loading strip. `ready-opening-functional.jsonl` and
`ready-opening-*.png` retain that proof. These earlier timings remain evidence,
not a new timing claim for003.

| Entry and pair | Before modern | Modern002 | Matched legacy | Former loading |
|---|---:|---:|---:|---:|
| DBM21101138001000/P016_1001 |2.360s|1.227s|9.820s|0.308s|
| BTR21101153051000/P015_1004 |2.097s|3.542s|6.159s|1.152s|

These are individual bounded browser observations at the same14-day horizon,
retained April7 data, broad scopes and matched SQL/PG3GiB/2CPU and API4GiB/2CPU
limits. They are not distributions, cold-start or load acceptance. The first DBM
after observation was1.289s vs legacy5.307s; the permitted DBM repeat verified the
final body-height correction. The first legacy BTR observation ended prematurely
at the observer's iteration cap; its one permitted repeat completed10.177s legacy
and10.889s modern, including an observed401/token refresh on modern. That slow
repeat does not erase the complete2.097s original modern baseline. The initial
DBM shell metric was unavailable because its dialog root had zero height. Initial
layout records selected a hidden chart slider; corrected records explicitly use
the visible modal slider. All raw observations are retained.

**Authorized follow-up and remaining gate:**
The authorized5October follow-up used one deployed003 diagnostic and one final
matched opening pair, with no code change or speculative optimization. Diagnostic:
2.379s to observed chart,2.106s to HTTP completion, no token/date retry. A separate
native profile preserved the exact response and15 queries:0.364s SQL of2.365s
including profiler/first-request initialization. Reader checksum work was
substantial; this does not attribute the serving browser request.
Final modern003 had the selected pair,14-day horizon and eight-series chart at
1.008s (HTTP0.919s), below2.097s retained baseline. This is a chart observation,
not a claim that the modal transition and all interaction work finished then.
The final legacy observer stopped at5.671s while **No data to display** remained:
its predicate only excluded **No Data Available**. Legacy later rendered, but its
exact completion was missed and modern began before that completion was proved.
Therefore the final pair cannot close the required completed comparison.
No further sample is authorized. Preserve the build; a separately authorized
comparison must require populated chart legends, absence of either empty overlay,
and a completed interactive modal. Do not infer another code bottleneck.
Evidence: `D:/freshvcf-build/evidence/daily-graph-modal-20261004-001/followup-validation.json`,
raw traces and screenshots. The subsequent modern horizon interaction passed
and restored14. `validation.json` includes the follow-up evidence.
The browser interruption before the diagnostic terminated its budget controller:
its exact named Windows jobs were absent and PostgreSQL identity/limits were
explicitly restored from the saved receipt, errors[]. The final window restored
normally, errors[]. See `resource-followup-001/budget-recovery-result.json` and
`resource-final-003/budget-result.json`. No graph sample was consumed by that
interruption; no serving services or databases were replaced.

Deployment uses `compose.daily-graph.json` after the existing fixture, portfolio,
BPR, Guided, Guided-export and Guided-corrected overlays. Current tags:
`freshvcf-preview-mta:daily-graph-20261005-001` and
`freshvcf-preview-frontend:daily-graph-20261005-003`. The height correction and subsequent user-requested ready-only opening
deployments recreated frontend only. Rollback tags remain
`freshvcf-preview-mta:guided-corrected-20261004-002` and
`freshvcf-preview-frontend:guided-export-20261004-001`; use the same overlay chain
and `up -d --no-deps --no-build` only for the intended service(s). Backend startup
must finish publication admission before browser checks. No reload/replay is needed.
Selected fixture remains`bfd75b4b-a9df-4a08-82d3-852e3324b623`, date2026-04-07,
BTR generation`e5bdac30-bbd9-45d8-a93d-84a645fad73c`, admission digest
`5c90ae58f6478f7b1805f534f95fbe0de241a5280c4422ec70f28467221bf3e7`.
Users should refresh3005 to load the new bundle; no browser zoom change is needed.
Follow-up restoration is described above. The retained21-container isolation proof and F1/F2,
permissions, source rows, engines and other serving ports remain unchanged.

## Guided Insights fixture preparation and serving

The subsequent whole-page Guided contract is
[GUIDED_PRESENTATION_PLAN.md](GUIDED_PRESENTATION_PLAN.md). Its evidence directory
is `D:/freshvcf-build/evidence/guided-presentation-20261004-001` and its current
browser acceptance status is recorded only in MIGRATION.md. It supersedes the
earlier portfolio batch's history-optimization exclusion for these eleven reads.

Migration0021 adds one typed daily DBM occurrence relation and immutable receipt.
The grain is suggestion × SKU × location × optional pair × master occurrence;
raw keys, NULL equality and source ordinals are preserved. Endpoint-specific
description bags remain live joins. Permissions, parent weights and filters are
applied before aggregation. Native decimal-string attributes remain text so their
MAX and wire behavior match the retained consumer; they are not rounded or
reinterpreted numerically. The retained97097 rows took28.925s to prepare and use
52379648 bytes including indexes and the receipt. Its source binding remains
`4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73`;
prepared row digest is
`b161d0abe38510a463a70882acea6f9717137cea20fea035178a3974d7d21856`.

Append `compose.guided.json` from that directory after the existing base, fixture,
portfolio and BPR overlays. With that isolated configuration, run
`python manage.py migrate_btr_fixture --guided-preparation`, then
`python manage.py prepare_guided_dbm_fixture`. A repeated command verifies the
complete sealed bag without replacing it; `--verify-only --verify-mutation-guards`
checks readback and exact mutation-denial messages. The owned fixture contains
no normal run, so the normal-owner live insertion probe is explicitly unavailable;
the installed guard body is checked and requires LEGACY_UI_FIXTURE/FIXTURE_BLOCKED.
No engine runs or source facts are created by this command.

`VF_GUIDED_PREPARED=1` routes the seven daily fixture reads through the new SQL
paths. Missing DBM receipt/schema/source or altered guards fail closed. Approved
hierarchy supplements retain the existing projected reader. Chronic charts use bounded
typed SQL with their distinct INNER-description grain. The grid correction below
prepares its LEFT-NMS occurrences. Query-local planner settings restore on success
and roll back on failure. The initial history occurrence-count reader preserved
outputs but failed browser latency acceptance. It is replaced by narrow
shared Availability and separate Excess serving ingredients; scope, supported
filters, horizon and minimum age remain live. No permission-specific cache is used.
Frontend request and display transformations remain unchanged.

Deploy only `mta` with `--no-deps --no-build` and wait for `/readyz` admission.
Rollback uses the same first four overlays without `compose.guided.json`, restoring
`freshvcf-preview-mta:bpr-prepared-20261004-001` (immutable image
`sha256:a8733a685bb53c9449dcafb2d2453a0b7b0171214de9655fdab5d4bb45c152fa`).
Retain migration0021 and its sealed rows; the earlier image ignores them. Selected
April7 run, BTR generation, BPR switch, accounts and source facts stay unchanged.

Daily producer integration remains debt: normal accepted publication must supply
and atomically prepare its own daily suggestion occurrences, bind its own receipt,
and prove refresh/retry/retention before this fixture path can be generalized.
This implementation neither schedules refresh nor copies legacy calculations into
accepted F1/F2 state. Complete before/after results cover all11 broad reads and
four restricted family cases; native timings alone are not browser acceptance.

The failed whole-page timing pass prompted a narrower Chronic grid preparation.
Migration0022 adds its own sealed3340-row occurrence relation, built in8.191s,
using1384448 bytes including indexes and receipt. It retains the five original
source ordinals and11 grid output fields, without copying wide filter attributes.
Broad reads use only prepared rows and live permission weights. Supported filters
join only the required immutable source-owner ordinals; parent eligibility remains
live. Exact broad/restricted output, two PostgreSQL differential tests, retry and
seven exact-message mutation guard probes pass. Receipt-insert/normal-owner live
probes are not claimed. Source binding is unchanged; row digest is
`c71e9444fb8e41f256f36aafef1972836dc4d8cd9950a443583e8ab308d5c13f`.
The existing `migrate_btr_fixture --guided-preparation` now includes0022; run
`prepare_guided_chronic_fixture`, or `--verify-only --verify-mutation-guards`
to verify the sealed retained population. No new calculation or source data is
created. The corrected deployment and browser results are in MIGRATION.md.

History preparation uses migrations0023–0026. Apply them with
`python manage.py migrate_btr_fixture --guided-history-preparation`, then run
`python manage.py prepare_guided_history_fixture`. Availability Trend and Ageing
share narrow typed fact × SKU × location × optional pair occurrences. Snapshot
eligibility references use original snapshot ordinals, including duplicate eligible
snapshots; unmatched history remains available to Trend and excluded from Ageing
by its existing INNER eligibility. Excess has a separate importer-owned occurrence
relation. No integer business-key dictionary, per-user cache or per-horizon copy
is introduced. The retained BPR source contains8,483,003 rows, so this is a full
one-time historical preparation rather than a daily97,000-row projection.

Ordinary history SQL equality, source occurrence order and source NULL exclusion
are preserved. Endpoint scope/permission weights, parent filters, arbitrary
supported raw-owner filters, horizon and minimum age remain live. Broad reads
avoid rebuilding stable source joins; filtered owners are reached by original
ordinals. The explicit fixture switch and source/schema/guard checks gate these
readers. Normal publication and approved hierarchy projection retain their prior
paths. A repeat or `--verify-only` streams and verifies both sealed families and
the snapshot references; it never replaces an existing sealed population.

0024 records the explicit correction to the initial0023 guard/receipt contract.
0025 moves repeated fixture/seal checks to a statement trigger under the owned
run lock, retaining a cheap per-row run-identity check and immutable-row guards.
The first two uncommitted attempts were stopped for NULL-join correctness and
repeated row-guard cost respectively; their absence of committed rows was checked.
The completed build took1700.176s under1GiB/1CPU and committed8,483,003
Availability rows plus97,299 snapshot references and920,774 Excess rows.
Before the covering-index correction, their total relation sizes are respectively
1,940,742,144,43,376,640 and213,090,304 bytes. Availability's complete digest is
`45cbc4e841ed23ca81f66fc80d45c542a21ad89324f80c3d54e196ad9e2e15c0`;
Excess is`6376cf626c560a7e3a0f64a6854ba0340413bb94e427ee404101cc0ad8427095`.
Build, storage and configured-output evidence is retained in
`D:/freshvcf-build/evidence/guided-history-prepared-20261004`.
0026 adds the840,966,144-byte`fresh_guided_avail_cover` index on run/date,
including the permission codes, location type, colour, source order and snapshot
anchor needed by both broad Availability reads. Raw-owner filters still use
their original source-ordinal joins. The index changes no stored values and can
remain installed when reverting application code. Its observed build wall time
was approximately209s, separately from the1700.176s historical row preparation.
Daily incremental preparation, producer integration and retention remain future
work; no scheduler or production calculation boundary is changed here.

Guided XLSX export uses an explicit opt-in on the shared chart-table component;
unrelated Planning/MTO callers retain their previous handler. Guided chart tables
and the Chronic toolbar obtain AG Grid's workbook blob synchronously and trigger
a native anchor click during the user's click task. This avoids the asynchronous
compressed-download path implicated by the failed clicks. The workbook is an
uncompressed ZIP, so file size increases; there is no new server transfer.
The scoped frontend image is `freshvcf-preview-frontend:guided-export-20261004-001`,
`sha256:893c1672179651413144cf1ac3a95d5414313ec3c8339cbb3c68204fde53e7ac`.
Append `compose.guided-export.json` after the existing overlays and recreate only
frontend with `--no-deps --no-build`. Its limits remain128MiB/0.5CPU, restart=no.
The user confirmed DBM location export after refresh. The retained80,368-byte
workbook is a valid uncompressed XLSX and all129 rows ×25 columns match the
retained response in displayed order (`dbm-location-xlsx-validation.json`).
The in-app browser still cannot capture this download. Four focused helper/
component tests cover the Guided opt-in and unchanged shared default. The user
also confirms Chronic grid XLSX downloads. Its file was not independently located
for cell validation. The separate Chronic location-chart workbook is65,323 bytes,
with all91 rows ×26 columns matching the retained response; these are distinct
evidence claims in`export-runtime-validation.json`.
For frontend rollback select the prior immutable image
`sha256:37643d580475db6fac763bad2c9a091afbfebc52cd62f17d66a3e912ff5fbb7f`
and recreate only frontend with the same configuration.

The final correction appends`compose.guided-corrected.json` after
`compose.guided-export.json`, retaining all earlier base/fixture/portfolio/BPR/
Guided overlays. It selects`freshvcf-preview-mta:guided-corrected-20261004-002`,
immutable image`sha256:7b31f6da2c336301e26729ed3599434d051f965d1effa31dbbd3fc4a2229626d`.
Recreate only MTA with`--no-deps --no-build`. Its unchanged full startup
admission takes minutes on the heavy fixture; wait for`/readyz` before sending
consumer requests. Do not weaken admission or treat that startup interval as
request latency. Final readiness reports the original admission digest.
The service remains4GiB/2CPU, restart=no, with no host-port mapping.

To revert only the corrected history/grid backend while retaining the passing
first Guided batch, omit`compose.guided-corrected.json`; the previous image is
`sha256:b2a4baa2c5fe5b0f5d8414af85e70ffea121e57c287f06abd57a90fce552b16e`.
Retain all additive prepared tables/indexes and existing fixture rows. The
pre-Guided rollback described above remains available. Neither rollback changes
accounts, source data, accepted calculation state or the BPR/BTR selections.

Final evidence includes`deployed-corrected-proof/corrected-exact-comparison.json`
(eight complete affected broad/restricted responses),
`browser-corrected-trials.jsonl`(24 completed screens),
`browser-corrected-request-correlation.json`(all12 modern request windows),
`browser-corrected-legacy-correlation.json`(all12 legacy windows),
`browser-corrected-medians.json`and`resource-window-final-003/budget-result.json`.
`guided-final-validation.json` consolidates the bounded result and its limits.
The retained failed landing-heading click is separately identified as navigation
instrumentation failure. It did not initiate a report request. No completed
report observation was replaced. Resource restoration has no errors;21 other
retained serving containers are unchanged. Final age2/horizon8 browser evidence
is`corrected-age2-horizon8.txt`and its screenshot.

History full-stream repeat readback reproduces both sealed digests. Seven
rolled-back mutation probes reject sealed insert, row update/delete/truncate,
snapshot update and receipt update/delete without changed counts. Receipt-insert
and normal-owner live probes are not claimed. Prepared history PostgreSQL2/2,
fallback5/5, Django/schema/migration-enabled checks and production builds pass.
The four frontend export tests pass; the TypeScript check retains the same three
pre-existing useBTR errors. Existing independent legacy ordering differences and
daily producer integration remain explicitly bounded residuals in MIGRATION.md.

## BPR fixture preparation and serving

The bounded BPR correction uses the same April 7 run
`bfd75b4b-a9df-4a08-82d3-852e3324b623`. Evidence is in
`D:/freshvcf-build/evidence/bpr-ui-performance-20261004-001`.
Migrations 0019/0020 add one typed native candidate relation and an immutable
receipt. It retains all six source occurrence ordinals, raw filter/display
owners, nullable standard presence, unrounded numeric pens and normalized
lookup keys. Permissions, filters, parent multiplicity, key-bag paging,
latest remark ties and trend availability remain live. Count and analytics
retain their separate grains. Calculation state and the export reader are unchanged.

With the existing base, fixture and portfolio Compose files, append
`compose.bpr.json` from this evidence directory. Run `python manage.py
migrate_btr_fixture --bpr-preparation`, then `python manage.py prepare_bpr_fixture`.
Both are bounded to the owned fixture. Preparation is atomic and refuses partial
or mismatched existing rows. Repetition verifies the complete typed digest;
`--verify-only` cannot insert. The retained preparation produced 97,097 occurrences
in 75.44 seconds including container startup, using 65,232,896 bytes including indexes
and receipt. The source binding is unchanged. INSERT after sealing, UPDATE,
DELETE and TRUNCATE are denied. No normal run or engine publication is prepared.

`VF_BPR_PREPARED=1` explicitly enables only fixture grid/count/analytics and the
retained AdminBPR configuration. The latter restores all 29 canonical column
definitions instead of the older 19-column static UI projection; ordered values,
types and NULL omissions match the authenticated canonical API. Normal-publication
configuration and export behavior remain unchanged. Missing source/schema/receipt,
altered guards and unsupported hierarchy opt-in fail closed. Query-local JIT-off
avoids measured compilation overhead and restores the caller's setting on both
success and failure. It is not a PostgreSQL-wide setting change.

Deploy only `mta` with `--no-deps --no-build`, then wait for startup admission and
`/readyz`. Roll back to the prior portfolio MTA image
`sha256:12568efc81d6b15af95e693b7c1f7f1667bff5d05154e0d0b230625060f0c027`
using the base/fixture/portfolio overlays without `compose.bpr.json`; the old
reader ignores this additive relation. Retain its rows and migrations on rollback.
Do not reset source data, accounts, F1/F2 or the unchanged BTR generation.

Future daily publication remains explicit debt: connect this finite preparation
to accepted daily outputs and prove refresh/retry/retention before enabling it
for normal publications. This one-time fixture loader is not a daily scheduler
or acceptance of that later producer integration. Current browser performance
status and the bounded three-pair result belong in MIGRATION.md.

## Implementation

The existing immutable April 7 fixture and BTR reporting generation are reused.
Research reads selected pairs and their existing relatives instead of rebuilding
the whole publication. Guided history uses scoped, date-bounded SQL over typed
history. Exact-key occurrence indexes replace repeated Python scans without
normalizing or deduplicating source rows. Current Excess reads select the date
before transferring history. Native remarks and populated custom Expedite now
use their retained source contracts. No calculations or accepted F1/F2 state change.

The frontend removes duplicate Guided request ownership and Buffer Trends array
processing. Research and Planning settle independent count/grid requests together.
Pagination, request bodies and source value transformations remain unchanged.

Migration 0018 adds `fresh_guided_history_date` on run/image/ReportDate with covering
history fields. It was applied with the existing atomic `migrate_btr_fixture
--guided-history-index` command, preserving fixture binding and metadata guards.
It adds 875732992 bytes. Django check, migration drift/plan and physical PostgreSQL
verification passed. No pending migrations remain on the retained fixture.

## Correctness evidence

External evidence directory:
`D:/freshvcf-build/evidence/prepared-portfolio-20261004-001`.

- Seven full-population Guided lookup comparisons preserve every field,
  occurrence and order (`lookup-comparison.json`).
- Twelve Research/historical/Guided/Excess comparisons cover broad/restricted
  scopes and nine-/three-day windows (`source-comparison-summary.json`).
- Current-date Excess matches 9871 rows from the prior full-history read;
  populated custom Expedite matches 1030 canonical-query rows.
- Three PostgreSQL SQL differential tests and 52 focused backend tests pass.
  The existing unrelated two Expedite fixture-mock failures remain documented;
  this is not a claim that the historical entire suite passes.
- TypeScript, four request-pair tests, production backend/frontend builds and
  pinned baseline identity verification pass.

The single post-index plan replaces the 30.8-second history scan with a 176.7ms
index-only scan per worker and zero heap fetches. The whole query still takes
14.277 seconds because joins/sorts remain. This is not click-to-usable-screen
performance acceptance or a claim of legacy performance parity. Further history
optimization is outside this batch's approved correction.

## Explicit upstream dependencies

Planning overview/GIT cannot be represented as an empty result: the fixture has
2567 positive-GIT rows but lacks GoodsInTransitMaster. Dependent Expedite parent
grid/chart paths lack BPRMaster. Those consumers must retain attributable 503
responses. Available Excess, Fulfillment and custom Expedite are assessed
independently. No source reconstruction or new workflow is implied.

## Deployment and rollback

The deployment uses existing `compose.preview.yaml`, the retained
`stage2-vm-dataset-20261003-002/compose.fixture.json`, and this evidence directory's
`compose.portfolio.json`. Only mta and frontend are recreated with `--no-deps
--no-build`; authentication, MTO, PostgreSQL and other serving stacks stay intact.
Wait for `/readyz` before route checks: immutable BTR startup validation precedes
the listener and is not instantaneous.

Rollback uses the prior `btr-typed-reader-20261004-001/compose.typed.json` overlay
with the same base/fixture files. The additional index is compatible with that
reader and need not be removed to roll back application code. Never reset data,
weaken admission, change accounts or reverse accepted F1/F2 state for rollback.

Authenticated runtime and browser results are recorded at the bounded inspection
exit in MIGRATION.md and the external evidence directory.

Deployment receipt: backend image
`12568efc81d6b15af95e693b7c1f7f1667bff5d05154e0d0b230625060f0c027`,
frontend image
`37643d580475db6fac763bad2c9a091afbfebc52cd62f17d66a3e912ff5fbb7f`.
Startup admission remains
`5c90ae58f6478f7b1805f534f95fbe0de241a5280c4422ec70f28467221bf3e7`.
All 21 protected running container identities are unchanged; mta remains 4 GiB,
2 CPU, restart=no, without host ports. Frontend remains loopback 3005 only.

`gateway-deployed/summary.json` records 23 expected statuses, with full compressed
response bodies: 20 successful reads including a restricted trend, two attributed
503 dependencies, and one unauthenticated 401. Two additional Planning graph
responses also completed 200. The preliminary `gateway-before-ready` failures
were sent before the startup listener existed and are retained as failed
orchestration, not included as successful application evidence.

Observed broad Guided trend/age requests took 15.06/23.19 seconds, and other
Guided requests also remain slow. These single observations overlapped bounded
browser inspection and are not controlled performance measurements. This batch
does not establish minimum latency or superiority to legacy.

Research renders 5000 of 97097 rows and selected history summaries. Its inherited
calendar initially opens the system month (October) while the fixture is April;
the existing DayPicker has no publication-month binding. Treat that display issue
as an explicit residual, not data loss or a reason to modify retained dates.

The bounded browser pass verifies Research selection/history, Guided trend and
Chronic tab transition, Buffer Trends Show All/30-day seven-series chart,
Planning Excess chart-to-grid with 5000 of 9871 rows, BTR 5000 of 97299,
RRR 5000 of 8063 and DBM 5000 of 11158. Screenshots and DOM receipts are retained.
Fulfillment/custom Expedite and remarks have complete authenticated API/source
proof; their every browser interaction was not independently exercised. Existing
export proofs are reused because their producers/contracts did not change; no
fresh export or write-workflow acceptance is claimed.

BPR also rendered its configured50-row page of97097. Desktop visibility was
verified at1280x720 (`browser-bpr-desktop.png`), then the temporary viewport was
reset. The other retained screenshots use the default narrow browser viewport;
DOM receipts establish their loaded data, not responsive-layout acceptance.


## Daily Data Graph selected-scope correction,5October2026

Current backend: `freshvcf-preview-mta:daily-graph-scope-20261005-001`, image
`sha256:30edcdbf605853f17c8912ad5114b65f5142d4150513c4302cb433d5af3b03bc`.
Frontend remains `freshvcf-preview-frontend:daily-graph-20261005-003`:
full modal opens after response readiness, without the thin loading strip.
Selected fixture/run/admission unchanged. Normal Gunicorn, no profiler;
backend4GiB/2CPU, restart=no, no host ports.

Deployment: external `daily-graph-modal-20261004-001/deploy-scope.ps1` without
`-Profile`, retaining base, fixture, portfolio, BPR, Guided, export, corrected
Guided and Daily Graph overlays, then `compose.scope.json`. Recreate only mta;
wait for readyz200. Rollback uses that chain ending at `compose.daily-graph.json`,
omitting scope and scope-profile overlays. Do not reset data or other services.

24 focused tests pass; independent review has no findings. Both selected full
responses and restricted response are byte-exact in `backend/scope-deployed.json.gz`.
Final matched BTR: chart-ready1.843s, settled2.169s; legacy11.888s.
Both horizon controls work. Token renewal occurred inside modern's measurement
and is included. Retained2.097s baseline missed by72ms; performance acceptance
remains unmet. All caps restored without errors; temporary viewport reset.
`scope-validation.json` consolidates proof and limitations. No further sampling
under the one-pair amendment; MIGRATION.md remains the only status tracker.

## Planning prepared delivery, 5 October 2026

The Planning additions preserve the April7 fixture run
`bfd75b4b-a9df-4a08-82d3-852e3324b623`, source digest
`4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73`
and admission digest
`5c90ae58f6478f7b1805f534f95fbe0de241a5280c4422ec70f28467221bf3e7`.
Database: `test_freshvcf_stage2_vm_20261003_002`. No engine replay is needed.
The consumer grains are fixed in PLANNING_CONSUMER_MATRIX.md; current acceptance
and precise unresolved dependencies are exclusively in MIGRATION.md.

Migrations0027–0035 add sealed typed source/display/occurrence relations;
0036 adds the Excess run/date covering index. Existing source rows are unchanged.
Preparation commands, in dependency order, are `prepare_planning_sources`,
`prepare_planning_grids`, `prepare_planning_charts`, `prepare_planning_custom`,
`prepare_planning_git`, `prepare_planning_expedite_grids`,
`prepare_planning_expedite_transit`, `prepare_planning_expedite_custom`, and
`prepare_planning_expedite_charts`. Each supports `--verify-only` and binds the
configured fixture and immutable receipt. The existing fixture is already prepared:
use verification when operationally needed, not a reload. Normal fresh databases
use real Django migrations; this sealed fixture uses the exact forward allowlist
in `migrate_btr_fixture`. Never fake history or disable source guards manually.

The earlier latency checkpoint used `planning-grid-latency-20261005-003` for
backend/frontend. The final backend and operational overlay are recorded below.
The final frontend caller repair has immutable image ID
`sha256:725f04d6d8b9117188bea286fdb28d33b4730c2371d311ad357a4d337b01637c`;
the tag was rebuilt, so use the retained deployment receipt for exact identity.
External operational scripts are under
`D:/freshvcf-build/evidence/planning-prepared-20261005-001`:
`deploy-planning-latency.ps1` retains the existing overlay chain and deploys only
the owned backend/frontend; `deploy-modal-caller.ps1` deploys frontend only.
`check-latency-deploy.py` verifies readiness, selected admission and21 protected
resources. Keep existing ports, restart policy and resource limits. Rollback only
the affected image using the retained connected/latency image checkpoint; leave
additive prepared rows/indexes and source data intact. Do not reset the database.

Evidence includes complete source/storage/reader comparisons, scoped cases,
`latency003-api-summary.json`, corrected-grid screenshots and
`fulfillment-modal-final.txt/.png`. The latter proves selected SKU21125076009000
at P064, real chart data and14→30day horizon. API timings are not browser timings.
Observer failures and the8.192s modal observation remain retained and unaccepted
as performance proof. User-confirmed Excess/Fulfillment graphs and XLSX exports
are reused. Daily refresh automation remains outside this one-time preparation.

The human-authorized focused extension on5 October supplies valid modern
usable-screen observations: Excess3.058s,Fulfillment5.058s,selected modal1.322s.
See `planning-prepared-20261005-001/performance-extension/consolidated.json` for
request correlation and resource restoration. Existing5000-row pages and totals
are preserved. These are automation upper bounds, not matched legacy grid gains;
legacy chart-entry timings are not equivalent reference journeys. The failed
Excess observer/casing check is retained separately. No application code or image
changed during this investigation; temporary nginx instrumentation was restored
byte-for-byte and both resource windows report RESTORED with zero errors.

## Final Planning operational handoff, 5 October 2026

The finite April7 six-destination batch is delivered on3005 with its exact approved
report/order exceptions. The user currently confirms all Excel downloads and
instructs no further exploration. Reuse that confirmation, the accepted graphs
and the retained full-response proofs; no new export/benchmark campaign is needed.
Current status and the six-destination matrix are exclusively in MIGRATION.md.
This does not accept other-date/positive-shipment behavior, action workflows or
the deferred historical Daily Data Graph baseline.

Final backend: `freshvcf-preview-mta:planning-report-corrections-20261005-001`,
immutable image `sha256:fb08d8e5ede9ec7fde36e432836d3db5d1c44b0a2e34c948c79b3513127acaf4`.
Frontend remains `freshvcf-preview-frontend:planning-grid-latency-20261005-003`,
immutable image `sha256:725f04d6d8b9117188bea286fdb28d33b4730c2371d311ad357a4d337b01637c`.
`report-corrections/deploy-receipt.json` proves admission, readiness, unchanged
ports/restart/caps and22 protected containers unchanged. Backend4GiB/2CPU,
two workers, restart=no, no host mapping; only the existing frontend3005 endpoint
is exposed. PostgreSQL returns to its normal1GiB/1CPU budget. All comparison
windows restored without errors; nginx was restored byte-exact.

Use `report-corrections/deploy.ps1 -Action deploy` only for an authorized redeploy
of this checkpoint; it retains the complete existing overlay chain and changes
only the owned MTA service. Its `build`/`admit` actions are separate. Do not run
deployment or preparation merely to consume the already-serving fixture.
For a coordinated rollback, use the earlier latency003 backend image from
`deploy-latency-receipt.json` with the same fixture/portfolio/BPR/Guided/modal
overlay chain, omitting only the final report-corrections image overlay.
Retain the current frontend unless its caller change is separately rolled back.
Recheck readyz/admission after any authorized rollback; that earlier backend
restores the known child-GIT/unpaged-Parent/label limitations. Leave additive
prepared rows/indexes, sealed source data and other services intact.

Preparation is already complete and source-bound. The nine commands listed
above are the repeatable one-time loader path, not a daily scheduler. Use their
`--verify-only` mode when verification is operationally required; never change
the fixture run/date/source/admission to load a different population implicitly.
Retained build costs (single functional observations, not throughput guarantees):

| Preparation | Population | Recorded seconds |
| --- | --- | ---: |
| Sources | BPR97097 / GIT2567 |14.535 |
| Normal grids | Excess9871 / Fulfillment12720 | Sealed load/readback retained; no total inferred |
| Excess/Fulfillment chart grains |65694 members /6068 displays |29.58 |
| Excess/Fulfillment custom |9871 /12720 |12.07 |
| GIT locations |1627 |0.47 |
| Expedite grids |6249 across four grains |2.09 |
| Parent nested transit ingredients |97100 bases /5 matches |9.87 |
| Expedite custom |1030 |0.78 |
| Expedite chart/prepost |15713 members /2416 pairs |7.82 |

Source/grain map: PLANNING_CONSUMER_MATRIX.md. Preparation/storage and mutation-
denial proofs, Django migration checks, builds and complete reader comparisons
are retained under `planning-prepared-20261005-001`; no source roster was replaced
by a derived receipt. Migrations0027–0036 are real applied migrations, not faked.
Current-reference proofs cover broad/restricted, meaningful filter/page and
affected NULL/duplicate/order behavior; native SQL/DLL proofs are additionally
retained for the qualified sources, Expedite charts and broad/restricted Parent.
Do not describe this as all-endpoint independent legacy HTTP parity.

`acceptance-continuation/consolidated.json` closes the bounded matched observations;
`performance-extension/consolidated.json` supplies the modern Excess/Fulfillment/
selected-modal request attribution. Parent grids remain relatively slow, while
improving over their retained legacy observations. These single automation upper
bounds do not establish percentiles or minimum possible latency. No passing
journey needs resampling. Fulfillment legacy grid was loading at55.1s and observed
ready by89.611s; its exact completion remains unknown.

Remaining dependencies are precise: real April shipment inputs are empty, so
positive transporter/shipment behavior is unproved; inherited invalid Norm/filter
SQL stays explicitly denied; daily publication/refresh/retry/retention integration,
request/action workflows, other datasets and3004cutover remain separate work.
The historical modal baseline is deferred/unaccepted. None requires a new dataset,
calculation replay, permission change or further work in this closed bounded batch.
