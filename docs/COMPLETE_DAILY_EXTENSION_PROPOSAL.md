# Proposed complete-day boundary extensions

8 October 2026. Decision package for review; **not implementation or execution
authorization**. Human approval authorizes preparing/reviewing this proposal and
independent assessment/timing support. It does not yet authorize the business,
commit or admission extensions described here. `MIGRATION.md` owns status.

## Decision requested

Approve one integrated extension scope only after resolving the configuration and
canonical-behavior questions below. Retain the current oracle and its accepted
receipts unchanged. Add a distinct complete-day execution path in newly owned
resources, and choose explicitly between strict migration-gated publication and a separately
authorized operational-publication policy.
Measure one captured, instrumented two-day exercise per engine; report raw elapsed
and diagnostic attribution, with no claim of an uncaptured production runtime.
Do not restart the original full run or implement performance optimizations.

This direction preserves all work rather than shortening the benchmark by leaving
out outputs or bypassing acceptance. It is larger than adding timers: the
deployed daily boundary has not been fully implemented/qualified by the selected
temporal contract. If uncaptured production timing is mandatory, decide the extra
capture invocation budget before execution instead of relabeling a captured run.

## 1. Exact source gaps and required implementation

| Source / dependency position | Inputs and writes | Modern equivalence / proposed scope | Required proof |
|---|---|---|---|
| `Engine/VectorFLOWv4.bat`: settings/fullkit/sanitation/start gates before import | Site/StdSettings, dates, DataSanitizationResult, directories/configuration/critical-script roster | `execute_day` owns explicit day/MDM/input identity, but is not a proven replacement for the complete BAT gate set. Reconcile each enabled gate and its failure output | Freeze actual selected settings and source rows; missing/stale/invalid feed/date must yield qualified canonical behavior |
| `Scripts/BPR/ValidateBPRBatchExecutionFlags.sql`, after core BPR/vendor/distributor processing and before site PostBPR | Records execution flag; compares BatchFileExecutionDate with RunDateTime; checks critical BPR scripts; updates IsBPRBatchFileExecuted | No equivalent flag implementation found in modern non-migration source. Eight boundary names alone are not equivalent. Define typed completion/status representation and its consumer | Missing critical script, stale date, SQL error-result handling and flag update; no invented success flag |
| `Scripts/BPR/ClearTableForBPRBatchExecutionFailure.sql`, BAT's failed-BPR branch | Truncates BPR_Table, SupplierDispatchReq, vf_PickListReport, vf_RationedReqReport; BAT jumps to finish alert | Modern atomic FAILED/unchanged prior publication differs physically. Preserve the semantic discrepancy explicitly; replacing legacy destructive failure with prior-ready publication requires a named compatibility decision | Failure visibility must be tested on fresh owned data. No protected-table clear, no silent equivalence claim |
| `Engine/SiteSpecific/GulfOil/PostBPRProcessing.bat` calls `Scripts/SiteSpecific/GulfOil/BPR/CalculatedAttributes.sql` before DBM | Current Pick, MasterDataRaw.SKULocAtt01/02, VirtualNorm, Stock/GIT, ParentPackSize/stock. First sets c3 to RationedReq for non-self rows; conditionally overwrites with rounded/capped dispatch; propagates into BPR_Table.SKULocAttr3, Importer.SkuLocAttributeData.c3, NMSAllItems.SKULocAtt03. Truncates Intermediate before/after | No matching post-BPR calculation in current temporal chain. Earlier `r1_gulfoil_input` copies raw attributes; that is not this computed overwrite. New business producer and exact stage position are required if the deployed hook is included | Differential SQL cases for NULL/TRY_CAST, rounding, negative/clamp, pack limits, duplicate joins and native UPDATE behavior. Independent current-day/end-state/UI attribute equality; do not invent duplicate tie-breaks |
| `Engine/GenericFinalProcessing.bat → Scripts/Importer/ValidateBatchExecutionFlags.sql`, after BTR/site PostBTR/runtime reports | Current batch date and full critical ScriptExecutedFlag roster; sets ImporterSettingsTbl.IsBatchFileExecuted | Modern status/root/roster exist but lack explicit critical-script mapping. New completion-owner mapping needed; preserve emitted/error behavior | Omitted critical operation versus optional operation; stale date; complete end-of-day flag; reader denial on incomplete result |
| RuntimeReports at five BAT positions; DownloadInputData; UI upload logs; backup/alerts | Configured active report SQL, tables/files, flags/horizons/paths | Conditional work is included when enabled. Current frozen profile does not specify all deployed operations. Need exact activation/source/file roster, not a guessed empty set | Every enabled file/result/header/export retained and readable. Disabled branches documented from config; no transmission/shared backup during assessment |

