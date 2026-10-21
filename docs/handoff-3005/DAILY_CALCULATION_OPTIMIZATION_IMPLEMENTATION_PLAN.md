# Consolidated daily calculation optimization implementation plan

21 October 2026 · **RELEASED by direct human instruction through the existing controller. The sole tracker records actual authority and progress.**

This is one implementation effort covering the six researched calculation costs. It reuses the existing installation, committed master opening and accepted April8 inputs. It includes profiling, incremental correctness checks and exactly one final large-data acceptance attempt. It does not create six projects, a new controller process or a second status queue. `PLAN.md` governs the handoff; `F:/freshvcf/docs/handoff-3005/TRACKER.md` remains the sole status, blocker, decision and evidence tracker.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

## 1. Outcome and invariants

Deliver the existing complete daily business flow with less repeated preparation, searching, copying and serialization. Preserve the calculations and all parameter/control applications. Complete the same April8 day through typed output persistence and required backend report preparation/publication, with a measured result and an operational handoff.

Fixed invariants:

- Keep the current formulas, both canonical requirement passes, rule ordering, action policy, effective dates, rounding, overflow behavior, NULL treatment and rejection behavior.
- Preserve SQL comparison semantics, every duplicate occurrence, source ordinals, allocation priority and consequential ordering. Do not invent missing join keys or tie-breaks.
- Keep one authoritative input cut and the existing production day/final-commit ownership. No copied legacy outputs, altered facts, changed policies or reduced acceptance.
- Preserve master/opening seals, historical run/capture receipts, original rollback artifacts, accounts, scopes, authentication, all 3005 resources and unrelated services.
- Do not reinstall, register another source, initialize masters again, reset a database, reseed/reseal data, add a date, grow resources or rerun a legacy campaign.
- Keep Pick and DBM sequential in this effort. Concurrent workers, durable BPR/DBM split runs and changed partial-publication rules are separate proposals; do not combine them with the six optimizations.

## 2. Starting checkpoint and actual performance evidence

The installed code baseline is `be480eb412ace0e7d86b7dedf396910f0818746e`, MTA image `sha256:cc8db971956c64a1e7a250486ae9ab2dbd94a2837fdb2f72bfb773be494353bf`. The later handoff commit `f816e907686bba92cbd3791266bea5a50aca6c91` records the stop; it is not a different calculation image. Source work belongs in `C:/Users/thapa/.codex/worktrees/handoff-3005/freshvcf`; `I:/VectorFLOW` is the deployment tree. The unrelated product source in `F:/freshvcf` remains docs-only for this task.

| Preserved item | Identity or result |
| --- | --- |
| Working PostgreSQL container | `896b3688c10f` / `vectorflow-postgres-1` |
| Database | `vectorflow_mta`; retained database OID 16399, to be reconciled against live identity |
| Master initialization | `ebed3913-8e83-4da2-ae07-0c02f3b0beca` |
| Opening content digest | `9be120d9971642698f1dd90c0ff5e218adb7e4bfc837ce9359906515d45bae59` |
| Interrupted April8 run | `383104fe-3cf8-4666-bbe1-5156e767d0d7` |
| CSV attempt | `819ffecb-ffc1-4284-94fc-d4b81a8d515a` |
| Captured run input root | `652680b13c8260b5dcdd753338f1adcd96a14583ce4be6ff72e612a16fa2f116` |
| Accepted daily fact rows | 117,978 across the retained feed roster; 97,097 are DailyDataRaw rows |
| Additional physical capture rows | 204,906; distinguish these from daily facts and from calculation results |
| Native preflight/bootstrap | 266.895075 seconds, complete |
| Preparation/input capture | 2,151.978705 seconds, committed |
| Calculation | No return after at least 4,154.399854 seconds; no internal stage attribution |
| Stop | External 120-minute operation bound; total 7,216.485379 seconds |
| Persisted final outputs/publications | Zero / zero in the post-stop reconciliation |

The worker was externally terminated; exit 137 alone is not an OOM diagnosis. The sampled native-worker peak was 7.349 GiB. The calculation was approximately one-core CPU work while PostgreSQL was idle. There is no successful large-data modern baseline and no evidence identifying the particular function that exhausted this run's time.

Existing evidence is under `D:/freshvcf-build/evidence/ingestion-m4-20261021`, especially `terminal-proof.json`, `daily-measurement.json`, `capture-proof.json`, `native-worker-checkpoint.log` and `daily-resources.jsonl`. Preserve these bytes and conclusions. The original physical rollback set remains at `I:/VectorFLOW-benchmark-20261020/ingestion-m4-checkpoint`.

## 3. One execution sequence

These are internal work steps within one plan, not separate approval programmes. Once implementation is explicitly released, resolve routine choices within this scope and record meaningful outcomes in the existing tracker. Do not ask for permission per file, script or command.

### A. Reconcile reuse and establish profiling

First perform a bounded read-only reconciliation of the exact instance and receipts: original database/source/opening/configuration, accepted batch/capture identities, zero live workers/transactions, no final output or publication, and no accepted successor. Stop on an unexpected identity or committed result; do not repair by reset or overwrite.

