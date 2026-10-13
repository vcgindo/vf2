# C02: one connected external logistics ledger

The authoritative execution status remains in `F:/freshvcf/docs/handoff-3005/TRACKER.md`. This file specifies the simple C02 case and its acceptance boundary.

## Purpose and boundary

Use one retained SKU (`337`) at `DP010290 -> LDC001 -> PL002`, with PL002 remaining an external supplier. Keep the full retained 200-SKU/20-location metadata, names and hierarchy. Only DP010290 and LDC001 are active calculated pairs. Their unchanged RLTs are 6 and 5; the inclusive test horizon is 1–18 July 2026.

This reduces the S1 target of 4–8 SKUs and two children so the newly connected allocation, report-source and external shipment values can be independently derived before execution. Stock100 versus allocation18 does not test competition or rationing under scarce shared supply. That required coverage remains unmet G2 work; passing this case cannot close allocation as a whole.

Starting Norms12/120 and Spike/PSO thresholds50% are explicit test overrides. Retain pack1, Elephant cap1000, RCP/GCP from the catalogue, no utilized stock, no reservations or competing demand. Initial physical stock is DP0/LDC100/external supplier1000. No calculated orders, recommendations, acceptances, reports or histories are seeded. Original ordinary-order identity counter starts at1.

## Finite input sequence

| Day | External facts and reason |
|---|---|
| July1 | Ordinary order `C02-ORDINARY-001`, qty2, then spike `C02-SPIKE-001`, qty18; both customer expected dates NULL. The producer assigns keys2 then3. |
| July2 | Nonempty ordinary-only order feed removes the dispatched spike. External dispatch18 from LDC to DP reduces LDC stock100 to82; DP GIT becomes18. |
| July3–4 | Same physical stock and GIT18. Shipment customer ID, route, quantity, LR and creation/gate-out dates remain fixed. |
| July5 | DP receives18; stock18, GIT0, Receipts18. Remove the shipment from the current transit population. |
| July6 | DP customer consumption18 reduces its stock to0. |
| July7–18 | Stable external stock; ordinary qty2 remains outstanding. No new dispatch, receipt or consumption. |

Half-RLT transit uses explicit nonnegative round-half-up `(RLT+1)//2 = 3`. This external movement duration does not populate canonical standard SLT. The generic importer leaves SLT and Price NULL; derived ETA, valuation and delay statuses retain the corresponding NULLs. No positive site-specific SLT/Price/delay coverage is claimed.

The shipment OrderNo equals the spike customer ID. There is no native allocation-to-shipment foreign-key transition in this producer. Acceptance is exact external ID/quantity/route/date reconciliation and ledger conservation. Do not describe it as an implemented fulfillment workflow. Closing the outstanding spike on dispatch prevents repeated allocation; shipment intake itself does not reduce outstanding Qty.

## Independent expected values

`expected-source-values.json` records complete ordered rows for 15 source families on every day, including both report histories. The worksheet uses literal values and simple contract arithmetic; it does not import or run the application to create expected results.

- Day1: spike first service LDC, due at DP July7, LDC-to-DP route due July1. Sole allocated-order row is qty18/allocated18/pack allocation18, key3, Green/BPP0.00.
- Canonical allocation date distinction: the LDC residual-child candidate subtracts LDC RLT5 from that July1 route date, giving AllocatedOrders.DueDate June26. Stock-bearing-node promotion changes its endpoints to LDC-to-DP without replacing the date; DueDateAtDest remains July7. The original frozen expectation incorrectly used July1. Preserve that frozen value and original failed assertion; the separately authorized `c02-expectation-amendment-v1.json` changes only this one day1 expected field (SHA256 `14c8d7ecfc297b1f58b59263281470012be4e490283aaeb16920a7e97e40e473`). Derivation and exact canonical hashes are retained in `c02-day01-diagnosis-v1.json`; this is an expectation correction, not a business-rule change.
- Day1 RRR: Order row has requirement18 and allocation18 in Green. Norm row has Norm12, VirtualNorm24, requirement12 (Black4/Yellow4/Green4), allocation24 (Black8/Yellow8/Green8), parent leftover70. Preserve the canonical report's distinct requirement and allocation calculations; do not reinterpret their sum as physical dispatched quantity.
- After spike closure, no allocated-order rows. RRR is empty July2–5; July6–18 has the sole Norm row, Norm/VirtualNorm12, requirement/allocation12 split4/4/4 and parent leftover70.
- Normal BOR uses its own requirement producer: parent Norm120 minus stock100 gives20 on July1; stock82 gives38 thereafter. SOB100/MOQ1 leaves these quantities in Green. Actual supplier attribute01 is `PL002`; the remaining attributes are NULL.
- BOROA uses requirement bands: on July1 parent stock100 consumes child residual order18, Red40 and Yellow40, leaving Green38. After dispatch, stock82 with no residual order also leaves Green38. Parent Norm/VirtualNorm120, GIT0 and external-parent leftover0; penetration16.67 then31.67. The approved nullable text availability contract supplies NULLs for the 15 unavailable BOROA attributes.

Supplier timing is explicit: root BOROA reads empty prior SOB/MOQ and uses the canonical top-node fallback SOB100/MOQ0. Normal BOR refreshes from the supplied raw SOB100/MOQ1 on day1. Own successors read that persisted SOB100/MOQ1 for BOROA. The expected positive quantities exceed either MOQ and do not conceal this ownership distinction.
- Transit and transporter complete rows preserve NULL current location/contact/remark/SLT/ETA/Price and actual dates/quantities. No rejected shipment rows are expected.
- An external current request and initial remarks test complete typed capture, empty text, NULLs, duplicate BOR remark ordinals and supplied timestamps. The June30 BPR remark remains through July13 and expires July14 under the existing 13-day cutoff. This is not SubmitRequest or UI remark-workflow acceptance.

Source derivation references: canonical CalculateDD.sql, CalculateRoute.sql, ReqInColorBand.sql, OrderAllocation.sql, GenerateRRR_OrderAllocation.sql, GenSupplierWiseReq.sql, CollectBOR_OrderAllocationData.sql, ValidateGoodsInTransit.sql and GoodsInTransitTransporterMaster.sql; their exact identities accompany the frozen manifest. Approved normal BOR Black and BOROA nullable-text amendments retain their separately recorded scope. A bounded independent static review derived the order and RRR values and checked successor assumptions.

## Execution proof

Freeze exact inputs, expectations, derivation, runtime and resource identities before database creation or calculation. Use one new uniquely named database inside the existing bounded S2 PostgreSQL container and original owned test principals. No additional container or port; no changes to serving stacks or earlier C01/C03/C04 evidence.

Require actual fresh migrations, exact typed initialization readback, all 18 own-predecessor days, complete input/output readback and source rows, preserved ordinals/NULLs, expected history growth, and final resource/source protection checks. Stop at the first unexplained difference and preserve the attempt. Never edit frozen expectations to match a run, replay an accepted day, or seed calculated outputs.

C03/C04 retain only their accepted independent action/horizon scope. This case does not establish complete BPR/BTR report semantics, every MDM1–13 workflow, all enabled producers, shared-supply competition, UI readers/preparation, deployment, capacity or production handoff readiness. Those remain in the single G2/G3–G5 tracker as applicable.
