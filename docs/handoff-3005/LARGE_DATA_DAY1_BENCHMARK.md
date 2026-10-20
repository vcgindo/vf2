# Large-data fresh-start benchmark — measured result

20 October 2026. Status: **cohesive backend scalability correction implemented; new-image large-day verification pending**. The sole status authority is `F:/freshvcf/docs/handoff-3005/TRACKER.md`.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

## Authorized engineering correction

Human instruction "set goal and implement this" releases one cohesive correction,
not a new historical-parity or optimization programme. Ordered lookup groups
replace full-population scans in master/daily, route/allocation and expedite
joins. SQL NULL exclusion, duplicate matches, source order, ambiguity checks and
business formulas are retained. Immutable opening reconstruction, family
projections and hashes are reused only within an explicit identity-bound
operation, with expensive sealed-input work before the write transaction.
Live owners/queues/tasks and all atomic commit/integrity checks remain active.

CSV intake reads files individually and streams the exact existing canonical
native envelope to its archived file. The parser hashes the same descriptor it
decodes. Complete validation errors use disk-backed records. BOR/BOROA source
preparation, Planning contribution checksums and typed export readback are
streamed/batched. CSV opening ownership transfer removes one redundant graph
copy while retaining isolated mutable snapshots. Lost-session reporting writes
an explicit reconciliation-required filesystem receipt without inventing a
database failure status or automatically retrying a business day.

The consolidated affected run passed 178 tests (one pre-existing optional
integration skip), including large CSV/typed threshold and eager/streamed
equivalence checks. Additional focused native-family batching checks also pass.
Two source-only CLI
tests needed their existing release-identity dependency mocked explicitly;
production independent release pins remain mandatory. Independent source review
identified the hash/parse descriptor gap, which was corrected and given a
regression test. Indexed joins passed 1,148 old/new result-or-error comparisons.
These are source proofs, not successful large-case execution timings.

Residual limits: current-master/native validator contracts still require
materialized lists, JSON decoding still constructs its input text and graph,
and typed persistence throughput/capacity is not established for arbitrary
future volumes. No timeout or resource increase is introduced. Native phase
logs distinguish input capture, calculation, atomic commit and reporting; no
guessed overhead subtraction or linear extrapolation is allowed.

### Complete capture-path follow-up

The first corrected image completed full initialization in 2,527.618 seconds
(peak process RSS 3,538,034,688 bytes) and daily CSV admission in 454.776 seconds
(peak RSS 1,494,384,640 bytes). Its ordinary execution then reached native
preflight/bootstrap in 514.543 seconds but again lost the PostgreSQL session to
the unchanged 300-second idle-in-transaction limit. The exact worker was stopped
after that observed database failure; it was not OOM. Read-only reconciliation
found one initialization and zero calculation runs or captures. This is not a
completed-day result.

The remaining capture composition performed full attribute scans per master.
Ordered key indexes now preserve lazy ambiguity checks, exact duplicate values,
NULL behavior and source order. Stable full-row DISTINCT preserves first
occurrences. Supplier location/description joins also use ordered indexes.
Validated source references are retained instead of another cleaned row image.
Complete root comparison/copying is prepared before the transaction and bound
to the refreshed locked initialization/source seal; live admission still runs
inside the snapshot. Family overlays share one hash of the actual unmodified
working state, complete live owner rows compare incrementally, and capture
models are constructed in batches of 500. No timeout, formula, input, schema,
frontend or MTO change is included.

The affected consolidated suite passed 225 tests with one existing optional
integration skip; focused follow-up passed 56 tests. Legacy component test
mocks were updated for the existing typed-production input and server cursor
contracts, retaining their producer/consumption/carry assertions. Differential
tests compare complete old/new composition outcomes or exact errors, including
NULLs, duplicates, normalized codes and unused ambiguous keys. Scan-count tests
show linear indexed lookup growth rather than per-master population scans.
New packaged full-day verification remains pending; these checks do not prove
arbitrary future capacity or a completed performance benchmark.

### Capture passed; original description text admitted explicitly

