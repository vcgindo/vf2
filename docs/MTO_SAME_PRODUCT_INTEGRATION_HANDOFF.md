# Existing MTO in the 3005 product — bounded verification handoff

10 October 2026. **Infrastructure is connected; all-feature API/UI visibility remains unproved and active.** Only the explicitly approved navigation role was added: role3 for user2,55 existing permission links. No source, service, business data, credentials or existing scope grants changed. No rebuild, restart, business-day call, workflow write or new port was performed. The human stopped the separate performance tranche; that incomplete evidence remains in UI_PERFORMANCE_PARITY_REPORT.md and was not used as a prerequisite for this check.

Evidence: [runtime identities](D:/freshvcf-build/evidence/mto-same-product-20261010-001/runtime-identities.json), [running nginx routing](D:/freshvcf-build/evidence/mto-same-product-20261010-001/nginx-routing.conf), [read-only checks](D:/freshvcf-build/evidence/mto-same-product-20261010-001/read-only-proof.json). The read-only proof explicitly distinguishes runtime observations from configuration declarations.

| Boundary | Result |
|---|---|
| Existing MTO image | Running `sha256:bc5a6fb828bc9e0123a837763c9d3cbf6f4f8e8fbd1e91f10c73a0e1c373ab5f`, started2026-10-09 06:05:24 UTC, not restarted or OOM-killed |
| Gateway image | `sha256:1c226612541b36f135a352e2d626cee778ca479c55b5f302447ff5f7eca7e8e0`; effective `MTO_BACKEND_URL=http://mto:10015` |
| Frontend image | `sha256:042d7a51371827ecc789cdca29b4f13fb281c9def8f9932b58cd04b86e6677b1`; existing public127.0.0.1:3005 |
| API routing | Running nginx `/api/` forwards to user-service:10016. Retained gateway MTO mapping uses application3 and the MTO interceptor. Public `/api/mto/getPlantMasterData/` rejects an unauthenticated request with401. This is denial proof, not an authenticated positive read. |
| MTO database | Effective `freshvcf` database / `mto` schema on owned freshvcf-test-postgres-1; internal `/healthz` and `/readyz` both200. Readiness checks connectivity only. |
| Business prerequisites | PlantMaster, CCRMaster, BufferMaster, OrderData, MTOOrderData, MTOLineItemData and DailyWorkingCalendar each contain0 rows. Empty data is allowed by the latest human amendment; populated workflow/persistence acceptance is deferred and is not a prerequisite. |
| Current broad account | Actor2 now has the exact approved55 MTO navigation permissions through role3; application3 product/location assignments remain empty. Existing MTA scopes were preserved. Actor1 is admin but has no ordinary role MTO navigation/scopes; effective admin navigation was not inferred from that fact. |
| WebSocket configuration | Running nginx `/ws/` forwards to mto:10015 with Upgrade/Connection headers. Redis host is configured. No WebSocket-dependent business journey was possible, so runtime WebSocket acceptance is unproved. DDQ UI remains disabled. |
| Browser journey | Same-login MTO landing, every existing feature screen/API, truthful empty/error state and MTA return remain unproved. Chrome's existing tab control detached; a new3005 landing tab attempt timed out. No further browser recovery campaign was opened at that checkpoint. A later single normal Chrome recovery restored authenticated3005 landing for Stage2 VM broad reader; only Replenishment cards are visible and MTO cards are absent. |
| Protected MTA | Container/image/start time and selected fixture SHA256`a6b28597dc5ec7d5e013521f548da0f90512d64834d3c8e869225033fc2a3f3d` remain the recorded identities. No mutation was made. Final public `/readyz` returned503: identity and catalogue true, MTA false. Running container identity is not a health PASS; cause was not diagnosed or attributed to this no-change check. |

## Current bounded result — incomplete

The human approved the exact navigation proposal and it was applied transactionally. All previous role/permission links, application rows and product/location/data scopes were retained exactly. Recovered Chrome showed four MTO landing cards and the Procurement card navigated successfully to Material Coverage for Open Sales Order. This is real shared-login navigation proof.

The persisted evidence contains **36 of54 distinct routes rendered with the authenticated actor**, not37 (the progress estimate was corrected against saved observations). These are screen-shell/empty-state observations, not complete API or business-workflow acceptance. Eight earlier Loading-only observations remain preserved and do not count. A later batch timed out; the same tab then reported detached control. Browser proof stopped without a recovery campaign.

