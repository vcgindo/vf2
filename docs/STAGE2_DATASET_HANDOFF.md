# Stage 2 shared VM dataset handoff

3 October 2026. Operational reference; `docs/MIGRATION.md` is the sole status tracker.

## Identity and source

Current dataset: `stage2-vm-dataset-20261003-002`. Source preservation, staging,
consumer mapping and the explicit fixture boundary are complete. **Four-page
availability remains blocked.** The subsequent bounded correction made RRR and
BPR browser-visible; BTR's concurrent browser count/grid requests still exceed
the unchanged60-second gateway limit. NormalJune17 serving has been restored.
The original `dataset-validation.json` and windows001–004 remain historical
evidence, not a new readiness claim. The follow-up is consolidated in
`visible-availability-validation.json` and windows005–007 under the same root.

Evidence root: `D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002`.
Manifest SHA256: `afe42593ca2abdf5e2395433ac70834723f4eac1dfa5a2982192c7688906b836`.
PostgreSQL database: `test_freshvcf_stage2_vm_20261003_002` in
`freshvcf-test-postgres-1`. Consumer partition:
`bfd75b4b-a9df-4a08-82d3-852e3324b623`, business date **7 April 2026**.

The human supplied original VM backups in `E:/vflow_backup_dump`, matching the
preserved deployed API's four `_1` database names. The eight configured historical
engine roles were assessed. Interface, IntermediateDB, Vendor and Distributor
are conditional dependencies, not automatic UI gates; none was borrowed from
synthetic sources. Authentication data/passwords/sessions were not imported.

| Source | Preserved tables / rows | Selected staging tables / rows |
|---|---:|---:|
| Importer | 136 / 4,244,445 | 17 / 541,651 |
| BPR | 78 / 12,019,317 | 18 / 1,526,483 |
| BTR | 22 / 12,473,563 | 22 / 12,473,563 |
| DBM | 67 / 62,907,798 | 16 / 41,958,344 |
| Total | 303 / 91,645,123 | 73 / 56,500,041 |

All four full backups passed header/filelist inspection, RESTORE VERIFYONLY and
actual restoration into exclusively owned, read-only
`VFTEST_Fresh_S2_VM_20261003_002_<role>` databases. They lack SQL backup checksums;
that fact is retained, not misreported as checksum verification. SHA256 pins,
SQL types, counts and source dates are in the manifest. LastBatchRun agrees on
7 April across all four sources; this is observed date consistency, not a claim
that independently captured backups were a single transactional snapshot.

The first three backups have frozen owned copies. DBM's original completed copy
is pinned by SHA256 `c0042264452f9bf73f4504e47d6257a67266701fa79a7d859f613990aa71e9ba`
and a read-only restored clone. The earlier interrupted DBM capture remains
preserved with its different hash; it was never used as source. See
`dbm-capture-reconciliation.json`.

The prior `stage2-shared-dataset-20261003-001` candidate and commit `f85ee2e`
remain quarantined evidence. Its local Demo population was synthetic. Its loaders
remain under SOURCE HOLD; use only the new VM tools. No old source rows were
mixed into this dataset.

## Transfer and coverage contracts

`dataset-manifest.json` plus `manifest-seal.json` own immutable input identity.
`mapping.json` records every source/target column, typed wire representation,
source-only columns, image/projection receipt and exported-table disposition.
`staging-validation.json` and `dataset-validation.json` consolidate proof.
Raw data and credentials stay outside Git.

The bounded loader streams compressed JSONL into typed PostgreSQL COPY staging.
Datetime2 uses declared text preservation where needed to retain SQL Server's
seventh fractional digit. Every export ordinal, value digest, NULL vector and
row count is checked; duplicates are retained. The extraction ordinal pins this
export's order, not an invented legacy business ordering. Every consumer copy
rechecks full source values against the sealed manifest, then checks every mapped
target value. It does not execute either engine or manufacture producer receipts.

The selected roster maps 60 consumer images and six projection families into the
existing modern schema:52,760,538 image rows and965,475 projection rows, all
fully read back. Ancillary/configuration/permission/rationing exports
without an admitted adapter remain explicitly staging-only. All other source
tables remain intact in backups/read-only clones. `DistributorList` and synthetic
`OrderIdentity` are not current presentation reads and are not fabricated.
Planning Expedite's `closing/bpr/BPRMaster` remains in the preserved original
backup/clone, outside this mapped roster; that ancillary-dependent path is not
claimed as fixture-ready.

Source observations:

- Importer/BPR: 2,189 SKUs, 235 locations and 97,097 current pairs. Their master
  key bags agree. BTR has 97,299 snapshot pairs and 202 native differences from
  BPR, retained without repair. Each checked population has its own attributes.
