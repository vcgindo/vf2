# Fresh VectorFLOW migration — current baseline

Baseline date: 3 October 2026. Implementation checkpoint: `2d0cfde95606aef58a486e186bde1558802ef542` (pushed).

## Authority and current instruction

This is the **only migration status tracker**. Whole-page implementation remains
**PAUSED**, not complete. The separately authorized Stage2 dataset preparation
and bounded four-page availability correction are complete for the scope below:
RRR/BPR/BTR/DBM populated browser grids, counts, local filters and restricted reads
on3005. Engines, accepted F1/F2 state, replay, authentication permissions, other
pages and Stages3–5 were not changed. The isolated fixture remains serving after
window010's successful admission, security and protected-resource checks.

The previous 4,286-line tracker is preserved byte-for-byte in [the historical snapshot](archive/MIGRATION_2026-10-03_2d0cfde.md), SHA256 `a913419e34a3318d7ca09f11b163295c9d695b55d99e3060e87c23fadc84242b`. It contains provenance and exact earlier approvals, **not active instructions or a second queue**. Do not load the whole archive routinely; consult the relevant passage only when an unresolved contract requires it.

Current human instructions and applicable repository constraints govern execution. This baseline records their current status; it does not broaden an approval or waive a source contract. Historical “active”, “pending”, “unpublished”, “continue” and old outage statements do not override this baseline. Supporting plans describe contracts, not current authorization.

## Objective and architecture

Port the canonical deployed MTA behavior into Django/Python and PostgreSQL, connecting the retained frontend, authentication and direct-port MTO. Deliver a runnable application with calculation/state parity, correct presentation and complete application acceptance. SQL Server/.NET remains the independent validation oracle, not a modern production calculation dependency.

Canonical authority: deployed DLL/BAT/SQL/config at `F:/VFlow_Local/local-runtime/mta-engine` and `mta-latest`, preserved at `F:/VFlow_Source_Backup/deployed-demo/MTA`. API DLL SHA256: `0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346`. Pins are in `baseline/manifest.json`. Recovered source is authoritative only where matched to that deployment.

`execute_day` remains the production day boundary. Operational state, histories, actions and consumer projections are typed PostgreSQL rows linked to run identity, preserving duplicates and source order. JSON metadata or trace blobs do not replace operational state. MSSQL and PostgreSQL physical schemas must not be assumed identical.

## Programme status

Latest human override: STOP benchmark-copy/recovery/repopulation and copy-readback
work. Preserve partial artifacts without deletion. Advance the same BTR task using
existing legacy SQL and existing Fresh PostgreSQL databases, with authorized
temporary reversible resource matching on BOTH (including serving PostgreSQL),
then restore original settings. This supersedes copy prerequisites and the earlier
fixed-serving-allocation restriction for the benchmark window only. No data reset,
reload, replay or infrastructure expansion. Future replication or replacement
infrastructure decisions require prior explicit human approval. Immediate exit:
verify existing legacy availability and deliver comparable heavy-data BTR timings,
reusing retained identities/correctness proof without full table rescanning.

Prepared next intervention (planning only): [BTR daily reporting-layer assessment](BTR_DAILY_REPORTING_PLAN.md).
The human requests BTR-specific design aligned to the existing daily refresh.
Build validated report generations after successful daily output publication;
preserve engine state, live permissions, exact report semantics and atomic
generation selection. This is not active implementation authorization or a second
queue. The bounded existing-database benchmark has reached the consolidated
blocker below; its baseline feeds the proposed architecture decision.

### BTR query/access-path performance — consolidated blocker; no successor deployed

The bounded intervention stops at its authorized consolidated-blocker exit. No
safe query/index improvement was established. Accepted source7b40ba6 and MTA image
761719e96c0f95ccdb5f0ad79f7e96125b172ab79fafac72e3a3790615bc952a remain serving.
Performance parity and broader Stage2 acceptance are **not achieved**.

The latest human override was followed: copy/recovery/full-copy verification was
stopped, only the owned scan cancelled, and both owned copy containers stopped.
Partial data and evidence remain inert; no recovery or deletion occurred. Existing
legacy SQL and existing Fresh PostgreSQL supplied the actual comparison. Future
replication/replacement infrastructure requires prior explicit human approval.

The existing legacy launch issue was resolved;3002/5153 became available and both
native APIs returned200 from the same HTTP client in the existing gateway. The
benchmark temporarily enforced3GiB/2CPU per database and4GiB/2CPU per application.
SQL's own resource view reported cpu_rate200 and3072MiB throughout the measured
boundary snapshots. No active SQL request was observed at those boundaries.
Shared host load, Windows-versus-Linux memory accounting, storage and cache
conditions are retained qualifications; no disk cache was flushed.

Five warmups followed by30 alternating measured paired grid/count journeys per
engine completed at concurrency1, using both branches/all90days/page1/5000 and
the same broad scope. Request timing includes full response transfer; compression
and evidence processing occur afterward. Full responses were retained and checked.

| Existing reader | Median paired journey | p95 | Journeys/second | Errors |
|---|---:|---:|---:|---:|
| Canonical legacy |12.728s|19.228s|0.07072|0/30|
| Fresh accepted reader |13.976s|22.020s|0.06788|0/30|

Fresh is9.81% slower at median,14.52% slower at p95 and4.01% lower in throughput.
This measured scope fails the no-worse performance gate. It is a baseline result,
not a query optimization or a full API/browser performance certification.
All120 measured responses passed their full contracts: Fresh strictly; legacy grid
Category alias order only under the exact human-approved April7 multiset exception,
including duplicate multiplicity. Original strings remain retained; types, other
values and row positions are strict. Counts remain97299 in both branches.

The first concurrency4 warmup was interrupted by a resource-observer prelogin
timeout. SQL Server logged insufficient memory in its default pool at06:51:11;
its3GiB job ceiling was reached. Response evidence was not saved before that
observer failure, so concurrency4 is UNPROVED. The recorder is corrected to save
responses first; the failed attempt is not reclassified as a passing measurement.
SQL's configured max-server-memory remained its original unrestricted setting;
future c4 testing must account for internal buffer/non-buffer headroom within the
same total ceiling. No speculative capacity increase or infrastructure replacement
was performed. Application-cold/browser performance remains unproved as well.

