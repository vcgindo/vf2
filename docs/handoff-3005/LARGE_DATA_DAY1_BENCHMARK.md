# Large-data fresh-start benchmark

20 October 2026. **The full modern day is not yet accepted.** The routing correction
is committed as `be07a07443df14283152aab4b35dd4de1203d8d4`; the next attempt passed
initialization, CSV validation and input capture, then failed at a downstream
zero-quantity order guard. The human-approved two-check correction is now applied;
64 affected tests pass. Its packaged-image smoke and the approved fresh
source-bound continuation remain required before a large-day success claim.
`F:/freshvcf/docs/handoff-3005/TRACKER.md` is the sole live status authority.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

## Workload and measurement boundary

Latest route-corrected attempt: initialization2,839.033415seconds; CSV
validation434.560216seconds; native preflight/bootstrap502.480926seconds;
input capture1,124.519835seconds. Daily execution stopped after2,213.197469seconds,
including those last two phases, with peak process RSS7,879,434,240bytes and
exit1/non-OOM. The remaining586.196708seconds is time until calculation failure,
not completed calculation time. Run `a4accc28-8af1-40b2-ac66-0b02e8771e8a` is FAILED,
output digest empty, and no other database clients remain. No report/UI acceptance
or whole-day performance conclusion is established.

The zero-order discrepancy is SQL-004 in `SQL_BEHAVIOR_DISCREPANCIES.md`.
Source intake and legacy SQL allow zero outstanding quantities, while two
downstream modern demand checks require strictly positive values.30 applicable
zero orders are present in this population. Candidate tests preserve all ten
existing complete fixture outputs, handle four zero-order flows and retain
eight invalid-input denials. No frozen fact is removed or changed.

Load 97,097 distinct SKU/location combinations once, with their necessary opening
facts and configuration, then run the single synthetic 8 April 2026 day from the
7 April opening. There are 2,189 SKUs and 235 catalogue locations; 234 participate
in the calculation configuration. The 1,692,306 owner/configuration records are
not additional SKU/location combinations or imported daily history. Current open
orders number 10,256. The daily feed has 97,097 rows: 18,788 known stock values,
78,309 NULL stock values, 829 positive consumptions and 590 positive receipts.

No historical BPR/DBM/BTR observations are imported. Text SKU/location identifiers
remain; integer surrogate conversion is not implemented or credited. The input
is a ledger-consistent synthetic next day derived from a read-only 3005 snapshot;
unavailable customer-specific preprocessing is excluded. This is a modern
fresh-start performance test, not a historical-parity campaign.

Measure initialization, daily CSV admission, native preflight/input capture,
calculation/typed commit, existing report preparation/selection and usable
original UI separately. CPU processor-seconds and actual process peak RSS are
reported alongside wall time. Do not subtract guessed overheads, extrapolate
linearly from the small starter case or describe a failed attempt as day timing.
The shared Docker VM is not dedicated benchmark hardware. Compute configuration,
300-second idle/statement and 5-second lock timeouts, 20 GiB physical free-space
reserve and 120-minute per-command failure stop remain unchanged.

## Engineering corrections

The cohesive scalability correction eliminates repeated immutable reconstruction
within an identity-bound operation, prepares sealed-input work before the writer
transaction and rebinds its complete locked identity before writes. Live owners,
queues, revisions and atomic commits remain authoritative. Ordered indexes
replace quadratic joins without losing SQL NULL exclusion, duplicates, source
order or ambiguity denials. CSV, capture batches and selected report/readback
paths stream or batch rows; errors do not mask a lost connection or invent a
successful/failure database status. Initial full JSON/master lists remain a
capacity limit, not an unlimited-capacity claim.

