# S2 C02 simple allocation and logistics proof

Evidence boundary: the retained one-SKU, two-active-pair C02 case, July 1–18, 2026. This document records proof scope; the sole programme status is `F:/freshvcf/docs/handoff-3005/TRACKER.md`. [S2_C02_CASE.md](S2_C02_CASE.md) defines the case and [S2_C02_EVIDENCE.json](S2_C02_EVIDENCE.json) binds 103 external evidence files by SHA256 and size.

## Result and limits

The eighteen-day case passes within its declared simple allocation/source/logistics scope, with one explicit controller-approved correction to the original day1 expectation. All 270 complete source-family comparisons pass under that amendment. Every daily proof verifies complete typed input/output/source readback, source and input identities, owned initialization, predecessor identity/output digest, required closing order/Norm values and supplier opening/closing state. Final reconciliation verifies all 54 external ledger rows and the corresponding active-pair BPR and DBM daily facts.

This does not close G2. It does not prove constrained shared supply, competing-child allocation, an automatic allocation-to-shipment fulfillment workflow, all MDM1–13 workflows, every enabled producer, complete BPR/BTR report semantics, UI behavior, production-volume capacity or deployment readiness. The shipment customer ID, route, quantity and dates reconcile through an external ledger; no native fulfillment foreign key or workflow is claimed. SLT, ETA and valuation NULLs are retained, so nonnull site-specific logistics coverage is also separate.

## Exact execution binding

| Binding | Identity |
|---|---|
| Database | `handoff3005_s2_c02_20261014_001` in the existing sole isolated PostgreSQL container |
| Frozen manifest | `c02-case-frozen-v2/manifest.json`, SHA256 `ea16b7ecb4bc79024eef64b95d4836b70b06b875bd1ddf53ba594ad16e3ca906` |
| Operator input | SHA256 `9dd22117954175130b00b627856fe60e1709771c1323b38257aa2833112ff783` |
| Initialization | `03b484ee-b183-4f2c-b8d4-2c858b1afc72` |
| Source digest | `04cf25d05f7dbfc77eb61d47f69af06e226c546bc5cfcbd83a1052387f29aa0d` |
| Configuration | `553fa9c6e2a4c520edb908de2b7c2012f9fd748eb905f72bd33f3568597af08f` |
| Terminal run | `e93fc00f-6dbd-43ca-b40e-ca91652fc181`, July 18 |
| Terminal output digest | `6215d097aba260260fd33e54d1711d894a1c1584d16653aa84a260ffb2f8839e` |
| Terminal full readback | SHA256 `0cd6b87fabcdd429672479b4230f946f4b15de89c4aba300728a0b73ff597d70` |

All evidence below is under `D:/freshvcf-build/evidence/handoff3005-s2-20261013-001`. The frozen source archive contains 854 runtime files; base commit `837ef17fe5465200736ef29429a4c1bb0b8081ad` alone does not identify the later integrated source. Use the frozen file manifest/archive for exact reproduction.

## Preserved failures and amendment

The first migration-plan invocation used the wrong environment file and failed its issuer assertion before Django setup or migrations. Its log is preserved. The corrected invocation passed the plan and applied the actual fresh schema through migration0127. Registration, exact typed initialized input and all thirteen native family bootstrap bindings passed.

The first day committed successfully as run `7a3b3f15-6a5b-4053-81bc-d204d4868b4f`, but its original frozen assertion failed: AllocatedOrders ordinal0 DueDate was June26, while the expectation said July1. Execution stopped before day2. The original `c02-execution-v1/STOP.json`, readback, difference and frozen expectation remain unchanged.

Independent canonical diagnosis established that July1 is the parent route date. OrderAllocation.sql195–204 subtracts LDC RLT5 for the residual-child candidate, giving June26. Its stock-bearing-node promotion at255–259 changes endpoints without replacing that date. The separate destination-date update retains July7. Both primary and independent review corroborated the port; no code or input correction was supported.

The controller approved only `c02-expectation-amendment-v1.json`, SHA256 `14c8d7ecfc297b1f58b59263281470012be4e490283aaeb16920a7e97e40e473`: day1 AllocatedOrders ordinal0 DueDate July1→June26. It carries old/new values, affected run, canonical source hashes and derivation. The existing committed day was reverified under PostgreSQL `default_transaction_read_only=on`; the complete typed readback remained exactly equal to the original. All fifteen source families and remaining day1 assertions passed. No calculation, new database, source/input change or seal rewrite occurred. Days2–18 then consumed the same chain and unchanged remaining expectations. There was no further divergence.

## Proved business boundaries

- Day1 computes ordinary key2 and spike key3, first service LDC, destination dueJuly7 and the full canonical allocated-order row for18 units. Both full RRR rows, normal BOR, BOROA, supplier requirement and history values match independent literal expectations.
- Day2 closes the spike through the nonempty ordinary-only order feed. The eighteen-unit shipment is published on days2–4, with exact transit/transporter dates, ageing and NULL values. It disappears on receipt day5; consumption18 occurs on day6. Ledger conservation is checked against captured external facts and typed BPR/DBM current-day rows for both active pairs. External PL002 is not fabricated as an active DBM pair.
- Every successor consumes its own persisted prior output; root supplier defaults and later SOB100/MOQ1 opening state are verified. Complete BOR/RRR histories grow according to frozen expectations.
- Initial requests and remarks retain supplied values, NULLs, empty text, duplicate ordinals and timestamps. The June30 BPR remark remains through July13 and expires July14. This proves capture/retention, not interactive request or remark workflows.

## Protection and evidence

`c02-resource-after.json` verifies six protected serving identities, start times, environment hashes, mounts, ports and resource settings unchanged. The same two owned containers remain within their original limits, without host bindings or OOM. All854 runtime files and original frozen inputs/expectations are unchanged. No serving stack was restarted or replaced.

`c02-execution-amended-v1/case-result.json` binds the18 complete daily readbacks and chain. `close-c02-proof.py` verifies the270 full source comparisons,54 ledger rows, typed BPR/DBM facts, frozen identities, original failure and additive amendment. These are separate from the previously accepted C03/C04 action proofs; no action campaign was repeated. Controller review of this C02 submission does not release S3.