Bounded query experiments remain rejected:
- Key-prefix paging matched eight complete heavy responses and104 strict normal
  cases (14 retained declared flaws), but changed values/tied selection in10/30
  actual-reader adversarial cases, including D90=11 becoming10. A semijoin variant
  also failed ordering. Neither can be deployed.
- Normalized materialization regressed counts from approximately3.52/4.96s to
  9.48/10.17s and timed out the grid at55s.
- Duplicate-multiplicity count aggregation preserved97299 counts but regressed
  approximately1.12/1.88s to3.42/3.44s.
These diagnostics do not certify all possible query designs; they establish that
none of the bounded candidates is a correct demonstrated improvement.

Restoration passed: exact accepted image/runtime, admission, selected catalogue,
protected state, original PostgreSQL1GiB/1CPU (2GiB memory+swap), and grant digest
92579e9b054da03d9e170b91ca3037d35c6d7a8ae757179a9a28a6b7658d264a.
SQL/API temporary job limits were cleared with no restoration errors, and SQL
requests drained. No calculation, replay, serving dataset write, grant/index/schema
change, new image or reporting projection was deployed. Prior accepted browser,
export/security/overlap/restart/rollback proofs remain applicable to the unchanged
image; no new candidate acceptance is claimed. Fourteen focused restored-reader
checks and six scoped comparator tests pass; the unrelated prior suite failures
remain as recorded below.

Consolidated evidence:
`D:/freshvcf-build/evidence/3005-btr-performance-20261004-001/matched-consolidated-result.json`.
It binds `existing-matched-001/observations.jsonl`, `summary-c1.json`, full bodies
and comparisons, `existing-budget-001/budget-result.json`, SQL memory evidence,
`matched-final-runtime.json`, grants and rejected candidate receipts. Earlier
`validation.json` is historical and its copy prerequisites are superseded.

Next decision: review the prepared BTR daily reporting-layer assessment as a
separately authorized storage/read-model intervention. Reuse existing databases,
full response contracts, normal-publication proof and the measured baseline.
Do not implement it, resume copy work, or open broader Stage2–5 under this exit.
Operational details: [dataset handoff](STAGE2_DATASET_HANDOFF.md).

### Report contention correction — PASS for bounded overlap; stopped for review

4 October 2026: the human in the successor control chat authorizes the bounded
[report contention correction](REPORT_CONTENTION_CORRECTION_PLAN.md) following
accepted login/profile checkpoint `fe8ad13`. Active exit: eliminate the retained
60-second 504s for the four existing grid/count pairs plus ChronicUnavailabilityLoc
under the same full fixture and resource limits, preserving complete responses,
scopes and login/profile independence. Diagnose query/request/queue work, apply
only measured non-semantic corrections, verify repeated overlap and browser
behavior, deploy on isolated3005, commit/push and stop for review. This narrowly
supersedes the report-tuning pause below; general Stage2 and Stages3–5 stay paused.
The contract fixes the permitted boundary, required proof and blocker conditions;
it is not a second status tracker.

Execution starts from the unchanged `fe8ad13` runtime. Capture individual/pair
and eight-/nine-request timing, isolated native profiling, DB activity and drain
before choosing a correction. Successful retained responses remain the oracle;
timeouts are failures, never expected response bodies. No engine, import,
permission, capacity or broader page work is opened.

The bounded baseline reproduced six 60-second failures in the nine-request burst;
the eight-request burst succeeded (maximum33.91s). Native attribution identified
Chronic Location's repeated lookup scans as dominant:55.14s initially, and105.31s
in the retained full-bag differential run. Its insertion-ordered lookup correction
reduces that reconstruction to0.56s, preserving all3340 joined rows and five full
response cases (broad, restricted, SKU/location filters, empty). The broad response
matches the retained successful native response byte-for-byte; the candidate full
request took6.24s. The normal June17 response also matches exactly (empty terminal
population); adversarial tests cover duplicate/NULL/missing joins and order.

Only the MTA image is changed. Dataset/policy/catalogue hashes, admission, resource
limits, worker count, gateway/frontend, grants and accepted state remain fixed.
No SQL/index/schema or calculation change is included. Evidence:
`D:/freshvcf-build/evidence/3005-report-contention-20261004-001`.
The original drain monitor included its own CPU overhead; its nine-burst drain
timeout is retained as an observer failure. A corrected Gunicorn-only CPU plus DB
activity check confirmed quiescence before candidate proof/deployment. Do not use
the original aggregate-CPU drain times as precise worker completion times.

Final bounded acceptance: three consecutive nine-request bursts returned all27
complete expected responses, maximum50.565/53.155/54.376s under the unchanged60s
gateway limit, without restart/cache clearing between bursts. The eight-request
burst also passed (45.424s). All six measured candidate phases match the retained
successful native baseline in complete JSON types, values, fields and ordering.
Fresh login overlapped each burst (0.865/1.022/1.228s);94 profile reads succeeded,
maximum2.046s. Worker/DB quiescence was observed between bursts. Sampled candidate
MTA/gateway maxima were502.98/125.24MiB with no OOM, within unchanged4GiB/1GiB.
The finite samples are not formal matched-legacy median/p95 acceptance.

Browser RRR/BPR/BTR/DBM rendered5000/50/5000/5000 rows from8063/97097/97299/11158
totals; local SKU filters worked and both BTR inventory branches rendered.
Address navigation away from pending BTR reached Profile Details; work drained
and returning BTR loaded successfully. The SPA profile-link attempt during BTR
loading stayed on BTR; this observation remains, and immediate SQL cancellation
is not claimed. Restricted/forged/unauthenticated/normal-actor/action-denial proofs
pass, and serving grants retain SHA92579e9b054da03d9e170b91ca3037d35c6d7a8ae757179a9a28a6b7658d264a.
23 focused tests pass. Normal Chronic's terminal empty response is byte-identical;
populated/duplicate coverage is supplied by fixture and adversarial proofs.
There is no affected backend Chronic download route.

Unchanged BTR paired reads varied19.16s before to44.89–46.87s afterward. Image
source comparison proves only insights.py changed; the SQL text and response
hashes match. Follow-up observed37096 PostgreSQL block reads,10.58MB temporary
files,26.32 CPU-seconds and9.24 throttle-seconds at the fixed1CPU/1GiB allocation,
with no lock waits or other active database. Exact EXPLAIN/BUFFERS plans are
retained. The earlier baseline lacks matching PG counters, so a specific host/
cache cause is unproven. This remaining SQL/I/O performance limitation is explicit;
the bounded timeout fix does not certify broader low-latency acceptance.