Canonical identifiers are recorded in the companion source inventory. Selected
hashes: GenericFinalProcessing BAT
`ef27b6388517c1337c2b2f9216e036bfc8829355a6b7dabc4dc2d8a01620aa34`;
GulfOil PostBPR BAT
`0a4d607eb06315406d064338a3f78f30f5ed04d30fb333dd3bd96dfcf859737a`;
ValidateBatchExecutionFlags SQL
`7c91eab8a46d3d6db540b11ba4bd5ee4daff526d1ffe6cd58ff46b70a8173b67`.
GulfOil PostDBM and Final hooks contain no business commands; record those no-op
paths. Do not infer that all site hooks are empty.

### Additional core outputs identified by review

`RunCoreBPR.bat` continues after the selected `R1_SEQUENCE` endpoint:

| Required operation | Inputs / final output | Mapping and proof required |
|---|---|---|
| `ProdOrderSuggestions.sql` after GenSupplierWiseReq | SupplierDispatchReq + Plants + rationed colour requirements + current plant stock/GIT; regenerates ProdOrderSuggestions, clears scratch | No qualified complete producer mapping yet. Its script warns that the feature cannot be used with order data. Reconcile frozen order workload and actual Plants/config; do not skip it, assume empty, repair SQL or invent a replacement |
| `ClearHistoryData_BPR.sql` | Deletes DailyConsumption and BPR/request/transit remarks at inclusive configured date cutoffs | Modern capture filtering is not the same as live-owner deletion. Map DailyConsumptionHorizonBPR/BPR_RemarkHorizon and all four histories, preserve canonical NULL/cutoff behavior and subsequent reads |
| `Planning.bat` | GITAndExcessInventory, ExpediteDispatches, CollectOrderFulfillmentData | Existing modern narrow projections/prepared consumers are candidates, not proof of canonical table equivalence. Map each source/table/row and required display/file output explicitly |
| `GenerateBPRExceptionReport.bat` after UpdateBPR | Actual nonempty BPRExceptions triggers CSV/ZIP; prior files have defined removal/absence behavior | Data-dependent output, not a RuntimeReports flag. Preserve schema/header/order/content and file availability in owned output directory; no email transmission |
| `PickListReports.bat`, `OrderAllocBasedReports.bat`, optional GenerateModifiedRRR | Qualified Pick/BOR/order populations and configured wrappers/exports | BOR UI deferral does not waive existing batch files/tables. Resolve exact configured output roster; modified RRR flag is not implied enabled by independent RRR acceptance |

### Consolidated direct-call review: further outputs and final writers

The bounded review followed VectorFLOWv4, RunCoreBPR, Planning, RunCoreDBM and
RunCoreBufferTrend plus their named immediate wrappers in the retained atlas.
It found the following additional obligations. This is a finite starting roster;
full settings/branch closure is still an unmet exit, not a passing assertion.

