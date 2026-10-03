# Stage 2 shared dataset handoff — source blocked

3 October 2026. This is an operational handoff, not a second status tracker.
Current status is maintained only in `docs/MIGRATION.md`.

## Result

Dataset readiness is **not established**. The human's corrected source is
`F:/VFlow_Source_Backup`. Matching local Demo database names was insufficient:
the local 1,240-row population is explicitly documented as synthetic. It cannot
be silently used as the preserved original population.

The preserved deployed API configuration names `Demo_Importer_1`, `Demo_BPR_1`,
`Demo_DBM_1`, `Demo_BTR_1`. Its preserved engine Settings.bat names unsuffixed
`Demo_Importer`, `Demo_BPR`, `Demo_DBM`, `Demo_BTR`, `Demo_Interface`,
`Demo_IntermediateDB`, `Demo_Vendor`, `Demo_Distributor`, plus separate Demo_Users.
The suffix relationship and populated snapshot must be reconciled from original
data evidence; neither configuration alone supplies that data. Demo_Users and
all authentication data remain outside the dataset load.

The bounded inventory found no SQL `.bak`, `.bacpac`, `.mdf`, `.ndf`, or `.ldf`
population under the preserved root. The `.bak` candidates are Celery scheduler
state. Listings of `27092026/MTA - Copy.7z`, `deployed-demo/MTA/V6.zip` and
`deployed-demo/MTA/BackEndAPI/Gulfoil QA.zip` contain no database backups.
Report CSV/ZIP files and application/schema sources exist; they do not establish
the complete eight-database population, histories or relationships. This is a
bounded finding, not a claim about archives elsewhere.

Evidence: preserved reconstruction runbook line 307 states databases were not
copied. `F:/VFlow_Local/LOCAL_STACK_RUNBOOK.md` lines 54–56 explicitly identify
the local Demo closure as synthetic and distinguish it from former feeds. No
excluded `F:/new_vflow` source was accessed; its name occurs only in that lineage
documentation.

## Preserved candidate and proof

External evidence root:
`D:/freshvcf-build/evidence/stage2-shared-dataset-20261003-001`.

| Artifact | What it establishes |
|---|---|
| `source-reconciliation.json` | Corrected authority, configuration hashes, bounded archive inventory and rejection of candidate lineage. |
| `dataset-manifest.json` | Eight local backup hashes, SQL backup headers, table/column types, counts, date ranges, extraction ordinals and portable-file/value hashes. Not original-source acceptance. |
| `tables/` | Gzip JSONL exports retaining typed decimal/date representations, NULLs, empty strings and duplicate rows. Source columns and SQL types live in the manifest. |
| `staging-validation.json` | Complete ordered row hashes and column NULL counts for 523 staging tables / 280,651 rows, verified after PostgreSQL COPY. Not count-only proof. |
| `mapping.json` | Explicit source→existing typed target columns for 102 operational images and six report projection families; image counts/digests and projection readback digests. One absent source binding: `closing/orders/OrderIdentity`. |
| `permission-compatibility.json` | All 200 SKU and 20 location native hierarchies are LOCAL_ALL triples; zero matches against unchanged modern catalogue. |
| `source-checks.json` | 1,240 BPR/rationed rows have no positive GIT; Importer InTransitData is empty. No supplement approval transfer or positive-logistics claim. |

All eight backups passed SHA256/size checks and SQL RESTORE VERIFYONLY WITH
CHECKSUM. Backup times span 11:17:02–11:17:04 on 3 October as recorded by SQL
Server. Four main LastBatchRun dates agree on 8 October 2025. This is bounded
date consistency, not proof of a coordinated original application snapshot.

`EnvironmentConfiguration` (47 rows) remains only in the retained original
backup, because it can contain runtime credentials and is not a Stage 2 report
input. No credentials or data dumps are committed to Git. Datetime2 staging is
text with its original SQL type/scale declared, preserving SQL's seventh
fractional digit. Extraction ordinal preserves this frozen export's ordering;
it does not invent a source business sort or claim heap order is contractual.

