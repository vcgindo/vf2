# MTA report contract inventory

This is the report/source contract map for the released final G2 integration,
not a status tracker. Status, decisions and proof remain in the canonical
`F:/freshvcf/docs/handoff-3005/TRACKER.md`. Inventory baseline: `17525dc0`.
The controller's human-authorized sequence puts this work before final paired
native Full/split qualification. Frontend design, MTO and accepted runs remain
unchanged. Static reachability is not installation readiness or parity proof.

## Architecture decision

Keep the existing three delivery mechanisms: prepared UI/API reads and their
exports; fixed operational downloads; placement-driven RuntimeReports files.
Use one versioned deployment configuration to reference those existing owners,
without copying their business logic or inserting every UI report into the
legacy RuntimeReports table. Existing permission and source-readiness checks
remain authoritative. Configuration presence must never imply readiness.

A report requires its actual run, accepted phase/action revision, source images,
configuration and file/read generation. Continuations inherit prior accepted
effects; they must not regenerate BPR histories, Pick files or input archives.
Empty, unavailable and inherited are different states. A Full publication seal
cannot certify an intermediate phase. Current test-only declarations and exact
retained-run exceptions cannot become production defaults.

## Delivered UI/API surfaces

All API names below are below `/api/mta/`. Routes are in
`mta/presentation/urls.py`, frontend screen registration in
`frontend/src/app-routes.tsx`, permissions in `release/identity_catalogue.json`.
CSV means server `GetExportDataAsync`; Excel means the existing client grid
export. Neither is a placement-driven batch file.

| Surface / report key | Permission | API and existing owner | Scope and export contract |
| --- | --- | --- | --- |
| Planning | `MTA-P` | `GetPlanningDataCount/Grid/GridCount/Graph/Custom`; `views.planning_*`, `scoped_api._planning` | Full and scoped Excess/Order Fulfillment/GIT/Expedite branches with their own source guards; existing client exports. |
| BPR / `BPR`, `AdminBPR` | `MTA-BPR` | `GetBPRData[Count]`, `GetAnalyticsData`; `bpr_prepared`, `scoped_api.bpr_rows` | Full and accepted BPR/DBM composed views; CSV BPR and Excel. Remarks remain a separate workflow. |
| RRR / `RRR` | `MTA-RRR` | `RRRData[Count]`; `rrr_sql`, `scoped_rrr` | Full and phase-owned rationed/Pick sources; CSV RRR and Excel. |
| RRR colour bandwise / `RRROA` | `rrr-color-bandwise` | `GetRRROrderAllocationReportData`, `GetRRRAllocationReportDataCount`; `daily_rrr_read.read` | Full and phase views; CSV RRROA and Excel. |
| Buyer Order / `BOR`, `BuyerOrderReport` | `MTA-BOR` | `BORData[Count]`, `BORAnalytics`, `BORUIConfig`; `bor_sql`, `bor_sources`, `scoped_bor` | Actual configured BOR sources required; synthetic core-without-BOR denies; CSV BOR and Excel. |
| Buyer Order colour bandwise / `BOROA`, `BOR_OA` | `SCIH-BOR-color` | `GetBOROrderAllocationReportData[Count]`; `boroa_sql`, `scoped_bor` | Actual allocation sources required; same synthetic denial; CSV BOROA and Excel. |
| Supplier Wise Allocation | `SCIH-Supplier-Wise-Allocation` | `getSupplierWiseAllocationReportData[Count]`; `supplier_allocation.read` | Full native implementation uses authenticated supplier account and BOROA. Scoped dispatcher absent. Excel only. |
| DBM Norm Suggestions / `NormSuggestion` | `MTA-DBMNS` | `DBMData[Count]`; `dbm_read`, `scoped_dbm`, `scoped_dbm_view` | Full, inherited BPR view and accepted DBM view use explicit owners/revisions. Excel; Apply/Sleep remain typed action workflows. |
| BTR / `BTR` | `MTA-BTR` | `GetBTRData[Count]`; `btr_sql`, `scoped_btr` | Full or explicitly inherited phase BTR, never fabricated current BTR; CSV BTR, on-hand/pipeline layouts and Excel. |
| Buffer Trends | `MTA-BT` | `GetBufferTrendGraphData`; `buffer_trends_sql` | Full and guarded phase graph; no server CSV report key. |
| Research Insights / historical availability | `MTA-RI` | `GetResearchInsightData`, `GetHistroricalAvailabilityBPRData`, `DailyDataGraph`; `research_read`, history readers | Full prepared implementations. First two phase dispatch branches absent; DailyDataGraph phase branch exists. Existing grid exports. |
| Guided Insights | `MTA-GI` | `DBMNormSuggestionLoc/SKUs/Pie/Ageing`, `ChronicUnavailabilityLoc/Sku/GridViewData`, `AvailabilityTrend/Ageing`, `ExcessInventorySku/Value`; `guided_dbm`, `chronic_sql`, prepared history | Full optimized readers; phase `insight_data` dispatcher absent. Preserve history coverage/unknown-before-root rules; existing client exports. |
| Open Expediting Requests | `MTA-OER` | `GetOpenExpediteRequest`; `logistics_views`, `logistics_read` | Full and phase logistics binding; existing client export and separate remark workflow. |
| InTransit Whereabouts | `MTA-IW` | `GetInTransitWhereAboutsData[Count]`; `logistics_read` | Full and phase producer-owned transit binding; existing client export and transporter/remark history. |

