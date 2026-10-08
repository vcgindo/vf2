# Complete daily execution: coverage and assessment contract

8 October 2026. This document records evidence and the benchmark contract, not
execution status. `MIGRATION.md` is the sole status tracker. The approved objective
is one complete daily outcome, including actions and daily published outputs
consumable by the existing UI. No new business invocation has been made for this
assessment. No complete-day timing is available yet.

The human-stopped `temporal-full-001`, all accepted/interrupted attempts, source
transitions, SQL namespace and serving selections remain protected. Do not run
the previous H3 command to perform this assessment.

## Authority and evidence boundary

Use `baseline/manifest.json`, actual deployed BAT/SQL/config and the deployed API
DLL `0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346`.
The retained `docs/batch-atlas/inventory.json` and `diagrams-v2.json` provide
navigation and source hashes; their static edges are not execution proof. Existing
`DAILY_EXECUTION_COVERAGE.md` described the earlier narrower refinement, whose
presentation preparation was outside its timing. That boundary cannot close this
assessment. Untracked atlas/guide files are read-only evidence, not adopted changes.

Frozen facts remain
`D:/freshvcf-build/synthetic/rlt-4-7-v1/scenario-004/full-input.json`, SHA256
`ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56`:
1,240 pairs, 200 SKUs, retained 20-location catalogue (13 active pair locations),
21 dates June 6–26. The proposed exercise uses ONLY June 6 and June 7, retaining
the complete artifact; no regeneration or new history. The profile declares
`delivery.site_code=VECTORFLOW-DEMO`, disables vendor/distributor/VectorDMS and
AutoDBMActive, and selects explicit report horizons. It is not a complete deployed
GulfOil BAT settings export. GulfOil hooks must be reconciled explicitly, not
inferred from the atlas's site selection.

## Complete coverage map

Each row follows producer order. Inputs include its listed predecessors. Stored
outputs must preserve types, NULLs, duplicate occurrences and native order; a row
count or final-state match cannot prove an overwritten intermediate population.
`R1` through `R7` below refer to the reuse matrix, not new acceptance receipts.

