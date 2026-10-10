# UI performance parity and unchanged MTO integration

> Status amendment,10 October2026: the human stopped tranche A before completion.
> Preserve its incomplete qualified evidence; no further measurement or tuning.
> The same instruction removed the A-before-B dependency and retained only the
> existing MTO configuration/routing/packaging verification. Its no-change handoff
> records blocked business acceptance in MTO_SAME_PRODUCT_INTEGRATION_HANDOFF.md.
> The original plan below is retained as the historical scope, not a restart order.

10 October 2026. Released by the direct human request for a legacy/modern page-loading comparison and MTO within the same product without codebase changes. MIGRATION.md is the sole tracker. This is a finite execution contract, not authority to resume deferred MDM daily work.

## Objective and two sequential exits

A. Produce one current matched legacy-versus-modern UI timing artifact for every implemented MTA report page/defined loading branch below, including Planning's four quadrants and BPR/BTR/DBM. Measure displaying complete usable output, not spinner disappearance or API time alone.

B. Verify and, where necessary, configure the existing MTO service into the same3005 product experience, preserving source code and business contracts. Deliver one combined-product handoff with exact supported workflows and gaps.

The old MDM approval-to-day goal stays paused. Preserve all its dirty files, input/capture/failure receipts and consumed call count. Do not package its unaccepted working tree into this demo. Performance target is the actual committed/deployed3005 runtime, not latest Git HEAD by inference. No business-day or legacy calculation run is authorized.

## A1 — Fixed providers and one matching gate

Modern: working localhost3005, MTA image b3bc7ea3994db6967a590fb3d5d7b265d680d7bce205f9395643e7efd3582016, retained April7 fixture/source and BTR generation in MDM_3005_DEPLOYMENT_HANDOFF.md. Verify running identities read-only before measurement; record actual frontend/gateway/MTO and DB resource identities too.

Legacy: use the already retained canonical browser/API provider referenced by existing matched receipts (historical browser3002/API5153); verify its actual deployed authority and selected data, do not assume a port proves canonical identity.3003/3004 are not substitutes. If unavailable, identify the exact provider/startup requirement once; no SQL restoration, new public port, borrowed DB or shared restart under this test.

Match selected date/source population, product/location scope, configuration, filters, page sizes, sort/layout, horizon and visible columns per row. Reuse existing source/parity receipts where identities match. Record exact known qualifications (ordering, ambiguous categories, blocked routes); a mismatch cannot earn a performance-parity PASS. Do not alter/seed either dataset to make a screen populated or convenient. Report unmatched rows as UNMATCHED with both observations if useful, never silently compare different workloads.

Use the same browser engine/version, viewport and machine for each pair, equivalent accounts and normal resources. Record CPU/memory/worker/deadline limits for both sides; if unlike, mark resource-qualified instead of claiming controlled parity. No resource increase, cache flush, host restart or cold-database claim.

## A2 — Finite page roster

Resolve the literal sidebar/route names from existing page matrices and retained browser walks ONCE; do not inventory all frontend services or discover new business routes. Required rows:

1. Planning overview: all four quadrants, counts/labels and readiness independently recorded.
2. Planning order-fulfillment quadrant: defined primary chart/grid and implemented drill-down/custom branches.
3. Planning excess quadrant: defined primary chart/grid and implemented drill-down.
4. Planning GIT quadrant: defined primary chart/grid and implemented child branch.
5. Planning expedite quadrant: defined primary chart/grid, parent and child branches where implemented.
6. BPR main populated grid/count, one retained selected-row detail/history path.
7. BTR Tech and Eco branches, one retained daily/history modal.
8. DBM current grid/count and one retained daily/history modal.
9. RRR populated grid/count.
10. Buffer Trends implemented tabs/branches.
11. Guided: each already implemented tab (including availability/excess/chronic branches), declared history/source limitations retained.
12. Research Insights: grid and already implemented selected summary/calendar/ageing branches.
13. BOR and BOR-OA implemented pages; explicitly distinguish empty current fixture from historical populated evidence.
14. Supplier/allocation or other implemented report page already named in the current accepted page matrix: include existing reachable branch only; unavailable/undefined branches get an explicit row, not speculative implementation.

All implemented report pages are represented, but this is not an MDM workflow timing campaign. Do not benchmark unimplemented pages as if loading an empty error screen were success. Exports/reload are functional observations only unless the selected page's usability requires them; no separate download-throughput programme.

For each quadrant/page, fix one default populated workload and one necessary defined branch. Existing grids' paging is part of readiness: record rows displayed and full count, not loading all97097 pairs if native page size does not. Every reachable loading branch in the accepted matrix must have a timing/disposition row; no omission of a slow result.

## A3 — Measurement protocol

One initial clean browser-context observation per side is labeled fresh-session (not cold DB). Then exactly THREE paired normal-navigation samples per row, alternating legacy/modern order. The first observation remains in the artifact but is not mixed into the three navigation-sample median. No warmup calculations or favorable-repeat selection. Preserve every raw sample, timeout, error, token refresh and mismatch.

