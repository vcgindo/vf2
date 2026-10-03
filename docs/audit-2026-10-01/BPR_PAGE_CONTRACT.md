# BPR page contract and QA inventory

Scope: Stage 2, existing BPR page on localhost:3005, selected June 17 publication.
This is a contract map, not a status tracker; `docs/MIGRATION.md` owns status.
Review the complete map, implement the authorized gaps as one batch, then execute
the interaction checks below. An endpoint test does not establish browser acceptance.

## Evidence and source boundaries

- Frontend: `frontend/src/VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BPR/{index.tsx,useBPR.ts}`;
  services in `frontend/src/VectorFlow/Services/MTA/SupplyChainIntelligenceHub/BPR/api.ts`.
- Shared controls: MTA `Common/MTAVFMultiFilter`, `Common/VFFilterContent`,
  `frontend/src/hooks/useSaveAllState.ts`, `frontend/src/helpers/BPRConstants.ts`,
  `frontend/src/components/VectorFLOW/layouts/BPRDailyAnalytics/index.tsx`.
- Canonical BPR processor: retained `f3-canonical-api-001` decompilation,
  SHA256 `68b9680373d7edf530fe5985f89d88d67b6fc4f7f1870112230cba9c7bb6b03b`,
  bound to DLL `0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346`.
- Modern reader: `mta/presentation/bpr.py`, `bpr_read.py`, `views.py`, `urls.py`.
  Seven native persisted images plus explicitly admitted terminal ancillary input;
  no recomputation or substitution of an earlier run.
- Reuse unfiltered proofs: `f3-bpr-terminal-003`, `f3-bpr-wire-001`,
  `f3-bpr-gateway-001`, `f3-bpr-restart-001`, `f3-bpr-ui-001` under
  `D:/freshvcf-build/evidence`. These do not certify filters, CSV or analytics.

## Interaction-to-contract map

| Interaction | Connection and expected contract | Required QA |
|---|---|---|
| Navigate to BPR; refresh; leave and return | Authenticated gateway; GetUIConfig AdminBPR, GetState BPR, GetLastRunDate, count and grid. Preserve selected publication and permissions. | Initial filter dialog, date, loading/error/empty states, return navigation and reload; compare actual requests and rendered fields. |
| Show All; Apply; Reset; cancel filter dialog | MTAVFMultiFilter supplies filters to grid/count and shared analytics. Apply resets page to 1. | Request payload, count, first page and analytics agree with canonical population; cancel does not apply staged changes. |
| Add Filter; selected chips; delete individual filter | Reopen current filter state; chip deletion calls onApplyFilter. | Remove each populated family; correct count/page and no stale rows/errors. |
| Supply-chain filters | LocationType lookup; location/parent type and explicit location selections. | Single/multiple values, parent join multiplicity and authenticated scope intersection. |
| Product and location filters | SKUDesc/WHDesc; code/description search; P1–3/L1–3; predicate add/remove and text operators. | Empty/multiple selections, each operator, NULLs, combined predicates; retained hierarchy only. |
| Custom attribute filters | AdminBPR configured fields; SKU/location/pair owner and numeric/text predicates. | Correct raw source owner, NULL behavior, multiple clauses and invalid field disposition. |
| Availability filters | Norm, virtual norm, stock, GIT, colour, category and tag predicates. | Actual deployed expression and source column; do not resolve invalid legacy aliases by invention. |
| Colour count/age; coverage | Shared filter payload, historical colour columns and coverage predicates. | Verify column ownership and canonical invalid cases before declaring support. |
| Historical and horizon controls | Historical component uses local state; horizon emits dates but generic report filtering does not by itself prove date filtering. | Trace actual submitted payload and canonical consumer behavior. Inert inherited controls are not permission to invent behavior. |
| Floating grid filters; clear grid filters | AG Grid client filtering of loaded page, distinct from server filters. | Text/number filtering, clear, displayed counts and no claim that client filtering searches all server rows. |
| Sort; column menus; pin/order/resize/hide; columns panel | Existing AG Grid and UI config; grouping/pivot/value controls suppressed for BPR. | Actual enabled menu actions, field formatting, NULLs, tags and locked action columns. |
| Pagination: first/previous/next/last; custom page size | GetBPRData paging with separate string count. Canonical key bag then final rejoin. | Boundary/empty/last page, page-size change, duplicate multiplicity and exact ordering; no invented tie-break. |
| Save Layout; Reset Layout; reload | SaveState/GetState/ResetState, reportname BPR, existing actor. | Persist/reload column state; reset and reload; no cross-user state leakage. |
| Row selection; multi-selection; split-pane resize | `intransit` JSON field drives lower detail pane; terminal admitted input is empty. | Select/deselect/change selection, placeholder and resize. Empty terminal input proves no positive logistics behavior. |
| Daily Data Graph; close/reopen; graph controls | DailyDataGraph SKUCode/WHCode; StockData, NormChangeHistoryData, MasterData, SuggestionHistoryData, MonitoringData. | Pair identity, every exposed horizon/overlay control, plotted values and modal lifecycle. Reuse source proofs, verify entry from BPR. |
| Norm history modal | Same selected-pair history response. | Dates, old/new norms, reason, ordering, empty case, close/reopen without stale pair. |
| Remark-history eye | GetRemarkDetails with SKU/location and forwardUsers; exact approved empty terminal remarks. | Empty history rendering, close/reopen and auth; denied admission remains unavailable. Populated history not certified. |
| Edit remark; Save Remark | AddRemark is a business write, outside Stage 2. | Inventory visibility only; do not submit, fabricate history or claim workflow acceptance. |
| CSV Export | GetExportDataAsync, reportName BPR, ISExport=1, stream=1; canonical unpaged export query and configured headers. | Full filtered population, all cells/types/NULLs/escaping/header order and download filename; do not substitute current page or grid final join. |
| Sidebar expand/collapse; analytics refresh | GetAnalyticsData name BPR with shared filters; seven OnHand and Pipeline colour counts and totals. | Correct canonical aggregate query/scope, filter refresh, zero cases, loading/error behavior and render. Route is currently absent. |
| Session refresh and scope | Existing gateway and identity handling. | Root/leaf/overlap API scope proofs plus available real browser actor; forged requested scope cannot expand authenticated scope. No auth redesign. |
| Restart/readback; latency | Same selected-run/digest, bounded MTA service and frozen comparison protocol. | Relevant contracts survive authorized restart; matched legacy/modern API and browser timings. Modern-only timings cannot prove performance parity. |