The retained run and CSV attempt still say `RUNNING`; those records are not live-process proof. Define an audited recovery operation for this exact interrupted owner. After proving it has no final outputs, publication, consumed capture or successor, use the canonical failure/lifecycle boundary to record the external interruption. Preserve its input and failure provenance. Do not issue arbitrary SQL status edits or relabel the old attempt as the new successful run.

Resolve the actual continuation interface before the final run. The existing `--retry-capture` path expects a failed capture owner and a distinct execution revision; publication-only `-Resume` cannot recover this calculation. Prove whether that path can reuse this accepted CSV batch and committed capture without reparsing/restaging or rewriting unchanged populations. If a narrow recovery adapter is necessary, implement and test it within the backend boundary, preserving the accepted input root and original receipts. Do not describe unsupported reuse as already available.

Add lightweight begin/end/failure timings around these existing boundaries:

1. Accepted-input reconstruction and reference checks.
2. Entry master/supplier/daily preparation.
3. Control processing and master snapshot.
4. R1 context preparation and order processing.
5. Requirement passes and rationing/report assembly.
6. Pick input joins, queue construction and truck iteration summary.
7. Remaining BPR processing, DBM and BTR, separately.
8. Finalization/qualification, typed output commit, input archive, report preparation and publication.

Each record should identify run/attempt and stage, elapsed wall/process CPU time, available memory observation, input/output sizes and success/failure. Capture Pick queue sizes, truck-iteration count and candidate-match counts as bounded summaries. Emit records when a stage starts so a deadline stop remains attributable. Do not log business payloads or one line per row/truck, retain trace graphs, or let instrumentation alter outputs.

Use a standard external profiler on existing valid retained fixtures and focused component workloads to identify call costs. Include a bounded stage-only probe on captured large populations only when small fixtures cannot expose the scaling issue; it must not create a production day, apply actions, write results or become another full-day campaign. Do not run the unoptimized full large day again to manufacture a baseline. The one final large run uses low-overhead stage observations, with any sampling mechanism and overhead settled before launch.

### B. Optimize the six areas, proving each affected boundary

| Area | Implementation boundary | Proof required before integration |
| --- | --- | --- |
| 1. Pick truck-loop matching | Replace global row/snapshot/formed-pick scans with ordered multimaps using the exact respective SQL join predicates. Rebuild or update iteration-local indexes when quantities change. Keep the global truck loop and its progress/termination rules. | Exact formed/residual rows, truck numbers, cumulative quantities, capacity crossings, duplicate joins, ambiguous-update rejection and mixed partition behavior versus baseline. No added join keys. |
| 2. Pick input joins | Index SKU attributes, location attributes, vehicles and parent mappings once per immutable generation. Reuse ordered candidate lists in eligibility and later dimension validation. | SQL equality and NULL exclusions, source ordinals, repeated attributes, filtered/unfiltered dimension candidates and approved weight-only behavior unchanged. |
| 3. R1 preparation reuse | Carry an internal, operation-owned prepared context through timeline/order/engine boundaries. Share immutable master/hierarchy/stock structures; invalidate or recompute order/control-dependent fields when their real source changes. Do not expose a caller-supplied bypass token. | Both calls' dependency map documented; stock, Norms, thresholds, routing, order identities, closure validation and changed-control rejection remain exact. Root and successor cases both covered with retained fixtures. |
| 4. State-copy lifetime | Replace full-state deep copies with explicit changed-table copies and safe sharing of immutable populations. Release no-longer-used contexts at known lifetime boundaries. Keep independently retained report snapshots isolated from later mutation. | Baseline and candidate complete states match; input/previous-stage objects do not change; required historical/report snapshots remain stable after later rules; memory scales with live required state rather than all earlier generations. |
| 5. Serialization/hash/sort reuse | Reuse already accepted operation-local identities and computed sort keys where dependencies are identical. Avoid serializing whole graphs repeatedly to derive the same identity. Preserve versioned digest/wire contracts and consequential ordering. | Types, decimal/date wire forms, NULLs, duplicates, JSON/download contents and authoritative roots remain valid. No removed integrity boundary without an equivalent trusted owner/revision check. A sort is removed only if downstream order equivalence is proved. |
| 6. Requirement template construction | Inventory fields actually read from the preliminary Track A output. Factor shared Norm/demand/template preparation so unnecessary preliminary result construction can be avoided, without creating an alternative formula implementation. | Keep both canonical R1 passes, their advance allocation, frozen CNR and residual behavior. Prove every consumed template field and final output equal. If profiling shows negligible cost or safe separation is unproved, retain this area and record the reason rather than forcing a rewrite. |

Implement the six evidenced structural costs using architectural dataflow, operation counts and ownership/lifetime reasoning. Neither attribution of the interrupted large-run bottleneck nor a successful unoptimized large baseline is a prerequisite. Tiny-fixture timing alone does not justify retaining a known avoidable cost. Implement the structurally consequential hotspots first. Resolve Pick joins/loop matching together and preparation/copy/serialization reuse together where their ownership overlaps. Keep changes inspectable in logical commits; do not wait until all six are edited to discover the earliest divergence.

