# Guided Insights — whole-page prepared presentation performance

Human authorization4October2026: cover all existing user interfaces at
`http://localhost:3005/mta/insights-and-trends/guided-insights` in one coherent
implementation, using the preparation methodology accepted for BTR and BPR.
Starting implementation checkpoint194ade6; planning checkpointf8071c6 contains
earlier DBM-only research. This plan SUPERSEDES that DBM-only execution boundary.
Sole status tracker: `docs/MIGRATION.md`. No numeric token budget is supplied.

## Outcome and exact coverage

Deliver correct, faster usable presentation across ALL FIVE visible Guided tabs,
their existing panels, related table/modal views and the Chronic grid. Their
implementation/read integration is one batch, followed by one bounded whole-page
inspection. Do not stop after pie, table preparation, HTTP200 or backend timings.
Preserve accepted BPR/BTR, existing frontend/chart/grid components and all canonical
business results. Use existing retained April7 heavy data; simulate preparation
once as the output of a daily refresh. Actual ingestion/engine/daily orchestration
is later debt, not part of this trial.

| Visible tab | Included endpoint/panel contracts | Stable authoritative inputs |
|---|---|---|
| Availability Trend | AvailabilityTrend; date/location-type series; integer non-Black/non-NULL percentage; dynamic horizon/filter | BTR BPR history8483003 and BTR attributes |
| Chronic Unavailability | ChronicUnavailabilityLoc/Sku charts and their full tables; ChronicUnavailabilityGridViewData and existing local filtering/page/export | Chronic3340, BTR dimensions/descriptions; NMS97097 for grid |
| Availability Ageing Trend | AvailabilityAgeing; date Black/Red/White counts; horizon and minimum-age controls | Same BPR history; current BTRSnapshotForUI97299 qualifies historical keys, including duplicate snapshot multiplication |
| DBM Norm Suggestions | DBMNormSuggestionLoc/Pie/SKUs/Ageing; all four charts and complete tables/modal/downloads | Daily suggestions97097, DBMMaster97097, BTR dimensions; endpoint-specific descriptions |
| Excess Inventory Trend | ExcessInventorySku/Value; two date/location-type series, total legend, horizon/filter | Retained typed ExcessInventoryRow921651, importer dimensions |

Five tabs own ELEVEN implemented API reads. Custom Screens is commented out in
the visible tab list and renders only a placeholder; do not implement or activate
it. Main actionable DBM, other URLs, new workflows and application-wide rollout
are excluded. Existing per-panel download contracts remain supported; no new export.

## Research findings that determine the architecture

Shared dimensions do not imply shared fact grain. Current daily suggestion and
Chronic populations, historical BPR and Excess history have distinct source owners,
join rules, order and filters. Reuse typed dimensions, predicate infrastructure,
existing run binding and migration patterns; keep those fact boundaries intact.
No universal snapshot/table or mandatory relation for an already-efficient path.

The current suggestion pie profile97097 joined rows ->3 groups takes12.868s:
source context8.567s, Python join3.443s, scope/filter0.813s, aggregate0.046s;
database execute-wrapper0.576s excludes fetch/decode. Preparation removes the
full-population Python loading/join representation; scoped SQL aggregation stays.
Existing evidence: `D:/freshvcf-build/evidence/guided-dbm-preparation-research-20261004/pie-profile.json`.
Prior individual gateway observations: DBM15–34s; Chronic charts~6s/grid~20s;
availability15s/ageing23s; Excess~6s. They are not controlled legacy comparisons.
Availability's post-index plan is14.277s, JIT0.584s: JIT alone cannot explain that
remaining cost. Do not assume the BPR JIT remedy closes historical readers.
Controller's single current Chronic-grid profile3340 selected rows takes24.004s:
source context23.520s, join0.389s, scope/filter0.095s. Thus bounded source loading
or preparing the small served grain is more valuable than another Python join
micro-optimization. Evidence is in the same external research directory.

