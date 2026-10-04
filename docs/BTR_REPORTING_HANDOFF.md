# BTR reporting trial — operational handoff

This is the bounded BTR reporting-layer experiment. Acceptance status lives only
in [MIGRATION.md](MIGRATION.md). The trial uses existing textual product/location
keys and source ordinals; it does not change calculations, engine state, grants,
other reports, or default raw API/export contracts. The authorized BTR frontend
uses the bounded display opt-in described below. Integer business dimensions are deferred.

## Schema and lineage

`BtrReportingGeneration` binds source kind, selected run/date, input/output/production
digests, version and each image's role/path/table/count/digest. Its JSON fields hold
bounded provenance and validation summaries, not report rows. `BtrJoinReference`
stores raw and normalized textual SKU/location keys and nullable source ordinals
for the numeric trend, colour trend, requirement, pair/product/location attributes
and standard attributes. It does not copy the90 daily measures or colours.

There are separate inventory/dispatch and grid-count/export reference bags. Grid
and count include SLA; export omits it. Requirement projection differences, the
conditional parent-location join, filters, permission membership multiplicity,
descriptions, category labels and daily-column serialization retain the accepted
reader contract. Selection and final rejoin retain both limits and normalized-key
ordering. No source ordinal is an added ordering criterion.

The fast path is conservatively eligible only with unique normalized source keys,
including descriptions and category alias identities, and singleton effective
permission memberships. Ambiguity uses the accepted query through the same API;
it is not excluded from comparison. Server logs explicitly identify `reporting`
or `accepted-fallback`, selected generation, count and export.

Migrations in app `fresh_mta`:

| Migration | Purpose | Dependency / operation |
|---|---|---|
|0013_btr_reporting_references|Typed generations/references and key index|0012; generated model operations|
|0014_btr_reporting_immutability|Completed-attempt and reference mutation guards|0013; reversible PostgreSQL RunSQL|
|0015_btr_reporting_truncate_guard|Preserve generation/reference history against truncation|0014; reversible PostgreSQL RunSQL|

All are required on fresh databases and upgrades. No migration is faked. The
fixture freezes Django metadata as well as source rows, so use the narrowly
bounded command below there. It unlocks only the migration registry and content
types inside one transaction and restores both guards before commit, requiring
identical fixture admission/freeze identity. Ordinary publications use `migrate`.

## Build, activation and rollback

There is no production daily scheduler in this checkout. `run_temporal` is a
retained validation command; do not run it to refresh reports. After a daily run
has committed and passed its existing acceptance/admission, configure its exact
published run/digest and existing hierarchy/permission inputs, then run:

```powershell
# In the configured MTA environment; choose a new evidence filename each time.
python manage.py migrate --noinput
python manage.py build_btr_reporting --evidence /owned-evidence/btr-build-YYYYMMDD.json
```

For the immutable fixture, replace the migration command with:

```powershell
python manage.py migrate_btr_fixture
```

The builder acquires a source-bound advisory lock and records a BUILDING attempt.
All reference rows and the READY transition commit atomically in a repeatable-read
transaction. Failure rolls back rows and retains a FAILED attempt. After a worker
interruption, obtaining the released lock permits marking only its incomplete
attempt failed and retrying. A matching complete generation is fully verified and
reused. The builder never selects a generation, changes a run, or marks an engine
calculation failed. There is no automatic deletion or retention cleanup.

Set `VF_BTR_REPORTING_GENERATION` to the exact READY UUID alongside the already
selected source run/digest. Startup verifies the source binding and complete
reference checksum. Missing/wrong/incomplete generations fail closed. There is
no latest-run fallback. The previous generation remains available for explicit
selection; it is never labelled as a new day's data.

Activation uses a non-overlapping stop/start of the existing MTA service, followed
by startup admission/readiness and a browser reload. Do not rolling-reload old and
new source dates: the existing frontend has no cross-request generation token.
Daily date switching across concurrent user sessions remains this controlled
maintenance boundary. Live gateway identity/grants, request filters and user export
layout remain read-time inputs; none are snapshotted as entitlements.

For the current local fixture trial, from `F:/freshvcf`:

```powershell
docker stop --timeout 60 freshvcf-preview-mta-1
docker compose --env-file D:/freshvcf-build/preview/preview.env `
  -f compose.preview.yaml `
  -f D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002/compose.fixture.json `
  -f D:/freshvcf-build/evidence/btr-reporting-20261004-001/compose.reporting.json `
  up -d --no-deps --no-build mta
docker logs --tail 15 freshvcf-preview-mta-1
```

Rollback uses the same stop/start with the last override replaced by
`D:/freshvcf-build/evidence/3005-report-contention-20261004-001/compose.candidate.json`.
That override pins the accepted image
`sha256:761719e96c0f95ccdb5f0ad79f7e96125b172ab79fafac72e3a3790615bc952a`.
Do not include the reporting override in rollback. Additive reporting tables remain
inert; do not reverse migrations or delete evidence as part of service rollback.

## Current source and inspection

Fixture run `bfd75b4b-a9df-4a08-82d3-852e3324b623`, April7 2026, database
`test_freshvcf_stage2_vm_20261003_002`, generation
`3242710a-7478-4668-b9ed-b7af543e4f84`. Its389196 references comprise97299 in each
branch/purpose. Source digest:
`9177a8ef26fc6f727098ec8161361537a490936e1a39054a309dff69e21cc076`.
Reference digest:
`0030262c2b9fe36f08cf97ea72c34d21a26a5d7e232f39b75d5deba392764787`.
Initial build74.5s; relation plus indexes115499008 bytes (about110MiB).
Isolated peak memory was not captured for that build. It completed under the
then-configured4GiB MTA and1GiB PostgreSQL ceilings, but those ceilings are not a
peak-memory measurement. No fixture rebuild is authorized merely to fill that gap.
The actual daily refresh window is not configured in this checkout; no daily SLA
is claimed from this one-time fixture build.

