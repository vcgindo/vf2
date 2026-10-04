# Prepared presentation rollout and daily integration plan

Prepared 4 October 2026 from the current repository and retained runtime evidence.
The user accepts the delivered BTR snapshot and typed reader as the baseline for
extending presentation efficiency to other UI surfaces. The human now authorizes
one holistic reporting-contract and implementation batch, frontend integration,
then module-by-module inspection. This supersedes both the BPR-only rollout and
the later four-screen restriction. Only this read-only presentation intervention
is resumed; daily ingestion integration and other application work remain paused.
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

## Reporting families in the holistic contract

These families are one contract and implementation batch, not successive
independent designs or a measured latency ranking. Reuse the current implemented
read routes in `mta/presentation/urls.py` and retained screen maps to bind the exact
endpoint/tab inventory once. Inspect known reconstruction paths and use one
targeted trace only where the actual work is unclear. Do not launch a fresh
whole-application discovery or benchmark programme.

| Family | Observed current path | Implementation direction within the batch |
|---|---|---|
| BPR and dependent Research grid | Fixture uses `bpr_sql.py`; normal output uses Python `ReadModel` reconstruction. `mapBPRRowData` is an identity function. | Use existing typed SQL or prepare repeated display joins/types where warranted. Keep grid/count/analytics/export relationships explicit; different response grains need not use identical rows. Research reuses the BPR grid contract. No remarks/logistics writes. |
| DBM current suggestions and daily-history reads | Fixture bounds selected inputs, then `dbm_filtered` joins/scopes/numbers the population in Python before paging; count repeats this path. Frontend count/grid pairing is already concurrent. | Persist stable daily suggestion display fields only if needed; use selective typed reads/counts and pair-selected history. Preserve immediate Apply/Sleep visibility through the existing command owner; never display a frozen daily snapshot after a command changes state. No new action trial or action activation. |
| RRR | `rrr_sql.py` already scopes/filters/pages typed operational rows and consumes `PickProjection`; frontend assigns returned rows directly. | Retain this reader unless there is a specific remaining join, count or request bottleneck. Reuse persisted Pick data; no duplicate table. Shared histories and supported exports remain in the contract. Missing color-band/other route implementations are not new business-porting work in this batch. |
| BTR, Buffer Trends, Guided and Research graphs | Accepted BTR grid already uses prepared typed reads; its counts/exports retain a reference reader. Buffer Trends has a selective SQL graph reader. Guided loads named history tables and performs joins/aggregates in Python. Research graph routes call whole `publication()`, which is denied for the heavy fixture. | Preserve the BTR baseline. Share exact compatible history ingredients, replace whole-population reconstruction with selected typed reads, and prepare reusable per-day/per-product-location values where needed. Support all existing implemented graph/tab contracts with available authoritative inputs. Keep missing-input failures explicit. Preserve inherited total/percentage behavior unless a semantic change is separately approved. |
| Planning overview and existing category read views | Pick, Excess, Fulfillment, Expedite and PickPost already have run-linked typed projections; several readers load/verify broad bags before selecting. | Reuse existing rows, push selection/count/page to SQL where exact semantics permit, and eliminate repeated request reconstruction. Cover existing overview/grid/detail/graph readers together; do not replace producers or add missing workflow/logistics facts. |
| Later application reads | BOR/supplier reports, logistics and workflow screens have separate source/state obligations in the existing application ledger. MTO is retained as a direct port. | Apply selective typed reads after their canonical producers and live workflows are connected. Daily immutable snapshots cannot replace editable masters, requests, remarks, permissions or workflow state. No blanket MTO refactor. |

## Boundary for the complete batch

Before editing application code, name all included surfaces/endpoints and their
run/date/population, producer-owned inputs, stable preparation, request-dependent
work and live state in one contract. Include grid/count, related existing graphs,
history and supported read exports; do not silently exclude a consumer because
it is harder. Classify genuine missing inputs with source evidence and continue
available dependencies. Cover preparation/storage, SQL, API packaging, transfer,
frontend requests/transforms and usable rendering from the outset.

