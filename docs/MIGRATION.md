# Fresh VectorFLOW migration — current baseline

Baseline date: 3 October 2026. Implementation checkpoint: `2d0cfde95606aef58a486e186bde1558802ef542` (pushed).

## Authority and current instruction

This is the **only migration status tracker**. Whole-page implementation remains
**PAUSED**, not complete. The separately authorized Stage2 dataset preparation
and bounded four-page availability correction are complete for the scope below:
RRR/BPR/BTR/DBM populated browser grids, counts, local filters and restricted reads
on3005. Engines, accepted F1/F2 state, replay, authentication permissions, other
pages and Stages3–5 were not changed. The isolated fixture remains serving after
window008's successful admission, security and protected-resource checks.

The previous 4,286-line tracker is preserved byte-for-byte in [the historical snapshot](archive/MIGRATION_2026-10-03_2d0cfde.md), SHA256 `a913419e34a3318d7ca09f11b163295c9d695b55d99e3060e87c23fadc84242b`. It contains provenance and exact earlier approvals, **not active instructions or a second queue**. Do not load the whole archive routinely; consult the relevant passage only when an unresolved contract requires it.

Current human instructions and applicable repository constraints govern execution. This baseline records their current status; it does not broaden an approval or waive a source contract. Historical “active”, “pending”, “unpublished”, “continue” and old outage statements do not override this baseline. Supporting plans describe contracts, not current authorization.

## Objective and architecture

Port the canonical deployed MTA behavior into Django/Python and PostgreSQL, connecting the retained frontend, authentication and direct-port MTO. Deliver a runnable application with calculation/state parity, correct presentation and complete application acceptance. SQL Server/.NET remains the independent validation oracle, not a modern production calculation dependency.

Canonical authority: deployed DLL/BAT/SQL/config at `F:/VFlow_Local/local-runtime/mta-engine` and `mta-latest`, preserved at `F:/VFlow_Source_Backup/deployed-demo/MTA`. API DLL SHA256: `0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346`. Pins are in `baseline/manifest.json`. Recovered source is authoritative only where matched to that deployment.

`execute_day` remains the production day boundary. Operational state, histories, actions and consumer projections are typed PostgreSQL rows linked to run identity, preserving duplicates and source order. JSON metadata or trace blobs do not replace operational state. MSSQL and PostgreSQL physical schemas must not be assumed identical.

## Programme status

### Four-page visible-data delivery — PASS; fixture serving on3005

The direct human instruction in this chat authorized closing only the current
3005 availability blocker. Window008 completed that bounded exit on3 October2026.
Full page implementation remains paused. This is visible dataset availability,
not whole-page, Stage2, F3, engine parity or matched performance acceptance.

Reused the sealed April7 VM dataset, existing typed consumer schema, mapping,
loader, fixture admission, page contracts and all unaffected proofs. No source
extraction, reload, engine/replay/F1/F2 mutation or permission change occurred.
The BTR execution plan showed repeated full scans/sorts of97k-row relations.
Seven exact normalized join-expression indexes were added only to the owned
fixture database; the fixture-only `enable_nestloop=off` override was removed.
SQL predicates, parameters, bags, values and ordering are unchanged. Full sampled
tech/eco responses and counts equal the retained slow result. The index tool
validates manifest/database, exact index definitions and frozen identity.

| Page | Browser population | Local SKU filter | Restricted API count |
|---|---|---|---|
| RRR |5000 of8063 |11 rows for21101151051000 |809 |
| BPR |50 of97097 |1 row for23102164028000 |5076 |
| BTR |5000 of97299; both inventory views |Retained21101050051000 rows |5082 in each branch |
| DBM |5000 of11158 |13 rows for21101149051000 |1036 |

