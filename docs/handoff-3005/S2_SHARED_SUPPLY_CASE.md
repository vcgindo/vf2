# C02 constrained shared-supply supplement

This finite S2 case extends the accepted simple C02 proof without repeating its logistics or action campaigns. The sole status and execution release remain in `F:/freshvcf/docs/handoff-3005/TRACKER.md`. Source checkpoint:7890415. No runtime change is proposed.

## Existing evidence and remaining boundary

The native allocation component tests already cover self-stock deduction of original Qty, canonical integer pack division, GIT netting, residual parent/NULL customer-date behavior, duplicate joins and differing UPDATE-winner denials. C02 proves same-run native source publication and persistence for one SKU/one child. Neither proves connected competition between two children. These component and source-persistence boundaries may be reused; their prior acceptance does not establish this case's expected winners.

## Retained population and facts

Full retained200-SKU/20-location catalogue metadata remains unchanged. Active SKUs337/5708/5954/6249 each use childrenDP010290/DP020819, parentLDC001 and external supplierPL002. RLTs, names, hierarchy, pack1 and control values remain retained; starting child Norm12, parent Norm120 and Spike/PSO thresholds50% are explicit test overrides. Original C01 action-specific RCP/GCP overrides are removed in favor of retained values. SuperDelayFactor2 is explicitly supplied because source publication requires that setting even for empty transit.

| SKU | Child RLTs (DP010290, DP020819) | Parent RLT | Parent stock | Lower-key order child |
|---|---|---|---|---|
|337|6,5|5|9|DP010290|
|5708|5,4|5|10|DP020819|
|5954|7,6|4|35|DP010290|
|6249|7,4|7|18|DP020819|

Child stock, GIT, receipts and consumption are zero. Each external supplier has stock1000. There are no physical shipments; stock stays constant. The21-day horizon July1–21 is3×maximum RLT7. Allocation recommendations do not themselves mutate external physical stock. Expected global stock conservation is4072 across336 daily ledger rows.

## Canonically defined order identities

The discarded, unexecuted first draft proposed simultaneous new orders. Canonical CalculateDD.sql uses an unordered multirow identity insert, so file order could not determine child priority. Preserve that draft as inapplicable; it is not executed evidence and its generated-key assumptions do not transfer.

The revised draft introduces exactly one new order per day. Days1–8 introduce eighteen-unit spikes at337/DP010290,337/DP020819,5708/DP020819,5708/DP010290,5954/DP010290,5954/DP020819,6249/DP020819,6249/DP010290, respectively. Each feed retains all existing orders. Day9 introduces only ordinary order337/DP010290, qty2. Starting counter1 therefore gives spike keys2–9 and ordinary key10, without a competing new-row insertion.

Each spike's supplied customer expected date isJuly10 plus its retained child RLT. The parent route date is thereforeJuly10 for all eight orders. Day10 is the common competition. On day11 the external order feed withdraws all spikes and retains the ordinary order; no dispatch or fulfillment transition is inferred from this external cancellation. The ordinary feed stays nonempty throughday21.

## Complete values, priorities and conservation

The independent worksheet uses literal contract arithmetic and does not import or run application calculation code. It supplies all fields for fifteen source families on all21 days, including complete BOR/RRR histories. Required complete typed row multisets retain duplicates; tables with no canonical ORDER BY are not given an invented cross-SKU ordering. Every actual persisted ordinal is retained in complete readback. No field is excluded and counts alone cannot pass.

On day10, canonical order-allocation priority compares candidate due date, customer expected date, OrderKey, then RLT descending and Norm descending. The residual-child path supplies NULL customer date and equal candidate due dates within each SKU. Each order has exactly one qualifying hierarchy candidate. Lower OrderKey therefore wins before RLT; the5708 and6249 cases distinguish that from a larger-RLT winner. Orders share stock only within their own SKU/source partition.