The actual large-case audit also found pre-existing migration admission defects:
Spike/PSO demand multipliers were incorrectly capped at 100 at two consumers,
while preflight accepted those same policies. The frozen case has 97,011 rows
with legitimate 100,000 or 1,000,000 Spike overrides. Both consumers now use the
same nonnegative finite exact numeric domain, preserving the existing formula
`Norm * threshold / 100`. Shared true-percentage validation remains bounded.
Cheap early semantic checks retain global defaults, distinct pair identities,
NULL overrides and the raw four-default contract. They change no input values.

An accepted phase-in percentage string is converted to the selected SQL FLOAT
arithmetic before an active phase row uses it. Its 0–100 domain remains. Initial
master description diagnostics delegate to the approved field validator rather
than report an obsolete blanket ASCII failure. Frontend, MTO and auth are untouched.

Authority: direct human “Approved, resume the corrections”, exact decision
SHA256 b93f95bc81b0e778aa0865dbbfc931c71c48e41ecb248cd0ed549eaee2fa65af.
The six-file candidate passed full 97,097-policy admission, eight small complete
native flows and unchanged full output digests for both existing MOQ forms.
The isolated production-Python 3.11 rehearsal passed in 7.180 seconds. This is
focused correctness evidence, not execution of the large benchmark day.

## Established-order routing assessment

The port assumed an order's historical first-service warehouse must still belong
to the current hierarchy. Canonical `CalculateRoute.sql` explicitly permits the
hierarchy to change: retain the old first-service field and original DueDate,
but traverse current parent/RLT edges to the current supplier/plant if needed.
The fix changes only established-route construction. New-order classification,
quantities, due-date generation, allocation formulas and publication are unchanged.

The actual opening has 1,514 established Spike orders. Complete route comparison
preserves all 1,511 previously valid routes; three retained orders require the
canonical fallback. This is a migration correction, not legacy repair or new facts.
The existing off-path fixture had no executable regression reference in the
original or current tracked test suite; it is now exercised through preparation,
requirements and report/Pick producers. Twelve-day evidence for a different
dataset did not certify this branch.

| Related scenario | Diagnostic result / proof |
| --- | --- |
| Historical warehouse retired or no longer present | Three actual orders pass; original servicing field and DueDate retained |
| Historical warehouse exists on another branch | Retained off-path fixture passes complete current-day producer path |
| Case/trailing-space variant of historical code | SQL-equivalent comparison stops at the correct current node; stored text is not rewritten |
| Parent/RLT changes, including zero-day edge | Current route dates change; original order DueDate remains fixed |
| On-path service, service at source, new Spike/PSO | Existing behavior and complete unaffected output digests pass |
| Removed source, amended/closed orders, multipart identity | Existing order-owner, counter, next-opening and allocation checks pass |
| Duplicate nodes, cycle, broken parent/RLT or missing historical fields | Still rejected; no blanket hierarchy waiver |

The affected suite covers 57 tests. One existing typed-readback test mocked
`cursor` although production now uses `chunked_cursor`; the mock was corrected
with every value/order/successor assertion retained. These unit checks do not
replace new-image, PostgreSQL commit/readback, publication or UI acceptance.

Impact can propagate beyond three route rows: requirements and shared allocation
consume routes, then BOR/Pick, persisted closing state and reports consume those
results. Full-day verification therefore remains required. The domain comparison
above is not a claim that all downstream results stay identical to a rejected run.

The related deep-hierarchy discrepancy is now guarded: canonical
`CalculateRoute.sql` stops after 100 iterations, and both modern route walkers
explicitly block paths beyond that certified boundary. No deeper-path parity or
silent legacy truncation/repair is introduced. The full frozen master graph has
maximum physical depth 5 (6 route nodes including the terminal), so this condition
does not block the approved case. Arbitrary Unicode identifier collation and
unsupported ambiguous SQL joins are not newly certified.

The durable finding ledger is [SQL_BEHAVIOR_DISCREPANCIES.md](SQL_BEHAVIOR_DISCREPANCIES.md).

