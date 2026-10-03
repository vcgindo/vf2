# Stage 2 shared VM dataset handoff

Updated 4 October 2026. Operational reference; `docs/MIGRATION.md` is the sole status tracker.

## Current login/profile delivery and operation

### 4 October report contention successor

The bounded report correction is deployed on3005. Only Chronic Location's repeated
Python lookup scans changed to insertion-ordered lookup tables; full rows, duplicate
multiplicity, NULL behavior and order are preserved. No SQL/schema/index, engine,
grant or dataset change. Three consecutive nine-request bursts passed with full
response equality (max50.565/53.155/54.376s); the eight-request burst also passed.
All four browser grids/filter journeys, both BTR branches, restricted scopes,
denials, restart, drain and image rollback checks are retained in
`D:/freshvcf-build/evidence/3005-report-contention-20261004-001/validation.json`.

Current MTA image is
`sha256:761719e96c0f95ccdb5f0ad79f7e96125b172ab79fafac72e3a3790615bc952a`.
Gateway/frontend identities below are unchanged. The older MTA image mentioned
below is now the tested rollback target. Fixture policy image_sha256 remains its
original serving provenance; deployment image is separately pinned in deployment.json.
The policy/catalogue/admission bytes remain identical.

From `F:/freshvcf`, verify current state and normal-restoration inputs:

```powershell
D:/freshvcf-build/venv/Scripts/python.exe tools/stage2_report_contention_runtime.py check
D:/freshvcf-build/venv/Scripts/python.exe tools/stage2_identity_catalogue.py check --runtime-checkpoint D:/freshvcf-build/evidence/3005-report-contention-20261004-001/after.json
```

For an expressly requested normal-publication restoration, use the second command
with `restore` instead of `check`. It closes ingress, uses the existing fixture
account disable mechanism and restores MTA/catalogue together. No normal switch
was performed by this correction. Earlier commands without the successor checkpoint
intentionally reject the changed MTA image.

Tested MTA-only rollback/reapply (gateway/catalogue remain selected to the fixture):

```powershell
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml -f D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002/compose.fixture.json -f D:/freshvcf-build/evidence/3005-report-contention-20261004-001/compose.rollback.json up -d --no-deps --no-build mta
```

Replace `compose.rollback.json` with `compose.candidate.json` to reapply the current
candidate, then run the check command above. The prepared operational tool also
records a guarded first rollback receipt; existing receipts are never overwritten.

Remaining limitations: SQL/I/O-heavy BTR paired samples varied19.16–46.87s despite
unchanged SQL and full response equality. Retained PostgreSQL plans/counters show
data/temp I/O and fixed CPU throttling, but matched baseline PG counters are absent;
no specific host/cache cause or general latency acceptance is claimed. Navigating
away from pending BTR via the address bar worked and drained; its SPA profile-link
attempt remained on the loading page. Immediate database cancellation is unproven.
Broader Stage2 and Stages3–5 remain paused. The following login checkpoint details
remain historical evidence, superseded only for MTA image and report timeout status.

The bounded login/profile correction following `612a629` is deployed. The gateway
consumes the same registered MTA catalogue locally, pinned to the active fixture
policy or retained normal-publication hierarchy binding. Live grants, roles,
authentication and scope enforcement are unchanged. No MTA catalogue HTTP call
occurs in configured login/profile assembly. Invalid local metadata fails closed;
there is no stale/empty success or network fallback. Other deployments remain in
their existing HTTP mode.

The stale SPA redirect flag that could leave profile on Loading is corrected.
Real login, Profile Details and navigation to populated RRR/BPR/BTR/DBM pass.
Under the retained nine-request report burst, fresh login took 2.495s while all
nine remained outstanding; 72/72 profile requests succeeded, maximum 2.427s.
Report 504s remain under that load and are not hidden by this identity correction.
This does not close report-performance or general Stage 2 acceptance.

Consolidated evidence:
`D:/freshvcf-build/evidence/3005-login-decoupling-20261004-001/validation.json`.
26 backend and five frontend tests pass; both catalogue payloads match native
MTA exactly. Full broad/restricted identity response content is retained (existing
URL/feature set ordering alone is unordered). Restricted/forged/denial proofs
pass. Gateway/MTA sampled peaks are 119.95/719.02 MiB, with no new OOM events.

