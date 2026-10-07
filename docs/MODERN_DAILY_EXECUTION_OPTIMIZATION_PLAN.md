# Modern daily execution refinement — integrated implementation plan

Revised7October2026. The human implementation authorization and current execution
status are recorded only in `docs/MIGRATION.md`. This supersedes the three
performance-checkpoint plan; editing this contract does not expand its scope.

## Delivery decision

ONE bounded integrated implementation, ONE final acceptance exercise, ONE report.
No intermediate ingestion/BPR, RRR or DBM performance approval gates. Focused
correctness checks continue during implementation. No wholesale engine rewrite.
The stopped21-day run stays stopped; no automatic continuation/publication.

Remove diagnostic overhead from production, optimize measured DBM/shared-work
costs, and preserve the complete daily flow. Broad surrogate-key migration is
deferred; narrow internal indexes/lookups are allowed for measured operations.

## Retained evidence

Reuse `D:/freshvcf-build/diagnostics/dayperf-001/`: June6,1240pairs, frozen input
SHA256 `ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56`.
Modern407.433s/legacy294.698s inclusive boundaries are NOT matched calculation
timings. Modern capture259.152s (63.6%): trace113.452s, checksum87.730s among
other work. DBM99.808s includes residual capture; legacy DBM27.139s. BPR/RRR
was combined. Modern BTR2.529s is not a new optimization priority. No rediscovery.

## Invariants and protected resources

Preserve formulas, rounding, NULLs, duplicate ordinals, native ordering/ties,
business-code equality, gates, action policy, histories, report sources and exact
successor openings. `execute_day` remains the authoritative daily boundary.
Calculation success, parity, publication readiness and selection remain distinct.
Preserve existing approved synthetic exceptions/deferred families; no new exclusions.

Preserve full-run days1–2 accepted, modern day3 SUCCEEDED and failed legacy day3.
Do not mutate frozen full-run images/source/input/config or accepted timelines.
Use new exclusive owned test resources/candidate images. Protect3002/3/4/5/6 and
excluded checkouts. Workers4GiB/twoCPU; no new ports, resource increase, shared
restart, borrowed/reset databases or DB copies. No UI campaign/history reproduction.

## Mandatory storage and serialization architecture

- Persist required inputs, closing state, actions, operational histories, daily
  report sources and necessary projections in TYPED RELATIONAL rows linked to run
  identity. Preserve exact reconstruction and duplicate occurrences. JSONB is
  bounded metadata, never the replacement for operational state. Traces are not truth.
- Eliminate unnecessary internal JSON encode/decode handovers, whole-result
  normalization and repeated copies. Use typed interfaces between stages and
  explicit adapters at genuine storage/API boundaries, preserving conversion semantics.
- Do NOT save every scratch variable. Use bounded temporary working sets for
  small transforms; use relational staging/set operations for large joins,
  aggregations and intermediates requiring recovery or durable consumers.
- Design for millions of pairs and larger event/history populations: no full
  population dictionaries/lists merely to map, compare or hash; no whole-output
  JSON strings. Declare working-set ownership, batch/dependency-group limits,
  release points, database I/O and handling of oversized dependency groups.
  Cross-pair/parent allocation cannot be partitioned arbitrarily. No new parallelism.
- Preserve one logical atomic daily completion/rollback. Staging is not permission
  for partially accepted stage commits or exposing incomplete results to readers.
  Additive relational changes require real migrations, not ad hoc state tables.
- JSON remains appropriate for bounded config/manifests, API envelopes and opt-in
  validation evidence. This is not an incompatible blanket JSON ban.
- Defer a daily source/projection only after proving its consumers, lifetime,
  reconstruction, successor independence and failure behavior. Terminal readers'
  sources cannot be discarded because next-day calculations do not consume them.

Million-record scale is a design requirement, not certified by1240pairs. Exact
volume/events/retention/SLA remain unspecified; disclose limits without inventing
capacity claims or opening a benchmark matrix.

## Complete-flow coverage — reconcile once before edits

Use existing DAGs and known owners. Produce one compact coverage map with inputs,
consumer, final writer, persistence requirement and timing category; not a second
status queue. Unmapped required stages/outputs block closure.

Include captured MDM/predecessor (`runtime/temporal.py`); importer master/daily/
supplier validation, SOB/MOQ refresh and master reconciliation (`temporal/chain.py`);
controls, forced/accepted Norms, phase-in/out/seasonality; spikes/orders/due dates/
closure; requirements/reservations/sourcing/rationing/Pick/logistics and RRR;
BPR consumption/penetration/colour/BlueRequirement/UpdateBPR; DBM ingestion,
suspensions/cooling, suggestions/Norms/post-rule reports; norm0/1/2/detail/advisory
and norm-change exports/history; BTR trends/ageing/insights and final standard
attribute writes; shared controls, ClosingState and operational histories.

Daily completion includes `save_daily`, required production images/exports and
`finalize_consumption`; Pick-band, Excess, Fulfillment, Expedite/Pick-post writers;
`daily_sources.write_sources` supplier opening, colour, requests/remarks/transit
sources and `offline_rrr.write`. These are not optional just because they reside
under presentation. Expensive `daily_publication.prepare` builders, seals/access
and selection are a separate preparation/admission boundary.

Reconcile generated ClosingState, MasterValidation, Supplier/Daily/Control/Order
Stages, CalculationInput/Outputs/Run, BPR/DBM/BTR Stages/Final, Reports,
MajorBoundaries, Lineage, PublicationContext and enabled images/daily sources.
Mixed operational/diagnostic collections must be classified by consumer, not
discarded wholesale. Actual requirement/rationing precedes late BPR, and BTR is
final writer of some attributes after DBM: preserve those dependencies, not an
artificial BPR→RRR→DBM ordering. Shared work is counted once.

