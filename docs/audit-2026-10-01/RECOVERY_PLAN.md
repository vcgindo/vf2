# Proposed F3 recovery and acceptance sequence

This is the requested proposal, not authorization to start coding. It keeps `docs/MIGRATION.md` as the only tracker and uses its existing F3.1–F3.5 obligations. The stages below describe dependencies and exits; they introduce no new recovery IDs or parallel queue. All deployment, browser and final acceptance work remains on **3005**. MTO API/business code, F2 calculations, frozen inputs, canonical SQL, accepted receipts and protected services remain unchanged.

Do not restart the migration. Preserve current RRR, DBM/history, BPR and Planning-overview proofs. Start by reconciling the audit inventory into the existing F3 screen matrix, then complete connected journeys. A failed unrelated input boundary must be recorded once and must not cause repeated discovery or replay of passing calculations.

## Stage 1 — Adopt the complete connection contract and serving boundary

Subsequently authorized and implemented only as the bounded Stage1 checkpoint
in `docs/MIGRATION.md`. That tracker records the evidence and stopping boundary;
Stages2–5 below remain a proposal. Stage1's new Planning overview browser evidence
means the first remaining Stage2 journey is RRR finishing acceptance.

**Maps to F3.1/F3.3; first prerequisite for subsequent implementation.**

Use the attached route/service/backend inventories and `screen-connections.csv`. Reconcile only unresolved entries against exact deployed controller/method, current configuration and page hooks. Do not re-inventory already proven RRR/DBM/BTR contracts. For every required screen, the tracker row must specify:

1. Sidebar/URL permission, browser route/component, selected-profile activation.
2. Initial, interaction and export requests: verb, path, category/type/reportName, body/query, configuration and layout key.
3. Canonical deployed source and output shape, including double-encoded JSON, strings vs numbers, omitted NULLs, errors and empty states.
4. Producer-owned PostgreSQL inputs/projections, accepted run/date and scope hierarchy owner.
5. Reusable parity receipt; remaining screen behavior; precise missing input if any.
6. Functional and matched-performance proof required on 3005.

Freeze a finite required denominator. Classify unused service declarations, mock calls, inactive MTO-profile reports and configuration-dependent screens separately. A route hidden only by current preview permission is not automatically outside the selected product. Do not widen user permissions just to make a screen appear.

Define integrity admission for selective serving: validate full selected publication and projection identities once at a designated deploy/start boundary; admit only that run/digest/version; normal reads use the lightweight run guard and appropriate relation/projection checks. A failed preflight prevents readiness. Retain immutable publication semantics and full command integrity. Prefer the existing deployment process over a new service or general framework.

**Permitted future boundary:** existing F3 tracker, presentation read helpers/queries, deployment admission/readiness and focused affected tests. No engine or MTO changes. No schema change until a specific consumer requires one; then use real migrations and the mandated PostgreSQL checks.

**Exit:** every active page has a complete finite request contract or exact source/input disposition; all remaining `publication()` read-path callers are mapped; the selected-run integrity admission contract is explicit. Inventory is a one-time input to delivery, not an ongoing documentation programme.

## Stage 2 — Finish the currently connected reporting journeys

**Maps to F3.1/F3.2/F3.3.** Keep one screen active at a time; a screen exit includes its relevant export/action, not a later application-wide download sweep.

First close the latest Planning-overview browser checkpoint against the existing accepted image. This is evidence completion, not another SQL comparison. If browser attachment remains unavailable, mark that exact exit blocked and continue the next independent screen; do not call it accepted.

Recommended connected-screen order after that checkpoint:

