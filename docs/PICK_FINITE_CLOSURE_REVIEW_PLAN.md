# Pick: end-to-end review and finite closure plan

**Approved contract:** direct human controller turn
`01a11a8b-e70d-74f0-899a-f9e034e42938` authorizes this five-step plan and D1–D4
within the existing goal, then stop after Pick delivery. The original review
below is retained as historical reasoning; current status is only in MIGRATION.md.

Reviewed 8 October 2026 against committed base `f7616d7` and the current uncommitted Pick changes. `docs/MIGRATION.md` remains the only status tracker. This document is a supporting review and implementation contract, not a second queue. The executor is blocked; no new business-day, native fixture, benchmark or serving operation was run for this review.

## 1. Verdict and actual blocker

Pick is partly implemented and is not accepted end to end. The immediate blocker is an acceptance rule applied to table retrieval order, not a demonstrated quantity or truck-content mismatch in the failing case. Resolving that rule alone will not finish Pick: nine declared native cases remain unexecuted, several known input domains need an explicit disposition, and actual daily integration is not yet proved.

Retained receipt: `D:/freshvcf-build/complete-daily-assessment/pick-integration-a001.json`.

| Boundary in concurrent-active-queues case | Verified result |
|---|---|
| Formed truck table | All five complete 21-column rows match, including NULLs, types, quantities, ranks, truck numbers, cumulative values and flags; observed retrieval sequence differs. |
| Residual table | Both complete 16-column rows match as typed populations. |
| Observed formed sequence | Native `[A,D,B,D,B]`; modern `[A,B,D,B,D]`. B/L1 and D/L2 are separate partitions. |
| Four downstream reports | Retained report headers/types and complete data-row multisets match for all four. Only the Logistic report data-row sequence differs. This was checked directly from the saved receipt, without rerunning calculation. |
| Harness outcome | FAIL because it requires both table retrieval sequence and exact report-resultset sequence. |

`FixtureSQL.rows()` uses `SELECT *` with no `ORDER BY` (`parity/verify_complete_daily_producers.py:181`). The canonical table definitions have no stored capture ordinal. `verify_pick_integration.py:155` adds strict observed-sequence equality over the complete-row comparison. Its downstream comparison at line175 also compares the whole result object positionally, reimposing report order already qualified by the approved four-file exception.

Canonical `GenerateLogisticPickList.sql` does contain ranking/window order and two ordered INSERT sources. Those calculation orders and stored rank values must stay exact where specified. They are different from the sequence returned by a later unordered table read. The modern `order_native_pick_state()` sorts the final capture to approximate an observed insertion order; further sorting to fit a particular SQL read is not a sound closure strategy.

Canonical source identity verified in this review:
`F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR/Ration_Scripts/GenerateLogisticPickList.sql`, SHA256 `b5044bcb979e57c270d944fdcf3a7998bee33484a384dae89aaaf414c7d05dfb`.

**Recommendation:** approve a narrow relation-order qualification for the two final operational Pick tables, with exact complete typed rows and duplicate multiplicity, exact rank/truck fields, and exact modern ordinal round-trip. Keep raw sequences and the original failure. Do not transfer this qualification to calculation order, ordered queries, API pagination or grids. Apply the already approved four-file qualification consistently in the integration harness.

This is a proposed acceptance change because the current mandate explicitly protects table ordinals. The executor was right to stop rather than silently weaken that mandate. The process problem was defining order acceptance one component at a time; settle the whole Pick boundary now.

## 2. End-to-end evidence and remaining work

