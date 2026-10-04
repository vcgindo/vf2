# Prepared presentation rollout and daily integration plan

Prepared 4 October 2026 from the current repository and retained runtime evidence.
The user accepts the delivered BTR snapshot and typed reader as the baseline for
extending presentation efficiency to other UI surfaces. This document proposes
the sequence; it does not start implementation or resume paused application work.
`docs/MIGRATION.md` remains the only status tracker.

## Accepted method and its limits

Prepare reusable report values once from authoritative outputs, store them as
typed relational rows, and serve the existing UI through selective typed reads.
Apply live authorization, filtering, canonical ordering and paging before
avoidable response packaging. Keep JSON at the existing API transport boundary;
avoid database JSON construction and round-trip parsing. The frontend formats
cells and handles interaction; it does not repeat already prepared report work.

This is a method, not a requirement to add a snapshot table for every endpoint.
Use an existing projection or an efficient direct SQL reader where sufficient.
Create a narrow presentation table only when repeated preparation is evidenced.
Filter-dependent aggregates still require selective serving-side computation:
do not precompute every possible user scope, filter or date-range combination.

BTR baseline: `806a239`, April 7 retained heavy dataset, both 97,299-row branches,
selected generation `e5bdac30-bbd9-45d8-a93d-84a645fad73c`. Typed-reader complete
output comparisons pass; deployed 3005 UI returned 5,000 prepared rows and
responded to scrolling. Observed response capture 5.47s/grid completion 7.82s
include verification overhead. These are an accepted development baseline,
not a universal speed target, controlled legacy speedup or whole-page acceptance.
The one observed typed SQL plan took 0.77s and removed the final wide sort.

## Research findings and proposed order

The order below is a recommendation from code structure, not a measured ranking
of current screen latency. Confirm the selected screen's bottleneck once at its
slice entry; do not launch a whole-application benchmark or inventory programme.
Existing route and contract inventories remain references, not new work queues.

| Order and surface | Observed current path | Proposed bounded intervention |
|---|---|---|
| 1. BPR grid and its count | Fixture uses `bpr_sql.py`; normal output uses Python `ReadModel` reconstruction. `mapBPRRowData` is an identity function. | Prepare only repeated display joins/types if one trace warrants it; otherwise improve the existing typed SQL reader. Use the same prepared population for count predicates where semantics match. Include a targeted Research grid compatibility check because it uses BPR APIs. No remarks/logistics writes or analytics redesign. |
| 2. DBM current suggestions grid and count | Fixture bounds selected inputs, then `dbm_filtered` joins/scopes/numbers the population in Python before paging; count repeats this path. Frontend count/grid pairing is already concurrent. | Persist stable daily suggestion display fields only if needed; use selective typed reads/counts. Preserve immediate Apply/Sleep visibility through the existing command owner; never display a frozen daily snapshot after a command changes state. Do not reopen positive action trials without missing evidence. |
| 3. RRR and supported related grids | `rrr_sql.py` already scopes/filters/pages typed operational rows and consumes `PickProjection`; frontend assigns returned rows directly. | Retain this reader unless one trace finds a specific remaining join, count or request bottleneck. Reuse persisted Pick data. Do not manufacture another table simply to copy the BTR design. Color-band variants require their own predicate/output check before reuse. |
| 4. Buffer Trends, then Guided and Research | Buffer Trends has a selective SQL graph reader. Guided loads named history tables and performs joins/aggregates in Python. Research graph routes call whole `publication()`, which is denied for the heavy fixture. | Replace whole-population reconstruction with selected typed history reads. Prepare reusable per-day/per-product-location ingredients, not all filter combinations. Reuse BPR grid and BTR history producers where their contracts agree. One graph/tab family at a time. Preserve inherited total/percentage behavior unless a specific semantic change is separately approved. |
| 5. Planning overview and category read views | Pick, Excess, Fulfillment, Expedite and PickPost already have run-linked typed projections; several readers load/verify broad bags before selecting. | Reuse these rows, push selection/count/page to SQL, and avoid repeated request reconstruction where measured. Work on one category's overview/grid/detail/graph journey at a time; do not replace existing producers. |
| Later application reads | BOR/supplier reports, logistics and workflow screens have separate source/state obligations in the existing application ledger. MTO is retained as a direct port. | Apply selective typed reads after their canonical producers and live workflows are connected. Daily immutable snapshots cannot replace editable masters, requests, remarks, permissions or workflow state. No blanket MTO refactor. |

## Boundary for every presentation slice

Before editing, name one surface, its run/date/population, current requests,
producer-owned inputs, stable preparation, request-dependent work and live state.
Inspect the whole journey: preparation/storage, SQL, API packaging, transfer,
frontend requests/transforms, and usable rendering. Change only the demonstrated
overhead. A quick query alone does not close a UI slice.

