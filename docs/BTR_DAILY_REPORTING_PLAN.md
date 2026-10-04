# BTR daily reporting layer: authorized implementation and slice test

Explicitly authorized by the human on4 October2026: implement and test the BTR
reporting slice using existing textual product/location keys, then assess the
performance gain before considering integer keys. The prior query-only tranche
ended at its evidenced blocker in5d7ef83. This is the next bounded intervention,
not a new migration programme. Status belongs only in docs/MIGRATION.md.

## Execution authority and fixed slice

Implement typed BTR reporting tables/indexes, their daily builder, generation
selection and report reader in the existing Fresh PostgreSQL database. Add real
Django migrations. Use existing canonical legacy and modern databases/services;
NO new database copies/restores, full-copy verification or replacement stacks.
New derived BTR tables populated from existing committed inputs are the expressly
authorized reporting implementation, not permission to clone source databases.

Retain textual SKUCode/WhCode/LocCode and existing comparison semantics. Do not
introduce or evaluate integer product/location dimensions or a star-schema rewrite.
Technical generation IDs and duplicate/source-row ordinals remain permissible;
they are not substitute business dimension keys. Integer-key work is deferred
until the human reviews this intervention's measured results.

The slice includes BTR Physical Inventory and Dispatch grids/counts, existing
filters/scopes/horizons/paging and affected exports. It uses the full retained
April7 population (97299 counts per branch), not a reduced-row demonstration.
Preserve existing endpoints/frontend behavior and existing source exceptions.
No other report family, workflow, engine/F1/F2 modification or general framework.

Necessary existing local legacy launch/configuration and temporary matched-resource
changes are already authorized. Necessary3005 MTA build/deploy/restart and additive
BTR migrations are authorized for this trial after correctness checks. Use explicit
opt-in selection so the accepted reader remains immediately recoverable. No new
ports, credentials/grant changes or unrequested infrastructure expansion. Do not
ask again for these permissions; ask before expanding beyond this slice.

## Decision and boundary

Assess a BTR-specific, typed, publication-bound reporting projection while keeping
accepted engine state authoritative. Compare the accepted reader with a narrow
selection/join-reference structure first; test full prejoined serving rows only
if the narrow design leaves measured repeated work. Adopt the simplest design
that preserves outputs and meets matched heavy-VM legacy performance gates.
No general report framework, DBM/workflow redesign, engine change or F2 replay.

Both Physical Inventory and Dispatch are required. Count, grid and export may need
different relations because their native join semantics differ; they share one
generation identity, not an artificially unified row definition. Retain duplicate
source identities, NULLs, full filter fields and defined ordering. A SKU/location
pair is not assumed unique. The rejected key-prefix optimization's tied-row
failures are mandatory adversarial cases, not permission to invent a tie-break.

## Daily refresh contract

Align refresh with the existing successful daily calculation/publication cycle,
not a new timer, hourly refresh or per-request rebuild. execute_day remains the
sole production calculation boundary. After the day's authoritative output has
committed and passed existing admission, build the corresponding BTR generation
from those committed inputs. Reporting construction must not alter calculation
results or retroactively mark a successful calculation failed.

Identify a generation by source kind, run/date, output/input identity and projection
version. Persist typed report rows with source references and duplicate ordinals.
Build privately, validate complete required populations and both branches, then
atomically activate the complete generation. No partially refreshed grid/count/
export mix. Bind related requests to the same selected generation using the
existing run-selection contract where possible; if that cannot provide consistency
across a daily switch, identify the required API/UI contract change before adopting
the design. Do not silently add a frontend token or mix dates.

Failed build leaves the prior admitted generation intact for explicit selection;
never label it as the new day's data or silently serve it for a requested new run.
Expose accurate selected date/readiness through existing contracts. Retry the same
source/version idempotently, retain failed-attempt evidence, and validate existing
completed generations rather than recomputing accepted outputs. On restart resume
or discard only owned incomplete reporting work; never reset engine state.

Retain current and previous complete reporting generations for rollback at minimum.
Historical BTR and retained evidence obligations remain: do not delete old data
merely because two active generations suffice for a rollback mechanism. Define
retention/garbage collection separately before any automated deletion.

Live identity grants and request filters remain read-time authorities. Precompute
stable business joins and scope attributes, not per-user entitlements. Establish
whether any BTR input changes intraday: if so, document its existing visibility
contract and stop before silently replacing that behavior with daily staleness.
Daily refresh is the intended cadence, not permission to conceal live mutations.