Primary source boundaries are `mta/temporal/chain.py`, `entry_preparation.py`, `mta/planning/engine.py`, `mta/application/r1_input.py`, `r1_calculation.py`, `complete_daily_pick.py`, `mta/domain/remaining_capabilities.py`, and affected control/DBM/BTR functions. Select actual files from the measured dependency map; the list does not authorize unrelated refactoring.

### C. Focused correctness, integration and candidate packaging

Use the pre-change source as the component comparator, executing baseline and optimized functions on independent copies of the same retained valid inputs. Reuse existing accepted legacy/component fixtures; do not create a new legacy campaign. Compare complete values, not only counts, totals or digests.

The focused matrix must include:

- Exact matches, duplicates, NULL/case/trailing-space comparisons, partial and full trucks, multiple vehicles/partitions, ties, all approved dimension modes, no-progress detection and genuine ambiguity rejection.
- Zero-quantity orders and already-approved high policy thresholds; no renewed business-rule debate or silent input adjustment.
- Changed and unchanged masters, NonNMS/no-Norm cases, accepted controls and actions, hierarchy/season/phase dependencies, multipart order identities and reservation behavior.
- Both requirement passes, rounding/overflow limits, CNR/advance stock/GIT sequencing and final allocation conservation.
- Copy isolation, stage-snapshot stability, rejection paths, stale revisions and altered-reference denial.
- Recovery reconciliation, absence of partial outputs, exact retained-input selection, distinct attempt ownership, source compatibility and rollback on commit failure.

Run focused repository tests and affected integration checks. Use real PostgreSQL for recovery/finalization ownership proof, on the smallest already-authorized isolated test boundary; never perform destructive fixture tests in the loaded working instance. Do not add resources by inference. Broaden testing only for changed contracts or unresolved failures. A focused independent review should concentrate on joins, mutation ownership, template equivalence and recovery integrity.

Build only the MTA candidate from an exact committed export, preserving the original image. Before installing it, prove source-bound compatibility with the retained opening, certificate and captured-input manifests. The existing M4 upgrader must not be assumed to admit an arbitrary later image. Use a supported, narrowly scoped release transition if required; preserve historical producer identities and seals rather than forging a current-source receipt for old inputs. Backend instrumentation should not require business schema changes; any necessary recovery metadata migration must be genuine, additive and verified.

Keep the existing physical backup and matching MTA files/configuration/secrets. Validate their identity and applicability without another full archival campaign or destructive restore. Prove all candidate recovery/configuration prerequisites before starting the final worker. No changes to frontend, MTO, auth or unrelated services.

### D. Exactly one final large-data acceptance attempt

After component proof and compatibility checks pass, run one candidate continuation of the same April8 input cut on the same installation, from its original committed opening. Use a distinct audited calculation attempt/revision linked to the preserved interrupted capture. Never execute the previous accepted CSV/master operations again merely to start the candidate.

Start the operation timer before recovery/input reconstruction; do not hide that time by starting it only at the formula call. Retain the existing 120-minute operation bound, 20 GiB free-disk reserve and unchanged host resources unless the human explicitly changes them. Use one sequential native worker and the existing fail-closed resource observation; do not quietly add parallel workers, remove limits or introduce timeout extensions. Calibrate profiling overhead on focused fixtures before this run.

Required acceptance:

1. Exact captured inputs/configuration/opening selected; original master/opening records and historical receipts preserved, with no master reload, altered facts or extra date.
2. All required calculation boundaries, Pick, DBM and BTR finish. Record stage timings, memory, row/byte volumes, Pick iteration/candidate counts and finalization cost separately.
3. Complete typed results commit atomically under the candidate run, with correct capture consumption and histories. Independently reconstruct required outputs and verify types, values, NULLs, duplicates and ordinals, plus real action/lineage ownership where applicable.
4. Required native report layers, archives and Pick downloads are produced from those committed outputs; file contents and API/backend contracts pass. No generic empty response or count-only success.
5. Prepare and publish/select only through the existing supported backend admission path, within the explicitly released working-instance serving boundary. Preserve MTA rollback and all other service identities. If serving/UI access is not released or browser control is still unavailable, record that boundary as pending; do not claim full connected acceptance. Do not rebuild or replace the frontend.
6. Worker terminates successfully; no active calculation job or open transaction remains. Report the original interrupted run and new accepted run separately. Do not mistake the old retained `RUNNING` header for a second live worker.

There is no full large-data reference output today. The final report must distinguish complete generation/persistence/contract proof from exact legacy parity coverage. Use applicable retained fixtures and independent invariants, and disclose where no complete large-data golden exists. Do not manufacture an all-row parity claim or use an earlier failed run's duration as a successful baseline.

