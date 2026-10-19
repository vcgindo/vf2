# Large-data synthetic benchmark — legacy day-one result

19 October 2026. The sole current status authority is `F:/freshvcf/docs/handoff-3005/TRACKER.md`. This is the frozen result of a separate benchmark follow-up; it does not reopen the original Step5 production handoff.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

## Scope and result

The human authorized the seven-step benchmark through legacy day one, then instructed a stop while independently resetting the modern installation. After read-only source inspection, the human chose **"Use synthetic next-day benchmark"**: copy the large3005 snapshot as opening, generate one conserved next-day raw CSV workload, and exclude unavailable GulfOil customer-source preprocessing from timing.

**Steps1–4 completed for the legacy portion. Step5 attempted and failed in native Pick generation. There is no completed-day legacy timing baseline. No modern run or comparison was performed.**

| Step | Observed outcome |
| --- | --- |
| 1. Freeze workload | Complete:7April2026 opening;8April synthetic day;2,189SKUs/235locations;97,097daily rows; retained90-date history. |
| 2. Prepare CSV pack | Complete: full14-file daily raw roster and explicit216-row requirement-stock support input. Complete source/typed-parser comparisons; actual legacy SQL load/readback subsequently passed. Whole modern opening/binding admission remains unproved. |
| 3. Isolate targets | Complete:8new SQL databases and a new disabled restricted login;17.818seconds for schema setup. No serving-network/port change. |
| 4. Initialize legacy opening | Complete: restore the same recorded four native backup sets; dates/populations and denial to protected sources verified.252.775seconds including verification. This is snapshot restore, not CSV master-import throughput. |
| 5. Run legacy day one | Failed: SQL8115, arithmetic overflow, `GenerateLogisticPickList.sql`. BPR/RRR had97,097rows each, but subsequent Pick/report finalization, DBM and BTR were not executed. Those intermediate counts are not whole-day acceptance. |

The97,097daily rows include18,788known-stock and78,309NULL-stock rows. Only known-stock rows have a provable numeric conservation identity. NULL availability remains for native missing-input rules. Generated receipts/consumption retain source values where possible, cap consumption at available stock, and derive closing stock.829rows have positive consumption;590have positive receipts. This is not100,000fully populated daily transactions or a general capacity proof.

## Native failure

Pinned producer: `F:/VFlow_Local/local-runtime/mta-engine/Scripts/BPR/Ration_Scripts/GenerateLogisticPickList.sql`, SHA256`b5044bcb979e57c270d944fdcf3a7998bee33484a384dae89aaaf414c7d05dfb`.

Its cumulative truck-formation insert at source lines111–127 calculates running weight by parent/logistic location. One retained expression result was **13,145,646,112.000**; the destination `CumulativeWeight decimal(13,3)` permits at most **9,999,999,999.999**. Another result was13,693,789,388.000. A read-only projection of the unchanged expression reproduced the out-of-range values. No producer rerun was performed for that diagnosis.

The isolated scratch column matches the pinned canonical Intermediate DDL and the existing protected `Demo_IntermediateDB_1` column metadata. The restored BPR closing schema also uses `decimal(13,3)` cumulative fields. SKU attributes remained2,189distinct source/target rows; the failure was not attributed to duplicated SKU attribute loading. The original VM's matching Intermediate backup was not supplied, so the conclusion is about this measured canonical isolated run, not every legacy installation.

The native script catches the SQL error and returns a result set with `ERROR`, `ErrorNumber8115` and `ErrorLine111`; SQLCMD itself exits0. The benchmark guard checks those error result sets and blocked every subsequent SQL call. BAT echo lines saying "finished" do not prove that later SQL executed. The initial clock stage set all four role dates to8April; that also does not prove DBM/BTR ran.

## Measurements and qualifications

| Observed stage | Seconds |
| --- | ---: |
| Reset flags and set clock | 3.012 |
| CSV load plus complete external typed readback | 63.038 |
| Native input validation | 38.032 |
| Native norm/control processing | 28.024 |
| BPR/RRR/Pick stage, ending in failure | 173.142 |
| Total through driver stop | **305.277** |

Peak observed shared SQL process RSS was6,552,653,824bytes (about6.10GiB); shared process CPU increased415.359processor-seconds. These are instrumented measurements including existing SQL background activity and warmed restore buffers. No SQL service/cache restart or memory ceiling was introduced. Existing SQL maximum memory was unrestricted; existing MAXDOP8 was recorded and unchanged. The host has16logical CPUs and34,010,619,904physical-memory bytes.

**305.277seconds is time through a failed partial attempt, not successful daily throughput.** CSV loading includes an extra full readback; wall timing includes Python transport/guard overhead. Per-call native SQLCMD timings are retained separately. There is no modern speedup ratio, cross-engine parity claim, percentile estimate or extrapolation to other populations.

