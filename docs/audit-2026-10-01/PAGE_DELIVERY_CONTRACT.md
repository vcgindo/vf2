# Page delivery and interaction contract

Prepared 3 October 2026. Adjacent execution artifact; docs/MIGRATION.md remains the ONLY status tracker.

## Authority and objective

The human requests whole-page delivery batches, including remaining Stage 2. This supplements STAGE_2_COMPLETION_PLAN.md and supersedes procedural fragmentation into per-click, per-endpoint or per-proof deliveries. It does not authorize new business behavior, frontend redesign, legacy repairs, data seeding, F1/F2 changes, authentication changes, additional services, or later-stage execution. Stage 3–5 groupings below are a prospective interface inventory, not authorization or a rewrite of their scope.

The default work is integration: consume the existing modern MTA outputs and owners, match the inherited request/response/configuration contracts, and connect the page. Do not classify every adapter as a new architecture project. Where a required fact or workflow owner really is absent, identify that precise dependency once rather than inventing data or another engine.

## Delivery rule

One page is one delivery package: all enabled tabs, charts, grids, filters, lookups, row actions, dialogs, downloads, configuration, lifecycle calls and background effects belong together. Planning is ONE page containing all its categories and parent/child/custom branches; do not create separate endpoint projects. Shared dialogs remain part of each parent page entry, while their unchanged internals reuse one proof. MDM subpages retain separate route entries but their dependent draft/review/approval lifecycle must be delivered together when Stage 4 is authorized.

One pass means a coherent implementation batch followed by consolidated verification, not a promise of bug-free code on the first attempt. Focused tests during implementation are allowed. Repair a failed affected check and rerun that check; do not restart the entire inventory, source discovery, screenshot collection, or proof chain. A click is a test step, never a delivery milestone.

## Current review and immediate sequencing

Snapshot: the executor is on BPR, not Expedite. Its current batch contains BPR filtering, export, analytics, remark-history reads and configuration. It found canonical AdminBPR Daily Data Graph configuration missing from modern configuration despite a working API. This is concrete integration work, and the full configuration comparison belongs in the same batch. Do not interrupt or discard its uncommitted work. BPR_PAGE_CONTRACT.md is its detailed page contract; incorporate it by reference rather than recreate it. Recent user instruction explicitly authorizes the executor to perform the existing 3005 login and displayed CAPTCHA itself.

Finish the active BPR authorized read batch first. Then finish pending Stage 2 page packages from MIGRATION: Guided and Research and any remaining recoverable gaps in Planning, RRR, DBM, BTR and Buffer Trends, respecting already-recorded dependencies and the current authorized sequence. Do not reopen passed checks without a relevant change. Do not count a read-only Stage 2 slice as whole-page workflow completion when Stage 4 writes remain.

## Inventory scope and honest completeness

PAGE_INTERACTION_INVENTORY.csv contains all 27 unique route paths from the retained 29 route declarations and all 129 retained API/helper declarations. C001–C129 retain the complete original call tracing, including unresolved/shared/MTO callers. Direct page links use exact traced source paths, not broad service imports. Additional current-source anchors identify local handlers, effects, timers, query hooks, storage and client exports. These anchors are candidates, not proof of runtime activation.

This is exhaustive for those retained route/call catalogues, NOT a claim that static scanning proves every dynamic interaction. Original unresolved declarations, dynamic downloads, shared authentication and configuration-generated controls stay in the denominator. Source offsets from older catalogues may move; resolve by symbol. At page entry, reconcile its current JSX/configuration/hooks once with these anchors and the actual enabled UI, including dynamic columns and shared imports. Add genuinely new contract facts to this artifact; record implementation results only in MIGRATION. Do not re-inventory the entire app for every page.

## Page delivery groups