Image `af2b7f1c…`/source `a90abded…` completed initialization in 2,621.196
seconds and daily CSV admission in 441.915 seconds. Native preflight/bootstrap
took 468.033 seconds; input capture then committed in 1,268.071 seconds without
the previous transaction timeout. Run `aba1c902-f8fd-465b-8384-1375adae7fcc`
subsequently failed at the Importer text validator, before successful calculation
or report preparation. It retains a typed CAPTURED input and FAILED status;
no accepted day is claimed. Worker Exit1/nonOOM/guard-null was recorded and its
container removed.

The original catalogue has 161 descriptions containing U+00A0 (non-breaking
space), U+00AE (registered sign), or U+2013 (en dash). A read-only scan of all
1,692,304 text-bearing CSV rows found these only in SKU-description populations.
Actual source metadata is `varchar(125)` with
`SQL_Latin1_General_CP1_CI_AS`. All 2,568 actual/edge equality groups match the
unchanged comparison function. No characters are replaced or trimmed differently.

The human approved exact decision packet SHA256
`6c47632737b0d9f97b82bf8af020ecc73e4935c31edcf4355462dca0da73e539`.
Only those three characters gain admission in the existing bounded description
fields. Identifiers/custom fields remain ASCII, other Unicode remains rejected,
and formulas/NULL/duplicates/order/ambiguity rules stay unchanged. The quick
applied-code smoke passed all 2,189 actual descriptions and complete small
native BPR/DBM/Pick/BTR flows for each character in 1.956 seconds. All 56 focused
regression checks passed. This is source/component proof; the new packaged
image and same single-day benchmark still require actual verification.

## Workload

The requested case contains **97,097 distinct SKU/location master pairs**, 2,189 SKUs and 235 catalogue locations. One unused untyped catalogue location is excluded from the calculation configuration, which contains 234 locations. The opening is 7 April 2026; the single synthetic CSV business date is 8 April. There is **no imported historical BPR, DBM or BTR population**. The 10,256 outstanding orders are current opening facts.

The daily CSV contains 97,097 rows: 18,788 known-stock and 78,309 NULL-stock rows, with 829 positive-consumption and 590 positive-receipt rows. Native missing-input rules retain ownership of NULL handling. This is not 100,000 fully active transactions. Product and location identities remain text codes; integer-surrogate performance is not implemented or credited.

## Actual measurements

| Boundary | Result | Wall time | CPU / memory |
| --- | --- | ---: | --- |
| CSV master/opening initialization, typed persistence and complete native readback | PASS | 2,088.524 s — 34m 48.5s | 1,326.722 processor-seconds; peak process RSS 4,074,659,840 bytes (3.795 GiB) |
| Daily CSV admission, including opening-state integrity and input validation | PASS | 529.162 s — 8m 49.2s | 513.181 processor-seconds; peak process RSS 2,255,724,544 bytes (2.101 GiB) |
| Ordinary daily execution command | Interrupted after PostgreSQL terminated its connection | 6,971.147 s — 116m 11.1s until controlled stop | Last live cgroup CPU 6,829.005 processor-seconds; observed container peak 4,022,800,384 bytes (3.747 GiB) |
| Completed calculation, typed closing state, report preparation/publication and usable UI | **Not reached** | No successful timing available | No success or throughput claim |

The daily execution CPU/memory observation was taken at 01:20:35.688 UTC, immediately before stopping the worker. It is not a terminal process-RSS measurement. The worker had no CPU/RAM ceiling and no recorded CPU throttling. The existing Docker VM has approximately 15.46 GiB and 16 logical CPUs; PostgreSQL shares that VM with existing services. No resource leveling or capacity increase was introduced.

These timings exclude image building, fixture preparation, development tests and the legacy run. They include the ordinary repository command's internal validation. The execution command also owns capture, calculation, persistence and existing reporting; its elapsed time must not be labelled pure calculation time. No guessed overhead is subtracted and no linear scaling estimate is made.

## Verified outcome and blocker

