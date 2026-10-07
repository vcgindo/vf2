# DBM timing diagnostic: one sample per engine

**The strongest optimization lead is repeated full-history scans in white, spike
and supply suspension.** Each scans 1,240 masters against 27,280 observations:
33,827,200 candidate pairs per pass. The three functions account for171,932,274
calls to the suspension key helper in the instrumented sample. No optimization
was implemented.

**The exact breakdown of the original33.733 seconds remains unproved.** cProfile
was substantially more intrusive than the intended lightweight instrumentation:
modern DBM measured211.011s under it. Its timings/proportions must not be scaled
to33.733s, treated as normal production costs, or compared as a speed ratio.
No repeat sample was run. The controller correction on profiler bias was retained.

## Measurements and coverage

| Sample | DBM wall seconds | CPU seconds | Boundary |
|---|---:|---:|---|
| Retained modern reference |33.733|33.729 worker|Existing generator timer|
| New modern, cProfile active |211.011|210.971 worker|Same selected_stages next() boundary|
| Retained legacy reference |18.771|0.172 client|DBM-role scripts except DailyDataImportExport|
| New legacy, script timers/session statistics enabled |54.363|16.578 client|Same script classification,64 invocations|

Different instrumentation and database resources prevent matched ratios or
regression claims. Legacy client CPU is not SQL server CPU. Modern production
mode kept mandatory operational persistence; actions, parity, diagnostic
snapshots, extra result exports, preparation and publication were disabled.
Only DBM was profiled; necessary surrounding daily work was not investigated.

### Modern: disjoint timed stage intervals

Each row includes its called functions but excludes other stage intervals and
caller work between yields. These rows sum to211.011s; nested tables below are
**alternative views, not additional time**. Fifty yields plus exhaustion give51
calls. The postrules function computes both results before yielding, so its
`discard` interval includes both discard and report generation.

| Stage group | Profiled wall s | Worker CPU s | next() calls |
|---|---:|---:|---:|
| ingestion | 8.743 | 8.738 | 1 |
| Other suspensions | 20.180 | 20.174 | 19 |
| suspension13 | 43.512 | 43.503 | 1 |
| suspension14 | 68.594 | 68.585 | 1 |
| suspension15 | 29.540 | 29.536 | 1 |
| Rules 1-6 and 12 | 10.487 | 10.485 | 7 |
| Postrules | 3.111 | 3.111 | 2 |
| Other final writers and exhaustion | 5.991 | 5.990 | 6 |
| suspension-history | 8.022 | 8.020 | 1 |
| Norm 0/1/2 report stages | 12.832 | 12.831 | 12 |
| **Total** | **211.011** | **210.971** | **51** |

Function-exclusive records total207.465s, leaving
3.545s outside the retained
function attribution. This residual is not a measurement of total profiler
overhead; overhead also perturbs attributed function times. No uninstrumented
paired sample or per-function CPU attribution was collected.

### Finest useful attribution in the three dominant profiled functions

Each function is called once. Own time excludes child functions; key and copy
columns include their respective descendants. The last column retains other
calls and any attribution gap. Each row reconciles to its parent total.

| Function | Parent wall s | Own/loop s | Direct key-helper subtree s | Direct deepcopy subtree s | Other/gap s |
|---|---:|---:|---:|---:|---:|
| apply_white | 68.594 | 27.632 | 34.133 (67,654,425 calls) | 1.123 | 5.705 |
| apply_spike | 43.512 | 12.053 | 30.487 (70,449,409 calls) | 0.899 | 0.072 |
| apply_supply | 29.540 | 8.590 | 19.626 (33,828,440 calls) | 1.263 | 0.062 |

Callsites: `mta/domain/dbm_suspensions.py:315` (supply),`:364` (white),`:392`
(spike), helper`:8`. White parses/checks each fact's date before testing its key;
spike repeats key comparisons and then scans joined receipt memberships;
supply scans the complete history for each master despite hoisting its master
key. Stage cardinalities show49 spike memberships and25 white memberships.
The source loops and exact call counts support the scan diagnosis independently
of the biased timing weights.

