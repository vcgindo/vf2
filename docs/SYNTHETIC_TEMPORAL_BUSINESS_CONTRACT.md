# Synthetic replenishment scenario — approved parameters v1

Status: complete numeric scenario and eligible-Sleep variant approved directly
in this task (`call_20bfc654f3364f6a86e035b492365e46`) on7 October2026. Parameters
are frozen; generated artifacts are validated and registered in baseline/offline-temporal-scenarios-v1.json.
`docs/MIGRATION.md` remains the only execution tracker.

## Fixed approved identity and duration

Use amended catalogue SHA256
`2ecf4e079807e00d0f809abedde1303640910ca82faeb5b8e56671b22d5de0ff`, preserving
1240 pair occurrences and every non-RLT raw-master field. RLT4/5/6/7 counts are
312/299/296/333. All pairs execute June6–26,2026 inclusive (21 days); opening is
June5. Transit is exactly `max(1,(RLT+1)//2)`, with no delay scenario.
Existing hierarchy, permissions, parent routes and transporter conventions stay.

## Approved demand facts

Seed337515802; cohort is first8 SHA256 bytes (big endian) of UTF-8
`337515802|SKUCode|WhCode`, modulo10. Slots0–6 are regular,7–8 intermittent,
9 promotion. Preserve original master iteration order; no resampling.
Base daily end-customer demand is retained initial raw-master Norm divided by
`3*amended_RLT`, rounded half-up to a whole unit, minimum1. This uses a supplied
initial master value, never either engine's subsequent Norm/recommendation.
Weekday multipliers Monday–Sunday:1.00,1.05,1.10,1.00,1.20,0.75,0.40.
Calendar-week multipliers over the three execution weeks:1.00,1.10,0.95,
where week means consecutive seven-day blocks from June6. Warm-up uses1.00.
Regular demand uses these factors; intermittent demand is zero unless
`(day_index + cohort_hash % 3) % 3 == 0`, then uses3 times base demand.
Promotion demand multiplies by1.50 on June13–15 and0.70 on June20–22,
otherwise1.00. Multiply exact decimal factors, then round half-up once.
No additional noise or implicit randomness. Zero requested demand is an explicit
quiet day. Requested, realized and unserved demand are retained separately.
Unserved end-customer demand is lost sales, not backlogged, and never negative
stock. Only realized consumption goes into canonical ingestion.

## Approved physical supply and accounting

Retained parents supply children along existing routes.810 pairs have a parent
pair inside the1240 population;430 reference an external/root source. Confirm
acyclic topology before generation; a cycle is a contract failure, not repaired.
External sources have unlimited availability but dispatch only the fixed scheduled
quantity. No supply depends on computed orders, suggestions or Norm changes.
Standing daily shipment quantity to each pair equals that pair's base demand
plus the recursively summed standing downstream requirements, rounded up to its
retained positive PackSize (explicit unit1 only where PackSize is exactly1;
missing/nonpositive PackSize is a decision failure, never silently defaulted).
Each day, apply dated inbound receipts, then satisfy local requested demand,
then dispatch downstream requests in retained child occurrence order from remaining
physical stock, rounded down to whole child PackSize lots. Unsupplied downstream requests are cancelled for that day and
recorded separately; no unledgered top-up or hidden carry-over. Parent consumption
is local realized sales plus actual downstream dispatch; child receipts equal
those exact dispatched quantities on their own declared receipt dates.
Opening physical stock at the start of warm-up is each pair's retained raw Norm;
opening GIT then is0. Generate21 warm-up dates May16–June5 with the same rules.
These are declared external stock/demand/shipment facts, not calculated DBM state.
All shipments in this finite closed scenario must arrive by June26: do not launch
shipments whose receipt would be beyond that date. Record this explicit final
run-out boundary in the preview; do not claim perpetual steady-state coverage.
Stock balance: previous stock + receipts - local sales - downstream dispatch.
GIT balance: previous GIT + inbound dispatch - receipts. Every parent outbound
has an identical child shipment; external roots and sales are named sources/sinks.

## Opening, controls and actions

Reuse compatible retained configuration, initial master Norms and empty
recommendation/action/history owners, updating RLT consistently from the approved
catalogue; do not seed new calculated recommendations or Norm changes. Replace
all physical daily history with the new reconciled warm-up. Retain existing
explicit initial disabled-Norm configuration with its provenance; it is not a
new inferred suspension. Any incompatible nonempty derived opening owner must
be surfaced before freeze, never silently regenerated.
No newly scheduled phase changes, manual forced-Norm edits, PSO, advance orders
or separate customer order feed in this base demand scenario. Their inputs are
explicitly empty; no positive branch acceptance is promised for them.
Approved action variant `own-recommendations-apply-eligible-retained-sleep-v1`:
each day APPLY all own eligible computed suggestions, except the original eight
retained Sleep-selected identities on June6: SLEEP only those actually suggested
by that engine and record any absent selection as not exercised. This differs
from the old policy's strict failure when an intended Sleep target is absent;
the direct scenario approval authorizes only this named variant. No copied
decisions between engines. Preserve the old strict policy and artifacts unchanged.

## Freeze and proof

Human approval covers the numeric demand/supply/warm-up/run-out and
action variant above as one package. Before freeze, generate an unregistered
preview of cohort counts, daily requested/served/lost totals, receipt/dispatch,
stock/GIT and covered events. Present it with any actual incompatibility together.
After approval, deterministic duplicate generation must reproduce all hashes;
validate exactly26040 business pair/date rows across the21 execution dates,
plus separately counted warm-up/source occurrences. Retain native NULLs and
field omissions; never promise positive calculated report results. The permitted
engine trial is only10 selected pairs and three days, including all RLT cohorts
where feasible and explicit parent dependencies. Full execution remains offline
and human-operated after package handoff.

## Decision preview (not calculation acceptance)

`D:/freshvcf-build/synthetic/rlt-4-7-v1/business-decision-preview-001.json`
contains the deterministic unregistered preview. Cohorts:855 regular,265
intermittent,120 promotion. The graph is acyclic;1224 pairs have PackSize1 and
16 have PackSize10. Over the21 execution dates: requested/realized local demand
262533 units, lost sales0, receipts459521, dispatch395358, unmet scheduled supply
1 unit. Opening in-transit facts explain receipts exceeding new dispatch.
First execution day closing stock167914/GIT64163; terminal stock204866/GIT0.
The zero terminal GIT is the explicitly approved finite run-out rule, not an
engine result or evidence of normal ongoing supply. No stockout branch is
promised; do not tune inputs merely to force one.
Retained opening DBMMaster/control/importer masters and two explicit initial
DisabledNorm rows are input/configuration lineage, not newly computed outputs;
existing season-status configuration is retained. No new computed opening state
is synthesized. This preview has not been supplied to either calculation engine.