On any mismatch, resource breach, deadline, unexpected prior result or candidate compatibility failure, stop the exact owned operation and preserve its state, logs and partial artifacts. No automatic restart, reset, accepted replay or second large acceptance attempt. Diagnose the earliest concrete failure and bring back only the smallest recovery/scope decision that is actually needed.

## 4. Measurement and scope limits

The final report should show preparation, numerical calculation, Pick, DBM, BTR, persistence, archive/report and serving costs separately, with CPU/memory observations. Compare baseline/candidate on matched focused workloads; the first completed candidate large day establishes an absolute large-data result, not a proven full-day percentage speedup.

The earlier input-write/revision-guard amplification is a separate known cost from these six calculation areas. Reusing the accepted capture should avoid unnecessary repeated intake, but final output persistence may still incur that writer cost. Measure it explicitly; do not report faster calculation as a fast complete operation. A broader database-writer redesign is not silently included in this plan. If it blocks acceptance, report the measured dependency and the smallest additional change required.

No current evidence supports an honest completion-time promise for the large day. Success here means the complete released flow finishes inside the unchanged agreed bound, with full required correctness and resource proof. A faster but semantically different result is failure.

## 5. Handoff and release

Deliver one optimized MTA package/source identity; component equivalence and focused profile results; one final large-run record; complete stage/resource timings; typed readback and report/download evidence; preserved-instance/old-attempt reconciliation; rollback instructions; and exact remaining UI/deployment limitations. Keep secrets and dumps outside Git.

Update the existing tracker at meaningful functional exits: profiling/earliest hotspot established; integrated candidate equivalence passed; final large-data acceptance passed or a real blocker. Do not add routine per-command approval gates or a new queue. Do not declare M4 complete while any of its agreed connected exits remain unproved.

This plan was originally written before implementation release. Actual subsequent human/controller decisions in the sole TRACKER govern execution; plan text does not create additional runtime authority. Genuine exceptions remain business-rule/input/acceptance changes, frontend/MTO/auth/security changes, protected-service impacts, resource expansion, deadline relaxation, destructive recovery or deployment/cutover. Routine in-scope engineering choices do not need separate human approvals.

## References

- [Terminal proof](D:/freshvcf-build/evidence/ingestion-m4-20261021/terminal-proof.json), [capture proof](D:/freshvcf-build/evidence/ingestion-m4-20261021/capture-proof.json), [operation measurement](D:/freshvcf-build/evidence/ingestion-m4-20261021/daily-measurement.json).
- [Calculation timeline](I:/VectorFLOW/mta/temporal/chain.py), [R1 preparation](I:/VectorFLOW/mta/application/r1_input.py), [requirement passes](I:/VectorFLOW/mta/application/r1_calculation.py).
- [Pick joins](I:/VectorFLOW/mta/application/complete_daily_pick.py), [truck loop](I:/VectorFLOW/mta/domain/remaining_capabilities.py).
- [Existing retry eligibility](I:/VectorFLOW/mta/runtime/production_daily.py), [day ownership](I:/VectorFLOW/mta/runtime/temporal.py), [finalization/failure services](I:/VectorFLOW/mta/runtime/services.py).
- Legacy [BPR sequence](F:/VFlow_Local/local-runtime/mta-engine/Engine/RunCoreBPR.bat), [Pick SQL](F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR/Ration_Scripts/GenerateLogisticPickList.sql), [two requirement passes](F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR/Ration_Scripts/CalculateReq.sql).

These source links refer to working trees. Reconcile the actual implementation baseline before editing; this document does not assert that later source changes have already passed acceptance.

## 21 October native input-contract follow-up — source proof, runtime stopped

The later optimized continuation used the same loaded opening and accepted CSV capture, without master reload, CSV restaging, history or extra dates. Its latest run `9039402d-14d9-4d7d-b5e7-9ecf85753eb0` failed during control processing after entry preparation passed. It is not a completed-day benchmark: all three retained attempts are FAILED, their captures remain CAPTURED, and no output checkpoints or UI publication exist. The original initialization seals remain unchanged; the original frontend/auth/MTO/Redis/PG IDs remain unchanged, and MTA is in maintenance.

The source-only consolidated correction addresses collection ownership and identity contracts, not calculation formulas. Immutable persisted inputs stay immutable; only explicit current working populations receive mutable rows. The existing typed atomic finish, native preparation, selection and archive consumers remain the owners of their respective operations.

