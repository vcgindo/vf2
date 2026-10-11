# Planning summary preparation and navigation reuse

11 October 2026. Direct human implementation release: turn the proposed typed summary, fast scoped read and return-navigation reuse into this finite delivery. `docs/MIGRATION.md` is the ONLY status tracker. This document defines the contract, not another queue.

## Outcome

The four Planning cards read a small prepared summary instead of executing the underlying detail-count joins on every visit. Returning from a quadrant reuses the same authenticated summary while its source/publication/scope/request identity remains valid. The summary is prepared with the reporting generation after committed daily calculations, never used as calculation input.

Preserve existing frontend design, routes, response envelopes/string count types, business date and all detailed chart/grid/export behavior. This is NOT a Planning redesign, general cache platform, report-engine rewrite or production-readiness claim.

## Verified starting point and exclusions

- `mta/presentation/planning_overview_sql.py:counts` currently resolves scope, calculates three custom counts and invokes parent/child GIT, parent/child Expedite and Excess/Fulfillment count readers. The corresponding daily implementation lives in `mta/presentation/daily_planning/planning_overview_sql.py`.
- Existing endpoint is `GetPlanningDataCount`; the frontend Planning service uses `useMutation`, so it does not provide ordinary query-result reuse by identity across return navigation.
- Four cards expose TEN totals: GIT parent/child/custom; Expedite parent/child/custom; Excess review/custom; Fulfillment review/custom. Preserve all ten even if a particular layout displays fewer numbers.
- Existing working3005 serves the April7 retained fixture. Pin the actual deployed image, selection and source once at execution; do not assume the checkout equals the deployed image. Preserve BPR5000-row default and all existing MTA/MTO services, identities, grants and data.
- BPR index trial is closed/rejected; DBM index assessment is a separate closed task. Old MDM approval-to-day remains paused. Guided canonical-order stop remains a separate acceptance boundary. Do not resume, repair or relax them here.

## Finite implementation: S1–S4 only

### S1 — exact contribution contract

Inspect ONLY the ten existing count selectors and their direct prepared sources. Record a compact metric map: family/direction/custom branch, native source grain, eligibility conditions, business-date rule, product code owner, location/parent owner, equality profile, source occurrence multiplicity and failure conditions. Reuse existing source maps and fixtures; no report inventory campaign.

Choose a typed contribution relation grouped by metric and the EXACT product/location authorization keys of that selector. Each row carries native occurrence multiplicity before live permission weights. This concrete initial design avoids caching global totals or user-specific snapshots. It may contain many small rows; measure preparation/storage rather than promising ten physical rows for all users.

Do not silently normalize raw codes or convert NULL to empty string. If different metrics use different key comparisons, retain their exact representation/profile in the preparation recipe and reader. Preserve parent-vs-child owner differences, native duplicate joins and numeric overflow behavior. A contribution count is additive only where the actual selector is additive; if a metric contains a DISTINCT/non-additive boundary, preserve its exact typed membership/grain rather than summing precomputed distinct counts. Resolve that one direct seam without expanding into report redesign.

Use existing permission expansion at read time. Multiple assigned permissions may create weighted membership, not just boolean access. Do not build a global count and return it to restricted users. Do not precompute per user or hardcode current actor IDs.

### S2 — typed preparation and atomic generation admission

Add a bounded Django model/migration on the actual serving migration branch, independent of paused MDM migrations:

- Summary receipt: run/source digest, business date, selected reporting generation/recipe identity, required metric roster, contribution count/digest and completion status.
- Summary contribution: receipt owner, fixed metric enum, ordinal, nullable exact product/location authorization keys, native occurrence count. Operational rows remain typed relational; JSON only for bounded metadata.
- Unique receipt/ordinal identity and an owner/metric index sufficient for this small read model. Do not create an index on every field or include wide source records.

Populate contributions directly from existing prepared/source relations after all required Planning layers are complete. Avoid reading whole wide tables into Python or running all ten final scoped counts for every account. One generation can be prepared once, in bounded batches/set SQL, with original occurrence/multiplicity preserved.

Integrate an explicit `planning_summary` step into the existing reporting preparation coordinator and `prepare_daily_ui` contract. Add only its exact dependencies and verifiers. `execute_day` calculation stays unchanged: daily operator pipeline commits the day, prepares reports including the summary, then admits/publishes the coherent generation.

Separate physical generation creation from publication: readers see the new summary only with the completed matching reporting generation. Partial/failed attempts cannot become visible. An interrupted attempt preserves its failure and is resumable/idempotent for the SAME source; never overwrite accepted receipts or regenerate business days. Retain the previous selected coherent generation if the new one fails; do not show its numbers under the new date.

Support one zero-calculation materialization for the currently selected3005 fixture using its exact retained source and existing reporting selection. For daily integration proof reuse an existing accepted owned daily source in an isolated existing facility, if available. No new daily run, no borrowed closing, no trace-derived replacement, no serving selection switch. If a necessary daily source is unavailable, report that exact integration-proof gap; do not fabricate a successful day.

### S3 — fast read and frontend reuse