| Process and purpose | Inputs / dependency | Legacy implementation / final writer | Modern implementation / final writer | Persisted output; next-day and UI consumer | Integrity / diagnostics and proof gap |
|---|---|---|---|---|---|
| Admission, run dates, fullkit, sanitation, critical-script flags | Explicit site/settings/date and external fact availability | `VectorFLOWv4.bat`, `StdSettingsPre/Post`, site Settings, `CheckRunStartCriteria`, `FullkitCheckForPostRun`, sanitation, `SetRunDate` | `run_daily`, `execute_day`, artifact/MDM/source binding and day-boundary roster | Dates, settings, input/run identity, execution flags/logs; all stages and UI completion | R1/R2 bind selected profile, not full BAT gates. Missing settings/flag mapping must be resolved; no invented empty gate tables |
| MDM capture / approved master changes / pair exclusion | Own pending approved occurrences, raw master, effective configuration | NMS import/task/archive SQL under input/control BAT sequence | `mdm/daily_input`, `daily_source`, `runtime/mdm_configuration`, `execute_day` | Typed input snapshots, occurrence/task/history archives; current master and subsequent day | Repeatable-read capture and atomic consumption; R3. Legacy actor/check exceptions retain exact scope |
| Raw master validation / reconciliation | Frozen raw master, NoNorm/NonNMS, own master opening | `ValidateAndProcessMaster.sql`, master import adapter | `r1_master_input`, `r1_gulfoil_input`, `entry_inputs` | MasterData, attributes/descriptions, rejected rows; BPR/DBM/MDM/UI | Outcome checks, exact schema/row policy; intermediate diagnostics R1/R2 |
| Supplier feeds and SOB/MOQ | Raw supplier rows, prior SOB/MOQ, validated master | Supplier validation/import then refresh at supplier allocation | `r1_supplier_input`, supplier calculation state | Opening supplier sources distinct from refreshed SOB/MOQ; allocation/BOR consumers/next day | Decimal preservation, readback; R2/R3. Opening is not BOR-OA output |
| Daily input and ingestion | Daily stock/sales/GIT facts and valid master | Daily validation SQL and configured missing-data handling | `r1_daily_input`, `process_daily_validation` | Processed daily rows, reject/history/settings; current calculations | SQL-error/outcome checks, source identity; R1/R2. Optional distributor/vendor disabled by exact profile |
| Controls and accepted/forced Norms | Prior controls, new requests, phase-in/out, seasonality | `NormChangesRun`, control SQL, force update then clear | `timeline_controls`, `control_carry` | Effective masters, control histories, exports and cleared requests; BPR/DBM and next day | Order-sensitive; force-before-clear diagnostic images required. R1/R2 |
| Orders and due dates | Own order history/identity, frozen order feed, effective master | `r1_runner.R1_SEQUENCE`, order SQL | `order_closing`, `order_stages` | SpikeOrderData/identity/due dates/history; Pick and next day | Existing used-counter setup is fixture initialization, not timing replacement; no new default/tie break |
| Stock, requirements and reservations | Processed facts, routes, standard attributes, orders | Current-day R1 SQL sequence | `planning.engine.calculate_current_day`, domain producers | Requirement/stock/advance/GIT/order and allocation populations; downstream Pick/BPR | All15 calculation comparisons include transient populations; R1/R2, cannot infer from final reports |
| Sourcing, rationing, Pick, supplier allocation and logistics | Requirements, priority, packs, supplier opening, vehicle/logistics | R1 sequence, supplier refresh, BOR-OA collect, Pick/logistics SQL | Current-day planning/ration/Pick/logistics producers | Rationed/Pick/BOR populations, own logistics state; BPR/Planning/RRR | Opening BOR-OA and refreshed supplier BOR captured at different positions. Existing calculation proof is not daily BOR UI source proof |
| BPR / BlueRequirement / RRR sources | Pick/ration output, inventory, daily consumption/colour | CollectDataForBPR, UpdateBPR and retained SQL source queries | `bpr_construction`, `rationed_report`, `offline_rrr.write` | BPR_Table, vf_RationedReqReport, colour, RRR typed source; BPR/RRR/DBM/BTR | R1/R2 plus independent RRR source proof; scoped RRR0 exception unchanged |
| Production order suggestions | SupplierDispatchReq, Plants, rationed bands, own plant stock/GIT | ProdOrderSuggestions.sql, after GenSupplierWiseReq | No complete producer mapping yet | ProdOrderSuggestions and scratch effects; configured planning/production consumers | Unconditional BAT call omitted from selected R1 sequence. Script warns about order-data use; frozen-workload compatibility must be resolved |
| BPR history retention | Own dated consumption and BPR/request/transit remarks; declared horizons | ClearHistoryData_BPR.sql | Typed histories and remark capture filtering do not prove matching owner cleanup | DailyConsumption and three remark histories; next day/current readers | Inclusive cutoff/delete behavior must be mapped; unknown horizon is not zero |
| Planning final populations / batch files | GIT/excess, expedite, order fulfillment, Pick/order/BOR outputs | Planning.bat and PickListReports/OrderAllocBasedReports wrappers | Existing projection/preparation families require per-producer equality | Planning tables and configured files/downloads; unchanged UI | No omission under BOR UI deferral. Source/input/output mapping still required |
| BPR exception export | Actual nonempty BPRExceptions | GenerateBPRExceptionReport.bat | No full file-wrapper equivalence established | Header/rows/CSV/ZIP and absent-output behavior | Data-dependent required output; owned paths only, email separate |
| BPR completion / failed-output clearing | Run-date setting and critical BPR script flags | `ValidateBPRBatchExecutionFlags.sql`; failure clears four BPR report tables and skips later work | Eight-boundary roster and atomic `finish_run` are not proven equivalent BAT failure behavior | IsBPRBatchFileExecuted and report availability; readers and continuation | Missing behavior mapping. Preserve canonical failure outcome; do not silently equate transaction rollback to table clearing |
| Site post-BPR attributes | Current Pick, ParentPackSize/stock, VirtualNorm, raw SKULocAtt01/02 | GulfOil `CalculatedAttributes.sql`, before DBM | No matching producer found in current temporal chain | c3 in BPR/Importer attributes, BPR_Table.SKULocAttr3, NMSAllItems.SKULocAtt03; attribute readers and possible downstream facts | Real missing source/config decision, not diagnostic overhead. See extension proposal |
| DBM ingestion and ExtendedOCP | BPR/controls/exclusions/order facts and own DBM opening | Daily import/DBM selected sequence | `dbm_ingestion`, selected/connected DBM stages | DBMMaster, consumption, attributes; ordered suspensions/rules | d004dc1 lookup refinement retained; R2. DBM-ingestion boundary is overwritten later |
| Suspension/cooling and rule competition | Own suspension/cooling/history plus current imported master | Ordered suspension/rule/discard SQL | `dbm_suspensions`, rule stages, `dbm_suspension_history` | Suggestions, suspension/log/acceptance/history; real actions/next day | Formula, date/tie and reason precedence fixed. R2; stage snapshots diagnostic, histories operational |
| DBM reports, Norm0/1/2/advisory and norm exports | Stage-specific rule outputs and configured horizons | Ordered report resultsets/tables followed by overwrite/cleanup | DBM report stages and `chain` retained report slices | Ordered report tables, header/row cells/row lengths, Norm history; export readers | Capture before overwrite is required output preservation, not removable debug data. R1/R2/R3 |
| BTR finalization, ageing, category, insights | Own BTR history plus current BPR/DBM/Pick | Core BTR SQL; final UpdateCategoryCol writer | `btr_finalization`; `chain` copies final standard attributes back to closing DBM | Trends, dates, BTRSnapshotForUI, Chronic, norm suggestions, final standard attributes; next day/BTR/Research/Guided | Core final writer matters: earlier DBM snapshot differs. R1/R2/R3 do not include GulfOil post-BTR overwrite |
| Site post-BTR computed attributes and files | Rolling BTR/current master under explicit GulfOil hook selection | CalculateAttributeBasedonBTR.sql then GulfOil_BTRReports.py | No qualified computed/file equivalent established | c9/c10/c12/c13 across BPR/DBM/Importer/Supplier/NMS, Interface.FGTrendData and site reports; UI/final state | Omitted from retained core-BTR sequence. New final writer; Python called by pinned BAT but not currently baseline-registered |
| Parent-Norm report and batch flag reset | Effective master and run-date/critical-script roster | ValidationForParentNorm / ResetBatchExecutionFlag | Existing input/control/run owners not yet qualified for these exact outputs | NoNormParent files and completion flags; operator/readers | Scope includes output/absence/error behavior, not just formulas |
| BOR/RRR order-allocation history and file wrappers | Current allocation/supplier populations and declared horizons | CollectBOR_OrderAllocationHistory / CollectRRR_OrderAllocationHistory and export wrappers | Existing prepared/UI histories are not proof of these batch producers | Canonical history rows/files; subsequent day and configured consumers | Unconditional history/export calls distinguished from IsMTOEnvironment-gated exports |
| Runtime reports, input-downloads, UI upload logs, backup/alerts | Exact activation/config rows and intermediate/final products | GenerateRuntimeReports at PostImporter/PostBPR/PostDBM/PostBTR/Final; DownloadInputData; GenerateUIUploadLogs; Backup/alerts | No full-deployed operational wrapper equivalence established | Files/archives/logs and configured reader downloads; operation audit | Conditional is not free exclusion. Need exact flags/SQL/report-file roster. No email transmission or shared backup authorized |
| Final completion and cleanup | Critical script flags, final reports and date | GenericFinalProcessing / ValidateBatchExecutionFlags; site final hooks | `finish_run` status/manifest/MDM consumption; separate readiness seal | IsBatchFileExecuted; durable run/output identities; next-day/UI admission | Final flags absent in selected oracle. No-op site hooks still recorded; no assumption flag=1 |
| Real Apply/Sleep | This engine's OWN eligible Suggestions and frozen eligible-Sleep policy | Canonical deployed action SQL/API contract, `replay_commands` | `record_command`, `command_state` | Command selection/before/after digests, typed action images, acceptance/suspension changes; UI overlay and successor | R2/R3 real8Sleep+120Apply day1,6Apply day2 evidence. New workload determined anew, never copied from other engine |
| Closing persistence and predecessor continuity | All final owned state plus commands | Current oracle writes own capture/closing archive after SQL rollback; actual daily SQL must commit | `save_daily`, `finish_run`, typed relational state; next `execute_day` reads own closing and applies own commands | Run-linked histories/state/images/lineage and source receipts; every successor | R3 atomic typed/readback proof. Legacy archive is persisted evidence, not durable SQL publication; new commit proposal required |
| Daily narrow report sources | Supplier opening, colour, requests/remarks, frozen shipment facts, calculation outputs | Canonical consumer ingredients in SQL/own external input | `daily_sources`, `daily_transit`, `daily_requests`, `ancillary_live`, Pick/Excess/Fulfillment/Expedite/PickPost writers | Seven source/projection families and source metadata; existing readers | Explicit identical empty request/BPR owners. Missing remains unavailable. R2 corrective proof covers owners, original70.199s does not |
| Daily presentation preparation | Same-day persisted output and complete source identities | Canonical API/SQL views/query populations plus configured output files | `daily_publication.prepare`, finite `daily_preparation` layers | Prepared typed rows, BTR generation, sealed layer receipts; all supported report readers | R4/R5 retained preparation proof is not new-day end-to-end timing. Every required layer must be READY; no partial seal |
| Publication, access, readiness and finite consumers | Complete run, output/seal, exact catalogue/hierarchy, action overlays | Durable committed own SQL + fresh compatible canonical reader connection | `activate_daily_ui`, `activate_offline_readers`, `check_daily_selection`, `admission`, `context.selected_run` | Explicit selection tuple/readiness and actual response payloads; unchanged UI | Current modern gates require external parity. Existing service config cannot change. Isolated in-process/private reader proof only; no browser timing claim |