Fixture and modern outputs use the same reporting/query contract where equivalent,
with separate source adapters and provenance. The immutable April7 fixture gets
one explicitly built generation for benchmarking; no invented daily fixture replay
or fabricated accepted calculation receipt. Normal retained outputs are functional
compatibility proof, not scale-performance baselines.

## Finite assessment sequence

1. Reuse EXISTING databases, canonical legacy consumer, resource controls and
   measurements from5d7ef83. Do not resume copy work or repeat source discovery.
   Record the expensive work and exact source dependencies for grid/count/export.
2. Specify the narrow typed relation, indexes, source identity, ordering behavior,
   generation lifecycle and expected storage/build cost. Map daily refresh onto
   the existing publication orchestration; no separate scheduling platform.
3. Implement the authorized bounded slice in additive reporting tables and focused
   tests. Compare complete results for both branches, scopes, filters,
   horizons, first/later pages, exports and adversarial duplicates/ties/NULLs.
   Preserve the Category alias-order qualification only in its approved fixture
   scope. A failed semantic comparison rejects the candidate irrespective of speed.
4. Measure matched legacy/Fresh API and browser performance on the full VM dataset,
   using the established warm/cold/concurrency protocol and comparable resources.
   Also measure generation build time, peak memory, additional storage, restart,
   retry, atomic switch and rollback. Establish the available daily refresh window
   from the actual schedule rather than inventing a build-time SLA.
5. Decide: retain existing reads, adopt the narrow projection, or adopt a precisely
   justified prejoined BTR structure. Deliver one decision with schema/lifecycle,
   comparative evidence, remaining limits and rollout/rollback boundary. No
   automatic adoption or extension to other report families.

## Concrete test and delivery pass

- Record a short schema/lineage and builder design in the implementation handoff,
  then implement; do not spend the tranche generating more plans. Start with the
  narrow structure. Full prejoining is allowed only within BTR if measured remaining
  join work justifies it; preserve distinct count/grid/export contracts.
- Compare every field, row multiplicity, type, NULL and defined ordering against
  the accepted reader and canonical legacy consumer. Include the retained30
  adversarial cases, both source kinds, broad/restricted scopes, empty results,
  first/later pages and exports. Normal engine outputs are functional regression
  only. Do not patch assertions or invent order to rehabilitate a faster candidate.
- Prove builder idempotency, failure before activation, restart/retry, concurrent
  reads during switch, date/run consistency and rollback. Use retained source
  publications/test transactions, not calculation replay or changed frozen rows.
  Integrate the builder at the existing daily publication boundary where present;
  if no scheduled integration exists, expose and verify the exact post-publication
  command/runbook step rather than silently creating a new scheduler.
- Reuse prior full response and resource evidence. Compare the reporting candidate
  with the accepted Fresh reader AND legacy under the same declared resource budget.
  Retain five warmups/30 alternating measured observations, concurrency1/4 and five
  application-cold repetitions; measure complete API and real browser journeys.
  Record median/p95, throughput/errors, payload bytes, query/build time, CPU/memory,
  added storage and current host conditions. No benchmark during projection build.
- Correct the SQL resource setup before repeating c4: fit SQL internal buffer
  allocation/non-buffer headroom within its enforced total ceiling. Apply equivalent
  feasible aggregate budgets to both databases/application tiers and record/restore
  settings. Reuse existing services, not copies. If a larger common budget is needed
  to operate both stacks fairly, choose from measured local headroom under existing
  resource authorization; do not enlarge only one side or call hardware gains code
  gains. Preserve the previous memory failure as failed evidence.
- Repeat the existing fixed-deployment-limit three nine-request bursts, full
  responses, login/profile during load, browser BTR controls/downloads and drain.
  This is distinct from matched-resource parity. Preserve the known SPA-link issue
  as a disposition, not an implied UI fix.
- Run migration checks and affected PostgreSQL tests. Benchmark results and complete
  correctness must pass before leaving the new reader selected. If they fail,
  restore the accepted reader and settings, retain the candidate/evidence, report
  the exact unmet gate and stop. A statistically unproved improvement is not PASS.