| Operation | Obligation and modern disposition |
|---|---|
| GenericPreProcessing / ResetBatchExecutionFlag.sql | Reset critical-script and completion flags, set batch execution date and mark own execution. Absent in selected oracle; modern run identity is not yet a qualified replacement |
| ValidateParentNorm / ValidationForParentNorm.sql | NoNormParent report/CSV and conditional ZIP/email. Exact modern producer/file mapping unproved; email remains excluded from actual transmission |
| UpdateTaskStatus / NMSTaskStatusUpdate.sql | Runs even when NMSActive=0. Existing modern daily_input consumption/task-pruning owner must be reconciled, not automatically reimplemented |
| OrderAllocBasedReports | BOR CSV and CollectBOR_OrderAllocationHistory / CollectRRR_OrderAllocationHistory are outside the MTO conditional. MTO OrderAllocation/RRR-OA exports depend on IsMTOEnvironment. Existing UI deferrals do not waive batch history/file work |
| GITAndExcessInventory | GenerateGoodsInTransitMaster, GoodsInTransitTransporterMaster, CollectExcessInventoryDetails; map exact outputs to daily transit/Excess source owners, not just similarly named reports |
| ExpediteDispatches | PostRationEcoAvailability, penetration recalculation, UpdatePostRationPipelineInventoryPen and EcoAvailabilityComparision need exact mapping. Existing adapter reuses CollectDataToExpediteDispatches later; stage position and complete dependencies must match |
| GulfOil PostBTR / CalculateAttributeBasedonBTR.sql | Computes rolling c9/c10/c12/c13 and propagates to BPR_Table, BPR/DBM/Importer attributes, SupplierDispatchReq and NMSAllItems; writes Interface.FGTrendData and clears scratch. No qualified equivalent. Core UpdateCategoryCol is not this final site writer |
| GulfOil PostBTR / GulfOil_BTRReports.py | Unconditional Python file/report producer called by pinned BAT. Not registered in the current baseline manifest. Observed canonical and backup hashes are in source inventory; do not claim old SQL-only provenance covers it or import credentials/config |
| DBMNormChange / Norm0–2 / phase-out wrappers | Core resultsets already retained; CSV/ZIP/template output and retention need explicit file ownership. DBMNormChange file creation is unconditional; email conditional. Site SQL selection depends on file existence |
| BTR wrapper files | Tech/Econ/location exports depend on BTR30/60/90Days, LocId and GenerateLocWiseBTR; keep generated tables and files distinct |

Known static defaults from pinned StdSettingsPre plus GulfOil Settings resolve
DailyConsumptionHorizonBPR=90, BPR_RemarkHorizon=90, GenerateModifiedRRR=0,
AutoDBMActive=0, vendor/distributor/VectorDMS=0, OrchestratorImplemented=0 and
GulfOil ActivateNorm0Report30Days=1/BPR_ShowNormZeroItems=1. These are static
settings, not proof of current database-held activation rows. RuntimeReports,
critical-script roster, sanitation/fullkit and alert activation still need a
declared authoritative dataset. Input-download/upload and pre-backup flags are
already present in the frozen opening, as reconciled below. Frozen batch/rule overrides must be
reconciled against those defaults explicitly, rather than silently substituted.
DBM NormZeroOneRuleActive and DelistingofNormRuleActive affect rule activation;
the selected adapter's direct rule sequence is not proof of those settings.

### Frozen configuration reconciliation

The frozen opening itself supplies these authoritative values; they are not
missing settings requiring a default:

| Setting/population | Frozen value and implication |
|---|---|
| GenerateDownloadableInputData / ActivateNMSUIUploadLogs | Both1 in opening.importer_settings and controls.importer_settings. Their file/output work is enabled and must be included |
| IsMTOEnvironment |0 in opening.dbm.VFSettings. Bind the corresponding canonical Importer settings owner explicitly; do not enable MTO order-allocation exports by assumption |
| NormZeroOneRuleActive / DelistingofNormRuleActive |0 /1 in both DBMSettingsTbl and controls.dbm_settings. Reconcile exact rule branches with the selected adapter |
| IsPreBackupActive |0. No pre-backup workload is implied. Post-backup per-database flags still require reconciliation |
| BatchFileExecutionDate |Retained October8,2025 opening value, not the June2026 run date. Canonical reset/date advancement is required; never seed a success date or flag merely to pass admission |
| IsBatchFileExecuted / IsBPRBatchFileExecuted |0 /1 in opening. These are prior state, not proof the new run finished |
| Plants |Seven opening BPR rows; production-order suggestions cannot be dismissed as an assumed empty configuration |
| Orders for this two-day workload |Zero initial SpikeOrderData rows and zero order-feed rows on both June6/7. This narrows the production-suggestion script's order-input compatibility question without proving its result |
| RuntimeReports / ScriptExecutedFlag / DataSanitizationResult / EmailAlertSettings |Absent from frozen opening/profile. Absence is unknown, not empty/disabled; require explicit source/configuration disposition |

