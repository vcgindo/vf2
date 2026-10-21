# BTR memory correction handoff — 22 October 2026

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

The sole live status and decision tracker remains `F:/freshvcf/docs/handoff-3005/TRACKER.md`. This document records the bounded candidate; it is not a new work queue or a release to run another day.

## Problem and authority

The saved April8 run98abd748-5823-4c51-9dac-9a1ce4bb0298 completed BPR/RRR/Pick/DBM, then the existing worker RSS8GiB guard stopped it during BTR. No typed output rows, checkpoints, commands or publication were committed. Its header/attempt retain the interrupted RUNNING/CALCULATE/CAPTURED state; no status rewrite or replay occurred. The original opening, seven earlier complete records and archives, global roles and protected services passed separate read-only preservation checks. The accepted schema transition remains committed.

Baseline: `4f887576cc1c1ddffb9656ee7a0f98a193bd24fb`. Controller release `controller-btr-correction-scope-release.json`, SHA256 `12e0f406f9ceff51d2ca4c77672bbfa0ec086e4d148881f68c36b277cbc66805`, authorizes only two production files plus focused proofs under the existing Section11B/D lifetime/copy/streaming scope. It excludes builds, PostgreSQL mutation, another large attempt, service changes and increased resources.

## Change

- `mta/domain/btr_finalization.py`: retain sparse observed-day cells while emitting complete ordered D1–D90 trend rows, reusing column keys. Replace the retained per-pair90-day scratch grids with compact scalar age/count summaries; only one expanded pair grid is live at a time. Required output fields, day horizon, values, NULL rules, duplicate counts, source-order failures, collation and ageing rules are unchanged.
- `mta/temporal/chain.py`: capture the existing independent DBM report images at the DBM last-consumer boundary, then release its input/terminal working wrappers. Delay independent closing-state copies until BTR scratch has been released. Preserve closing-versus-final mutation independence and the existing commit-owned flag/settings writers. No blanket aliasing or mutable-input sharing was introduced.
- `tests/test_btr_memory_lifetime.py`: regression coverage for ordered pivots, NULL/duplicate/gap rules, actual immutable file-backed rows, real integrated DBM-wrapper lifetime, final family independence and unchanged complete typed-manifest writer/reader access.

No initializer, CSV/orchestration, admission, schema, persistence, report-consumer, R1 algorithm, formula, policy, frontend, MTO or auth source changed. The existing public BTR component non-mutation contract remains.

## Evidence

External evidence root:
`D:/freshvcf-build/evidence/daily-contract-audit-20261021/section11/admission-contracts-20261022`.

- 64 focused affected tests PASS in8.548s: BTR/reporting/snapshot/category, supplier/BTR indexed consumers, actual daily entry ownership, streamed histories, serialization, commit-owned finalizers and separate Norm0 report families. No PostgreSQL test or installed instance mutation occurred.
- Direct comparison against raw pinned4f887576 source:32 complete BTR stage cases PASS across ordinary/operation-owned paths, reporting modes, ageing flags, empty/nonempty histories and lists/file-backed RecordRows; three identical failure cases PASS; two complete native daily output graphs PASS, including the actual typed-input reconstruction representation. Types, field order, values, duplicate ordinals and input non-mutation compare completely, not just counts.
- 12 bounded allocation cases PASS at64/128/256pairs and1/30history dates. Every measured output matches the baseline. Peak Python allocations decreased27–56% for trend construction and42–54% for colour processing. These tracemalloc measurements are NOT whole-worker RSS or a large-data capacity result.
- A real next-producer boundary test confirms DBM working wrappers are no longer retained when BTR starts. Complete ClosingState/DBMFinal/BTRFinal/report values and required independent mutation boundaries remain covered.
- The real typed manifest traversal, image/export shape and conversion code, and complete reader reconstruction passed with SQL transport/fetch substituted locally. Actual PostgreSQL commit/rollback and full large persistence remain unproved by this candidate.

Exact proof/source hashes are in `btr-memory-candidate-proof.json`; affected test log `btr-final-affected-tests.log`. Source-consumer findings are in `BTR_MEMORY_CONSUMER_QUALIFICATION.md`. The failed launch and read-only preservation receipts remain distinct and unchanged.

## Limits and next decision

The failed image did not log individual BTR substage boundaries, so the exact allocation that crossed8GiB is unknown. The source costs and measured correction are evidenced; a full large-data peak or successful day is not claimed. Required independent final populations and their persistence remain real costs.

No new image was built. No large run, recovery-depth extension, sibling/second finite child, source reseal, master reload, new date, resource increase, service activation or execution-window reset is authorized by this handoff. The previous maximum-one attempt is consumed. Any next large validation requires a concrete separately approved method that preserves the current interrupted child and loaded opening.