The final source correction preserves all declared current-master list contracts and current open orders through CSV admission and typed reconstruction. All 47 affected initialization/scalar/packaging tests passed. Actual full-scale initialization and daily admission then passed, including full native opening readback; this is more than a row-count check.

At 01:19:44.339 UTC, PostgreSQL logged termination of the benchmark connection for the database-scoped **300-second idle-in-transaction timeout**. The sole benchmark backend disappeared while the Python worker remained CPU-active. Its observed SQL activity had repeatedly read opening and master integrity data. Static source confirms that `production_families._opening_input` and `_verified_initialization` use `once_per_request`; that decorator explicitly leaves offline callers uncached. Several daily entry paths invoke those checks. This identifies repeated reconstruction/validation as a concrete performance concern; no profiler-derived attribution to one function or pure-math timing is claimed.

The exact owned worker was stopped after that database-session failure. It exited 137 because of the controlled stop, **not OOM**. The 120-minute command guard had not fired. No timeout was relaxed, no calculation was retried, and no second day was attempted.

Read-only reconciliation after stopping proves:

- One source and one successful initialization; 97,097 master rows and 97,097 distinct pairs.
- Zero committed calculation runs, daily captures or publications; zero imported BPR/DBM/BTR history rows.
- No other client transaction in the benchmark database.
- The CSV attempt remains `RUNNING / CALCULATE`, with no run ID, because the process was interrupted. This is retained interrupted metadata, not an accepted day or an automatic retry instruction.

The initialized database is 1,139,891,223 bytes. The outstanding acceptance is a successful ordinary daily run, closing state, existing native reports and original UI. The large-scale validation/transaction-lifetime problem must be resolved before claiming that acceptance. There is no historical-parity, completed-day performance or public-deployment claim.

## Source, case and cleanup

- Branch: `codex/3006-logistics-integration`.
- Tested code commit: `a2784e30a6e351877efb1f4aa4456d90e157687e`, committed and pushed.
- Image: `sha256:c1ba11fa6dcdf9e19c0b5384851a83ac733aeb7002b3ed295b4b2eb03fea10c7`.
- Opening input SHA256: `27b3893b0f8a0f0db0197439c760677e9dc6dca07ad00f26fc4297781dd57a70`.
- Opening CSV manifest SHA256: `889e2021cca5d0665718a7bf827673c7995d47443489c05c50aefd6d9ec61489`.
- Frozen first-day input SHA256: `30ddb9bd8c4ddbc51ffd743d23c4c8d5ef0146416baf37cfa58e9580899a41bc`.
- Current database: `vectorflow_mta_perf_final_20261020`, OID 50303; opening `aceac0a6-b461-4677-ad72-51476349511f`.
- Reusable CSV case: `I:/VectorFLOW-benchmark-20261020/fresh-start`.
- Final measurements: `D:/freshvcf-build/evidence/large-data-day1-benchmark-20261019/modern-fresh-performance/final-result.json`.

All completed/failed benchmark command containers have been removed. Obsolete benchmark image versions and owned abandoned build containers were removed; future MTA builds remove intermediate containers automatically. The superseded benchmark database `vectorflow_mta_perf_20261020` was ownership/fingerprint checked and deleted, with zero runs/captures/publications. Only the current image and successfully initialized case remain for the unresolved benchmark; duplicate failed versions are not retained in Docker.

The original `vectorflow_mta` installation database remains untouched. All six 3005 container IDs, images, start times and states match the pre-benchmark snapshot; the four large source SQL databases remain ONLINE/READ_ONLY. Frontend, MTO and auth were not changed. No browser testing occurred because daily results were unavailable. No automatic review or extra test campaign was started.

Automatic approval blocked deletion of old host-side build folders/logs/draft input with the reason “blocked by policy”; those files remain. No alternate deletion path was used.

## Retained legacy reference

The corrected legacy result remains a separate full-history, split-phase reference: 1,920.976851 active seconds, excluding customer-source preprocessing. It is not the same fresh-start workload and supplies no modern speedup ratio. No legacy rerun was performed for this fresh-start test.
