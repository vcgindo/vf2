# Cohort2 — consolidated closure decision

Approved directly by the human on 8 October 2026: "Approve the four items exactly
as documented in COHORT2_CONSOLIDATED_CLOSURE_DECISION.md. Complete only this
finite acceptance and delivery, preserve all qualifications and failures, then
stop." This authorizes exactly the four bounded items below. `docs/MIGRATION.md`
is the only status tracker; this document fixes the decision and proof boundary.

## 1. BOR history ordering

Accept only `BOR_OrderAllocationHistory` as complete typed row bags when its
unordered canonical SELECT returns a different physical sequence. Every field,
NULL, duplicate occurrence, retention boundary and date remains exact. Keep the
strict sequence failures and modern persisted ordinals. Do not add a sort or
transfer this qualification to current BOR, RRR, exports, allocations or UI.
The exact source and two-row difference are in
[the BOR decision](COHORT2_BOR_HISTORY_ORDER_DECISION.md), with preserved native
evidence `bor-native-a002.json` / `bor-native-a003.json`.

## 2. SOB table-export ordering

Accept only the generated `SOBDataRaw` input-table member as an exact header plus
complete exported-row bag. All bytes within each row, NULL spelling and duplicate
occurrences remain exact. Preserve the 245-byte strict sequence failure in
`input-files-a003.json`. This does not apply to the physical intake
`SOBDataRaw.csv`, any other archive member, calculations or UI. Exact source and
the four-row difference are in [the SOB decision](COHORT2_SOB_EXPORT_ORDER_DECISION.md).

## 3. Missing ZIP restoration

Use an existing verified identical copy first. The post-intent retry now reuses
an exact recorded ZIP only after its name/content/size map matches the current
producer's staged files; its container hash and intent identity remain exact.
That case passed in `integrated-retry-a001.log`. No qualification is needed for
that exact-copy behavior.

When every copy of a previously successful mapped ZIP is missing, allow a
**qualified archive restoration** from the same persisted producer and pinned
ZIP tool. Require exactly the original ordered member roster, decompressed
bytes, sizes and hashes, with no missing, extra, encrypted or directory members.
Keep the original successful receipt, original container hash and intent rows
unchanged; link the replacement in a new repair attempt and record its distinct
container hash. Never call this exact container-byte restoration. Plain CSVs
remain exact bytes. Changed member data or source/config/action/owner identity
still fails.

This applies only to mapped Cohort2 report ZIPs: O2 BPRExceptionReport; O3
NoNormParentReport; O4 InputData; O5 its eight named upload-log archives; O6
DBMNormChange, NormChangeLogReport and the enabled 30-day Norm1/Norm2 archives;
and O7 InvalidDataReport, PhaseInPhaseOutExceptionReport and the conditional
DailyDataUnavailabilityReport. It does not apply to PostgreSQL/SQL backups,
calculation traces, arbitrary ZIPs or unsupported report branches. The existing
implementation limits member-equivalent repair to O4/O5/O6; approval would
permit only extending that same check to these already mapped report archives.
No new recovery mode or schema is proposed.

## 4. Exactly two modern source-capture dates

Authorize **two calculation invocations total**, June 6 and June 7, 2026, under
new identity/revision `cohort2-real-source-20261008-001`. Use the unchanged
retained nonempty Pick artifact, which contains one SKU at ten locations for
this slice. This is a new isolated correctness proof, not a replay into accepted
Cohort1 owners, a full-day legacy comparison, a benchmark or temporal continuation.

The proposal and complete file hashes are frozen at
`D:/freshvcf-build/evidence/cohort2-20261008-001/closure-proposal-v1/proposal.json`,
SHA256 `6298483327fccde514356b3bc1db0a5a263cce0f52023f5456c317a1110c1c68`.