Keep `GetPlanningDataCount` and its current envelope/field names. For an admitted matching summary, read only contributions plus exact current permission weights and sum per metric. Reuse the existing scope resolver and authentication boundary. Request handling must not invoke GIT/Expedite/Excess/Fulfillment detailed count readers on this prepared path.

Retain existing unsupported-filter, missing-source, nonempty transit and admission qualifications. Do not silently make an unsupported Planning overview filter valid. A missing/not-ready/changed summary must be explicit unavailable; preserve a named legacy/reference path for comparison or feature rollback, not an invisible slow fallback. A supported metric with genuinely zero contributions returns zero. Missing metrics, missing source and failed preparation never become zero.

Expose/use a small Planning identity through the existing report identity mechanism where its contract supports both fixture and daily owners. Extend only the missing Planning identity seam; the current Guided cache identity is fixture-specific and must not be blindly reused for daily runs. Identity includes selected run/date/source/generation/summary recipe, authenticated actor and permission revision/signature, plus normalized supported request. No new authentication provider, TTL bypass or general caching framework.

Use the existing TanStack Query/browser read infrastructure to retain this small summary outside quadrant component-local state. Key by the verified identity; preserve original response data from mutation by consumers. Returning within the same Planning session uses it without another heavy summary calculation. A cheap identity check on remount is acceptable; the goal is no repeated expensive count work, not skipping access validation.

Invalidate on logout/account change, permission identity change, publication/selection/date/generation change, relevant request change and any existing write event that actually changes this summary's source revision. Do not key solely by calendar date or a generic `Planning` key. Never show prior-user counts before current identity validation. Prevent a late response from an older request from replacing the current summary. Do not cache failed/unavailable responses as success or persist credentials in browser storage.

Business date on the page and all card counts must come from the same accepted identity, rather than combining an independently refreshed last-run date with old cached numbers. Preserve all detail navigation and the selected quadrant when using back navigation.

### S4 — affected proof, controlled3005 delivery and STOP

Prove only the complete Planning-summary flow:

1. Exact ten-field responses against the retained original selectors for broad, restricted, denied and existing overlapping permission assignments. Focused retained NULL/duplicate/parent-child/date-boundary cases where required; no new fixture campaign or whole-publication checksum scan.
2. Preparation transaction/failed attempt/nonpublication, idempotent same-source retry, source/recipe/generation mismatch denial and old valid selection preservation. One focused injected preparation interruption is sufficient; no recovery framework.
3. Required Django check, makemigrations check, actual migration plan and migration-enabled fresh-owned-PG schema verification for the new schema only. Reuse existing exclusively owned facilities; never apply paused migration branches or change unrelated apps.
4. One existing accepted daily-source preparation/coordinator proof without calculation, alongside selected fixture materialization. Confirm the production pipeline command includes the new step. Runtime fixture proof alone does not certify daily integration.
5. One controlled3005 deployment of task-owned overlay/schema/frontend changes with preflight/rollback. Pin deployed foundation image/hashes; exclude unrelated dirty source edits and preserve working optimized readers, source selection, MDM data, MTO routing/accounts and other service identities. Existing configured resources only. No new ports or shared restart.
6. Three before/after actual summary API observations for broad and restricted actors (no warmups/cache flush/favorable retries), recording source/scope/plan/SQL and whole API wall boundaries. One browser journey per actor: enter Planning, enter ONE quadrant and return, observe ready cards, correct date and absence of another heavy summary calculation. Verify identity change invalidation with existing scope/publication test facilities; do not switch serving source merely to create a test.

Correctness/access/source consistency are mandatory. Performance evidence must show materially lower uncached summary API time (target at least50% median reduction) and no repeated detail-count work on unchanged return navigation. This target is for this summary endpoint only, not legacy parity or whole-page capacity. Record actual click-to-ready-card observations with tool overhead qualified; no invented milliseconds/p95 or broad quadrant timing campaign. If a target fails, diagnose ONLY observed time in this summary flow and make the smallest in-scope correction; do not open general optimisation.

Finish one cohesive code/migration/tests/docs commit/push, upstream verification and a handoff: exact count map, contribution population/storage/preparation costs, recipe/source identities, verified fixture/daily commands, deployment/rollback, sample API and navigation evidence, admitted scope and honest unresolved limits. Then STOP.

## Authority and protections

This plan release authorizes necessary bounded implementation, additive Planning schema, zero-calculation summary preparation, task-owned3005 deployment and affected verification above. No routine per-file approval waits. Exact new business-source authority, calculation/date replay, business-count interpretation change, grant expansion or protected-resource change requires ONE concrete human decision before dependent work; independent work continues.

No new engine or legacy calculation calls. No index trials/removals, Guided/DBM/BPR/MTO repair, browser performance roster, wider test campaign, frontend redesign, cache/auth framework, scheduler, ClickHouse or producer expansion. Protect3002–4/3006, accepted inputs/actions/rows/seals/failures, stopped temporal artifacts and unrelated dirty work. Existing4GiB/twoCPU application and existing DB ceilings; no resource increase/reset/prune/borrow/shared restart.

Rollback restores only the task-owned feature selection/image/config and preserves existing selected publication. Keep additive tables/failed evidence unless explicit approved cleanup; no destructive migration rollback against shared data. Missing new summary must never trigger a fake successful overview.
