# Frontend static extraction notes (2026-10-01)

This initial audit snapshot precedes the separately authorized Stage1 work.
The later supplement below supersedes potential module linkage where exact
invocations were traced. `docs/MIGRATION.md` remains the sole status tracker.

- Source scope: `frontend/src`, static reads only. No app, build, tests, SQL, services or network calls were run.
- Provenance in `baseline/manifest.json`: inherited reuse revision `66a77735d3f3f9a9becf4c87a08ae7827900cf84`; pinned frontend Git tree `dd1b8441644dc3439a27c15015f1ffcd40169faf`. `F:/vflow_integrated` HEAD was observed at the pinned revision. The primary agent verified the full Git tree delta against the pinned revision: frontend 1,886 source entries versus 1,883 in Fresh, with only three absent inherited public assets (`public/assets/img/forced/excel (1).zip`, `public/assets/img/manual/Group 473.zip`, and `public/assets/img/manual/plus.zip`). MTO (156/156) and user-service (188/188) match by exact hashes; frontend/MTO/user-service show no changes after foundation commit `4d5ffdb` per primary audit.
- `frontend-api-calls.csv`: 129 active request/helper rows extracted, including service wrappers, `CsvExportMTA` (`GetExportDataAsync`), both `handleDownloadVF` (`DownloadReports`) helpers, and `handleDownloadVFReports` (`POST /download-excel`).
- `frontend-routes.csv`: 29 route declaration rows; duplicate declarations retained. MTA MDM relative `view-modify` child expanded to its full path.
- Caller values are production source import-path matches from `Pages/MTA`; these establish potential static linkage, not runtime activation. For service wrappers the importer is linked by module family, not by runtime query execution. Explicit direct helper call sites were included where found; seven rows have untraced callers. Many wrapper inputs are typed `any`; payload descriptions therefore preserve available function signatures without inferring fields.
- Dynamic/conditional behavior: `app-routes.tsx` `lazyLoad` checks `urlAllPage` and `user.url_permission`. `listMenu.tsx` conditionally removes 5 routes in demo mode. Routes can remain declared while absent from demo menu. Route duplicates: `/mta/supply-chain-intelligence-hub/planning` and `/mta/dbm/dbm-norm-suggestions`.
- Excluded from MTA API CSV and categorized separately: MTO service methods hosted at `REACT_APP_VF_API_HOST_MTO` in shared `Services/MTA/MDM/api.ts`; mock `MCGrid` health route using `REACT_APP_VF_MOCK_API_HOST`; shared `/api/user/*` endpoints; auth/session calls outside MTA Services. These are not classified as MTA business API wrappers.
- Direct MTA menu download-report links found in comments are inactive and excluded. Client-side AG Grid Excel exports are not HTTP calls and are not listed as endpoints.
- Counts exclude commented calls; where a wrapper's request body is a variable, the CSV records its declared function parameter/signature. `known_page_callers` may list multiple screens importing a service family; it does not prove each screen invokes each listed function. Endpoint use and server implementation require separate tracing.

Primary reconciliation: 29 route declarations resolve to27 unique paths (26 under /mta plus the merchandising/mock route outside that prefix). The MDM menu is indirect through /masters-interceptor/* and ApplicationSelectModal, not absent; its relative View/Modify child is explicitly resolved in the CSV. Dynamic masterId/processId suffixes in the retail validation helpers are retained. TotalRequirementReport imports mock row data and has no active grid-fetch call in the inspected hook; its canonical selected disposition remains unresolved. See AUDIT.md and screen-connections.csv.

Endpoint reconciliation: 114 distinct MTA method/path templates,36 matching Fresh method/routes and78 absent; eight call-site rows are outside /api/mta. These are static potential calls, not selected feature completion counts. No exact lookup match in the recovered-controller catalogue proves nothing about absence from the deployed DLL.

## Stage1 exact-call supplement

`frontend-call-controls.csv` retains all129 declaration/helper rows and adds
service-hook definitions, exact hook/call lines, mutation alias invocations and
short payload/control excerpts. The source scanner removes comments while
preserving line offsets, resolves named imports to the exact service module,
maps service function→exported React Query hook, then maps destructured
`mutateAsync`/`mutate` aliases to actual calls. Tests are excluded. Shared
components/hooks and MTO page imports of MTA wrappers are retained separately
from MTA page use; they must not be silently altered during migration.

117 rows have production invocation evidence,10 have no invocation traced,
one is an unused duplicate download helper, and one initializes a progress
hook without a traced call. This is still static evidence, not proof every
conditional control is reachable for the current actor. CSV excerpt truncation
does not limit the contract: each source line points to the complete body.
Manual confirmations cover MenuToolTip's useDownloadHandler object method,
MDM history's nested closure, Save/Reset imported through BPR services, and
the RRR config/layout/export distinction. Dynamic download names come from
GetAllReports; selected paths are empty. `/download-excel` has a helper call
but final per-screen control use remains explicitly unresolved.

`deployed-consumer-anchors.csv` is an IL navigation index, not a normalized
contract or list of mandatory features. Method spans and literal SQL relation
identifiers came from the retained pinned-DLL IL, SHA256
ccd47dc8d76895a6aa63ad5d6beaadb32f4f53ab75047a68fb8055382fd87ca1.
Dynamic query concatenation and async helpers still require reading the owning
method when implementing that journey. In particular, deployed supplier-wise
allocation reads BORWithOrderAllocation; Supplier Dispatch reads SupplierDispatchReq.
Current authenticated sidebar evidence includes Supplier Dispatch and Elephant
Orders. Earlier broad import matches or preview permission assumptions cannot
exclude those consumers. No report-reader/frontend/MTO/auth source changed.
