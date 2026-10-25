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

### Live read-reference integration checkpoint (not native workflow acceptance)

The human released the reviewed ownership integration through Release Controller
user turn `01a174c7-374f-7b53-9779-dde7cdfab860`; the implementer read that turn.
The sole status remains the canonical TRACKER. This checkpoint changes no DBM
formula, action semantics, frontend component, MTO contract or serving instance.

The implementation extends the existing immutable ScopeReadReference with
nullable `action_command` and `previous_reference` foreign keys. New v2 metadata
distinguishes the live command cut from the unchanged report build cut. An action
publishes only a successor reference; a remark publishes its dependent parent
projection and a successor retaining the command. Initial/ordinary UptoBPR
references keep their existing full-generation path. Old reference rows and
generation metadata are not rewritten or relabelled.

The retained graph reader receives the reference explicitly and binds its
dependencies once through the existing component validators. It has no ambient
allow-stale flag or cross-write cache. DBM selection, composition and commands
use the effective live cut; BOR supplies its exact reference, and DBM history
uses the composed current DBM context instead of rebinding the BPR build cut.
Independent final selection still runs after writes. Historical223-to226 guard
upgrade is explicitly frozen to226 instead of following the new default.

Migration register: `fresh_mta.0227_scope_read_action_reference`, generated by
Django, adds two nullable FKs/indexes without a data backfill; dependency0226.
`0228_scope_read_action_ownership`, dependency0227, installs two invoker helpers
and exact guarded transitions, updates dependent remark/ingestion guards, and
retains the prior v1 branch. Both apply on fresh and existing databases. Reverse
SQL rejects retained v2 references or registered application capability; a
committed deployment therefore needs a verified compatible forward recovery or
rollback build, not an assumed image downgrade or reverse migration.

Local focused proof: 68 tests, 66 passed and two PostgreSQL tests skipped. Eleven
new contract/control-flow tests cover current/build separation, successive
actions, action/remark permutations, no-op, stale/mixed/forged owners, unsaved or
other-database reference denial, and no report preparation in the DBM writer.
These tests use ORM-shaped objects and mocks; they do not certify persisted
action execution, concurrency, native admission or UI latency. Independent
read-only review found no concrete graph/current-consumer defect; its unsaved
reference concern was corrected with persisted/default-database admission.

Real PostgreSQL diagnostic used the existing private namespace508161 and a
source-mounted worker at the existing caps, with all migrations and writes in
one outer rollback transaction. Django check, makemigrations --check --dry-run,
and migrate --plan passed; the plan contained only0227/0228. The first diagnostic
found an added PL/pgSQL record alias colliding with an existing table alias.
The corrected diagnostic applied both migrations, verified exact guard bodies,
accepted a v2 base reference and denied missing predecessor, forged remark
transition and stale live metadata. It preserved all old fields/rows through
the additive schema change and restored the exact schema, migration history,
portable catalogue and affected row-hash multiplicities after rollback.

Evidence: `three-day-positive-test/live-reference-schema-diagnostic.json`, SHA256
`c129b755b262396267483a5a254527468728174f9cbb959a10e24b68f6c16063`,
with retained original/corrected logs. Before schema `17212aa7…`; diagnostic
after schema `f04db079…`. Migration pins are recorded in that evidence. This is
source-mounted migration/guard diagnostic proof, not a packaged native release
or successful action/remark workflow proof.

Protected source HBA/owner hashes, zero replication slots/workers and8080's
200 response/body stayed unchanged. Retained footprint2,992,867,219bytes is
below4GiB. PrivatePGdfdfcebb stopped at2026-10-25T20:52:01.675671755Z with
zero clients, no worker, unchanged mounts and all databases retained; see
`protected-source-after-live-reference-contract.json` and
`live-reference-contract-stop-proof.json`.

Remaining before delivery: supported exact native schema-release transition and
admission, packaged full action/remark sequences, all26report populations,
stale/mixed/unauthorized denial, failure injection through commit-time checks,
native interruption/restart/retry, consistent concurrent reads/downloads and
compatible rollback after committed references. Then real authenticated Chrome
action-to-usable timing at matched resources/data. No new latency claim is made.
Existing scale, filesystem-arrival/cancelled-download and native Full/split
obligations remain open; later PostDBM/final Full require release, G3 is deferred.

### Native live-reference upgrade and rollback workflows