| Journey | Concrete implementation/verification boundary | Required exit |
|---|---|---|
| RRR finishing checks | Retain existing SQL reader/export; close outstanding saved-layout/history/control behavior and matched benchmark | Same 14-row terminal population, permitted filtered populations, full filtered export, layout behavior, history and reload; no repeat of ten already accepted export cases without relevant change |
| DBM current and daily history | Keep current empty population; benchmark current/history including command-bearing retained cases; use bounded query selection if measurements require it | Date/0 count/NULL envelope correct; designated entry points and six graph sections correct; saved layout and client XLSX; retained positive Apply/Sleep browser proof handled under Stage 4 without switching default publication |
| BTR and Buffer Trends | Replace full-publication reads with report-specific relational queries; retain exact Tech/Eco predicates, joins, date labels and wire types | Both 1,240-row branches; supported horizons, count/filter/page, daily dialog, chart selection, BTR-specific CSV bytes and reload; Buffer Trends only exports if its actual UI supports one |
| Planning categories | Reuse overview and persisted Excess/Fulfilment/Expedite projections; implement missing selected grids/charts/custom branches and actual filters, replacing full reads | Overview→category→chart→grid→filter→export stays on one run; exact per-category counts, nested details and permission multiplicity; no generic count substitution |
| BPR | Keep canonical key-bag paging and approved terminal supplement; connect real server filters, applicable shared lookups, details and report-specific CSV/client export | 1,240 terminal rows, full vs paged scope, filter/clear, sorting, details and date; terminal empty transit displays canonical behavior; remarks are completed through Stage 4 |
| Guided and Research Insights | Select only required BTR/DBM/report relations; complete selection, horizon/date and graph/grid dependencies | All enabled tabs and defined branches, correct historical/current populations and rendered labels, Research grid selection→summary/calendar/ageing and XLSX; distinguish client filtering from server filtering |

For Planning GIT and BPR terminal detail, the approved empty ledger may support the exact terminal empty consumer. It does not authorize positive logistics data. Finish the defined zero branch, record any remaining input blocker precisely, and address positive logistics under Stage 3. Likewise, a legacy ambiguous Expedite label remains a narrow `NOT_PARITY` qualification; do not invent a label or discard valid numeric comparisons.

**Read architecture rule:** scope/filter/count/order/page in PostgreSQL where appropriate, preserving legacy semantics; stream large exports without changing rows, headers or order. Reuse the existing typed relational store first. Add a bounded typed projection only when its producer and purpose are known and a query cannot reasonably serve the required contract. Preserve run ID, source digest and duplicate ordinal. No whole-run response cache, trace-serving fallback, blanket DISTINCT, invented tie-break or truncated page.

**Exit per screen:** one committed image on 3005; real authenticated navigation; complete request roster; matching API and rendered output; applicable controls/export; correct prompt denial/error behavior; performance gate below; reload/restart stability for that boundary. A screenshot alone is insufficient. Reuse unchanged comparisons and run only affected proofs.

## Stage 3 — Complete operational reports and logistics

**Maps to F3.1/F3.2/F3.3.** This is finite missing product work, not an optional tail.

| Family | Source/input decision before implementation | Completion boundary |
|---|---|---|
| BOR | Reconcile deployed BOR opening/refresh/current/history joins to accepted modern facts | Count/grid/analytics/config/layout, date/filters, BOR-specific export and remark entry/readback |
| BOR colour-band | Use the selected producer outside the IsMTOEnvironment gate | Full allocation bands, count/grid, filters, BOROA export, remarks; compare values and duplicates, not only totals |
| Supplier-wise allocation | Follow deployed PlanningProcessor reads of `BORWithOrderAllocation` and exact consumer joins | Actual supplier allocation grid/count, scope, filters and client export; MOQ/SOB alone are not the finished report |
| Logistics whereabouts/GIT | Separate transporter directory, dated shipment/movement facts, generated GIT report and user remarks | Grid/count/charts, selected row/transporter/detail, remarks and client exports; terminal empty plus required positive retained case |
| Elephant Orders | Reconcile selected rule/consumer and due-date update ownership; terminal image is empty | Correct empty view and retained eligible update/rejection/readback/next-run consequence when selected |
| Open Expediting Requests | Port deployed request→list→remark lifecycle and any downstream consumer | Planning submit, own persisted request, permissions, list/details/remarks/export/reload; no new expediting rules |
| Supplier Dispatch | Required by exact calls and Stage1 authenticated sidebar; deployed PlanningProcessor reads SupplierDispatchReq generated by GenSupplierWiseReq | Map the generated terminal population and complete count/grid/filter/client-export journey; supplier MOQ/SOB are inputs only |
| Conditional Total Requirement | Resolve selected profile and inherited mock-grid behavior once | Exact inactive/undefined disposition or approved scope decision; never count a mock grid as output parity |
| RRR colour-band / Order Allocation | Selected MTA profile is 0; corresponding gated producers inactive | Correct configured behavior/disposition; no manufactured population or MTO change |