Real broad-account browser login, navigation and filters passed. All four
restricted count/grid APIs returned200; forged scope did not expand any count.
Concurrent authenticated BTR requests at the actual5000-row page size returned
200: both grids35.965s and count42.903s, below the unchanged60-second gateway.
Peak MTA memory was2.20GiB with zero OOM events. Seven focused BTR tests passed;
Django check, migration drift check and migration
plan passed (no model migrations). Independent bounded review found no blockers.
No claim replaces the retained broader suite's two pre-existing Expedite failures.

403 attribution: normal `fresh.preview@vectorflow.local` is intentionally absent
from fixture policy and returns `fixture_actor_scope_denied`; dedicated broad/
restricted actors pass. The frontend's existing forbidden-page navbar can repeat
GetAllReports after a403, masking that cause. Window007 lacks actor identity, so
its human session cannot be retrospectively attributed. Window008 proves the
supported fixture accounts work, normal/unauthenticated access remains denied,
and Apply/Sleep remain disabled. No authentication/permission bypass was added.

Current service: isolated April7 fixture on3005, dedicated read/layout actors
are enabled. Use `stage2.broad@vectorflow.local` (or the restricted actor); retrieve
its existing password from the local fixture secret file identified in the
handoff. Ordinary preview accounts are not fixture accounts. Protected services,
accepted publication and existing grants passed the window's unchanged checks.
F1/F2 engines/state, other pages and Stages3–5 remain outside this delivery.

Current consolidated proof:
`D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002/visible-availability-validation.json`.
Window008 retains browser text/screenshots, scope/security and concurrent gateway
receipts, runtime resource evidence and `serving-handoff.json`. Windows001–007
and the former blocked consolidated receipt remain preserved. To restore normal
June17 and disable the fixture actors:
`D:/freshvcf-build/venv/Scripts/python.exe tools/stage2_fixture_window.py restore --attempt 008`.

### Bounded Stage 2 dataset preparation — consolidated consumer blocker

The human supplied VM-extracted backups at `E:/vflow_backup_dump` in the review
chat on 3 October 2026. Active work now verifies/freezes/restores the available
Importer/BPR/BTR originals in **new** owned resources and prepares their staging
and mapping independently. The human subsequently confirmed DBM copying complete;
its stable original was hash-pinned and restored separately after preserving an
interrupted capture. All four API sources share 7 April 2026 LastBatchRun dates.
Interface/IntermediateDB/Vendor/Distributor are conditional source dependencies,
not automatic readiness gates; any required missing input must name an actual
Stage 2 consumer. None may be borrowed from synthetic sources. Exit remains
dataset readiness or a consolidated evidenced blocker. Required proof includes
hashes, usable restores, source dates/identity/coverage, bounded capacity, typed
bulk readback and actual consumer mappings. No engine, accepted-state, permission,
serving or page changes under the initial scope. The existing app goal is active.

**Bounded authorization amendment (3 October 2026):** verified human instruction
in command-centre chat `01a100e2-7943-7102-9760-62d9e492ecd9`, turn
`01a100e3-6258-7bf1-a9d0-f191636ed24f`, authorizes its relayed grant: dedicated
local fixture actors through existing account/auth mechanisms, new actor-owned
MTA read/navigation and layout grants using the original 9-product/60-location
catalogue; preserve source IDs, NULL/empty semantics and existing accounts/grants.
No VM passwords/sessions or invented memberships. Catalogue collisions require
isolated fixture configuration/storage. Implement only explicit fixture admission
and representative real authenticated API reads/scope denial. If needed, switch
only MTA on3005 temporarily after recording image/config/database/publication and
exact restoration; restore June17/catalogue/actions-disabled on every exit and
prove protected resources unchanged. Preserve gateway/frontend/auth/MTO services.
Fixture accounts must have no normal-publication access and be disabled outside
the test window; credentials remain outside Git/logs. Keep4GiB/2CPU/two workers/180s/
restart=no. Engine changes/execution, F1/F2 mutation, business actions, page-by-page
work, performance campaigns and Stages3–5 remain excluded. Active exit remains
dataset readiness or a precise additional blocker; no new queue.