Across the whole DBM profile, `_key` has172,133,312 calls; `dict.get` has453,832,460.
`deepcopy` has33,663,977 total recursive calls (26,091 primitive calls),30.463s
exclusive and55.533s inclusive. Those copy/key totals overlap stage timings and
must not be added to them.

Other demonstrated work:

- `dbm_ingestion.py:74 calculate_extended_ocp`:7.493s inclusive; its master-match
  list comprehension1.694s and sorted observation traversal5.766s include child
  lookups. The traversal scans history per eligible master.
- `dbm_suspension_history.py:15 gather_suspension_history`:8.021s inclusive;
  contributor set comprehensions4.580s, direct key calls1.539s, deepcopy1.263s,
  own time0.634s and remaining calls0.006s. It joins1,240 stock and1,240 consumption
  rows, then scans contributor bags for each joined row.
- `ordinal_lookup.py`:9 index builds total0.965s;13,325 lookup initiations,
 26,650 SQLite fetchmany calls. The matching generator totals0.414s inclusive;
  index close0.006s. Existing ordinal indexing is a much smaller profiled cost
  than the three unindexed scans. These are observed costs, not a throughput or
  million-row capacity prediction.

### Legacy: disjoint script intervals

| Script group | Client wall s | Calls |
|---|---:|---:|
| Pre-selected controls/report scripts (unmatched) | 16.338 | 10 |
| ExtendedOCP (ingestion remainder) | 2.922 | 1 |
| Suspensions | 8.294 | 26 |
| Rules 1-6 and 12 | 16.473 | 7 |
| Postrules | 0.141 | 2 |
| Other final writers | 2.690 | 5 |
| Suspension history | 0.589 | 1 |
| Norm 0/1/2 report stages | 6.917 | 12 |
| **Total** | **54.363** | **64** |

The largest script intervals were CollectPhaseInData3.365s, ExtendedOCP2.922s,
CollectSeasonalityData2.853s and CollectFailedForceNormData2.796s. The control
scripts are outside modern selected_stages, making them unmatched bucket work.

**Finer legacy attribution was not obtained.** The adapter passes `owner.raw`
into DeliverySQL (`parity/adapters/legacy/temporal_day.py:140,289`), bypassing the
instrumented isolation.Cursor hooks. All execute/fetch splits and captured SQL
statistics messages are empty. Session STATISTICS TIME/IO was enabled around
these scripts, but its added overhead is unmeasured. The entire54.363s remains
unseparated into SQL calculation, driver/transfer, embedded result handling and
instrumentation. Server CPU, logical reads, waits and statement/procedure costs
are unavailable. There was no server-wide tracing or retry to manufacture them.

## Mapping to canonical SQL and unmatched work

| Modern operation | Canonical Scripts/DBM counterpart | New legacy script wall s |
|---|---|---:|
| apply_spike / suspension13 | SuspensionRules/07. SpikeToday.sql |0.233|
| apply_white / suspension14 | SuspensionRules/08. WhiteStock.sql |0.083|
| apply_supply / suspension15 | SuspensionRules/10. SupplyIssue.sql |2.639|
| calculate_extended_ocp | CalculateExtendedOCP.sql |2.922|
| gather_suspension_history | SuspensionRules/GatherSuspensionHistory.sql |0.589|
| Remaining suspensions / rules | RunCoreDBM.bat PRE/SUSP/POST and RULE1-6/12 bindings |Grouped above|
| Discard / reports | DiscardSuggestions.sql / DBMRules/08. GenerateReports.sql |0.089 /0.051|
| Order summary / norm1 advisory | Misc/UpdateOrderSummaryData.sql / AdditionalRules/Norm1IncreaseSuggestions.sql |0.012 /2.307|
| Norm-change export / history | DBMNormChange/ExportDBMNormChange.sql / NormChangeHistory.sql |0.043 /0.042|
| Norm0/1/2 data/detail/export/clear | Norm 0-1-2 Reports/Norm{0,1,2}Data.sql, GenerateNorm0-1-2Report.sql, ExportNorm0-1-2Report.sql, ClearNorm0-1-2ReportData.sql |Grouped above|
| Daily cleanup | ClearHistoryData_DBM.sql |0.285|