The Full readiness roster is exactly the existing 20
`daily_preparation.REQUIRED_LAYERS`: dbm_sources, bpr, btr, rrr,
planning_sources, planning_grids, planning_charts, planning_custom, planning_git,
planning_expedite_grids, planning_expedite_custom, planning_expedite_transit,
planning_expedite_charts, history, research_availability, guided_history,
guided_dbm, guided_chronic, bor and boroa. `daily_publication` binds their
configuration/recipes/source owners. Keep this implementation roster as its
source of truth rather than maintaining a second independently editable list.

Inherited frontend links are not delivered report implementations:
OrderAllocationReport calls endpoints absent from modern URLs;
TotalRequirementReport initializes mock RRR-colour rows with its data call
commented out; SDR and Elephant Orders have frontend services/permissions but
no corresponding modern report routes. Do not count these as parity or silently
implement new business contracts under report registration. BOR/BOROA phase
read/export support also does not imply support for their phase remark writers.

## Fixed files and operational outputs

`mta/config/mta_report_paths.json` and the `report_paths/download_report` views
are the existing public catalogue. The four Pick keys are
LogisticPickListReport, LogisticRemainingQtySummary,
LogisticRemainingQtyDetails and TransportReqSummaryRpt. Full uses selected-run
files; scoped delivery uses accepted BPR custody in `scoped_pick_files`.
Permission is administrator or `mta-report-urls`, plus complete file population
product/location authorization. Bytes, filename and selected owner must agree.

InputData.zip uses the bound `native_input_archive`/`scoped_artifacts` owner and
requires administrator access. BOR_OrderAllocation.csv is conditionally exposed
from the scoped batch manifest, with BOR population authorization; its retained
terminal adapter preserves that original BPR file. It is not a RuntimeReports
row and not interchangeable with the similarly named dynamic allocation files.

The public path catalogue also names DailyDataUnavailabilityReport,
InvalidDataReport, seven NMS upload logs and ForceNormChangeUpload. The normal
download handler currently sends non-InputData keys to the four-key Pick reader,
so those catalogue entries alone do not establish working downloads.
`scoped_batch_files` produces FailedForceNormChanges, NoNormParentReport and
BPRExceptionReport operational artifacts; only BOR allocation from that bundle
is exposed by the current public scoped download branch. Preserve each native
conditional generation/absence rule and configured destination when connecting
these existing producers. A zero-row output is not always an absent file.

## Canonical RuntimeReports configuration

Canonical `GenerateRuntimeReports.bat` selects **Active=1**, matching Placement,
ordered by **Id**. VectorFLOWv4 invokes PostImporter, PostBPR, PostDBM, PostBTR
and Final. The same wrapper subsequently invokes ProvideDownloadableUIReports,
whose independent DownloadableUIReportSettings table controls the RRR ZIP.
That separate table must not disappear from configuration reconciliation.

The retained eight-row lead is
`D:/freshvcf-build/evidence/large-data-day1-benchmark-20261019/corrected-legacy-attempt-01/dbm-after-maintenance/final-runtime-report-config.json`,
SHA256 `1f036745abadf0224d9778a8fabf3cc93ad632d106a61127973f08b2baa9af55`.
Its case/owner provenance is retained in canonical tracker line5922. All eight
rows are active, CSV, comma-delimited, DeleteOldFile=true, destination
`%ReportsDownloadLoc%`, with NULL template names/locations. These facts qualify
the captured configuration, not its applicability to a new deployment or the
current approved empty TEST roster.