Use the existing heavy dataset and databases. Freeze the old affected outputs;
then implement the smallest complete change. Validate full ordered field/value
responses for the actual page and one scoped or range case, retaining empty,
NULL, duplicate, denied and error behavior through affected existing tests.
Include count/next-page/export comparison only when that contract is changed.
Use a first/later-page comparison when selection/order is changed. Reuse passing
producer and engine receipts; never replay calculations just to measure reads.

Finish the batch with affected tests/checks/build, one completed browser response at the
actual configured page size, usable grid/chart and the affected interaction.
Observe one equivalent legacy load when that surface lacks comparable retained
evidence; do not reduce rows/columns to claim improvement. Hold date, population,
scope, filters, branch, page and resource conditions comparable, or state the
limitation. Record the actual API wait/transfer and browser completion; a page
counter or retained old grid is not response-completion evidence. No repeated
warmup/sample/concurrency campaign for this development batch. This does not
declare the older formal application-performance obligation satisfied.

Deliver one committed/pushed coherent batch and its 3005 handoff, with rollback
and honest module results, then stop. Do not stop and request renewed permission
after each report; do not start daily integration after the batch.
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

## Authorized holistic execution contract

This replaces the per-screen sequence and four-screen proposal. The authorized
sequence is foundation across the portfolio, reporting implementation across the
portfolio, frontend integration across the portfolio, then module inspection.
It is not permission to build generic infrastructure or to replace every report
with a wide snapshot. Keep each phase's proof in MIGRATION.md before advancing.

### 1 Establish the complete reporting contract

Use the existing endpoint/screen inventory to add one compact contract matrix
here: endpoint and consumer, exact row/series grain and fields/types, source
run/date/digest, reusable producer/preparation, daily versus live values,
authorization/filter/count/page/export rules, and serving choice. The three
choices are existing typed projection, narrowly prepared repeated work, or
bounded live/request-dependent read. Record the relationship between fixture
and normal output sources without copying fixture outputs into engine state.

Cover BPR/DBM/RRR and all existing read-only BTR, Buffer Trends, Guided, Research
and Planning consumers enumerated above, including shared histories and existing
read exports. Unimplemented BOR/supplier/MDM/logistics workflows and MTO changes
remain excluded. Every existing included consumer must receive an explicit
contract; it cannot disappear through a runtime permission denial. Do not change
grants to run a denied screen. Distinguish absent input, incompatible source,
missing reader wiring and genuinely undefined legacy behavior. Available retained
producer data authorizes correcting read wiring; it does not authorize fabricating
missing data or overriding accepted input/supplement boundaries.

Exit: complete portfolio contract and explicit dependency decisions, not a new
framework design. Start implementation immediately after this compact matrix;
do not spend repeated turns inventorying already mapped producers and routes.

### 2 Implement one coherent reporting foundation

Read and rewrite only the preparation/read paths required by that contract.
Reuse existing typed operational rows/projections, shared exact source ingredients
and the proven BTR typed-reader pattern. Prepare repeated display joins/conversions
once from the existing heavy April 7 outputs, using bounded streaming/batches and
one repeatable preparation entry point only if preparation is needed. Do not
replay the engine, change source data or build a new loader/publication service.

Where a new narrow typed table is justified, preserve provenance, duplicate
occurrences, strings/numbers/NULL/nonfinite values and existing order. Do not create
one table per endpoint by default or materialize every filter/permission/horizon
combination. Scope/filter/page before response packaging; avoid SQL JSON building
and per-row decoding. Counts/exports retain their distinct canonical grains and
wire contracts. Reuse current permission and command mechanisms; do not freeze
entitlements, actionable DBM state or mutable facts until the next refresh.

Freeze affected full before-results and perform focused backend output checks
while implementing; do not postpone correctness to the browser pass. Reuse
passing F1/F2/projection receipts. A new schema change needs normal migration
checks and rollback planning. Record one preparation's time/storage, where added,
so the batch does not conceal multiplication of BTR's 20-minute/440MiB cost.