Use a simple input disposition for each missing population:

- **Already persisted and correct:** query it selectively.
- **Deterministically derived from accepted modern facts:** add the exact typed consumer projection with provenance and an independent legacy consumer comparison; do not alter accepted F2 rows.
- **External/application fact not present:** identify exact fields/date/owner and registered artifact. Reconcile a retained source or present one bounded decision; never infer empty from missing.
- **Genuinely inactive or undefined:** retain source/config proof and narrow qualification; it is not a fabricated success.

**Exit:** all selected operational reports have complete 3005 journeys and accurate reports/exports. Positive logistics is either proved using admissible retained inputs or remains an explicit blocker to unrestricted full parity. It must not disappear into a generic “legacy exception”.

## Stage 4 — Complete application workflows and editable master data

**Maps to F3.2/F3.3.** Implement workflows end to end, with one authoritative state owner.

MDM requires configuration and current-master access, draft creation/edit/delete, validation, submit/forward, pending review, task details, approval/rejection, task status and modification history. Connect all selected frontend operations, including task downloads and control-specific data such as seasonality. Attribute inputs to exact deployed methods and table transitions. Optional admin configuration/permissions and non-MTA validation routes must be classified by actual selected reachability before porting; their presence in a broad service file alone is insufficient.

The Fresh runtime currently has no complete API workflow for these operations. The work may require typed application tables and migrations; it should not be described as merely exposing existing report rows. Keep submitted/approved application inputs distinct from immutable accepted publications. Feed approved effects through the existing production `execute_day` boundary as required by the canonical flow. Never update frozen June 17 calculated rows in place or make UI code calculate Norms.

For DBM, reuse the already accepted 62-comparison gateway/action/next-day proof. Add actual eligible browser Apply/Sleep, selection, denial, success/readback and reload on separately owned retained shallow cases. Keep the default terminal run unchanged and actions disabled there. Before any positive browser trial, define how 3005 accesses the isolated action state without replacing an accepted default publication; a temporary explicitly scheduled 3005 test mode or another run-scoped existing mechanism requires concrete authorization if it changes the serving configuration. Do not introduce another public port.

For remarks/expediting/due dates/MDM, verify actor identity, source-correct timestamps, authorized scope, persisted histories, duplicate/retry behavior and downstream effects. Use the actual legacy idempotency/error semantics, not a redesigned workflow. Approval loops and emails are separate external effects; use owned local test handling and never send real messages merely to close a test.

**Required proof:** at least one complete valid lifecycle and the actual applicable rejection/denial branches; exact persisted rows/histories and own-next-day effects where required; no cross-engine state seeding. Unit tests or a successful POST alone do not close the flow.

**Exit:** every selected user write has a working 3005 journey, a canonical state consequence, isolated retained proof and restart/readback evidence. MTO remains unchanged.

## Performance contract — applied to every stage, not postponed

The acceptance target is **Fresh at least as fast as legacy**, per equivalent user journey and workload. Do not invent an absolute two-second target and treat it as meeting that requirement. Do not use existing 3003/3004 applications as the canonical legacy benchmark unless their route/provider identity is proven; they contain other migrations.

Before the first affected optimization, establish a matched baseline using the deployed legacy DLL/query and retained independent facts. Use isolated owned legacy resources without resetting or modifying live databases. Hold constant selected date, input identity, hierarchy supplement, actor scopes, request, page size, visible columns, export scope and output population. Normalize resource budgets and test conditions; if the systems cannot be comparably provisioned, report the limitation rather than assert speed parity. The legacy calculation engine is not rerun just to time consumer reads.

Capture two layers:

| Layer | Measurements |
|---|---|
| API/query | queue time where observable, DB query count/time, rows scanned/returned, first-byte and complete-response time, bytes, CPU and peak memory |
| Browser journey | click→usable grid/chart, complete request waterfall, rendering/long tasks, filter/clear/page, modal history, layout restore, download completion and responsive empty/error handling |

Cover cold application start, warm reads, first and later page, filtered and denied populations, canonical empty results, known failure/unsupported branches, full export and a concurrent page-load mix. “First request after restart” is not “cold disk”. Never flush shared host or database caches for this test. Keep canonical page sizes and fields; smaller payloads count only when the legacy contract permits them.

