# Large-data fresh-start benchmark — measured result

20 October 2026. Status: **blocked before a completed modern daily run**. The sole status authority is `F:/freshvcf/docs/handoff-3005/TRACKER.md`.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

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