| ID | Route / component | Delivery boundary |
|---|---|---|
| P01 | `/mta/master-data-management/control-panel` (ControlPanel) | Stage 4 prospective; linked MDM lifecycle, reads/writes/task progress/history/downloads. |
| P02 | `/mta/master-data-management/control-panel/view-modify` (ViewModify) | Stage 4 prospective; linked MDM lifecycle, reads/writes/task progress/history/downloads. |
| P03 | `/mta/master-data-management/saved-drafts` (SavedDrafts) | Stage 4 prospective; linked MDM lifecycle, reads/writes/task progress/history/downloads. |
| P04 | `/mta/master-data-management/task-status` (TaskStatus) | Stage 4 prospective; linked MDM lifecycle, reads/writes/task progress/history/downloads. |
| P05 | `/mta/master-data-management/task-pending` (TaskPendingForReview) | Stage 4 prospective; linked MDM lifecycle, reads/writes/task progress/history/downloads. |
| P06 | `/mta/master-data-management/control-panel/add` (AddRecord) | Stage 4 prospective; linked MDM lifecycle, reads/writes/task progress/history/downloads. |
| P07 | `/mta/master-data-management/control-panel/delete` (DeleteRecord) | Stage 4 prospective; linked MDM lifecycle, reads/writes/task progress/history/downloads. |
| P08 | `/mta/master-data-management/data-modification-history` (DataModificationHistory) | Stage 4 prospective; linked MDM lifecycle, reads/writes/task progress/history/downloads. |
| P09 | `/mta/supply-chain-intelligence-hub/planning` (Planning) | Stage 2 remaining authorized reads; existing action exceptions only; later writes remain explicit. |
| P10 | `/mta/supply-chain-intelligence-hub/bpr` (BPR) | Stage 2 remaining authorized reads; existing action exceptions only; later writes remain explicit. |
| P11 | `/mta/supply-chain-intelligence-hub/open-expediting-requests` (OpenExpeditingRequests) | Stage 3/4 prospective; all read controls together, writes gated by existing authority. |
| P12 | `/supply-chain-intelligence-hub/merchandising-grid` (MCGrid) | Retained mock/merchandising route; selection/disposition unresolved, do not silently accept or implement. |
| P13 | `/mta/logistics/intransit-whereabouts` (InTransitWhereAbouts) | Stage 3/4 prospective; all read controls together, writes gated by existing authority. |
| P14 | `/mta/supply-chain-intelligence-hub/bor` (BuyerOrderReport) | Stage 3/4 prospective; all read controls together, writes gated by existing authority. |
| P15 | `/mta/insights-and-trends/research-insights` (ResearchInsights) | Stage 2 remaining authorized reads; existing action exceptions only; later writes remain explicit. |
| P16 | `/mta/supply-chain-intelligence-hub/rrr-color-bandwise` (RRRColorBandwise) | Stage 3/4 prospective; all read controls together, writes gated by existing authority. |
| P17 | `/mta/supply-chain-intelligence-hub/bor-color-bandwise` (BuyerOrderReportColorBandwise) | Stage 3/4 prospective; all read controls together, writes gated by existing authority. |
| P18 | `/mta/supply-chain-intelligence-hub/SupplierWiseAllocation` (SupplierWiseAllocation) | Stage 3/4 prospective; all read controls together, writes gated by existing authority. |
| P19 | `/mta/supply-chain-intelligence-hub/order-allocation-report` (OrderAllocationReport) | Stage 3/4 prospective; all read controls together, writes gated by existing authority. |
| P20 | `/mta/supply-chain-intelligence-hub/total-requirement-report` (TotalRequirementReport) | Stage 3/4 prospective; all read controls together, writes gated by existing authority. |
| P21 | `/mta/insights-and-trends/guided-insights` (GuidedInsights) | Stage 2 remaining authorized reads; existing action exceptions only; later writes remain explicit. |
| P22 | `/mta/insights-and-trends/buffer-trend-report` (BufferTrendReport) | Stage 2 remaining authorized reads; existing action exceptions only; later writes remain explicit. |
| P23 | `/mta/supply-chain-intelligence-hub/rrr` (RRR) | Stage 2 remaining authorized reads; existing action exceptions only; later writes remain explicit. |
| P24 | `/mta/insights-and-trends/buffer-trends` (BufferTrends) | Stage 2 remaining authorized reads; existing action exceptions only; later writes remain explicit. |
| P25 | `/mta/dbm/dbm-norm-suggestions` (DBM) | Stage 2 remaining authorized reads; existing action exceptions only; later writes remain explicit. |
| P26 | `/mta/supply-chain-intelligence-hub/sdr` (SupplierDispatchReport) | Stage 3/4 prospective; all read controls together, writes gated by existing authority. |
| P27 | `/mta/supply-chain-intelligence-hub/eo` (ElephantOrder) | Stage 3/4 prospective; all read controls together, writes gated by existing authority. |