| Step | Current implementation/evidence | Remaining exit |
|---|---|---|
| Source position | Legacy RunCoreBPR calls rationed report, bifurcation, Pick calculation and four-file reports. `chain.py:292` derives native Pick input from the modern rationed report and bands. | Prove the actual upstream-to-Pick connection without a stub or manually supplied calculated rows. |
| Five source populations | `complete_daily_pick.py` consumes Pick rows, SKU attributes, location attributes, vehicles and location/vehicle mappings. Native 28/69-column input proofs exist within their declared domain. | Complete occurrence joins, NULL and vehicle cases below. No representative-row shortcuts or hidden missing-input defaults. |
| Allocation and truck state | Complete path uses `calculate_pick_cases_state()` and a global queue loop. Weight/volume and tied-order witnesses exist. | This includes new calculation logic beyond the former narrow output capture; old narrow proofs alone cannot certify it. Finish the fixed native fixture list and retain original ordered allocation checks. |
| Typed storage | Additive migration0080 adds the 21/16-column tables. Three fresh-PG tests prove complete rows, duplicates, ordinals, isolation and rollback. | Bind the current final producer output and prove actual-day readback and successor ownership. Reuse unchanged migration receipts. |
| Daily execution | `execute_day` supports explicit `complete_pick` policy plus owned output root. It defers the old narrow Pick calculation and writes the new results into closing state. | Prove exactly one Pick calculation and coherent source/output identity through the real path. All retry branches must preserve the same behavior. |
| Files | Four existing legacy CSVs have native format/copy evidence in the declared direct-CP1252 domain. Runtime writes per-run output/download directories. | Verify all four from the real persisted producer; document consumer location. A run-owned folder alone does not establish that an existing download consumer can reach it. No serving activation is included. |
| Failure/retry | Two real-PG protocol tests use a stubbed day calculation: file failure denies completion; successful retry reconstructs a missing file from own rows. | Real-path correctness proof, partial-file/failed-attempt isolation and consistent retry entry points; no replay of accepted calculation. |
| Operator access | `run_temporal` calls `execute_day`, but currently has no complete-Pick/output-root option or forwarding. | One supported command must enable the new path explicitly, validate required mappings/root and document recovery. Preserve existing defaults and stopped-run pins. |

The native script/consumer search was bounded to the canonical engine Scripts/Engine and the relevant modern calculation, runtime and presentation files. Within that scope, final truck-table consumers are the four report projections plus relational updates/aggregations. No position-based business consumer of the final unordered table read was found. Existing Pick API/projection contracts must still be protected; this is not an assertion about every external integration.

### Known issues to settle together

1. **Order qualification:** distinguish calculation ranks, final relation retrieval, modern storage ordinals and report sequence as above. Preserve the two existing approved qualifications separately: tied allocation outcomes and four-file export order.
2. **Duplicate SKU attributes with mixed NULLs:** the modern adapter filters both-NULL rows out. Canonical initial/cumulative joins filter them, but later allocation, final weight/volume and load-type joins do not all repeat that filter (native lines188,205,232,239,256). The unit assertion that adding a both-NULL duplicate is harmless is not an end-to-end native proof. This is a concrete source/proof gap, not yet a demonstrated wrong production output.
3. **Multiple vehicles:** the canonical source joins all configured parent vehicle IDs; the adapter currently rejects more than one applicable vehicle. This is an implementation limit, not evidence that legacy lacks the feature. Implement the deterministic native case or record the exact ambiguous UPDATE/window outcome requiring a decision. Do not silently call the single-vehicle subset generic completeness.
4. **Other ambiguous updates:** differing duplicate SKU dimensions and conflicting residual-update candidates currently raise errors. Their behavior is outside the tied-rank approval. Record whether canonical behavior has a unique answer before selecting an implementation; never choose an arbitrary representative.
5. **Known native failure/input limits:** single-NULL underfilled queues can fail to make progress; modern detects and raises instead of looping. Zero/negative capacities, unsupported dimensions, overflow, case-insensitive spelling ambiguity and encoding/display-width limits already have guards. Consolidate these into one supported-domain/failure table. An explicit rejection is safer than fabricated output but is not full compatibility. No execution of a known nonterminating legacy case.

## 3. Proposed acceptance decisions — one consolidated review

Approval of this plan would authorize the following bounded implementation/proof contract. It would not authorize benchmarking, a 21-day run, deployment or client-only work.

**D1 — two-table relation order.** Compare LogisticPickList and PickListDataForTruckFormation as complete typed multisets, retaining duplicate counts and all fields, including NewSRNo, MinSRNo, TruckCount, Priority and flags. Preserve exact modern saved/read-back ordinal sequence and raw native capture sequence. Keep explicitly ordered legacy consumer checks intact. If an actual consumer depends on a differing order, report that exact consumer before applying the qualification there. No new runtime sort or business tie-break merely to make captures match.

**D2 — existing report qualification.** Use exact headers/column types and complete data-row multisets for the four already approved unordered exports; preserve native/modern sequence differences as diagnostics. Test byte formatting using the same qualified input order on each side. Do not claim whole-file byte identity across intentionally different row orders.

**D3 — known unsupported/ambiguous cases.** Finish the fixed source-grounded cases below. Approve fail-closed handling of the known nonterminating legacy domain as an explicitly documented operational difference, with no successful-day/readiness receipt. Do not thereby approve dropping multiple-vehicle support or other deterministic legacy behavior. Any unresolved ambiguity or broader input restriction must be presented together with its exact affected configuration/population; closure remains qualified or blocked until that concrete disposition is accepted.