**Bounded preparation stopped at a consolidated blocker; dataset readiness is
withheld.** All303 source tables /91,645,123 rows are preserved. The73-table
Stage2 union /56,500,041 rows passed full staging readback;60 consumer images
/52,760,538 rows and six projections /965,475 rows passed full typed source/target
comparison. Manifest `afe42593ca2abdf5e2395433ac70834723f4eac1dfa5a2982192c7688906b836`
is sealed. Database `test_freshvcf_stage2_vm_20261003_002`, fixture run
`bfd75b4b-a9df-4a08-82d3-852e3324b623`, remains explicitly non-production.
A zero-insert retry passed;396 relations are immutable. Three fixture-owned
pair-history indexes preserve the same frozen identity.

Window004 proves native DBM counts11158 broad /1036 restricted, populated grids,
forged-scope non-expansion, a populated history drill-down, Apply/Sleep403 and
normal-preview-actor403. Research/historical-availability/BPR/remarks/Planning
Expedite remain explicitly503. Existing accounts/grants are unchanged. Both
fixture actors are disabled, real login denial is proved, and normal June17
image/configuration/admission plus all protected services are restored.

**Blocking contract:** existing `RRRDataCount` over this native population
returns gateway504 after60seconds (windows003 and004). RRR grid, BTR and
fulfillment checks following it were not executed; do not claim their acceptance.
Further RRR presentation-query diagnosis/correction is a separate authorized
boundary, not page implementation or an engine change. Other declared native
ancillary/history adapter gaps and39 static UI metadata differences remain in
the handoff. No timeout increase, API assertion waiver or performance campaign.

Earlier windows are retained:001 exposed the fixture DBM quadratic join;
subject-bag partitioning now uses the unchanged selector and passes exact
bag/NULL/missing/accepted/predicate equivalence.002 exposed pair-history scans;
owned indexes resolved that check (window003 history200 in4seconds). All four
windows restored normal service.37 focused tests pass; the broader19-test HTTP
suite retains exactly two pre-existing Expedite failures. No engine execution,
F1/F2 mutation, replay, frontend implementation or Stages3-5 work occurred.

Consolidated receipt: `D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002/dataset-validation.json`
(`BLOCKED_CONSUMER_READINESS`). Manifest, mappings, repeatable loaders and exact
operation/restoration steps are in [the operational handoff](STAGE2_DATASET_HANDOFF.md).
The requested stop-at-readiness-or-blocker boundary is reached; no adjacent work
is active. Page implementation remains paused.

The following describes the preserved, superseded first candidate:

On 3 October the human corrected source authority to `F:/VFlow_Source_Backup`
in review chat `01a0f7c6-1050-7741-b80a-a7f10ca0d04d`. No original populated
SQL backup set was found in the bounded preserved-source inventory/MTA archives;
its reconstruction runbook says databases were not copied. The local Demo
runbook explicitly identifies its 1,240-row population as synthetic reconstruction.
Matching database names did not establish original-data lineage.

Before the correction, eight checksum-verified local Demo backups were restored
to owned read-only `VFTEST_Fresh_S2_20261003_001_*` clones. 523 tables / 280,651
rows passed full typed staging readback in owned PostgreSQL database
`test_freshvcf_stage2_dataset_20261003_001`; 102 consumer images and six projection
families were copied and fully read back. The consumer transaction finished before
the stop took effect. All are preserved as quarantined evidence, **not dataset
readiness**. Fixture partition `f9db3dfc-efc3-488d-af2f-a88e8b2c68ee` is
`LEGACY_UI_FIXTURE/FIXTURE_BLOCKED`, with no engine success, parity receipt,
checkpoint, command or production manifest. No fixture admission/serving change
was implemented. All three loader entry points now fail before source/database
work pending reconciliation; no environment override is provided.

Additional observed limits of that rejected candidate: native `LOCAL_ALL`
hierarchy matches zero unchanged modern permission memberships; Suggestions,
SuggestionsLog and RationingHistory are empty; BTR BPR has one date; source
OrderIdentity is absent. Do not transfer these findings to the missing original
data. No engines, accepted F1/F2 rows, authentication permissions, serving services
or page implementation were changed. Scope ends at this consolidated blocker.