Exit: all available required reporting paths and preparation delivered together,
with complete affected output checks. Preserve BTR's accepted run/generation and
behavior; do not rebuild it without an attributable dependency. Efficient paths
may be retained unchanged with evidence, not rewritten for uniformity.

### 3 Connect the existing frontend in one batch

Integrate the agreed ready-data responses across the included frontend consumers.
Remove proven duplicated calculations, conversion/copy loops, redundant requests
and grid rebuilding; retain cell formatting, selection and user interactions.
Do not replace grids or introduce a shared frontend framework. BPR's identity
mapper and RRR's direct assignments need no cosmetic rewrite. A ready-value
marker is useful only if existing contracts need an explicit compatible opt-in;
do not create a new metadata/descriptor protocol.

Run the affected frontend/backend builds and focused integration checks. Prepare
one coherent 3005 deployment with the previous backend/frontend images and selected
presentation data retained for rollback. Deploy only the changed preview services;
protect 3002/3003/3004 and shared infrastructure. Do not silently switch business
date or selected run to make an unavailable screen look populated.

Exit: available included consumers connected to the reporting contract on3005,
not separate per-module releases requiring renewed controller approval.

### 4 Inspect and correct module by module

Run one bounded final UI pass over the fixed inventory. Check completed response,
actual configured row population/series/horizon, displayed values and one affected
interaction per module. Related tabs with different contracts need their affected
branch checked; do not multiply every possible combination into a benchmark
matrix. Compare count/later page/export only where affected. Keep frontend response
wait/transfer and usable rendering visible; old rows/page labels are not proof.

Correct attributable integration defects, rerun only failed or newly affected
checks, and reuse passing evidence. Do not resume unrelated known legacy flaws
or the prior application-wide test/benchmark protocol. An impossible check needs
its exact input/permission/source disposition; no synthetic replacement or new
positive action trial. Finish with commit/push, deployment identity, rollback,
contract coverage versus implemented/validated coverage, and concrete remaining
upstream debt. Do not claim all screens delivered if an available required path
remains unfinished. Stop after this batch; daily ingestion, scheduling, automatic
publication activation and3004 cutover require their later scope.

## Source references

- Baseline and open obligations: [MIGRATION.md](MIGRATION.md), [BTR handoff](BTR_REPORTING_HANDOFF.md).
- Typed BTR builder/reader: [btr_snapshot.py](../mta/presentation/btr_snapshot.py); generation selection: [btr_reporting.py](../mta/presentation/btr_reporting.py).
- Current route dispatch and reconstruction: [views.py](../mta/presentation/views.py), [context.py](../mta/presentation/context.py), [dbm_read.py](../mta/presentation/dbm_read.py).
- Existing readers: [bpr_sql.py](../mta/presentation/bpr_sql.py), [rrr_sql.py](../mta/presentation/rrr_sql.py), [buffer_trends_sql.py](../mta/presentation/buffer_trends_sql.py), [insight_read.py](../mta/presentation/insight_read.py).
- Daily ownership and projection hooks: [temporal.py](../mta/runtime/temporal.py), [services.py](../mta/runtime/services.py), [admission.py](../mta/presentation/admission.py).
- Frontend behavior: [BPR hook](../frontend/src/VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BPR/useBPR.ts), [row helpers](../frontend/src/helpers/utils.ts), [DBM hook](../frontend/src/VectorFlow/Pages/MTA/DBM/DBMNormSuggestions/useDBM.ts), [Research hook](../frontend/src/VectorFlow/Pages/MTA/InsightsAndTrends/ResearchInsights/useResearchInsights.tsx).
- Remaining route denominator: [retained screen map](audit-2026-10-01/screen-connections.csv) and [frontend routes](audit-2026-10-01/frontend-routes.csv); these are historical inventories, not current runtime acceptance.
