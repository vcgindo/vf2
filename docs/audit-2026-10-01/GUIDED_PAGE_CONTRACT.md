# Guided Insights page contract

Stage2 whole-page read package P21; docs/MIGRATION.md alone owns status.
Preserve inherited frontend, F2, auth, MTO, June17 publication and resource bounds.
This map supplements PAGE_INTERACTION_INVENTORY.csv; it is not a new queue.

## Enabled branches and call owners

| Branch | Calls and producer facts | Interactions and background dependencies |
|---|---|---|
| Availability Trend (initial tab) | POST AvailabilityTrend, horison and filters; BTR.BPR dates/colours and SKU/location/pair attributes | Mount/filter effect fetches; horizon callback submits hvalue; location-type legend and Total, chart export/shared controls, filter apply/reset/chips. |
| Chronic Unavailability | POST ChronicUnavailabilityLoc/Sku with empty bodies in inherited service; BTR.ChronicUnavalabilityData plus descriptions/attributes | Child filter effect fetches location then SKU; chart/table controls and split pane. Grid toggle fetches ChronicUnavailabilityGridViewData (page1, configured page size, filters), joined to NMSAllItems; UI config ChronicUnavailability, grouping by location, local pagination/filters/columns, toolbar XLSX. |
| Availability Ageing Trend | POST AvailabilityAgeing, horison/ageing/filters; same history plus BTRSnapshotForUI.AgePhysicalInv | Initial age1, horizon9; child effect depends on filter only. Age handler changes local state but does not itself call API; horizon callback sends current age. Determine retained semantics before any repair. |
| DBM Norm Suggestions | Four POSTs DBMNormSuggestionLoc/SKUs/Pie/Ageing with empty bodies; BTR.DBMNormSuggestionsData, descriptions/attrs and DBMFinal.DBMMaster | Child effect runs four calls concurrently, then renders four chart/table views. Pie transforms counts to percentages locally. Link to DBM workflow; existing workflow proof reused, no new writes. |
| Excess Inventory Trend | POST ExcessInventorySku and ExcessInventoryValue with horison/filters; canonical ExcessInventoryDetails source requires exact retained owner/provenance | Two parallel child effect calls; two horizons/charts/Total legends. Both horizon handlers currently send old horizon state, not hvalue. Routes absent from modern urls. No silent empty fallback or frontend fix. |

Custom Screens is commented out in the tab roster, not an enabled delivery branch.
Tab change resets filters and returns chart view. onViewChange invokes chronic
Grid fetch even on return to chart; children may also fetch. Parent chart-filter
handler contains commented trend/age/excess calls; actual fetches belong to child
filter effects. Chronic and DBM service declarations send empty bodies: do not
mistake a parent argument for a transmitted filter.

Chronic grid uses GridViewTable with category GuidedInsightchronicunavailability.
Resolve its shared context/ref/layout/export dependencies before accepting toolbar
XLSX; the parent supplies a ref and empty export setters, child does not directly
attach that ref. Do not infer a broken export without tracing GridViewTable.

## Existing code and proof to reuse

Current nine insight routes dispatch to views.insight_data, which calls publication()
and uses whole BTRFinal/DBMFinal/ClosingState reconstruction. Selective reads must
preserve the exact native images and checksum/admission/scopes, not recalculate.
insights.py already implements selected projections. Existing13 variants and
parity/verify_insight_consumer.py are unfiltered terminal proofs, not all page
contracts. Reconcile their receipt/source hashes before reuse.

Canonical processor retained at D:/freshvcf-build/evidence/f3-insights-source-001/
VectorFlowAPIs.VectorFlow.Processors.Replenishment.InsightsAndTrends.GuidedInsightsProcessor.decompiled.cs,
SHA256 d2f578a2beda0b67226b3c85ae65d3a39fe732496237ee41f7c0a9b067f29249.
parity/insight_queries.py defines nine selected methods. Excess methods are present
in the same source but absent from that query map. The SKU SQL contains
from .dbo.ExcessInventoryDetails; this must be attributed, not silently repaired.

## Remaining reconciliation before implementation

Compare full configuration/types/actions to canonical; resolve shared chart/table
exports, filters and background payloads; map exact excess producer input and SQL
failure behavior; match each selective image to current reconstruction. Reuse
registered unfiltered receipts and prepare one complete affected contract batch.
Then verify enabled controls, actual client files, scope, stable selected run,
restart and matched performance. Independent SQL currently fails18456/823; that
blocks new independent parity and is not authority to substitute Python as oracle.


Shared GridViewTable reconciliation: it consumes the parent GridStateContext ref
and attaches it to VFTable, so the toolbar export ref IS connected. Its config
change effect calls GetState(GuidedInsightchronicunavailability); row/config/ref
changes apply returned column state. Do not repair this already-connected ref.

Canonical ChronicUnavailability configuration differs from the hand-authored
modern11-column list: selected visible9, correct location/skudesc positions,
canonical labels/alignment/NULL omission and joined DataType. Pinned SQL hashes
are the same config/type identities used for BPR. The complete9-column projection
is retained in mta/config/chronic_selected_ui.json for this batch.

Excess input distinction: mta.presentation.excess.produce and ExcessProjection
cover current-day Planning output only. Canonical CollectExcessInventoryDetails
retains previous ReportDates over its configured horizon before inserting today.
A current-day receipt therefore does not establish Guided history. No new facts,
replay, missing-to-empty default or silent historical extrapolation is authorized.


Actual pinned DLL filter captures: f3-stage2-guided-batch-001/Guided*-filters.json
contains52 expressions per branch, across9 branches. DBM loc/sku/pie/ageing final
captures use *-final-filters.json after applying the processor's explicit
parent alias replacement a.ParentWhCode -> db.ParentWhCode. Earlier raw captures
are preserved and do not certify final parent ownership. No SQL execution occurs.
Trend aliases sa/b/sla; ageing and chronic grid sa/la/sla; SKU and DBM ageing
b/la/sla. DBM/chronic chart request models have top-level filter groups, while
trend/ageing/grid use nested filters. Custom-only predicates are behind the six
standard-group call gate, exactly as the source. Existing generic _filter_rows
is not this contract (wrong operators, ownership, grouping and invalid-field
empty behavior), so it must not certify Guided filters.

Availability-ageing SQL joins BPR A and BTRSnapshotForUI B. Both contain Norm,
so unqualified Norm filtering must not be guessed to mean one of them. pic/ohic
remain unreplaced names in the captured Guided SQL. Resolve against full joined
schemas before claiming valid predicates; source aliases are not display names.

Dependency update: the legacy recovery chat reports SQL health restored after
the human's restart. Verify the retained June17 oracle setup when resuming SQL
proof; the healthy serving October2025 snapshot is not a matched input.
Current-day Excess85 and the independent shallow June6/7 trial projections do
not establish full-prefix Excess history. Assess the existing report producer
against accepted daily facts within the authorized read boundary; never combine
those independent trials or silently default missing historical populations.

Implemented batch now uses InsightPredicate over native join owners. Empty-schema
SQL checks of all468 captured cases agree on valid/invalid classification; they
do not prove populated results or HTTP failures. SQL connection recovery is locally
confirmed under the Fresh lease. Fourteen focused tests pass. Chronic chart
methods explicitly replace scalar null with an empty List<string>; the API now
preserves that conversion. Original13 unfiltered query strings remain unchanged.
Keep filtered values/scopes, error envelopes, Excess history, browser interactions
and matched performance as outstanding proof before delivery.