Mapping owner: `parity/adapters/legacy/temporal_delivery.py:105 sequence` and
`mta/domain/dbm_selected_chain.py:16 selected_stages`. SQL white/spike scripts
use key joins and current-date predicates; supply uses joined windows/grouping.
Modern ingest includes daily/order/exclusion import, but the retained legacy
bucket excludes those DailyDataImportExport scripts. Modern caller-side report
copies and PostgreSQL commit are outside selected_stages; unavoidable legacy
captures surrounding scripts remain outside this diagnostic's timed intervals.
Neither table is an API/UI or matched end-to-end performance comparison.

## Proposed DBM-only strategy, for later approval

1. Extend ordered, typed key-candidate lookup to white/spike/supply. Eliminate
   full master-by-history scans without changing matching-row order or duplicate
   multiplicity. The evidence supports fewer candidate comparisons, **not a
   defensible saved-seconds estimate** from this biased profile.
2. Apply the same bounded lookup approach to ExtendedOCP and suspension-history
   contributor joins. Retain tied-date ambiguity checks and all contributor
   reason arithmetic. Do not replace bags with sets or collapse duplicates.
3. Only after those changes, assess DBM-local copy ownership. The profile shows
   substantial copying but does not justify removing snapshots/copies blindly.
   Preserve predecessor immutability and every writer's input/output ownership.

Future acceptance must retain canonical SQL, exact ordered occurrences, NULL
exclusion, midnight/date windows, `(key,Norm)` grouping, duplicate receipt
multiplication, ceiling arithmetic and complete31 comparisons plus independent
RRR and persisted successor/action behavior for any changed DBM calculation.
No such validation campaign or optimization was performed here. Any less
intrusive timing follow-up needs a later human decision; no new run is implied.

## Reproduction identities and stopping point

- Evidence root: `D:/freshvcf-build/diagnostics/dbm-33733-001`.
  `samples-a001/modern-dbm.json` contains all51 intervals and389 function records
  with caller edges; `legacy-dbm.json` contains all64 script intervals.
- Probe source: `tools/dbm_timing_probe.py`, SHA256
  `20ba39216d52f7c76601e9deacb5c9739a3109abe630eb95eeb49de289a78736`.
  Host code checkpoint4897f72; immutable refined modern image
  `sha256:3791d148878aae8780200cb91fcee9e90920f9afb6f63f974d07a3569330c48f`.
- Frozen1240-pair June6 input SHA256
  `ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56`.
  Independent initial state per engine; no imported legacy calculated outputs.
- Modern run `87e8afc8-21aa-4b92-ade3-95bbbb774c97` completed production mode, with one
  committed run, zero actions and empty validation digest. SQL namespace prefix
  `VFTEST_Fresh_Offline_726490d1c903c67a_`; eight new exclusive owned databases.
- Workers4GiB/two CPUs; PostgreSQL1GiB/oneCPU, no host ports. Legacy retained
  the existing SQL server; matched SQL server limits were not established.
  Legacy worker peak2,445,631,488 bytes. Private credentials remain outside Git.
- First network-allocation failure preserved. Human approval permitted existing
  network reuse; one sample per engine then completed, sequentially, no repeats.
  Probe PostgreSQL was stopped with its data retained. No shared service changed.
- Existing31-comparison correctness evidence was reused, not rerun. No new parity
  claim. Refinement99d4854/b884ff7, readinessb89c790 and the original accepted
  June6-8 prefix remain protected. Full-run/publication holds are unchanged.
