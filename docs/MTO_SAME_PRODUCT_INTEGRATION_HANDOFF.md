# Existing MTO in the 3005 product — bounded verification handoff

10 October 2026. **Configuration is connected; the business journey is blocked and not accepted.** No source, configuration, service, grants, data or credentials were changed. No rebuild, restart, business-day call, workflow write or new port was performed. The human stopped the separate performance tranche; that incomplete evidence remains in UI_PERFORMANCE_PARITY_REPORT.md and was not used as a prerequisite for this check.

Evidence: [runtime identities](D:/freshvcf-build/evidence/mto-same-product-20261010-001/runtime-identities.json), [running nginx routing](D:/freshvcf-build/evidence/mto-same-product-20261010-001/nginx-routing.conf), [read-only checks](D:/freshvcf-build/evidence/mto-same-product-20261010-001/read-only-proof.json). The read-only proof explicitly distinguishes runtime observations from configuration declarations.

| Boundary | Result |
|---|---|
| Existing MTO image | Running `sha256:bc5a6fb828bc9e0123a837763c9d3cbf6f4f8e8fbd1e91f10c73a0e1c373ab5f`, started2026-10-09 06:05:24 UTC, not restarted or OOM-killed |
| Gateway image | `sha256:1c226612541b36f135a352e2d626cee778ca479c55b5f302447ff5f7eca7e8e0`; effective `MTO_BACKEND_URL=http://mto:10015` |
| Frontend image | `sha256:042d7a51371827ecc789cdca29b4f13fb281c9def8f9932b58cd04b86e6677b1`; existing public127.0.0.1:3005 |
| API routing | Running nginx `/api/` forwards to user-service:10016. Retained gateway MTO mapping uses application3 and the MTO interceptor. Public `/api/mto/getPlantMasterData/` rejects an unauthenticated request with401. This is denial proof, not an authenticated positive read. |
| MTO database | Effective `freshvcf` database / `mto` schema on owned freshvcf-test-postgres-1; internal `/healthz` and `/readyz` both200. Readiness checks connectivity only. |
| Business prerequisites | PlantMaster, CCRMaster, BufferMaster, OrderData, MTOOrderData, MTOLineItemData and DailyWorkingCalendar each contain0 rows. No existing representative populated workflow can be selected from these prerequisites. |
| Current broad account | Actor2, non-admin, has no MTO navigation grants or application3 product/location assignments. Existing MTA scopes were preserved. Actor1 is admin but has no ordinary role MTO navigation/scopes; effective admin navigation was not inferred from that fact. |
| WebSocket configuration | Running nginx `/ws/` forwards to mto:10015 with Upgrade/Connection headers. Redis host is configured. No WebSocket-dependent business journey was possible, so runtime WebSocket acceptance is unproved. DDQ UI remains disabled. |
| Browser journey | Same-login MTO landing, populated read, representative workflow, persisted readback/reload and MTA return remain unproved. Chrome's existing tab control detached; a new3005 landing tab attempt timed out. No further browser recovery campaign was opened once the independent data/access blockers were established. |
| Protected MTA | Container/image/start time and selected fixture SHA256`a6b28597dc5ec7d5e013521f548da0f90512d64834d3c8e869225033fc2a3f3d` remain the recorded identities. No mutation was made. Final public `/readyz` returned503: identity and catalogue true, MTA false. Running container identity is not a health PASS; cause was not diagnosed or attributed to this no-change check. |

No configuration-only defect requiring a change was demonstrated. A connected empty service is not a supported combined-product business workflow. There is therefore no deployment rollback to perform and no full-MTO or production-readiness claim.

The remaining steps require a separate bounded package, not execution under this handoff:

1. Name and approve a target-bound retained MTO input/state package and existing representative operation, including expected persisted fields. The current empty schema cannot demonstrate that operation; do not borrow another service's database or invent orders.
2. Resolve exact application3 navigation and scope authorization for the intended same-login actor, without changing MTA grants. Do not infer that an admin account proves the broad fixture journey.
3. Restore a usable connected3005 browser session and verify landing, populated read, the named operation, readback/reload and MTA return. Include WebSocket proof only if the chosen operation uses it.
4. Separately assess the observed MTA readiness503 before any combined-product readiness claim. No performance tuning or service restart is authorized by this observation.

The finite no-change configuration verification is finished with these explicit blocked exits. Stop here; do not resume the stopped measurement or paused MDM daily work.