Use the existing heavy dataset and databases. Freeze the old affected outputs;
then implement the smallest complete change. Validate full ordered field/value
responses for the actual page and one scoped or range case, retaining empty,
NULL, duplicate, denied and error behavior through affected existing tests.
Include count/next-page/export comparison only when that contract is changed.
Use a first/later-page comparison when selection/order is changed. Reuse passing
producer and engine receipts; never replay calculations just to measure reads.

Finish with affected tests/checks/build, one completed browser response at the
actual configured page size, usable grid/chart and the affected interaction.
Observe one equivalent legacy load when that surface lacks comparable retained
evidence; do not reduce rows/columns to claim improvement. Hold date, population,
scope, filters, branch, page and resource conditions comparable, or state the
limitation. Record the actual API wait/transfer and browser completion; a page
counter or retained old grid is not response-completion evidence. No repeated
warmup/sample/concurrency campaign for these development slices. This does not
declare the older formal application-performance obligation satisfied.

Deliver one committed/pushed slice and its 3005 handoff, with rollback and an
honest user-facing result, then stop. Do not move to another screen automatically.
No generic reporting framework, cache, service, registry, integer product/location
key migration, grid replacement, new port, database copy/repopulation or resource
increase. A new table requires the repository's normal Django migration checks,
not migration squashing or schema cleanup of unrelated tables.

## Debt before daily application integration

These obligations block unrestricted daily integration, not every retained-data
UI slice. Clear each at the boundary where it becomes necessary.

| Debt evidenced in code or tracker | Required resolution and exit |
|---|---|
| Fixture-only preparation | BTR `build_selected()` rejects non-fixture runs and hierarchy supplements; it depends on a qualified version-1 reference. Connect the accepted reader/preparer to normal modern run outputs, preserving native/hierarchy provenance, duplicate behavior and types. General data may not satisfy the fixture's uniqueness qualification: prove it or retain an explicit compatible path, never deduplicate or invent an order. |
| Two BTR generations and differing read paths | Current grid uses version 2 while count/export/raw clients use version 1; normal BPR/DBM use different paths from the fixture. Converge inputs and supported readers only after their contracts are proved. Count/export may deliberately have different grains/fields; they must not blindly use grid rows. Retire superseded reference dependencies only once no required consumer depends on them. |
| Real daily input handoff | Existing R1 ingestion logic and `execute_day` consume explicit registered facts/profile/predecessor; retained replay tooling is not proof of a configured real daily feed. Identify the actual source file/API, master-data ownership, date/completeness validation and trigger, then connect the smallest adapter to the existing engine boundary. Do not rebuild the engine or create calculated outputs as input facts. |
| Presentation publication and serving selection | `finish_run` atomically publishes operational rows and several existing projections, but the BTR display builder is separate and serving selection is configuration-bound with startup admission. Prepare required presentation rows from a completed run; verify run/digest/date/producer bindings and readiness before controlled selection. A preparation failure leaves the previous complete presentation available with its truthful date. Do not expose a mixed-day set or reuse the old BTR generation with a new run. |
| Daily preparation cost and retry | BTR's first heavy build took about 20 minutes and added roughly 440 MiB. Adding more copies may make refresh expensive. Reuse existing rows, bounded batches and existing idempotent identity; measure one representative combined refresh once. A failed build must not rerun accepted calculation or duplicate completed rows. Retention must preserve the previous serving set/rollback and required history; no blanket database cleanup. |
| Current commands and mutable facts | DBM commands affect current display and next-day opening; layouts/auth/remarks/workflow facts have separate owners. Keep commands authoritative and their visible effects current, using the existing overlay or the smallest targeted update. Permissions remain live on every request. Do not snapshot entitlements or freeze actionable state until tomorrow. |
| Missing history and ancillary populations | Fixture `publication()` is unavailable; the tracker records incomplete histories, positive logistics, remarks, NMS/Expedite contracts and run-specific supplements. Attribute every missing population to a producer or external fact. Connect actual sources or record the precise unavailable contract; missing is not empty, and June 17 supplements do not transfer to April 7 or arbitrary future dates. |
| Remaining whole-application acceptance | Existing Stage 2 page gaps, inherited UI defects and two known Expedite test failures remain recorded. Efficient snapshots do not close these or authorize later workflows/MTO/cutover. Retain the ledger; resolve only dependencies encountered by the authorized slice, and return to complete application acceptance after integration is explicitly authorized. |

## Later daily connection sequence

The desired flow is:

