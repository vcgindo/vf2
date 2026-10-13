# S2 constrained shared-supply proof

The four-SKU, two-child case completed all21 own-successor days, July1–21, with315 complete source-family comparisons and336 conserved external stock-ledger rows. Acceptance includes an explicit, controller-approved correction to the original day-ten expectation. No runtime code, input facts, prior run, source seal or serving configuration changed during this case.

This proves the declared constrained allocation and persistence boundary. The sole programme status remains `F:/freshvcf/docs/handoff-3005/TRACKER.md`; it does not close all of S2 or release S3.

## Exact boundary and identities

- Source checkpoint: `7890415c24c493fe4b21ccd471cd37d3da1d2cd0`; all854 runtime files remain unchanged.
- Isolated database: `handoff3005_s2_c02_supply_20261014_001`, actual fresh migrations through0127. Existing bounded worker/PostgreSQL containers and original shared test principals were reused. This does not prove tenant credential isolation.
- Initialization: `87e77da9-6ab7-427b-9d4c-6120a12ef156`; full typed input reconstruction and thirteen native family bindings passed.
- Input SHA256: `f3c7b39ec3c3a73df70bdb5fe5efc32a51b81dfd5a6919cf8b154cb3dba5643d`.
- Frozen manifest SHA256: `89712791081b4c3fe1b9789976395268fb235cd52ca3da282b904f3ddb7eb220`.
- Terminal July21 run: `2317480d-7b9c-4901-bf15-1084cab1735a`; complete readback SHA256 `130ef2b4770e59e47a53a2b40768803b546e5e06ada5f09a66f58e13b9272e05`.

The retained200-SKU/20-location metadata is unchanged; only four SKUs and twelve pairs are active. No heavy facts or calculated outputs were imported. One new order per day establishes canonical order keys without relying on unordered multirow identity insertion. The21-day horizon is three times maximum retained RLT7. All physical stock stays constant at4072; proposals are not treated as physical shipments.

## What the case demonstrates

| Check | Result |
|---|---|
| Future orders and ordinary demand | Days1–9 retain exact serial keys, no premature spike allocation, and ordinary quantity2 below the threshold. |
| Scarce order supply, July10 | Parent stocks9/10/35/18 produce child allocations9/0,0/10,18/17,0/18 for SKUs337/5708/5954/6249 respectively. Complete order rows, quantities, dates, colors and keys match. |
| Normal allocation, July10 | Child quantities4/5,5/5,17/17,9/9. Eligible residual stock follows the canonical priority. SKU5954's remaining unit is ineligible for normal residual allocation and enters the subsequent SnP stage. |
| Subsequent SnP allocation | SKU5954 receives1/0 by explicit location-code priority. Normal34+remaining1=35; SnP1+final remaining0=1; combined replenishment18+17=35. The separate order projection is not added to these totals. |
| External withdrawal, July11 | Spikes leave the external feed, ordinary order remains, current order allocations clear and normal quantities return to baseline. No native shipment/fulfillment transition is inferred. |
| Full source persistence | All fields and duplicate multiplicity in fifteen source families match on every accepted day, including complete cumulative BOR/RRR histories. SQL populations without ORDER BY use complete typed row multisets; persisted ordinals remain in full readbacks. |
| Own lineage and facts | Every successor references its own persisted predecessor and output digest; complete captured inputs, active Norms, supplier openings/closings and BPR/DBM current facts reconcile with the frozen facts. |

## Original failure and additive amendment

Day10 run `3f4786ef-0756-4432-8861-cb44b2bd1b38` committed successfully, but the first comparison failed. The original worksheet expected normal quantities17/18 for SKU5954. It omitted the residual eligibility predicate: after17 each, penetration7/24 is below one third. Canonical normal allocation is17/17, with one remaining unit allocated later by SnP. The report's leftover field is the post-SnP value0, while its Norm quantity remains17.

Independent attribution confirmed this expectation defect and explicitly withdrew the earlier static17/18 conclusion. Six relevant SQL files match the pinned baseline and preserved deployed copy. The original frozen expectations, stopped proof and complete readback remain unchanged.

Controller-approved amendment `f126b272f3af5493e412282a2fd8a919bc048aeafa08e9af2560f974b98c687e` changes only SKU5954/DP020819, AllocationFor=Norm, July10: RationedQty18→17, RationedCasePacks18→17, TOGreen_AllocQty2→1. It also changes that same July10 history occurrence in cumulative histories throughJuly21. Exact key/date/field and occurrence assertions prevent broader changes. Conservation distinguishes the normal-stage remainder1 from final post-SnP remainder0.

The existing day10 was reverified with PostgreSQL `default_transaction_read_only=on`, all fifteen full source comparisons, own lineage, report intermediates and staged conservation. Its complete input/output readback exactly matched the original preserved content; no calculation was replayed. Only then did unchanged own successors11–21 run. No further divergence occurred.

## Evidence and limits

`S2_SHARED_SUPPLY_EVIDENCE.json` binds147 external files under `D:/freshvcf-build/evidence/handoff3005-s2-20261013-001`. The amended execution directory's `case-result.json` identifies all21 accepted readbacks and chain links, while the original directory retains the failure. Fresh Django/schema checks, real migrations, immutable registration, source/input freezes, controller amendment, independent attribution, complete rows and before/after resource protection are included.

Final protection checks confirm all six serving identities, start times, environment hashes, mounts, ports and limits unchanged. Both owned containers retain their identities/resources, no host port mapping and no OOM flag. No serving stack was restarted or repopulated.

This case does not prove a native allocation-to-shipment fulfillment workflow, an undefined exact full-key tie winner, all BPR/BTR report semantics, positive MDM1–13 or enabled-producer workflows, UI/export acceptance, production capacity, packaging or recovery. Those remain outside this proof's acceptance boundary. No previous C02 logistics or Apply/Sleep campaign was repeated.
