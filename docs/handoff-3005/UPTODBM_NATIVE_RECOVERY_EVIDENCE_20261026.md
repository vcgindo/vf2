# Native UptoDBM recovery evidence — 26 October 2026

This appendix records evidence, not a new execution queue or scope release.
`F:/freshvcf/docs/handoff-3005/TRACKER.md` remains the sole status authority.
The full shared lifecycle goal is incomplete.

## Qualified native interruption boundary

Human approval `call_b3ea06a1f0df495d87b7e577a8ee7741` authorized a separately
initialized stockout test, its explicit TEST dispositions, one intentional
worker exit after BPR, exact fencing and frozen recovery. It used the unchanged
native release `a83ed4b8d24a38f888de1697d584a7c6fd4519cc`, image
`sha256:5d000e2a8a551808a98c2a409749ebd399f43b39e6d010b45839bba8c3c1920d`.

The test's own 23 October predecessor is
`08fb80da-28e5-4758-b775-57459235e9a9`. Complete comparison with the retained
canonical-roster predecessor found exactly one expected difference:
`Lineage.initialization_id`. All business values matched. The independent
initialization identity was retained, not normalized in stored outputs.

The 24 October run is `f1969f82-b703-48b4-9827-90f85047f563`. An external proof
driver terminated its own native process with exit code 86 at the call into
DBM, after accepted BPR and its files. Native product files were not patched.
The host observed the terminal exit, absent worker container and zero remaining
database clients before fencing; the checkpoint marker alone was insufficient.

- Unfenced retry was denied while attempt
  `2e06d096-4687-42cf-9801-983fd97c7786` remained ACTIVE.
- The packaged fencing command marked that exact attempt FAILED using its
  inspected worker token. A subsequent release with the old token was denied.
- Recovery attempt `01ca7e77-0fc7-4e40-82af-8f776330aea5` reached RELEASED on
  the same captured run. PRE_BPR/BPR identities, snapshot digests, frozen input,
  predecessor output and existing files remained exact; one DBM was accepted.
- A released repeat made zero `prepare_day`, `produce_bpr` and `produce_dbm`
  calls and preserved run, phase, attempt, command, read-reference and master
  revision headers.
- Exact ordered typed readback verified DBM state, eight BOR history rows,
  eleven RRR history rows and the ten-member InputData archive. NULLs and
  duplicate ordering were included.

This qualifies one same-release abrupt-exit boundary. It does not qualify
other interruption windows, an old process attempting a delayed commit,
arbitrary cross-release recovery, paired native Full/split equality or scale.

## Positive action qualification remains unproved

The recovered stockout trial computed no current suggestions. Its declared
consumption of 11 and 40 with zero stock triggers canonical spike suspension:
the thresholds are `CEILING(Norm/3)`, respectively 4 and 12. Both pairs receive
reason 2048 and disabled red flags. The positive expectation failed; no Apply
or Sleep action was executed. The failed assertion and diagnostic rows remain.

Human approval `call_d44a754951074860b6ffb06683736d84` then authorized a separate
balanced two-day low-stock fixture. Its 23 October predecessor
`0b18b6e5-d48f-4c82-b6d9-208ef211894f` completed, but the pre-successor check
found supply-issue suspension, reason 128, for both intended targets.

An independent read-only review traced the exact approved 24 October facts
through canonical `10. SupplyIssue.sql`, lines 27–87:

| Pair | Norm / RLT | Receipts, 22–24 Oct | Required receipts | Stocks, 22–24 Oct |
|---|---|---|---|---|
| SEASON / WH8 | 12 / 3 | 0 + 1 + 1 = 2 | 4 | 1, 2, 0 |
| Z9 / PARENT | 36 / 3 | 0 + 0 + 0 = 0 | 12 | 3, 3, 0 |

Neither has stock strictly above two-thirds Norm to exclude it from the supply
rule. The rule replaces nominated memberships with disabled current-day rows
before evaluating receipt-based release. Neither receipt total can release its
membership. A disabled predecessor is not universally disqualifying: sufficient
successor receipts can release it before Rule 1. These exact facts cannot.

