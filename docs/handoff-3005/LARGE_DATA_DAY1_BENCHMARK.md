# Large-data synthetic benchmark — legacy day-one result

19 October 2026. The sole current status authority is `F:/freshvcf/docs/handoff-3005/TRACKER.md`. This is the frozen result of a separate benchmark follow-up; it does not reopen the original Step5 production handoff.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

## Scope and result

### Current checkpoint — 20 October2026

The human subsequently released the whole comparison through step7. Historical
stop/pending wording below describes earlier attempts only. Legacy has now
passed the approved BOR and supplier mappings, remaining BPR/Planning and DBM
business stages. The current continuation is processing BTR and remaining
reports; final execution/readback is not yet complete. All earlier failed
attempts and checkpoints are retained. Timings are split active phases, not an
uninterrupted daily benchmark. Terminal shared-tempdb shrink was denied and
excluded without increasing privileges or replaying the completed DBM rule.

Modern source includes the separately approved independent-vehicle Pick
alignment, historical BTR carry admission and versioned requirement-stock CSV
connection. Focused tests cover the actual CSV-to-connected-calculation path,
typed/NULL/duplicate/date guards and retained old intake formats. These are
not a large-data initialization/day or full parity result.

**New step6 admission blocker:** the production CSV opening reader constructs
all history rows as Python dictionaries; initialization then deep-copies the
opening. The frozen DBM DailyConsumption31,040,788/SuspendHistory8,483,159 and
BTR BPR8,483,003/RationingHistory2,882,051 populations require at least
20,880,562,288 bytes (19.447GiB) for one set of row dictionaries alone, measured
with the running image's Python3.11 container sizes. Docker reports
16,594,939,904bytes (15.455GiB) total. Two dictionary copies alone exceed
38.89GiB. Values, lists, CSV/JSON text, all other history and runtime/services
are additional. This is a source-derived memory lower bound, **not an observed
OOM or completed modern performance measurement**. Evidence:
`modern-opening-memory-admission.json` under the external benchmark root.
No history truncation, output seeding, capacity increase or risky initialization
has been attempted. Full-history memory processing needs a separately bounded
implementation decision before this exact modern comparison can proceed.

There is also an unresolved intake-ownership boundary, recorded in
`modern-intake-ownership-admission.json`: the frozen source has NMSActive=1,
while the approved v4 extension adds requirement stock to the inactive-NMS
external-master route. The existing active route still requires its captured
master/queue owners. No configuration switch, master override or acceptance
waiver is authorized by adding the feed. The exact whole opening/profile/day
binding has not passed native admission. These are remaining step6 limits,
not proved engine defects or permission to alter the frozen case.

All63 affected focused checks pass, including seven requirement-stock checks,
the real connected calculation's effective override, old CSV modes,
historical-date guards, vehicle isolation and source-variant boundaries.
The actual216row stock feed also passes complete typed parsing, date checks
and ordinal retention. Neither result substitutes for full-scale PostgreSQL
initialization/readback or modern day acceptance.

The human authorized the seven-step benchmark through legacy day one, then instructed a stop while independently resetting the modern installation. After read-only source inspection, the human chose **"Use synthetic next-day benchmark"**: copy the large3005 snapshot as opening, generate one conserved next-day raw CSV workload, and exclude unavailable GulfOil customer-source preprocessing from timing.

**Steps1–4 completed for the legacy portion. Original step5 attempt failed in Pick. After explicit human approval, the isolated vehicle correction PASSED in the one corrected rerun; that attempt stopped at a later BOR report schema mismatch. DBM/BTR remain unexecuted. There is still no completed-day legacy timing baseline and no modern run/comparison.**

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

## Approved correction executed — Pick passes; later report mismatch stops the day

Human reply to call_98195d12502940dbacd9b5277ee7fd97: **"Approve isolated legacy correction and one rerun"**. Proposal SHA fbb90e2cd8783552f761142acb791d20be51675b8abe8a017680924a834b16da; actual approval receipt recorded before creation of the new targets. Owner cb27310d-dc74-4eb8-b152-624b9c1c5bc2, evidence subdirectory `corrected-legacy-attempt-01/`, separate8owned databases/files. The original case and all CSV feeds remain byte-identical. New SQL source variant SHA9999cc27102d176401a24081bf61d6fe6ef7aaa339e110e5ebea18ca5facd438; only isolated Pick SQL/scratch schema changed, original canonical source stayed pinned. External bridge allows only the exact approved producer/hash and labels every call CORRECTED_LEGACY.9focused generator/variant-pin/Unicode-error-reader tests pass.

The new opening restore/verification took242.927seconds, outside the daily timing. Actual Pick SQL completed successfully in38.161seconds. Final6,568formed rows and1,516residual rows have no negative quantities, no unflagged unfinished rows and zero complete grouped SKU/location/parent/priority/vehicle quantity-conservation mismatches. Both complete typed relations are retained as compressed evidence. The earlier temp reproduction's6,603/1,481counts are not asserted as row-by-row parity: canonical ranking ties can change formed-row splits. Invariants and the actual rerun's complete rows are the proof for this attempt.

The one rerun then stopped on unchanged `CollectBOR_OrderAllocationData.sql` SHAe06d22c31b0b51b6ba375c4bdf8ddeac52806d6e0b5b1c362a77dd8d3b4b18da: SQL213, column/value count mismatch. Canonical creation DDL and writer use26columns; the restored snapshot table has those26plus15nullableSKULocAtt01–15attributes. The implicit INSERT supplies26values for41columns. Snapshot and target schemas match; this is a benchmark snapshot/engine compatibility gap that setup should have detected before execution. It is separate from the truck-allocation defect.

The failed report batch did not execute its statements: its script flag remains0 and BOR retains3,098old snapshot rows. External guard denied all later SQL. No UpdateBPR/final BPR reports, post-BPR site attributes, DBM or BTR execution is claimed. Reset4.021s; CSVload/fullreadback163.170s; validation58.094s; norms33.037s; partial BPR/RRR/Pick/reports203.152s; total461.537seconds is another FAILED partial attempt, not full-day throughput.

A narrow **unapplied** compatibility proposal explicitly names the same26destination columns and retains all41columns. Temporary-table execution produces3,098rows with zero complete26-field typed/duplicate differences versus the canonical26-column destination; all15extra columns remain present and NULL under the writer's unassigned nullable-field behavior. No formula, default business fact, supplier text, datatype, raw input or quantity change is proposed. Proof: `bor-explicit-columns-temp-proof.json`; exact patch/decision: `corrected-legacy-attempt-01/bor-report-compatibility-proposal/decision.json`, SHA6502ddaf2e3bf525e898c1954f4482f7a71d7ffd9179bea79425bc01b10120db. This producer was not included in the earlier one-script exception; approval is required before modifying it or resuming the failed day.

Proposed continuation preserves a cold copy of the failed owned files and all failed receipts, reconciles the accepted prefix, then runs only the previously unexecuted report operation and original remaining BPR-finalization/DBM/BTR stages. It never repeats ingestion, validation, norm processing, BPR requirements, rationing or Pick, nor creates a second business date. A continued run would have separately measured active phases; their sum must not be called one uninterrupted wall-clock benchmark. No continuation or new daily attempt has been executed.

Both8-database attempts are now READ_ONLY/OFFLINE. No active owned work is left; a completed temp diagnostic's idle connection was closed specifically to release its own offline-transition lock (no business transaction was open).3005container identity/image/start/state matches the original receipt. Original failed files/hashes, protected four databases, canonical legacy code, modern installation, frontend and MTO remain unchanged. No Docker resources/services were created/restarted/replaced.
