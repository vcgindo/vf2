# MTA frontend integration audit — 1 October 2026

**Recommendation: retain the accepted calculation engine and inherited frontend, and finish F3 as complete user journeys backed by selective PostgreSQL reads.** The recovery has corrected several important paths, but it has not yet delivered a complete or performance-equivalent MTA application. Adding the next missing endpoint without a complete screen contract would continue the same drift.

This is an audit snapshot and proposed delivery contract, not a second status tracker. `docs/MIGRATION.md` remains the sole execution status. No implementation, acceptance status, service, database content, goal, or other chat was changed during this audit. All future application work and acceptance in this proposal use **3005**. There is no proposed 3004 cutover.

## Basis and limits

The original audit observations below are retained at commit24c05db. The later
authorized Stage1 added exact-call/deployed-IL anchors, corrected supplier report
ownership and performed new3005 admission/browser checks. Its current evidence
and status are exclusively in `docs/MIGRATION.md`; the earlier image/timing
snapshot below is not the current deployment identity.

Reviewed Fresh commit `24c05db04e531a04584b93e3912f0da1c1a84f30`, both referenced chats, current source, retained comparison/browser receipts, canonical BAT/SQL and deployed-DLL-derived consumer evidence. The original ten-step plan is in [rebuildplan](codex://threads/01a0ed2b-dd20-7722-a00c-5f32b4d5c1f3), in the turn starting 29 September 2026 at 18:08:58 IST, close to the supplied Tuesday 18:10 anchor. The detailed earlier audit is in [rebuildplanmonitor](codex://threads/01a0f29e-ec6b-7cf2-adb1-3ebda9365a55), in the turn starting 1 October at 12:35:13 IST, followed by the 12:42 recovery handoff. These are turn timestamps, not an assertion of the precise message time within each turn.

Read-only Docker inspection confirms the 3005 MTA image is `sha256:846da0f2e909c31d1136aaec0dade85b9ce7c6793d4592c341156c1435de8709`, matching the latest Planning receipt. It has the existing 4 GiB/2 CPU cap and `restart=no`. Only the preview frontend maps a public application port: `127.0.0.1:3005`. A PostgreSQL transaction explicitly set READ ONLY confirmed selected run `ac1612c8-0e49-4155-83c3-f59f41422293`, 17 June 2026, `SUCCEEDED`, `PASS_WITH_LEGACY_FLAWS`, and zero command overlays. Its output digest remains `bd1c522f3df299d2fc3841aed7f66d48e4307e6967450b2d8a5463dc7867d33d`.

The source/input identity verifier passed for all **376 pinned resources**. The three principal F2 execution, comparison and terminal-readback receipt hashes match the tracker. This confirms identity preservation, not a new replay or universal calculation certification. F2 remains accepted for its registered scope: 360 strict passes and 12 narrowly qualified Norm0 occurrence-text results.

No fresh browser acceptance or matched legacy-versus-Fresh timing experiment was run. Browser observations and timings below are attributed to retained receipts. Static route presence does not establish a successful HTTP response, reachable UI control, or parity. The older normalized API catalogue is supporting controller-source evidence; its own paths point to recovered C# and must not be promoted to deployed-DLL authority for an unverified method.

Machine-readable observations accompany this report:

- [Frontend service calls](F:/freshvcf/docs/audit-2026-10-01/frontend-api-calls.csv) and [browser routes](F:/freshvcf/docs/audit-2026-10-01/frontend-routes.csv).
- [Fresh backend routes](F:/freshvcf/docs/audit-2026-10-01/backend-api-inventory.csv), including handler lines, read paths and branch limits.
- [Endpoint reconciliation](F:/freshvcf/docs/audit-2026-10-01/endpoint-reconciliation.csv), joining every extracted request to its Fresh handler or explicit missing-route observation.
- [Screen-to-backend connections](F:/freshvcf/docs/audit-2026-10-01/screen-connections.csv), including input ownership and required acceptance.
- [Evidence snapshot](F:/freshvcf/docs/audit-2026-10-01/evidence-snapshot.json), with source and receipt hashes.
- [Phased recovery plan](F:/freshvcf/docs/audit-2026-10-01/RECOVERY_PLAN.md), including performance and final acceptance criteria.

## What should be preserved

The fresh build has a credible calculation and persistence foundation. No evidence inspected here justifies another engine rewrite, replacing synthetic artifacts, replaying accepted days, or changing a legacy business rule.

The inherited application sources are also stable. Comparing Git blobs against the exact registered reuse revision `66a77735d3f3f9a9becf4c87a08ae7827900cf84` shows:

| Tree | Observation | Meaning |
|---|---|---|
| MTO | All 156 tracked files match | Preserve its API and business implementation. Operational regression remains necessary, not re-engineering. |
| Authentication/user service | All 188 tracked files match | Preserve identity and gateway behavior; investigate only an attributable integration defect. |
| Frontend | 1,883 retained files match; three ZIP assets were omitted | There is no Fresh frontend source redesign. The omitted files are `forced/excel (1).zip`, `manual/Group 473.zip`, `manual/plus.zip` under `public/assets/img`. |

This is correspondence to the **pinned inherited application**, not a new claim that its JavaScript equals every original deployed legacy frontend bundle. No frontend/MTO/user-service change occurred after the Fresh foundation commit. Existing report serializers, permission joins, typed projections, action service, comparison drivers and accepted receipts are reusable assets.

The correct application connection is:

```text
Existing browser route / sidebar permission / control
  → same-origin /api/mta request on 3005
  → nginx → existing authenticated user-service gateway
  → gateway-derived identity and product/location permissions
  → Django MTA compatibility route
  → explicitly selected accepted run + applicable command state
  → report-specific PostgreSQL relation and canonical joins
  → legacy-shaped response / download
  → visible grid, chart, history or workflow result
```

The gateway owns identity; producer-owned hierarchy determines row membership; the MTA engine and command service own calculations and state transitions. A frontend filter, adapter, supplement or report projection cannot become another owner of Norms or computed history.

## Findings

**1. The delivery unit is still too often an endpoint proof rather than a complete screen.** The tracker now names the missing families, which is an improvement over the earlier audit. Nevertheless, it contains many narrowly closed checkpoints inside five still-open F3 obligations. Planning's ten overview counts are now connected and independently compared, while its GIT drilldowns, custom grids, filters and workflow remain incomplete. BPR shows 1,240 rows, while server filters, remarks, dependent logistics and exports remain incomplete. These distinctions are recorded honestly, but the sequencing continues to let visible screens remain unfinished for long periods.

The correction is to make one complete selected user journey the implementation unit: metadata, count, grid/chart, filter, clear, page, layout, relevant action, export and reload. Backend receipts should be reused inside that exit, not repeated as separate deliverables. A screenshot of one populated grid cannot close the other controls.

**2. The original full-publication bottleneck still exists on many report reads.** [context.py](F:/freshvcf/mta/presentation/context.py:71) calls `read_outputs`, which reads/hashes input, reconstructs the operational publication and hashes its complete production output. Current [views.py](F:/freshvcf/mta/presentation/views.py:250) still reaches that path for:

- BTR count and grid.
- Buffer Trends.
- Research Insights and historical availability.
- All nine Guided Insight endpoint variants.
- Excess/Fulfilment Planning grids/charts and Expedite counts/charts.

There are **515 operational images** in the selected manifest. The earlier review measured whole-publication reconstruction and hashing and observed roughly 10–20 second requests; those are historical findings, not newly measured current timings. The call graph still demonstrates the same unnecessary dependency for the paths listed above. BTR even reconstructs before checking pagination; Buffer Trends reconstructs before rejecting an unsupported active filter. This explains why a request that eventually fails can still do substantial work.

The preview retains two synchronous Gunicorn workers. A screen's concurrent requests can therefore queue behind unrelated full reads. More workers, memory, timeouts or a cache of the entire publication are not the right default correction.

**3. Selective images are a meaningful improvement, but do not always equal selective database queries.** RRR now performs SQL-side joins, filtering, counting and paging. DBM/history and BPR load a smaller list of complete images and then join/filter in Python. `load_image` uses `fetchall`, preserves ordinal and verifies the whole image digest. DBM current loads nine tables; a one-pair daily graph loads the required history tables for the whole estate before selecting the pair. Runs with committed commands deliberately reconstruct the complete DBM section for the unchanged command digest contract.

This is not a reason to discard the new readers. It is a reason to benchmark them honestly and, where needed, move selection/count/page into bounded SQL without changing joins, NULL behavior, multiplicity, order or command semantics. A scoped count must not build every wide display row simply to count it. Preserve BPR's unusual canonical distinction: it pages a joined **key bag** and rejoins it; a simplistic `DISTINCT` or page-after-final-join rewrite would change results.

**4. Route existence is a particularly weak coverage metric here.** Fresh exposes **37 MTA route patterns**. Several are multipurpose dispatchers and implement only selected branches:

| Route/family | Current implementation limit |
|---|---|
| `GetExportDataAsync` | RRR only; other `reportName` values explicitly unavailable |
| `GetBPRData/Count` | Terminal supplement, no active server filters |
| `GetPlanningDataCount` | Ten scoped counts; active filters unavailable |
| `GetPlanningDataGrid/Count` | Normal Excess/Fulfilment; Expedite count special case; no complete Expedite grid, GIT or custom branch |
| `GetPlanningDataGraph` | Selected Excess/Fulfilment/Expedite; no GIT; known receiving-label ambiguity |
| `GetUIConfig` | Multiple configurations exist even where data routes are absent |
| `GetState/SaveState/ResetState` | Generic user/report storage does not prove every report's state key and browser control |

The extracted inventory contains **129 request/helper call sites**: 114 distinct method/path templates in the MTA API namespace, plus eight call sites outside that namespace. Of the 114 templates, **36 match an existing Fresh route/method and 78 do not**. Fresh's 37th route is its permission-catalogue service endpoint, which is not in this browser service-call roster. The browser inventory records 29 declarations resolving to 27 unique paths: 26 under `/mta` and one out-of-namespace merchandising/mock page. Duplicate Planning and DBM declarations are retained; the relative MDM View/Modify child is resolved explicitly.

These counts are reproducible static coverage observations, not the active feature denominator or a parity percentage. The service inventory includes dormant declarations, optional profile branches and shared dependencies. Do not divide 37 by a raw frontend endpoint count and call the result completion. Count route+verb+category/type/reportName contracts, and then classify actual consumer reachability. The inherited duplicate routes are not a reason to redesign routing during this migration.

**5. Several unfinished families require application implementation, not wiring alone.** BOR, BOR colour-band, supplier allocation, logistics whereabouts, Elephant Orders, open-expediting workflows and MDM have inherited UI/service consumers but no corresponding complete Fresh API implementation. MDM is a connected draft/submit/review/approve/reject/task-history workflow, not covered by DBM Apply/Sleep.

Canonical activation must be precise. `RunCoreBPR.bat:64` invokes `GenSupplierWiseReq`. `OrderAllocBasedReports.bat` closes the `IsMTOEnvironment=1` block before the BOR allocation producer at line 46. Therefore BOR colour-band cannot be excluded merely because RRR colour-band is gated off in selected MTA profile 0. Total Requirement remains configuration-dependent; Stage1 exact-call tracing and authenticated sidebar evidence establish Supplier Dispatch as a required consumer of SupplierDispatchReq; Elephant Orders has a persisted image with zero terminal rows, but that alone does not prove the UI action, consumer joins or selected reachability.

Deployed SupplierWiseAllocationReportData/Count instead read BORWithOrderAllocation; they must not be mapped to SupplierDispatchReq merely by name. Current operational bindings contain supplier MOQ/SOB inputs and ElephantOrders, but do not provide an obvious named BOR/supplier report or MDM task/remark/draft model. That is an **unresolved producer-to-consumer mapping**, not proof that every necessary underlying fact is absent. The next implementation must name the exact existing modern relations or add a source-backed typed projection from them. It must not serve internal comparison traces, copy legacy output, or fabricate empty records.

Two navigation/data traps deserve explicit treatment. MDM's menu goes through `/masters-interceptor/*`, whose application selector redirects into `/mta/master-data-management/*`; searching only for a literal MTA menu URL misses it. The inherited Total Requirement hook imports `mock-data/RRR-Color-Bandwise`, initializes `rowData` from it, calls a real RRR count, and has its grid-fetch call commented out (`useTotalRequirementReport.tsx:16,34,62,84`). A populated page therefore cannot be presumed to display accepted backend data. Classify its canonical activation and inherited behavior before enabling it; do not promote those mock rows into acceptance or invent a replacement report.

**6. The two approved supplements solve narrow problems only.** The hierarchy supplement projects only approved SL1–3/LL1–3 attributes for exact run-bound consumer use. Without opt-in, native NULL hierarchy continues to deny membership. The terminal ancillary supplement proves empty June 17 `InTransitData` and initial Fresh BPR remarks. It does not establish a reusable logistics ingestion/workflow contract, positive shipment detail, arbitrary-day publication, or remark writes.

The selected run also contains four `GoodsInTransitTransporterMaster` rows with transporter identity/contact columns. A transporter directory is not four current shipments and cannot supply LR, movement, date or current-location facts. The approved empty terminal shipment ledger must remain distinct from older retained June 5 transit context. Positive logistics/workflow evidence needs an appropriately owned, already registered input or a specific new decision; it must not be hidden behind the terminal zero.

**7. Error-path and authorization acceptance are incomplete.** The inherited gateway uses authenticated sessions and overwrites browser-supplied row permissions, with retained forgery/denial proofs for selected calls. MTA's private route guard checks the trusted identity header. The private service has no public host-port mapping; keep that boundary.

However, a missing Django route returns an HTML 404, and the gateway attempts `response.json()`. Its exception path can turn an absent report into a generic 500. This behavior follows from the inspected code and was observed by the earlier audit; it is not a new current HTTP measurement. MTA outbound forwarding has no explicit request timeout in the inspected interceptor. These need bounded error-path tests, not timeout increases used to conceal expensive reads.

The React route permission gate is not, by itself, backend authorization. Verify direct authenticated requests with disallowed URL/action roles as well as wrong row scope, against canonical behavior. Do not infer a new role policy or modify MTO/shared authentication to solve an unproven concern. Unsupported, source-invalid and permission-denied branches must remain distinguishable and prompt.

**8. Integrity checking has been moved out of some requests, but automatic readiness is not yet a verified integrity gate.** `selected_run` checks configured identity, successful status, digest metadata and parity status. Selective readers check consumed images/projections. Complete integrity checks exist in explicit verification/restart evidence. The current `/readyz` only runs `SELECT 1`, and the preview command starts Gunicorn directly. No automatic whole-publication startup admission check was found in that path.

The proposed design must say exactly where complete integrity is enforced before serving a selected image. A verified deployment preflight or one startup check bound to run/digest/projection versions is sufficient; a new coordination service is unnecessary. If readiness is used as that guarantee, database connectivity alone cannot fulfil it. Command overlays must retain their complete before/after checks; do not replace them with a partial checksum in a performance edit.

The runbook also needs lifecycle reconciliation: its old “When idle” command stops the test PostgreSQL container, while the 3005 preview now depends on that same container. That instruction is unsuitable for an operational preview unless the application is deliberately being stopped. The final runbook must distinguish restart, disposable verification and stopping the entire owned preview; no command was executed from it during this audit.

**9. At-least-legacy performance has not been demonstrated.** Retained observations show substantial progress:

| Retained 3005 measurement | Recorded result | What it proves |
|---|---|---|
| RRR final gateway | Individual requests 0.206–0.5551 s; four-request batch 0.5593 s | Local warm-database response improvement |
| DBM count/grid | 0.4829–1.0012 s across the selected observations | Terminal current read timing, not positive action UI |
| Selected daily graph | 1.9635 and 2.0141 s | One selected graph's HTTP timing |
| BPR count/grid | 0.9949–1.3928 s | Terminal selected requests, including paging |
| Planning overview | 0.7966 and 0.9595 s | Ten-count gateway response, not drilldown/render timing |

These are small recorded samples, not p95s, cold-disk tests or current full-screen timings. No matched legacy series accompanies them in the inspected receipts. RRR's explicit two-second/five-second thresholds are not a substitute for the user's relative performance requirement. BTR's canonical large response and browser rendering also matter; backend speed alone does not prove screen responsiveness. Full matched methodology is in the recovery plan.

## Assessment against the original ten-step method

| Original principle | Current assessment |
|---|---|
| Freeze deployed authority | Preserved for registered sources; verified identity again in this audit |
| One executable capability map | Source map exists, but frontend branch/dependency coverage was not complete early enough |
| Complete execution skeleton early | Engine integration progressed; complete usable application skeleton did not keep pace |
| Cohesive business port | F1/F2 substantial and reusable; application workflows remain incomplete |
| Separate shallow and full-depth synthetic proof | Preserved in registered evidence; terminal UI cannot stand in for positive action/logistics trials |
| Fixed comparison boundaries | Valuable proofs retained; screen acceptance must add consumer branches without reopening unrelated calculations |
| Record legacy flaws narrowly | Retained; unavailable/contained branches are not exact parity |
| Compatibility-based UI | Source retained, but incomplete API dependencies and expensive reads violate the intended delivery outcome |
| Lean finite execution | Many granular proofs accumulated; one complete journey and one unmet exit should govern the next slice |
| Explicit product/operational acceptance | Still open for complete screens, performance, workflows, restart/retry and unchanged MTO operation |

The drift is primarily an **application-delivery and read-architecture problem**. It is not evidence that the accepted calculation results should be discarded. The appropriate recovery changes the unit of completion and finishes known gaps within F3.

## Meaning of full parity at completion

The final statement must mean all **defined, selected-profile MTA behavior** matches canonical outputs and workflows, and every required inherited screen works on 3005 at least as fast as the matched legacy journey. It must separately list source-undefined behavior, safe containment and inactive-profile functionality. Source defects cannot be silently repaired, but missing required integration cannot be placed in the same exception category.

The default DBM grid must continue to show June 17 current `Suggestions=0`. Historical `SuggestionsLog=132` belongs on history/insight surfaces. The catalogue contains 200 SKUs/20 locations, while its retained 1,240-pair DBM population spans 13 locations; neither 14 qualifying RRR rows nor zero current suggestions implies a shallow replacement dataset.

A terminal expected-empty screen can pass its empty-state contract. It cannot certify a nonempty action, shipment or report branch. A required input that remains unresolved prevents unrestricted full-product acceptance unless the user explicitly narrows that acceptance; no such narrowing is proposed here.

MTO remains an unchanged neighboring API. Its future work is limited to proving that login/routing/data access and existing operations remain functional in the same PostgreSQL stack on 3005. The source audit supports preservation, not a new claim that every MTO scenario was retested today.