The source inventory records exact paths and values. No live database state was
queried or substituted for these frozen settings. The read-only reconciliation
does not authorize the missing business producers or any engine invocation.

These gaps supplement the table above. The coverage map is an inventory under
reconciliation, not a certificate that every deployed operation is implemented.
No source-by-source completeness exit is claimed until every enabled BAT node and
its output is resolved against the pinned configuration.

### Genuine configuration/behavior questions

* Frozen `VECTORFLOW-DEMO` site identity is not a deployed GulfOil settings file.
  Bind GulfOil business hooks to the synthetic workload explicitly without changing
  frozen facts/catalogue. Record a new invocation contract; never edit the retained
  artifact or transfer old all31 receipts to changed producer outputs.
* Resolve the complete enabled BAT flag/table roster from retained authoritative
  settings. A missing setting is unknown, not zero. RuntimeReports activation,
  critical-script flags, fullkit/sanitation and configured output retention are
  not fully declared by the frozen temporal profile.
* SQL `UPDATE ... FROM` with duplicate source matches, TRY_CAST/float conversion,
  rounding and zero/NULL packs must retain canonical behavior. An incomparable or
  ambiguous case is a recorded decision/exception, not a fabricated tie-break.
* SQL catches often return error resultsets rather than throw. Preserve actual
  statement effects and distinguish a stopped benchmark from a changed business
  failure policy. Modern immutable publication versus canonical failed-table
  clearing requires an explicit compatibility disposition before implementation.

## 2. Isolated legacy daily execution and durable publication

Do **not** add a COMMIT switch to `parity/adapters/legacy/temporal_day.py`.
It clears/reloads supplied state and guarantees rollback; its callers and receipts
depend on those semantics. Merely changing its final rollback would not establish
real successor execution or full deployed daily behavior.

Proposed new `tools/complete_daily_legacy.py` plus a narrowly named sequence module:

1. Provision a new unique eight-role VFTEST_Fresh namespace using verified owned
   paths/schema and exclusive lease/restricted principal. Initialize frozen initial
   state ONCE, including declared used order counter and genuine empty workflow
   owners. Setup is reported separately from recurring daily time. Do not copy a
   database, reset an old namespace or copy another engine's outputs.
2. Bind exact canonical SQL text/configuration and explicit same-day facts to the
   declared date and owned names. Use the BAT dependency/branch order, including
   gates, site attributes, final checks and configured reports. Reuse qualified
   source substitution/error-result consumers; record actual executed source
   hashes. Never invoke unreviewed BAT against its original database settings.
3. Preserve canonical transaction boundaries. The real BAT uses separate sqlcmd
   operations; do not wrap the whole day in an invented all-or-nothing transaction.
   Expose state to finite benchmark readers only after the full daily completion
   check. A failed attempt stays in its unique owned database with its actual
   partial effects; it is not reset/retried speculatively.
4. Capture transient comparison images and emitted files before the next writer
   overwrites them. Measure their capture/normalization/compression/hash cost as
   diagnostics while preserving all user-visible exports as required output work.
   Final SQL remains the engine's operational truth, not its evidence archive.
5. Select and execute real Apply/Sleep from SQL's own Suggestions with the exact
   frozen eligible-Sleep/Apply policy and timestamp. Preserve native command order,
   before/after state and action receipts. Commit canonical effects normally.
6. Open a fresh connection to read durable final tables, action histories and the
   configured reports. Run a finite set of compatible deployed query/response
   contracts. Day2 reads this committed state; no reseeding from the capture.

No existing web service needs rebinding for the finite reader proof. Reuse pinned
query bodies from daily Planning/BPR transit/BTR/RRR/history/GIT proof modules, but
replace fixture-only identity assumptions with an explicit new owned input contract
only after review. A raw SQL SELECT is not enough where the existing UI expects a
specific wrapper/serialization: use the retained deployed API contract or matched
serializer proof for that family. If a real deployed API endpoint cannot be hosted
in a permitted private facility, name that remaining gap; do not call a SQL-only
check end-to-end API acceptance or add a public port.