MTA image761719e96c0f95ccdb5f0ad79f7e96125b172ab79fafac72e3a3790615bc952a
is deployed. Restart, exact rollback to66ddf0722c4f87cbbfa9291067b991f85d51acfbd0cb604661591788463263c2,
candidate reapplication and coordinated normal-restoration input checks pass.
Gateway/frontend, fixture admission and accepted/protected state remain unchanged.
Consolidated receipt:`3005-report-contention-20261004-001/validation.json` under
the evidence root above. Operational commands are in the dataset handoff.
The delivery commit is identified by the external `delivery.json` receipt, avoiding
a self-referential commit hash. General Stage2 performance and Stages3–5 remain open.

### Login/profile catalogue delivery — PASS; stopped for review

4 October 2026: direct human authorization in command-centre turn
`01a10375-b2b4-7993-aad5-35e850573d9d` opens only the dependency correction in
[the implementation contract](LOGIN_REPORT_WORKER_DECOUPLING_PLAN.md), from
`612a629`. Consume the same validated catalogue locally in the configured 3005
user-service; preserve live identity grants, scope enforcement, response values,
fixture/publication selection, resource limits and protected services. No report
tuning, F1/F2 changes or general Stage 2–5 work. Required exit: exact catalogue
and identity comparisons, fail-closed selection/startup and isolated revocation
proof, real login/profile under the retained report contention, coordinated
restoration, committed/pushed deployed result or precise consolidated blocker.
The preceding stabilization stop remains in force outside this boundary.

Deployed and verified on 4 October 2026. The configured user-service reads the
same checksum-bound catalogue locally, with the existing fixture policy or normal
publication/hierarchy binding. Its MTA permission branch makes no catalogue HTTP
request. Missing, corrupt, mixed or wrong selection fails startup/returns 503;
local assembly failures cannot become an empty-permission success. Effective
grants remain live identity-database queries; other deployments retain HTTP mode.

The profile Loading defect was a stale module-level redirect flag surviving SPA
login. A new protected verification clears that transition flag, always fetches
profile, and sends missing/failed profile responses through the existing login
redirect. Successful local login also resets the flag. No permission or route
rule was changed.

- 26 focused backend tests pass, including actual login/profile assembly without
  MTA HTTP and grant addition/revocation in an isolated identity test database.
  Five frontend regression tests pass; both production images built successfully.
- Complete normal and fixture catalogue payloads equal the unchanged native MTA
  view, including ordering and types. Network-disabled ASGI startup accepts both
  valid configurations and rejects missing/wrong selections. Broad/restricted
  login and profile preserve all response content; only the pre-existing
  `list(set(...))` URL/feature arrays are compared as unordered sets. No values
  are excluded; catalogue and hierarchy array order is compared exactly.
- Unloaded login/profile: broad 0.931/0.437s; restricted 1.161/0.403s. During eight
  full grid/count requests plus Chronic, fresh login returned 200 in 2.495s with
  all nine report requests still outstanding. All 72 profile requests returned
  200; maximum 2.427s, 70 completed while reports were pending. Earlier 30s login
  timeout and 51.47s profile evidence remain retained. These are bounded diagnostic
  observations, not matched legacy report-performance acceptance.
- Real browser login during contention returned 200, Profile Details rendered,
  all four populated pages were reached, and SPA navigation back to profile
  completed. Restricted four-page reads, forged scopes, unauthenticated and
  normal-versus-fixture denials, and disabled Apply/Sleep all pass.
- Sampled gateway/MTA memory peaks: 119.95/719.02 MiB; no new OOM events. CPU over
  the measured phase, including the probes/browser activity: 45.049/157.149s.
  Existing limits/timeouts/restart policies are unchanged. MTA was not restarted;
  image, admission, full fixture, accepted F1/F2 and serving grants are unchanged.

Evidence: `D:/freshvcf-build/evidence/3005-login-decoupling-20261004-001/validation.json`,
with retained bodies, browser screenshots, resource samples and test logs. Initial
test setup/coverage-run failures remain recorded alongside the corrected passes.
Gateway image `sha256:9de37195b08a33a6916fa9c10e8ecd0dc5b4d847bd8f0c96c1892caa61c1188b`;
frontend `sha256:c7f4fc70f70df8a3a59b557a6d815fc0f473d856c799877c9515cc0f01facf4e`.
Recreated startup/readiness and `tools/stage2_identity_catalogue.py check` passed.
The handoff records coordinated normal restoration and exact-image rollback;
normal restoration was not executed, so the April 7 fixture remains available.

Residual limitation: the retained contention burst produced 60s 504s for BPR
grid, BTR grid, DBM grid/count and Chronic. The following aborted-read diagnostic
also received a BTR 504. The login/profile dependency exit is complete; report
latency, general Stage 2–5 and other workflows remain paused, not accepted.

### Earlier 3005 stabilization checkpoint — memory fixed, identity blocker superseded above

4 October2026: human authorization in review chat
`01a100e2-7943-7102-9760-62d9e492ecd9`, turn
`01a1033b-54a0-7692-9984-d480048bd840`, supersedes the pending serving-approval
blocker for the isolated3005 gateway/user-service, MTA and frontend only. The
gateway exited137/OOMKilled at1GiB on3 October19:16:41UTC; frontend liveness200
did not establish login/API availability. Preserve this incident and diagnose
actual forwarding/request memory lifetime before choosing the smallest correction.
Active exit: reliable real login/profile during bounded repeated and overlapping
RRR/BPR/BTR/DBM navigation, full retained responses/scopes and resource/timing
proof, verified deployment, rollback identities, one committed/pushed handoff.
Keep limits/restart policy fixed; no reload, engine/F1/F2/auth/permission change,
other-page implementation or broader Stage2/Stages3–5 continuation. Earlier
four-page availability is historical, not a claim that the failed gateway is healthy.

Result: the bounded gateway correction and RRR/DBM frontend candidate are deployed.
Stop for command-centre review; do not resume general Stage2 or Stages3–5. Evidence
root: `D:/freshvcf-build/evidence/3005-stabilization-20261004-001`;
`stabilization-validation.json` consolidates resources, timings, protected state
and exact running identities. This is **not full stabilization acceptance**.