Direct human authority: “Approve narrow routing correction and continuation”,
question `call_d113a503430a43b89d047558a0b284e9`, decision SHA256
`c41d429f496c95c233d2c864e6a5364fdf82a8e3cfeb5a08aad0f74aa0afd4fc`.
The diagnostic additionally preserves the selected ASCII SQL equality rule when
deciding whether historical service has been reached. Original candidate bytes
and actual approval remain unchanged in external evidence.

## Completed measurements before the routing correction

These measurements are from source `a7b62d4ce5ba3a518332121281ab15cc47628cc5`,
image `sha256:f6ffeb220806bd829e363d11e45d134742d51617d12a2598ad70f155d1b7c864`.
They are not claimed as measurements of the routing correction.

| Operation | Native wall seconds | Result |
| --- | ---: | --- |
| Master/opening initialization and complete typed readback | 2487.863 | PASS; CPU1584.569s, peakRSS3,538,018,304bytes |
| Daily CSV admission | 503.116 | PASS; no calculation at this boundary |
| Native daily preflight/bootstrap | 452.422 | PASS within the failed daily attempt |
| Complete input capture | 1110.154 | CAPTURED within the failed daily attempt |
| Whole daily invocation | 2064.944 | FAILED at established-route closure; peakRSS7,818,489,856bytes; not a completed-day timing |
| Calculation/commit, reports and large-data UI | — | Not yet accepted |

The failed run has no output digest and no open client transaction. The command
container was removed after actual Exit1/PID0/non-OOM proof. No output seeding or
master loss was found. CSV-stage resource sampling has a qualified observation
gap; continuous capacity observation is not claimed.

## Source, frozen case and next execution

- Branch: `codex/3006-logistics-integration`; this revision contains the approved correction.
- Reusable CSV case: `I:/VectorFLOW-benchmark-20261020/fresh-start`.
- Opening SHA256: `27b3893b0f8a0f0db0197439c760677e9dc6dca07ad00f26fc4297781dd57a70`.
- Opening CSV manifest SHA256: `889e2021cca5d0665718a7bf827673c7995d47443489c05c50aefd6d9ec61489`.
- Configuration SHA256: `214a1c4326975ddbf9ea67a2535fa4130d3ec3a5958320ab68b80624b1f795fc`.
- Recipe SHA256: `b76147260e3f58cd2fbe16a370bfe7d562f3160843595a2e9bfb853ae4fe176d`.
- April8 native input SHA256: `30ddb9bd8c4ddbc51ffd743d23c4c8d5ef0146416baf37cfa58e9580899a41bc`.
- Evidence root: `D:/freshvcf-build/evidence/large-data-day1-benchmark-20261019`.
- Routing assessment/proposal/approval: `modern-fresh-performance/policy-integrity/established-route-proposal/` in that evidence root.

After focused regressions: commit/push, one MTA-only build, actual new-image
smoke before database creation, then one absent source-bound database
`vectorflow_mta_perf_route_20261020` on the same owned PostgreSQL/roles/volume/
private network. Existing initialization seals are never rewritten or reused
under a different implementation. Load the same opening, execute only April8,
prepare/select existing reports and perform the agreed small original-UI check.
Stop on the first genuine failure; no automatic business retry, extra date,
resource/timeout increase, historical import or legacy rerun.

## Preservation, cleanup and limitations

The original installation, entire3005 stack, four large source SQL databases and
unrelated projects stay unchanged. Completed command containers are removed only
after actual terminal Exit/PID/OOM proof. Obsolete owned benchmark databases and
images are disposed of after exact ownership, success/usage and client checks;
no global prune or shared Docker/WSL restart. Frozen case, concise causes/lessons
and final useful measurements stay outside Docker; secrets stay outside Git.

The retained corrected legacy result is a separate full-history, split-phase
reference: 1,920.976851 active seconds, excluding customer-source preprocessing.
It has different starting conditions and supplies no modern speedup ratio.
Full-day performance, full-scale capacity, historical parity and public deployment
remain unproved until their own applicable acceptance evidence exists.