The low-stock trial therefore stopped before any 24 October capture or
calculation. Its predecessor, inputs and failure evidence are retained. No
further fixture, settings change, recommendation seeding or assertion weakening
was used to obtain positive coverage. The two positive-fixture designs were
insufficient; this is not evidence of a business-rule defect. A future positive
scenario needs complete eligibility analysis before another execution decision.

## Evidence and preservation

Evidence root:
`D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/uptodbm-private-20261025`.

- `positive-stockout-test/bounded-recovery-result.json` consolidates the actual
  exit/fence/recovery, released repeat, typed history and failed expectation.
- `positive-stockout-test/post-recovery-complete-diagnostic.json` retains the
  complete typed DBM state used to explain spike suppression.
- `low-stock-positive-test/eligibility-gate-result.json` records the exact
  supply-rule assessment and confirms that only its predecessor exists.
- `low-stock-positive-test/prior-native-trials-preservation.json` and
  `private-preservation-proof.json` verify earlier native trials, database
  identities, old copied-run headers and global role attributes.
- `protected-source-after-lowstock.json` verifies source HBA and owner headers,
  zero replication slots/workers, and unchanged 8080 readiness response.
- `low-stock-positive-test/bounded-test-stop-proof.json` confirms the private
  PostgreSQL container stopped with identical mounts and its volume retained.

Measured retained private storage/evidence was 2,759,269,093 bytes, below 4 GiB.
PG remained at 384 MiB/0.5 CPU; one worker at most used 4 GiB/2 CPU with no ports.
Serving 8080, accepted earlier runs, frontend visual design and MTO API were
unchanged. No browser, positive action, UI-latency, production configuration,
large-data deployment or whole-lifecycle acceptance follows from this appendix.


## Subsequent approved three-day positive trial

Human decision `call_da428cf59cff45978a7199f4872087ce` approved one new
namespace, unchanged retained feeds, its own 23 and 24 October Full auxiliary
predecessors without actions, and 25 October UptoDBM. This subsequent evidence
closes the positive native-handler/action gap described above only within this
owned test. It does not release PostDBM implementation or general Full acceptance.

The namespace is `vftest_fresh_uptodbm_three_day_20261026` (OID 508161), initialized
as `dcfa9a34-18d1-4b00-b1a6-973fade774b2`. Native code remains `a83ed4b8`, image
`5d000e2a8a551808a98c2a409749ebd399f43b39e6d010b45839bba8c3c1920d`.
Fresh migrations through 0226, Django check, migration drift and migration plan
passed. No product implementation changed for this trial.

| Business date | Own run | Result |
| --- | --- | --- |
| 23 October | `d1d66b4f-946b-4234-bd19-d30e231528f3` | Full predecessor succeeded; output `6682424b06af02faf2b80119cccf6353d05210343b7bcb40ef9c51a2552f3011` |
| 24 October | `fd626e5a-01d2-4b55-a231-c4692652027f` | Full predecessor succeeded; output `79b69485442da69ad0343dd3dde2d2cb77bdb8eb5848a285372d08245e65bb27` |
| 25 October | `a2661554-4450-4ac2-a2fc-c2055e685663` | PRE/BPR/DBM accepted, one RELEASED attempt; remains RUNNING before BTR/final |

Before 25 October execution, exact target master, daily observations, monitoring,
aggregate and control rows matched the retained canonical 24 October evidence.
Actual Type 5 recommendations were NEXT/WH8 and PHASE/WH8, both Norm 12 to 8,
and Z9/PARENT, Norm 36 to 24. All three complete consumer and HTTP grid rows
were preserved and compared, including order and field values.

