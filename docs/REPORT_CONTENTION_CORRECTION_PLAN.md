# Bounded 3005 report contention correction

Authorized by the human in the successor control chat on 4 October 2026.
Implementation owner: `01a10098-1a4b-7e03-a9d3-77542504632b`.
This is an implementation contract, not a status tracker. Only
`docs/MIGRATION.md` records execution status.

## Handoff assessment and objective

The login/profile assignment is complete at pushed `fe8ad13`. Retain its local
validated catalogue, live grants, fail-closed selection and profile-loading fix,
plus the preceding streaming gateway. Its receipt records 72 successful profile
requests, maximum 2.427s, and fresh login in 2.495s while nine reports remained
outstanding. This is accepted for that bounded identity exit, not report speed.

The same burst produced 504s at approximately 60s for GetBPRData, GetBTRData,
DBMData, DBMDataCount and ChronicUnavailabilityLoc. RRRData completed in 46.57s;
count requests completed progressively at 5.92, 14.52 and 26.31s. A subsequent
aborted-read diagnostic also received a BTR 504. Gateway/MTA sampled peaks were
119.95/719.02 MiB, with no OOM. These observations support contention and excessive
request work; they do not isolate SQL, Python, serialization or queue time as the
sole cause. A 504 does not prove upstream work stopped.

Implement the smallest measured, non-semantic report-read corrections that let
the existing four grid/count pairs plus the existing Chronic request complete
under the unchanged public 60-second limit, with full retained data and continued
responsive login/profile. Deploy, verify, commit/push and stop for review.
This supersedes the report-tuning pause only for this contract. General Stage 2
page completion and Stages 3–5 remain paused.

## Fixed population and permitted boundary

- Start from fe8ad13 and the serving April 7 VM fixture
  `stage2-vm-dataset-20261003-002`, partition
  `bfd75b4b-a9df-4a08-82d3-852e3324b623`. Reuse frozen source/consumer receipts.
- Routes: RRRData/RRRDataCount, GetBPRData/GetBPRDataCount,
  GetBTRData/GetBTRDataCount, DBMData/DBMDataCount, and ChronicUnavailabilityLoc.
  Retain probe payloads: RRR/BTR/DBM page size 5000, BPR 50, existing filters,
  `name=both`, and Chronic `{}`. Cover both BTR branches in affected regressions.
- Allowed: targeted PostgreSQL query shape/index corrections, selective loading,
  measured redundant reconstruction or serialization removal, and bounded
  request/resource-lifetime corrections on those paths. Existing Chronic read
  performance is included because it is part of the observed contention; no
  completion of Guided business behavior or other Guided routes is authorized.
- Frontend changes only for measured redundant requests or abandoned-request
  cleanup in these journeys; preserve endpoints, payloads, counts, fields and
  navigation behavior. Do not serialize or suppress the acceptance burst to hide
  insufficient server capacity. Do not replace failures with empty/partial success.
- Keep normal publication behavior and full command integrity. If a shared helper
  changes, prove its affected normal path too. Do not unify fixture and production
  readers speculatively or build a new serving/storage framework.
- Necessary isolated 3005 MTA/gateway/frontend build/deploy/restart is authorized
  for this correction with exact rollback identities. Preserve catalogue selection
  coordination. No other service replacement, new port or 3004 cutover.

## Execution sequence

1. Record the active item and unmet exit in MIGRATION.md. Reuse the retained
   handoff/evidence; do not repeat dataset discovery or imports. Capture the
   checkpoint and current selection/resources before mutation.
2. Use one bounded baseline to attribute elapsed time: individual routes, each
   grid/count pair, the eight-request burst, then the nine-request burst. Correlate
   gateway arrival, MTA execution, database work, Python reconstruction,
   serialization/transfer and completion where observable. Label unobservable
   queue components rather than guessing. Measure DB activity/locks and worker
   occupancy; inspect relevant EXPLAIN plans on owned resources. Account for work
   remaining after 504/disconnect before starting another sample. Do not count
   an abort after a 504 as successful cancellation proof.
3. Correct the dominant evidenced bottleneck first. Preserve SQL comparison/NULL
   semantics, duplicate multiplicity, source order, existing RRR tie disposition,
   numeric/date types, scope/filter/count/page behavior and response envelopes.
   Add only justified owned indexes; schema changes require Django check,
   makemigrations --check, migration plan and migration-enabled PostgreSQL proof.
   No edits to canonical legacy SQL or calculation semantics.
4. Verify affected complete responses against retained successful baselines and
   independent/reference readers, not the old 504 body. Obtain any missing
   successful Chronic baseline in isolation. Preserve existing source flaws; if
   exact successful behavior cannot be established, record a blocker rather than
   inventing a response. Compare full rows/fields/NULLs/duplicates/order, counts,
   types, envelopes, restricted scopes, denials and affected downloads. No weakened
   assertions, field exclusions or count-only equality.
5. Deploy the verified candidate, run the consolidated acceptance pass below,
   update the tracker and operational handoff, commit/push and stop. Retry only
   failed or changed proof. Do not create another recovery programme.

## Acceptance and honest stop conditions

- All nine requests return their complete expected successful responses within
  the unchanged public deadline in three consecutive retained overlap bursts.
  Also pass the eight-request burst and repeated four-page navigation. Preserve
  all failures and timings; establish drained/quiescent work between independent
  bursts without restarting services or flushing caches to manufacture a pass.
- Record before/after individual and paired route timings and burst completion,
  queue/service breakdown where observable, bytes, gateway/MTA CPU and memory,
  database activity and error counts. Show that the diagnosed bottleneck improved;
  no unexplained material regression may be concealed behind passing the timeout.
  These finite diagnostic runs are not formal matched-legacy median/p95 acceptance;
  the broader performance contract remains open.
- Fresh real login and profile complete while reports are outstanding. Retain
  identity, scope, forged-scope/unauthenticated denial, disabled-action and
  normal-versus-fixture checks affected by the change. Do not regress fe8ad13.
- Browser: all four populated pages, filters/count/grid consistency, navigation
  away with requests pending, return and profile completion. Verify abandoned or
  timed-out work releases resources or demonstrably drains without poisoning
  subsequent requests. No request-lifetime claim without observation.
- Fixed limits: gateway 1 GiB; MTA 4 GiB/2 CPU/two workers; current PostgreSQL
  allocation; existing timeouts and restart=no. No memory/CPU/worker/timeout
  increases, reduced population/page size/fields, blanket cache, new worker pool,
  background report-job system, broad storage redesign or admission weakening.
- Preserve F1/F2 engines, accepted state, frozen artifacts/actions/SQL/receipts,
  fixture immutability, grants, credentials, MTO and protected 3002/3003/3004.
  No replay, dataset reload/reset, shared infrastructure restart/prune or borrowed
  test resources. Raw evidence stays under D:/freshvcf-build/evidence.
- Verify startup/restart/readiness, selected publication/catalogue, exact running
  images, resource settings, protected state and coordinated rollback consistency.
  Hand off one consolidated PASS or precise unmet exit with evidence, deployed
  source/image identities, remaining limitations and rollback instructions.

If passing requires a business-rule/response-contract change, new materialized
state, broad storage redesign or extra capacity, stop with measured evidence and
the concrete decision needed. Do not claim success by excluding Chronic, accepting
504s or silently lowering load. A blocker does not close the larger migration.
