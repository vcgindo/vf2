# Retained dataset presentation handoff

The scope is the read-only reporting batch in
[the reporting contract](PREPARED_PRESENTATION_ROLLOUT_PLAN.md).
[MIGRATION.md](MIGRATION.md) is the sole status tracker. This document records
implementation and operational evidence, not acceptance of all F3 workflows.

## BPR fixture preparation and serving

The bounded BPR correction uses the same April 7 run
`bfd75b4b-a9df-4a08-82d3-852e3324b623`. Evidence is in
`D:/freshvcf-build/evidence/bpr-ui-performance-20261004-001`.
Migrations 0019/0020 add one typed native candidate relation and an immutable
receipt. It retains all six source occurrence ordinals, raw filter/display
owners, nullable standard presence, unrounded numeric pens and normalized
lookup keys. Permissions, filters, parent multiplicity, key-bag paging,
latest remark ties and trend availability remain live. Count and analytics
retain their separate grains. Calculation state and the export reader are unchanged.

With the existing base, fixture and portfolio Compose files, append
`compose.bpr.json` from this evidence directory. Run `python manage.py
migrate_btr_fixture --bpr-preparation`, then `python manage.py prepare_bpr_fixture`.
Both are bounded to the owned fixture. Preparation is atomic and refuses partial
or mismatched existing rows. Repetition verifies the complete typed digest;
`--verify-only` cannot insert. The retained preparation produced 97,097 occurrences
in 75.44 seconds including container startup, using 65,232,896 bytes including indexes
and receipt. The source binding is unchanged. INSERT after sealing, UPDATE,
DELETE and TRUNCATE are denied. No normal run or engine publication is prepared.

`VF_BPR_PREPARED=1` explicitly enables only fixture grid/count/analytics and the
retained AdminBPR configuration. The latter restores all 29 canonical column
definitions instead of the older 19-column static UI projection; ordered values,
types and NULL omissions match the authenticated canonical API. Normal-publication
configuration and export behavior remain unchanged. Missing source/schema/receipt,
altered guards and unsupported hierarchy opt-in fail closed. Query-local JIT-off
avoids measured compilation overhead and restores the caller's setting on both
success and failure. It is not a PostgreSQL-wide setting change.

Deploy only `mta` with `--no-deps --no-build`, then wait for startup admission and
`/readyz`. Roll back to the prior portfolio MTA image
`sha256:12568efc81d6b15af95e693b7c1f7f1667bff5d05154e0d0b230625060f0c027`
using the base/fixture/portfolio overlays without `compose.bpr.json`; the old
reader ignores this additive relation. Retain its rows and migrations on rollback.
Do not reset source data, accounts, F1/F2 or the unchanged BTR generation.

Future daily publication remains explicit debt: connect this finite preparation
to accepted daily outputs and prove refresh/retry/retention before enabling it
for normal publications. This one-time fixture loader is not a daily scheduler
or acceptance of that later producer integration. Current browser performance
status and the bounded three-pair result belong in MIGRATION.md.

## Implementation

The existing immutable April 7 fixture and BTR reporting generation are reused.
Research reads selected pairs and their existing relatives instead of rebuilding
the whole publication. Guided history uses scoped, date-bounded SQL over typed
history. Exact-key occurrence indexes replace repeated Python scans without
normalizing or deduplicating source rows. Current Excess reads select the date
before transferring history. Native remarks and populated custom Expedite now
use their retained source contracts. No calculations or accepted F1/F2 state change.

The frontend removes duplicate Guided request ownership and Buffer Trends array
processing. Research and Planning settle independent count/grid requests together.
Pagination, request bodies and source value transformations remain unchanged.

Migration 0018 adds `fresh_guided_history_date` on run/image/ReportDate with covering
history fields. It was applied with the existing atomic `migrate_btr_fixture
--guided-history-index` command, preserving fixture binding and metadata guards.
It adds 875732992 bytes. Django check, migration drift/plan and physical PostgreSQL
verification passed. No pending migrations remain on the retained fixture.

## Correctness evidence

External evidence directory:
`D:/freshvcf-build/evidence/prepared-portfolio-20261004-001`.

- Seven full-population Guided lookup comparisons preserve every field,
  occurrence and order (`lookup-comparison.json`).