- Original BTR33.7MB forwarding raised an isolated gateway process from128MiB
  to377MiB peak through body/text/JSON/serialization allocations. Actual old
  gateway cgroup peak reached695MiB during two full four-page rounds.
- Large MTA grid/export and observed Chronic reads now use an async byte iterator;
  no duplicate report object graph, explicit close on EOF/error/disconnect,
  bounded connect/read waits, and count-request cleanup within the existing
  public60-second limit. Commands, authentication, scope injection and MTO remain
  unchanged. The measured final gateway peak is134MiB across stress samples;
  no gateway/MTA OOM. Largest sampled MTA usage is742MiB under the unchanged4GiB.
-16 focused gateway tests pass, including ASGI first-chunk/disconnect, timeout,
  downloads and existing identity tests. All16 complete grid/count responses at
  full page sizes match the original gateway after UTF-8 JSON decoding. No new
  RRR tie-break is introduced. The complete1,524,093-byte RRR CSV and headers
  match the native response. Four restricted grids/counts, forged scope,
  Apply/Sleep403, normal-preview403 and unauthenticated denials pass.
- Real browser login and all four populated pages pass. Observed page times are
  RRR13.82s, BPR9.12s, BTR On Hand9.00s and DBM navigation4.52s. Navigation away
  during pending reads and return to populated RRR were exercised. `/profile`
  itself remained Loading despite observed API200; that UI is not certified.
- Full paired API medians (two diagnostic observations each), before→final:
  RRR7.31→10.36s, BPR7.47→11.78s, BTR both15.99→22.49s, DBM4.18→5.42s.
  There is **no demonstrated API latency improvement** or matched legacy parity.
  Eight supported overlapping grid/count requests returned200 within39.88s;
  adding Chronic produced60-second report504s in retained stress attempts.

Consolidated blocker: `ResponseUser.response()` and `ResponseProfile.response()`
call `ALL_PERMISSIONS.get_combined_permissions()`, which synchronously retrieves
MTA `GetAllPermmision` through the same two sync workers as large reports. The
final dependency probe's profile requests returned200 but took up to51.47s
(65-second observer, unchanged60-second gateway). Real login during that burst
exceeded the existing30-second probe timeout. Earlier10-second profile observer
failures are retained and are not misreported as public HTTP failures. Gateway
memory is healthy; report-worker contention still delays identity responses.
Correcting catalogue delivery/freshness or worker isolation changes the present
dependency boundary and is not inferred here. No permission snapshot/cache,
new source, extra workers, memory increase or timeout extension was introduced.

Current gateway image: `sha256:ccf8da228c02c7ebd25eb91c5dae52447fed13ae58f20fd17bf931ea768bee36`.
Current frontend: `sha256:89118af27cb171259f14d570f35cfcdc35e21ebcd20d2a784716c76ec60fe401`.
MTA remains `sha256:66ddf0722c4f87cbbfa9291067b991f85d51acfbd0cb604661591788463263c2`.
Readiness now distinguishes frontend-only `/healthz` from `/readyz` checks of
the identity database and admitted MTA; neither certifies whole-page behavior.
Protected services/publications match the retained checkpoint. Normal restoration
uses `tools/stage2_stabilization_restore.py` (check-only passed), preserving
window010 and checking the explicitly updated protected-service identities.
Gateway/frontend rollback commands and limitations are in the dataset handoff.

The existing four-page latency history below is retained context for this result.

Direct human follow-up authorizes inspecting contracts and data-fetch architecture
and reducing latency on the existing RRR/BPR/BTR/DBM fixture paths. Profile the
current full page-size requests, reuse earlier selective-read work, and correct
measured redundant work at the relational/request boundary. Preserve responses,
scope/filter semantics, duplicate bags/order, immutable dataset, admission and
the4GiB/two-worker/60-second limits. No engines/F1/F2/authentication/permission
changes, other-page work or dataset reload. Required proof: complete affected
response comparisons, focused regression checks, authenticated concurrent API
and browser timings, and preserved fixture/normal restoration. Retain window008
as the rollback checkpoint; record measured improvements and remaining limits.

Measured follow-up within this same item: the retained RRR and DBM frontend hooks
serialize count then grid on filter application (RRR browser12.76s versus concurrent
gateway6.7s). BPR and BTR already start both requests concurrently and remain unchanged.
Prepare only concurrent existing count/grid reads in the RRR and DBM hooks,
retaining endpoints, payloads, page sizes, error cleanup and UI configuration.
Prove concurrency and rejection handling with deferred-request tests. The
protected frontend service is not replaced by the MTA-only fixture window;
any frontend runtime replacement must respect the separate serving approval.

Backend checkpoint: window010 repeats the populated four-page browser/filter,
restricted-scope and denial proofs with the same frozen dataset. Fixture reads
now use bounded BPR SQL, pair-filtered DBM inputs, narrower BTR metadata/late daily
column fetching, inline RRR CTEs and a transaction-local measured count plan.
The index roster retains the prior seven and adds nine measured access paths;
raw keys and stored facts are unchanged. Full first-page response comparisons
pass; RRR preserves full row bags and declared sort-key groups, with physical
permutations inside undeclared exact ties (no invented tie-break).

Three concurrent gateway observations give median complete grid/count wall times
RRR6.70s, BPR7.83s, BTR16.75s and DBM4.21s. Existing-frontend browser observations
are12.76s,16.84s,16.76s and3.20s respectively. These are diagnostic observations,
not the required matched legacy performance protocol. BTR remains slow; minimum
latency and production-scale normal-run performance are not accepted. Evidence:
`latency-001/response-comparison.json` and `fixture-window-010` below the dataset
evidence root. Window009's unsuccessful timing trial restored normal serving;
window010 retains fixture serving and its exact normal restoration command.

Normalization finding: the original synthetic-run RRR serving SQL also used
`lower(rtrim(...))`; relational state was keyed by run/image/source ordinal,
without dedicated canonical SKU/location lookup columns. F1/F2 correctness proof
did not certify a scalable consumer lookup design. The present expression indexes
are an isolated compatibility correction, not a schema-wide canonical-key
migration or evidence that normal production access paths are now optimized.

