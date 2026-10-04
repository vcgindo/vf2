# Planning consumer and preparation contract

5 October 2026. Fixed scope under PLANNING_PRESENTATION_RESEARCH_PLAN.md.
This is a contract map, not a status tracker; execution status stays in MIGRATION.md.
All rows refer to the sealed April 7 fixture. Existing page inventory and frontend
destinations are reused. Source qualification is not acceptance of derived rows.

| Consumer | Existing contract and grain | Preparation boundary | Live read and proof |
|---|---|---|---|
| Landing counts | planning_overview.counts: ten distinct count contracts, string values; normal and custom count grains differ | Reuse family eligibility occurrences below; do not infer counts from paged grids | Product/location permission bags; exact broad/restricted ten counts; no zero fallback for unavailable families |
| GIT parent default/grid/count/export | git_read.NORMAL_COLUMNS; positive critical GIT, child-location permission ownership; parent descriptions and transporter multiplicity | Canonical derived GIT fact plus exact normal-view occurrence references | Filters/count/order/page before selected response expansion; full normal values and export; parent graph is not implemented by legacy |
| GIT child default chart | Location and transporter chart sections are independent grains; graph ignores filters | GIT source/display membership; transporter source remains separate | Live parent/location scopes and canonical aggregates; positive aggregate GIT does not imply nonempty shipment detail |
| GIT child location/transporter grid, counts | Combined grid contains canonical SQL207/8120; counts have separate location/transporter joins and filter limitations | Prepare valid independent ingredients only | Preserve attributable dependency for invalid combined query; do not treat legacy concealed empty success as healthy parity |
| GIT custom/export | Shared CUSTOM_COLUMNS; ignores filters/type | Exact canonical custom occurrence grain, not normal-grid totals | Scope/page and native NULL omission; genuine empty transporter data is allowed only with source proof |
| Expedite parent default charts | expedite_charts: critical, receiving, nil-stock, chronic, pre/post; receiving uses window sums then DISTINCT | Prepare location-display matches, child/parent matches, parent-master membership and PickPost child multiplicities once | Live scope-weighted SQL aggregates/window operations; unchanged response transform; receiving-label exception requires demonstrated scope transfer |
| Expedite parent dispatch/availability grid and counts | parent_rows LEFT joins; availability adds parent BPR master; counts use INNER dimensions/standards and different eligibility | Separate exact grid and count occurrence references; retain source fact and filter owners | Paged string-valued rows, NULL omission, canonical RN and ambiguity denial; unpaged SQL156 remains unresolved, not silently repaired |
| Expedite child default charts | Child critical uses parent-row matching/IsParent; receiving uses IsReceiving; no parent-master fields consumed | Exact child critical/receiving and PickPost ingredients | Live child-direction permissions; do not load unrelated BPR master |
| Expedite child dispatch/availability grids, counts, details/export | child_rows: dispatch LEFT joins, availability INNER joins; permissions belong to ParentWhCode; request/transit overlays are independent | Stable dimension occurrences only; never freeze request state | April OpenExpediteRequests must be acquired/qualified; June17 empty-history permission does not transfer. Numeric wire values and existing ETA remain exact |
| Expedite custom | NMS/BPR/site grain, canonical NULL omission and RN | Existing retained nonempty sources or exact empty-NMS disposition; no inferred IDs | Scope/page; terminal-only stable-order exception is not automatically April acceptance |
| Excess default location/product charts and expanded table export | excess_views.chart_queries: current-day facts, description joins and scope aggregate BEFORE attribute join | Current-day fact references, description membership and attribute references at separate grains | SQL COUNT/SUM with canonical overflow, NULL sums and ordering; preserve four chart datasets and response types |
| Excess normal grid/count/export | Current-day fact INNER SKU/location descriptions and attributes/pair; LEFT parent description | Exact expanded grid occurrence with filter-owner references, normalized lookup keys, display values and producer ordinals | Scope/filter/count/RN/page in SQL; serialize selected rows once; preserve duplicate expansion and unresolved tie semantics |
| Excess custom/export | NMS INNER parent description/standard; different grain and NULL omission | Narrow custom occurrences, not normal-grid reuse | Filters ignored as canonical; scope/RN/page |
| Fulfillment default location/product charts and table export | fulfillment_charts: summary Coverage and real detail OrderStatus grains; description aggregate before attribute join | Summary/detail remain distinct; prepare description membership and attribute references without multiplying aggregate grain | COUNT(OrderNo), SUM(PendingQty), scope-weighted SQL aggregates, native overflow and NULL behavior; unchanged first-three-band response rule |
| Fulfillment normal grid/count/order details/export | Summary INNER description/attribute/pair occurrences; real order details keyed by canonical SKU/location | Summary display/filter occurrences; retain indexed independent typed order detail rows and ordinals | Scope/filter/page summary first, then fetch selected-pair details; preserve OrderNo/date/NULL values and nested transit wire contract |
| Fulfillment custom/export | Summary LEFT NMS and parent description; NULL omission | Distinct custom occurrence grain | Scope/page and explicit conflicting-NMS ordering denial; never manufacture order identity |

