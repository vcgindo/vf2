# Section11 implementation handoff

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

Scope: Section11 Aâ€“E of DAILY_CALCULATION_OPTIMIZATION_IMPLEMENTATION_PLAN.md, over source `67b3c253e8ec268917306dc168e9fc49862ecf5a`. TRACKER.md remains the sole status/decision authority. This handoff describes the bounded backend correction; it does not release an image build, another large run, a loaded-database migration, serving activation or UI acceptance.

## Resulting execution boundary

The operational transaction still owns both R1 passes, DBM, controls, supplier/Pick results, current masters, consumption, actions and required histories. BTR computes the dispatch/physical trends needed for category and age effects transiently. Those business effects and exact next opening remain atomic. The eight wide trend matrices and four derived analytics are rebuilt after commit from typed BPR, closing norms and frozen source facts. No calculation formula, ranking, action policy, fact, date, NULL rule or duplicate ordering changed.

The new v3 operational manifest/root retains complete typed source facts, including overwritten DBM export inputs and order-route occurrences. The existing daily publication coordinator prepares an independent INCOMPLETEâ†’READY report generation. A report failure leaves the operational run committed; explicit resume rebuilds reports without execute_day. Next-day admission uses the operational predecessor and remains valid while reports are incomplete. An already staged successor is not invalidated by report-only writes. Actual facts, actions and operational mutations still invalidate preparation.

Version-two readers and roots retain their old contracts. New report classification applies only to SUCCEEDED DAILY_CHAIN v3 owners and exact declared image paths. Existing user remarks and business histories remain operational. A generation lock serializes derived appends with sealing; its source lock permits FK readers while preventing source mutation. Sealed rows cannot be changed or renamed into another image.

## Measured changes and dispositions

| Area | Change and evidence | Limit |
|---|---|---|
| Copies/lifetimes | Season and phase finalizers convert only their owned bags. Current-master publication constructs its location projections once per generation. At 16,000 unrelated list rows, season incremental allocation fell from 45.21MB to 0.206MB; spooled input remains bounded. | This does not establish the sole cause of the earlier large OOM. |
| History/snapshot amplification | Eight 90-column matrices and four analytics leave the operational snapshot. Matched 1,000-pair/four-prior-date BTR retained allocation fell 62.89â†’3.19MB; peak 87.40â†’36.62MB; canonical operational bytes 10.76â†’1.67MB. Separate population and depth scaling is recorded. Required BPR/rationing/log histories remain typed and complete. | Remaining required history snapshots scale with retained rows and the configured horizons. No cross-run history-reference schema was added: it is unnecessary to remove the measured matrix cost and would enlarge migration/reader risk. Deep-history storage capacity remains unproved. |
| Exports/projections | DBM export-cell expansion, twelve BTR derived images and four consumer projections run after operational commit. Their overwritten/opening-only inputs are captured atomically as typed facts. | Work is deferred, not eliminated. Reporting still has its own memory/time cost. |
| Repeated preparation | One current-master projection generation is reused for writes and receipt metadata; unrelated whole-state conversion is removed. Complete source and persisted-value/type/order checks remain. | No cache or skipped audit substitutes for integrity. |
| Database transport | Typed-image writes of at least 500 rows use psycopg COPY, retaining conversion, PK/FK/triggers, durability, outer transaction and full readback. At 4,000 rows/110 columns, insert 13.829â†’9.807s and incremental allocation 7.84â†’3.05MB versus executemany500. | Single ordered component measurement, not a whole-day speedup or capacity guarantee. Small images and other writers keep their existing transport. |
| Report SQL | Four actual BTR producer SELECTs were EXPLAIN ANALYZE'd: 12 rows each, 0.747â€“0.991ms, no temporary spill. | This fixture provides no evidence for an index/query rewrite or a large-screen latency claim; existing join multiplicity is preserved. |

The final small native commit contained 190 operational/source images, 2,503 rows and 366,189 tuple bytes. Its twelve separate derived images contained 124 rows and 24,846 tuple bytes. Tuple sizes exclude shared relation/index/WAL allocation; they are not a production-storage estimate.

## Verification

