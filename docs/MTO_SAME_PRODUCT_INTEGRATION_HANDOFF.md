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

## Current bounded result — all route screens observed; acceptance gaps remain

The exact approved navigation role3/user2/55 links remains installed. Existing roles, scopes, credentials and restricted accounts are unchanged. All54 retained route screens rendered under the same broad fixture login:37 saved Chrome observations plus17 completed in Edge. The four MTO landing cards are visible. Procurement card navigation and return through the shared landing's MTA Planning card passed. Direct route visibility is not proof of every interaction or every API response payload.

The only service correction changes the MTO entrypoint from Uvicorn to already-installed Daphne in compose.preview.yaml, using the SAME image and matched environment/resources/mounts. Before correction, the scheduler socket returned404 and MTO logs reported no supported WebSocket library. After MTO-only recreation, public localhost3005 `/ws/scheduler/mto-visibility-probe-20261010/` returned101, and internal HTTP health, ready and plant-master reads returned200. The probe sent no application messages and started no scheduling run; business progress delivery remains deferred with populated workflows. Original failures are retained.

All other recorded container IDs/images/start times match. MTA fixture SHA256 remains `a6b28597dc5ec7d5e013521f548da0f90512d64834d3c8e869225033fc2a3f3d`. Public readyz503 remains an earlier unresolved observation, not permission for unrelated MTA repair.

Authenticated gateway logs contain successful MTO reads and retained failures. `GetAllReportData/` returns400 because `/app/Downloads/ReportPaths.json` is missing; dynamic download visibility remains blocked. Scheduling's `getLatestRunStatus/` returns404 with `No run data available.` but the retained screen displays `Failed to fetch the run status`; this is not a truthful empty-state pass. Its file configuration returns404 and the UI explicitly says no files configured. A top-failure-reasons chart displays Invalid date when dates are absent. Simulation direct navigation sends releaseDate=undefined and returns400; no simulation was run to manufacture prerequisites. These gaps remain distinct from empty successful charts/grids.

No populated workflows, scheduling, data import, source discovery, application-code changes or MDM continuation occurred. Native read endpoints were invoked by the unchanged UI; no business submission controls were used. All-feature acceptance remains INCOMPLETE. Exact remaining decisions are in MTO_UI_REMAINING_GAPS.md.

## Finite route coverage