| Id | ReportName | Placement / output | Required source semantics |
| --- | --- | --- | --- |
| 2 | BOR WH Efficiency report | PostBTR; ZIP | BTR RationingHistory, today's Stock/GIT join, attributes and Pick join; strict today-45 lower bound, no upper bound. ParentNorm is numeric: NULL/zero selects BOR. TOR_B/TOR_R/TOY/TOG resolve to the Pick join, with its complete multiplicity. |
| 3 | RRR WH Efficiency report | PostBTR; ZIP | Same history/joins; nonempty ParentNorm selects RRR. |
| 4 | BOR_Color_Bandwise | PostBTR; CSV | BORWithOrderAllocation, colour ordering, descriptions and pair/SKU attributes. Not the existing fixed BOR CSV's column contract. |
| 5 | Chennai_BOR_OrderAllocation | PostBTR; CSV | Id4 projection/order with literal receiving location P041. Site-specific, not a global default. |
| 6 | Silvasa_BOR_OrderAllocation | PostBTR; CSV | Id4 projection/order with literal receiving location P001. Site-specific, not a global default. |
| 7 | Spike_Order_Dump | PostBPR; ZIP `Spiker_Order_Dump.zip` | Exact 12-column SpikeOrderData projection. Preserve the distinct report/file spelling. |
| 8 | BOR_OrderAllocationHistory | PostBTR; CSV `BOR OrderAllocationHistory Report.csv` | Accepted BOR allocation history, latest remark window partitioned by SKU/location, supplier join, descriptions/attributes and requirement join supplying AdvAllocDone; inclusive today-44 through today. No invented tie-break for equal remark dates. |
| 10 | TotalReqReport_YYYY-MM-DD | PostBPR; CSV `%TotalReqReport%` | Rationed report, SupplierDispatchReq and mandatory pair/SKU/location attribute joins; exact substitution/date contract. Retained last-generated name is not the next business date. |

Retain all 16 literal native fields, including misspelled `Delimeter`, HeaderList,
Query, BaseDB and LastGeneratedFileName. `ExportRuntimeReport.sql` updates the
last-generated name, emits configured headers, substitutes database variables,
then executes the query. File deletion/compression/copy and the independent UI
RRR ZIP wrapper follow their native owners. Template support must be explicit
when a deployment enables Excel; NULL templates here do not qualify Excel.

Pinned wrapper hashes:

| Canonical path relative to mta-engine | SHA256 |
| --- | --- |
| Engine/GenerateRuntimeReports.bat | `8e1c83c49dd7c12dad25c153c923caf28b01db03720fe8aa665a3df09a88c7e8` |
| Scripts/Common/ExportRuntimeReport.sql | `87622287f8f2b8032babb6f04e084a4d0906dc96130f770072a2a79f849a4cdb` |
| Engine/ProvideDownloadableUIReports.bat | `c72a24ce8fb1650fc0362b2016986ba14179362382d13891ef7dc34c6f432372` |
| Engine/VectorFLOWv4.bat | `6e70b6c7a6675ab1c8e38dfcba9a9a945f3da70aab673fc95ea7ce0e93f78d75` |

## Implementation and qualification boundary

There is also a clean-setup boundary: `initialization_contract.COMPLETE_OUTPUTS`
currently classifies RuntimeReports with calculated outputs and rejects every
nonempty initial population. `initialization_storage_v1.json` already defines
its 16 typed fields. Production registration therefore needs a deliberate
configuration-versus-generated-state distinction, not just a new file or a
relaxed scoped validator. Preserve the prohibition on seeding calculated
outputs and distinguish configured file names from last-generated runtime state.
Do not enable nonempty rows until their enabled execution/readiness path exists.

1. Bind a versioned deployment configuration to existing UI/readiness owners,
   fixed-file settings and the applicable RuntimeReports/DownloadableUIReportSettings
   records. Preserve old request digests and the explicit empty TEST validator.
   Nonempty production configuration needs actual query/file implementations;
   widening that validator alone would falsely certify readiness. Reconcile
   retained source/setup evidence before deciding any remaining site policy.
2. Connect enabled placement files to existing phase effects and file custody.
   Qualify each query against its exact source representation before execution;
   reuse existing projections only if columns, joins, NULLs, types, duplicate
   occurrences and ordering really match. No generic SQL interpreter or second
   calculation pipeline. Reuse grouped lookups and stream output where valid;
   do not repeatedly scan or materialize the same immutable source population.
3. Connect delivered report readers missing from scoped dispatch only through
   demonstrated current/inherited phase owners. Preserve supplier-account
   authorization and history date/coverage rules. Do not fall back to unrelated
   terminal selection, a stale cache or mock frontend rows.
4. Qualify configuration and compatible setup/upgrade, exact cells/headers/file
   names/member sets/dates, empty versus absent, permission/filter isolation,
   failure and retry without repeated accepted effects, restart and actual UI
   consumption. Use existing bounded component resources first; additional
   native fixtures/resources require their specific scope decision. Then use
   the completed configuration in the final paired native Full/split proof.

Registering a future report must identify its existing/new delivery mechanism,
permission, source grain and owner, phase/trigger and order, configuration,
query/projection/template, filename/encoding/compression, absence behavior and
required proof. Extend the owning catalogue and preparation/dispatch mechanism,
not an unrelated table. A configuration-only registration is not implementation
or acceptance. Matched latency/scale and G3 remain separately deferred.