Proposed initial protocol: five unscored warmups and at least thirty measured runs per representative warm request/journey, in interleaved legacy/Fresh blocks; five application-cold repetitions; concurrency 1 and 4, then the actual expected user load if known. These are proposed measurement settings, not existing receipts. Record the raw samples and median/p95, including failures. Report small-sample uncertainty; extend only the disputed measurement if the comparison is inconclusive.

Gate: Fresh median and p95 must be no worse than matched legacy for required successful journeys, with equal output and no worse error rate; throughput must be at least legacy at the same bounded load. If the distributions overlap too much to establish this, mark performance **unproved**, not passed through an invented tolerance. Safe-denial branches where legacy SQL is invalid cannot claim latency parity to a nonexistent successful result; prove prompt containment and label the exception separately. Keep the 4 GiB MTA cap; no OOM or runaway report-size-dependent full-state reconstruction.

Tune the evidenced bottleneck only: remove full reads, push predicates/count/page down, inspect `EXPLAIN (ANALYZE, BUFFERS)` on owned read-only test queries, add justified indexes through migrations, and avoid unnecessary duplicate work inside one request. Do not create a generalized cache/pipeline/framework before measurements justify it. Any cache later proposed must be keyed by run/digest, projection version, authenticated scope, request and command revision, with a demonstrated invalidation contract.

## Stage 5 — Combined runtime, MTO preservation and final acceptance on 3005

**Maps to F3.4/F3.5.** Reuse the one owned isolated stack and preserve all earlier evidence.

1. Verify one PostgreSQL database and intended service schemas, no operational SQL Server/.NET calculation dependency, no new public port, resource caps and `restart=no`.
2. Prove migrations and a fresh-start procedure in explicitly owned disposable resources. Do not erase/repopulate the serving database. Separate clean bootstrap from ordinary restart; neither may reset user state or substitute a trial publication.
3. Prove accepted publication admission, frontend asset loading, authenticated sidebar/deep links, cookie-host isolation, restart-stable run/date/rows/layouts/actions and interrupted-attempt handling. An immutable retry must verify existing results; a failed attempt must retain identity and no partial production rows. Do not replay F2 unless an attributable relevant defect requires an approved correction.
4. Exercise unchanged MTO through the real 3005 login, navigation, gateway and PostgreSQL schema. Reuse existing MTO business cases and verify representative read/write/reload behavior in owned test state, including WebSocket-dependent behavior if the selected workflow uses it. Confirm unchanged source/image contract. An attributable issue is investigated at routing/configuration first; no MTO business-rule changes.
5. Run the focused repository suite and affected PostgreSQL/gateway/browser checks. For schema changes run Django check, makemigrations --check, migrate plan and migration-enabled PostgreSQL verification. Expand testing only for a relevant change/failure. Verify F2 receipt identity and protected-service isolation at the combined boundary, not after every small edit.
6. Update the runbook to the commands actually exercised and the already verified local test login; document startup/readiness, publication selection, restart/retry, logs, restoration and known exact qualifications. Commit/push the isolated accepted checkpoint and tie screenshots/network/download/timing evidence to the commit and image.

**Final exit on 3005:** every selected required screen/workflow is fully verified or has an explicitly approved narrow source-undefined disposition; no required missing route/input is hidden; defined results match legacy; matched performance passes; fresh-start/restart/retry and unchanged MTO operation pass. No 3004 handoff is needed for the user's current 3005 delivery instruction.

## One acceptance record per complete journey

Add the following fields to the existing tracker row/evidence link rather than creating another status document: commit/image; run/date/digest; actor URL and row scopes; complete requests and canonical sources; expected and actual typed rows/charts; UI screenshot and network evidence; filter/clear/page/layout/history; action and downstream effect where applicable; exported file/header/rows/bytes; matched latency samples; restart/readback; exact exception and residual blocker.

The first implementation instruction after approval should name the active F3 row, its unmet screen exit, reusable receipts, permitted files and proof. Finish or explicitly block that row before moving to an independent item. Do not change the denominator to claim progress, and do not let another endpoint count become the acceptance criterion.
