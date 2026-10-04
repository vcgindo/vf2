# Daily Data Graph — bounded shared-route performance delivery

Authorized 4 October 2026. Start from completed Guided delivery `396a62c`.
Execution contract: this file. Only status tracker: `docs/MIGRATION.md`.
This is a new bounded goal, not a continuation of the completed Guided rollout.
No numeric token budget is supplied.

## Outcome and boundary

Reduce row-icon click-to-usable Daily Data Graph time on these two existing
3005 pages: `/mta/dbm/dbm-norm-suggestions` and
`/mta/insights-and-trends/buffer-trend-report`. Open the modal promptly with
honest loading feedback; also reduce actual graph readiness time. Opening an
empty shell alone is not delivery.

Permitted changes: the two click handlers, shared DailyDataGraphModal and its
existing data type/state plumbing, `DailyDataGraph` endpoint, selected-pair
DBM history reader and narrowly necessary request-local source resolution.
Shared changes must retain other callers' existing contracts. Optional run-date
input may retain the existing fallback for callers outside these two pages.

Preserve selected-run identity, live permissions, DBM command freshness,
six response populations, types/NULLs/duplicates/source order, exact FULL OUTER
date matching, norm history and suspension semantics. Existing legacy date-gap
and chart formulas are not permission to repair business behavior. Retain
F1/F2, accepted BPR/BTR/Guided reads and the existing chart component.

## Established evidence

Both pages await `DailyDataGraph` before opening the shared modal. The modal
then fetches last-run date separately although the response already has RunDate.
Fixture history is already pair-bounded; it does not use Guided Availability's
prepared relation. Its source is DBM consumption/suspension/norm/suggestion
history, not BPR colour history.

Controller native deployed endpoint observations (not browser acceptance):
SKU21101138001000/P016_1001:0.789s,19570 bytes; SKU21101153051000/P015_1004:
0.371s,20534 bytes. Both execute58 SQL calls and return91 StockData records.
These warm-order single observations do not prove multi-second backend delay.
Repeated image/receipt resolution and the sequential date request are concrete
work to remove; do not assert chart rendering dominates without a trace.

## One implementation pass

1. Record the active item and unmet exit in MIGRATION.md. Capture one existing
   modal-opening trace per modern page and its matched legacy counterpart.
   Use the same pairs above, actor scope, selected data and default14-day horizon.
   Separate click-to-shell, DailyDataGraph wait, last-run-date wait and usable
   chart. Reuse existing tooling; no new measurement framework or load matrix.
2. Open the modal shell immediately, with loading/error state and no stale row's
   graph. Populate it when the selected request completes. Close or a newer
   selection must prevent an older completion from replacing/reopening it.
   Use local request identity/cancellation facilities already available, not a
   new request manager. Apply to both click handlers.
3. Pass DailyDataGraph.RunDate through existing state to the modal. In these
   two flows, eliminate the extra last-run-date request and its dependency.
   Use the same date-format/timezone behavior; do not substitute host date.
4. Resolve validated fixture source metadata/receipt inputs once per request
   and reuse them across named pair reads. Keep integrity checks and denied
   responses intact; no global cache or weakening of publication admission.
   Preserve normal and command-bearing read behavior. Keep pair/date filtering
   in SQL. Add at most a targeted pair/date index only if the captured plan
   demonstrates it is needed, with required migration checks.
5. Derive unchanged90-day chart ingredients once per response/run date;
   horizon/suspension interaction selects those ingredients. Consolidate
   unnecessary intermediate state/effect work and stabilize chart options
   where needed. Preserve first-match/duplicate handling, gap values, ordering,
   rounding, tooltips and norm/suspension results exactly. Do not move tiny
   chart loops to the API merely to change their location.

No new materialized table is authorized: this route already reads a small
selected-pair history. If the trace contradicts that evidence or the bounded
corrections fail, report the exact remaining operation and required decision;
do not start a second architecture/profiling project or silently expand scope.

## Proof and closure

Use complete before/after endpoint values for both selected pairs and one
restricted/denied scope check. Focus frontend checks on loading, failure,
close/selection races, eliminating the extra date request, and unchanged default
and one changed-horizon chart values. Reuse affected tests; add only missing
meaningful cases. Run affected backend tests, frontend build and required checks
if schema changes. Do not repeat unrelated passing proofs.

