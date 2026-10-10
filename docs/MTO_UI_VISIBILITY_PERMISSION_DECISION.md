# MTO UI visibility — exact navigation decision

10 October 2026. Approved by direct human reply call_jPHZWrH2goPmZWawLWrztZ4l:0 and applied: role3, user2, exactly55 permission links. Existing grants and all scope tables matched the pre-change snapshot. Receipt: D:/freshvcf-build/evidence/mto-same-product-20261010-001/navigation-grant-receipt.txt.

## Requested change

In the owned 3005 identity database `freshvcf`, schema `identity`, create one role named `Stage2 MTO UI Visibility`, code `STAGE2_MTO_UI_VISIBILITY`, application_id 3, visible true. Assign it only to existing broad fixture user 2 (`Stage2 VM broad reader`). Link only the existing FUNCTION rows listed below. Reuse existing application `Orders` (application_id 3); create no application or FUNCTION rows.

No product, location or data-scope grants are requested. Preserve all current roles, MTA permissions, credentials, other accounts and serving selection. This is navigation access, not a new read-only security role: retained screens can expose action controls. Verification will not submit business writes or start scheduling/calculation. Missing scopes or API errors will be recorded, never bypassed or silently broadened.

The finite roster contains 54 distinct existing routes plus existing dynamic report-menu gate 83. Exclude malformed duplicate permission 91 (`mto/production/scheduling`). Source: `frontend/src/app-routes.tsx`, `frontend/src/components/layouts/NavbarMenu/listMenu.tsx` and its report-menu gate. Existing route aliases remain separate visibility checks.

| Existing FUNCTION ID | Exact URL |
|---|---|
| 19 | `/mto/planning/simulative-fullkit` |
| 20 | `/mto/procurement-planning/planning` |
| 21 | `/mto/procurement/material-coverage-open-sales` |
| 23 | `/mto/procurement/insights-and-trends/rmpm-orderwise-coverage` |
| 24 | `/mto/procurement/material-requirement` |
| 25 | `/mto/procurement/insights-and-trends/day-wise-coverage` |
| 27 | `/mto/procurement/insights-and-trends/rmpm-buffer-trends` |
| 28 | `/mto/procurement/insights-and-trends/rmpm-expediting-rm-suppliers` |
| 29 | `/mto/production-planning-scheduling/enquiry-response` |
| 30 | `/mto/production-planning-scheduling/insight-and-trends/stpl-full-kits` |
| 31 | `/mto/production-planning-scheduling/insight-and-trends/bm-trends` |
| 32 | `/mto/production-planning-scheduling/full-kit-assignment` |
| 33 | `/mto/production-planning-and-scheduling/order-rescheduling` |
| 34 | `/mto/production-planning-scheduling/insight-and-trends/order-at-risk` |
| 35 | `/mto/production-planning-scheduling/deptwise-bm-report` |
| 36 | `/mto/production-planning-scheduling/dynamic-release-mangement` |
| 37 | `/mto/production-planning-scheduling/insight-and-trends/order-balance` |
| 38 | `/mto/production-planning-scheduling/insights-and-trends/fol-summary` |
| 39 | `/mto/poogi/insight-and-trends/otif-analysis` |
| 40 | `/mto/poogi/insight-and-trends/resource-utilization-wip-profile` |
| 41 | `/mto/poogi/reasons-for-delayed-orders` |
| 42 | `/mto/production-planning-and-scheduling/due-date-quotation` |
| 43 | `/mto/poogi/insight-and-trends/ot-and-if-analysis` |
| 44 | `/mto/poogi/insight-and-trends/trend-of-failure-reason` |
| 45 | `/mto/poogi/insight-and-trends/lead-time` |
| 46 | `/mto/production-planning-scheduling/insights-and-trends/elapsed-time` |
| 47 | `/mto/poogi/insight-and-trends/top-failure-reasons` |
| 48 | `/mto/production-planning-scheduling/overall-bm-report` |
| 49 | `/mto/manufacturing-intelligence-hub/delivery-performance/bm-trends` |
| 50 | `/mto/manufacturing-intelligence-hub/delivery-performance/otif-analysis` |
| 51 | `/mto/manufacturing-intelligence-hub/delivery-performance/ot-and-if-analysis` |
| 52 | `/mto/manufacturing-intelligence-hub/delivery-performance/lead-time` |
| 53 | `/mto/manufacturing-intelligence-hub/congestion-analysis/elapsed-time` |
| 54 | `/mto/manufacturing-intelligence-hub/congestion-analysis/orders-at-risk` |
| 55 | `/mto/manufacturing-intelligence-hub/congestion-analysis/order-balance` |
| 56 | `/mto/manufacturing-intelligence-hub/forward-exceution/fol-summary` |
| 57 | `/mto/manufacturing-intelligence-hub/forward-exceution/stpl-and-fullkit` |
| 58 | `/mto/manufacturing-intelligence-hub/forward-exceution/day-wise-coverage` |
| 59 | `/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-order-wise-coverage` |
| 60 | `/mto/manufacturing-intelligence-hub/forward-exceution/expetiting-rm-supplier` |
| 61 | `/mto/manufacturing-intelligence-hub/forward-exceution/rm-pm-buffer-trend` |
| 62 | `/mto/manufacturing-intelligence-hub/improvement-areas/top-failure-reasons` |
| 63 | `/mto/manufacturing-intelligence-hub/improvement-areas/trends-failure-reasons` |
| 64 | `/mto/manufacturing-intelligence-hub/improvement-areas/resource-wip-profile` |
| 72 | `/mto/master-data-management/control-panel` |
| 73 | `/mto/master-data-management/control-panel/add` |
| 74 | `/mto/master-data-management/control-panel/view-modify` |
| 75 | `/mto/master-data-management/saved-drafts` |
| 76 | `/mto/master-data-management/task-pending` |
| 77 | `/mto/master-data-management/task-status` |
| 78 | `/mto/master-data-management/data-modification-history` |
| 83 | `mto-report-urls` |
| 86 | `/mto/manufacturing-intelligence-hub/future-order-load-chart` |
| 87 | `/mto/production/scheduling` |
| 88 | `/mto/production-planning-scheduling/insight-and-trends/future-order-load-chart` |

## Execution and proof after approval

1. Read back user, application and exact permission ID/URL pairs; reject any mismatch or existing conflicting role. Save the pre-change role/scope snapshot outside Git.
2. In one transaction create only the named role, its listed permission links and user 2 membership. Read back the exact resulting links and unchanged existing grants/scopes.
3. Refresh the ordinary authenticated profile, verify Orders/shared navigation and each existing feature route, its API target and truthful empty/error state. Inspect retained feature controls without business submissions. Treat API failure differently from an empty successful response.
4. Verify return to MTA with selection preserved. Scheduler WebSocket use is conditional on an existing run ID; do not generate a run just to exercise it. Report any unavailable WebSocket proof explicitly.
5. Record outcomes in MIGRATION.md. Rollback, if needed, removes only the newly created role and its links after confirming exact ownership; it never removes pre-existing grants.

Populated-data workflow/persistence acceptance is deferred and is not a prerequisite for this delivery. No data package, source discovery, seeding, engine call, performance measurement or source-code change is authorized. Approval of this proposal is not acceptance of unverified features.