## Presentation output accountability

The 18-layer `core-without-bor-v1` roster remains explicit: dbm_sources, bpr, btr,
planning_sources, planning_grids, planning_charts, planning_custom, planning_git,
planning_expedite_grids, planning_expedite_custom, planning_expedite_transit,
planning_expedite_charts, rrr, history, research_availability, guided_history,
guided_dbm and guided_chronic. Each has an existing prepare/verify owner in
`daily_preparation.py`; record its receipt, row identity and consumer response.
Both days must prepare all required layers and prove finite reader usability.

Direct operational readers also include DBM current/history/actions, Pick,
Fulfillment, Excess, Expedite and Pick-post. They are not optional merely because
they lack a separate prepared-layer entry. Live requests/remarks remain their
own source families and are initialized explicitly; MDM histories remain owned
and typed. Existing auth/menu/hierarchy/MTO behavior is reused, not redesigned.

BOR and BOR-OA daily UI source gaps remain existing explicit deferrals despite
their underlying calculation comparisons. Guided Excess rolling history remains
coverage-bounded/unknown outside qualified dates; do not synthesize pre-June6
history or extend an old fixture-only waiver. Current Excess projection must
still be produced and read. No other report is silently deferred.

The companion source inventory records EVERY current `mta/presentation/*.py`
file (including nested planning files), its hash and top-level symbols. It is a
completeness backstop, not a claim that a lexical symbol is an equivalent producer.
Every changed output requires a named consumer and proof before benchmark closure.