Handoff: [Stage 2 dataset handoff](STAGE2_DATASET_HANDOFF.md). Evidence:
`D:/freshvcf-build/evidence/stage2-shared-dataset-20261003-001/`, especially
`source-reconciliation.json`, `dataset-manifest.json`, `mapping.json` and
`staging-validation.json`. Resumption requires the original populated source set
and API/engine suffix reconciliation, or an explicit human change of source scope;
use separately owned replacement resources and retain this candidate.

| Boundary | Current assessment |
|---|---|
| F0 Foundation | Complete for the registered foundation scope. |
| F1 Current-day MTA | Complete for selected registered contracts; not universal customer/branch coverage. |
| F2 Temporal MTA | Complete for selected registered 12-day scope with declared Norm0 occurrence-text flaw: 360 strict passes and 12 narrowly qualified report contracts. Norm0 text is not parity. Day 12 peak 3.10 GiB; terminal relational/readback proof passed. No further F2 recovery queue. |
| F3 recovery Stage 1: connection/admission boundary | Accepted at pushed `52f2ff5` (implementation `26158a6`). Retain accepted inventory and admission proof. |
| F3 recovery Stage 2: connected reporting journeys | **Incomplete; paused at `2d0cfde`.** Implemented and verified portions below are not whole-page acceptance. |
| Stage 3: operational reports/logistics | Not opened under the Stage 2 authorization. Reassess after Stage 2. |
| Stage 4: workflows/master data | Not opened, except the completed bounded DBM action validation amendment. Reuse that proof later. |
| Stage 5: combined runtime/MTO/final acceptance | Not opened. Final application acceptance and any 3004 cutover remain outstanding. |

## Stage 2 page ledger

These are the remaining obligations, not parallel work queues. Guided was the active page at the stop. On an explicitly authorized continuation, finish or give an evidenced disposition for one whole page before independent next work. A recorded blocker permits independent progress; it does **not** make that page complete or remove its required exits. An untested feasible check is not an external blocker.

| Page / journey | Implemented or verified at checkpoint | Remaining acceptance / disposition |
|---|---|---|
| RRR | SQL/read/export proofs retained; layout save/reset/reload/restart and full saved-layout CSV proved. | Real leaf actor, residual controls and matched performance. Inherited screen has no wired history entry: retain exact source disposition. Partial, not accepted. |
| DBM current / daily history | June 17 current Suggestions = 0; positive Apply/Sleep, own-next-day effects and restoration proved in owned trials; Product/Location controls repaired and proved. | Downloaded XLSX, remaining positive controls/scopes, real actor coverage and matched performance. Reuse consumed trial receipts; never reset trials. Partial, not accepted. |
| BTR | Both branches, selective reads/CSV, authenticated gateway/restart, browser views/paging/Depo/horizon/history/layout save/reset and both toolbar files proved. Delayed tab-return restore passes. | Inherited fresh-reload hook fails; disposition required. Residual controls, leaf actor and matched performance remain. Partial, not accepted. |
| Buffer Trends | 134 exact graph responses and 30 declared failures; gateway/restart and type/horizon/summary/Depo/reset/reload controls proved. | Inherited doubled Total / stale Percentage behavior needs exact disposition; residual controls, leaf actor and matched performance remain. Partial, not accepted. |
| Planning categories | Overview proof retained; user explicitly verified exports working and directed deferral. Normal To Child grid rendered 7 dispatch rows, filter/selection and selected-run controls proved. | Custom NMS identity provenance/disposition; canonical child SQL and filtered-count wire proof; residual controls, leaf actor and matched performance. Empty request input does not prove request workflows. User-directed deferred, not accepted. |
| BPR | Read batch deployed at `88c434d`: filtering/count/grid/CSV/analytics/history/configuration; authenticated graph/filter/layout/paging proof retained. | Independent 52-case grid/count/analytics/export and CSV-cell comparisons; actual browser CSV receipt; leaf actor; matched performance; deferred drag/resize/split/multiselect/filter/historical/concurrency controls; inherited Reset Layout ordering disposition. Partial, not accepted. |
| Guided | Read batch deployed at `2d0cfde`; 578 independent consumer comparisons; approved 12-day/770-row history published; all 11 authenticated routes returned 200. Availability Trend rendered six location types; legend hide/restore proved. | Five-tab controls, horizons/ageing, chart/table/legends, Chronic grid/filter/layout/paging/downloads, DBM panels/link, Excess dual horizons; gateway value/wire comparisons; real leaf actor; persisted-layout/restart interactions; configured query-count and unaffected-route overhead diagnostic; matched API/browser performance. Inherited ageing/stale Excess horizon remains source-mapped, not waived. Partial, paused. |
| Research Insights | Existing native history/BPR evidence may be reused. Not opened in the Guided batch. | Whole-page selection→summary/calendar/ageing, graph/grid/date/horizon/filter/config/layout/export contract and proof, scope/restart/performance. Not accepted or covered by Guided. |