- DBM: 11,158 Suggestions, 1,962,935 SuggestionsLog rows and 31,040,788 daily
  consumption rows spanning 365 dates, 8 April 2025–7 April 2026.
- BTR BPR: 8,483,003 rows over 90 dates, 8 January–7 April 2026.
  RationingHistory: 2,882,051 rows, preserved separately in staging.
- Excess: 921,651 rows over 90 dates; Pick report: 8,063 rows with no missing
  required band values. Native BPR contains 2,567 positive-GIT rows, empty
  Importer InTransitData and five remarks. No June17 empty-data exception transfers.
- Native AdminBPR metadata has 81 columns; 39 differ from the retained static
  UI configuration. This is preserved evidence, not UI/configuration parity.

The existing page inventory CSV is reused and hash-pinned. Data coverage is not
whole-page acceptance. No page-by-page frontend implementation was commenced.

## Explicit fixture boundary

The run remains `LEGACY_UI_FIXTURE/FIXTURE_BLOCKED`, with empty output/production
acceptance, parity, checkpoints, commands, predecessor and completion fields.
The status intentionally prevents ordinary production admission even when the
separate fixture dataset is usable. `stage2_owner.consumer_publication` binds
finalized consumer receipts. Immutable-table triggers protect copied rows and
receipts; only actor-owned layout preferences remain writable.

`mta/presentation/fixture.py` requires a separately pinned fixture policy,
manifest, consumer roster, native catalogue and actor list. Production identity,
hierarchy/terminal/history supplements and actions must be unset/disabled.
Normal production admission and calculation services remain separate. Pair-based
daily-history reads use relational filtering; unbounded eager images exceeding
one million rows fail closed. Imported rows never imply engine success/parity.

The human's bounded grant was verified in command-centre chat
`01a100e2-7943-7102-9760-62d9e492ecd9`, turn
`01a100e3-6258-7bf1-a9d0-f191636ed24f`. Two dedicated local actors use existing
account mechanisms and native source IDs/values: `stage2.broad@vectorflow.local`
and `stage2.restricted@vectorflow.local`. The restricted scope is product4 /
location25; no existing actor, grant or authentication business contract changes.
Both remain disabled outside the controlled window.

Credentials are retained only in the local secret file
`D:/freshvcf-build/preview/secrets/stage2-fixture-accounts.json`. The user-facing
login address for an authorized fixture window is `http://localhost:3005/login`.
The accounts have only Stage2 read/navigation grants and their own layout state.
The broad actor sees only native catalogue memberships; NULL/unrepresented
hierarchies remain denied.

## Verified outcome and blocker

`dataset-validation.json` records `BLOCKED_CONSUMER_READINESS` and
`dataset_ready:false`. Window004 proved populated DBM count/grid/history reads,
11158 broad versus1036 restricted Suggestions, forged-body scope non-expansion,
Apply/Sleep403, and403 for the unchanged normal preview actor. Five explicitly
unavailable native ancillary/history readers returned503. No business action
transaction or engine was executed.

`RRRDataCount` returned504 after60seconds in windows003 and004. Its existing
full-population presentation query needs a separately bounded diagnosis and
correction before readiness can be asserted. RRR grid, BTR and fulfillment
checks after that failure were not executed. Do not interpret mapped data as
their API acceptance or commence frontend implementation from this receipt.

Every window restored the original June17 image/configuration/admission and
proved protected resources unchanged. Both dedicated actors are disabled;
`fixture-window-004/disabled-login-proof.json` proves real login denial.
The zero-insert retry and immutable guards on396 relations passed.37 focused
tests pass; the broader HTTP adapter suite has17 passes and the same two
pre-existing Expedite failures, recorded in `code-proof.json`.

Windows001–004 are retained. Fixture-only subject partitioning resolved the
initial DBM join timeout without changing its selector output; duplicate/NULL/
missing/accepted/weighted-predicate equivalence is tested. Three owned history
indexes resolved the history scan timeout, with frozen identity unchanged.
Neither correction changes either calculation engine or the gateway timeout.

## Repeatable operation

Use `D:/freshvcf-build/venv/Scripts/python.exe` locally. Source tools are fixed to
this dataset's owned resources; they never reset a database or overwrite an
unfinished source export. `stage2_vm_dataset.py reconcile` idempotently reconciles
the completed DBM capture; `seal` verifies immutable final identity. Capture/export
cannot mutate a sealed dataset.

The one-time database worker uses the existing private test network, no ports,
4GiB memory/swap, 2CPUs and restart=no. Mount this checkout at `/app:ro` and the
evidence root at `/dataset`. Supply isolated database settings outside Git.
Run, in order:

1. `python tools/stage2_vm_load.py` (or `--role DBM` for an explicitly recorded
   remaining role), then `python tools/stage2_vm_load.py --finalize`.
