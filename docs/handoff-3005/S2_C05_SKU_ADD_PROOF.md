# C05 request 25 — bounded SKU Add correction and recovery

This is evidence, not a second status tracker. The authoritative status remains
`F:/freshvcf/docs/handoff-3005/TRACKER.md`. C05 and whole G2 are incomplete;
Step 3 is unreleased. Running 3005 was not changed.

## Defect and correction

The frozen July 3 SKU Add request `2_20260703080115` approved SKU5328 and
completed its audit/history/task effects, but the current-owner guard rejected
canonical synchronous publication outside a consumed running day. The handler
preserved the deployed exception sequence, completing the task and clearing the
queue after the failure. All eight master rows were absent. Day 3 was not run.

`tasks.publish_add` now holds the existing source advisory lock and scopes an
authorization marker to each of its eight existing INSERT statements. Database
authorization requires the sealed native source, real master-1 Add task,
approved request/history/queue backing, exact owner and ordinal, and the complete
task-selected projection including NULLs. The global source queue and duplicate
occurrences remain intact. Legacy publication and the approval/audit/completion
sequence are unchanged. UPDATE, DELETE, TRUNCATE and location tables gain no
authorization. Bootstrap and consumed-day rules retain their existing predicates.

Additive migration0130 was applied only to the component database when duplicate
testing exposed PostgreSQL trigger snapshot visibility. It remains immutable.
Additive0131 makes exact validation a mandatory STABLE row trigger, before the
current-owner trigger. A VOLATILE helper acquires the same advisory/source locks;
competing direct INSERTs fail rather than wait on an obsolete snapshot. Both
migrations were applied normally to C05 only after component proof passed.

## Verification

Twenty-two focused PostgreSQL tests pass: ten new native SKU cases and twelve
existing daily-consumption cases. They cover actual submit/approve with eight
complete rows, owner ordinals200/200/5/200, duplicate and other-task global-queue
occurrences, normalized existing-code exclusion, invalid markers/backing/values,
unchanged write denials, statement failure effects and native task completion,
normal consumed-day guards, and two-connection lock exclusion. Tests use small
inline fixtures inside rollback-only TestCases; all pre-existing component table
values remain identical. The partial-publication test proves statement/savepoint
effects and sequencing; it does not claim a separate multi-connection commit
visibility test. Django check, makemigrations --check, migration plans and real
PostgreSQL migrations passed. Independent bounded review found no remaining
concrete defect.

The first component failures, snapshot experiment and preflight failure remain
preserved. The initial preflight mistakenly used an initialization-only verifier
that requires just base families2/3; the corrected runner uses the existing
complete13-family binding verifier and also compares the full frozen opening.
This is a runner correction, not a seal or acceptance change.

## Exact recovery

The controller explicitly authorized missing-effect completion, not reapproval.
Read-only preflight proved the complete108-model reviewed snapshot unchanged,
accepted days1–2 inputs and outputs unchanged, the approved/completed request
present, queue empty, and no day3/request26.

Under the source lock, one recovery transaction revalidated those predicates,
rebuilt only request25's queue through `update_approved_queue`, called the corrected
production `publish_add`, and removed only that reconstructed queue. Full-value
comparison against the frozen expectation proved exactly four attribute and four
description rows added. All existing master rows and the other106 source-owned
model populations, including approval, audit, history and task timestamps,
remained identical. All calculation-run rows remained identical. No calculated
output was supplied as input or seeded into current masters.

Recovery `c05-request25-missing-effect-v1` committed. The same recovery gate was
called again and returned `ALREADY_COMPLETE_NO_OP` before any queue reconstruction
or publication. A separate PostgreSQL read-only postcommit verification passed.
The original failed request remains a failed original attempt; this is explicitly
a recovered result, not uninterrupted first-pass acceptance.

## Identities and limits

- Initialization: `c5fe5b52-2f7e-4081-bf68-bc46a6584d72`.
- Accepted day1: `f80f0692-80e6-473f-af89-eb12c17146bb`.
- Accepted day2/predecessor: `388a7810-ad96-4473-9104-8accb48f95b3`.
- Corrected runtime amendment: `38924a0f54418d2477b6cefc82097988580f004bd848793a8ff14303e60909ae`.
- Original reviewed snapshot: `d4352bb9e86221ce39ba64eb6b99f360e613d6fabd64e56e1d70cd09834d07bb`.

The amendment freezes862 files and a complete archive. Only the existing
`tasks.py` changed; the statement helper, two additive migrations and focused
test module are new. Calculation/capture/daily-publication files and the existing
initialization/adapter digest definitions and values are unchanged. Days1–2 did
not exercise synchronous SKU Add and were not replayed. All old input files,
runtime archives, failure receipts and database seals are preserved.

External evidence root:
`D:/freshvcf-build/evidence/handoff3005-s2-20261013-001`.
`S2_C05_SKU_ADD_EVIDENCE.json` binds exact evidence hashes and sizes, including
`c05-request25-recovery-v2`, the original failed attempts, component proofs,
runtime archive and migration/protection receipts. Six protected services and
the two existing bounded test containers remain unchanged; no new resources,
host ports, heavy data, OOM or restart were introduced.

Request26's independently identified location-Add publication/completion gap is
deferred for controller disposition. No location authorization or implementation
is included here. The remaining frozen C05 requests and own-successor days3–21
have not passed. No full G2, UI, production capacity or handoff claim is made.