## Coherent implementation boundary

Authorized read-contract batch: BPR server filtering, unpaged CSV export,
sidebar analytics once canonical processor ownership is established, and the
already-uncommitted GetRemarkDetails route. Preserve frontend, auth, MTO,
calculation outputs, duplicate rows, typed NULLs and terminal admission checks.
Existing grid, lookup, history and layout contracts receive the interaction QA
above; change them only if an attributable mismatch is found.

Filter implementation must retain raw BPR (`a`), rationed (`vf`), SKU (`c`),
location (`d`) and pair (`sla`) owners. The actual DLL's 52 captured expressions
are in `f3-stage2-bpr-filters-001/dll-filters.json`: expression evidence only.
Count has different joins from grid; grid filters the candidate key bag before
paging and rejoins it afterward. Export has its own unpaged query. Neither count
nor export may be inferred from the final displayed page.

Sidebar source lead: read-only retained
`F:/vflow_integrated/.local-stage7/block3-one-pass/delivery-v1/AnalyticsController.cs`
dispatches to `VectorFlowAPIs.VectorFlow.Processors.Replenishment.Analytics.AnalyticsProcessor`.
The processor has now been recovered directly from the hash-checked deployed DLL:
`D:/freshvcf-build/evidence/f3-stage2-bpr-analytics-source-001/AnalyticsProcessor.cs`,
SHA256 `5aaa5d1d137789ca46a1d41608872c6b0074dcaabe9d914ad07412fbca200d6e`.
Its BPR branch applies GenericFunction report filters and authenticated SKU/location
CTEs, then left joins rationed rows, SKU/location/pair attributes and importer
SKULocStandardAttributes. It counts seven physical and dispatch colours from
`vf`, preserving joined-row multiplicity. It does not join remarks or trend rows.
Therefore analytics cannot be calculated by summing the displayed page or the
count endpoint's differently joined rows. NULL/unrecognised colours contribute
to none of the seven colour counts. The query returns one aggregate object in
the JSON array, including all-zero counts for an empty population.
The initial app-host invocation failed because .NET was not on PATH; invoking
the retained .NET 6 runtime explicitly completed successfully. No installation
or protected checkout modification was required. SQL execution proof remains open.

## Proof limitations to resolve or explicitly report

- Independent SQL oracle previously failed with 823/18456. No shared SQL repair,
  reset or restart is authorized; source or Python tests do not replace SQL parity.
- Browser provider disconnected during history verification. API success is not
  a substitute for the pending browser checks.
- Approved empty transit and remarks inputs constrain positive-case acceptance.
- Existing user confirmation concerns Planning Excel exports; it does not certify
  BPR CSV cell parity.
- No whole-page acceptance, matched performance claim or Stage 2 closure follows
  from this inventory. Finish the batch, then record each actual result once in
  the authoritative migration tracker.


## Background dependencies reconciled with whole-page inventory

Use PAGE_DELIVERY_CONTRACT.md / P10 in PAGE_INTERACTION_INVENTORY.csv for delivery
granularity. Current BPR hook has its initial data/config mount effect commented;
ActionToolBar route effect opens the initial filter dialog. Apply/Show All invokes
count, page1 grid and configuration without awaiting them serially. Configuration
changes map columns and filter options, then request saved BPR layout; grid-ready
and gridState changes apply order and size columns. Page changes fetch grid only;
page-size changes fetch the current page with the new size. Filter-chip removal
reuses onApplyFilter. No timer or polling exists in the inspected BPR hook.

Row selection reads the intransit JSON already on the row; there is no extra
logistics request. Daily graph explicitly requests the selected SKU/location,
then opens the shared dialog. Norm history is the same response's data. CSV toolbar
calls CsvExportMTA with BPR/current filters/ISExport=1/stream=1; the retained
hidden-grid Excel callback is a separate source candidate, not this toolbar path.
Layout reset ordering observation remains attributed separately in MIGRATION.
Full async race behavior and all dynamic/shared shell calls are not certified by
this static dependency trace. Do not infer whole-page acceptance from it.