2. Apply existing Django migrations normally to the owned database; never fake.
3. `python tools/stage2_vm_consumer_load.py`.
4. `python tools/stage2_vm_consumer_load.py --verify-binding closing/dbm/LastBatchRunTbl`
   proves a bounded zero-insert retry without replacing the complete mapping.
5. `python -m tools.stage2_vm_freeze` after completed load proof.
   Run `python -m tools.stage2_fixture_indexes` for the three owned pair-history
   indexes required by the retained DailyDataGraph timeout evidence. It verifies
   exact index definitions and unchanged freeze identity; no row writes occur.
6. Prepare the native catalogue with `python -m tools.stage2_vm_permissions`,
   and create disabled fixture accounts with `python tools/stage2_fixture_accounts.py create`.
7. Build the separate `freshvcf-stage2-fixture:20261003` image. The normal image
   tag is retained. `python tools/stage2_fixture_window.py prepare` renders and
   verifies exact-image/environment/mount/network/resource restoration before
   any serving switch. With that pinned policy and native catalogue supplied as
   the worker's fixture settings, run `python -m tools.stage2_fixture_integrity`
   to prove immutable rows and rejection of mixed or mismatched selections.
8. `python tools/stage2_fixture_window.py prove --attempt <new-three-digit-id>` performs only the
   MTA switch, real encrypted-password/cookie login and bounded API checks, then
   disables accounts and restores normal MTA in `finally`. Each attempt uses a
   new evidence directory; failed receipts are preserved.
9. `python tools/stage2_vm_validate.py --window fixture-window-004` reproduces
   the delivered consolidated blocker and completed source/mapping/boundary/
   restoration proof. A later authorized correction must preserve these attempts
   and use its own new window; failed route assertions must not be waived.

During a later separately authorized UI window, reuse the prepared Compose
fixture override and account enable operation after the exact restoration
preflight. On exit run `stage2_fixture_window.py restore --attempt <recorded>`.
It disables the actors first, restores only MTA's original image/configuration,
then checks readiness/admission and protected resources. Existing frontend,
gateway/auth, MTO and all3002/3003/3004 services are not restarted. There is no
new public port, serving database reset or automatic cutover.

## Explicit limits

Research Insights and historical availability still call production-only whole
output; remark history and Planning GIT/overview/Expedite need native ancillary
adapters. Guided availability needs a bounded daily-history reader, and Guided
Excess retains its production history contract. These are honest API adapter
limits, not missing synthetic replacements or permission bypasses. Source data
is preserved for later authorized integration. This handoff does not certify
API value parity, whole-page behavior, performance parity or Stages3–5.

## Bounded four-page follow-up and current operation

The separately authorized availability follow-up stopped at window007's BTR
browser blocker. RRR showed8063 total records,5000 on its first page and11 after
a local SKU filter. BPR showed97097 total records,50 on its first page and one
after a local SKU filter. Representative SKU/location values were checked in
the retained read-only SQL clones (`source-samples.json`). BPR's exact native
empty transit and five remark rows are explicitly bound to frozen staging;
this does not enable populated remark history or write workflows.

BTR's fixture planner choices preserve SQL predicates/parameters and returned
the same sampled rows as the earlier successful slow diagnostic. They are not
accepted for concurrent browser availability: count/grid both timed out and
queued metadata requests. Do not enable the fixture for human use on this proof.
DBM's earlier count11158/restricted1036 and history/security receipts are reused;
the latest four-page browser pass did not reach DBM.47 focused tests passed.
Graphs, full filters, export/layout, parity and matched performance remain
unverified obligations in the existing inventory/tracker. No later stage began.

The human reported403s; repeated GetAllReports403 requests were observed from
permission-forbidden pages. That user's account was not identified, so do not
claim a resolved root cause. Dedicated fixture login did show RRR/BPR. After
restoration, a real normal-account login proved GetAllReports200 and June17
GetLastRunDate200; fixture actors are disabled. The controlled browser was
logged out. Existing actor grants and protected service identities are unchanged.

Current URL: `http://localhost:3005/login` (normalJune17). Use the existing local
normal preview login, `fresh.preview@vectorflow.local`; its verified password
is `PREVIEW_PASSWORD` in `D:/freshvcf-build/preview/preview.env`. Do not copy it
into Git or reports. Fixture credentials remain separately in
`D:/freshvcf-build/preview/secrets/stage2-fixture-accounts.json` and are disabled.

Exact restoration, already completed and verified:

```powershell
D:/freshvcf-build/venv/Scripts/python.exe tools/stage2_fixture_window.py restore --attempt 007
```

`serve --attempt <new-id>` is a bounded25-minute browser verification lease.
It restores normalMTA and disables actors unless an explicit four-page visible
proof succeeds. A later authorized retry must use a new attempt, preserve all
prior receipts and reuse the existing manifest/mapping; never reload the dataset
or run engines to address this read-path blocker.