## Reuse matrix

| ID / retained evidence | Reusable claim after pin reconciliation | What it cannot establish |
|---|---|---|
| R1 baseline manifest, source DAG/contracts and canonical DLL | Deployed source identities and selected dependency provenance | All enabled BAT branches or complete daily publication acceptance |
| R2 `refinement/dbm-joins-001/final-proof.json`, `identities.json`, validation day1/day2 replay and independent RRR | Five DBM joins, all31+RRR, own actions/continuity for the recorded two-day profile; preserve d004dc1 | New site hooks/final flags, new commit/admission semantics, fresh complete-day timing |
| R3 integrated-001 typed persistence, migration/rollback/input tamper proofs and DBM mode-equivalence-resolved | Typed operation/report persistence and all515 images plus seven source groups where code/input ownership match | Intermediate stages absent from production; no parity transfer by swapping run IDs |
| R4 terminal/daily preparation, reader/scoped SQL receipts and source implementations | Unchanged reader SQL/serializer/scoping semantics and finite roster recipes | New-day readiness, post-action publication and changed attributes; no copied acceptance |
| R5 readiness-dbm-v1 before/after/service/source pins | Prior immutable readiness and exact source transition evidence | Authority to restart temporal-full-001 or change a service |
| R6 old modern89.159→70.199s / DBM30.862→10.131s and earlier89.895/legacy180.878 samples | Historical measured components with recorded resource/input limits | Actions, successor opening, full source owners, presentation, durable legacy publication or complete-day ratio |
| R7 preserved temporal-full-001 June6–9 acceptance / interrupted later attempts | Exact accepted original identities and diagnostics only | Permission to replay, reset, time again or publish the stopped run |