Authenticated gateway access logs contain200 responses for MTO master, run-date, filter and several report reads. They also contain400 for `GetAllReportData/` and simulation read `getProdDataAfterSimulation/?releaseDate=undefined&eas=0&page=1&page_size=500`. A separate direct internal read confirms the report menu failure is missing `/app/Downloads/ReportPaths.json`; this is an API/configuration failure, not legitimate empty-data success. No catalogue was invented or installed. A context-dependent simulation route was opened directly without a preceding simulation; that400 is retained, not treated as successful workflow proof.

Public readyz503 remains recorded, with no speculative repair. All five container IDs/images/start times and the MTA fixture file SHA256 match the earlier pins. Browser return-to-MTA, scheduler WebSocket, complete API response-content checks and the remaining18 route observations are still unproved. No full-feature visibility or combined-product readiness claim is made.

Evidence: `navigation-grant-receipt.txt`, `landing-approved.png`, `ui-route-observations.json`, `gateway-ui-check.log`, `post-navigation-protected-readback.json` under D:/freshvcf-build/evidence/mto-same-product-20261010-001. The screenshot was captured before the permission-refresh and therefore is not proof of the new MTO cards; the later browser accessibility observation is the card evidence.

## Finite route coverage

| Permission | Existing route | Current evidence |
|---|---|---|
| 19 | `/mto/planning/simulative-fullkit` | Authenticated screen rendered; full API acceptance unproved |
| 20 | `/mto/procurement-planning/planning` | Authenticated screen rendered; full API acceptance unproved |
| 21 | `/mto/procurement/material-coverage-open-sales` | Authenticated screen rendered; full API acceptance unproved |
| 23 | `/mto/procurement/insights-and-trends/rmpm-orderwise-coverage` | Authenticated screen rendered; full API acceptance unproved |
| 24 | `/mto/procurement/material-requirement` | Authenticated screen rendered; full API acceptance unproved |
| 25 | `/mto/procurement/insights-and-trends/day-wise-coverage` | Authenticated screen rendered; full API acceptance unproved |
| 27 | `/mto/procurement/insights-and-trends/rmpm-buffer-trends` | Authenticated screen rendered; full API acceptance unproved |
| 28 | `/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers` | Authenticated screen rendered; full API acceptance unproved |
| 29 | `/mto/production-planning-scheduling/enquiry-response` | Authenticated screen rendered; full API acceptance unproved |
| 30 | `/mto/production-planning-scheduling/insight-and-trends/stpl-full-kits` | Authenticated screen rendered; full API acceptance unproved |
| 31 | `/mto/production-planning-scheduling/insight-and-trends/bm-trends` | Authenticated screen rendered; full API acceptance unproved |
| 32 | `/mto/production-planning-scheduling/full-kit-assignment` | Authenticated screen rendered; full API acceptance unproved |
| 33 | `/mto/production-planning-and-scheduling/order-rescheduling` | Authenticated screen rendered; full API acceptance unproved |
| 34 | `/mto/production-planning-scheduling/insight-and-trends/order-at-risk` | Authenticated screen rendered; full API acceptance unproved |
| 35 | `/mto/production-planning-scheduling/deptwise-bm-report` | Authenticated screen rendered; full API acceptance unproved |
| 36 | `/mto/production-planning-scheduling/dynamic-release-mangement` | Authenticated screen rendered; full API acceptance unproved |
| 37 | `/mto/production-planning-scheduling/insight-and-trends/order-balance` | Authenticated screen rendered; full API acceptance unproved |
| 38 | `/mto/production-planning-scheduling/insights-and-trends/fol-summary` | Authenticated screen rendered; full API acceptance unproved |
| 39 | `/mto/poogi/insight-and-trends/otif-analysis` | Authenticated screen rendered; full API acceptance unproved |
| 40 | `/mto/poogi/insight-and-trends/resource-utilization-wip-profile` | Authenticated screen rendered; full API acceptance unproved |
| 41 | `/mto/poogi/reasons-for-delayed-orders` | Authenticated screen rendered; full API acceptance unproved |
| 42 | `/mto/production-planning-and-scheduling/due-date-quotation` | Authenticated screen rendered; full API acceptance unproved |
| 43 | `/mto/poogi/insight-and-trends/ot-and-if-analysis` | Authenticated screen rendered; full API acceptance unproved |
| 44 | `/mto/poogi/insight-and-trends/trend-of-failure-reason` | Authenticated screen rendered; full API acceptance unproved |
| 45 | `/mto/poogi/insight-and-trends/lead-time` | Authenticated screen rendered; full API acceptance unproved |
| 46 | `/mto/production-planning-scheduling/insights-and-trends/elapsed-time` | Authenticated screen rendered; full API acceptance unproved |
| 47 | `/mto/poogi/insight-and-trends/top-failure-reasons` | Authenticated screen rendered; full API acceptance unproved |
| 48 | `/mto/production-planning-scheduling/overall-bm-report` | Authenticated screen rendered; full API acceptance unproved |
| 49 | `/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends` | Authenticated screen rendered; full API acceptance unproved |
| 50 | `/mto/manufacturing-intelligence-hub/delivery-performance/otif-analysis` | Authenticated screen rendered; full API acceptance unproved |
| 51 | `/mto/manufacturing-intelligence-hub/delivery-performance/ot-and-if-analysis` | Authenticated screen rendered; full API acceptance unproved |
| 52 | `/mto/manufacturing-intelligence-hub/delivery-performance/lead-time` | Authenticated screen rendered; full API acceptance unproved |
| 53 | `/mto/manufacturing-intelligence-hub/congestion-analysis/elapsed-time` | Authenticated screen rendered; full API acceptance unproved |
| 54 | `/mto/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk` | Authenticated screen rendered; full API acceptance unproved |
| 55 | `/mto/manufacturing-intelligence-hub/congestion-analysis/order-balance` | Authenticated screen rendered; full API acceptance unproved |
| 56 | `/mto/manufacturing-intelligence-hub/forward-exceution/fol-summary` | Authenticated screen rendered; full API acceptance unproved |
| 57 | `/mto/manufacturing-intelligence-hub/forward-exceution/stpl-and-fullkit` | Not yet observed |
| 58 | `/mto/manufacturing-intelligence-hub/forward-exceution/day-wise-coverage` | Not yet observed |
| 59 | `/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage` | Not yet observed |
| 60 | `/mto/manufacturing-intelligence-hub/forward-exceution/expetiting-rm-supplier` | Not yet observed |
| 61 | `/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-buffer-trend` | Not yet observed |
| 62 | `/mto/manufacturing-intelligence-hub/improvement-areas/top-failure-reasons` | Not yet observed |
| 63 | `/mto/manufacturing-intelligence-hub/improvement-areas/trends-failure-reasons` | Not yet observed |
| 64 | `/mto/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile` | Not yet observed |
| 72 | `/mto/master-data-management/control-panel` | Not yet observed |
| 73 | `/mto/master-data-management/control-panel/add` | Not yet observed |
| 74 | `/mto/master-data-management/control-panel/view-modify` | Not yet observed |
| 75 | `/mto/master-data-management/saved-drafts` | Not yet observed |
| 76 | `/mto/master-data-management/task-pending` | Not yet observed |
| 77 | `/mto/master-data-management/task-status` | Not yet observed |
| 78 | `/mto/master-data-management/data-modification-history` | Not yet observed |
| 86 | `/mto/manufacturing-intelligence-hub/future-order-load-chart` | Not yet observed |
| 87 | `/mto/production/scheduling` | Not yet observed |
| 88 | `/mto/production-planning-scheduling/insight-and-trends/future-order-load-chart` | Not yet observed |

## Required continuation

1. Reconnect Chrome's Codex extension on the existing localhost3005 session. Resume only the18 unobserved routes above, applicable navigation/controls and return-to-MTA proof; do not repeat completed screen checks merely to rebuild evidence.
2. Resolve the missing report-menu configuration within an explicitly supported existing packaging contract before claiming dynamic-report visibility. Do not fabricate report files or business inputs. Retain the400 failure.
3. Complete API success/empty-versus-error evidence and applicable WebSocket proof. Do not start a scheduler run to manufacture evidence. Record any remaining limitation explicitly.
4. Update MIGRATION.md and deliver the bounded result. Empty MTO data remains allowed; populated workflows/persistence are deferred. No engine calls, source-code changes, performance measurements or MDM resumption.