**D3 clarification issued at the human's direction after question `call_aeedbb88452f48ce9d9b6e9b287e775c`:** the three concrete conflicting UPDATE configurations in `PICK_SUPPORTED_DOMAIN.md` may fail closed only when canonical candidate values actually conflict. Preserve deterministic duplicate and multiple-vehicle behavior, including differing capacities where the outcome is unique. Denials require explicit diagnostics and failed-attempt isolation; they are operational differences, not parity. Existing declared numeric/identifier/encoding restrictions may remain limitations of qualified Pick closure. Any unimplemented deterministic legacy behavior remains a documented production-readiness gap. This resolves that consolidated question and does not authorize new restrictions or unrestricted production-readiness claims.

**D4 — minimal real integration exercise.** After implementation and focused gates pass, authorize exactly two modern daily invocations in one fresh owned timeline, at most ten retained SKU-location identities, using two consecutive retained daily fact sets, existing action policy and each day's own persisted predecessor. Select and pin the existing case before execution; do not invent Norms, recommendations, calculated opening history or facts just to populate a report. It must exercise nonempty Pick output and genuine carryforward. If no retained case meets these conditions, present one input decision instead of generating an improvised case. No timing objective. See proof limits in step4 below.

## 4. One finite implementation batch

### Step 1 — settle acceptance and freeze the case roster

Record approved D1–D4 in the existing exception/tracker locations. Correct the two comparison-policy inconsistencies, without changing the saved failed receipt. Reassess the concurrent-queue receipt offline first; rerun native calculation only when relevant implementation has changed.

The existing twelve-case roster is fixed: original weight, original volume, concurrent queues, duplicate Pick/sticky flag, duplicate Pick plus location, identical duplicate SKU attributes, distinct logistics locations, both-NULL exclusion, both-zero residual, single-NULL exact fit, single-NULL overshoot and zero boundary after a prefix. The first two passed; the third stopped on sequence; nine were not executed. Reuse passing cases where their implementation identity remains valid.

Add only four source-identified cases to this roster: mixed qualifying/both-NULL duplicate SKU attributes; multiple vehicle IDs with equal capacities; multiple vehicle IDs with different capacities; differing duplicate SKU dimensions. Use terminating bounded rollback fixtures or static denial proof where canonical execution is unsafe. Existing tie witnesses are reused if affected inputs/ranking logic remain unchanged. No additional fixture campaign without a new concrete defect.

Before running, publish the complete input/failure-domain table from section2 once. Do not discover and ask about these already known limits serially.

**Exit:** acceptance policies and all sixteen case dispositions are explicit; no hidden generalization from unique positive single-vehicle fixtures.

### Step 2 — finish the existing implementation, together

Permitted files are the existing Pick input/algorithm/projection/file modules, `mta/planning/engine.py`, `mta/temporal/chain.py`, relevant runtime storage/execute_day code, the existing daily operator entry point, their focused tests and supporting docs. Extend this list only for an identified necessary caller. No new engine, profile framework, general registry or unrelated producer work.

Implement deterministic native join/window/update semantics needed by the fixed cases. Preserve known canonical flaws; label approved failure differences. Keep the former path/defaults and accepted artifacts intact. Remove stale declarations that still describe completed materializers as missing.

Complete configuration and command forwarding for the new Pick policy/root, required vehicle IDs, location bindings and own input identity. Do not auto-migrate old timelines. Review all existing-run branches, including the initial opening-key collision path, so a successful retry has consistent file restoration without rerunning calculation. A failed or partial run must not appear complete or replace another run's files.

Keep each occurrence in typed rows with its modern ordinal. Generate the four named files from those rows. Show the existing download/file consumer mapping without a UI redesign or protected serving activation. Reuse the existing daily completion/flag mechanism; do not introduce a separate Pick workflow.

**Exit:** one supported route from real daily inputs to allocation, persisted final truck state and all four consumable files; no benchmark-only implementation or stub in the delivery route.

### Step 3 — one focused correctness pass

Run the remaining/affected fixed native cases under unique owned VFTEST_Fresh resources, rollback and preservation guards. Compare complete typed fields and multiplicities, actual rank/quantity/truck semantics, retained ordered narrow contracts, and qualified report rows. Test deliberate quantity/rank/duplicate corruption so the new order policy cannot hide business differences.

Run affected unit and PG protocol/storage tests, including nonmutation, missing sources, cross-run isolation, file failure, missing-file repair, failed-attempt denial and retry consistency. Reuse the 0080 fresh-schema proof unless storage changed; when changed, perform Django check, makemigrations check, migration plan and migration-enabled fresh owned PG proof. Build one immutable final candidate and record source/image/config identities. No repeated broad baseline campaign.

