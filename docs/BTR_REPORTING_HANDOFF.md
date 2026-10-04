# BTR reporting trial — operational handoff

## Typed-reader follow-up — 4 October 2026

The prepared grid reader now selects flat typed columns and constructs the
response dictionary directly. SQL JSONB construction/concatenation and per-row
JSON decoding are removed. Both canonical paging passes remain; the ordered
bounded page drives a lateral typed-row lookup. No schema/index/data refresh or
frontend change is required. Counts/exports remain on their existing reader.

Evidence root: `D:/freshvcf-build/evidence/btr-typed-reader-20261004-001`.
`before-*.json.gz` freeze the prior deployed reader; `after-*.json.gz` and
`after-receipt.json` prove complete ordered responses for5000 rows per branch
and20 per branch under restricted permissions and a seven-day range. JSON
numbers compare numerically (JavaScript's single Number type); strings, NULLs,
field presence, arrays/row order and sparse descriptors compare strictly.
Seven affected tests and Django check passed; backend build succeeded.
One retained EXPLAIN (`plan.json`) took773.097ms for On-Hand5000. Its top node is
a nested loop after page selection, with no final wide sort; a narrow internal
sort remains. These single observations do not certify p95 or legacy speedup.

UI: On-Hand, Show All, page1,90 days, page size5000 rendered and scrolled. Retained
`ui-grid.jpg` and `ui-observation.json` record the observation. One observed grid
completion was5.132s, including tool round trips; an earlier observation was6.967s.
The response-body proof remains open: browser tooling has no response inspection,
and external read-only packet reconstruction failed. Retries were confined to
this verification defect; no extra benchmark matrix was run. Do not represent
the grid footer as independent proof of the actual response's prepared flag or
5000-row population. Direct-reader complete response equality is proved above.
Observer processes were stopped; no diagnostic service or permission change was
left behind. Complete one supported network-body/UI observation to close this
remaining proof, rather than changing the reader again without a measured defect.

Backend image: `sha256:31f08919bd25dfd6f62561ea46fd74d2f7ad935df2749804fa9f57944e901c90`.
Use the base preview compose, existing fixture overlay, then this evidence root's
`compose.typed.json`. Recreate **mta only**, with `up -d --no-deps --no-build mta`.
Rollback uses the same command with `compose.rollback.json`, restoring backend
`8b218cd3cc5a…` and the same version2 generation `e5bdac30-bbd9-45d8-a93d-84a645fad73c`.
Wait for `/readyz` after the unchanged startup integrity check. Do not use the
older trial rollback below for this reader-only reversal. Frontend image/container,
snapshot digest, memory/CPU limits, permissions and other services are preserved.

## Current ready-snapshot trial — 4 October 2026

Open `http://localhost:3005/mta/insights-and-trends/buffer-trend-report` with the
existing `stage2.broad@vectorflow.local` fixture account (credentials remain in
`D:/freshvcf-build/preview/secrets/stage2-fixture-accounts.json`). The normal
`fresh.preview@vectorflow.local` actor remains denied this fixture; no grant changed.

The unchanged April7 fixture/run is `stage2-vm-dataset-20261003-002` /
`bfd75b4b-a9df-4a08-82d3-852e3324b623`. Selected snapshot:
`e5bdac30-bbd9-45d8-a93d-84a645fad73c` (generation version2),97299 rows per branch.
The generation's source digest is
`5517272bbb84f80e95b1bc3db45dac4b2f08a161edaf337467cafa2b6b037b57`;
typed-row digest is
`ee0bcf8aad5b98636db5051f132782667d6cab1417633f30538b66c918fec60d`.
It was built once in1213.73 seconds. Rows/indexes add461586432 bytes (440.2MiB).
No engine, source facts, F1/F2 state, grants, other services or new date were changed.

Migrations0016/0017 add `BtrPresentationRow`, immutable-generation guards and
covering indexes for live scope expansion. Display cells use typed number/text
alternatives; source filter values retain SQL NULL/types separately. Stored source
ordinals preserve occurrences; normalized SKU/location keys preserve canonical
two-pass paging without a new business tie-break. Build time performs the retained
joins and JS-compatible display mapping, including cumulative available/empty-day
summaries. Default Availability is stored; ranges use two prefix differences.
Grid requests read this table directly and the existing prepared-response frontend
uses those values. Entitlements remain live. Counts, raw clients and exports retain
the pinned version1 reference generation; startup verifies both generations.

Repeatable preparation, in the configured existing fixture MTA environment:

```text
python manage.py migrate_btr_fixture
python manage.py build_btr_snapshot --evidence /owned-evidence/new-build-receipt.json
```

Do not rerun preparation merely for another timing: the matching READY generation
is reused after verification. A new build commits rows/READY atomically; interrupted
BUILDING attempts remain attributable. Serial VACUUM of this derived table completes
visibility for the covering indexes, within existing resources. No scheduler,
ingestion, automatic activation or general production refresh is implemented.

Evidence and exact compose overrides:
`D:/freshvcf-build/evidence/btr-ready-snapshot-20261004-001`.
Current backend image is
`sha256:8b218cd3cc5adfb94b6b70772d622f0eadf0756ba5db3041916bbd8e25fe71b2`.
The unchanged frontend is
`sha256:f88d22416ab5b5b50a30479c1684449eb020dd29d8feb1bdd7399c2d02df0e91`.
Admission is `5c90ae58f6478f7b1805f534f95fbe0de241a5280c4422ec70f28467221bf3e7`.
Only the authorized MTA/frontend pair was recreated; protected containers/resources
were unchanged (`deploy-verified.json`). The deployment wrapper initially expected
an extra readiness field; `check-result.json` verifies the actual digest-only
readiness contract without another restart.

To restore the previous image pair and generation, from this checkout:

```powershell
D:/freshvcf-build/venv/Scripts/python.exe `
  D:/freshvcf-build/evidence/btr-ready-snapshot-20261004-001/deploy.py rollback
```

This uses `compose.rollback.json`, backend image `a7c58a5097357be81b44a710fdc6c9588b50a810facc99029e1365887a8c91f2`
and generation `3242710a-7478-4668-b9ed-b7af543e4f84`. It stops/starts only the same
preview pair and verifies the prior admission. Leave additive schema/data intact;
rollback requires no reverse migration, deletion or source reload. The snapshot can
be selected again using `compose.snapshot.json`; keep selection explicit.

Focused proof is in `proof-result.json`, with retained complete response bodies:
both full5000 first/later pages, full5000 shorter range, scoped/empty/filter/error
contracts, broad counts and one100-row export. Seven focused local tests passed;
PostgreSQL migration/check/drift/guard proofs passed. Existing JS-mapper and unchanged
frontend build/tests are reused. Gateway tests preserve restricted scope against
forged IDs and retain the normal actor's403. The first default read exposed wide
scope scans (67.92s);0017 corrected that access path without rebuilding the data.
An initial parallel VACUUM exceeded existing shared memory; serial maintenance
passed without increasing resources. These are retained failures, not green trials.

The single UI observation per view used broad scope,90 days,5000 rows and1280x720.
All three screenshots show populated grids/counts. Pipeline action-to-observed-ready
was14.53s. Exact On-Hand/Both elapsed times are UNPROVED because browser waits failed;
their later observations bound completion at32.47s/30.45s but are not latency results.
Retained equivalent before screenshots have no precise baseline timings/request
counts. Therefore no speedup or p95 acceptance is claimed. API request counts were
4/2/1 for On-Hand/Pipeline/Both respectively (one grid request each; count on the
first view). Grid bodies were16.65MB/16.65MB/33.31MB, with proxy temporary-file
buffering. Remaining queries, serialization, transfer and rendering still cause
visible delay. No compression, count consolidation, hidden-grid changes or further
benchmark/optimization campaign was opened. Stop here for human review; status is
owned by [MIGRATION.md](MIGRATION.md).

## Retained version1 reference design and historical deployment notes

The following explains the preserved predecessor. Its older deployment commands
are historical; use the exact current/rollback overrides above for this trial.

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