Running gateway image:
`sha256:9de37195b08a33a6916fa9c10e8ecd0dc5b4d847bd8f0c96c1892caa61c1188b`.
Running frontend:
`sha256:c7f4fc70f70df8a3a59b557a6d815fc0f473d856c799877c9515cc0f01facf4e`.
MTA remains `sha256:66ddf0722c4f87cbbfa9291067b991f85d51acfbd0cb604661591788463263c2`.
The full April 7 fixture remains selected. Resource limits, worker count,
timeouts, restart policies, serving grants and accepted F1/F2 are unchanged.

Rollback to the preceding streaming gateway/frontend checkpoint:

```powershell
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml -f D:/freshvcf-build/evidence/3005-login-decoupling-20261004-001/compose.rollback.json up -d --no-deps --no-build user-service frontend
```

That selects gateway `ccf8da228c02` and frontend `89118af27cb1`, restores the former
HTTP catalogue dependency, and leaves MTA/data untouched. The same command with
`compose.candidate.json` reapplies the locally selected catalogue. Both selections
are explicit; never pair a fixture gateway catalogue with normal MTA. After any
manual recreation, retained checkpoint IDs must be reconciled before using the
guarded restoration tool; it deliberately refuses changed runtime identities.

The normal-restoration commands below supersede the historical MTA-only commands.
The tool checks current runtime/input identities, stops frontend ingress, disables
fixture accounts through the existing tooling, restores MTA and gateway catalogue
selection together, validates readiness/selection and protected state, then starts
frontend. On failure ingress stays stopped. Check mode passed; an actual normal
switch was not performed. Startup of both catalogue modes was exercised in owned
network-disabled containers. Earlier fixture-window and stabilization proofs are
preserved and are not rewritten as new acceptance.

## Identity and source

Current dataset: `stage2-vm-dataset-20261003-002`. Source preservation, staging,
consumer mapping, explicit fixture admission and **four-page visible availability
are complete**. Window010 re-proved RRR/BPR/BTR/DBM populated browser grids, local
filters, restricted reads and BTR concurrency. The April7 fixture is serving on
3005 for human inspection. This certifies only the four-page availability scope;
whole-page behavior, remaining reports and later-stage acceptance remain open.
Windows001–007 and their failures remain preserved. Current consolidated result:
`visible-availability-validation.json`; historical through007 result:
`visible-availability-validation-through007.json`.

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

## Historical outcome and blocker — windows001–004

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
   indexes required by the retained DailyDataGraph timeout evidence. Also run
   `python -m tools.stage2_btr_indexes` for the seven exact normalized BTR join
   indexes proved in window008. Both tools validate their isolated database and
   exact index definitions; row data remains immutable. The history tool verifies
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

## Four-page availability — retained window008 proof

Window008 uses the same immutable April7 dataset. Seven fixture-only indexes
match the existing case-insensitive, trailing-space-normalized BTR joins, with
run/image keys included. Removing the former forced full-scan planner override
preserves SQL predicates, parameters, rows and ordering. Complete sampled
tech/eco values and counts match the retained result. No schema/model migration,
source reload or engine execution occurred.

Real browser proof: RRR5000/8063 with11 filtered rows; BPR50/97097 with1 filtered
row; BTR5000/97299 in both inventory views with a working SKU filter; DBM5000/11158
with13 filtered rows. The restricted actor sees RRR809, BPR5076, BTR5082 per branch
and DBM1036. All four restricted grids/counts returned200, and forged scope did
not expand any count. Apply/Sleep, normal-preview and unauthenticated denials
remain enforced. Concurrent BTR5000-row grid/count requests returned200 in35.965s
and42.903s under the unchanged60-second gateway and4GiB service limits.

Use `http://localhost:3005/login` with `stage2.broad@vectorflow.local` for the full
native catalogue, or `stage2.restricted@vectorflow.local` for the retained limited
scope. Their existing passwords are the `broad.password` / `restricted.password`
fields in `D:/freshvcf-build/preview/secrets/stage2-fixture-accounts.json`.
Do not copy passwords into Git. Select **Show All** if a page opens its filter
dialog; RRR/BTR/DBM default to5000 rows and BPR to50.