Released repeat made zero prepare_day/produce_bpr/produce_dbm calls and left
owner headers unchanged. Typed readers matched complete accepted DBM tables,
12 BOR and 16 RRR history rows, inherited BTR from the own Full24 predecessor,
and all 10 InputData archive members. Seventeen packaged handler checks passed:
DBM reads/paging/empty filters/permissions, Planning, BPR/RRR/BTR, selected date,
four Pick downloads, BOR allocation CSV and InputData. These used the actual
runtime PostgreSQL role and explicit test gateway headers, not a browser session.

Positive actions also passed through the packaged handlers:

- Apply NEXT/WH8 recorded OldNorm 12/NewNorm 8; visible count changed 3 to 2.
- Sleep PHASE/WH8 recorded the actual action date; count changed 2 to 1.
- Repeated Sleep was a canonical no-op, retaining the third recommendation.
- Injected failure after composing the new action view rolled back every
  affected table and left zero committed commands at that checkpoint.
- Exact idempotency replay appended nothing; stale revision and unauthorized
  requests were rejected without changes.
- Complete typed action state matched the canonical command transition, while
  accepted master and phase headers stayed unchanged. Three commands remain,
  with final action revision 4; PostgreSQL sequence allocation during rollback
  need not be gapless. Downstream consumption was not executed.

Action responses took 20.653, 20.419 and 23.372 seconds in this constrained stack;
selected runtime startup took 12.684 seconds. These are observed timings,
**not performance acceptance**. Browser/gateway delivery, click-to-usable-screen
latency, paired native Full/split equivalence, downstream action consumption,
other interruption windows and required scale remain open. Later PostDBM,
final Full closure and G3 remain unreleased.

Three external test-driver issues are retained honestly: an initial PG readiness
probe failed before database creation; the positive assertion used `WhCode`
instead of the consumer's `LocCode`; and a read-only wrapper incorrectly nested
a helper which owns its own transaction. Corrected readback passed without
repeating any accepted calculation or editing its outputs.

Evidence is under `three-day-positive-test/` beneath the evidence root above.
`bounded-trial-result.json` pins the input, run, handler, action, preservation and
driver evidence; SHA256
`53ab003f381d29a7f79d98335848ce0481f03cfddaa4bbaf94cba58226a99a31`.
Its functional assertions are supported by `native-action-proof.json`,
`native-typed-readback-proof.json`, `native-repeat-proof.json`,
`complete-grid-wire-proof.json` and `private-api-proof.json`.

Earlier trials, copied-run headers, database identities and global roles were
preserved. Protected source HBA/owner fingerprints and 8080 readiness body were
unchanged, with zero source replication slots/workers. Aggregate measured
private storage/evidence was 2,824,555,653 bytes, below 4 GiB. The exact private
PG container was stopped at `2026-10-25T19:26:52.111559971Z`, with identical
mounts and all databases retained. Serving 8080, frontend design and MTO API
were unchanged. See `protected-source-after-three-day.json` and the trial's
`bounded-test-stop-proof.json` for those boundaries.


## Startup guard reuse correction

The subsequent latency investigation used the same three-day database and
resource limits. One positive action was profiled inside an outer rollback;
all affected table values and owner headers matched afterward, with the original
three committed commands retained. The first probe closed the HTTP response too
early, closing its connection before the post-action assertion; its failure log
is retained. The corrected probe completed preservation checks. Profiling adds
substantial overhead: its 39.504-second action measurement is not directly
comparable with the earlier unprofiled 20–23-second responses.

The profile identified 5,144 SQL calls for one action, 51 source bindings,
108 typed input reads and 88 recursive accepted-phase checks. Nested cumulative
times include 23.910 seconds in read-reference preparation, 5.094 seconds in
full phase restoration and 17.971 seconds in canonical digest computation;
these times overlap and must not be summed. Action optimization remains open.

Startup separately repeated complete guard coverage 25 times because its
metadata operation was excluded from the existing request-level reuse path.
Commit `5b28f552` corrects only this measured boundary. A successful check can
be reused within one startup metadata operation only when the existing live
PostgreSQL snapshot/session stamp and exact default database/physical connection
match. Each lookup reads the stamp; fills require equal before/after stamps.
Transactions, non-default/closed/reopened connections and failures retain full
verification. No entries survive the operation. HTTP and writer validation
lifetimes are unchanged; no source or business-state cache was introduced.