Normal retained publication `ac1612c8-0e49-4155-83c3-f59f41422293`, June17 2026,
generation `bb0b0859-431d-426b-a71b-9629692c8357`, has4960 references. It supplies
functional compatibility proof, not the scale benchmark.

- Modern: [BTR on3005](http://localhost:3005/mta/insights-and-trends/buffer-trend-report).
  Use `stage2.broad@vectorflow.local` and the existing local credential from
  `D:/freshvcf-build/preview/secrets/stage2-fixture-accounts.json`.
  `fresh.preview@vectorflow.local` is intentionally not granted fixture access.
- Legacy: [BTR on3002](http://localhost:3002/mta/insights-and-trends/buffer-trend-report).
  Use the existing3002 login in `F:/VFlow_Local/LOCAL_STACK_RUNBOOK.md`.
- Compare April7, Show All, all90 days, page1,5000 rows, then each On-Hand/Pipeline
  branch. Both counts must be97299 under equivalent broad scopes. Record the actual
  actor and scope; matching counts alone do not establish permission equivalence.
- Use separate browser profiles if localhost cookies interfere between the two
  independent authentication services. Do not change cookies, grants or credentials
  to bypass an access decision.

The evidence root is `D:/freshvcf-build/evidence/btr-reporting-20261004-001`.
Complete response proofs, migration receipts, failed attempts and benchmark bodies
are retained there. Preliminary one-shot timings are not performance acceptance.

## Recorded measurement boundaries

The completed c1 series in `matched-reporting-002/summary-c1.json` contains five
warmups followed by30 alternating measured grid/count journeys per engine. Both
database ceilings were4GiB/2CPU; application ceilings were4GiB/2CPU. SQL's internal
buffer allocation was2560MiB, leaving1536MiB within its total ceiling for other
allocations. The same client requested both branches,5000 rows per branch, all90
days, page1, broad scope, April7. Every complete response passed the retained
comparison, including only the previously approved Category alias-order exception.

| Native API, c1 | Median journey | p95 journey | Journeys/s |
|---|---:|---:|---:|
| Legacy, matched4GiB window |14.035s|21.302s|0.06470|
| Reporting Fresh, same window |10.449s|19.948s|0.08744|

These are shared-host observations with variable competing activity, not reserved
hardware. They exclude authentication, gateway, browser parsing/transformation and
grid rendering. Reporting grid responses contain37703760 decoded bytes for both
branches; legacy responses contain33723563 bytes. Exact values/types are compared
after decoding, so differing wire serialization lengths are retained rather than
treated as a semantic mismatch. No compression/transfer saving is claimed here.

The earlier accepted-Fresh c1 measurement used a3GiB database ceiling; it is not a
same-budget baseline for this4GiB experiment. The first reporting3GiB window failed
on legacy SQL pool memory before valid samples. Its complete failure evidence and
successful resource restoration remain in `matched-reporting-001` and
`budget-reporting-001`. Later gates and the delivery decision are in MIGRATION.md.
Under the human's benchmark scope limit, a second full accepted-Fresh matrix is
deferred. The unmatched accepted-Fresh comparison stays UNPROVED. Reuse passing
correctness proofs and complete only the finite runtime/browser checks recorded
in MIGRATION.md.

The human stopped c4 at completed pair22. Eighteen measured batches/72 journeys
per stack passed complete comparisons: legacy median50.239s/p9564.359s; reporting
Fresh20.879s/32.569s. This is partial evidence, not the full protocol. The owned
runner ended intentionally before pair23 and its resource helper restored the
original limits without errors. PostgreSQL is back at1GiB/1CPU; SQL's previous
memory settings were independently checked. See `human-stop-result.json`.
Cold/three-burst/extra baseline/attribution campaigns are deferred by the human.

## BTR display opt-in

Only grid callers sending JSON `displayPrepared: true` and integer
`displayHorizon: 1..90` receive display-ready rows. The response data includes
`displayPrepared: true` and `displayNonFinite`, a sparse list of
`[branch, rowIndex, field, "NaN"|"Infinity"|"-Infinity"]`. A listed cell is `null`
on the JSON wire; the BTR adapter restores its precise JS non-finite value.
Without the explicit marker, grid output remains raw. Counts and CSV export keep
their existing contracts. The seven protected identifier/description fields stay
strings. Numeric-prefix conversion, selected daily subset, missing/empty days,
sentinels and two-decimal Availability follow the retained `mapBTRRowData`.

This is request-time preparation after the existing permission/filter/page read,
not a new calculated-state projection. The daily join-reference generation is
unchanged. Browser full-row conversion/copy and Availability scanning are removed
on this path; their cost moves to Python and is not claimed as eliminated overall.
The frontend retains the old mapper fallback for rollback to an older server.
Both non-finite descriptors and every field/row position are checked against the
actual JS mapper. Evidence: `display-unit-tests.txt` (all90 adversarial horizons)
and `display-fixture-proof.json` (5000 rows per branch at90 and7 days).

Same-view grids remain mounted while an inert loading overlay blocks actions.
Branch/count request versions prevent superseded responses or failures from
publishing rows or clearing newer loading states. Column definitions and config
are reused within the mounted actor/publication, while saved layout is loaded on
tab entry. Layout restore follows grid/column/state readiness, with defaults
captured before applying saved state; fixed two-second restore timers are removed.
Split views copy column definitions before adapting them. Publication changes
invalidate in-flight results/config and refresh only an already-applied report.

The deployment/browser status and final image/rollback identities remain in the
active tracker until the production build and live proof are completed.
