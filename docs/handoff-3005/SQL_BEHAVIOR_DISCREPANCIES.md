# SQL and modern-runtime behavior discrepancies

Started 20 October 2026 at the user's request. Record confirmed differences where
the legacy SQL/batch tolerates, compares, truncates or continues differently from
the modern runtime. SQL Server does not inherently hide these defects; the exact
script, comparison or error-handling behavior must support each entry.

This is a technical finding ledger, not another execution queue. The sole live
status/approval/blocker tracker is `F:/freshvcf/docs/handoff-3005/TRACKER.md`.
Record the source, trigger, impact, disposition and executable proof for each
finding. Do not infer parity or broaden an exception from a passing count.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

## SQL-001 — historical servicing warehouse no longer on the current route

- **Evidence:** canonical `Scripts/BPR/Ration_Scripts/CalculateRoute.sql`, SHA256
  `66abe2e41ce2fb9d9a3f8583001d53a7cdc7a4fa2306a73a4da66f36f7416a41`.
  Its opening comment explicitly describes hierarchy changes and routing to the
  current supplier/plant when historical first service is no longer reached.
- **Trigger:** three of 1,514 established Spike orders in the frozen opening have
  first service `0000_Discontinued` or `0000_HighInventory` outside today's route.
- **Legacy behavior:** retain the historical first-service field and order DueDate;
  rebuild the route along current DBM parent/RLT edges to the terminal node.
- **Modern defect:** require historical service to belong to the current node set,
  then require it to be reached. The whole day failed after valid input capture.
- **Impact:** route-derived requirements, shared allocation and Pick/report results
  can be affected downstream; this is not limited to three output rows.
- **Correction/proof:** narrow established-route fallback, retaining historical
  fields and invalid-graph checks. Full comparison preserves all 1,511 previously
  valid routes. The three actual cases and the previously unused off-path fixture
  have permanent regression tests through requirement/report producers.
- **Authority:** direct human approval to `call_d113a503430a43b89d047558a0b284e9`;
  exact original decision SHA256
  `c41d429f496c95c233d2c864e6a5364fdf82a8e3cfeb5a08aad0f74aa0afd4fc`.

## SQL-002 — SQL-equivalent historical identifiers compare differently in Python

- **Evidence:** `CalculateRoute.sql` stops at `CurrentWhCode=FirstServicingWhCode`;
  the selected ASCII SQL comparison ignores case and trailing spaces. The existing
  ported `_sql_key` uses that same selected comparison domain.
- **Trigger:** historical `PARENT` or `parent ` with current node `parent`.
- **Legacy behavior:** recognize the servicing node and stop there.
- **Modern defect:** exact Python equality could mistake a valid service node for
  an obsolete one; after fallback admission it could silently route too far.
- **Correction/proof:** use the selected case/trailing-space comparison only when
  deciding whether historical service has been reached. Preserve stored text.
  Permanent tests assert identical route/dates for all three representations.
- **Boundary:** no global identifier rewriting or arbitrary Unicode collation
  equivalence is introduced. This is a diagnostic refinement of SQL-001.

## SQL-003 — legacy route loop stops after 100 iterations

- **Evidence:** `CalculateRoute.sql` increments `@loopCount` and forcefully breaks
  when it exceeds100, printing a diagnostic after100 route insertions.
- **Trigger:** a route needing more than100 nodes; the supplied master graph needs
  at most6 including its terminal. This was found by source inspection, not a
  replay of the large day or an observed failure in this workload.
- **Legacy behavior:** may leave an incomplete route while the batch continues.
- **Modern defect:** the walker could produce a deeper complete route and silently
  exceed the canonical source's certified boundary.
- **Correction/proof:** both new and established routing explicitly raise
  `R1_ROUTE_SOURCE_LIMIT` beyond100 nodes. Boundary tests accept100 and deny101.
  This blocks an uncertified branch; it does not copy incomplete output or repair
  the legacy algorithm. Supported shallow routes/formulas are unchanged.