- Deliver one comparison table (legacy, accepted Fresh, reporting-layer Fresh),
  daily build/storage cost, exact source/schema/image identities, verified rollback
  and runbook; update MIGRATION, commit/push and stop for human review. No automatic
  integer-key follow-up or broader Stage2–5 continuation.

## Adoption gates

## Human firsthand UI comparison handoff

The human explicitly requests inspecting the new BTR slice on modern3005 beside
equivalent legacy BTR on3002 (canonical API5153). This extends browser proof into
a usable handoff: verify real login and leave both existing stacks available,
with modern requests demonstrably selecting the new reporting generation and
legacy reading the equivalent retained April7 data. Match branch, scope, horizon,
filters and page size. Cover both Physical Inventory and Dispatch; report any
accepted-reader fallback honestly so a working screen is not false slice proof.
Provide verified direct BTR URLs/navigation, selected date/generation, usable
existing local test login instructions via the established local runbook, and a
short matching inspection sequence. Do not reset credentials or rely solely on
screenshots. Restore benchmark-only resource limits before handoff and verify
both stacks still respond. No new port, UI redesign or source-data replacement.

This is trial visibility, not a waiver of the adoption gates. Complete correctness
is required to leave the candidate selected. If only the performance gate remains
unproved or failed, the user's explicit inspection request permits leaving the
correct candidate opt-in on3005 as a clearly documented UNACCEPTED TRIAL with
verified rollback; do not call it accepted. If correctness/permissions/readiness
fail, restore the accepted reader and state why the requested slice is unavailable.

## Adoption criteria

Complete correctness and permission proof; Fresh median/p95 no worse than legacy,
throughput at least equal and errors no worse under matched resources; practical
daily build/storage costs; no partial-generation visibility; safe restart/retry
and rollback; functional consumption of normal modern outputs; preserved serving
limits and bounded overlap/login behavior. Missing equivalent measurement remains
UNPROVED. A benchmark pass is not whole-page Stage2 acceptance.

Schema implementation requires real migrations, Django check,
makemigrations --check, migration plan and migration-enabled PostgreSQL tests.
The bounded3005 trial above is authorized. New ports, F1/F2 mutation and broader
Stage2–5 work remain excluded. The outcome decides whether this reporting layer
is sufficient; integer product/location keys remain a later human decision.

## Addendum: remove BTR frontend work from the report journey (4 October 2026)

### Superseding human instruction: stop benchmarking and implement frontend now

The latest direct instruction authorizes frontend implementation immediately and
supersedes the benchmark-completion dependencies below. Stop scheduling c4 batches
at the next complete legacy/modern pair, at most the pair already in flight; retain
all completed samples. Do not pursue the30-batch target. Gracefully stop the owned
runner, preserve its cleanup/finally path, drain bounded in-flight requests and
restore temporary resource settings. Verify existing services are ready. Mark
partial evidence as human-truncated and remaining cold/load/comparison campaigns
DEFERRED, not passed. Do not start another benchmark window.

Begin frontend edits while cleanup completes; deploy only after the measurement
has stopped. First remove confirmed unnecessary work: same-view grid remounts,
unstable/repeated column preparation, uncancelled layout timers, full-response logs
and redundant configuration reads with proper invalidation. Preserve stale-response
protection, truthful loading, intended resets, errors, permissions and all features.
Keep Availability/coercion/horizon semantics intact; do not make a prepared-data
schema or grid-library replacement a prerequisite. The earlier proposed prepared
values remain a later evidence-based option, not this first implementation pass.

Verification is focused affected tests/build, one representative before/after
browser capture for On-Hand, Pipeline and Both, and affected interaction smoke
checks (paging/filter/layout/error/race/export). This small sample is diagnostic,
not p95 proof. Reuse existing correctness evidence. Missing baseline timings must
not delay edits or trigger a new campaign. Deploy verified changes to existing3005,
keep rollback and legacy available, record results in MIGRATION.md and commit/push
at the logical frontend checkpoint. No redesign, engine change, database copies,
integer keys, reduced5000-row workload or unrelated report work.

### Controller limit on benchmarking (latest human direction, 4 October)

Do not expand benchmarking while preparing this intervention. Preserve the completed
30-observation c1 evidence and finish the already-running finite c4 protocol once;
do not restart its warmups, increase its sample count or add resource/concurrency
combinations. State whether samples mean batches or individual journeys and retain
that distinction in summaries. Reuse correctness, lifecycle, migration and source
identity proofs unless a relevant change invalidates them.