The frontend already runs suggestion/chronic pairs and Excess's initial reads in
parallel. DBM/Chronic chart wrappers send{} despite refetching on parent filter
changes; other routes send nested filters and horizon/age. Preserve actual payload
and canonical call gates; do not silently add new filtering or repair inherited
stale-horizon/count-label semantics as a performance change. Record attributable
mismatches and separate them from this performance acceptance.
DBM's small scoped pie percentages, chart-option construction and legend formatting
are legitimate UI work. Chronic converts numeric-looking values/copies/sorts;
history panels build series by repeated filter/map. Only remove unnecessary work
when actual supported display types/order can be reproduced exactly. No framework
or wholesale hooks/shared component rewrite.

## Architectural implementation boundaries

1. **Daily DBM suggestions:** one typed prepared common occurrence relation for
   suggestion INNER SKU INNER location LEFT pair INNER DBMMaster. Preserve source
   ordinals/raw filter owners/master parent/age/classification. Small site/SKU
   description INNER joins stay endpoint-specific and retain duplicate/exclusion
   semantics. Serve all four grouped results with scoped SQL. Never turn daily
   Guided outputs into live Apply/Sleep overlays or precompute permission combinations.
2. **Current Chronic:** prepare required stable current-row join/display ingredients
   once, or use equally efficient bounded typed SQL if measured evidence supports
   it. One narrow occurrence relation at most for this family. Keep NMS left-join
   grain of the grid separate from chart-specific description inner joins; do not
   multiply chart counts by grid NMS occurrences. Avoid loading97097 NMS rows merely
   to display3340 Chronic rows. Chart eligibility BRAge>RLT is not a grid exclusion.
3. **Availability history:** reuse existing typed history/date index. Bound date/scope
   before wide work, avoid unnecessary columns and repeated stable dimension joins.
   If those request-time joins remain the bottleneck, prepare one narrowly typed
   historical serving relation containing only required row/filter ingredients,
   preserving source/date/key/attribute occurrences. Shared by availability and
   ageing; snapshot age qualification remains exact and source-bound. Do not copy
   all descriptions/attributes into every historical row unless the required filters
   demonstrably demand that field. Use existing dimension relations/reference ordinals
   where cheaper; no new integer business keys. Do not aggregate away dimensions
   needed by arbitrary supported scope/filter/age/horizon queries. No per-horizon,
   per-user or per-filter snapshots. Record actual build/storage cost before judging
   a preparation successful; history scale is materially larger than daily facts.
4. **Excess history:** retain its producer-owned typed rows and importer filter owners.
   Efficient date-bounded SQL is valid. Correct measured join/access/assembly overhead;
   one narrow prepared relation is permitted only if repeated stable work remains
   and existing typed rows are insufficient. Never use BTR attributes instead of
   importer, borrow the June supplement, or derive Excess values from BPR facts.

These are at most four justified family-specific preparation boundaries, not a
requirement to create four new tables. Qualify occurrence grains first; no source
deduplication or fabricated empty data. Bound preparation to existing retained data,
preserve old serving data/readers, use one small explicit trial switch/binding where
needed and manual tested deployment. No generic preparation service/registry.
Typed rows hold display/filter values; JSON is only the final API envelope/metadata.
Do not reconstruct full-source Python bags or construct wide SQL JSON intermediates.

## Exact semantic requirements

Use current `insights`, `insight_filters`, `insight_history_sql`, `insight_response`
and pinned consumer contracts as the differential reference. Preserve full values,
types, omitted NULL keys, empty null-versus-list differences, duplicates, stable
source order/tie behavior, text comparisons and permission/parent weights. Daily
Guided source joins currently use exact Python keys; their predicate comparisons
and parent joins use their own normalized rules. Do not import BPR key semantics.
SQL MAX/text order must match the accepted source/Python contract, not an assumed
default PostgreSQL collation. Keep invalid/ambiguous canonical filters invalid.

DBM loc/SKU description multiplicity belongs only to those kinds; pie NULL group
count0/omitted suggestion key, raw API counts ->existing frontend percentages;
age NULL/No Suggestion exclusion and <2/<4/<7/else bands remain unchanged.
Location sorting by inc+dec and SKU frontend stable sorting/top10 preserve full
table rows. See the retained DBM contract details in GUIDED_DBM_PRESENTATION_PLAN.md;
its former execution sequence/exclusions are superseded by this plan.