Independent review found no material defect. The focused suite ran 51 tests:
49 passed and two PostgreSQL-only cases were skipped locally. A separate native
PostgreSQL proof verified committed DDL invalidation, failure non-reuse, session
stamp changes, transactional bypass, new-operation revalidation and a commit
during cache fill. Its temporary owned probe relation was dropped and the
complete schema digest matched before/after.

The exported native source differs from `a83ed4b8` only in
`mta/presentation/request_scope.py` and `mta/runtime/ingestion_ownership.py`.
Calculation/SQL/migration/initialization and selection recipe code is unchanged.
Native manifest `2ab47aa5b56974d7330bc9ef77789b3dd22b6da872374488813d203eac08ee7f`
and image `c49988c4d96e93b3491ba593ad455ce0372b22954944c142ddaeab7e1cdf3375`
were built and verified. Supported code-only admission appended the release only
in namespace 508161, preserving its original certification, schema/security,
accepted phases, three commands and every compared affected table value.

| Same retained native test | Before | After |
| --- | ---: | ---: |
| First startup | 12.764 s | 6.493 s |
| Repeated startup | 7.740 s | 5.923 s |
| Complete guard checks per startup | 25 | 2 |
| SQL calls per startup | 1,078 | 720 |
| Three-repeat grid median | 1.737 s | 1.749 s |
| SQL calls per grid request | 581 | 581 |

The grid repeat followed an initially variable grid timing; all runs retained
the same complete current result. These finite backend measurements establish
startup work reduction only. They do not close action latency, browser delivery,
UI response time or production scale acceptance. Serving 8080 was not deployed.

Evidence is in the same `three-day-positive-test` directory:
`startup-guard-result.json`, native invalidation/transition proofs, paired timing
files and source-boundary proof. Protected source fingerprints and 8080 readiness
were unchanged. Measured private storage/evidence was 2,880,515,121 bytes, below
4 GiB. The private PG was stopped at `2026-10-25T19:44:53.391828728Z`, retaining
all databases/mounts; earlier trial and global role preservation checks passed.

### Certified DBM action-state reader

Commit `59854f3d` narrows only the native certified UptoDBM action reader.
Apply/Sleep need DBMMaster, Suggestions, NormAcceptanceTbl and
NormsInSleepModeTbl; they previously restored the entire calculation phase,
opening and unrelated consumers. The native certified path now reads those
four exact typed images. BPR actions, older/component owners and downstream
calculation restoration retain their existing full reader.

The source/run locks, actionable head, current source cut, canonical command
calculation, immutable accepted prefix and complete command-chain checks remain
in place. Fresh input metadata is validated on each action. The prefix reader
retains capture locking by default; only the already locked action path uses
read-only capture access, matching the existing runtime grants. Every chain
verification uses a fresh copy of the immutable base. There is no cross-write
cache or grant/schema change.

Focused tests: 50 passed, two PostgreSQL-only cases skipped locally. An
independent review found no concrete defect. The native source manifest
`6b9140ee3731999b264ba3b9af287e3bcece98ff9b7b6296b739d77d51ed96b3`
and image `4bd04322ff264127f9b4a544dff89f3e876cabe23e555334a9987a31147e2d7b`
change only `scoped_actions.py` and `scoped_final.py` relative to the prior
qualified image. Phase recipes, calculation code, migrations and initialization
implementation are unchanged. Code-only admission is confined to namespace
508161; its original certificate, schema/security and affected rows are retained.

Native exact-state comparison, including stored field rosters and the existing
three-command chain, passed. Under the same PostgreSQL 384 MiB/0.5 CPU and worker
4 GiB/2 CPU limits, full restoration took 3.037 seconds/763 SQL calls; the four
table read took 0.071 seconds/15 calls. This is a reader measurement, not a
whole-action or browser latency claim. All evidence remains in
`three-day-positive-test/action-subset-*`; no serving 8080 deployment occurred.