| Consumed boundary | Representation and responsibility | Correction / proof |
|---|---|---|
| Whole frozen input | 233 collection paths; 22 flat populations actually decode as RecordRows above10,000 rows; nested child owners and bounded settings/flags remain lists | Complete frozen metadata matrix, and exact equality between its22 paths and the test adapter; real packing/reconstruction code with in-memory images, unchanged small fixture values |
| Master/daily entry | Immutable source rows retain types, NULLs, duplicates and ordinals; canonical producers construct current mutable masters/raw daily rows | Existing lazy BIT conversion and owned raw-day boundary; active/inactive full flow and original-entry reproduction |
| Calculation configuration | Current stock/policy rows are transformed; SKU/location/exclusion and vehicle arrays enter existing list/JSON contracts | Owned filtered stock/policy rows and explicit current configuration arrays; no materialization of opening/history graphs; full type/value/order/digest equality, including large-configuration shapes |
| Orders | Current established orders and current-day feed enter the unchanged list-based producer | Own only current SpikeOrderData/order_feed; keep validation, identity counters, routing and order semantics unchanged |
| Controls and DBM | Control projections create working rows; current stock/consumption/order suspension flags have in-place writers; historical observations stay read-only/new generations | Copy immutable current flags once at DBM entry. Positive pre-existing flags exercise forced/final writers; empty collections alone are not accepted as mutation proof. Order flags already have a fresh prior producer in the actual route; the adapter is a no-op for lists |
| R1/Pick/BPR/BTR | R1 receives produced current rows; Pick projects attributes and creates owned output; final BPR/DBM/BTR replace current tables and retain historical generations | Complete eager-versus-persisted-shape connected flow reaches each normal producer; original inputs and earlier result snapshots remain unchanged; no new allocation or business policy |
| Typed commit and public identities | execute_day/finish_run retain atomic ownership; run UUIDs, public attempt UUIDs and internal numeric keys remain distinct | Real SQL rollback/commit/consume, stale/foreign/numeric/race/depth denials, full typed input/output audits and original certificate preservation |
| Native report/archive | Existing native preparation and selected output remain separate from calculation; archive logical input root differs from expanded capture checksum | Captured wrappers resolve the existing validated physical owner for archive digest-kind metadata; both wrapper versions preserve complete original/archive bytes and hashes |

Evidence root: `D:/freshvcf-build/evidence/daily-optimization-20261021`.
`native-input-contract-matrix.json` records every collection path, producer, representation, ownership, field roster and proof. `native-input-contract-audit-proof.json` binds changed source/test hashes and the matrix. The original entry, stock-opening, nonempty suspension and archive-kind failures have retained reproductions.

Final affected verification:63 tests passed in8.107s, including complete active/inactive results, positive current flags, variable-size configuration, invalid-policy error equivalence and input/previous-snapshot nonmutation. Actual PostgreSQL proof:2 tests passed in130.288s, including atomic late rollback, commit, consumed capture, real UUID boundaries, report preparation, archive open/readback and selection. That SQL snapshot preceded only the final pure-calculation current-flag copy; the final delta has complete nonempty eager/persisted value/error/nonmutation proof and changes no SQL/storage/commit boundary. `chain.sql-proof-snapshot.py` records that qualification. The empty scratch DB was removed after exact ownership and zero clients were checked.

This source correction has NOT been built, activated or run against the large data. It does not establish large-day completion, throughput, UI usability or universal historical-load capacity. The last deployed candidate remains source95931b3f/image7734c3c3. Further execution requires a concrete decision: the additional attempt was consumed, and the two-hop guard still rejects another continuation. No recovery-depth expansion, new image, reset/reload, new date, deadline/resource increase or runtime restart follows from this audit. Browser acceptance also remains pending.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

## 7. Consolidated remaining R1 scan correction — planning only, 21 October 2026

**SUPERSEDING DIRECT HUMAN RELEASE:** the running worker has been stopped safely; implementation of this entire section is now authorized. The planning-only paragraphs below describe its original preparation state and do not hold implementation. Scope/proof/resource restrictions remain. No further large run or new deadline is released; TRACKER is the sole current authority.

### Decision and current boundary

Use local, generation-owned lookup indexes and grouped aggregates to remove the remaining repeated searches across R1 preparation, orders, requirements, rationing, report projections and native allocated-order production. Keep the existing producers, formulas, statement order and day transaction. No alternate engine, global cache, schema migration, concurrency or split-run implementation is proposed.

The human requested this plan while the final April8 attempt continues. This section is a proposed correction to the same effort, not a replacement plan, status queue or implementation release. TRACKER remains the sole status/authority record. No source edit, agent interruption, profiling attachment, test campaign, rebuild or restart is authorized by preparing this section. Do not change the running source/image/operator. Its recorded deadline remains 2026-10-21T09:05:26.030330Z (14:35:26 IST); this plan does not extend it or release another attempt.

Research reference: clean production source `8b4993422ca31fc65d699be929ca088da3697579`, image `sha256:d4f60ba6de7ea41a628474123da91641a5be5e272d77d5ccadfe78855d1e8d81`. Existing initialization, accepted inputs and failed-attempt evidence stay authoritative. If implementation occurs later, reconcile the then-current committed outcome before selecting any input or execution path; never assume the currently running attempt failed or may be replayed.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

### Evidence and limits

Static review confirms the scan patterns below. The original six-area implementation left the listed projection/order/allocation files unchanged from installed baseline `be480eb4`. Preparation reuse and reduced copy/requirement counts do not establish that every R1 consumer scales efficiently. Small fixture timings were mixed. The earlier review was incomplete: it did not inspect all downstream consumers, and the specified separate R1 preparation/calculation observations were collapsed into one timer.