| Permission | Existing route | Evidence |
|---|---|---|
| 19 | `/mto/planning/simulative-fullkit` | Authenticated screen rendered; interaction/API qualifications above retained |
| 20 | `/mto/procurement-planning/planning` | Authenticated screen rendered; interaction/API qualifications above retained |
| 21 | `/mto/procurement/material-coverage-open-sales` | Authenticated screen rendered; interaction/API qualifications above retained |
| 23 | `/mto/procurement/insights-and-trends/rmpm-orderwise-coverage` | Authenticated screen rendered; interaction/API qualifications above retained |
| 24 | `/mto/procurement/material-requirement` | Authenticated screen rendered; interaction/API qualifications above retained |
| 25 | `/mto/procurement/insights-and-trends/day-wise-coverage` | Authenticated screen rendered; interaction/API qualifications above retained |
| 27 | `/mto/procurement/insights-and-trends/rmpm-buffer-trends` | Authenticated screen rendered; interaction/API qualifications above retained |
| 28 | `/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers` | Authenticated screen rendered; interaction/API qualifications above retained |
| 29 | `/mto/production-planning-scheduling/enquiry-response` | Authenticated screen rendered; interaction/API qualifications above retained |
| 30 | `/mto/production-planning-scheduling/insight-and-trends/stpl-full-kits` | Authenticated screen rendered; interaction/API qualifications above retained |
| 31 | `/mto/production-planning-scheduling/insight-and-trends/bm-trends` | Authenticated screen rendered; interaction/API qualifications above retained |
| 32 | `/mto/production-planning-scheduling/full-kit-assignment` | Authenticated screen rendered; interaction/API qualifications above retained |
| 33 | `/mto/production-planning-and-scheduling/order-rescheduling` | Authenticated screen rendered; interaction/API qualifications above retained |
| 34 | `/mto/production-planning-scheduling/insight-and-trends/order-at-risk` | Authenticated screen rendered; interaction/API qualifications above retained |
| 35 | `/mto/production-planning-scheduling/deptwise-bm-report` | Authenticated screen rendered; interaction/API qualifications above retained |
| 36 | `/mto/production-planning-scheduling/dynamic-release-mangement` | Authenticated screen rendered; interaction/API qualifications above retained |
| 37 | `/mto/production-planning-scheduling/insight-and-trends/order-balance` | Authenticated screen rendered; interaction/API qualifications above retained |
| 38 | `/mto/production-planning-scheduling/insights-and-trends/fol-summary` | Authenticated screen rendered; interaction/API qualifications above retained |
| 39 | `/mto/poogi/insight-and-trends/otif-analysis` | Authenticated screen rendered; interaction/API qualifications above retained |
| 40 | `/mto/poogi/insight-and-trends/resource-utilization-wip-profile` | Authenticated screen rendered; interaction/API qualifications above retained |
| 41 | `/mto/poogi/reasons-for-delayed-orders` | Authenticated screen rendered; interaction/API qualifications above retained |
| 42 | `/mto/production-planning-and-scheduling/due-date-quotation` | Authenticated screen rendered; interaction/API qualifications above retained |
| 43 | `/mto/poogi/insight-and-trends/ot-and-if-analysis` | Authenticated screen rendered; interaction/API qualifications above retained |
| 44 | `/mto/poogi/insight-and-trends/trend-of-failure-reason` | Authenticated screen rendered; interaction/API qualifications above retained |
| 45 | `/mto/poogi/insight-and-trends/lead-time` | Authenticated screen rendered; interaction/API qualifications above retained |
| 46 | `/mto/production-planning-scheduling/insights-and-trends/elapsed-time` | Authenticated screen rendered; interaction/API qualifications above retained |
| 47 | `/mto/poogi/insight-and-trends/top-failure-reasons` | Authenticated screen rendered; interaction/API qualifications above retained |
| 48 | `/mto/production-planning-scheduling/overall-bm-report` | Authenticated screen rendered; interaction/API qualifications above retained |
| 49 | `/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends` | Authenticated screen rendered; interaction/API qualifications above retained |
| 50 | `/mto/manufacturing-intelligence-hub/delivery-performance/otif-analysis` | Authenticated screen rendered; interaction/API qualifications above retained |
| 51 | `/mto/manufacturing-intelligence-hub/delivery-performance/ot-and-if-analysis` | Authenticated screen rendered; interaction/API qualifications above retained |
| 52 | `/mto/manufacturing-intelligence-hub/delivery-performance/lead-time` | Authenticated screen rendered; interaction/API qualifications above retained |
| 53 | `/mto/manufacturing-intelligence-hub/congestion-analysis/elapsed-time` | Authenticated screen rendered; interaction/API qualifications above retained |
| 54 | `/mto/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk` | Authenticated screen rendered; interaction/API qualifications above retained |
| 55 | `/mto/manufacturing-intelligence-hub/congestion-analysis/order-balance` | Authenticated screen rendered; interaction/API qualifications above retained |
| 56 | `/mto/manufacturing-intelligence-hub/forward-exceution/fol-summary` | Authenticated screen rendered; interaction/API qualifications above retained |
| 57 | `/mto/manufacturing-intelligence-hub/forward-exceution/stpl-and-fullkit` | Authenticated screen rendered; interaction/API qualifications above retained |
| 58 | `/mto/manufacturing-intelligence-hub/forward-exceution/day-wise-coverage` | Authenticated screen rendered; interaction/API qualifications above retained |
| 59 | `/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage` | Authenticated screen rendered; interaction/API qualifications above retained |
| 60 | `/mto/manufacturing-intelligence-hub/forward-exceution/expetiting-rm-supplier` | Authenticated screen rendered; interaction/API qualifications above retained |
| 61 | `/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-buffer-trend` | Authenticated screen rendered; interaction/API qualifications above retained |
| 62 | `/mto/manufacturing-intelligence-hub/improvement-areas/top-failure-reasons` | Authenticated screen rendered; interaction/API qualifications above retained |
| 63 | `/mto/manufacturing-intelligence-hub/improvement-areas/trends-failure-reasons` | Authenticated screen rendered; interaction/API qualifications above retained |
| 64 | `/mto/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile` | Authenticated screen rendered; interaction/API qualifications above retained |
| 72 | `/mto/master-data-management/control-panel` | Authenticated screen rendered; interaction/API qualifications above retained |
| 73 | `/mto/master-data-management/control-panel/add` | Authenticated screen rendered; interaction/API qualifications above retained |
| 74 | `/mto/master-data-management/control-panel/view-modify` | Authenticated screen rendered; interaction/API qualifications above retained |
| 75 | `/mto/master-data-management/saved-drafts` | Authenticated screen rendered; interaction/API qualifications above retained |
| 76 | `/mto/master-data-management/task-pending` | Authenticated screen rendered; interaction/API qualifications above retained |
| 77 | `/mto/master-data-management/task-status` | Authenticated screen rendered; interaction/API qualifications above retained |
| 78 | `/mto/master-data-management/data-modification-history` | Authenticated screen rendered; interaction/API qualifications above retained |
| 86 | `/mto/manufacturing-intelligence-hub/future-order-load-chart` | Authenticated screen rendered; interaction/API qualifications above retained |
| 87 | `/mto/production/scheduling` | Authenticated screen rendered; interaction/API qualifications above retained |
| 88 | `/mto/production-planning-scheduling/insight-and-trends/future-order-load-chart` | Authenticated screen rendered; interaction/API qualifications above retained |

## Evidence and rollback

External root: D:/freshvcf-build/evidence/mto-same-product-20261010-001. Evidence includes navigation-grant-receipt.txt, ui-route-observations.json (including incomplete Loading attempts), gateway-ui-final.log, edge-mto-landing.png, edge-return-mta.txt/png, websocket-handshake.txt (404), websocket-after-daphne.txt (101), daphne-transition-preflight.json and post-daphne-protected-readback.json. Earlier landing-approved.png predates the refresh and does not prove MTO cards; use edge-mto-landing.png.

MTO launch rollback only if requested/needed: restore the MTO entrypoint from compose.preview.before-daphne.yaml to the original Uvicorn command, then run `docker compose --env-file D:/freshvcf-build/preview/preview.env -f F:/freshvcf/compose.preview.yaml -p freshvcf-preview up -d --no-deps --no-build mto`. Do not restore the whole file over unrelated subsequent edits. This would restore the known WebSocket404 fault. Navigation rollback is limited to newly owned role3 and its55 links/user2 membership after verifying exact ownership; never remove previous roles or scopes.

Stop at this bounded configuration delivery and consolidated review boundary. MDM remains paused; performance remains stopped. No broad readiness claim.