## SQL-004 — zero-quantity orders pass intake but fail demand calculation

- **Observed failure:** run `a4accc28-8af1-40b2-ac66-0b02e8771e8a` completed
  input capture, then failed in `collect_orders` with “outstanding quantity
  outside supported nonnegative range”. No output committed; no OOM occurred.
- **Trigger:** the frozen opening contains30 zero-quantity orders. The daily
  feed contains1,393 zero rows, of which30 match the opening BPR master closure.
  Neither population contains negative quantities.
- **Legacy behavior:** `ImportSpikeOrders.sql` retains matching orders and
  updates their Qty, including zero; it closes absent identities rather than
  treating zero as omission. `CalculateReq.sql` sums Qty for PSO and due Spike
  demand, and separately filters positive remainder for allocation.
- **Modern defect:** `r1_order_input.validate_order_input` accepts nonnegative
  SQL integers and reconciliation retains zero correctly. Downstream
  `collect_orders` and the direct `classify_spike` seam require positive
  quantities, contradicting that accepted source contract.
- **Proposed correction:** permit zero at those two quantity checks only.
  Preserve the order, key/part identity, original quantity, dates, classification
  and normal closure rules. Keep negative, fractional, nonfinite and oversized
  inputs rejected. Do not remove zero rows or alter the global number validator.
- **External candidate proof:** four small complete requirement/rationing/BOR/Pick
  cases pass: new zero PSO, retained zero PSO with empty feed, existing Spike
  amended to zero, and multipart Spikes amended to zero. All ten existing
  fixture output digests remain identical; eight invalid-quantity checks still
  reject. This is pure candidate testing, with no database or benchmark replay.
- **Status/authority:** human “Approve zero-order correction and continuation”
  to `call_798281cd3593406597007b099b172f39`, decision SHA256
  `14f8df7f6eb8eb5985f981422f07b0c4c216ee34913629b7c34c85d86be8fd1c`.
  The exact two-check candidate is applied.64 affected tests pass, including
  seven permanent zero-order tests. The fresh source-bound continuation still
  requires packaged-image smoke before runtime; no successful large day claimed.

## Current correction/readiness disposition — 20 October 2026

Human authorized the three fixes together and focused conditional-risk checks,
explicitly prohibiting a full daily run without further approval.

- **SQL005 fixed:** only PSO parent-stock admission now accepts signed integral
  values. Negative proportional values and parent leftovers remain signed;
  allocation remains zero where the canonical SQL assigns no positive amount.
  Negative demand, fractional/nonfinite stock and invalid packs still fail.
- **SQL006 fixed:** cleanup uses the existing checked configured-date cutoff,
  with the source's inclusive deletion boundary. NULL report dates survive
  DELETE's UNKNOWN predicate. Production preflight checks the configured
  horizon and actual date range before calculation.
- **SQL007 fixed:** all three30-day Norm reports ignore NULL consumption in
  positive predicates and SUM. NULL report dates are excluded. Duplicate
  observations and occurrence-order safeguards remain. All-NULL totals still
  fail the pinned NOT NULL TotalSale target; integer overflow is not hidden.

Verification:59 tests passed in the first affected batch;55 tests ran in the
second batch with one existing skip. The12 new boundary tests occur in both,
giving101 unique passing tests and one existing skipped integration test.
An initially included historical `test_complete_daily_pick` module cannot
import because it depends on the removed `mta.evidence` module through parity
helpers; it was not repaired or counted as a pass. Active native Pick-state and
vehicle-option tests passed. No image build, database, full day or service was
started. These are source-level proofs, not a fresh packaged-image proof.

**The conditional risks are diagnosed, not waived or declared absent:**

- RRR tests prove that tied children are accepted when no scarce residual pack
  crosses the tie, and refused precisely when that boundary would choose an
  unspecified winner. Both input orders reproduce the refusal. Canonical
  ROW_NUMBER has no additional key. Adding an arbitrary tie-break would violate
  the instruction to preserve legacy semantics.