The active R1 timer cannot identify the currently executing function. CPU use alone proves neither internal progress nor hotspot attribution. For N requirement rows and N unique matching inventory rows, two searches from the start perform approximately N(N+1) candidate examinations; about 9.4 billion at 97,000 rows. The native allocation stock join performs N by S full examinations when inventory and stock populations have sizes N and S. These are structural cost estimates, not measured durations or a promised speedup.

Native `production_order_sources.produce` and `production_order_allocation.allocated_orders` execute after the present R1 timer ends and before Pick begins (`chain.py:455–482`). Include them in this correction and measurement boundary. Their cost cannot explain a still-open R1 timer but can cause a later untimed delay.

### Architecture invariant and affected contracts

Persisted opening/facts and current producer outputs remain the sources of truth. Indexes are disposable derived views over those rows, never a substitute for authoritative state or admission. `execute_day` and atomic `finish_run`, existing input/capture manifests, public attempt UUIDs, internal keys, histories and publication ownership remain unchanged.

Before editing each join, record its exact key/comparison, unique versus multiple-match contract, row representation, mutation owner and generation. Exact Python tuple comparisons remain exact; SQL-style joins retain their existing `_sql_key`/`_k` handling, including case, trailing spaces and NULL nonmatches. Do not standardize them into one comparison rule. A scalar dictionary is allowed only where the existing producer proves unique grain. Otherwise use ordered lists of original row references, retaining every occurrence and the same first-match, all-match or `_winner` ambiguity behavior. Keep original ordinals separately from lookup keys.

Preserve NULL versus zero versus missing, signed quantities, Decimal scale/rounding, dates, controls/effective dates, both canonical requirement passes, frozen first-pass CNR, routing/allocation priority, SQL identity generation and known legacy defects. No changed quantities, policies, tie-breaks, assertions or rejection behavior. Building an index must not eagerly raise a later validation error before the original earlier failure point.

### One correction scope

Symbols below are the implementation boundaries; line numbers are research locators in source8b499 and will move.

| Boundary / current cost | Proposed correction and expected growth | Specific preservation proof |
| --- | --- | --- |
| `planning/projections.py:_requirement_band_rows`, lines203–212: two inventory scans per requirement, O(N²) | Build/reuse one exact `(sku_code, location_code)` inventory lookup from the validated same-generation foundation; retrieve both fields from the same row. Expected O(N) construction plus O(N) lookups. | Full band input/output values; missing-key and duplicate-grain behavior; do not replace existing first-match semantics with last-wins unless uniqueness is already mechanically established. |
| Same function, lines174–185: direct-advance allocations search all BPP rows, O(A×B) | Build the exact ordered membership/lookup needed by `(order_id, destination, colour)` once. Preserve short-circuit conditions and the original predicate. Expected O(A+B) plus matches. | Direct NULL-destination versus routed advances, White/non-White BPP, repeated order IDs/parts and duplicate rows; no additional join key. |
| `application/r1_order_input.py:reconcile_order_feed`, lines130–165: each feed row searches/rebuilds retained orders and Elephant rows, O(F×O + F×E) | Build ordered buckets using the existing normalized identity. Apply each feed row sequentially to its current bucket; retain occurrence/order references and stage deletions without globally compacting on every row. Emit the final live sequence once. Index new rows and removals immediately for later feed rows. | Repeated/amended feed keys, PSO-to-Spike promotion, multipart orders, Elephant conversion/cap, missing versus empty feed, closure history, generated identity order and exact rejection sequence. Never reorder feed processing. |
| `application/r1_input.py:prepare_r1_current_day`, lines825–827; `_prepare_r1_orders`; `domain/r1_current_day.py` route functions | Prepare per-SKU location membership once rather than once per master row. Reuse validated immutable route-node lookup per SKU, with validation at its existing semantic boundary. Expected O(N + order route lengths), rather than repeated per-order map construction. | Same node closure, duplicate rejection, current controls, established/new Spike behavior, route ceiling/cycle detection, first service and DueDate. Public standalone functions retain their complete validation path. |
| `application/rrr.py:calculate_rrr_groups`, line84: scan participants for every allocation, O(sum K²) | Reuse the already-built participant lookup after proving its existing group uniqueness; read `virtual` from the same participant. | Virtual/direct rows, deleted negative-parent groups, exclusions, quantities, order and missing/duplicate behavior; all rationing arithmetic unchanged. |
| `application/r1_calculation.py`, line248; `application/r1_rationed_report.py`, lines115–116: sibling lists and averages repeated per child, O(sum K²) | Prepare immutable child/peer tuples once per parent; compute the existing average function once per unchanged group when first needed. Share references, not a copied peer list per child. Expected O(N) group work plus existing sorts. | Zero/positive Norms, direct nodes, excluded children, validation and overflow ordering, exact averaging/rounding and reported sibling/child values. Do not change membership of either group. |
| `r1_calculation.py` phase-out membership and `rrr.py`/`planning/projections.py` exclusion membership: O(N×list size) | Retain ordered authoritative tuples; derive operation-local frozensets for membership only. | Exact identity comparisons, phase-out effects in both passes, physical versus `_SYNTH` exclusions and exported ordering. No normalization change. |
| `r1_calculation.py` level grouping and due-route selection; `domain/order_closing.py` new-Spike level selection: repeated scans per hierarchy level | Group immutable keys/routes by their actual existing level, preserving per-level order and the canonical loops. Pending mutable orders remain owned by their existing sequential producer. Expected O(N+R) grouping plus necessary per-level/allocation work. | Both canonical passes, level order, source depth ceilings, same candidates seeing pre-insert state, generated identity order and loop termination. Do not shorten legacy loops or parallelize dependencies. |
| `application/production_order_sources.py:produce`, lines27–74: repeated order/BPP/master joins and self-colour/date searches | Prepare exact order-part/UUID-independent business identity, ordered BPP/route/master/colour buckets. Replace repeated scans without dropping duplicate matches or `_winner` checks. Expected linear index construction plus actual matching/output work. | Customer ID versus OrderKey/part distinction, normalized SQL predicates, direct self rows, NULL routes, future dates/White colour and conflicting-update denial. |
| `application/production_order_allocation.py:allocated_orders`, `_matches`, `order_for`, `eco_one`, `pack_variants`: inventory×stock full join and repeated master/band/attribute/order searches | Build ordered join indexes per immutable population. Index unique EcoStock rows by existing canonical grain and refer to current mutable rows. Reuse stock index for the initial join; retain all attribute pack variants. Expected O(N+S) for the initial stock join and join cost proportional to matches thereafter. | SQL NULL exclusion, duplicate expansion and ambiguity, missing-row defaults, all stock/GIT/capping/pack results. Preserve `_winner` validation; never replace an all-match join with one row. |
| Same allocation producer: per-stock output totals, per-target remaining-quantity scans and final colour/date updates | Compute grouped totals and ordered source candidates once at each existing statement/phase boundary. Rebuild when membership or quantity generation changes; retain simultaneous UPDATE-source snapshots where applicable. | Preserve subtraction of original `Qty` where legacy does so, every stock-before-GIT transition, rounding, cumulative pack order, mutable-row refresh, exact hierarchy-loop progression and final typed output ordinals. |