All required gaps remain in the Stage 2 denominator. Stage 2 closes only when required exits are proved or the human explicitly approves a narrow scope disposition. SQL/provider recovery makes formerly blocked comparisons feasible again; the old 18456/823 outage is not a continuing excuse to omit them.

## Serving checkpoint and approved inputs

The following identity is the recorded safe-stop state, not a perpetual health claim:

- Preview: `localhost:3005`; no 3004 cutover. Only MTA was recreated at the checkpoint.
- MTA image: `sha256:526ebe525ca7ea1b4c90e7fd475d3dc1eec6166a40161983477a117f7b302da8`.
- Container: `a7a583ea16a86197fe507013927db9df859b13574f25257b129b4fc5a922e9e8`.
- Selected run: `ac1612c8-0e49-4155-83c3-f59f41422293`; business date: `2026-06-17`.
- Output digest: `bd1c522f3df299d2fc3841aed7f66d48e4307e6967450b2d8a5463dc7867d33d`.
- Startup admission: `34a99fa5de6f70c2e7384283d083f6011558ac92c5927e627f4fd322d97044a7`.
- Normal current Suggestions = 0; normal actions disabled. Limit 4 GiB / 2 CPU, two workers, 180-second timeout, restart=no; MTA has no separate host port.
- Build/gateway/SQL comparison jobs ended and owned exclusive leases exited. Retain `test_freshvcf_guided_history_20261003_002`; no cleanup/reset is implied.

Approved supplements are exact, bounded exceptions. Missing input otherwise means unavailable, not empty:

| Input / exception | Allowed scope |
|---|---|
| Retained hierarchy | Exact approved 200-SKU/20-location catalogue, hierarchy and scopes; versioned read-time SL1–3/LL1–3 supplement bound to approved run/date/digest/catalogue. No F2 modification or invented hierarchy. |
| Empty transit and initial BPR remarks | Exact June 17 terminal supplement only, bound to complete retained shipment ledger and audit/input identities. No positive logistics or other-date transfer. |
| DBM positive trials | Separately owned retained pre-action scenarios, genuine run/date/actions and own predecessors. Apply/Sleep and restoration evidence is retained; no standing trial mode or permission reassignment. Any future authorized trial must stop action access and prove normal admission/date/Suggestions0/actions-disabled/gateway restoration on success, failure or interruption. |
| Empty initial OpenExpediteRequests | Human approval `call_zbzXQ93n4Qfs9tOGAixne3Lc`, selected June 17 preview only. No historical-empty claim or request writes. |
| Excess preview history | Human approval `call_bEZzSUkIR32TJ5lhNiuxhyFI`; empty pre-June 6 opening ONLY for this preview; June 6–17 own-output projections, 770 typed rows. Not proof of empty legacy history or a general rolling publication lifecycle. |