- Twelve Research/historical/Guided/Excess comparisons cover broad/restricted
  scopes and nine-/three-day windows (`source-comparison-summary.json`).
- Current-date Excess matches 9871 rows from the prior full-history read;
  populated custom Expedite matches 1030 canonical-query rows.
- Three PostgreSQL SQL differential tests and 52 focused backend tests pass.
  The existing unrelated two Expedite fixture-mock failures remain documented;
  this is not a claim that the historical entire suite passes.
- TypeScript, four request-pair tests, production backend/frontend builds and
  pinned baseline identity verification pass.

The single post-index plan replaces the 30.8-second history scan with a 176.7ms
index-only scan per worker and zero heap fetches. The whole query still takes
14.277 seconds because joins/sorts remain. This is not click-to-usable-screen
performance acceptance or a claim of legacy performance parity. Further history
optimization is outside this batch's approved correction.

## Explicit upstream dependencies

Planning overview/GIT cannot be represented as an empty result: the fixture has
2567 positive-GIT rows but lacks GoodsInTransitMaster. Dependent Expedite parent
grid/chart paths lack BPRMaster. Those consumers must retain attributable 503
responses. Available Excess, Fulfillment and custom Expedite are assessed
independently. No source reconstruction or new workflow is implied.

## Deployment and rollback

The deployment uses existing `compose.preview.yaml`, the retained
`stage2-vm-dataset-20261003-002/compose.fixture.json`, and this evidence directory's
`compose.portfolio.json`. Only mta and frontend are recreated with `--no-deps
--no-build`; authentication, MTO, PostgreSQL and other serving stacks stay intact.
Wait for `/readyz` before route checks: immutable BTR startup validation precedes
the listener and is not instantaneous.

Rollback uses the prior `btr-typed-reader-20261004-001/compose.typed.json` overlay
with the same base/fixture files. The additional index is compatible with that
reader and need not be removed to roll back application code. Never reset data,
weaken admission, change accounts or reverse accepted F1/F2 state for rollback.

Authenticated runtime and browser results are recorded at the bounded inspection
exit in MIGRATION.md and the external evidence directory.

Deployment receipt: backend image
`12568efc81d6b15af95e693b7c1f7f1667bff5d05154e0d0b230625060f0c027`,
frontend image
`37643d580475db6fac763bad2c9a091afbfebc52cd62f17d66a3e912ff5fbb7f`.
Startup admission remains
`5c90ae58f6478f7b1805f534f95fbe0de241a5280c4422ec70f28467221bf3e7`.
All 21 protected running container identities are unchanged; mta remains 4 GiB,
2 CPU, restart=no, without host ports. Frontend remains loopback 3005 only.

`gateway-deployed/summary.json` records 23 expected statuses, with full compressed
response bodies: 20 successful reads including a restricted trend, two attributed
503 dependencies, and one unauthenticated 401. Two additional Planning graph
responses also completed 200. The preliminary `gateway-before-ready` failures
were sent before the startup listener existed and are retained as failed
orchestration, not included as successful application evidence.

Observed broad Guided trend/age requests took 15.06/23.19 seconds, and other
Guided requests also remain slow. These single observations overlapped bounded
browser inspection and are not controlled performance measurements. This batch
does not establish minimum latency or superiority to legacy.

Research renders 5000 of 97097 rows and selected history summaries. Its inherited
calendar initially opens the system month (October) while the fixture is April;
the existing DayPicker has no publication-month binding. Treat that display issue
as an explicit residual, not data loss or a reason to modify retained dates.

The bounded browser pass verifies Research selection/history, Guided trend and
Chronic tab transition, Buffer Trends Show All/30-day seven-series chart,
Planning Excess chart-to-grid with 5000 of 9871 rows, BTR 5000 of 97299,
RRR 5000 of 8063 and DBM 5000 of 11158. Screenshots and DOM receipts are retained.
Fulfillment/custom Expedite and remarks have complete authenticated API/source
proof; their every browser interaction was not independently exercised. Existing
export proofs are reused because their producers/contracts did not change; no
fresh export or write-workflow acceptance is claimed.

BPR also rendered its configured50-row page of97097. Desktop visibility was
verified at1280x720 (`browser-bpr-desktop.png`), then the temporary viewport was
reset. The other retained screenshots use the default narrow browser viewport;
DOM receipts establish their loaded data, not responsive-layout acceptance.
