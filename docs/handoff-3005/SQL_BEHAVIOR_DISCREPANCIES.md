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

## Verification boundary

Permanent coverage: `tests/test_established_order_routes.py`, plus adjacent order
identity/own successor, allocation, temporal policy and complete native-flow
tests. Full-day PostgreSQL outputs, report preparation and UI remain subject to
the approved benchmark; pure checks are not proof of those unfinished exits.

External finding/approval/corpus proof is under
`D:/freshvcf-build/evidence/large-data-day1-benchmark-20261019/modern-fresh-performance/policy-integrity/established-route-proposal`.
Future entries must distinguish observed runtime failures from source-derived
risks, and record any accepted SQL flaw without silently changing its meaning.