Native business SQL and BAT conditions were retained. External adapters bind only owned database/path variables, load normalized typed raw CSV, impersonate the disabled restricted login with NO REVERT, and detect failures. They do not call the modern calculation producer or the reset-and-seed legacy parity runner. Customer file collection/Interface transformations, external notifications, operational backup jobs and serving/UI work are outside the measured shared boundary. Portable7-Zip26.04 was obtained from the [official download page](https://www.7-zip.org/download.html) into benchmark-owned evidence; no system installation/PATH change. Failure occurred before report compression, so it supplies no compression timing.

## Retained evidence and stopping point

Root: `D:/freshvcf-build/evidence/large-data-day1-benchmark-20261019`.

- `case.json`: SHAc872e22ceacdefdaeafc2255ae2bd35a9472de44e58f216ea6b133a6f9663104.
- `csv/DailyDataRaw.csv`: SHA5714e18c51c4a65bb636bedc8437b4003d870e2c7da11eb97b72660184afce20.
- `csv-pack.json`, `csv-pack-verification.json`, `input-load.json`: complete CSV/source/parser/SQL readbacks, not merely counts.
- `targets.json`, `initialization.json`: ownership, schema setup, native backup identities, initialization timing and actual permission denials.
- `day-attempt.json`, `day-failure.json`, `sql-calls.jsonl`, original logs and bound SQL: failed attempt and exact execution prefix. Earlier pre-business observer startup failure is separately preserved; it ran no daily SQL and caused no business replay.
- `failure-confirmed.json`, `failed-pick-input.csv`, `failed-pick-input-proof.json`, `original-demo-scratch-schema-readonly.json`: exact failure, full3,454-row failed Pick input and metadata diagnosis.
- `resource-context.json`, `resources.jsonl`, `legacy-day1-failed-result.json`: observations and limits.
- `owned-terminal-state.json`: all8owned targets retained READ_ONLY/OFFLINE; shared SQL service remains running. No active owned jobs/open user transactions remained before stopping them.
- `3005-before-day.json`, `3005-after-day.json`: all six3005container IDs/images/start times/states unchanged. Four protected source databases remain ONLINE/READ_ONLY. No modern installation command or mutation occurred.

Owned namespace: `VFTEST_Fresh_Benchmark_1cd1a13f1dbb41d3b33e7c826edd5816_*`; files: `D:/freshvcf-build/sqlserver/large-data-benchmark-1cd1a13f-1dbb-41d3-b33e-7c826edd5816`. Nothing was reset/deleted/reseeded to conceal failure. The standalone harness refuses replay once business SQL has executed. The failed physical state is retained for inspection; it is not a successful opening for another daily run.

Stop here as requested. A change to workload, numeric storage/rules, acceptance boundary or a new daily attempt needs a separate decision. Do not automatically repair the legacy oracle or run modern while the human prepares its blank installation.

Before any later modern comparison, establish equivalent full native opening/history and binding. The216configured additional requirement-stock rows are outside the public14-file daily CSV roster; their exact native source/binding path must be proved, not silently omitted. The supporting source export is retained unchanged, with a separate dated8April projection. No new production feature or input waiver has been inferred from that finding.

## Follow-up diagnosis — existing multi-vehicle Pick defect

The19October user requested investigation and a fix after the failed attempt. The initial decimal-limit diagnosis identified the failing storage operation, but **was not the underlying cause**. No decimal widening is recommended.

Read-only source/failed-row tracing confirms ordinary producer allocations: SKU212100215100/P066_1002 has RationedReq840 (TOY630/TOG210); SKU221170230400/P017_1001 has RationedReq1080 (TOR_B600/TOY480). The failed32–34million quantities are mutated loop residuals, not raw input quantities or initial RRR allocations. SKU attributes remain unique; dimensions and both21MT/24MT vehicle options are inherited unchanged.

The canonical producer ranks requirements before joining vehicle options. Its cumulative windows partition only by parent/logistics location, pooling both vehicle copies. Boundary and residual joins also omit vehicle identity. In a session-local temporary-table reproduction, the first iteration allocates negative quantities: for SKU212100215100, -526/-511 for the two vehicles; residual630 increases to1156 under that observed SQL UPDATE winner. SKU221170230400 similarly produces -496/-481. Subsequent iterations amplify the residual until the unchanged decimal field overflows. Native UPDATE has conflicting vehicle candidates; row ranking and UPDATE winner are not uniquely specified. This is an existing canonical SQL defect exposed by the synthetic workload, not a proven CSV loader or modern-engine defect.

A **test-only proposed correction** keeps the two configured vehicle options independent throughout cumulative windows, truck-boundary staging/joins, residual updates/deletes and load-type aggregation. Scratch PickListOfTruckFull carries VehicleName. It selects no arbitrary vehicle, changes no raw quantity/dimension/capacity and does not widen decimals. Applied only to session-local temporary tables containing the retained complete pre-Pick population, it terminates after50iterations with zero negative formed/residual rows, zero grouped quantity-conservation mismatches,6,603formed rows and1,481flagged residual rows. Both configured vehicle names remain. These are focused diagnostic checks, not full-day, full-parity, UI or regression acceptance; diagnostic elapsed time is not a daily benchmark.

Evidence: root-cause-row-trace.json; pick-temp-reproducer.sql/json; pick-vehicle-candidate-temp.sql/json; pick-vehicle-candidate-changes.json; diagnosis-terminal-state.json. Reviewable unapplied original-SQL patch and decision: D:/freshvcf-build/evidence/large-data-day1-benchmark-20261019/pick-correction-proposal/. Decision SHA256fbb90e2cd8783552f761142acb791d20be51675b8abe8a017680924a834b16da.

**Decision needed before application:** the repository mandate forbids silently repairing legacy flaws. Keeping each configured vehicle alternative independent changes the native calculation contract and therefore creates a corrected-legacy baseline. It must not be labelled unchanged legacy parity. Approve this precise isolated correction and one separately owned attempt of the same frozen April8workload before implementation/re-execution. Preserve the original8failed databases and canonical SQL. A modern rule change or modern execution is not released by this proposal; an aligned comparison needs an explicit subsequent scope decision. No automatic rerun has occurred.

All8failed targets are again READ_ONLY/OFFLINE, with no active owned requests or user transactions. The4protected sources remain ONLINE/READ_ONLY.3005, original SQL files, modern installation, frontend and MTO were not changed.