Start at an observed real navigation click/action. End only when required grid/chart/count/date output is rendered, loading indicators are gone and required controls respond. For Planning overview record each quadrant ready separately and overall readiness at the last required quadrant; do not sum parallel quadrants or call the first quadrant the whole-page time. For modal/drill-down use its own click-to-usable boundary.

Capture frontend request timestamps/waterfall, response completion/bytes and visible render readiness where available. Correlate gateway/backend/DB timestamps using existing observation facilities; do not introduce production instrumentation or profiling. Separate click-to-request, request/transfer and render where observable. Mark unavailable native paint/time components, tool/AX polling overhead and observation resolution explicitly. Tool wall time is not pure browser latency.

Deadline is the existing application/request deadline and a declared bounded UI observer limit (120seconds); a timeout is a failed sample, never a finite fast timing. Do not start another sample while prior timed-out work is still active; wait for owned requests to drain without restarting shared services. Recheck only a genuinely invalid measurement (wrong page/auth/observer failure), at most once with reason; preserve the original.

Primary comparison: paired median click-to-usable time, modern/legacy ratio and improvement=(legacy-modern)/legacy. PASS requires matched valid outputs and modern median <= legacy median; label three-sample evidence SMALL SAMPLE. No p95 or capacity/SLA claim from three samples. Report tail/max samples and failure counts. If a page is slower, capture the observed bottleneck clues and smallest follow-up proposal; DO NOT optimise in this measurement release.

## A4 — Required artifact

Create docs/UI_PERFORMANCE_PARITY_REPORT.md and a CSV plus raw JSON timing/evidence index under a new owned D:/freshvcf-build/evidence/ui-performance-parity-* root. Markdown links point to exact retained logs/screenshots/network records. No secrets or tokens in artifacts.

Required columns: page/quadrant/branch; route; date/source/scope/page-size/horizon; rows/count; data-match/resource status; three legacy samples/median; three modern samples/median; fresh-session observation; ratio/improvement; errors/timeouts; usable-output criterion; result PASS/SLOWER/FAILED/UNMATCHED/BLOCKED; exact qualification/evidence; next action. Never fill unavailable timings with zero or historical measurements labeled current.

Include ranked slower/failed pages and one concise executive comparison. Do not claim all-UI parity if any required row is missing/unmatched/blocked. Existing canonical defects remain defects, not migration performance improvements.

## B — Existing MTO configuration-only integration

Current read-only inspection confirms freshvcf-preview-mto-1 exists; compose.preview.yaml declares MTO_BACKEND_URL=http://mto:10015, PostgreSQL mto schema, Redis and frontend WebSocket host on3005. These declarations/running container are prerequisites, not acceptance.

After A is frozen, check only existing image/source identity, DB/schema, gateway/frontend route and WebSocket configuration needed for the existing MTO journey. Preserve source code: NO changes to MTO/MTA/gateway/frontend business or API implementation; no dependency modernization, new port, schema redesign or MDM adoption. Runtime private config/packaging/routing adjustments are authorized where necessary for this existing3005 integration, with recorded rollback identities. Do not reset/repopulate DBs, accounts, grants or secrets. If permission or missing data is indispensable, present one exact decision; do not invent it.

First verify existing same-login navigation/profile -> MTO landing -> existing representative read -> one supported existing user workflow/result -> readback/reload -> return to MTA with original selection intact. Use retained MTO business cases and owned test state; no emails/external effects. Read/write verification must name the actual existing business operation and expected persisted fields before use. No newly invented MTO workflow or calculation campaign. Verify WebSocket-dependent behavior only if that selected journey uses it.

If already correctly connected, record proof without unnecessary rebuild/restart. If config changes are needed, replace/restart only the exact affected owned3005 application service, not shared infrastructure; preserve data, identities, other services and rollback. Run only directly affected MTA navigation/auth/selection check after integration. Do not rerun timing samples to make B a new performance campaign; explicitly note any configuration change that invalidates a timing identity.

Any required source-code change is OUTSIDE this release: stop that exit with exact route/dependency/failure and smallest separate proposal, while retaining all feasible proof. Do not label config-only integration complete if core workflow is blocked. Existing MTO port is preserved, not automatically certified fully modern or production ready.

Deliver docs/MTO_SAME_PRODUCT_INTEGRATION_HANDOFF.md with image/config/source/DB identities, verified login/menu/workflow/reload/return evidence, actual changes or no-change result and remaining gaps. One cohesive artifact/config delivery commit/push where appropriate; no component commits or unrelated dirty files. Stop after verified A/B handoff; do not resume MDM or production-readiness backlog automatically.

## Execution and monitoring discipline

Executor first records old MDM goal paused and exact preserved state. Set ONE new bounded A->B goal, no numeric token budget; before mutation identify active exit, permitted boundary and proof in MIGRATION. Reuse lean-code-orchestrator and computer-use skills for the authorized browser work. No broad discovery/test inventory/framework or new fixture campaign.

Human's explicit request releases this finite UI measurement only, superseding prior benchmarking halt only at A. It does not release general profiling, optimisations, engine timing, load/stress tests, full temporal execution or deployment/cutover outside the existing3005 config-only B boundary. Preserve legacy provider and3002–4/3006, canonical semantics, stopped temporal receipts and unaccepted MDM work. Existing resource limits remain unchanged.