Excess input: `D:/freshvcf-build/inputs/excess-history-input-v1.json`, SHA256 `f7a03468227d2b5ef97fc28fec951ec8f373852ed906c9754d50269b75b84154`. Atomic publication/retry preserved accepted run metadata and existing projections. No engine replay or copying calculated legacy output into modern state occurred. General next-day publication/retention lifecycle remains a later architectural obligation, not an extra recovery platform to build during the paused page batch.

## Next bounded task — preparation, not execution authorization

The four-page dataset availability exit is accepted as recorded above; broader page implementation remains paused. Before a separately authorized whole-page continuation:

1. Reuse the retained page inventory and above residual ledger. Identify only missing page inputs/scenarios; do not repeat a full discovery programme.
2. Prefer the existing approved catalogue/population and retained history/trials. Define a finite fixture manifest covering required positive, empty, NULL, scoped and historical UI branches. Record exact missing facts and ownership before any loading.
3. Map the same logical consumer inputs to legacy MSSQL and modern PostgreSQL using their actual contracts. Confirm dataset/date/scope and restore boundaries. Do not assume identical physical schemas, overwrite accepted serving state, reset consumed trials, or create fake accepted calculation runs.
4. Separate claims: common consumer fixtures can prove API/UI contract compatibility. They cannot establish independent engine calculation parity. Calculated-state acceptance still requires each engine's own inputs, predecessor and outputs. Preserve F1/F2 proof untouched.
5. Deliver one complete page package with one consolidated affected QA pass, then record its result here. Retry only failed or changed behavior. No per-click delivery cycle, generic fixture/history framework or unbounded replay programme.

A small UI fixture does not satisfy whole-population performance or permission coverage. The separately stopped legacy date-alignment replay is not an instruction to resume it; retain its partial evidence and establish oracle availability before any new comparisons. SKU 6061's prior screenshot discrepancy was pagination/filter coverage, not proof that the catalogue identity was missing.

## Acceptance and engineering boundaries

- Preserve canonical NULLs, duplicate multiplicity/order, types, envelopes, filters, permissions and calculation semantics. No legacy repairs, guessed defaults, hidden fields, count-only parity or unsupported exclusions. Use `docs/LEGACY_EXCEPTIONS.md` for attributable, narrowly scoped flaws.
- Preserve accepted F1/F2 rows, frozen inputs/actions/SQL/comparisons/receipts. Reuse accepted evidence unless a relevant change invalidates it. Exact earlier approvals do not transfer to different runs, populations or workflows automatically.
- Existing frontend/auth/MTO business contracts remain the target. Retain explicitly approved fixes; no further redesign or permission changes implied. Actor-owned layout writes are distinct from immutable publication and business actions.
- Keep read queries tied to the actual page contract; scope/filter/count/order/page at the relational boundary where semantics permit. Preserve startup admission, run/digest/projection/config binding and full command integrity. No blanket cache, framework or speculative schema. Any schema change needs Django check, migration check/plan and migration-enabled PostgreSQL proof.
- Measure the configured request path when diagnosing repeated verification work. Consolidate demonstrably redundant reads without dropping integrity. The Guided diagnostic covers Excess and one unaffected route; it does not authorize a general admission redesign.
- Performance compares equivalent independently retained legacy/Fresh input/date/population, scope/hierarchy, request/filter/page/columns/export/output and resources. Protocol: 5 warmups, 30 interleaved warm samples, 5 application-cold repetitions, concurrency 1/4; retain raw failures, median, p95 and throughput. Fresh median/p95 no worse, throughput at least equal, errors no worse. Require affected API and browser journey proof. Missing comparable provider or inconclusive evidence stays UNPROVED. No arbitrary threshold, reduced population, shared cache flush or calculation replay just for benchmarks.
- Protect 3002/3003/3004, other tasks, live databases and shared infrastructure. `F:/vflow_integrated` is read-only reuse; `F:/new_vflow` excluded. No serving reset/repopulation, new public port, resource increase, shared Docker/WSL restart/prune or borrowed test database. SQL replay uses verified unique owned `VFTEST_Fresh_*` databases and the exclusive oracle lease; never bypass a verified owner.
- Stage 2 excludes BOR/supplier families, positive logistics, MDM, remarks, expediting/due-date writes and other Stage 3/4 workflows. DBM's exact amendment is the exception, not authority to open those workflows. MTO regression/final deployment and 3004 cutover remain later gates with explicit coordination.