Deploy on3005 using existing authorized preview deployment procedures. Then
perform one completed modern/legacy comparison per entry point, with the same
pairs/scope/horizon and enforceably matched resources through the existing
bounded restoration mechanism. Compare with retained pre-change modern traces
too. Require prompt visible loading feedback and lower click-to-usable graph
time than before and matched legacy; report both separately. Do not use shell
opening as chart completion. At most one extra pair per entry point is allowed
only for an identified noisy/inconclusive observation, preserving all results.
If parity inputs cannot match or timing exit fails, report that precise gap and
stop rather than claiming success or expanding benchmarks. Restore resource
limits after the comparison, including failures.

Commit/push the bounded implementation, update MIGRATION.md and the existing
handoff with actual timings, exact proof and limitations. Stop at delivery or
an evidenced unmet exit; do not begin another UI family.

## Explicit exclusions

No new reporting tables, giant snapshots, caches/frameworks/services/registries,
integer keys, chart/grid replacement, ingestion/schedulers, automatic activation,
database copies/reset/repopulation, new facts/date or engine rules, resource
increases, DBM Apply/Sleep changes, other report optimization or3004 cutover.
The completed Guided review stays paused; this plan does not activate a job.

## Authorized responsive addendum (5 October 2026)

The user also requests correction of the same modal's cramped desktop layout.
Bound the dialog to the viewport, keep a flexible chart and a sufficient details
column, and size the slider to its containing panel without breakpoint zoom.
Small optional shared-component props must preserve other callers. Keep values,
chart semantics and the existing layout/content; no redesign or device matrix.
Verify both DBM and BTR at CSS1280x720 and desktop widths on either side of1688,
including1713, with reachable controls and no horizontal overflow or overlapping
fields. These layout checks do not add performance trials.

## User amendment: open the completed modal (5 October 2026)

The user rejects the thin early-loading strip and requests the full modal once
usable. This supersedes the immediate-loading-shell requirement: keep the dialog
closed while fetching and open it with the prepared response/date. Retain request
identity, close/new-selection protection, errors, exact values and the responsive
correction. This amendment does not authorize further performance resampling.

## Authorized bounded BTR follow-up (5 October 2026)

Direct human authorization in controller thread01a1037c-5d96-7700-87a8-89a575f6c9f8
authorizes one diagnostic opening on deployed003/current, pair21101153051000/
P015_1004, broad actor,14days. Separate input/dispatch, auth/retries, gateway/API
SQL and non-SQL, response, React preparation and completed chart; retain observer
limitations and all earlier evidence. No early loading strip.
If the trace satisfies the retained gates, make no speculative edit. Otherwise
make one smallest correction justified by the dominant measured stage inside the
existing graph request/handler/modal. No cache, table, resource increase, chart
replacement, broad rewrite, engine/permission/data/formula or Planning changes.
Run only affected proofs/build and deploy if changed. One final matched
legacy/modern opening pair is authorized under the existing restoration limits.
Modern must beat2.097s and matched legacy; no more resampling. On success commit/
push and finish; otherwise hand off the exact unmet operation and stop.
This narrowly supersedes the exhausted-test stop rule for this follow-up only.

## Replacement comparison authorization (5 October 2026)

Direct user instruction: "authorised to run the remaining BTR matches".
Run the remaining legacy/modern BTR comparison with the corrected completed-modal
observer and the existing matched resource/restoration limits. Retain all earlier
results. No implementation change or expanded benchmark is implied.

## Selected-pair permission correction authorization (5 October 2026)

Verified direct human instruction in controller thread01a1037c-5d96-7700-87a8-89a575f6c9f8,
turn01a108c6-5fbc-7340-8b0c-816d37d96e34: "authorise the agent for unblocking task."
Implement a fixture-only selected-pair producer-attribute permission reader using
existing immutable admission/receipt guards and unchanged permission expansion.
Preserve invalid IDs, canonical comparisons, NULL denial, duplicate eligibility,
run/day binding, denied response, ordinary/command paths and complete graph bytes.
No cache, table, framework, actions, engine, permission grant or Planning changes.
Keep ready-only modal, date reuse, races and responsive behavior. Capture one
actual serving-request diagnostic with SQL/non-SQL and chart observations; do not
mislabel observer delay as React work. Run affected correctness proofs/build,
deploy3005 and one final matched BTR pair with existing limits/restoration.
Report both earlier chart-ready and settled interactive times; preserve2.097s
baseline. Require quiet user traffic or explicitly qualify interference, without
interrupting services. No resampling/matrix. Commit/push and hand off, stopping at
pass or exact unmet gate; do not weaken integrity if selective equivalence fails.
