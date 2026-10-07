# Daily execution refinement: evidence and limits

7 October 2026. Implementation `99d4854` is pushed. The user approved qualified
closure in reply to `call_SVuvxiw9ToTlqD50vcsbxKbf`: matched-resource legacy
performance remains UNPROVED; the full run and serving publication stay held.
[MIGRATION.md](MIGRATION.md) is the authoritative status. This report does not
authorize further execution.

## Implementation

`execute_day` remains the atomic production boundary. Production omits diagnostic
stage snapshots and whole-result JSON normalization; validation retains the
complete independent comparison roster. Both modes persist typed inputs, closing
state, ordered report rows, actions, histories and required daily projections.
The operational root binds input and manifest identity. Validation has a separate
trusted digest; retained version-one evidence remains readable.

Migrations 0076–0078 add evidence identity fields, typed input families, command
receipts, exact SOB numeric input storage, and relational export row lengths.
There is no JSONB operational-state substitute. Pick and Fulfillment readers now
verify operational receipts when diagnostic checkpoints are absent. DBM rules2–5
and insufficient-data suppression use bounded ordinal indexes instead of repeated
full-population matching scans. Formulas, ordering, NULLs and duplicates remain.
[Complete-flow coverage](DAILY_EXECUTION_COVERAGE.md) records owners and limits.

## One-sample measurements

Evidence root: `D:/freshvcf-build/refinement/integrated-001/`. Frozen input SHA256:
`ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56`.
June6, 1,240 pairs, 200 SKUs; identical declared initial external facts and profile.
Each worker was limited to4GiB/twoCPU. Modern PostgreSQL was1GiB/oneCPU with no
host ports; legacy used the existing SQL server through its exclusive lease.
SQL server CPU and matched database resources were not measured. Modern and
legacy timing invocations ran sequentially; background container inventory is
retained. No warmup/repetition matrix, actions, external parity, extra export,
report preparation or serving selection is included in these samples.

| Wall seconds | Earlier modern diagnostic boundary | Modern production | Legacy capture boundary |
|---|---:|---:|---:|
| Complete measured boundary |407.433|89.895|180.878|
| DBM bucket |99.808|33.733|18.771|
| BPR/RRR bucket |0.528|0.518|0.960|
| BTR bucket |2.529|1.522|15.439|

Modern production includes typed input persistence18.424s and final persistence/
commit18.692s. Legacy includes import SQL with embedded capture66.532s,
normalization14.962s and SQL snapshot readback14.630s. The modern process peak
RSS was689,618,944 bytes (observed cgroup674,230,272); legacy job peak was
2,441,334,784 bytes. Different memory metrics and database processes must remain
separate. Exclusive scalar timer wrappers, raw buckets and worker receipts are
retained in `timing_probe.py`, `modern-timing.json`, `legacy-timing.json` and
`legacy-timing-worker.json`.

Modern's observed boundary fell77.9% from the earlier diagnostic sample; that is
the combined benefit of removing diagnostic work and refining shared/DBM work,
not an algorithm-only speedup. The old DBM bucket also included residual capture.
Legacy and modern totals have unequal capture/persistence responsibilities and
database resources: no matched end-to-end speed ratio or p95/SLA claim follows.
Modern DBM remains slower than the measured SQL DBM bucket; modern BTR is faster.
Do not infer whole-engine legacy equivalence by adding unlike stage buckets.
The plan's matched-legacy performance objective remains qualified by these limits.

## Correctness evidence

Production run `f6842ba8-f3f3-4012-8be0-e43aea0aa48a` and validation run
`6ad55f99-fb4e-4e7a-8e62-616594030c26` match all515 ordered operational images,
required export metadata/rows and all7 source/projection groups. Normal readers
and typed input/output integrity pass. Independent run/MDM source identities and
lineage differ explicitly; business values are not excluded. Production has no
validation checkpoints. See `mode-equivalence.json`.