```text
Daily external facts and approved master changes
  -> existing ingestion mapping and validation
  -> execute_day with the modern persisted predecessor and commands
  -> atomic authoritative operational outputs and existing projections
  -> bounded typed presentation preparation for those outputs
  -> verify the complete serving set and select it through existing admission
  -> selective API reads with live scope/filter/count/page
  -> existing frontend displays ready values
```

Keep the existing daily cadence. Do not invent a scheduler, automatic activation
or a separate calculation/publication engine during UI trials. Once the selected
read surfaces are ready, first prove preparation against an already accepted
normal modern run without recalculation or serving cutover. That proof establishes
compatibility, not heavy-data speed parity. Next, under a separately authorized
integration scope, connect the real daily input adapter and presentation step to
the existing day boundary/trigger and prove one successful next-day transition
plus failure/retry without a partial serving set. Use existing serving selection
and controlled restart/admission initially; improve the transition mechanism only
if this proof identifies a concrete need. 3004 cutover remains a separate decision.

## Proposed single batch execution contract

The human proposes preparing the frontend integration in one implementation
batch followed by one bounded connected-UI validation pass. On explicit dispatch
of that instruction, this section supersedes the BPR-only recommendation and
per-screen stopping rule above for that batch only. All other boundaries remain.
Planning and the executor are still stopped until the human dispatches the task.

The controller recommends an exact four-surface batch to remove the previous
ambiguity between the rollout's five families and the conversational four areas:

1. BPR grid/count: `GetBPRData` and `GetBPRDataCount`; compatibility with existing
   Research BPR grid requests, without implementing Research graphs or widening
   fixture permissions.
2. DBM current grid/count: `DBMData` and `DBMDataCount`; preserve the existing
   command-bearing path, with no new Apply/Sleep trial or action activation.
3. RRR grid/count: `RRRData` and `RRRDataCount`.
4. Buffer Trends graph/table: `GetBufferTrendGraphData` and the existing Absolute/
   Percentage, Self/Parent, horizon and filter consumers of that response.

Guided, Research graphs, all Planning categories, color-band variants, exports,
history dialogs and other endpoints are excluded from this batch, except an
existing unaffected compatibility check when a shared helper changes. They are
still in the overall rollout; no executor may silently select them into item 4.

Implement through the four fixed items without stopping for a new permission
question after each one. Use one short batch entry in MIGRATION.md recording the
affected endpoints, exact overhead, expected values and dependencies. Keep basic
correctness checks during implementation; deploy one coherent batch to 3005 and
perform one targeted final UI pass per included surface. Leave efficient readers
and identity mappers unchanged with supporting evidence. Do not add storage to
make all four implementations uniform.

Preserve configured page sizes/fields. A 5,000-row check applies where the real
UI workload selects it; a chart is checked for its actual requested series and
horizon. Freeze complete before-results for changed paths, compare full affected
outputs and one scoped/range case, and add later-page/count checks where changed.
Correct only attributable failures and rerun only their affected checks. Deliver
commit/push, coherent deployment identity, rollback and each surface's result.
If a required input is unavailable or excluded work is indispensable, report the
precise dependency and partial delivery; do not call all four complete or expand
the scope. Do not start daily integration after this batch.

No executor prompt or implementation goal is created by this planning document.

## Source references

- Baseline and open obligations: [MIGRATION.md](MIGRATION.md), [BTR handoff](BTR_REPORTING_HANDOFF.md).
- Typed BTR builder/reader: [btr_snapshot.py](../mta/presentation/btr_snapshot.py); generation selection: [btr_reporting.py](../mta/presentation/btr_reporting.py).
- Current route dispatch and reconstruction: [views.py](../mta/presentation/views.py), [context.py](../mta/presentation/context.py), [dbm_read.py](../mta/presentation/dbm_read.py).
- Existing readers: [bpr_sql.py](../mta/presentation/bpr_sql.py), [rrr_sql.py](../mta/presentation/rrr_sql.py), [buffer_trends_sql.py](../mta/presentation/buffer_trends_sql.py), [insight_read.py](../mta/presentation/insight_read.py).
- Daily ownership and projection hooks: [temporal.py](../mta/runtime/temporal.py), [services.py](../mta/runtime/services.py), [admission.py](../mta/presentation/admission.py).
- Frontend behavior: [BPR hook](../frontend/src/VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BPR/useBPR.ts), [row helpers](../frontend/src/helpers/utils.ts), [DBM hook](../frontend/src/VectorFlow/Pages/MTA/DBM/DBMNormSuggestions/useDBM.ts), [Research hook](../frontend/src/VectorFlow/Pages/MTA/InsightsAndTrends/ResearchInsights/useResearchInsights.tsx).
- Remaining route denominator: [retained screen map](audit-2026-10-01/screen-connections.csv) and [frontend routes](audit-2026-10-01/frontend-routes.csv); these are historical inventories, not current runtime acceptance.