Implementation `9b639788` adds the supported exact226-to228 schema/release
transition. Its first packaged attempt correctly rejected an incomplete delta:
the fresh226 namespace had no schema-transition authority table, while the
supported upgrader creates the existing immutable registrar-owned table.
The original source-mounted diagnostic had omitted this bootstrap. An additional
rollback diagnostic independently reproduced the entire native delta: all21
original entries unchanged plus20 bootstrap entries. Schema, migration history
and affected rows returned exactly to their original state after rollback.
The original rejection and both diagnostics are retained; no acceptance check
was bypassed. Migration0227's native pin uses LF bytes; the original diagnostic
used CRLF. Its SQL is unchanged. Migration0228 bytes are unchanged.

Correction `a60042fa` pins the complete delta `ccbcd11a…` and schema `0fab95b7…`.
The34 focused transition/authority/read-cut tests pass. Nativev9 image
`sha256:80ab54b1a44f0454e11d1293cb2c9dd9c54746170adf0d356e4faf19e9fe92ff`,
manifest `4509f8475270c983501f7f1cb871d41e2b83ccee704bb3f0c37007ed90130ebb`,
was built from committed source `a60042fa3b26fc7c5730bbcd1c9a43d37afbca28`.
The rejectedv8 image was never activated. No frontend/MTO/business-rule changes.

The actual supported upgrade first injected a failure after successful target
admission. DDL, authority history, migration records and affected rows rolled
back exactly. The subsequent real upgrade committed only in namespace508161,
preserving the original certificate `887208f0…`, all old row values/multiplicity
and prior authority records. One target authority/compatibility entry per table
was appended. Repeating the supported upgrade returned
`EXISTING_SCHEMA_TRANSITION_VERIFIED` without changes. The physical guard digest
is `ad6b00d7…`; new function OIDs are captured rather than assumed portable.

Derived-only preparation produced reference `68024d47` over the unchanged
accepted phases and revision4. All26 complete report populations equal the
retained baseline (`7af98467…`). Every old row remains; only derived owners and
occurrences were appended. Repeating preparation changes nothing. The old
selection file remains intact; `phase-selection-v8.json` and its corresponding
runtime environment select the new graph. The filename denotes this reference
integration generation; the executable image is the corrected nativev9 above.
Current preserved header/table fingerprint is `602dff9467abd70824029c3f5c836933b1a9e5b4fac5bc1407d7af792347a178`.

Actual packaged runtime-role Apply, Sleep and no-op pass full canonical action
state, all26 report populations, unchanged immutable report owners, exact
successor-reference identity, idempotent replay, stale-revision/missing-identity
denial and final-selection failure rollback. Three interleavings also pass:
Apply/Sleep/repeat, Sleep/remark/Apply and remark/Apply/remark. They check complete
action state and independent report rows, remark history/parent visibility,
current command/remark revisions and immediate deferred-constraint validation.
The rollback harness initially left constraints immediate between simulated
requests; its corrected version restores deferred mode after each successful
constraint check. The failed log remains. Full independent remark-parent query
parity and durable multi-transaction sequence acceptance are not claimed here.

Eight injected publication failures preserve the exact starting fingerprint:
after command seal, after action-reference insertion, during remark projection,
after remark-reference insertion, after final action/remark selection and
simulated action/remark commit-driver failures. The latter are exceptions before
database COMMIT, not server-crash or ambiguous-commit proofs. All trial actions
and remarks rolled back; the original3 commands/revision4 and remaining
Z9/PARENT suggestion survive. No accepted calculation was replayed.

Unprofiled native handler timings under the same resource caps: Apply5.454s /
1045SQL, Sleep5.562s /1049SQL, no-op5.977s /1045SQL; priorv7 Apply12.038s /
3009SQL. This proves further work reduction, not latency acceptance. A separate
cProfile Apply is9.185s including instrumentation: two selected-view traversals
7.149s,385 digests4.922s,30 accepted-phase checks3.376s,31 phase-recipe hashes
2.138s,30 typed-input reads2.072s and canonical recording0.871s. These nested
times overlap and cannot be added. No report preparation occurs in DBM actions.
Remaining work is repeated selected-view/input/recipe validation, not evidence
for new hardware or business-rule changes. Real Chrome and scale remain open.

Prior canonical/stockout/lowstock and copied-run checks, database identities and
global roles remain unchanged. Protected source HBA/owner hashes, zero slots/
workers and8080 readiness/body match. Retained files plus privatePG total
3,105,871,146bytes before final evidence assembly, below4GiB. PrivatePGdfdfcebb
stopped at2026-10-25T21:18:24.93176121Z with no worker/other clients, unchanged
mounts and all databases retained. Serving8080 was not changed.