Never sum R6 with R4 or any other run to manufacture elapsed daily time. SQL server
resources are unmatched to the1GiB/oneCPU PostgreSQL fixture; worker4GiB/twoCPU
limits do not make database resources equal. No clean speed ratio, p95 or SLA.

## Integrity controls and possible future replacements

These are assessment candidates only. None is removed or weakened here.

| Control and origin | Failure prevented / authoritative owner | Classification | Existing guarantee and later proof needed |
|---|---|---|---|
| BAT fullkit/sanitation/run-date guards | Missing/invalid feeds or wrong date; deployment/input owner | Required admission | Modern explicit input/MDM binding covers selected fields, not every BAT condition; first reconcile missing config |
| Critical-script flags and BPR clear-on-failure | Silent script omission/partial report display; canonical BAT | Required completion semantics | Modern atomic status/roster is a candidate replacement, not current equivalence; test omitted critical stage, stale date, SQL catch-result and visibility |
| SQL TRY/CATCH resultsets | Business SQL errors that do not fail process exit; SQL producer | Required error recognition | Result consumer must inspect error rows; exit0 alone is insufficient; preserve canonical side effects |
| Namespace allowlist, files/schema signatures, lease | Accidental live/shared mutation or concurrent replay; isolation owner | Required safety/integrity | Unique ownership + restricted principal; never replace with a naming assertion alone |
| Input hash, typed input audit, source owner/revision | Drift, mixed approvals and missing-versus-empty; execute_day/MDM owner | Required boundary checks | Typed keys/FKs and repeatable-read capture already exist. Repeated immutable input scans are candidates only after tamper/mutation guarantees are proved |
| `read_outputs` / `audit_output` / ordered image checksums | Corrupt/missing/reordered/duplicated state; typed row owner | Required integrity with potentially repeated work | Constraints protect identity/ordinal, not all cell contents. Later immutable-write guarantee + once-per-boundary verification must still reject content tampering |
| `record_command` rereads all output and replays prior commands | Stale/invalid selections, wrong order, duplicate actions; command owner | Required action integrity, possible redundant reconstruction | Row locks/idempotency/before-after digests exist. Any narrower authoritative DBM read must retain every action eligibility and next-day invariant |
| `command_state` / action archive/readback | Wrong action lineage or changed typed action image; command owner | Operational validation plus diagnostic export | Persisted RunCommand/image receipts are operational; gzip copies are external evidence. Do not omit action execution or policy selection |
| Full accepted-prefix verification/copy in `run_temporal` | Changed historical evidence or source transition; validation continuation owner | External acceptance orchestration | Own immediate predecessor verification remains operational. Prefix archive copy/rehash is not calculation; assess once-bound immutable evidence later, no bypass in accepted timelines |
| `snapshot`, whole graph normalization, checkpoint compression/hash | Independent transient stage comparison; validation evidence owner | Diagnostic capture | Operational final state is not a replacement for overwritten stages. No invented all31 evidence from typed final rows |
| Report slices before overwrite | Loss of user-visible reports/exports; report producer | Required business output | Header/row cells and duplicate ordinals must survive even with diagnostics disabled |
| Atomic `finish_run` / MDM consumption | Half daily result or lost queued approval; PostgreSQL transaction | Required durability | Commit/readback/rollback proofs retained; actions and UI preparation have their own transactions and cannot be assumed part of this commit |
| Layer preparation verification, seal, activation and startup | Mixed run/config/recipe, partial prepared output, wrong scopes; publication owner | Required publication integrity, possibly repeated row verification | Immutable per-layer seals already exist. Consolidation needs crash/retry/config-change denial proof before removing any check |
| Per-run all31+RRR parity gate in UI | Unaccepted calculated run reaching readers; migration acceptance owner | External acceptance coupled to production admission | Cannot disable or label fake PASS. Separate operational readiness policy needs explicit approval and denial tests (proposal) |