Client candidate `freshvcf-preview-frontend:latency-20261003` built successfully;
four deferred-request Jest tests passed. Its RRR/DBM changes are now deployed in
the above stabilization frontend. The prior frontend rollback image is
`sha256:a37599db5558f52af99753ece785a0254aedc64a832906b3f99533d6983f366a`.
The final focused backend run passed16 of17 tests (one opt-in PostgreSQL case
skipped there and separately passed against PostgreSQL). A unit-route run inside
the serving fixture environment failed because its mocked actor was denied;
the clean local test environment passed. Preserve both receipts. The above
stabilization disposition supersedes the former pending deployment approval;
neither this checkpoint nor fixture availability closes Stage2.

### Four-page visible-data delivery — PASS; fixture serving on3005

The direct human instruction in this chat authorized closing only the current
3005 availability blocker. Window008 completed that bounded exit on3 October2026.
Full page implementation remains paused. This is visible dataset availability,
not whole-page, Stage2, F3, engine parity or matched performance acceptance.

Reused the sealed April7 VM dataset, existing typed consumer schema, mapping,
loader, fixture admission, page contracts and all unaffected proofs. No source
extraction, reload, engine/replay/F1/F2 mutation or permission change occurred.
The BTR execution plan showed repeated full scans/sorts of97k-row relations.
Seven exact normalized join-expression indexes were added only to the owned
fixture database; the fixture-only `enable_nestloop=off` override was removed.
SQL predicates, parameters, bags, values and ordering are unchanged. Full sampled
tech/eco responses and counts equal the retained slow result. The index tool
validates manifest/database, exact index definitions and frozen identity.

| Page | Browser population | Local SKU filter | Restricted API count |
|---|---|---|---|
| RRR |5000 of8063 |11 rows for21101151051000 |809 |
| BPR |50 of97097 |1 row for23102164028000 |5076 |
| BTR |5000 of97299; both inventory views |Retained21101050051000 rows |5082 in each branch |
| DBM |5000 of11158 |13 rows for21101149051000 |1036 |

Real broad-account browser login, navigation and filters passed. All four
restricted count/grid APIs returned200; forged scope did not expand any count.
Concurrent authenticated BTR requests at the actual5000-row page size returned
200: both grids35.965s and count42.903s, below the unchanged60-second gateway.
Peak MTA memory was2.20GiB with zero OOM events. Seven focused BTR tests passed;
Django check, migration drift check and migration
plan passed (no model migrations). Independent bounded review found no blockers.
No claim replaces the retained broader suite's two pre-existing Expedite failures.

403 attribution: normal `fresh.preview@vectorflow.local` is intentionally absent
from fixture policy and returns `fixture_actor_scope_denied`; dedicated broad/
restricted actors pass. The frontend's existing forbidden-page navbar can repeat
GetAllReports after a403, masking that cause. Window007 lacks actor identity, so
its human session cannot be retrospectively attributed. Window008 proves the
supported fixture accounts work, normal/unauthenticated access remains denied,
and Apply/Sleep remain disabled. No authentication/permission bypass was added.

Current service: isolated April7 fixture on3005, dedicated read/layout actors
are enabled. Use `stage2.broad@vectorflow.local` (or the restricted actor); retrieve
its existing password from the local fixture secret file identified in the
handoff. Ordinary preview accounts are not fixture accounts. Protected services,
accepted publication and existing grants passed the window's unchanged checks.
F1/F2 engines/state, other pages and Stages3–5 remain outside this delivery.

Current consolidated proof:
`D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002/visible-availability-validation.json`.
Window008 retains browser text/screenshots, scope/security and concurrent gateway
receipts, runtime resource evidence and `serving-handoff.json`. Windows001–007
and the former blocked consolidated receipt remain preserved. To restore normal
June17 and disable the fixture actors:
`D:/freshvcf-build/venv/Scripts/python.exe tools/stage2_fixture_window.py restore --attempt 008`.

### Bounded Stage 2 dataset preparation — consolidated consumer blocker

The human supplied VM-extracted backups at `E:/vflow_backup_dump` in the review
chat on 3 October 2026. Active work now verifies/freezes/restores the available
Importer/BPR/BTR originals in **new** owned resources and prepares their staging
and mapping independently. The human subsequently confirmed DBM copying complete;
its stable original was hash-pinned and restored separately after preserving an
interrupted capture. All four API sources share 7 April 2026 LastBatchRun dates.
Interface/IntermediateDB/Vendor/Distributor are conditional source dependencies,
not automatic readiness gates; any required missing input must name an actual
Stage 2 consumer. None may be borrowed from synthetic sources. Exit remains
dataset readiness or a consolidated evidenced blocker. Required proof includes
hashes, usable restores, source dates/identity/coverage, bounded capacity, typed
bulk readback and actual consumer mappings. No engine, accepted-state, permission,
serving or page changes under the initial scope. The existing app goal is active.

**Bounded authorization amendment (3 October 2026):** verified human instruction
in command-centre chat `01a100e2-7943-7102-9760-62d9e492ecd9`, turn
`01a100e3-6258-7bf1-a9d0-f191636ed24f`, authorizes its relayed grant: dedicated
local fixture actors through existing account/auth mechanisms, new actor-owned
MTA read/navigation and layout grants using the original 9-product/60-location
catalogue; preserve source IDs, NULL/empty semantics and existing accounts/grants.
No VM passwords/sessions or invented memberships. Catalogue collisions require
isolated fixture configuration/storage. Implement only explicit fixture admission
and representative real authenticated API reads/scope denial. If needed, switch
only MTA on3005 temporarily after recording image/config/database/publication and
exact restoration; restore June17/catalogue/actions-disabled on every exit and
prove protected resources unchanged. Preserve gateway/frontend/auth/MTO services.
Fixture accounts must have no normal-publication access and be disabled outside
the test window; credentials remain outside Git/logs. Keep4GiB/2CPU/two workers/180s/
restart=no. Engine changes/execution, F1/F2 mutation, business actions, page-by-page
work, performance campaigns and Stages3–5 remain excluded. Active exit remains
dataset readiness or a precise additional blocker; no new queue.

**Bounded preparation stopped at a consolidated blocker; dataset readiness is
withheld.** All303 source tables /91,645,123 rows are preserved. The73-table
Stage2 union /56,500,041 rows passed full staging readback;60 consumer images
/52,760,538 rows and six projections /965,475 rows passed full typed source/target
comparison. Manifest `afe42593ca2abdf5e2395433ac70834723f4eac1dfa5a2982192c7688906b836`
is sealed. Database `test_freshvcf_stage2_vm_20261003_002`, fixture run
`bfd75b4b-a9df-4a08-82d3-852e3324b623`, remains explicitly non-production.
A zero-insert retry passed;396 relations are immutable. Three fixture-owned
pair-history indexes preserve the same frozen identity.

