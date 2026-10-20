# Large-data fresh-start benchmark

20 October 2026. **The full modern day is not yet accepted.** The policy-integrity
correction is approved and applied; focused regression verification is in progress.
`F:/freshvcf/docs/handoff-3005/TRACKER.md` is the sole live status authority.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

## Workload and measurement boundary

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

## Last completed measurements before the policy correction

These measurements are from source `9a1572080c063ec5dcac7feca07734d79a9ea55d`,
image `sha256:adc2177bfac819a25b746e738963b5b8a961b48c226dd6c8d6d2e55e2297853a`.
They are not claimed as measurements of the new correction.

| Operation | Native wall seconds | Result |
| --- | ---: | --- |
| Master/opening initialization and complete typed readback | 2555.610 | PASS; CPU1616.447s, peakRSS3,537,629,184bytes |
| Daily CSV admission | 462.753 | PASS; no calculation at this boundary |
| Native daily preflight/bootstrap | 454.477 | PASS within the failed daily attempt |
| Complete input capture | 1166.673 | CAPTURED within the failed daily attempt |
| Whole daily invocation | 1989.562 | FAILED at the incorrect threshold validator; not a completed-day timing |
| Calculation/commit, reports and large-data UI | — | Not yet accepted |

The failed run has no output digest and no open client transaction. All 97,097
policies match the CSV in both typed opening and captured input, including all
values, NULLs and ordinals. No policy loss or output seeding was found.

## Source, frozen case and next execution

- Branch: `codex/3006-logistics-integration`; this revision contains the approved correction.
- Reusable CSV case: `I:/VectorFLOW-benchmark-20261020/fresh-start`.
- Opening SHA256: `27b3893b0f8a0f0db0197439c760677e9dc6dca07ad00f26fc4297781dd57a70`.
- Opening CSV manifest SHA256: `889e2021cca5d0665718a7bf827673c7995d47443489c05c50aefd6d9ec61489`.
- Configuration SHA256: `214a1c4326975ddbf9ea67a2535fa4130d3ec3a5958320ab68b80624b1f795fc`.
- Recipe SHA256: `b76147260e3f58cd2fbe16a370bfe7d562f3160843595a2e9bfb853ae4fe176d`.
- April8 native input SHA256: `30ddb9bd8c4ddbc51ffd743d23c4c8d5ef0146416baf37cfa58e9580899a41bc`.
- Evidence root: `D:/freshvcf-build/evidence/large-data-day1-benchmark-20261019`.
- Audit/proposal/approval and production-Python smoke: `policy-integrity-correction/` in that evidence root.

After focused regressions: commit/push, one MTA-only build, actual new-image
smoke before database creation, then one absent source-bound database
`vectorflow_mta_perf_policy_20261020` on the same owned PostgreSQL/roles/volume/
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