| Input | SHA256 |
|---|---|
| Unchanged Pick input-v1.json | `7e60ef1b3d73a36889b25a43995234ec5839a5bb646da5b782328189a1b2699d` |
| Unchanged Pick config-v1.json | `19a7b9f9dd840389d0d948ef21ed740bad2f0f55d01c286b3678da06c1e53a45` |
| Prior Cohort1 finalization supplement | `571e38fa7ef82759ce0ca439bff08015eb1eb688c29620958cd07f4c6dab2b3e` |
| Proposed finalization-input-v1.json | `e00799a63a29b856728a649809ca4db5816e42f28fe7784af378994ec7008c2b` |
| Proposed operational-opening-v1.json | `7ee4047b75a253e988b717ff7726d2aa72df3aa818b1fdb03295a4a08a5c9325` |
| Proposed profile-capture-v1.json | `4294f80a4b2bbe30a6a1bb33846e1d4eece72a516d4aef46d1a2c8f3a7bfba45` |

The supplement preserves every existing Cohort1 opening/configuration value and
adds only C1's explicitly empty `CriticalFiles` and `DataSanitizationResult`.
The operational opening retains the twelve approved empty/history/log/action
populations and explicitly declares initial `RunAbortReasons=[]`. Approval of
this package includes that previously absent abort-history opening. It cannot
certify a client filesystem hook or a positive sanitation path. Profile changes
enable only the three implemented source captures; business facts, shipment
ledger, Pick/DBM formulas and existing action policy remain unchanged.

Use the existing owned `freshvcf-complete001-postgres` resource and `fresh_complete`
database, with new run-owned rows and attempt directories only. Each calculation
uses one finite worker at4GiB/2CPU; PostgreSQL remains1GiB/1CPU, restart=no,
without host ports. Use the same pinned owned Cohort1 MDM source, read-only,
with new per-run captures; do not mutate accepted task/source rows. Freeze the
candidate source/image/tool/config identities before invoking date one. Any
material input or business-contract change requires stopping and reporting it.

Use `own-recommendations-apply-eligible-retained-sleep-v1` unchanged. Apply/Sleep
must use each new run's real workflow; date two must consume date one's exact
persisted state plus its own accepted actions and completed operational
predecessor. No legacy output is copied into modern state. Reconcile unchanged
core families against accepted Cohort1 and identify only the explicitly added
operational populations/captures separately.

## Execution after approval — perform these steps in order

1. Record the approved exact qualifications. Reuse identity-valid passed native,
   file/tool, typed-state, restore, lease, intent and integrated protocol evidence.
   Complete only the existing unmet native O2/O3/O6 file-format checks and the
   approved mapped ZIP condition; do not expand the fixture roster or open a
   new recovery programme.
2. Freeze and verify the candidate code/image, configuration, input/supplement
   and tool hashes. Run mandatory affected Django check, migration no-drift,
   plan and migration-enabled PostgreSQL schema verification. No serving changes.
3. Run June6 once. Prove complete typed source capture/readback, run-owned
   files/member bytes, all14 alert dispositions, real PG backup/qualified logical
   restore, the actual materialize/check/recover commands and zero-calculation
   idempotence. Record real Apply/Sleep actions. If an exit fails, retain the
   failed attempt and stop before June7; report the first cause and smallest
   remedy. No implicit calculation retry is included.
4. Run June7 once using its own accepted June6 predecessor/actions. Prove the
   same boundaries plus exact next-opening continuity and operational-history
   carry. Preserve both accepted Cohort1 days and every existing receipt.
5. Produce the precise coverage/qualification handoff and verified Cohort2
   commands. Commit and push one cohesive delivery containing only Cohort2 work,
   then stop. Do not include unrelated guides, atlas or NMS work.

All required exits must pass or receive an explicit disposition; this approval
does not waive a failing comparison. No third date, legacy-engine run, full-run
release, performance work, email, serving/publication, Cohort3/4 or cutover is
included. A new blocking failure must be reported, not silently retried.
