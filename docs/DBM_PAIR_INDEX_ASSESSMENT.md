# DBM pair-index assessment — recommend neither

11 October 2026. Read-only assessment of I2 DBMMaster and I3 SkuLocAttributeData.
Neither has sufficient demonstrated endpoint benefit to justify a trial now.
I3 ranks above I2 on observed restricted lookup cost, but neither has a proven
access-path win. No index, ANALYZE, migration, source, service or settings change
was made. BPR I1 remains rejected and MDM remains paused.

## Actual boundary and requests

Container freshvcf-preview-mta-1; image
sha256:f94d47c65a0f68bc3a4614e4821d68c35c42a15b28d42c477c4ab0e57949862e;
database test_freshvcf_stage2_vm_20261003_002; fixture
bfd75b4b-a9df-4a08-82d3-852e3324b623; source binding
4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73.
Live dispatch is LEGACY_UI_FIXTURE without commands → grid_state, confirmed by
actual captured pair queries. Reader hashes are in binding.json. The live
`dbm_read.py` hash differs from checkout bytes only in line endings (no text diff);
`dbm_fixture_read.py` and `views.py` hashes match exactly. No dirty code was deployed.

Three cases, each page1/5000: existing broad actor, existing restricted actor,
and broad actor with SKU21101119001000. That identity is retained in the prior
3005 DBMData response under 3005-report-contention-20261004-001/after-individual;
its existing productFilter contract was used without changing grants. Exact
actor permission arrays and payloads are retained externally. One decorated
endpoint execution with SQL timing wrapper plus two live private HTTP requests
per case =9 normal requests total. Both use the existing trusted-gateway actor
contract and fixture actor/scope validation; there is no mocked scope.

Four additional actual EXPLAIN ANALYZE/BUFFERS executions are explicitly separate:
broad and selective × each candidate table, once each. They do not count as normal
HTTP observations and are not hidden warmups. Plans follow normal requests.
60s statements/HTTP deadlines; read-only assessment connection; no forced planner,
cache flush, restart, warmup or favorable rerun. The three broad normal requests
finished before a probe matcher assertion failed: it expected a quoted schema
but the real SQL uses mta_state."table". SQL timings were saved; broad wall-time,
assembly and response-hash fields were lost before persistence. Broad requests
were NOT repeated. Original script/failure and corrected remaining-case script
are retained. This limits broad endpoint attribution and precludes a controlled
performance claim.

## Measured costs

Execute-wrapper durations include driver execution/transfer, exclude later
fetch/decoding and Python work. They are one instrumented sample per case, not
three SQL medians. Remaining normal observations are actual HTTP wall times.

| Case | Pairs per table / parameters | I2 SQL s | I3 SQL s | Suggestions s | Metadata s | Other SQL s | In-process endpoint s | Private HTTP s (two) |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Broad | 11158 /22318 |1.4968|1.3684|0.2543|0.0305|0.6126|unavailable|unavailable|
| Restricted |1036 /2074|0.1095|0.1949|0.0207|0.0310|0.1061|1.5608|1.9934,2.5852|
| SKU filter (2 displayed rows) |11158 /22318|0.2280|0.4253|0.0146|0.0363|0.2105|2.3736|2.7952,2.9102|

All candidate requests have zero nullable-pair branches; this does not prove a
NULL-pair case. The existing exact None semantics are unchanged. No single-pair
surrogate query was used. Restricted responses contain1036 rows; filtered
responses contain2. For each of those cases, the decorated endpoint and both
live HTTP bodies matched exactly. No new full parity campaign was run.

Restricted: context loading1.3457s (all SQL0.4622s), Python row/filter assembly
0.1839s, JSON envelope serialization0.0165s. Filtered: context1.8157s (all SQL
0.9145s), row/filter assembly0.5425s, JSON envelope0.0002s. Context residual includes
fetching, typed conversion, scope resolution and Python work; it is not pure SQL.
Other unallocated request time is retained rather than assigned speculatively.
HTTP timings exclude public gateway/browser/grid and cannot certify UI speed.

Even eliminating the ENTIRE candidate execute cost gives these optimistic ceilings
against the instrumented endpoint: restricted I2=7.02%, I3=12.49%; filtered I2=9.60%,
I3=17.92%. Indexes cannot eliminate all that work or accelerate the remaining
assembly/serialization. Broad ceiling cannot be computed because its denominator
was lost. Do not substitute another case's wall time or infer it from SQL totals.

## Actual plan evidence and decision

| Case/table | Execution / planning ms | Actual access path | Source rows | Shared hit/read blocks |
|---|---:|---|---:|---:|
| Broad I2 |75.871 /17.283|sequential scan → hash semi-join → ordinal quicksort|97097|2149 /0|
| Broad I3 |492.757 /27.691|parallel scan → hash semi-join → quicksort/Gather Merge|97097 total|2154 /0|
| Filtered I2 |58.018 /14.748|sequential scan → hash semi-join → ordinal quicksort|97097|2146 /0|
| Filtered I3 |166.654 /10.723|parallel scan → hash semi-join → quicksort/Gather Merge|97097 total|2154 /0|

Both actual joins emit11158 rows (11.49% of source); scan filters remove0 rows
because run/image select this owned population. Nonmatching pairs are excluded
by the join, not reported as scan-filter removals. I2 scan itself took24.713ms
broad and18.046ms filtered. I3 per-worker scan took23.905ms broad and10.000ms
filtered. Parallel node timings are not additive. Buffers are already hits;
there is no demonstrated disk-read bottleneck. Cold/order/scheduling variation
between normal executes and later plans is substantial and preserved.

The SKU filter is applied in dbm_filtered AFTER grid_state. It does not reduce
pair loading: broad and filtered query pair sets contain11158 identities each.
An index would still fetch required payload fields and restore global vf_ordinal
order across many pairs; its trailing ordinal is not a guarantee of sort removal.
Both tables currently have only the owner/image/ordinal primary key. Missing a
pair index alone does not demonstrate an endpoint bottleneck or prove a better
plan. An added five-column B-tree would have97097 entries, consume cache/disk/WAL
and increase preparation/write work. Exact index bytes/build cost are unmeasured;
no optimistic storage estimate is presented as fact.

Recommend NEITHER now. I3 has higher observed selective/restricted SQL share, but
the selective UI request is not a selective database lookup, the broad plan can
legitimately prefer a scan, and the restricted ceiling is modest. I2's measured
ceiling is smaller. A before/after index trial would be needed to prove any
benefit; this assessment does not authorize it or guarantee improvement. No
follow-up trial request is proposed on the current evidence. No query rewrite
or broader bottleneck investigation is included.

## Evidence and closure

D:/freshvcf-build/evidence/dbm-pair-index-assessment-20261011-001 contains scripts,
all actual SQL and parameters, payloads,4 plans, preserved failure, timing records,
source/index binding and manifest.json with SHA256 for every evidence file.
The final fixture binding is unchanged. The only persistent repository changes
are this assessment and its MIGRATION entry. No schema tests/migration are
applicable. Stop at this qualified assessment; no DBM implementation resumes.