The packaged runtime proof subsequently passed positive Apply, positive Sleep,
Sleep no-op, canonical complete-state equality, idempotent replay, stale-revision
rejection, missing-identity rejection and a late composed-view failure. Every
trial action was rolled back. The exact affected-table/header fingerprint
`593a59703c77ffd639997165cabc6b8705b43a96ba8d7ec69cb5877836406603`,
three commands, revision four and the remaining Z9/PARENT recommendation survive.
No downstream phase was executed.

| Complete native handler, same build and resource limits | Time | SQL calls |
| --- | ---: | ---: |
| Apply with previous full-restore reader | 19.714 s | 5,144 |
| Apply with four-table reader | 19.303 s | 4,396 |
| Sleep with four-table reader | 17.167 s | 4,400 |
| Sleep no-op with four-table reader | 16.172 s | 4,396 |

The complete request remains too slow. This single paired Apply observation does
not establish a material latency improvement; the reader removes measured work,
but the report dependency rebuild remains the active performance problem.
It is not browser/click-to-usable-screen acceptance.

Earlier trial headers, copied database, global roles/database identities,
protected-source fingerprints and 8080 readiness passed preservation checks.
Private storage/evidence measured 2,936,274,580 bytes, below 4 GiB. Private PG
stopped at `2026-10-25T20:03:13.835858513Z` with unchanged mounts, no worker or
other clients, and every database retained. Consolidated
`action-subset-result.json` SHA256
`9c71f3ebfb9b47aa59492ec98df2fe880574bf1cb21c9f01af95d0bdbc972e33`
pins the native proof, candidate, transition, preservation and driver files.

### Transaction-local report preparation handoff

Commit `fbb8abcc` passes admitted dependency bindings between preparation stages.
Previously each stage rebound the source graph, and final assembly rebound it
again. Seven producer modules now expose private transaction-local entries;
public ID-based entry points retain their locking, admission and model-row
returns. Every stage retains its SQL guards, occurrence ordering, complete row
readback/checksum, sealing and receipt checks. Planning/Expedite use their NMS
capabilities, GIT receives transit, and final BPR receives inherited BTR, fresh
locked remarks and transit. The completed graph still goes through independent
`_save()`/`_bind()` and final current-selection verification. No cross-write read
cache or schema change was introduced.

The alternative of reusing old BPR generations would require a distinct current
action-reference contract and retained-base admission. Simply relaxing revision
checks is invalid. A smaller diagnostic of input-identity reuse within one pure
validation pass reduced calls 125 to 51, but only changed Apply from 17.962 to
16.788 seconds; that in-memory prototype was not installed as product code.

Focused tests: 44 passed, two PostgreSQL-only cases skipped locally. The initial
combined invocation lacked the repository tests import path; the corrected
invocation passed. Independent review found no concrete defect. The shared
handoff validator is explicitly included in the changed derived recipe digests.
Native v7 image `331a8bfd`, manifest `4617b6c2`, changes nine presentation files.
Calculation/phase recipes, SQL, migrations, initialization implementation,
frontend and MTO are unchanged.

Code-only release admission preserved the original certificate and schema.
Repreparing only namespace 508161 appended new derived owners, retaining every
old row. All 26 complete report populations match the prior native build exactly
(digest `7af98467756a6553ad2abde615dd4f2b9256d8eb5ccb075962e34ea28e337916`).
Repeated preparation creates no further changes. The three committed commands
and action revision four remain unchanged. The new read reference is `60b66fe1`;
its previous references remain retained. The new affected-table/header
fingerprint is `7ddcf595384b818eb141c1d749b7c5c27fe329a34ebd1b994876414bc2c5318e`.