Normal preview credentials intentionally fail fixture admission. The exact API
reason is `fixture_actor_scope_denied`; the inherited frontend may repeatedly
call GetAllReports on its forbidden page. Sign out and use the dedicated fixture
account. Window007's original human identity was not captured and is not guessed.
Authentication and existing permissions were not changed.

The successful controlled window leaves only the isolated MTA fixture selected,
with dedicated read/layout actors enabled and business actions disabled. Other
preview services,3002/3003/3004 and accepted F1/F2 state remain unchanged.
`fixture-window-008/serving-handoff.json` records the admitted runtime identity.

Exact normalJune17 restoration (also disables fixture actors):

```powershell
D:/freshvcf-build/venv/Scripts/python.exe tools/stage2_identity_catalogue.py check
D:/freshvcf-build/venv/Scripts/python.exe tools/stage2_identity_catalogue.py restore
```

The existing bounded `serve` window restores automatically on failure/interruption
unless a successful four-page proof is present. Future retries must use a new
attempt and retain earlier receipts. `tools/stage2_availability_probe.py` can be
passed to Python stdin inside the existing user-service for the four restricted
count/grid and forged-scope checks; `stage2_visible_probe.py` retains the action,
normal-account and unauthenticated denials. Browser proof remains separate.

Seven focused BTR tests, Django check, no-drift migration check/plan and independent
review passed. Full export/layout/history/filter semantics, matched legacy
performance, remaining pages and workflows are not certified by availability.
The original `dataset-validation.json` remains historical; current availability
and scope limits are consolidated in `visible-availability-validation.json`.

## Current latency checkpoint — window010

The same sealed dataset is now served by MTA image
`sha256:66ddf0722c4f87cbbfa9291067b991f85d51acfbd0cb604661591788463263c2`.
`fixture-window-010/serving-handoff.json` supersedes window008's runtime identity.
Only MTA changed; all four browser grids/filters, restricted reads and denied
actions were re-proved. Window009 retained its slower diagnostic results and
restored normal serving before the next bounded trial.

The fixture uses bounded BPR SQL, scoped DBM pair reads, inline RRR CTEs and BTR
page keys before wide daily columns. Count queries use transaction-local planner
settings with success/failure restoration proof. The repeatable index utility
now validates16 exact definitions (the original seven plus nine additions);
unused additions from this attempt were removed. No raw key/value rewrite,
deduplication, engine change, reload or general schema migration occurred.

`latency-001/response-comparison.json` records complete first-page results.
BPR/BTR/DBM and all counts match exactly. RRR's complete row bags and declared
sort-group sequence match; physical order within exact undeclared ties differs.
This is not byte-for-byte ordered equality or permission to add a tie-break.

`fixture-window-010/gateway-latency.json` records three grid/count pairs per page:
median total wall time RRR6.70s, BPR7.83s, BTR16.75s and DBM4.21s. Browser timings
with the existing frontend are12.76s,16.84s,16.76s and3.20s. BTR's API probe requests
5000 rows in each inventory branch and returns33.7MB. The browser observation used
the default On Hand view. Peak MTA memory was1,896,857,600 bytes under4GiB, with no
OOM events. These observations establish neither minimum latency nor performance
parity with3002; the formal matched benchmark remains unproved.

The frontend candidate changes only RRR/DBM's serial filter-apply count/grid reads
to concurrent requests. BPR/BTR already issue them concurrently. This candidate
is separate from the serving MTA change; its build/test and deployment state are
recorded in the sole tracker, `docs/MIGRATION.md`.

Original synthetic-run serving queries also normalized strings during reads;
there were no separate canonical SKU/location lookup columns. Fixture expression
indexes preserve the legacy matching contract, but do not complete a general
canonical-key migration or certify normal-run performance. Accepted F1/F2 state
and calculation evidence remain untouched.

## Earlier 4 October gateway stabilization handoff (historical checkpoint)