This is the bounded inventory of confirmed patterns in the inspected native R1/Pick-handoff path, not a claim of a universal complexity audit. Existing BOR/BOR-OA projections, indexed report-leftover joins, memoized requirement-band hierarchy traversal and bounded colour passes should remain as they are unless profiling reveals a separate problem. Nested loops over required output matches are legitimate; do not label necessary duplicate Cartesian output or canonical allocation work redundant.

### Implementation order after a separate implementation release

1. Freeze a reference to the current source, accepted graph and terminal result of the ongoing run. Add bounded substage observations first, covering source/context preparation, order reconciliation, dependency check/order routing, two-pass requirements, RRR/PSO, band/BOR projections, rationed report, native order-source assembly and native allocation. Preserve the top-level timer for continuity. Log counts and phase summaries, not payloads/per-row events. No live instrumentation of the current worker.
2. Remove the two full-population joins first: requirement-to-inventory and EcoStock-to-stock calculation. Integrate ordered immutable lookup indexes with the current validated owners. Prove each affected output before moving to mutable joins.
3. Correct native order-source/allocation lookups and feed-order bucket maintenance together with explicit mutation/refresh boundaries. Use local functions/data structures; do not introduce a new cache framework. Review all `_matches` call sites in that bounded allocation producer so its repeated search class is corrected together.
4. Finish group-derived work: routing membership/lookups, RRR participant reuse, sibling tuples/averages, membership sets and level buckets. Keep required sorting, formula calls and sequential loops. Combine into one candidate, then verify the full affected flow and package once.

Logical commits may separate inspectable changes, but there is one integrated correction and one acceptance record in TRACKER, not one approval/run programme per issue. Do not overlap CPU-heavy proof work with the ongoing large worker. No benchmark-time promise or additional large-run permission is inferred from this plan.

### Proof criteria