Before the next run, put one compact remaining-check list in MIGRATION.md, with
existing exit criterion, fixed sample count and stop condition for each check.
Execute only the existing missing browser/cold, normal-limit load/login/drain and
rollback gates, consolidating overlapping checks. Attribution is a bounded
diagnostic for the frontend decision, not another repeated benchmark campaign.
No new generic harness, alternative grid trial, query candidate, resource sweep or
expanded report/filter/page matrix. Reuse tools already written. A retry needs a
specific failed check and relevant correction; timing variation alone is not a
reason to rerun. Do not repeat successful API suites after frontend-only changes
unless the request contract or server behaviour actually changes.

The unmatched older accepted-Fresh resource baseline remains an explicitly
identified evidence gap; do not silently present it as a matched comparison or
launch another full matrix merely to fill a table. Disposition any deferred gate
in MIGRATION.md and retain UNPROVED acceptance where applicable. Benchmarking must
produce a finite checkpoint and the evidence needed for the frontend addendum,
not indefinitely postpone that intervention. Existing semantic checks and full
5000-row workloads are not weakened by this scope limit.

Requested scope: inspect the existing frontend and plan eliminations, not deploy
frontend changes during the current benchmark. This addendum is the proposed
implementation boundary; MIGRATION.md remains the only status tracker. Preserve
the running reporting trial and its before-change evidence. No engine changes,
integer business keys, new databases, UI redesign or reduced benchmark population.
Daily refresh remains the producer cadence for any added derived presentation data.

### Findings and priority

These are source-confirmed operations, not yet measured shares of browser latency.
Paths below are relative to the repository. The BTR directory is
`frontend/src/VectorFlow/Pages/MTA/InsightsAndTrends/BTR/`.

1. **Primary calculation target: full-row preparation.**
   `frontend/src/helpers/utils.ts:3367` (`mapBTRRowData`) visits every field,
   converts NULL to an empty string, preserves seven named identifier/description
   fields as strings, and applies JavaScript parseFloat to other numeric-looking
   strings. It constructs a new object and spreads it into further copies, then
   scans D90 backwards for the selected horizon to calculate Availability.
   `useBTR.tsx:329,358,385` invokes it after each grid response, for both arrays in
   Both mode. At 5000 rows per branch and 90 days this is 900000 day iterations,
   in addition to scanning every field and allocating row copies. This is work per
   response, not per visible viewport and not on every React render.
   The target is to remove this full mapper from the opted-in prepared-data path;
   the calculation cannot simply be deleted because it produces displayed values.

2. **Avoidable grid teardown and reconstruction.**
   `useBTR.tsx` combines grid, count, UI-config and saved-state request loading flags.
   `index.tsx` renders the grid only when that combined flag is false. Consequently,
   these loading transitions unmount/recreate the grid, including split views.
   Keep the grid instance mounted for an unchanged view and show a loading overlay;
   block stale-data actions and clearly distinguish pending from current results.
   Apply new rows only for the latest valid request. Preserve the existing intended
   page/filter resets, failure and empty-state behaviour. Do not claim completion
   merely by hiding the spinner earlier.

3. **Repeated column/configuration work unrelated to new data.**
   `useBTR.tsx:603-637` rebuilds column definitions on row-array replacement even
   though definitions use configuration, labels, horizon and view, not row values.
   Remove row-data dependencies; include all actual dependencies and stabilize
   callbacks/labels. Split views currently mutate incoming definitions; use stable
   view-specific copies before sharing memoized definitions. Preserve column order,
   widths, filters and split-scroll behaviour. `useBTR.tsx:569,587` restores layout
   with uncancelled 2000ms timers; replace these with one restoration when the grid,
   columns and saved state are ready, with cleanup. These timers are potential late
   relayout, not evidence of a mandatory extra two seconds in every load.

4. **Unnecessary repeated ancillary work.**
   Every Apply calls getBPRUiConfig (`useBTR.tsx:455`); tab changes read saved state.
   Reuse configuration within the current actor/report session with explicit
   invalidation on save/reset, identity or relevant configuration changes. Keep
   permission checks live. Trace request initiators before removing any grid fetch:
   mount/tab/filter paths exist, but duplicate live requests are not yet proved.
   Grid/count requests already run concurrently; do not add another parallelization
   change or drop the count required for correct pagination.
   Remove full-response console logs at lines330,359,386 from the serving build.
   The hidden export grid in index.tsx is a conditional removal candidate only
   after checking toolbar/context users; the visible export callback uses server
   CSV export, but that alone does not prove the hidden path is unreachable.