## Coverage of the rejected candidate

Reuse `docs/audit-2026-10-01/PAGE_INTERACTION_INVENTORY.csv`; its hash is recorded
in the dataset manifest. No new page implementation or browser QA was started.

| Existing family | Data present | Limitation |
|---|---|---|
| RRR | Rationed/BPR rows; 755 Pick rows; direct PickBand/PickPost copies | Authenticated scope has zero members; no serving proof. |
| DBM/current/daily history | 1,240 master rows, suspension data and reference tables | Current Suggestions, SuggestionsLog and DailyConsumption empty; no positive recommendation/history scenario. |
| BTR / Buffer Trends | 1,240 wide trend rows and D1–D90 date columns | Wide snapshots do not prove deep daily fact history. |
| Planning | Existing Excess, fulfilment and expedite report populations | No source OrderIdentity; no new workflows; all scope reads blocked. |
| BPR | 1,240 BPR rows and retained configuration | No authenticated read proof; candidate provenance rejected. |
| Guided | 413 Chronic rows; availability/DBM trend inputs; 55 Excess rows | BTR BPR has only one ReportDate; no multi-day history coverage. |
| Research | Existing BTR snapshots/attributes | No page/API readiness proof; RationingHistory empty. |

Every family is blocked for accepted fixture use by source lineage and permission
membership. Relationships, representative authenticated APIs, fixture admission,
loader retry/failure injection and complete consumer coverage remain unproved.
Empty scenarios are preserved, never replaced with fabricated positive data.

## Resources and operation

- Read-only SQL clones: `VFTEST_Fresh_S2_20261003_001_` followed by Importer,
  BPR, DBM, BTR, Interface, IntermediateDB, Vendor or Distributor. Owned files:
  `D:/freshvcf-build/sqlserver/stage2-shared-dataset-20261003-001`.
- PostgreSQL: `test_freshvcf_stage2_dataset_20261003_001` in the existing owned
  `freshvcf-test-postgres-1`; no host port was added. Source schemas are
  `stage_demo_<role>_1`; modern tables use the repository's mta/mta_state schemas.
- Partition ID `f9db3dfc-efc3-488d-af2f-a88e8b2c68ee` has kind
  `LEGACY_UI_FIXTURE`, status `FIXTURE_BLOCKED`, empty parity/output acceptance,
  no production manifest, predecessor, checkpoints or commands. It is not
  selectable by normal production admission. Projection rows were copied
  directly; no modern-producer receipts were fabricated.
- One-off workers used restart=no, 4 GiB memory/swap and 2 CPUs on the private
  test network. The consumer load committed before the stop took effect; its
  final successful output was collected. No worker remains running.
- Existing Django migrations were applied normally to the owned database.
  Django check, makemigrations --check and migration plan passed. No model/schema
  changes were made. F1/F2 data and all serving containers were untouched.

The retained tools are `tools/stage2_dataset.py` (backup assessment/export),
`tools/stage2_dataset_load.py` (bulk typed staging COPY/readback), and
`tools/stage2_consumer_load.py` (bounded source-to-consumer copy/readback).
They now fail immediately with SOURCE HOLD. Do not remove that guard merely to
retry this candidate. Code is retained as work-in-progress for a reconciled source;
repeatable readiness and serving are not claimed.

No dataset-selection switch was made, so there is no serving restoration step.
Do not delete/reset these resources or repopulate 3005. Resume only after original
populated backups are supplied/located with lineage and API/engine bindings, or
the human explicitly revises source scope. Create separately owned replacement
resources, recheck mappings and permissions without changing permission grants,
then implement the minimal explicit fixture-admission boundary and consolidated
API/coverage validation. Stages 3–5 and page-by-page frontend work remain excluded.