- Qualify actual producer-to-consumer representations before a large execution: ordinary lists, actual file-spooled immutable RecordRows above the representation threshold, nested child owners and mutable current rows. Exercise the changed native entry path, not only standalone fixture functions. Verify input and earlier snapshots remain unchanged.
- Compare baseline8b499 and candidate on independent copies of the same retained valid cases, preserving every value, type, NULL, duplicate, ordinal, date, error and required output file. Reuse existing small fixtures and recovery proofs where unaffected. No all-row legacy parity claim without a complete reference.
- Add focused nonempty cases for every changed search: multipart/repeated orders, duplicate join candidates including conflicting winners, NULL/case/trailing-space identity boundaries, signed/zero stock, zero Norms, nonempty phase-out/exclusion lists, wide sibling groups, multilevel routes and mutable updates. Independently derive selected requirements/allocations from the authoritative SQL/formulas to avoid merely matching a shared defect.
- Measure scaling with focused component populations at n, 2n and 4n: include many SKUs/few locations, one SKU/many locations, wide parent fan-out, high feed/order counts and duplicate-match density. Reuse retained populations where applicable; any test-only constructed cases remain isolated, never substituted into accepted business inputs. The old algorithms need only run at bounded affordable component sizes, not another full large baseline day.
- Count index builds, lookup probes, scanned candidates and produced matches. For removed full joins, candidate examinations should grow with input plus actual matches, rather than n-squared. Measure CPU/wall time and peak memory as well: fewer calls alone are insufficient, and added indexes must fit the existing resource envelope. Record index preparation cost and release at the consumer's last use; do not retain indexes in traces/state/digests.
- Complete one small persisted native integrated flow through controls, both R1 passes, Pick, DBM/BTR, atomic typed commit/readback, reports/archive/selection and actual affected SQL rejection/rollback boundaries. Reuse unaffected proofs with explicit source/delta qualifications. No destructive tests against the loaded working instance.
- Only after implementation and focused proofs are released and pass, propose any necessary large acceptance against the then-current retained state. The currently approved final run does not authorize another April8 execution, replay of an accepted day, extra recovery hop, new database, resource growth or deadline extension. A further attempt needs a concrete separately approved packet.
- The final report must show each substage, index cost, actual matches, peak memory and end-to-end outcome. Preserve current browser/UI limitations; backend improvement alone does not close connected application acceptance.

### Trade-offs and architecture status

Recommended architecture: local ordered indexing/group reuse with explicit mutable ownership. Expected benefit: remove confirmed n-squared searches while retaining the same business producers. Cost: O(input rows plus indexed occurrences) auxiliary references and careful invalidation. Use only indexes justified by consumers; release them promptly. A database rewrite, surrogate-key migration, global memoization, concurrency or new retry framework adds risk without being required to correct these scans and is excluded.

Architecture is recommended from static evidence. Affected contracts are identified but candidate qualification is pending; no correction has been implemented or tested by this planning activity. Integrated candidate verification, measured speedup, full large-data completion and connected UI acceptance remain pending. The running attempt continues under its existing frozen package and deadline.

## 8. Exact next-operation proposal — NOT released

Section7 source, focused proofs and one unactivated package are complete. Its result does not authorize another large execution. The reviewed checkpoint has latest96138/87c3 still RUNNING/CALCULATE as interrupted metadata, no outputs, and exactly three immutable capture wrappers. Existing original and third-hop continuations cannot admit this leaf unchanged.

The single next decision packet is D:/freshvcf-build/evidence/daily-optimization-20261021/r1-next-execution-proposal/decision.json (SHA256 04e151650f9d6a5242d445b0d6478ef646a8990baa4b26a14ac0808ea854a14a). Its three-file candidate-unapplied.patch is SHA256 f1073c1626ae26ba1ac8170cb703536437c8017ff80ed05eb166830782309944. The patch passes AST parsing and git apply --check only; it has NOT been applied, runtime-tested, built or activated. Business source remains7de537cf and the existing package5542e7d7 remains unchanged.

Proposal: extend only the explicit interrupted-capture branch to one fourth canonical continuation, preserving V1/V2 wire formats/default writer limits and denying a fifth. Under the existing locks/atomic capture transaction, reconcile only the human-stopped96138/87c3 through normal fail_run/attempt metadata, create one new owner, and reuse the same physical accepted inputs. Filesystem or transaction failure must restore the interrupted state and leave no accepted new owner. Add only the exact completed fourth-prefix resolution predicates, never clear or rewrite earlier failed rows.

Before any large operation, require focused old-default/valid-fourth/denied-fifth/foreign/cycle/sibling/stale-cut/exclusive-lock/filesystem+late-SQL-rollback proof, then one actual small native commit/readback/report/archive/selection flow in the same exact owned scratch DB on the same PG. Build one MTA image after those pass, verify its actual bytes and all source pins, and append a compatible source release through the existing registrar without changing the original opening/certification/schema/roles.

The packet freezes exact initialization/root/capture/attempt/source/configuration/certificate/prefix/live-cut bindings. It proposes at most ONE same April8 large attempt, no master/CSV restaging/history/extra day/legacy rerun. The requested cumulative allowance is120minutes starting once before the first approved source edit, including proof/build/transition/reconstruction/calculation/persistence/report/terminal checks. Start and deadline are unset until a real decision; no clock reset or automatic retry. Existing resources/private network/mounts/20GiB C/D/I reserves and failure stops remain. Frontend/MTO/auth/serving and all protected resources remain untouched. Actual browser/serving acceptance is excluded from this backend operation.

One human question, after packet review:

> Approve the exact three-file interrupted-capture correction, focused proof and one MTA-only build, then one April8 run from the saved inputs on the same instance within one cumulative120-minute window, including atomically recording the stopped attempt as FAILED? No master/CSV reload, history import, extra day, resource increase, frontend/MTO/auth change or serving activation is included.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
