# Cohort3 finite source and consumer map

Contract map, not a status tracker. Exact owner/source identities are in
COHORT3_SOURCE_PINS.json; source evidence is the read-only a002 inventory in
D:/freshvcf-build/evidence/cohort3-20261009-001. The failed a001 serialization
output is retained and is not an accepted inventory.

All paths below are relative to `/api/mta/`. Both dates use their own persisted
closing sources. No prior date or trace substitutes for a missing population.

| Layer or consumer | Typed source / stage | Existing route family | Disposition / proof |
|---|---|---|---|
| dbm_sources | closing/dbm images, command state and accepted actions | DBMData, DBMDataCount, DBM helpers/actions | Prepared typed readback and authenticated scoped consumption verified. No new Apply/Sleep action is authorized. |
| bpr | reports/bpr/BPR_Table, closing/importer and dbm attributes, typed transit, BPR remarks | GetBPRData, Count, Analytics, BPR GetExportDataAsync | Native sources present; approved empty presentation remarks verified; populated remarks and writes remain unproved. |
| btr | closing/btr attributes/trends and consumer category metadata | GetBTRData, Count, export | Exact generation and authenticated scoped readback verified. |
| planning_sources | importer attributes, persisted excess/fulfillment projections | GetPlanningDataCount and common planning setup | Preparation and authenticated consumer proof verified. |
| planning_grids / planning_charts / planning_custom | same date's planning sources and projections | GetPlanningDataGrid/Count/Graph/Custom for excessInventory and orderFulfillment | Prepared grids/charts verified; fulfillment custom remains explicitly blocked under final closure approval. |
| planning_git | typed InTransitData and GoodsInTransitTransporterMaster | same planning routes, category git | 28 typed source rows per date; preparation and available parent/count/chart/custom branches verified. Combined child grid remains blocked under final closure approval. Old missing-shipment declaration is stale. |
| planning_expedite_grids / planning_expedite_custom / planning_expedite_charts | typed projections, OpenExpediteRequests, transit | same planning routes, category expedite | Approved empty presentation requests verified. Do not invent TOP(1) winners. |
| planning_expedite_transit | transit and BPR remarks | expedite transit branches | Approved empty presentation remarks verified. |
| rrr | reports/bpr/vf_RationedReqReport and same-run attributes | RRRData/Count, RRR export | Normal RRR typed preparation and authenticated reads verified;32 full native/prepared comparisons pass. |
| separate RRR colour extension (not enabled by the 18-layer roster) | DailyRrrColourReceipt or OfflineRrrColourReceipt | colour OA data/count and RRROA export | Neither existing extension admits these Cohort2 owners. The smoke path consumes validation-only capabilities and an exact MTO0 exception for different owners; no transfer or trace backfill is authorized. These routes remain unavailable. The normal rrr preparation receipt cannot establish their source. |
| history | closing/btr trends/dates/attributes | DailyDataGraph, GetBufferTrendGraphData | Exact available dates retained; preparation and authenticated history proof pass. |
| research_availability | prepared history and own BTR sources | GetResearchInsightData, GetHistroricalAvailabilityBPRData | Dependent preparation and authenticated reads verified. |
| guided_history | BTRSnapshotForUI and own history | AvailabilityTrend/Ageing | Source present; retain actual coverage, no invented prior history. |
| guided_dbm | DBMNormSuggestionsData and NMSAllItems | DBMNormSuggestion Loc/SKUs/Pie/Ageing | Source present; legitimate emptiness must be reported from actual rows. |
| guided_chronic | ChronicUnavalabilityData and NMSAllItems | Chronic Loc/Sku/Grid | Source present; legitimate emptiness must be reported from actual rows. |
| guided excess consumers | exact retained history coverage | ExcessInventorySku/Value | Rolling-history deferral retained; no positive population fabricated. |
| bor | complete SupplierDispatchReq, opening SOB/MOQ, remarks | BOR grid/count/analytics/remarks/export | Deferred: ReqTopOfBlack/CumulativeTOBlack absent. Present SOB/MOQ do not repair that calculation source. |
| boroa | operational BORWithOrderAllocation, requirement/remarks/ColorSequence | BOR-OA grid/count/remarks/export | Operational current rows exist, so blanket missing-row wording is stale. Daily requirement/remark/ColorSequence binding and consumer recipe remain unavailable; deferred. |
| Pick streams | closing/complete LogisticPickList and PickListDataForTruckFormation, accepted owned files | DownloadReports/LogisticPickListReport, LogisticRemainingQtySummary, LogisticRemainingQtyDetails, TransportReqSummaryRpt | Typed/file owners present. All four full-byte authenticated transport positives pass on both dates under approved Decisions3–4. Existing file-order and tied-allocation qualifications remain exact. |

Access follows persisted cookie-JWT actor -> gateway application2 scopes and
download entitlement -> trusted identity injection -> MTA admission and consumed
attribute membership. Native attributes contain NULL SL/LL fields on both dates;
the previously approved terminal manifest does not bind these owners.

Existing coordinator, per-layer commands, source readers, operational verifiers
and append-only activation are reused. Existing strict source/recipe/seal identity
must remain valid; changing globally hashed recipe functions would invalidate old
seals and is not permitted as an incidental implementation step. Qualified policy
logic must be opt-in and preserve the old identity path.

Closure evidence: COHORT3_EVIDENCE_INDEX.json and COHORT3_HANDOFF.md. Final human
call_d2cf547683b94376b8cd74ea91487794 accepts the two named unavailable planning
routes only as blocked boundaries. The original FAILED consumer receipts remain.
This map is a contract/proof reference, not an additional status tracker.