## Integrated modern implementation

### Evidence policy

Use ONE engine with explicit production/validation evidence policies. Production
retains input/business checks, source/predecessor identity, action eligibility,
transaction integrity, durable state/history/sources and concise status/failure/
timing records. Validation adds complete snapshots/checksums/parity artifacts.
Existing offline parity scripts explicitly retain validation mode by default.

Audit the known expensive checksum/trace/copy/normalization sites and consumers.
Make diagnostic capture lazy: do not build payloads then discard them. Consolidate
repeated immutable verification within its boundary while retaining mutation/tamper
rejection. Remove whole-output hashing/readbacks only with an explicit cheaper
replacement for any required invariant. Keep necessary admission/audit checks.
Stream validation serialization/compression and release copies without losing fields.

### Calculation/persistence refinement

Separate remaining embedded capture from DBM costs. Optimize the largest evidenced
DBM calls: repeated scans/lookups/joins/copies and redundant shared transformations.
Use existing set-based/indexed owners and bounded working sets. No formula rewrite,
new recommendation engine or general schema cleanup. Integrate necessary adapters
across all covered producers, persistence and readers; retain inexpensive algorithms.
Run focused correctness checks during edits, not only at the end.

## Separate prerequisite — legacy capture-memory repair

Correct only `_plain(full)` whole-result JSON conversion/duplicate retention in
`parity/adapters/legacy/temporal_day.py` and necessary capture plumbing. Preserve
actual `_json` conversion semantics, every field/type/NULL/order. Test conversion
equivalence first. No canonical SQL edit, output copying, omission or memory increase.

After plan approval, ONE explicit legacy day3 retry may use its own accepted day2
predecessor and existing successful modern day3. Preserve the failed attempt and
document the narrow adapter source-pin transition; run full day3 parity/source proof.
Do not recompute modern day3/replay days1–2 or advance day4. Stop on failure.
This repair acceptance is separate from the new performance case.

## ONE final integrated acceptance exercise

Use the same frozen1240pair scenario in separately owned timelines for TWO days.
Day1 is the measured case; day2 proves real actions/history/successor continuity,
not another benchmark. Engines use their own openings/predecessors independently.

1. Run required focused tests/source checks/builds. Schema changes require Django
   check, makemigrations check, migration plan, real owned PostgreSQL migration and
   fresh-schema proof. Repeat only after an attributable fix/failure.
2. Prove production/validation required output equivalence, disabled diagnostic
   builders, rollback, identity/NULL/duplicate/order behavior, changed-source/
   predecessor denial and incomplete-publication denial. If mode equivalence needs
   an extra execution, limit it to this day1 case and label it correctness-only.
3. Complete all31 integrated comparisons, affected daily source/readback and reader
   proof, real actions and exact next opening. Capture full validation evidence
   outside primary production timings; do not weaken logical comparisons to suit
   changed internal representations.
4. Measure modern production and equivalent legacy work once each, sequentially,
   using scalar exclusive wall/CPU timers. Separate loading/calculation, mandatory
   persistence/source generation, startup, diagnostic evidence and residual time.
   Subtract nested spans; SQL/database CPU is UNMEASURED if unavailable. Provisioning
   and external parity are not primary calculation timers. If timing needs separate
   invocation from validation, confine it to this same day1 case, no repetition matrix.
5. Record input/opening/profile/action boundaries, row counts, image/code identities,
   worker/database resources, execution order/background load. Unequal capture,
   persistence or resource boundaries are NOT COMPARABLE, not fabricated speed ratios.
6. Report improvement versus modern probe as total benefit including removed
   diagnostics, separately from equivalent calculation savings. Compare legacy on
   matched work only. Goal: modern required daily execution no slower than matched
   legacy, with unchanged business work; one sample is not p95/SLA certification.
7. Use ONE bounded component cardinality test to demonstrate working-set behavior;
   no million-pair daily run, large scale matrix or resource increase.
8. Run ONE unselected terminal-trial preparation and complete qualified reader/
   scope proof outside timing. Preserve deferred families; no browser login,
   activation/cutover. If proof needs serving selection, report for human decision.
   Preserve normal production single-day end-to-end publication and offline mode's
   daily canonical sources with terminal-only expensive preparation. Prove deferred
   presentation is not a successor input and required sources remain reconstructible.

Final gate: full correctness/parity, exact continuity, required source/reader
compatibility,4GiB resource compliance and honest performance outcome. If modern
misses comparable legacy time or semantics diverge, report the residual issue and
smallest remedy; only attributable correction/recheck, no unbounded tuning. Scope
changes require a consolidated decision. Do not claim acceptance with unresolved gates.

## Handoff and stop

One primary owns implementation/integration; at most one bounded consequential
review where transaction/storage truth warrants it. No serial discovery/review chain.
Commit/push substantive logical work and integrated delivery, not tiny probe commits.
Deliver storage/evidence policy, complete-flow map, changes/migrations, legacy repair,
ONE before/after/legacy report, correctness receipts, working-set limitations and
actual verified operator commands. Update runbook production-versus-parity modes.
Secrets outside Git. Million-record capacity and full21-day acceptance remain pending.

STOP after handoff. Full-run restart, surrogate migration, wider rewrite, capacity
campaign or serving publication require the next explicit human decision.