- Pick tests prove that exact-fit NULL dimensions remain NULL, zero allocations
  remain excluded, and an underfilled NULL-only prefix stops for nontermination.
  A non-NULL row later in the same queue does not necessarily resolve the
  prefix. A non-NULL first row can allow that small mixed queue to terminate;
  reordering production rows is not an authorized remedy.
- Additional frozen-input scan:89 SKUs have NULL volume;79 of their SKU/location
  pairs are in the opening DBM master, two of these pairs have positive Norm,
  and24 daily order-feed rows for those SKUs have positive quantities. Thus
  they cannot all be dismissed as unused catalogue entries. The263 RRR
  equal-Norm/RLT/priority groups remain potential, not calculated, ties.

**Readiness: not cleared for a full daily run.** The successful current-day
allocation/dispatch inputs needed to decide whether these exact conditional
stops occur have not yet been produced. This work does not authorize an
end-to-end calculation to discover them. There is no source-supported general
repair that both selects an unspecified RRR winner or terminates a genuinely
stuck legacy Pick queue and preserves the existing semantics. Keep the stops.
Any change to priorities, missing dimensions, tie selection or loop outcome
requires an explicit business/input decision; do not replace it with a generic
"continue" waiver. No calculation results, current facts, frontend or MTO were
modified by these conditional checks.

## Read-only downstream audit — 20 October 2026

The human stopped the goal and then requested an audit before any restart.
Source examined: `75bc550b3bb201bdb6478a17d2df25c23e216388`.
No image build, database access, master loading, daily execution or product-code
change was made for this audit. Five small isolated function probes reproduced
the cases below; these are not another benchmark day or completed-stage proof.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

### SQL-005 — signed adjusted parent stock rejected by PSO allocation

- **Source-derived defect, not an observed April8 failure.** Stock calculation
  explicitly supports a signed `stock_for_rationing_override`. `_pso_inputs`
  retains that stock unless normal-ration leftovers replace it. The downstream
  `allocate_spike_pso` calls the nonnegative `_integer` on parent stock.
- **Canonical source:** `CollectDataForPSORationing.sql` copies
  `StockForRationing`, followed by a conditional normal-leftover update.
  `PSORationing.sql` retains signed ParentStock, initializes RawAllocation to
  zero and updates it only when proportional allocation is positive. It does
  not reject the entire day for negative adjusted parent stock.
- **Probe:** one child with zero demand and parent stock -1 raises
  `parent stock must be finite and non-negative`. No calculation formula was
  altered. A correction would need to preserve signed proportional/leftover
  values, not clamp the input globally.
- **Frozen case relevance:** no negative parent-stock trigger established.
  The frozen reservation mode is Norm-percent (2), utilized stock is zero,
  and the extra 216-row feed overrides requirement stock only. Generated
  downstream balances were not recomputed by this audit.

### SQL-006 — configurable DBM cleanup accepts only 370 days

- **Confirmed configuration conflict:** `dbm_daily_cleanup.daily_cleanup`
  rejects every horizon other than370. Production preflight checks the supplied
  `DailyConsumptionHorizonDBM` as a SQL integer without this restriction.
- **Canonical source:** `ClearHistoryData_DBM.sql` uses the configured integer
  in DATEADD. There is no fixed370 test. A legitimate365-day configuration
  passes that source contract but the modern pure function rejects it.
- **Frozen case relevance:** current value370, so this is not the current
  April8 blocker. A correction should use the existing checked date-cutoff
  semantics and preserve the source's inclusive deletion boundary.

### SQL-007 — 30-day Norm reports do not preserve SQL NULL aggregation

- **Confirmed function-level conflict:** `dbm_norm012.data_stage` on the
  30-day branch compares `Consumption > 0` and sums values without skipping
  NULL. A mixed NULL/2 observation group raises TypeError before producing a
  report. This applies to the shared Norm0/1/2 30-day branch.