## 3. Modern production readiness versus external acceptance

Observed coupling: `context.selected_run`, `offline_scenario.require_run`,
`activate_daily_ui`, `activate_offline_readers` and `check_daily_selection` require
per-run external parity. `record_parity` binds exact run/output/input/action and
all31/independent RRR receipts. That is legitimate migration acceptance and cannot
be fabricated from final-row equality or disabled by a benchmark monkeypatch.

Two viable publication choices must remain separate:

**A. Retain strict migration admission for the captured baseline.** Capture each
day, perform genuine all31+RRR comparison in a separate proof worker, record its
real parity receipt, then prepare/admit/read the new owned publication. No gate
change is necessary for this choice. Raw elapsed includes the comparison wait;
report that wait separately. This is a complete instrumented migration-mode
baseline, not a clean operational production wall-time measurement. It cannot
close a requirement for uncaptured production timing.

**B. Implement operational admission distinct from external acceptance.** This is
the production-oriented design below and needs explicit scope approval. It permits
publication readiness to be measured without external parity on its critical path,
while genuine comparison remains mandatory outside primary timing for assessment
acceptance. It is not a prerequisite for timers or for choice A.

Proposed policy separation for choice B, requiring explicit approval:

* Keep current strict migration admission as the default for every existing run
  and serving configuration. Existing seals/acceptance receipts remain unchanged.
* Define a separately named complete-daily operational publication policy for
  the NEW benchmark owner only. Its authority is operational integrity and the
  qualified code/input contract, not a fabricated per-run comparison result.
* The policy must require SUCCEEDED, immutable typed input/output/source receipts,
  completed full daily operation roster (including newly qualified hooks/flags),
  expected date/predecessor, consumed own ordered action lineage, initialized
  source ownership, all required prepared layers and sealed configuration,
  exact catalogue/hierarchy, finite reader readiness and atomic explicit selection
  of one coherent tuple. No latest-run fallback or mixed BTR generation.
* External parity is stored/linked independently, still required for assessment
  acceptance and final reporting. A production-ready run is not labeled parity
  PASS until genuine external comparison succeeds. A divergence prevents closing
  this exercise and any release; no benchmark output reaches protected serving.
* Publish only inside an isolated worker/private facility with no mapped ports.
  A fresh reader process uses the explicit tuple and existing readers/serializers.
  Native row checks, auth/scope expansion, hierarchy NULL-denial and existing
  report deferrals remain active. Do not introduce a global allow-unaccepted flag.

This is an admission semantics change, not measurement plumbing. Proposed files:
`mta/presentation/context.py`, `admission.py`, `daily_publication.py`,
`daily_activation.py`, `daily_planning_extension.py`, `offline_rrr.py`,
`mta/runtime/offline_scenario.py` and explicit publication commands. Prefer one
small policy owner used by these call sites over several inconsistent bypasses.
Any new durable receipt/schema needs real migration/check/plan/PostgreSQL proof.
Do not infer permission to implement these changes from this proposal.

Required denial/failure tests: changed input/output/source, missing or duplicate
day boundary, wrong predecessor/date/owner, stale or changed Apply/Sleep lineage,
missing required projection/layer, wrong BTR generation, partial preparation,
changed config/catalogue/hierarchy, unknown/missing source versus valid empty,
mixed-run reader request, failed commit, concurrent selection and crash before
selection. Prove old strict admission still rejects unaccepted runs and old seals
still verify unchanged. Post-action current DBM overlay and next-day action
consumption must both remain correct.

## 4. Evidence mode and number of invocations

Recommended first complete baseline: **two business days per engine, four daily
engine invocations total**, one bounded worker per day. Capture necessary
intermediates during each invocation; measure capture separately. Use existing
validation behavior initially where needed rather than silently optimizing away
checks. Account for validation prefix verification/copy/export separately; do not
report it as business calculation. Keep original `run_temporal` unchanged.