The isolated gateway exited137/OOMKilled at00:46:41IST. The incident state and
gateway/nginx logs are preserved in
`D:/freshvcf-build/evidence/3005-stabilization-20261004-001`. Gateway restart
restored service; the deployed correction removes buffered text/JSON/serialization
copies for the four large grids, native export and the observed Chronic read
family. Async iteration avoids Django ASGI's eager conversion of sync iterators.
EOF, errors and downstream cancellation close upstream responses. Full-page
counts also receive bounded waits. No authentication/permission grants changed.

The final source and evidence are a **partial stabilization handoff**. Memory is
corrected; latency acceptance remains blocked. `stabilization-validation.json`
contains all samples, CPU deltas, OOM events and exact runtime configuration.
`response-comparison-final-002.json` compares16 complete responses; all match.
`download-proof.json` proves the full RRR CSV bytes/headers. `restricted-scope.json`
and `security.log` retain scoped reads and denials. `browser-done.json` and page
screenshots prove real login, the four populated pages and navigation away during
pending requests. The profile UI stayed Loading and is not certified.

Gateway sampled peak fell from678MiB before to134MiB across final stress phases;
the old cgroup high-water mark was695MiB. Final MTA sampled peak was742MiB;
its1896857600-byte cgroup high-water mark predates this assignment. Both retained
their limits (gateway1GiB/1CPU, MTA4GiB/2CPU) and restart=no. No OOM recurred.
Two-sample paired API medians worsened rather than proving a latency gain:
RRR7.31→10.36s, BPR7.47→11.78s, BTR both15.99→22.49s, DBM4.18→5.42s.
Browser observations were13.82/9.12/9.00/4.52s respectively (BTR On Hand only).
These diagnostic runs are not the formal matched legacy benchmark.

Eight supported grid/count requests all returned200 in the final overlap run.
Adding Chronic in retained runs caused report504s. Login/profile synchronously
call MTA `GetAllPermmision` via `ALL_PERMISSIONS.get_combined_permissions`; its
two sync report workers therefore remain on the identity-response critical path.
With the full gateway observation window, profile returned200 but took up to51.47s;
fresh login during the burst exceeded the30-second probe deadline. Earlier
10-second observer timeouts are client failures, not proof of HTTP502/504.
No catalogue snapshot, cache, alternate permission source, worker increase or
larger timeout was added. This is the precise unresolved concurrency/latency
boundary for command-centre review; wider Stage2 and Stages3–5 remain paused.

Running images:

| Service | Image |
|---|---|
| Gateway | `sha256:ccf8da228c02c7ebd25eb91c5dae52447fed13ae58f20fd17bf931ea768bee36` |
| Frontend | `sha256:89118af27cb171259f14d570f35cfcdc35e21ebcd20d2a784716c76ec60fe401` |
| MTA, unchanged | `sha256:66ddf0722c4f87cbbfa9291067b991f85d51acfbd0cb604661591788463263c2` |

`/healthz` explicitly means frontend-only liveness. `/readyz` checks gateway,
identity DB and admitted MTA dependency availability; report saturation can make
it503. It does not bypass business authentication or certify page acceptance.
After a controlled restart, wait for `/readyz`200 before attempting login; the
retained immediate-post-restart502 attempt is not hidden.

To roll back only this deployment to the exact prior gateway/frontend images,
from `F:/freshvcf`:

```powershell
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml -f D:/freshvcf-build/evidence/3005-stabilization-20261004-001/compose.rollback.json up -d --no-deps --no-build user-service frontend
```

That rollback reintroduces the known gateway buffering defect. The same command
with `compose.candidate.json` reapplies the verified correction. MTA, database,
accounts and other services are unchanged by either command.

At that historical checkpoint, normal June17 restoration used `stage2_stabilization_restore.py`
instead of the old window010 command. Its check-only mode passed against the
current runtime. It checks accepted/protected state and the sealed restore
configuration, creates a separate restoration receipt, then reuses the original
account-disable/MTA-only restore checks. Window010's historical protected-service
IDs are preserved. If gateway/frontend are subsequently rolled back or otherwise
recreated, the new checkpoint deliberately refuses restoration until those new
identities are explicitly reconciled. No normal restoration was executed here;
the full April7 fixture remained selected for review. The current coordinated
catalogue restoration at the top of this handoff supersedes this old procedure.