## Derived source qualification

Canonical `F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR/GenerateGoodsInTransitMaster.sql`
inserts one occurrence per positive-GIT rationed row INNER JOIN importer standard
attribute match. Status is the empty string; Tags/Price come from standards;
PipelineInventoryPen/Color come from DispatchPen/Color. IsReceiving is 1.
IsParent becomes 1 iff another inserted row has the same SKU and ParentWhCode
equal to this row's WhCode. This update is existence, not duplicate expansion.
Target SQL column types/conversions and matching-day bags must be checked before loading.

Canonical `Scripts/BPR/01. ImportData.sql` copies SKUCode, WhCode, Norm,
ParentWhCode, SKUIntroDate from importer MasterData into BPRMaster, without DISTINCT.
Preserve duplicates and target conversions. Neither operation runs either engine.
Derived rows receive their own source-bound receipt; the imported receipt roster
must not be modified to pretend those outputs were imported.

Read-only qualification against the retained owned SQL databases
`VFTEST_Fresh_S2_VM_20261003_002_Importer` and `_BPR` established complete
five-field BPR master bag equality (97,097 occurrences) and complete 17-field GIT
master bag equality (2,567 occurrences), including duplicate multiplicity.
GIT Price uses the canonical SQL int conversion; penetration is decimal(10,2).
These are bag proofs, not invented deterministic source ordering.
`dbo.OpenExpediteRequests` exists in the retained BPR database and has zero rows.
The separately acquired nine-column April input has SHA256
`0aeb5e2b97699d7516bf15850a1d1b0aa450522e362a765bd413615f1fb3c3c1`.
Its eventual admission must bind this actual acquisition and backup provenance;
the existing June17 opt-in must remain unchanged.
Evidence: `D:/freshvcf-build/evidence/planning-prepared-20261005-001/`
`source-schema.json`, `derived-source-comparison.json`, `april-request-history.json`.
PostgreSQL prepared-row equality and complete endpoint/order proofs remain required.

## Shared constraints and verification

Stable string matching is resolved once during preparation. Retain raw display
values and source ordinals; normalized lookup keys do not authorize changed
case/trailing-space comparison semantics, NULL matching or an invented tie-break.
Each added relation must identify its exact grain and consumers above before DDL.
Use existing immutable fixture preparation/seal patterns, not a new registry.

For each available family: one complete broad and relevant restricted comparison,
one meaningful filter/page case, affected duplicate/NULL/order tests; selected
Fulfillment details are mandatory. Default UI journeys use the existing configured
page size. One before and final matched journey per destination, supported final
grid/detail inspection and actual exports; only an evidenced failed/noisy path
gets the plan's single corrective recheck. Backend timing alone is insufficient.
Blocked consumers retain precise source/SQL dispositions and cannot count toward
six-destination completion. No action/request write workflows are included.