External comparator, independent RRR/source checks, reader checks and typed
readback are not additional business calculations and may use fresh bounded
workers. No warmups, retries, matrix or new21-day run. Extra diagnostic engine
invocations are ZERO in this proposal. A failure preserves its attempt and stops
the business sequence for diagnosis; it does not trigger an automatic rerun.

Report actual invocation-to-published-consumable elapsed for both days, explicit
exclusive categories, captured diagnostic overhead, external validation duration,
and whether any gate forces external-validation wait into raw elapsed. Never
subtract that wait and label the result an observed different invocation. If the
approved objective demands an uncaptured production wall time, this captured
baseline is insufficient: authorize a separately counted two-day production or
diagnostic companion before running, with its own predecessor and identities.

The post-BPR and post-BTR extensions change some formerly compared populations. Retain the
old31 contract snapshots at their original positions for continuity of proof;
add the new post-hook/final-flag/final-consumer obligations separately. Changed
downstream values require fresh comparison under the new contract; old accepted
outcomes cannot transfer, including scratch populations affected by added truncation. Do not move
the snapshot point and call old receipts applicable. Confirm every prerequisite
and downstream changed stage before asserting unchanged earlier evidence applies.

## 5. Files, resources, proof and limits

Business implementation, if approved: missing post-BPR and post-BTR producers plus
temporal-chain placement; typed final-attribute/NMS ownership; full completion/gate
mapping; new standalone legacy durable harness; the operational admission
policy only if choice B is approved; a separate complete-day command coordinating the existing execute_day,
real actions, daily preparation and finite readers. `execute_day` remains the one
production calculation boundary. Do not optimize its algorithms during this work.

Independent authorized work now: this assessment, source/reuse inventories,
read-only review, and `tools/daily_boundary_timing.py` with focused tests. The
timer does not call or wrap an engine until the extension scope is approved.

Normal4GiB/twoCPU worker limits; new owned PostgreSQL at existing approved1GiB/
oneCPU limit with no host ports; exclusive new SQL namespace on the existing SQL
server. SQL server resources remain unmatched; disclose them and avoid clean
speed ratios. Never alter shared database limits or restart/prune WSL/Docker.
Do not touch excluded checkouts or ports3002/3/4/5/6.

Before invocation, freeze exact code/image/SQL/config/input/action-policy and
publication contract; record owned identities and preservation snapshots. Run
focused differential and admission denial tests, required baseline identities,
build and any affected migration-enabled checks. Then run each engine exactly
once per day. Outside primary timing compare all applicable31 typed/NULL/duplicate/
occurrence/native-order obligations plus independent RRR, new attributes/flags,
source families, real action states, own successor openings, configured files and
finite reader payloads. Unknown history stays unknown.

No complete timings or ranked measured savings are asserted in this proposal.
Observed code hotspots suggest repeated input/output/action/prefix verification
as later candidates, but their full-day cost and safe replacement guarantee must
be measured/proved first. Subsequent optimizations require their own reviewed
scope and are not an automatic continuation of this assessment.

## Consolidated decisions remaining

1. Approve the new full deployed daily business scope, binding explicit GulfOil
   hooks/gates to the retained synthetic identities without changing frozen facts;
   resolve missing activation/critical-script settings and canonical failure
   visibility before implementing those behaviors.
2. Approve the distinct owned durable legacy path with canonical transaction
   behavior. Choose modern publication A (strict genuine parity gate, measured wait)
   or B (new operational policy with explicit invariants/denial tests); neither
   choice changes protected serving admission or fabricates external acceptance.
3. Confirm the two-day captured-inclusive baseline with separately attributed
   diagnostics (four daily engine invocations total). If an uncaptured wall-time
   sample is also required, explicitly decide its additional invocation budget.

All three belong in one reviewed disposition. Until then, no extension or engine
execution. The assessment goal remains unfinished, and the stopped original run
remains stopped regardless of the new benchmark decision.

## Review disposition

Focused read-only review identified and corrected missing production-order,
history-cleanup, exception/export, Planning, pre-run flag/parent-Norm/task and
post-BTR obligations, and separated publication choices A/B. The corrected
package is reviewed with open scope/configuration gaps; it is not an implemented
complete daily flow or a source-by-source closure certificate. No engine was run.