Window004 proves native DBM counts11158 broad /1036 restricted, populated grids,
forged-scope non-expansion, a populated history drill-down, Apply/Sleep403 and
normal-preview-actor403. Research/historical-availability/BPR/remarks/Planning
Expedite remain explicitly503. Existing accounts/grants are unchanged. Both
fixture actors are disabled, real login denial is proved, and normal June17
image/configuration/admission plus all protected services are restored.

**Blocking contract:** existing `RRRDataCount` over this native population
returns gateway504 after60seconds (windows003 and004). RRR grid, BTR and
fulfillment checks following it were not executed; do not claim their acceptance.
Further RRR presentation-query diagnosis/correction is a separate authorized
boundary, not page implementation or an engine change. Other declared native
ancillary/history adapter gaps and39 static UI metadata differences remain in
the handoff. No timeout increase, API assertion waiver or performance campaign.

Earlier windows are retained:001 exposed the fixture DBM quadratic join;
subject-bag partitioning now uses the unchanged selector and passes exact
bag/NULL/missing/accepted/predicate equivalence.002 exposed pair-history scans;
owned indexes resolved that check (window003 history200 in4seconds). All four
windows restored normal service.37 focused tests pass; the broader19-test HTTP
suite retains exactly two pre-existing Expedite failures. No engine execution,
F1/F2 mutation, replay, frontend implementation or Stages3-5 work occurred.

Consolidated receipt: `D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002/dataset-validation.json`
(`BLOCKED_CONSUMER_READINESS`). Manifest, mappings, repeatable loaders and exact
operation/restoration steps are in [the operational handoff](STAGE2_DATASET_HANDOFF.md).
The requested stop-at-readiness-or-blocker boundary is reached; no adjacent work
is active. Page implementation remains paused.

The following describes the preserved, superseded first candidate:

On 3 October the human corrected source authority to `F:/VFlow_Source_Backup`
in review chat `01a0f7c6-1050-7741-b80a-a7f10ca0d04d`. No original populated
SQL backup set was found in the bounded preserved-source inventory/MTA archives;
its reconstruction runbook says databases were not copied. The local Demo
runbook explicitly identifies its 1,240-row population as synthetic reconstruction.
Matching database names did not establish original-data lineage.

Before the correction, eight checksum-verified local Demo backups were restored
to owned read-only `VFTEST_Fresh_S2_20261003_001_*` clones. 523 tables / 280,651
rows passed full typed staging readback in owned PostgreSQL database
`test_freshvcf_stage2_dataset_20261003_001`; 102 consumer images and six projection
families were copied and fully read back. The consumer transaction finished before
the stop took effect. All are preserved as quarantined evidence, **not dataset
readiness**. Fixture partition `f9db3dfc-efc3-488d-af2f-a88e8b2c68ee` is
`LEGACY_UI_FIXTURE/FIXTURE_BLOCKED`, with no engine success, parity receipt,
checkpoint, command or production manifest. No fixture admission/serving change
was implemented. All three loader entry points now fail before source/database
work pending reconciliation; no environment override is provided.

Additional observed limits of that rejected candidate: native `LOCAL_ALL`
hierarchy matches zero unchanged modern permission memberships; Suggestions,
SuggestionsLog and RationingHistory are empty; BTR BPR has one date; source
OrderIdentity is absent. Do not transfer these findings to the missing original
data. No engines, accepted F1/F2 rows, authentication permissions, serving services
or page implementation were changed. Scope ends at this consolidated blocker.

Handoff: [Stage 2 dataset handoff](STAGE2_DATASET_HANDOFF.md). Evidence:
`D:/freshvcf-build/evidence/stage2-shared-dataset-20261003-001/`, especially
`source-reconciliation.json`, `dataset-manifest.json`, `mapping.json` and
`staging-validation.json`. Resumption requires the original populated source set
and API/engine suffix reconciliation, or an explicit human change of source scope;
use separately owned replacement resources and retain this candidate.

| Boundary | Current assessment |
|---|---|
| F0 Foundation | Complete for the registered foundation scope. |
| F1 Current-day MTA | Complete for selected registered contracts; not universal customer/branch coverage. |
| F2 Temporal MTA | Complete for selected registered 12-day scope with declared Norm0 occurrence-text flaw: 360 strict passes and 12 narrowly qualified report contracts. Norm0 text is not parity. Day 12 peak 3.10 GiB; terminal relational/readback proof passed. No further F2 recovery queue. |
| F3 recovery Stage 1: connection/admission boundary | Accepted at pushed `52f2ff5` (implementation `26158a6`). Retain accepted inventory and admission proof. |
| F3 recovery Stage 2: connected reporting journeys | **Incomplete; paused at `2d0cfde`.** Implemented and verified portions below are not whole-page acceptance. |
| Stage 3: operational reports/logistics | Not opened under the Stage 2 authorization. Reassess after Stage 2. |
| Stage 4: workflows/master data | Not opened, except the completed bounded DBM action validation amendment. Reuse that proof later. |
| Stage 5: combined runtime/MTO/final acceptance | Not opened. Final application acceptance and any 3004 cutover remain outstanding. |

## Stage 2 page ledger

These are the remaining obligations, not parallel work queues. Guided was the active page at the stop. On an explicitly authorized continuation, finish or give an evidenced disposition for one whole page before independent next work. A recorded blocker permits independent progress; it does **not** make that page complete or remove its required exits. An untested feasible check is not an external blocker.

