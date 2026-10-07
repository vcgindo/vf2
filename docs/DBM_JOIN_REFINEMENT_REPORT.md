# Targeted DBM join refinement

The five authorized DBM functions now use the existing bounded ordinal lookup
for exact key candidates. White, spike and supply suspension, ExtendedOCP and
suspension-history joins retain source order, duplicate multiplicity, NULL/text
keys, original predicates, date windows/ties, Norm grouping and reason arithmetic.
Each index belongs to one immutable call or local join and closes before any
indexed source mutation. No business rules, SQL, action policy or input changed.

All deep copies remain. Their snapshots preserve independent inputs and outputs;
removing them would require a broader ownership change than this task authorizes.

## Matched modern timing

Exactly one production day-one invocation per version, June 6, 2026, all 1,240
pairs, fresh separately owned PostgreSQL databases. Same lightweight boundary
clock wrappers, 4 GiB/two-CPU workers, 1 GiB/one-CPU PostgreSQL, no host ports.
Actions, external validation, extra exports and report preparation were omitted.
Both timing fixtures omitted explicit empty request/BPR-remark initialization;
see the acceptance correction below. Their mutual timing comparison is preserved
with this narrower source coverage.

| Measured boundary | Before | After |
|---|---:|---:|
| DBM selected stages | 30.862 s | 10.131 s |
| Typed input persistence | 16.218 s | 15.438 s |
| Output persistence/commit | 18.637 s | 21.074 s |
| Other boundary assembly/checks | 23.441 s | 23.556 s |
| Complete production day (sum of four boundaries) | 89.159 s | 70.199 s |
| Worker process CPU including startup | 76.769 s | 56.167 s |
| Peak worker RSS | 688,934,912 B | 689,033,216 B |

Observed DBM reduction: 20.730 s (67.2%); complete-day reduction: 18.960 s
(21.3%). Single samples establish this observation, not a repeatability estimate,
full-run ETA, browser latency or matched-resource legacy performance claim.
Index construction/query and retained copying are included in DBM time; they
were not separately instrumented. Optional validation work is absent from these
timing totals and is not folded into them.
The older 33.733-second reference used different wrappers; no ratio to that
reference or to the intrusive cProfile diagnostic is claimed.

Before/after persisted integrity audits match all 515 ordered business images,
report manifests and every Pick, Excess, Fulfillment, Expedite, Pick-post, offline
RRR and daily-source projection. Run IDs, source ownership/input lineage and
output receipt digests differ deliberately. Production runs have no validation
digest or checkpoint trace. Complete row-content digests, not counts alone,
underpin the comparison.

## Acceptance status

Both June 6 and June 7 pass all 31 canonical comparisons and independent RRR,
with no excluded comparison. Each engine continued its own persisted predecessor.
Day one exercised all eight eligible Sleep identities and applied 120 suggestions;
day two applied six. Persisted action-state digests, successor identity, complete
ordered outputs and all consumer-source readers passed readback verification.
The day-one accepted comparison remained unchanged while day two was attached.

`validation/comparison-day{1,2}-a001/accepted.json`, both replay receipts,
`validation/rrr-day{1,2}.json`, both `mode-proof-day{1,2}.json` and `final-proof.json`
retain the complete acceptance. The original timing pair and approved corrective
production run are separate from these two validation days.

The strict mode-equivalence check exposed a setup mismatch: the two timing
fixtures lacked initialized request/BPR-remark owners, while validation had
explicitly initialized empty owners. Every shared source path matched; missing
sources were not treated as empty. Day two was already in flight when this was
found; its result was preserved and canonical capture stopped at the gate.

Direct approval `call_o8pMnxLpwAhIoVdAvFccvmJ2` authorized one additional untimed
production acceptance run with identical authoritative empty initialization.
Run `2fa1b352-ef13-4e75-931c-975129122882` now matches validation day one across
all 515 ordered images, report manifests and all seven source/projection families.
No business code, reader or assertion changed. The original two timing receipts
remain unchanged: they measure the narrower source setup, not equivalent
full-source timing. The corrective run's incidental command duration is not
used as a timing sample or substituted into the before/after comparison.

Focused old/new differential and ordinal-index tests pass (six tests),
including duplicate facts/masters, NULL and distinct text keys, date ties,
receipt multiplication, ordering and predecessor/output independence. Independent
review found no actionable issue and verified the frozen reference functions
against source checkpoint 1ccef40. Commands: `python -m unittest tests.test_dbm_join_refinement tests.test_ordinal_lookup`
and `python tools/baseline.py verify`. All 387 pinned resources verify.
The candidate image built successfully; fresh owned PostgreSQL databases applied
the existing migrations normally. There is no schema change.

Canonical workers use the existing SQL server and mandatory capture/normalization.
Their host processes are bounded to 4 GiB/two CPUs; equivalent SQL-server and
PostgreSQL resource budgets were not established. This proves correctness, not
matched-resource legacy performance. No browser, terminal preparation, full
21-day continuation or serving publication was run by this refinement.

## Reproduction and release boundary

Evidence root: `D:/freshvcf-build/refinement/dbm-joins-001/`.
Frozen input: `D:/freshvcf-build/synthetic/rlt-4-7-v1/scenario-004/full-input.json`,
SHA256 `ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56`.

- Before image: `sha256:3791d148878aae8780200cb91fcee9e90920f9afb6f63f974d07a3569330c48f`.
- Candidate image: `sha256:8cd55a876595f37398eaa25828f4d51ecd07b737d25b9208498686732ab7abb2`.
- Before run: `28670490-df3f-4a37-a46c-edf7d7f95448`.
- After run: `f592509e-461b-4233-92c9-bbd811ae51a1`.
- Validation June 6 run: `68b7c59d-55fd-463c-b24f-25606aba6757`.
- Validation June 7 run: `3c0250bf-9831-4be3-b107-29f4f0f716ed`.
- Fresh canonical namespace: `VFTEST_Fresh_Offline_202ffbe586278845_*`.
- `before/modern-timing.json`, `after/modern-timing.json`, both `mode-proof.json`
  files, `timing_boundary.py` and `preservation-and-timing-equality.json` retain
  exact timing, image-content and preservation evidence. `identities.json` binds
  the three changed source hashes and original test resources.
- `source-mismatch-diagnosis.json`, `corrective-identities.json`,
  `mode-equivalence-resolved.json` and `modefix/opening.log` preserve the exact
  mismatch, approved setup correction, provenance and complete equality proof.
  `capture-day2-a001` stopped at the hold before canonical execution;
  `capture-day2-a002` is the first canonical day-two capture. No accepted day
  or modern day-two result was replayed. Credentials stay outside Git.

All four newly owned PostgreSQL containers are stopped with volumes retained;
the new SQL namespace and every attempt remain preserved. The 24 protected
service snapshots match, and all six 3006 serving containers retain their earlier
identities/images without a restart during this task. `final-proof.json` and
`serving-3006-preservation.json` retain these checks. The maximum observed bounded
canonical capture/comparison worker allocation was 3,116,765,184 bytes, below
4 GiB. No memory increase or schema change was used.

The original `temporal-full-001` package, three accepted June 6–8 receipts and
`readiness-v1/transition-a005.json` remain unchanged. This candidate is not a
readiness release. Its three changed calculation-source hashes intentionally
cannot pass the old transition. A future full run requires an explicitly approved
source/image transition and renewed readiness proof; do not replace pins silently.
The operator runbook now prescribes step 0: stop at that hold. Neither full-run
continuation nor serving publication is authorized by this refinement.