Native runtime actions passed canonical state, all 26 report populations,
idempotency, stale-revision and missing-identity denial, no-op and late-failure
rollback. Every trial action was rolled back. Complete Apply measured 12.038
seconds/3,009 SQL calls, Sleep 12.072 seconds/3,013 calls, and no-op 11.743
seconds/3,009 calls under the unchanged private resource limits. Prior v6 Apply
measured 17.962–19.303 seconds/4,396 calls. This is substantial measured work
reduction, but response time remains unacceptable; browser and scale acceptance
remain open. No serving 8080 change occurred.

The subsequent cProfile run preserved fingerprint `7ddcf595` and the three
commands. Its 26.908-second action includes profiling overhead and must not be
substituted for the 12-second unprofiled measurement. It records 76 typed input
reads, 42 recursive accepted-phase checks, 26 complete ingestion guard checks,
109 scoped-action ownership checks and 731 digest calls. Nested cumulative times
include report preparation 14.466 seconds, the two selected-view traversals
10.285 seconds, canonical command recording 1.107 seconds and digesting 11.147
seconds. These nested figures are not additive. Startup/grid SQL counts remain
720/581; the profile also checked the remaining current grid recommendation.

Final preservation checks passed for earlier trials, copied database, roles,
database identities, source HBA/owners, replication slots, workers and 8080
readiness. Retained private/evidence footprint is 2,992,567,466 bytes, below 4 GiB.
Private PG stopped at `2026-10-25T20:30:34.319658323Z`, preserving all databases
and mounts. `handoff-result.json` SHA256
`ffcf083d0f629bb229b138268cf275ddd7f74d4e161eb5818da9357dd4ddf65d`
pins candidate, proofs, profile, drivers and preservation records.

### Architecture review requested after the 12-second result

Recommendation: separate immutable calculation/report generations from current
DBM action and remark revisions. The handoff correction is valid and retained,
but it does not remove the structural dependency that regenerates BPR material
for every Apply/Sleep, including a no-op. Treating every action as a new report
preparation event makes work grow with the report population instead of the
selected action. It also holds source/run/remark locks for the whole rebuild.
The measured repetition is primarily ownership/metadata traversal and
materialization; this evidence does not identify a missing business-query index
or establish a need for more memory, more containers or Pick/DBM parallelism.

The target transaction should validate the current selected run and revisions,
append and verify the canonical typed action, then atomically publish a small
read reference binding the unchanged accepted BPR/report generation to the new
DBM action revision and the appropriate remark revision. Read requests observe
one complete reference. Existing report rows/receipts retain their original
identities; current DBM recommendations always use the current action chain.
An unchanged/no-op action can still receive its required auditable command
receipt without reproducing report populations.

This requires an explicit ownership/schema contract. The present SQL guards
bind all generations to the current action revision, so simply relaxing a
revision comparison, rewriting old receipts or serving an old complete view
would be wrong. A new reference must prove exact run/phase ancestry, sealed
base generation, command parent/current revision, source/configuration identity,
actor/transaction authority and remark highwater. Subsequent actions, remark
writes, recovery, current selection and final consumption must understand that
reference. A remark change refreshes its affected projection/reference, not
unrelated BPR data; this boundary must be implemented rather than ignored.

Implementation order within active UptoDBM: establish that dependency contract
and its negative/stale/concurrent tests; implement atomic action/reference
publication and readers together; then deduplicate repeated authority/input
validation within consistent read boundaries. Retain live invalidation, schema
and permission checks; a validation result must not outlive its proven owner or
revision. Do not add general cross-write caches or move incomplete publication
behind an asynchronous response. Full source/receipt audits remain available,
while an ordinary action should validate its exact current dependencies once.

Acceptance must cover exact reports/NULLs/duplicates, Apply/Sleep/no-op,
permissions, remarks, successive commands, stale revisions, rollback at each
publication boundary, restart/recovery and concurrent reads/downloads. Measure
SQL work versus selected-row count and report population, then real Chrome
click-to-usable latency on matched data/resources. Use the requested roughly
two-second interaction expectation as the acceptance target to test, not an
architectural guarantee inferred from backend timings. Current evidence is a
small owned backend trial; 8080 browser, native Full/split, remaining recovery
windows, scale and later lifecycle gates remain open.