### Removing calculation from the browser without changing its meaning

First preserve the existing mapper as the executable presentation oracle. Compare
its actual outputs, including types, against any prepared representation. The
current SQL reader explicitly projects Availability as NULL
(`mta/presentation/btr_sql.py:209`), so existing API data is not already grid-ready.
Neither bc/BlackCount nor a simple colour count is an established substitute.

If profiling shows material mapper cost, extend the BTR reporting projection only
as far as needed to supply prepared values at the daily build boundary. Bind them
to the same immutable generation, branch and source-row/duplicate identity; never
collapse rows by SKU/location alone. Keep live authorization, filtering, ordering
and paging at read time. Use an explicit opt-in presentation contract so canonical
API consumers and exports retain their existing raw types/NULLs. A response-level
prepared-version marker must be trustworthy before the frontend skips its mapper;
unsupported generations/readers retain the existing mapper. Do not silently change
the canonical endpoint's default response to make a parity assertion pass.

Prove numeric-prefix strings, protected leading-zero identifiers, NULL versus empty
versus missing fields, sentinel -99999999, negative/fractional values, NaN/Infinity
and rounding. JavaScript parseFloat/parseInt/toFixed are not interchangeable with
SQL casts or ordinary Python rounding. Existing unexpected coercions are retained
behaviour, not an opportunity to repair legacy display rules.

Availability is currently 100 * count(nonempty daily value with parseInt(value)
< 100) / (horizon - count(empty daily values)), rounded through toFixed(2) and
parseFloat. The frontend horizon state defaults to90; server date filters can
return a different subset of D columns. Missing columns and empty columns do not
behave identically. Enumerate actual reachable request/horizon combinations and
match them exactly before choosing stored summaries. Do not store only a90-day
value and reuse it for every range, or precompute all possible ranges speculatively.
If request-specific work remains, use proved compact summaries or a bounded
page-level presenter and report that cost as moved to the server, not eliminated
from the whole journey. Daily-derived reusable work should execute once per
generation, not rescan all90 values for every user request. Keep the mapper for
cases whose exact semantics have not been established.

### Bounded implementation order and proof

1. Finish/capture the existing backend-only benchmark. Then profile the browser
   on the same full April7 population, branch/scope/date/horizon/page size and
   generation. Separate action-to-request, request count/queue/server wait,
   response transfer/JSON parsing, mapper CPU/allocation, React/grid initialization
   and stable usable-grid time. Record decoded payload separately from wire bytes.
   Do not add browser load to an ongoing matched database benchmark.
2. Apply measured redundant-work removals first: stable mounted grids, stable
   definitions/readiness-based layout, ancillary-config reuse and no response logs.
   Verify request races and UI actions, not just first paint. No request cache may
   reuse rows across actors, scopes or generation changes.
3. Only if row preparation remains material, implement the smallest proved
   prepared-value extension above, with daily build/storage and server-cost evidence.
   Do not begin a speculative wide-table rewrite. JSON parsing, transfer, visible
   cell rendering and requested grid interactions remain necessary work; do not
   disguise them by reducing5000 rows, omitting daily fields/colours, disabling
   filters, or changing the legacy comparison workload.
4. Compare unchanged frontend + new reporting reader against optimized frontend +
   the same reader, and canonical legacy, using the existing repeated browser
   protocol (or define it before recording samples). Report sample count, median,
   p95, long tasks and request/payload counts for both branches and Both layouts.
   Exercise paging, filters/date ranges, saved layouts, rapid navigation, empty
   results, failures, restricted scopes, daily graph and exports. Preserve complete
   row/value/type/order/duplicate comparisons and the existing accepted exceptions.
   Keep ordinary3005 settings separate from matched benchmark resources.
5. Accept only measured click-to-usable-grid improvement without correctness or
   material interaction/API regression. Report component savings and total time;
   if total delay remains server/transfer dominated, say so and stop at the measured
   remaining bottleneck. Preserve a rollback to the existing frontend/reader pair.
   Apply migration checks only if schema changes are actually needed. Record proof
   in MIGRATION.md; this addendum creates no parallel queue or automatic wider work.