Chronic chart count/colour groups require BRAge>RLT; grid uses complete chronic
rows with existing9column contract and local pagination, no invented server limit.
Availability percentage counts all non-NULL colours, numerator all non-Black,
integer truncation; age history uses current snapshot minimum age and exact join
multiplicity, not a recalculated historical age. Excess SKU counts White only,
value includes all colours; NULL amount/SKU and BIGINT overflow contracts preserved.
Date cutoff remains strictly ReportDate>publicationDate-horizon. Persisted run/date
and age are used; wall-clock October must not replace April facts.

## One coherent implementation and finite proof

1. Reuse this map and retained receipts. Freeze complete outputs for11routes at
   their actual UI defaults (shared horizon9, age1 unless runtime differs), broad
   actor plus ONE restricted supported-filter/date-window case per distinct family.
   Reuse passing receipts where the code/input contract is unchanged. Inspect at
   most one profile/plan per distinct remaining bottleneck; no broad inventory.
2. Implement all required preparation/read changes, then the minimal frontend
   batch. No renewed per-tab permission or intermediate pie-only delivery. Required
   migration/Django checks, real PostgreSQL verification, source binding/readback
   and mutation guards apply. Keep normal-publication admission/readers unchanged
   unless a shared affected helper requires a focused compatibility proof.
3. Prove complete before/after outputs, every field/order/occurrence, with focused
   PostgreSQL differential cases for join multiplicity, unmatched rows, NULL/types,
   permissions/parent weights, age bands and one nondefault date range. No count-only
   proof, expanded matrix, repeated passing proofs or historical full suite campaign.
   Frontend checks cover changed consumers and exact displayed transformation parity.
4. Build/deploy one batch of changed3005 services only. Keep accepted BPR/BTR
   switches/generations, selected run, other container identities and resources.
   Existing authoritative rows remain intact. Record rollback to194ade6 code and
   existing serving selection; retaining additive indexes/tables is acceptable.
5. Inspect all five tabs and Chronic grid, actual responses, charts/table toggles,
   one supported horizon/age change, one affected client-download contract per
   distinct changed data shape, and one restricted actor. Record known inherited
   behavior without inventing workflows or responsive-layout redesign.
6. Run THREE paired legacy/modern whole-page walks, alternating which stack runs
   first each pair. Each walk visits all FIVE tabs in the same order/settings and
   times each tab separately through completed gating responses, current rendered
   panels and responsive interaction. Include Chronic grid as its distinct timed
   transition. Match actual series/columns/full table populations; no5000-row
   requirement for grouped charts, no top10-only correctness substitution.
   Use the existing BPR matched-resource window DBs3GiB/2CPU, APIs4GiB/2CPU,
   automatic/finally restoration; no higher limits/copies/concurrent measurements.
   Each tab and Chronic grid must demonstrate lower modern median than legacy.
   Keep raw failures/refresh retries. If an exit fails, report that tab UNPROVED
   and the smallest correction/decision; never mask it with a portfolio average
   or repeat samples until favorable. No cold/concurrency/p95 benchmark programme.
7. Commit/push, update MIGRATION.md and existing handoff with coverage, real per-tab
   before/after results, preparation/storage costs, rollback and daily-producer debt.
   Complete only when whole authorized page exits pass or human explicitly accepts
   named residuals. Genuine source/browser-consent dependencies are reported while
   independent implementation proceeds; no bypass or fabricated sources.

## Hard exclusions

No new hidden Custom Screens, main DBM commands, other URLs, engine/fact/state/date
changes, live permission changes, new metadata protocols/frameworks/caches/registries,
universal table, integer-key/grid/chart replacement, DB copies/reset/repopulation,
resource escalation, new ports, MTO/3004 cutover, daily ingestion/schedulers/automatic
activation, unbounded capture/benchmark campaigns or unsolicited production hardening.