## Evidence and supporting contracts

Read the relevant pointer, not the whole historical tracker. Evidence is external; this file keeps conclusions and open exits.

| Evidence / document | Purpose and limits |
|---|---|
| `D:/freshvcf-build/evidence/f2-runtime-memory-full-011/execution.json`, `terminal-readback.json`; `f2-runtime-memory-sql-full-011/replay.json` | Retained F2 terminal execution, relational readback and independent oracle evidence; qualifications remain. |
| `D:/freshvcf-build/evidence/f3-stage1-admission-002/receipt.json` | Accepted Stage 1 admission. |
| `D:/freshvcf-build/evidence/f3-stage2-guided-batch-001` | Guided checkpoint evidence described below. |
| [Archived tracker](archive/MIGRATION_2026-10-03_2d0cfde.md) | Earlier per-page receipt paths, exact approval context and preserved failures. Historical only. |
| [Page delivery contract](audit-2026-10-01/PAGE_DELIVERY_CONTRACT.md) and [interaction inventory](audit-2026-10-01/PAGE_INTERACTION_INVENTORY.csv) | Whole-page delivery method and static route/API/background candidates; inventory is not dynamic interaction proof or another queue. |
| [BPR contract](audit-2026-10-01/BPR_PAGE_CONTRACT.md), [Guided contract](audit-2026-10-01/GUIDED_PAGE_CONTRACT.md) | Specific source/request/producer contracts; current status comes from this file. |
| [Recovery plan](audit-2026-10-01/RECOVERY_PLAN.md), [earlier Stage 2 plan](audit-2026-10-01/STAGE_2_COMPLETION_PLAN.md), [audit](audit-2026-10-01/AUDIT.md) | Supporting scope/dependency references. Old sequencing, authorization and status statements are historical. Stages 3–5 require reassessment after Stage 2. |

Guided evidence: `filtered-scoped-comparison.json` has 468 independent cases; `excess-trend-comparison.json` has 110; these are **578 consumer comparisons, not UI interactions**. `excess-history-comparison-001/receipt.json` covers 12 own-output/770-row comparisons. `history-publication.json` and `history-postgres-tests-003.txt` prove atomic/readback/idempotent retry and six transaction/producer tests. Earlier failed attempts remain preserved.

`unit-suite-final.txt`: 270 tests, 268 passed; two pre-existing Expedite fixture failures (503 vs 200) remain: `test_expedite_chart_native_scope_and_source_flaw_unavailable` and `test_expedite_count_direction_and_unavailable_detail_contract`. Do not report the suite green. Baseline verification retained 376 pinned resources unchanged.

`build.txt` and startup admission establish the deployed checkpoint. `guided-gateway.json` records authenticated HTTP 200 twice for all 11 Guided routes plus BPR count, with complete bodies; it is not independent value comparison. Observed modern-only Excess 2.80–3.06s and BPR count 0.82–0.87s are not matched performance acceptance. `browser-handoff.png` proves only the bounded browser observations in the page ledger.

## How this tracker is maintained

Update current rows in place at a logical page exit or meaningful blocker change. Keep the active page, remaining exit, permitted boundary and required proof explicit before mutation. Record a concise result and evidence pointer; keep commands, test transcripts and incident chronology outside this tracker. Commit/push coherent checkpoints, not every probe. Never mark the overall goal complete while required exits remain. Do not resume the paused executor merely to acknowledge this baseline.