Stop the current execution on a real failure, preserve it, make only an evidenced in-scope correction, and rerun only failed/affected proof. No speculative retries or partial commits. A second unresolved semantic failure is one consolidated decision, not a new research programme.

**Exit:** all fixed cases pass their explicit exact/qualified/denial contracts, or the remaining supported-domain decision is clearly stated. Fixture count alone is not acceptance.

### Step 4 — prove the real route once, under D4

Use existing isolated SQL/PG facilities, normal 4GiB/twoCPU worker limits, no host ports, resets, borrowed databases or serving changes. Two modern dates are the maximum, not a benchmark budget. No engine warmups or extra mode runs.

Day1 must execute the real chain through Pick, store complete rows and produce all four files. Day2 must read its own persisted predecessor and configured actions, regenerate the next day's Pick sources and preserve day1 outputs. Use the existing action policy; if this small case produces no action, report that honestly and reuse separately qualified unchanged action proof, without fabricating a suggestion.

For Pick parity, use at most one bounded native Pick invocation per date from exactly the five modern-produced source images. These are matched-input Pick-stage proofs, **not independent end-to-end legacy/modern daily parity**. Reuse upstream accepted evidence only after source/config reconciliation; a new upstream divergence needs a concrete decision, not an unapproved full legacy-day campaign.

Read every persisted 21/16-column row and both output/download copies. Repeat the supported command for an already completed identity to prove no recalculation and restoration of one missing file. This is a retrieval/recovery call, not another business-day invocation. Reuse focused injected-failure tests rather than launching extra failing business days. Validate the consumer can access the declared files in isolated facilities.

**Exit:** real calculation-to-storage-to-file continuity on both dates, exact declared Pick comparison policies, no silent repeated calculation, truthful action/consumer limits. No performance or whole-system readiness claim.

### Step 5 — close Pick once

Update `MIGRATION.md`, the supporting assessment and the exact exception entries to remove superseded open/blocked statements while preserving their evidence. Deliver one coherent code/tests/migration-if-changed/runbook/report commit and push. Do not include unrelated dirty files from other work.

The handoff must include: supported configuration/domain; exact operator and retry commands; code/image/input identities; native/modern proof paths; exact versus qualified versus denied cases; two-day integration outcome; file consumer paths; and all remaining limits. The next work item may start only after Pick is closed or explicitly blocked/deferred by the human.

## 5. Scope after Pick

Pick closure is not full generic production readiness. Remaining goal work still includes other generic final writers, enabled files/archives, complete Apply/Sleep and history integration, backup/recoverability and local alert intent orchestration, full operational publication/readers, and the complete daily runbook/handoff. GulfOil remains an opt-in client profile. BOR/BOROA and Guided Excess rolling-history deferrals remain explicit. MTO, deployment/cutover, benchmarking, capacity claims and `temporal-full-001` continuation remain outside this plan.

## 6. Review evidence anchors

- Canonical producer: `F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR/Ration_Scripts/GenerateLogisticPickList.sql` (verified hash above); entry position in `Engine/RunCoreBPR.bat:45`; existing files in `Engine/PickListReports.bat`.
- Table schema: canonical `Scripts/DBCreation/BPR_DBCreation.sql:1659` and `:1686`.
- Current adapter/algorithm: `mta/application/complete_daily_pick.py:20`; `mta/domain/remaining_capabilities.py:218`, `:256`, `:331`.
- Integration: `mta/temporal/chain.py:292`; `mta/runtime/temporal.py:102`; `mta/runtime/management/commands/run_temporal.py:220`.
- Storage/files: `mta/runtime/complete_daily_state.py`; migration0080; `mta/application/complete_daily_batch_files.py`; `mta/application/complete_daily_pick_files.py`.
- Proof definitions: `parity/verify_pick_integration.py`; `parity/verify_pick_tie_witness.py`; `mta/runtime/test_complete_pick_runtime.py` (explicitly stubbed calculation).
- Retained receipts under `D:/freshvcf-build/complete-daily-assessment/`: `pick-integration-a001.json` (FAIL preserved), `pick-tie-witness-a004.json`, `batch-file-format-a001.json`, `pg/pick-storage-a001.json` / `pick-storage-a002.log`, `pg/pick-runtime-a001.json`.

The original review itself changed no implementation or runtime state. Subsequent
human approval above authorizes its bounded qualifications and real-day exercise;
it does not authorize new inputs, extra invocations or broader readiness claims.
