# Proposed daily shipment metadata supplement

This is a proposed external-input contract, not an implemented or accepted
source. It does not authorize generation. Quantities, dispatch/receipt dates,
catalogue identities and calculations remain exactly as registered.

Parent artifact: `F:/vflow_integrated/.local-stage7/block3-sizeable/v1/sizeable-input.json`,
SHA256 `0f3084b7a6fb60b84edbd7c4dc01fef3c4b40f1a7c389ec82f88b9ad22519546`.
Its32,909 shipment rows contain only shipment_id, SKUCode, WhCode, quantity,
dispatch_date, receipt_date and git_duration_days. The pinned generator
`parity/block3_sizeable.py` at commit `66a77735d3f3f9a9becf4c87a08ae7827900cf84`
does not assign the remaining raw shipment fields. Absent keys cannot silently
be treated as NULL or renamed into different business meanings.

## Proposed explicit synthetic conventions

For each business date, retain every original ledger occurrence satisfying
`dispatch_date <= business_date < receipt_date`, in original ledger order.
Populate the canonical raw input as follows:

| Raw field | Explicit convention |
|---|---|
| SKUCode | Exact shipment SKUCode |
| ToLocationCode | Exact shipment WhCode |
| InTransitQty | Exact shipment quantity |
| FromLocationCode | The matching retained master ParentWhCode, explicitly designated as this synthetic shipment's origin |
| CreationDate | dispatch_date, explicitly declaring creation and dispatch on the same date |
| GateOutDate | dispatch_date, explicitly declaring gate-out on that date |
| OrderNo | shipment_id, declaring one synthetic order per retained shipment |
| LRCode | shipment_id, declaring one synthetic consignment per retained shipment |
| TransporterCode | One of the four existing retained transporter codes, selected by the first eight SHA256 bytes of UTF-8 shipment_id interpreted as an unsigned big-endian integer modulo four; preserve the directory's retained order |
| CurrentLocationCode | Explicit NULL: current location is not simulated |
| Remark | Explicit NULL: no transport comment is generated |
| ReportDate | The business date of this input slice |

Every convention beyond the seven-field ledger is a **new declared synthetic
fact**, not a discovered legacy value. It requires explicit approval before an
immutable supplement is generated or registered. No catalogue is regenerated.

The four-row transporter directory is the retained
`case.opening.consumer_context.GoodsInTransitTransporterMaster` population;
despite that historical path name it has directory columns, not shipment rows.
SLT/Price come from the same day's actually produced standard attributes,
including their NULL values. The daily initializer clears opening attributes;
this supplement does not restore those opening values or add a site-import
feed. SuperDelayFactor comes from the current produced configuration (the
retained configuration is `1.5`). These are inputs to canonical raw import and
transport reporting; aggregate GIT is never used to manufacture shipments.

## Required proof before use

The supplement must pin the original artifact, exact ordered catalogue/
directory/standard inputs, convention version, generator source and output
hashes. Reconcile every daily raw quantity to the original ledger and retain
the original shipment IDs. Run the unchanged canonical raw import and
transporter-report SQL against these identical declared inputs on the owned
legacy/modern trials, comparing complete typed rows including NULLs and
duplicates. Preparation and readiness must still deny missing or changed
supplements and unqualified nonempty consumers.

The terminal-only empty supplement remains terminal-only. This proposal cannot
extend that exception, fill missing BOR formulas, authorize new business rules,
or independently release the smoke/90-day execution gates.
