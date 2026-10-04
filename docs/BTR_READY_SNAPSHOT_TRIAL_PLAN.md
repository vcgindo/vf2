# BTR ready presentation snapshot — heavy-dataset trial

Approved direction: 4 October 2026. This is a fresh implementation contract for
the user's one-time BTR presentation test. Status belongs only in MIGRATION.md.
Earlier BTR plans and addenda are historical evidence; they do not govern this
trial's scope, sequencing or acceptance. Useful existing code can be reused.

## Execution limits — these govern every section below

Deliver exactly one BTR snapshot trial: one preparation command, the minimum typed
table extension needed for its rows, one direct-read path through the existing BTR
endpoints, the existing frontend consuming those values, and a short delivery note.
Reuse the current generation/admission and prepared-response mechanisms. Do not
introduce another activation registry, metadata framework, worker, scheduler,
queue, cache service, API-versioning scheme, snapshot repository or new UI abstraction.

Only implement changes necessary to remove source reconstruction, full-row display
conversion and daily-value scans from this trial's grid request path. Do not fix
adjacent issues. Counts/exports must retain correctness, but consolidating their
endpoints or redesigning their storage is outside scope. Preserve existing legacy
row semantics even where that requires distinct grid/export derivations.

Permitted boundaries: existing BTR presentation modules/models, a necessary Django
migration, the BTR preparation command, BTR frontend integration and directly
affected tests. Change shared modules only where essential to connect this BTR path;
do not refactor them. Use existing services and ordinary resource allocations.
No changes to calculation engine, ingestion, source facts, identity grants, other
reports or retained legacy code. No cleanup programme for prior implementation.

The listed verification pass is the ceiling, not the start of a larger matrix.
Broaden only to resolve a specific failed affected assertion; do not repeat passing
proofs or rerun timings to obtain a better result. Do not add more plan artifacts,
benchmark tooling or separate review stages. A required browser measurement that
cannot be captured is reported unproved; it does not start a new tooling project.

## Objective and boundary

Prepare the complete BTR data the existing UI consumes once from the already
ported heavy dataset, persist it in typed PostgreSQL presentation tables, and
serve the existing grid directly from those tables. Remove repeated source joins,
row conversion/copying and daily-value scans from the normal trial request path.

Use the existing April 7, 2026 dataset, fixture identity
stage2-vm-dataset-20261003-002, calculation-run identity
bfd75b4b-a9df-4a08-82d3-852e3324b623, and PostgreSQL database
test_freshvcf_stage2_vm_20261003_002. Retain its actual date. Expected broad counts
are 97299 per branch. Simulating the day's presentation output means deriving
it from these retained inputs; it does not mean executing the calculation engine
or inventing another day of facts.

This trial does not implement daily ingestion, calculation, scheduling or automatic
daily activation. A one-time builder stands in for the eventual post-publication
preparation. Daily orchestration is a later task. No source reload, database copy,
integer business keys, new grid library, general reporting framework or other reports.

## 1. Checkpoint before branching

- Reconcile the current deployed BTR/frontend checkpoint with MIGRATION.md using
  existing deployment and test evidence. Record the pending CSV export as passed,
  failed or unproved; do not resume a large test programme to finish the old plan.
- Review the dirty worktree, stage the identified current-task files explicitly,
  and commit the reporting/frontend work as a preserved checkpoint. Include known
  limitations honestly. Keep credentials, external evidence and unrelated edits out.
- Commit this plan and the tracker instruction as documentation; they may be a
  separate commit from the implementation checkpoint. Record checkpoint commit and
  current image/rollback identities. No speculative rebuild or resource sweep.
- Create codex/btr-ready-snapshot-trial from the committed checkpoint. The new
  implementation and migrations belong on that branch. Preserve useful frontend
  changes; do not reset or delete the prior implementation/evidence.

## 2. Prepare the presentation snapshot once

- Use a bounded BTR-specific command to build both On-Hand and Pipeline snapshot
  rows from existing source tables. Store final identifiers/descriptions, category,
  Norm/VirtualNorm, tags, required scope/filter attributes, daily values/colours and
  other fields the current grid actually consumes. Perform stable joins and exact
  display conversion at build time. Keep numeric presentation values typed and
  identifiers textual. Preserve NULL/missing/sentinel and non-finite display meaning.
- Persist source-row identities and duplicates. Preserve canonical ordering and
  paging semantics; do not use new row IDs as invented business tie-breaks. Do not
  collapse count, grid or export multiplicity merely because they share keys.