## Existing screen contracts, grouped into the page packages above

| Surface / nested interaction | Required contracts | Existing modern owner |
|---|---|---|
| RRR | GetUIConfig(RationRequirementReport); GetState/SaveState/ResetState; LocationType; GetLastRunDate; RRRData/Count; DailyDataGraph; GetExportDataAsync(RRR) | PickBand projection; rationed requirement; importer hierarchy/attributes; user layout |
| DBM current | GetUIConfig(NormSuggestion); GetState/SaveState/ResetState; DBMData/Count; DBMApplySelectedNorms; DBMUpdateSleepTbl; DailyDataGraph; client XLSX | Current Suggestions/DBMMaster/NormAcceptance/reasons; DBM hierarchy; existing RunCommand service |
| Daily history dialog | DailyDataGraph(SKUCode,WHCode) | DBM history and command overlay; importer-owned scope |
| BTR | GetUIConfig; GetState/SaveState/ResetState; GetBTRData/Count(name,filters,horizon,pagination); DailyDataGraph; GetExportDataAsync(BTR) | BTR Tech/Eco trend tables/date labels; BTR producer attributes |
| Buffer Trends | GetBufferTrendGraphData(bufferTrendType,Days); applicable shared metadata | BTR technical/economic colour histories |
| Guided Insights | DBMNormSuggestionLoc/SKUs/Pie/Ageing; ChronicUnavailabilityLoc/Sku/GridViewData; AvailabilityTrend/Ageing; GetUIConfig where used | BTR produced insight populations; DBM final; NMSAllItems |
| Research Insights | GetBPRData/Count; GetUIConfig(ResearchInsight); GetState/SaveState/ResetState; GetResearchInsightData; GetHistroricalAvailabilityBPRData; DailyDataGraph; BPR-based client XLSX | Terminal BPR input; BTR histories; rationed master; importer/BTR scope |
| Planning overview | GetPlanningDataCount(category-independent ten counts) | Importer attrs/master; standards; rationed report; spike/expedite; typed reports; terminal supplement |
| Planning Excess | GetPlanningDataGraph/Grid/GridCount(category=excessInventory,type); GetPlanningDataCustom; client XLSX | ExcessInventoryRow + native attributes/standards |
| Planning Fulfilment | GetPlanningDataGraph/Grid/GridCount(category=orderFulfillment,type); GetPlanningDataCustom; client XLSX | FulfillmentSummaryRow/DetailRow + native facts |
| Planning Expedite | GetPlanningDataGraph/Grid/GridCount(category=expedite,type); GetPlanningDataCustom; SubmitOpenExpediteRequest; client XLSX | ExpediteRow; PickPostRow; native attributes |
| Planning GIT | GetPlanningDataGraph/Grid/GridCount(category=git/wip,type); GetPlanningDataCustom; selected drilldown details/export | Approved empty terminal InTransitData; exact GIT producers; transporter directory distinct |
| BPR | GetUIConfig(AdminBPR); GetState/SaveState/ResetState; GetBPRData/Count; DailyDataGraph; AddRemark/GetRemarkDetails; GetExportDataAsync(BPR); actual reached transit/lookups | BPR_Table/vf_RationedReqReport; importer/DBM attrs; trend; terminal ancillary |
| Logistics whereabouts | GetInTransitWhereAboutsData/Count; GetTransporterDetails; GetRemarkDetailsForInTransit/SubmitRemarksForInTransit; config/layout; client XLSX | Dated InTransitData and movement/remarks; directory alone insufficient |
| BOR | BORData/Count; BORAnalytics where actually called; AddBORRemark/GetBORRemarkDetails; GetUIConfig(BuyerOrderReport); layout; GetExportDataAsync(BOR) | BOR opening/refresh facts and report relation must be mapped; application remarks missing |
| BOR colour-band | GetBOROrderAllocationReportData/Count; AddBOROARemark/GetBOROARemarkDetails; config/layout; GetExportDataAsync(BOROA) | Canonical BOR allocation collection/report; accepted fact mapping needed |
| Supplier-wise allocation | getSupplierWiseAllocationReportData/Count; config/layout; client XLSX | BORWithOrderAllocation; vf_ReqCalculation; ColorSequence and native attributes; MOQ/SOB are not this report |
| Elephant Orders | GetElephantOrderData/Count; UpdateElephantOrderDueDates; config/layout; client XLSX | closing/orders/ElephantOrders; approved due-date workflow and next engine input |
| Open expediting requests | GetOpenExpediteRequest; AddRemarkForExpedite/GetRemarkDetailsForExpedite; Planning SubmitOpenExpediteRequest; config/layout; client XLSX | New application facts and deployed workflow; not derived from count alone |
| RRR colour-band / order allocation | GetRRROrderAllocationReportData/GetRRRAllocationReportDataCount; GetOrderAllocationReportData/Count; RRR_OA export/config/layout | No fabricated combined order-allocation output |
| Total Requirement | RRRDataCount; generic UI config/layout; client XLSX; no active grid-fetch in inspected hook | No demonstrated genuine report-data connection |
| Supplier Dispatch | GetSupplierDispatchReportData/Count; generic UI config/layout; client XLSX | SupplierDispatchReq generated by GenSupplierWiseReq; vf_RationedReqReport, MOQ/SOB and producer attributes |
| MDM lifecycle | GetMasterUIConfiguration; GetCount/GetMasterData; draft POST/PUT/GET/DELETE; allDrafts; draftCount; GetSeasonalityDetails; Modify/Add/RemoveMasterData; pending/status/task details/count/download; PostMasterAfterApproved; DeleteTask; GetSkuLoc; GetTaskMastersHistory | Application-owned drafts/requests/approval/history; approved controls feed execute_day; immutable runs remain untouched |
| Admin configuration and validation | GetAllUIReportConfig/GetAllUIMDMConfig; EditEnvironmentConfiguration; UpdateUIReportConfig/UpdateUIMDMConfig; GetAllPermissionsAdmin/AddPermissionsAdmin/BulkUploadPermissions; /api/validate-master/* | Application config/permissions; never calculated state |
| Configured report downloads | GetAllReports; DownloadReports/{reportName}; generic /download-excel helper separately unproven | Configured file catalogue + canonical runtime-report producer |
| Shared metadata/layout/gateway | GetEnvironmentConfiguration; GetLastRunDate; LocationType; GetUIConfig; GetState/SaveState/ResetState; reached SKUDesc/WHDesc; authenticated cookie | CalculationRun; attribute column; pinned config/catalogue; UserReportLayout; gateway-owned identity |

## Interaction checklist inherited by every page

Apply only where the control or background operation exists; name an inapplicable
item once, with source justification. This checklist is part of the page package,
not a queue of individual tasks.

| Interaction group | Complete contract to review together |
|---|---|
| Entry and initialization | Route/menu/permission gate, application selection, direct navigation/reload, configuration and column renderers, selected run/date, initial filter defaults, initial data/count/analytics and saved layout; ordering and failure dependencies between calls. |
| Filters and selection | All configured field types/operators, cascading SKU/location/hierarchy lookups, dependent dropdown refresh, apply/reset/clear, row and multi-selection, stale selection after filtering, shared global versus grid-local filters. |
| Views and navigation | Every enabled tab/category/parent/child/custom branch; chart/grid switches, back/return, expanded panels, legends, horizon/date changes and preservation/reset of page state. |
| Grid behavior | Count versus row population, pagination and last page, page-size changes, source-defined sorting, duplicate bags, NULLs/types/formatting, dynamic/action columns, grouping/pivot only where enabled. |
| Detail interactions | Row click/double-click/context actions, daily graph and norm/history dialogs, selection-driven lower panes, drilldowns, close/reopen and stale-pair prevention. |
| Layout | Load/save/reset, hide/order/resize/pin where enabled, refresh/relogin persistence, report/tab layout keys and actor ownership. |
| Downloads | Toolbar, row, menu and background-generated downloads; correct trigger and method, full filtered population versus current page, headers/layout order, filename/MIME, actual file contents, generation progress/status and failure. Include client-only Excel/CSV exports. |
| Writes, when authorized | Validation, confirmation, cancellation, success, rejection, duplicate submission/retry semantics, authoritative owner and transaction, persistent readback, reload and downstream effects. Inventory out-of-stage writes without executing or claiming them complete. |
| Nonvisual lifecycle | Mount/effect calls, query cache keys, invalidation/refetch, dependent requests, debounce/timers/polling, pagination-triggered counts, background analytics, local/session storage, session expiry/refresh, late response races, cancellation/unmount and stale data after switching. |
| Async jobs, when present | Start/upload/validate request, progress polling or event subscription, terminal success/failure, reconnect/retry and artifact retrieval. Inspect actual implementation; do not invent a worker, queue or WebSocket where none exists. |
| Failure and empty state | Distinguish empty success, denied scope, missing source, inherited defect and service failure; loading completion, recoverability and navigation after a failed branch. |

Shared shell: inventory auth/session calls, permitted URLs, environment metadata,
last-run date, common config/lookups, report-download menu and layout services
once. Attach their actual use to each page. MTO/shared callers in the CSV are
preservation dependencies, not authority to alter MTO. Final combined runtime
and existing MTO paths belong to Stage 5, not a duplicate MTA implementation.

## Contract review fields (one compact page packet)

For each distinct operation/branch, resolve these from existing evidence and
source; do not write an individual prose report per row:

- Trigger including invisible effect; exact hook/handler and HTTP method/path,
  payload defaults/optional fields, configuration name and layout key.
- Gateway actor/scope and denial behavior; producer/service/projection/command
  owner, selected run/date and genuine prerequisite data population.
- Exact response nesting/status/error, column and action metadata, numeric/string
  types, NULL omission, duplicate multiplicity and source-defined order.
- Distinct grid/count/export/analytics queries: never infer one from another when
  their joins/filtering differ. Canonical source identity and reusable proof.
- Persistent side effects, refresh dependencies and externally observable result;
  for writes, expected state transition and replay/idempotency behavior.
- Acceptance checks and known decision/blocker. Link existing proof; results and
  completion status live only in MIGRATION.

Do not demand a new specification where these facts are already available.
BPR_PAGE_CONTRACT.md is the existing example. For the next page, fill only its
missing facts in this page grouping before implementation; no new standalone
contract framework or generic compatibility layer.

## One implementation and verification cycle per page

1. **Assemble once:** reconcile the page's inventory, known contracts and current
   tracker gaps. Identify all recoverable mismatches together. Separate truly
   absent facts from unconnected existing owners. Escalate a material missing
   authority/input immediately; continue independent work within the same page.
2. **Implement the batch:** request/response adapters, configuration/action columns,
   lookups, filters/counts/analytics, export and read-model access together. Reuse
   modern owners and existing shared helpers. Use focused developer checks as
   needed; no deployment or checkpoint after every function or click.
3. **Verify coherently:** complete affected canonical API/data comparisons; one
   representative authenticated traversal exercising every distinct interaction
   family and dynamic branch; actual download content; state/readback where
   applicable. Exhaustive semantic cases can be API tests; browser testing need
   not repeat every equivalent filter combination. Missing screenshot alone is
   not failed proof. API success alone is not page success.
4. **Measure the real page:** identify slow request/render paths, correct attributable
   in-scope bottlenecks and compare before/after outputs and timings. Reuse the
   shared matched-performance setup; the frozen legacy equivalence/protocol remains
   mandatory. Modern-only diagnostics do not certify legacy performance parity.
5. **Deploy/check once for the coherent batch:** normal authorized MTA-only boundary;
   verify admission/readiness and affected persisted reads after required restart.
   Reuse unchanged integrity/isolation evidence; do not restart for screenshots.
6. **Report one outcome:** page behavior delivered, remaining exact exceptions,
   proof references and commit/image in MIGRATION. Commit/push at this logical
   boundary. Incidental recovery checkpoints are permitted when needed to preserve
   work, but are not separate delivery milestones. Fix failures and rerun affected
   checks within this cycle without reopening all discovery.

A page with an unapproved missing requirement remains partial/blocked. Once its
permitted work is exhausted, group unresolved decisions into one concrete request
with evidence and recommended treatment, then continue an independent authorized
page only with that disposition recorded. Never leave a known blocker cycling
through screenshots and receipts. Do not implement Stage 4 writes to claim a
Stage 2 page complete. The final Stage 2 assessment retains every missing exit.

## Communication and future reviews

Progress updates should report a material implemented behavior, a diagnosed cause,
a meaningful verification result or a real blocker. Normal tool progress can be
brief; do not announce each click as a new delivery. Required periodic reviews
summarize the active PAGE, substantive change, remaining acceptance and drift.

Reviewers should inspect the current page delta and its recorded outcomes, not
request fresh inventories or duplicate receipts. Ask: did a user-visible contract
or its necessary background dependency become operational? If not, is work fixing
an evidenced gap or merely repeating observations? Course-correct only the latter
or a concrete scope/acceptance violation. Do not stop useful debugging, required
semantic comparisons or a relevant configuration correction as 'ceremony'.

## Surgical clarification: Guided history serving cost — 3 October 2026

This clarification implements the human's request to incorporate the architecture
review without disrupting Stage 2 closure. It governs only the current Guided /
Excess read-path delta. It creates no new stage, tracker, architecture workstream,
acceptance waiver or requirement to redesign Stage 1. Current human approvals,
Stage 2 boundaries and the frozen parity/performance requirements retain priority.

- Continue the active Guided page batch and its existing independent comparison,
  publication and consolidated QA sequence. Preserve passing evidence and the
  already-made chain-lookup/model-field consolidation; do not redo those steps
  merely to acknowledge this clarification.
- Incorporate one bounded serving-cost diagnostic into the existing page QA:
  measure the configured Excess HTTP path and one unaffected MTA read, retaining
  query count/time and end-to-end timing against a comparable pre-change baseline
  where available. Include the admission wrapper, not just the pure consumer.
  Reuse existing measurements. If a baseline is unavailable, state that limit;
  do not redeploy/restart merely to manufacture one. This diagnostic does not
  replace the required matched legacy API/browser performance evidence.
- If measurements meet the existing acceptance requirements and reveal no
  unresolved regression, stop optimizing. If repeated work materially impedes
  those requirements, correct only the attributable path: reuse already-validated
  metadata within the same operation/request and avoid fetching unused fields.
  No cross-request cache, new framework, schema redesign or weakened checking is
  authorized by this clarification. Horizon/scope pushdown or a deeper admission
  change requires a specific measured cause and bounded proposal before expansion.
- Preserve source/row digests, run/date/predecessor identity, projection/config
  binding, command integrity, permissions and atomic publication. Retest affected
  complete outputs and relevant rejection behavior after a change; reuse unrelated
  passing proof. Do not remove checks simply because they cost time.
- Keep the approved June 6–17 / terminal-run binding exact. In the existing
  MIGRATION handoff, record that automatic next-day publication, advancing
  retention and general publication replacement are not certified by this
  preview-specific implementation. This is a later-stage assessment item, not a
  new Stage 2 feature requirement or authorization for Stage 3–5. Conversely,
  required current Stage 2 performance/behavior cannot be deferred under that label.

Report these results once with the Guided page outcome. No separate checkpoint,
inventory, proof series or per-request delivery is requested by this clarification.
The directive below is the original BPR-era handoff; it must not be interpreted
as an instruction to interrupt the now-active Guided batch and restart BPR.

## Original executor direction (BPR-era handoff)

Adopt PAGE_DELIVERY_CONTRACT.md and PAGE_INTERACTION_INVENTORY.csv for remaining
Stage 2 and future authorized work. Finish the active BPR read-contract batch;
reuse BPR_PAGE_CONTRACT.md and preserve your current changes. Include the full
configuration/action-column reconciliation, filters/count/export/analytics,
permitted details/history, layout and background refresh dependencies in one page
outcome. Do not turn each interaction into a separate discovery, notification,
deployment or QA milestone. Use the page-grouped inventory to scope the next page
once, implement all permitted gaps together, then consolidate API/browser/file/
performance and required restart proof. Resolve the existing login/CAPTCHA yourself
as the human authorized. Report actual behavior and precise blockers in MIGRATION;
no extra status tracker. Reuse unchanged evidence. This is a delivery-granularity
instruction, not authority to change F1/F2, seed data, repair legacy, redesign the
frontend, modify authentication/MTO, or open Stages 3–5. When existing constraints
prevent a required interaction, present one evidence-backed decision instead of
recapturing the same failure.