| Page / journey | Implemented or verified at checkpoint | Remaining acceptance / disposition |
|---|---|---|
| RRR | SQL/read/export proofs retained; layout save/reset/reload/restart and full saved-layout CSV proved. | Real leaf actor, residual controls and matched performance. Inherited screen has no wired history entry: retain exact source disposition. Partial, not accepted. |
| DBM current / daily history | June 17 current Suggestions = 0; positive Apply/Sleep, own-next-day effects and restoration proved in owned trials; Product/Location controls repaired and proved. | Downloaded XLSX, remaining positive controls/scopes, real actor coverage and matched performance. Reuse consumed trial receipts; never reset trials. Partial, not accepted. |
| BTR | Both branches, selective reads/CSV, authenticated gateway/restart, browser views/paging/Depo/horizon/history/layout save/reset and both toolbar files proved. Delayed tab-return restore passes. | Inherited fresh-reload hook fails; disposition required. Residual controls, leaf actor and matched performance remain. Partial, not accepted. |
| Buffer Trends | 134 exact graph responses and 30 declared failures; gateway/restart and type/horizon/summary/Depo/reset/reload controls proved. | Inherited doubled Total / stale Percentage behavior needs exact disposition; residual controls, leaf actor and matched performance remain. Partial, not accepted. |
| Planning categories | Overview proof retained; user explicitly verified exports working and directed deferral. Normal To Child grid rendered 7 dispatch rows, filter/selection and selected-run controls proved. | Custom NMS identity provenance/disposition; canonical child SQL and filtered-count wire proof; residual controls, leaf actor and matched performance. Empty request input does not prove request workflows. User-directed deferred, not accepted. |
| BPR | Read batch deployed at `88c434d`: filtering/count/grid/CSV/analytics/history/configuration; authenticated graph/filter/layout/paging proof retained. | Independent 52-case grid/count/analytics/export and CSV-cell comparisons; actual browser CSV receipt; leaf actor; matched performance; deferred drag/resize/split/multiselect/filter/historical/concurrency controls; inherited Reset Layout ordering disposition. Partial, not accepted. |
| Guided | Read batch deployed at `2d0cfde`; 578 independent consumer comparisons; approved 12-day/770-row history published; all 11 authenticated routes returned 200. Availability Trend rendered six location types; legend hide/restore proved. | Five-tab controls, horizons/ageing, chart/table/legends, Chronic grid/filter/layout/paging/downloads, DBM panels/link, Excess dual horizons; gateway value/wire comparisons; real leaf actor; persisted-layout/restart interactions; configured query-count and unaffected-route overhead diagnostic; matched API/browser performance. Inherited ageing/stale Excess horizon remains source-mapped, not waived. Partial, paused. |
| Research Insights | Existing native history/BPR evidence may be reused. Not opened in the Guided batch. | Whole-page selection→summary/calendar/ageing, graph/grid/date/horizon/filter/config/layout/export contract and proof, scope/restart/performance. Not accepted or covered by Guided. |

All required gaps remain in the Stage 2 denominator. Stage 2 closes only when required exits are proved or the human explicitly approves a narrow scope disposition. SQL/provider recovery makes formerly blocked comparisons feasible again; the old 18456/823 outage is not a continuing excuse to omit them.

## Serving checkpoint and approved inputs

The following identity is the recorded safe-stop state, not a perpetual health claim:

- Preview: `localhost:3005`; no 3004 cutover. Only MTA was recreated at the checkpoint.
- MTA image: `sha256:526ebe525ca7ea1b4c90e7fd475d3dc1eec6166a40161983477a117f7b302da8`.
- Container: `a7a583ea16a86197fe507013927db9df859b13574f25257b129b4fc5a922e9e8`.
- Selected run: `ac1612c8-0e49-4155-83c3-f59f41422293`; business date: `2026-06-17`.
- Output digest: `bd1c522f3df299d2fc3841aed7f66d48e4307e6967450b2d8a5463dc7867d33d`.
- Startup admission: `34a99fa5de6f70c2e7384283d083f6011558ac92c5927e627f4fd322d97044a7`.
- Normal current Suggestions = 0; normal actions disabled. Limit 4 GiB / 2 CPU, two workers, 180-second timeout, restart=no; MTA has no separate host port.
- Build/gateway/SQL comparison jobs ended and owned exclusive leases exited. Retain `test_freshvcf_guided_history_20261003_002`; no cleanup/reset is implied.

Approved supplements are exact, bounded exceptions. Missing input otherwise means unavailable, not empty:

| Input / exception | Allowed scope |
|---|---|
| Retained hierarchy | Exact approved 200-SKU/20-location catalogue, hierarchy and scopes; versioned read-time SL1–3/LL1–3 supplement bound to approved run/date/digest/catalogue. No F2 modification or invented hierarchy. |
| Empty transit and initial BPR remarks | Exact June 17 terminal supplement only, bound to complete retained shipment ledger and audit/input identities. No positive logistics or other-date transfer. |
| DBM positive trials | Separately owned retained pre-action scenarios, genuine run/date/actions and own predecessors. Apply/Sleep and restoration evidence is retained; no standing trial mode or permission reassignment. Any future authorized trial must stop action access and prove normal admission/date/Suggestions0/actions-disabled/gateway restoration on success, failure or interruption. |
| Empty initial OpenExpediteRequests | Human approval `call_zbzXQ93n4Qfs9tOGAixne3Lc`, selected June 17 preview only. No historical-empty claim or request writes. |
| Excess preview history | Human approval `call_bEZzSUkIR32TJ5lhNiuxhyFI`; empty pre-June 6 opening ONLY for this preview; June 6–17 own-output projections, 770 typed rows. Not proof of empty legacy history or a general rolling publication lifecycle. |

Excess input: `D:/freshvcf-build/inputs/excess-history-input-v1.json`, SHA256 `f7a03468227d2b5ef97fc28fec951ec8f373852ed906c9754d50269b75b84154`. Atomic publication/retry preserved accepted run metadata and existing projections. No engine replay or copying calculated legacy output into modern state occurred. General next-day publication/retention lifecycle remains a later architectural obligation, not an extra recovery platform to build during the paused page batch.

## Next bounded task — preparation, not execution authorization

The four-page dataset availability exit is accepted as recorded above; broader page implementation remains paused. Before a separately authorized whole-page continuation:

1. Reuse the retained page inventory and above residual ledger. Identify only missing page inputs/scenarios; do not repeat a full discovery programme.
2. Prefer the existing approved catalogue/population and retained history/trials. Define a finite fixture manifest covering required positive, empty, NULL, scoped and historical UI branches. Record exact missing facts and ownership before any loading.
3. Map the same logical consumer inputs to legacy MSSQL and modern PostgreSQL using their actual contracts. Confirm dataset/date/scope and restore boundaries. Do not assume identical physical schemas, overwrite accepted serving state, reset consumed trials, or create fake accepted calculation runs.
4. Separate claims: common consumer fixtures can prove API/UI contract compatibility. They cannot establish independent engine calculation parity. Calculated-state acceptance still requires each engine's own inputs, predecessor and outputs. Preserve F1/F2 proof untouched.
5. Deliver one complete page package with one consolidated affected QA pass, then record its result here. Retry only failed or changed behavior. No per-click delivery cycle, generic fixture/history framework or unbounded replay programme.