- Focused ownership/preflight/BTR/DBM/current-master checks: 87 tests, 7 PostgreSQL-only skips in that local invocation. Those relevant real-SQL boundaries were exercised separately below.
- Final migration-enabled PostgreSQL suite: three tests PASS, 158.570s; observer 242.904s; Exit0/PID0/nonOOM. It proved late operational rollback, real commit/full typed readback, positive controls, report-only failure/private rollback, exact successor admission while INCOMPLETE, report rebuild without calculation replay, unchanged operational root/closing/all five epochs, twenty layers/summary, archive/four Pick file bytes/selection, early next-day rejection, concurrent late-append denial and actual 10,001-row COPY/spool/read-only reader.
- Follow-on component suite: two tests PASS, 3.666s. The corrected late-COPY case reaches the final fractional integer conversion after 10,000 records and rolls back all partial rows. Version-two writes retain original revision invalidation and full-value tampering is detected. No daily run is repeated in this component suite.
- Ninety-five-date BTR fixtures prove full scalar closure plus all twelve rebuilt matrices, age generation enabled/disabled, actual spooled sources, unchanged inputs, and conflicting colour-history denial. Independent expected black-tail age is 90.
- Existing old-v2 full-output/READY-seal upgrade proof is retained in `old-v2-upgrade.log`; new version predicates and the latest v2 invalidation component are checked separately. This is not a claim that the loaded certified installation has been upgraded through the new schema.
- Consumer checks executed 52 tests: 48 passed, 3 PostgreSQL skips, 1 pre-existing removed-fixture import error. The older publication-test failures also expect removed fixture modes or omit mandatory release pins. Relevant production/test files are byte-equivalent to baseline for those failures. They are retained and attributed, not counted as passing and not repaired by weakening production guards. Actual native report preparation/admission is covered by the SQL suite.
- Independent review found and closed the concurrent append/seal race; no additional actionable D-delta finding remained.

Observed final native fixture phases: calculation 1.095s; operational persistence 13.168s; report layers 28.526s; aggregates 3.874s; archive 1.875s; report admission 18.960s. These include client/driver work and fixture overhead. Process RSS high-water was 181,370,880 bytes, cumulative rather than an allocation attributable to each phase. Do not extrapolate these timings to 97,097 pairs or compare them as a speedup against the split/history-bearing legacy run.

## Additive migration register

| Migration | Purpose |
|---|---|
| 0154 | Report generation receipt/model |
| 0155 | Typed order-route source facts/ordinal constraint |
| 0156 | Atomic route capture and report-sealing guards |
| 0157 | Exact v3 report/lifecycle revision ownership |
| 0158 | Derived row ownership and sealed-row guards |
| 0159 | Remaining derived reference bags and old-image UPDATE protection |
| 0160 | Nine immutable BOR/BOROA consumer-source projections |
| 0161 | Concurrent append/seal serialization and compatible source locking |
| 0162 | Eight derived trend image paths/guards |

Fresh migration execution, Django check and makemigrations check passed on actual PostgreSQL. No applied migration was rewritten or faked. Custom SQL is reversible. Loaded working database migrations, certificates, capabilities, all seven owner/capture records, inputs, original services and old large-worker state remain unchanged. Source changes are backend-only; no image was built.

## Evidence and next decision

External evidence root: `D:/freshvcf-build/evidence/daily-contract-audit-20261021/section11`. `section11-final-proof-summary.json` binds the native/component results, candidate source pins, measurements and exact logs. Initial failing proof logs remain distinct; routine observation/fixture corrections are not reported as production failures or successful attempts.

The one remaining large trial is not authorized by this handoff. Its concrete proposal must include:

1. The tested source commit and one exact MTA-only package/build identity, with frontend/MTO/auth unchanged.
2. A canonical, append-only migration/compatibility transition preserving the loaded opening and original certificate. Current `upgrade_ingestion.py` allows only 0144â€“0153, while `validate_activation` requires the certificate's exact schema/guard identity. Applying 0154â€“0162 and merely advancing a release would correctly fail. A new independently bound compatibility receipt/registrar transition needs separate review; do not rewrite the certificate, reseal the opening, reload masters or bypass the check.
3. An explicitly finite successor to the current six-wrapper recovery contract. The preserved seventh header is the stopped OOM run with no committed rows. Current readers deny another continuation. No status rewrite or recovery extension was implemented here.
4. The same saved April8 facts, initialization, seven owners/captures, physical input root and resources; no CSV reparse/restage, history import, new namespace or legacy rerun.
5. One proposed cumulative 180-minute all-work window, one MTA build and at most one April8 attempt, for a human decision. Proposed failure stops: 20GiB C/D/I free reserve; worker RSS 8GiB or combined Docker 12GiB; host available memory below 2GiB; observation older than 5s; any actual error/identity/readback mismatch. Stop and preserve; no automatic retry, resource growth or shared restart. These are proposed safety limits, not demonstrated large-run capacity.
6. Full operational commit/readback, subsequent report readiness, exact next-opening identity, source/image preservation and terminal no-jobs/no-open-transactions proof. Existing human UI and latency deferrals remain separate; no serving change follows from backend success.

The schema-transition and recovery changes are a real release decision for the preserved loaded target. They are not routine launch flags, and this completed bounded correction does not silently grant them.

Cleanup: the owned scratch database and17stopped Section11 proof containers were removed after external logs/inspect preservation and ownership checks. Protected services/roles/working metadata remain exact. No image or volume was removed. `section11-cleanup-receipt.json` records the result. The external `future-large-admission-scope-proposal.json` records the next release boundary and remains unapproved/non-executable.