The following is the original frozen worksheet, retained for traceability. SKU5954's day10 normal17/18 expectation and associated residual explanation were subsequently disproved; see the preserved failure below and the accepted values in `S2_SHARED_SUPPLY_PROOF.md`.

| SKU | Day10 order allocations to the two children | Original day10 normal expectation | Other days' normal allocations | Normal leftover on other days |
|---|---|---|---|---|
|337|9,0|4,5|4,5|0|
|5708|0,10|5,5|5,5|0|
|5954|18,17|17,18|12,12|11|
|6249|0,18|9,9|9,9|0|

The original worksheet applied RLT ascending to the odd unit for337 and5954. This priority applies only after the residual eligibility test; the original5954 conclusion omitted that test. Distinct RLTs avoid an undefined exact physical tie. No new winner is invented for fully tied canonical sort keys; such inputs retain their existing unsupported boundary.

For each SKU/source, compare complete allocated-order rows and prove summed pack allocation plus temporary order-allocation leftover equals available parent supply. Separately compare normal replenishment allocations and their leftover to the same normal-producer supply. Do not add those two reporting projections together as physical dispatch. BOROA unsatisfied percentages come from requirement-band numerator/denominator, not the individual order split.

The source archive, external inputs, overrides, complete expected values, canonical hashes, resource target and eligibility must be frozen before execution. Reuse the existing owned bounded worker/PostgreSQL resources and finite daily proof pattern. Stop at the first unexpected difference and preserve the attempt. No serving change, heavy dataset, new generic harness or S3 work is authorized by this supplement.

Full positive MDM1–13/enabled-producer flows, remaining complete BPR/BTR semantics, UI/export, packaging and recovery remain outside this case's acceptance claim.

## Preserved day-ten expectation failure

The table above records the original frozen worksheet. Execution passed days1–9 and stopped onJuly10, run `3f4786ef-0756-4432-8861-cb44b2bd1b38`. The original expectation that SKU5954's normal quantities would be17/18 is incorrect: after equalisation to17 each, penetration7/24 is below the canonical one-third residual-eligibility threshold. Normal allocation is17/17 with one unit remaining. Subsequent spike/PSO rationing allocates that unit toDP010290 using its explicit location-code priority, producing combined replenishment18/17 and final parent remainder0. The RRR Norm rows continue to show17/17; their leftover column is the later post-SnP remainder0.

The preserved complete readback differs from the frozen full source expectations only in three fields for SKU5954/DP020819's Norm row: RationedQty and RationedCasePacks18→17, TOGreen_AllocQty2→1. ItsJuly10 history row carries the same difference. Thirteen other source families, including complete AllocatedOrders, match. This is a worksheet attribution, not an application correction or acceptance amendment. All854 runtime files and all frozen input/expected files remain unchanged.

Read-only diagnosis: `D:/freshvcf-build/evidence/handoff3005-s2-20261013-001/c02-supply-day10-diagnosis-v1.json`, SHA256 `c6df83fe8941e472c6eb20ac63220ad5e2b549b6944b0be52d0c881a5ade1bb2`. Six relevant SQL files match both the pinned baseline and preserved deployed copy. Any proposed amendment must separately identify the currentJuly10 row, that date's history throughJuly21, and staged conservation: normal34+remainder1=35; laterSnP1+final remainder0=1. Do not equate normal-stage remainder with the report's post-SnP remainder. The original frozen case and STOP remain preserved; the canonical tracker owns the controller's disposition.

The controller subsequently approved the exact additive amendment `f126b272f3af5493e412282a2fd8a919bc048aeafa08e9af2560f974b98c687e`. Existingday10 passed read-only re-verification without recalculation, then ownsuccessors11–21 passed. `S2_SHARED_SUPPLY_PROOF.md` records the complete bounded result and `S2_SHARED_SUPPLY_EVIDENCE.json` its evidence bindings. The original frozen copy of this case remains unchanged.