- Prepare Availability for the default view and reusable daily
  summaries needed for existing range/horizon requests. Reuse the existing mapper
  equivalence findings. A range-dependent value may require bounded arithmetic;
  it must not require rescanning90 daily cells or rebuilding each row per request.
  Do not materialize every possible horizon/date-range combination.
  Account for the actual server date subset and frontend horizon semantics.
- Use the existing source/run binding and complete-build visibility mechanism where
  practical. Store this snapshot separately from prior join references so selecting
  it is explicit and the previous deployment remains recoverable. No new framework.
- Build the retained heavy snapshot once after focused local checks. A rebuild
  requires a specific data/implementation correction; it is not a benchmark repeat.
  Record source identity, branch populations, build duration and added storage once.
  Use real Django migrations and the repository-required schema checks.

## 3. Serve it through the existing API and frontend

- Live permissions remain authoritative. Apply scopes, requested filters, canonical
  order and paging against the prepared rows/attributes. No source-table rejoining,
  generic full-row conversion or Python presentation reconstruction for supported
  trial grid requests. Preserve related selected-run/date consistency.
- Return the prepared value types and Availability through the existing BTR-only
  prepared-response contract. The frontend passes rows to AG Grid, retaining the
  mounted-grid, stable-column, request-race and layout improvements already made.
  Formatting visible cells and interactions stay in the frontend.
- Keep existing count and export contracts correct. Reuse snapshot data only where
  their distinct semantics permit. Combining HTTP count/grid responses, changing
  export design, hidden-grid removal, compression and layout caching are not
  prerequisites and must not expand this trial. No broad raw API change.
- Do not hide a slow accepted-reader fallback as snapshot proof. Report any
  unsupported case precisely; support the required both-branch trial controls.

## 4. Focused verification and delivery

- Compare complete prepared results to the retained accepted outputs/JS display
  mapper for both branches at the full5000-row page size, default90-day and one
  supported shorter/date-range case. Include one later page, restricted and empty
  scope, and affected filters. Preserve duplicates, values, types and ordering;
  retain only already-approved exceptions. Reuse prior adversarial proofs and
  extend them only for semantics changed by this implementation.
- Verify permissions cannot expand and the selected snapshot/date is actually used.
  Verify count and one bounded export case for the affected path; no giant repeated
  export suite. Run required migrations/checks and focused affected tests/build.
- Deploy to existing3005 after correctness passes. Leave legacy available. Capture
  a brief before/after UI comparison under the same ordinary resource settings,
  dataset, scope, horizon and5000-row page size for On-Hand, Pipeline and Both.
  Use exactly one before and one after observation for each view, reusing any
  equivalent retained before observation. Report action-to-usable-grid time and
  request count. Do not rebuild/redeploy the old stack just to obtain missing
  before timings; disclose a missing baseline. This is diagnostic
  evidence, not a p95 certification. No concurrency/cold/resource benchmark matrix.
- Deliver the existing BTR URL, selected date/snapshot, concise changes and remaining
  delay, migration and rollback instructions. Update MIGRATION.md, commit and push
  the new branch at the completed trial checkpoint, then stop for user review.

## Completion

The full heavy-dataset UI uses stored presentation rows. Source joins, generic
conversion and daily-value scans execute during the one-time build rather than
repeating for grid requests. Supported permissions/filters/paging and displayed
results remain equivalent.3005 is usable for firsthand inspection and the brief
comparison shows whether the screen improved. A failed or unproved speed result
is reported honestly; it does not trigger another benchmark programme.

Stop after this delivery. Do not pursue an arbitrary speed target, zero compute,
zero requests, whole-application acceptance or a further optimization tranche.
Permission checks, filters, ordering, paging, small range-summary arithmetic,
serialization, transfer and visible-cell formatting/rendering are legitimate
remaining request/display work. They are not unfinished scope by themselves.

If a concrete contract prevents direct prepared reads, report the exact affected
case and smallest proposed correction. Do not silently widen the task. Future
daily refresh integration is explicitly deferred.

## Authorized typed-reader follow-up

Remove only the prepared-grid SQL JSON intermediate and per-row JSON decoding.
Read typed columns and map the existing response directly; preserve two-pass
paging, ordering, permissions, values/types and sparse nonfinite descriptors.
Keep narrow page selection ahead of wide projection where the planner permits.
Freeze current both-branch5000 and small scoped/range outputs before editing;
compare every row/field, run affected tests/check/backend build, inspect one plan,
and observe one completed On-Hand5000-row modern UI response and usable grid.
Deploy only the backend, retain its previous image and current generation for
rollback, update the existing handoff, commit/push and stop. No schema/data/index,
frontend, count/export, legacy-service or resource changes; no benchmark expansion.
