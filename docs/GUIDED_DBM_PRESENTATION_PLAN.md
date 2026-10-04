# Guided DBM suggestion presentation — bounded performance delivery

Authorized by the human on 4 October 2026 after satisfactory BPR delivery.
Starting checkpoint: `194ade6`, clean and pushed. Preserve accepted BPR/BTR.
This file is the execution contract; `docs/MIGRATION.md` is the ONLY status tracker.

## Single outcome and boundary

Make the existing Guided Insights **DBM Norm Suggestions** tab faster from user
selection to all four usable chart/table panels than canonical legacy, on the same
retained April7 heavy dataset, authenticated scope and resource allocation.
Deliver all four consumers together: location, suggestion pie, SKU and ageing.
Do not close at prepared-table readiness, HTTP200, an isolated pie improvement,
backend timing or screenshots without completed responses and usable panels.

This is ONE tab with four panels, not all Guided screens. Availability trend,
availability ageing, Chronic, Excess, Custom Screens, main actionable DBM,
Research, Planning, BPR and BTR optimization are excluded. Retain their routing.
Current facts/suggestions remain authoritative; preparation is derived read data.
Simulate one daily preparation from existing April7 inputs; no ingestion/replay,
scheduler, refresh service, automatic activation or other-day generation.

## Researched path and evidence

- `GuidedInsights/index.tsx` selects `DBMNormSuggestions/index.tsx` for
  `dbmnormsuggestions`. Its effect requests all four APIs with Promise.all;
  the page overlay waits for all four. Each panel includes the existing chart,
  table/modal view and client download controls.
- Existing services send `{}` to the four POST routes; filter changes cause
  refetch but are NOT forwarded by these wrappers. Preserve this inherited
  behavior: do not silently implement new UI filtering. Existing direct-API
  predicate/scoping contracts still require preservation.
- `views.insight_data` calls `insight_context`, `insights.joined_rows`, scope,
  `InsightPredicate`, then `insights.project` separately for each kind.
- Retained inputs: daily DBMNormSuggestionsData97097, DBMMaster97097,
  SkuAttributeData1965, LocationAttributeData210, SkuLocAttributeData97299;
  SiteDescriptionTbl210 and SKUDescriptionTbl1965 for respective panels.
- Existing full-population lookup receipts prove97097 joined occurrences for
  each suggestion kind; this is fixture evidence, NOT a uniqueness assumption.
- Prior deployed single observations: loc21.05s, SKU24.95s, pie33.52s,
  ageing15.07s. They are not a controlled legacy comparison.
- Controller's single current pie profile:97097 joined/selected rows,3 output
  groups; source context8.5666s, join preparation3.4426s, scope/filter0.8129s,
  aggregation0.0463s, total12.8683s;28 database execute calls total0.5757s.
  Cursor fetch/decode and checks are included in surrounding stages, not this
  execute total. Evidence: `D:/freshvcf-build/evidence/guided-dbm-preparation-research-20261004/pie-profile.json`.
  Do not repeat full discovery or claim these numbers predict UI speedup.

## Four contracts that must remain distinct

| Endpoint / kind | Existing result and exact semantics |
|---|---|
| DBMNormSuggestionLoc / loc | Group by location; NormInc/NormDec, MAX description/location attributes; decreasing sum of inc+dec, stable source occurrence order for ties. INNER site-description join preserves missing exclusions and duplicate multiplication. |
| DBMNormSuggestionSKUs / sku | Group by SKU; NormInc/NormDec, MAX description/SKU attributes. INNER SKU-description join preserves multiplicity. API retains existing source-group order; frontend stable-sorts by inc+dec and charts top10 while table retains complete rows. |
| DBMNormSuggestionPie / pie | Group by suggestion; COUNT semantics give NULL group count0 and omit NULL suggestion key. API returns raw counts. Existing frontend computes scoped percentages to two decimals; table uses those percentages too. No new API envelope or replacing raw counts with percentages. |
| DBMNormSuggestionAgeing / ageing | Exclude NULL/No Suggestion and NULL ages; bands age<2, <4, <7, else7+ (including inherited negative-age behavior); inc/dec counts; fixed band order. Use persisted age, never today's wall clock. |

All preserve scalar empty result `null`, omitted NULL properties, exact wire types,
attribute aliases/casing, duplicates, existing match semantics, parent-filter
multiplicity, permission membership multiplicity and canonical invalid-filter
responses. Custom-only filter call gates and endpoint-specific category ownership
must not be repaired or generalized. Use InsightPredicate as existing validation
and term source. Source joins in this family currently use exact Python keys;
do not substitute BPR's normalized join expressions. Predicate comparisons and
parent matches retain their existing normalized semantics where applicable.
Grouped text MAX/order must match accepted Python/canonical results; do not assume
the PostgreSQL default collation is equivalent. Never infer counts from chart top10.