- **Canonical source:** `Norm0Data.sql` uses CASE and SUM; NULL fails the
  positive predicate and is ignored by SUM. A mixed group has total2 and one
  positive observation. All-NULL groups require their own target-NULLability
  check; do not replace them with invented zeros.
- **Frozen case relevance:** zero NULL Consumption cells, no duplicate daily
  grains and zero inherited DBM daily history. The78,309 NULL Stock cells are
  a different field and must not be counted as this trigger.

### Remaining deliberate stops — not authorized fixes

1. **RRR tied final pack:** `allocate_rrr` stops if an insufficient final pack
   crosses children tied on penetration, Norm, RLT and priority.
   `RationPacksize.sql` uses ROW_NUMBER with those keys and no final unique key.
   A two-child pure probe reproduces `RRR-PACK-TIE-GAP09`. The frozen masters
   have263 sibling groups sharing positive Norm/RLT/priority, but that does
   **not** prove tied computed penetration or scarce residual stock. Whether
   any actual allocation reaches this stop remains unknown. Do not invent a
   SKU/location tie-break or call an arbitrary legacy winner deterministic.
2. **Pick NULL-dimension no-progress:** a positive underfilled queue with a
   NULL volume can leave SQL capacity comparisons UNKNOWN and make no progress.
   The modern producer explicitly stops instead of looping. A one-row pure
   probe reproduces that stop. The input has89 of2,189 SKUs with NULL volume,
   but the actual positive dispatch populations, logistics partitions, other
   rows and truck capacities determine whether it triggers. Missing volume
   alone is not evidence of a failed day. Do not fill it with zero by default.
3. Other guarded ambiguities remain: conflicting UPDATE candidates,
   order-allocation ties without retained keys, unordered occurrence text,
   SQL integer/decimal overflow and unsupported identifier collation.
   These require specific evidence and disposition, not blanket relaxation.

### Coverage and outcome

Reviewed the remaining call path through requirement aggregation/advance
allocation, normal RRR, PSO allocation, BPP/bands, BOR/BOROA, native Pick,
order-source projection, BPR finalization, selected DBM rules/reports/cleanup
and BTR/history validation. The audit inspected guards and their source/data
conditions; it did not execute these stages on the large workload.

Frozen CSV scan:97,097 unique DBM master pairs; no nonpositive RLT, negative
Norm, non-ASCII master identifiers or conflicting SKU dimensions; all non-NULL
dimensions have supported scale3. Current report cleanup horizon370. No
inherited daily history. Positive pack and RLT checks protect source division;
zero *new* Spike cannot arise from the nonnegative strict-greater classifier,
while zero *established* orders follow the separately corrected route/demand
path. Those guards must not be indiscriminately removed.

The repeated failures reflect uneven contract coverage: intake validates one
domain while older shared calculation seams and selected report helpers enforce
another. Prior small fixture success did not cover the composition over
production-shaped inputs. Broad guard deletion would hide source ambiguity and
introduce wrong results. Repair evidenced conflicts together with permanent
boundary tests, and separately resolve any evidenced ambiguity.

Audit script, five probe receipts, frozen-data counts and canonical SQL hashes:
`D:/freshvcf-build/evidence/large-data-day1-benchmark-20261019/modern-fresh-performance/route-integrity/remaining-validation-audit.py`
and the matching `.json`.
This is not a restart clearance or an assurance that all future valid legacy
datasets are covered. Goal and benchmark remain paused; no new run is released.

## Verification boundary

Permanent coverage: `tests/test_established_order_routes.py`, plus adjacent order
identity/own successor, allocation, temporal policy and complete native-flow
tests. Full-day PostgreSQL outputs, report preparation and UI remain subject to
the approved benchmark; pure checks are not proof of those unfinished exits.

External finding/approval/corpus proof is under
`D:/freshvcf-build/evidence/large-data-day1-benchmark-20261019/modern-fresh-performance/policy-integrity/established-route-proposal`.
Future entries must distinguish observed runtime failures from source-derived
risks, and record any accepted SQL flaw without silently changing its meaning.