Consolidated evidence:
`D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/uptodbm-private-20261025/three-day-positive-test/live-reference-native-result.json`,
SHA256 `920d43084846852fbc87d916d0877808cc56d2c6df00a3e159236361b9a51f20`.
It pins native candidates, upgrade/reprepare/action/sequence/fault/profile proofs,
drivers and preservation records. Still required: committed-reference restart,
interruption/retry and compatible recovery; concurrent reads/downloads; remaining
native negative cases; full remark-parent comparison; roughly2s real-Chrome
action-to-usable and scale evidence. Later lifecycle boundaries remain as above.

### Discarded binding removal and committed-reference recovery

Implementation `b02676ad` removes only the intermediate DBM compose after
`advance_action`. That constructed context was discarded after extracting its
identity; the following independent `selected()` already reconstructs and checks
the complete current context. Both pre-write and post-write selections remain.
BPR-only preparation, action algorithms, runtime/phase recipes, SQL, schema,
frontend and MTO are unchanged. Independent bounded review found no unique
check or effect lost by this removal. Focused tests:43 passed,2 PostgreSQL tests
skipped; the initially incorrect local import path was corrected to `.;tests`.

Nativev10 image `c125cdad90b118ca23eab9a0c3d26fb96bd89492cd58f17424a60063a675b7e1`,
manifest `871f5e6a3fcc17ffdf9ba139a7117c052cdc8e24be6b980bf986419c6392a85c`,
was admitted only to private namespace508161. Code-only admission preserves
schema0fab95b7, original certificate and business rows. Consumer selection recipe
advances honestly; reanchoring retains the same reference and all26 complete
report populations. Unprofiled Apply4.511s/994SQL, Sleep4.137s/997SQL and
no-op4.781s/994SQL remain above the interaction target. Relative to nativev9,
Apply removes51 SQL calls. Earlier paired baselines varied around4–5seconds,
so a stable elapsed-time percentage improvement is not claimed.

Actual native Apply/Sleep/no-op, replay, canonical complete-state equality,
all26 report populations, action/remark interleavings and eight publication
fault sites pass with rollback. Additional late permission, anchor and conflicting
Full-selection changes are denied after the real write; forged predecessor,
stale-command and mixed-report owners are rejected by PostgreSQL. Each case
restores the preceding complete fingerprint602dff94. Commit-driver exceptions
remain simulated before COMMIT, not proof of ambiguous-commit recovery.

An actual owned worker exited86 after inserting its sealed command/reference
and before COMMIT. Its Docker die event pins the exact nativev10 image. A fresh
worker found no partial command/reference and successfully retried positive Apply
inside a subsequently rolled-back transaction. While that writer held its locks,
a separate runtime connection read the complete old reference, canonical state
and all26 reports. This qualifies that native concurrent-read boundary only.

One canonical Sleep no-op for the already-slept PHASE target was then committed,
with intent and command receipts retained. Old commands and accepted phases are
preserved; the remaining positive Z9 recommendation survives. Authoritative test
state is now4 commands/revision65, reference
`782a010f-0bc8-4223-bf86-0a42ffa638ec`, complete fingerprint
`59a0ff04a0977c61eb70a1a629e8b77d85a40a6c30a62271902980e76d0b0b9d`.
Canonical four-table state and all26 report populations are unchanged. A Pick file
descriptor opened before that commit and completed afterward retains its exact
505bytes/SHA256; a fresh download reads the same bytes. This is file-adapter
evidence, not Chrome arrival, large-download or cancellation evidence.

After restarting only the exact privatePGdfdfcebb, new packaged runtime workers
using both nativev10 and compatible nativev9 read that committed reference,
revision65, canonical state and all26 populations exactly. Neither reverse
migration nor receipt deletion was used. Nativev7 remains incompatible with
the new schema/reference contract and is not a rollback target. Startup measured
6.417s/v10 and6.531s/v9 on this bounded recovery test, not browser latency.

Prior canonical/stockout/lowstock and copied-run checks, all database identities
and global roles pass. Protected source HBA6183a9be/ownersd42a7b5e, zero slots/
workers and8080 readiness/body remain exact. Retained private storage/evidence
measured3,161,636,641bytes before final evidence assembly, below4GiB. PrivatePG
stopped at2026-10-25T21:49:43.46007343Z with no other clients/worker, unchanged
mounts and all databases retained. No8080 deployment occurred.