## One preparation/read implementation

Prepare ONE typed relation containing occurrences of the common daily join:
suggestion INNER SKU INNER location LEFT pair-attributes INNER DBM master.
Retain source ordinals, original keys, raw filter-owner fields, master parent,
suggestion/age and required typed display attributes; stable classifications
(inc/dec/age-band) may be prepared exactly. Bind it to run/source/schema using
the existing narrow BPR pattern; no generic abstraction or new generation system.
Do not persist nested row JSON or four copied wide tables.

Site/SKU descriptions are endpoint-specific INNER joins. Keep their small typed
relations as bounded serving joins unless qualifying data proves a cheaper exact
attachment; do not deduplicate them or include their multiplicity in pie/ageing.
Qualify actual common/description-expanded occurrence counts once before building.
Keep source input rows unchanged. Record preparation time, row count and storage.

Serve all four through SQL scope/filter and group aggregates over prepared rows;
return existing small response contracts. No full candidate transfer, Python
joined-population reconstruction, database JSON packaging or per-scope/filter
materialization. Live permissions remain request dependent. Daily Guided output
does NOT become the main DBM Apply/Sleep command overlay. Normal-publication
read/admission behavior remains unchanged; future producer integration is debt.

Frontend: keep current components/four APIs/parallelism/complete tables/top10.
Small pie percentage and chart-option construction are legitimate scoped display
work, not reasons for a new schema/protocol. Change only measured overhead in this
component; no forced transformation migration. Fix a null/rejection/stale-loading
failure only if encountered by affected checks, with the smallest local change.
Do not suppress responses, trim output fields or show partial old panels as done.

## One-pass sequence and finite acceptance

1. Reuse research/provenance. Retain complete BEFORE responses for all four,
   broad scope and ONE restricted supported-filter case; qualify preparation
   grain. Capture ONE matched before journey per stack if not already retained.
2. Build the relation and all four readers as one correction. Use normal Django
   migration checks/plan and real PostgreSQL verification; additive ownership,
   atomic preparation and run binding. Reuse BPR guard/migration patterns without
   turning them into a platform. No broad admission redesign or integrity bypass.
3. Prove all four complete outputs against retained BEFORE values, every field,
   type/NULL/occurrence/order. Add focused PostgreSQL differentials for duplicate
   dimensions/descriptions/master, unmatched inner/left joins, permission/parent
   weights, NULL suggestion and ageing boundaries. Reuse existing proven filter
   contracts; no combinatorial matrix or whole historical suite repetition.
4. Build affected services/frontend only if changed; deploy only changed3005
   services. Verify selected run, BPR/BTR switches/generations and protected
   container identities unchanged. Record rollback to194ade6 with retained data.
5. Run exactly THREE paired legacy/modern full-tab journeys, alternating order,
   same data/scope/request bodies/layout/series and existing matched-resource
   window used for BPR (DBs3GiB/2CPU, APIs4GiB/2CPU; restore in finally).
   No database copies, higher limits or concurrent capture jobs. Time tab action
   through all four completed responses, overlay gone, four current charts rendered
   and table toggle usable. Retain per-request times/bytes and final screen timing.
   Modern median must be lower than legacy; show raw samples. Do not substitute a
   single pie timing, omit slow panels or sample until favorable. Exactly one
   affected table toggle/sort and existing client-download content check per distinct
   data contract is sufficient; no full export/interaction campaign. Compare one
   restricted actor/API selection; don't turn filter defects into new feature work.
6. Commit/push a coherent delivery and update MIGRATION.md and existing handoff
   with exact results, preparation cost, residuals and future daily-producer debt.
   Stop at this tab. If an exit fails, report the attributable unmet criterion and
   smallest next decision; do not broaden silently. Browser challenge consent must
   follow actual browser rules; complete independent implementation/proofs while
   awaiting any required human action, without bypassing authentication.

## Hard exclusions

No generic frameworks/caches/registries/services, universal snapshots, new metadata
protocols, integer keys, grid/chart replacement, DB copies/reset/repopulation,
engine/state/fact/date changes, new command/workflow behavior, MTO, new ports,
3004 cutover, resource escalation, scheduler/daily ingestion/automatic activation,
unbounded benchmarking or repeated passing proofs. No numeric token budget.
Missing data stays an explicit dependency, never fabricated empty data.