A small UI fixture does not satisfy whole-population performance or permission coverage. The separately stopped legacy date-alignment replay is not an instruction to resume it; retain its partial evidence and establish oracle availability before any new comparisons. SKU 6061's prior screenshot discrepancy was pagination/filter coverage, not proof that the catalogue identity was missing.

## Acceptance and engineering boundaries

- Preserve canonical NULLs, duplicate multiplicity/order, types, envelopes, filters, permissions and calculation semantics. No legacy repairs, guessed defaults, hidden fields, count-only parity or unsupported exclusions. Use `docs/LEGACY_EXCEPTIONS.md` for attributable, narrowly scoped flaws.
- Preserve accepted F1/F2 rows, frozen inputs/actions/SQL/comparisons/receipts. Reuse accepted evidence unless a relevant change invalidates it. Exact earlier approvals do not transfer to different runs, populations or workflows automatically.
- Existing frontend/auth/MTO business contracts remain the target. Retain explicitly approved fixes; no further redesign or permission changes implied. Actor-owned layout writes are distinct from immutable publication and business actions.
- Keep read queries tied to the actual page contract; scope/filter/count/order/page at the relational boundary where semantics permit. Preserve startup admission, run/digest/projection/config binding and full command integrity. No blanket cache, framework or speculative schema. Any schema change needs Django check, migration check/plan and migration-enabled PostgreSQL proof.
- Measure the configured request path when diagnosing repeated verification work. Consolidate demonstrably redundant reads without dropping integrity. The Guided diagnostic covers Excess and one unaffected route; it does not authorize a general admission redesign.
- Performance compares equivalent independently retained legacy/Fresh input/date/population, scope/hierarchy, request/filter/page/columns/export/output and resources. Protocol: 5 warmups, 30 interleaved warm samples, 5 application-cold repetitions, concurrency 1/4; retain raw failures, median, p95 and throughput. Fresh median/p95 no worse, throughput at least equal, errors no worse. Require affected API and browser journey proof. Missing comparable provider or inconclusive evidence stays UNPROVED. No arbitrary threshold, reduced population, shared cache flush or calculation replay just for benchmarks.
- Protect 3002/3003/3004, other tasks, live databases and shared infrastructure. `F:/vflow_integrated` is read-only reuse; `F:/new_vflow` excluded. No serving reset/repopulation, new public port, resource increase, shared Docker/WSL restart/prune or borrowed test database. SQL replay uses verified unique owned `VFTEST_Fresh_*` databases and the exclusive oracle lease; never bypass a verified owner.
- Stage 2 excludes BOR/supplier families, positive logistics, MDM, remarks, expediting/due-date writes and other Stage 3/4 workflows. DBM's exact amendment is the exception, not authority to open those workflows. MTO regression/final deployment and 3004 cutover remain later gates with explicit coordination.

## Evidence and supporting contracts

Read the relevant pointer, not the whole historical tracker. Evidence is external; this file keeps conclusions and open exits.

| Evidence / document | Purpose and limits |
|---|---|
| `D:/freshvcf-build/evidence/f2-runtime-memory-full-011/execution.json`, `terminal-readback.json`; `f2-runtime-memory-sql-full-011/replay.json` | Retained F2 terminal execution, relational readback and independent oracle evidence; qualifications remain. |
| `D:/freshvcf-build/evidence/f3-stage1-admission-002/receipt.json` | Accepted Stage 1 admission. |
| `D:/freshvcf-build/evidence/f3-stage2-guided-batch-001` | Guided checkpoint evidence described below. |
| [Archived tracker](archive/MIGRATION_2026-10-03_2d0cfde.md) | Earlier per-page receipt paths, exact approval context and preserved failures. Historical only. |
| [Page delivery contract](audit-2026-10-01/PAGE_DELIVERY_CONTRACT.md) and [interaction inventory](audit-2026-10-01/PAGE_INTERACTION_INVENTORY.csv) | Whole-page delivery method and static route/API/background candidates; inventory is not dynamic interaction proof or another queue. |
| [BPR contract](audit-2026-10-01/BPR_PAGE_CONTRACT.md), [Guided contract](audit-2026-10-01/GUIDED_PAGE_CONTRACT.md) | Specific source/request/producer contracts; current status comes from this file. |
| [Recovery plan](audit-2026-10-01/RECOVERY_PLAN.md), [earlier Stage 2 plan](audit-2026-10-01/STAGE_2_COMPLETION_PLAN.md), [audit](audit-2026-10-01/AUDIT.md) | Supporting scope/dependency references. Old sequencing, authorization and status statements are historical. Stages 3–5 require reassessment after Stage 2. |

Guided evidence: `filtered-scoped-comparison.json` has 468 independent cases; `excess-trend-comparison.json` has 110; these are **578 consumer comparisons, not UI interactions**. `excess-history-comparison-001/receipt.json` covers 12 own-output/770-row comparisons. `history-publication.json` and `history-postgres-tests-003.txt` prove atomic/readback/idempotent retry and six transaction/producer tests. Earlier failed attempts remain preserved.

`unit-suite-final.txt`: 270 tests, 268 passed; two pre-existing Expedite fixture failures (503 vs 200) remain: `test_expedite_chart_native_scope_and_source_flaw_unavailable` and `test_expedite_count_direction_and_unavailable_detail_contract`. Do not report the suite green. Baseline verification retained 376 pinned resources unchanged.

`build.txt` and startup admission establish the deployed checkpoint. `guided-gateway.json` records authenticated HTTP 200 twice for all 11 Guided routes plus BPR count, with complete bodies; it is not independent value comparison. Observed modern-only Excess 2.80–3.06s and BPR count 0.82–0.87s are not matched performance acceptance. `browser-handoff.png` proves only the bounded browser observations in the page ledger.

## How this tracker is maintained

Update current rows in place at a logical page exit or meaningful blocker change. Keep the active page, remaining exit, permitted boundary and required proof explicit before mutation. Record a concise result and evidence pointer; keep commands, test transcripts and incident chronology outside this tracker. Commit/push coherent checkpoints, not every probe. Never mark the overall goal complete while required exits remain. Do not resume the paused executor merely to acknowledge this baseline.