Fresh migration-enabled PostgreSQL proof passed19 affected tests, including
rollback, typed reconstruction/tamper denial, frozen MDM retry and incomplete
publication denial (`final-schema-proof.log`). All pinned387 baseline resources
remain unchanged. Focused conversion, archive, policy, source-transition and DBM
differential proofs are retained. This is not a claim that the entire repository
suite is green.

The approved single legacy day3 calculation repair passed all31 comparisons and
independent RRR source proof against retained modern day3. Its own accepted day2
was the predecessor; no modern/accepted day was recalculated. A first full-prefix
comparison exceeded memory; the retained failure was followed by a fresh bounded
day3 comparator that verified accepted-prefix receipts. This did not rerun the
engine. The original failed capture and all source-transition evidence remain.

The new two-day comparator also retained day1 while loading day2 and exceeded
the same memory limit. Its failed receipt remains. A fresh process compares only
day2 using the unchanged comparator body and verified day1 evidence; this is an
orchestration qualification, not a relaxed comparison or engine retry.

The first new validation day1 failed exact input readback because the SOB mapping
lost decimal text precision. That attempt remains FAILED without output rows.
Migration0078 stores the input as numeric without changing canonical BPR float
calculations; successful retry reused the frozen MDM capture.

The separately owned two-day timeline passed all31 comparisons on each day and
both independent RRR SQL source checks. Day1 exercised all8 designated eligible
Sleep identities and Apply for the other120 suggestions. Day2 consumed its own
persisted predecessor/actions and applied its six new suggestions. Modern day2
is `0499c478-0503-4abf-92ad-736a7eb7b0b4`, output
`81d3739acaec8b8d391816ffcdaa3bc468be7c851a7386f34994b4773f1f5e7c`.
Legacy day2 peak was3,116,068,864 bytes; fresh day2 comparison peak was
2,694,619,136 bytes. `comparison-day2-a002/replay.json` preserves the accepted
day1 entry; `rrr-day1.json` and `rrr-day2.json` retain complete source comparisons.
No engine retry was needed for day2. The comparator failure remains evidence.

Terminal preparation is READY for all18 layers of the unchanged approved
`core-without-bor-v1` roster, seal
`d961094ec657a054741fb94bc277b55b3e1bea355deafc684a8ec89e77736d35`.
The first attempt retained16 successful layers; two expedite builders required
RRR preparation that appeared later in the existing roster. Normal retry reused
all16 receipts unchanged and completed only those two layers. The failed attempt
and `terminal-retry-preservation.json` remain. No preparation ordering repair was
introduced into this refinement.

Qualified offline reader checks passed broad/restricted/denied scopes. Broad BPR
and both BTR counts are1,240; the retained restricted hierarchy scope gives133;
empty scope gives0. Native NULL hierarchy denies access without the approved
read-time supplement. BPR uses its normal daily ReadModel and BTR its SQL reader;
the initial probe's fixture-only BPR call was denied and retained in the log.
This proves persisted consumer compatibility, not HTTP admission, login or browser
acceptance. All18 prepared layers were independently reread through their
existing row/seal verifiers. See `terminal-readers-b.json`. No activation or serving
selection was performed. All30 protected container identities/images remained
unchanged (`protected-containers-after.json`).

## Capacity and publication limits

One bounded ordinal-index cardinality proof covers50,000 rows/500 keys, including
100 duplicate matches, with approximately18,946 additional Python heap bytes.
This does not certify million-pair daily execution. Full calculation state and
cross-pair dependency groups remain in memory; ordinary PostgreSQL cursors may
buffer rows natively. Inserts/checksum iteration are bounded, but whole-state
reader APIs still materialize their requested state. No oversized group is
silently truncated and no new parallelism or memory increase was introduced.

The original full21-day run remains held. This refinement does not activate,
select, restart or repopulate any serving instance. The two-day correctness and unselected reader proofs above do not certify
full21-day execution or matched-resource legacy performance.