Consolidated evidence:
`D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/uptodbm-private-20261025/three-day-positive-test/action-binding-result.json`,
SHA256 `faf9d21d5ea7653988affa2303cf81448cf1b78b5a87a45333b7dff7a01d93ed`,
pins37 candidate/proof/driver files. Positive action/remark sequences remain
rollback-only; the newly durable action is a no-op. Full independent remark-parent
comparison, broader recovery windows, native Full/split, required scale and real
Chrome roughly2s click-to-usable acceptance remain open. The UI also issues count
and grid requests after action success; endpoint time alone cannot close that
acceptance. The next performance boundary is repeated validation within each
existing read traversal, retaining fresh post-write checks. A smaller final
validator is not yet qualified and must not replace those checks implicitly.

### Shared phase validation within each existing read pass

Implementation `3ff09f30` changes only `scoped_dbm_stop` and `scoped_dbm_view`.
Their shared adapter normalizes UUID/text phase IDs before the existing
`scoped_sources._accepted_phase` cache. The original runtime verifier still
validates the complete recursive ancestry on a cache miss. No cache lifetime
extends across a write or independent read pass. Current head/revision checks,
actionable-scope SQL, permissions and the independent final selection remain.
The changed consumers only read the shared phase objects. Independent bounded
review found no correctness blocker. Focused39 tests:37 passed/2 existingPG
skipped;5 adapter tests also passed after strengthening direct-source sharing.

Nativev11 image `870f0373ca566552fd8d58131cf093fc51d09ed56df0a519b8ad618e23f053db`,
manifest `72f631debfeee74025c2fc7233509b2fa5b4c65973868f743346f8ecac195c0c`,
has unchanged runtime implementation/migrations/phase source. Code-only admission
preserved the original certificate, schema0fab95b7, guards and complete affected
rows. Normal selection reanchoring changes only consumer recipe/selection digests;
the reference782a010f and all26 report populations remain exact. No derived report
generation is rebuilt or relabelled. The start precondition correctly kept the
privatePG stopped while the candidate image was still building; it was started
only after the build completed and its physical identity/caps were verified.

Packaged runtime Apply/Sleep/no-op, canonical complete-state equality, replay,
stale/unauthenticated denial, action/remark interleavings, eight fault-site
rollbacks and late/mixed-owner negative cases pass. Unprofiled native actions:
Apply3.662s/966SQL, Sleep4.086s/969SQL, no-op4.723s/966SQL. These isolated timings
do not establish a stable improvement over the previous build.

A matched baseline/reuse/reuse/baseline run used the same packaged build and
unchanged four-command fixture. Baseline adapters called the unchanged runtime
verifier directly; reuse used the new adapter. Complete canonical action state,
all26 reports, unchanged generation owners and exact rollback were checked for
every sample. Baseline4.001s/3.842s versus reuse4.716s/3.541s overlaps and is noisy;
there is no supported elapsed-time improvement claim. Deterministic work falls
from998 to966SQL and22 to10 recursive verifier calls. Both selections execute:
each reuse pass performs5 recursive checks and reads its correct pre/post action
revision/reference. An additional injected failure in the actual runtime phase
verifier after the write proves the preflight cache cannot bypass final validation;
the entire command/reference is rolled back.

Current state remains4 commands/revision65/reference782a010f/fingerprint59a0ff04,
with the positiveZ9 recommendation intact. Prior trials/copied runs, database
identities and global roles pass preservation. Protected HBA6183a9be/ownersd42a7b5e,
zero slots/workers and8080 readiness/body remain exact. Private/evidence footprint
measured3,217,416,837bytes before final evidence assembly, below4GiB. PrivatePG
stopped at2026-10-25T22:05:24.10509086Z with no worker/other clients and retained
mounts/databases. Serving8080, frontend and MTO are unchanged.

Consolidated evidence:
`D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/uptodbm-private-20261025/three-day-positive-test/phase-validation-result.json`,
SHA256 `0ff29f44d3f4d0958816eb2630ef0c7ad3a38b87d5b2f3572d9583bf5b17026e`,
pins28 candidate/proof/driver files. This closes the bounded reuse correctness
and operation-count proof, not latency acceptance. Further local cache experiments
are not justified by these timings alone. The remaining architectural boundary
is action validation versus full report-view construction: specify every current
selection check, its state owner and required freshness before choosing any
smaller action path. Current full post-write validation remains mandatory until
an equivalent replacement is qualified. Real Chrome click-to-usable, required
scale and previously recorded lifecycle/recovery limits remain open.
