# Pick real-route input decision

Approved by direct human controller turn `01a11abd-22e7-77d3-b038-9396e7ee2b75`.
This records the exact approved input boundary; MIGRATION.md remains the tracker.

The registered small inputs do not meet D4's nonempty canonical Pick requirement.
The ten-pair June6–7 input (SHA256
7ee7d940da3bab89ffeeddff94b4f2a7d9abace4aacdd589d698df6de85c24fc)
and synthetic scenario004 ten-pair trial (SHA256
a7e12b4a0ea39c4e0122076df8f6a6268e749dca73a51387278878511281993f)
both have NULL Weight/Volume in producer-owned SKU attributes and raw master.
The registered representative bridge has39 pairs and also NULL dimensions.
Canonical initial Pick SQL excludes both-NULL dimensions. The retained profile's
logistics item dimensions are1/1, but substituting those silently is prohibited.

## Approved bounded input decision

Create a separately named derivative of the registered scenario004 ten-pair
trial, retaining all ten SKU/location identities and the first two existing fact
dates (6–7 June2026), existing opening business state and eligible-Sleep action
policy. Change only SKU6120's external dimension metadata from NULL/NULL to
the retained profile values Weight1/Volume1 in its ten raw-master rows and matching
opening Importer/DBM SKU attribute rows. Add an explicit Pick vehicle config:
VehicleID1, name DEMO-TRUCK, weight/volume capacities100/100, and mappings for
the three existing profile parents LDC001/LDC002/LDC006. The capacity override
is explicit test configuration to exercise formed and residual trucks.

Preserve every Norm, recommendation, calculated history, stock, demand, shipment,
fact date and business rule. No generated calculated opening or copied outputs.
Pin original/derivative hashes and a path-by-path delta receipt before execution.
No source artifact is overwritten. This is an input exception requiring approval,
not an implementation fallback or a claim about the unchanged retained artifact.
All D4 invocation/resource/owner limits remain unchanged. Approval does not allow
empty-output acceptance to substitute for the required nonempty exercise.

## Preserved limitation of the first derivative

The pinned derivative (`e62ec73eaeeb2b32bdee09ef74648bdb1adf10d9b7ae6c55fc75b7706652d51c`)
executed June6 once as run `63925b64-b786-4f71-a587-0f9e681a3399`. All ten
requirements are zero, so the Pick source and both truck tables are empty.
Dimension repair alone was insufficient; the pre-execution rationale did not
establish positive upstream demand. June7 has not calculated.

Saved June7 facts versus June6 effective Norms:

| Location | June6 Norm | June7 stock + GIT | Accepted next Norm |
|---|---:|---:|---:|
| AG515802 | 144 | 159 | 96 |
| DP010290 | 186 | 196 | unchanged |
| DP020819 | 142 | 152 | unchanged |
| LDC001 | 141 | 249 | unchanged |
| LDC002 | 219 | 239 | unchanged |
| LDC006 | 123 | 137 | unchanged |
| LP001 | 254 | 269 | 170 |
| LP002 | 224 | 267 | unchanged |
| MT0513 | 244 | 271 | unchanged |
| PPI000604 | 200 | 210 | 134 |

PSO is zero throughout; added orders, force requests and other control requests
are empty. These are retained facts and genuine day1 action results, not a
calculated day2 claim. Evidence:
`D:/freshvcf-build/complete-daily-assessment/pick-real-route/real-route-blocker-v1.json`.
No new scenario, fact alteration, additional day or relaxed nonempty criterion
was authorized by this finding alone. The new explicit human decision below
resolved it; the earlier successful day and unused second invocation are preserved.

## Approved positive Pick-only synthetic fixture

Human controller turn `01a11ad1-c612-7e62-aea1-985a531c709b` approves a separate
synthetic input solely to test Pick and close, including exactly two NEW modern
dates and at most one native Pick-stage call per date. The original artifacts,
empty run, actions, failed launchers and proofs remain untouched.

The immutable fixture is
`D:/freshvcf-build/evidence/pick-closure-20261008-001/positive/input-v1.json`,
SHA256 `7e60ef1b3d73a36889b25a43995234ec5839a5bb646da5b782328189a1b2699d`.
Configuration `config-v1.json` in the same directory has SHA256
`19a7b9f9dd840389d0d948ef21ed740bad2f0f55d01c286b3678da06c1e53a45`.
`freeze-v1.json` records all106 changed scalar paths, their before/after values,
source identity, ledger validation and the authorized executable dates.

Only AG515802 future external consumption/stock changes: June6 consumes its
138 opening units plus12 received units, closing at0; June7 consumes its12
received units and again closes at0. The unused future fact scaffold repeats
receipt-funded consumption. The full21-day ledger remains necessary for the
existing three-times-maximum-RLT validator; only June6–7 execute. Historical
facts/calculated opening, Norms, identities, routes, all shipments, transit dates,
receipts/GIT and every other location's facts remain byte-equivalent as objects.
Its original AG transit is2 days, positive-half-up rounding of RLT4.

VehicleID1 remains DEMO-TRUCK and the same three parent mappings remain. Explicit
weight/volume capacities change to10/10; the supported command replaces the
profile's old singleton vehicle with this pinned configuration. Actual persisted
source readback confirms10/10. No fallback dimension, calculated requirement,
allocation, recommendation or history is seeded.

Feasibility was checked before execution: existing child Norm144, stock0, GIT24,
unit pack/dimensions and zero parent reservation leave a positive child gap;
retained parent LDC006 has61 then65 physical units. The expected semantic branches
were positive parent-limited rationing, full trucks and a nonzero residual.
Actual modern/native results confirm six full trucks/60 units on each date and
residuals1/5, with every complete row field and four downstream reports matching.
Successor/action lineage, all16 file copies and no-calculation recovery pass.
Current closure status belongs in MIGRATION.md; this document records input authority.