## Benchmark design and measurement

One new explicit owner; one owned PostgreSQL database and one unique8-role
`VFTEST_Fresh_*` SQL namespace. Own initial state on day1; each engine consumes its
own durable persisted predecessor and real action state on day2. No engine
receives the other engine's calculated state. Initialize matching authoritative
empty request/BPR remark owners with provenance before day1; preserve all other
unavailable populations. Use exact frozen daily shipment facts, not a terminal
empty-transit supplement. Keep existing hierarchy catalogue/six-field projection
scope; bind it to the new run/date/output, never substitute native attributes.

Start: host invocation before worker startup/admission. End: durable daily output,
real actions, required histories/sources, prepared roster, publication admission
and successful finite compatible reader responses from a fresh connection/process.
Use complete payload/typed occurrence validation in subsequent external proof;
the finite timed readers must actually serialize/consume their responses, not
return a READY label. No browser campaign or click-to-render performance claim.
No protected selection, service, port, restart or proxy rerouting.

Each day includes these non-overlapping accounting categories:
admission/ingestion, own opening/calculation, action selection/verification/persistence,
closing/history/source persistence, preparation/publication/readiness, startup/
orchestration. Separately identify diagnostics and external acceptance. Raw
invocation elapsed includes everything that actually occurred before its endpoint.
Nested inclusive intervals must never be summed. Exclusive attribution uses one
monotonic clock and counts each interval once. Diagnostic-subtracted time is an
attribution, NOT an observed uncaptured production runtime.

`tools/daily_boundary_timing.py` is standalone measurement only: explicit scalar
boundaries, failure retention and a total partition. It installs no engine hooks,
runs no process, grants no publication authority and cannot infer readiness.
Worker/host clocks must have separate timelines; include subprocess waiting once
in host elapsed, not again by summing worker elapsed. Child rows explain the wait.
No cProfile, per-row timers, warmups, matrix or speculative repeats.

## Correctness and capture disposition

Current31 =8 boundaries +15 calculation populations +5 master obligations +emitted
reports +own-action-selection +post-action-state. Independent RRR is additional.
See `parity/accepted_prefix.py` and `replay_temporal.compare_day` for exact names.

Typed production rows preserve closing state, final reports, required exports,
actions, histories and narrow consumer sources. They do NOT preserve the complete
controls/DBM ingestion/suspension/discard stages, all transient calculation outputs
or force-before-clear images. `validation_storage.export_run` explicitly denies
production-mode intermediate export. Legacy SQL also overwrites report stages and
always rolls back in the existing temporal adapter. Final rows cannot reconstruct
these contracts. Reused R2 receipts prove unchanged old behavior only.

For a two-invocation-only baseline, retain required transient capture DURING each
day and disclose instrumented inclusive elapsed plus separately attributed capture
cost. Do not claim an uncaptured production measurement. If actual uncaptured
production timing is required as well as new full31 parity, additional diagnostic
business invocations require a concrete decision. No such invocation has been
made or authorized by this document. Separating production admission from external
acceptance also requires reviewed scope, not a timer change.

## Current findings, not timing conclusions

1. Whole daily work was absent from the earlier timing boundary: actions,
   successor orchestration, publication and full initialized sources.
2. Existing selected oracle and deployed BAT have a concrete scope mismatch.
3. Legacy rollback capture is not durable SQL publication.
4. Modern migration acceptance is coupled to normal UI admission.
5. Repeated readback/prefix/capture work is visible in code but has no measured
   complete-day cost yet. Rank it only after the new measurements; no invented
   savings or extrapolated two-day/full-horizon estimates.

The coverage map still has named unresolved producer/configuration entries; it is
not a completed source-by-source coverage certificate. The companion
`COMPLETE_DAILY_EXTENSION_PROPOSAL.md` defines the decisions required
before any benchmark. This assessment remains incomplete until those dependencies
are resolved and real complete-day results/proofs exist.
