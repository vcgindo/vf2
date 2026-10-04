# Planning six destinations — bounded prepared-presentation delivery

5 October 2026. The user now authorizes implementation of this amended plan.
This is the next bounded objective, separate from Daily Data Graph. Before
starting, record the delivered modal correction and explicitly defer its unmet
72ms historical baseline gate without claiming that gate passed. Do not mix
further modal trials or fixes into Planning. Preserve its deployed behavior.
`docs/MIGRATION.md` remains the only execution-status tracker.

## Findings and sources

Planning links to GIT parent/child, Expedite parent/child, Excess review and
Order Fulfillment review. Each destination includes its existing chart/grid,
count, supported custom views, details and exports, not just its first screen.

Git main already contains Planning overview integration24c05db, Fulfillment
filter/read integration11b659c and independent Expedite navigationce27f00.
These commits are ancestors of the current branch. Main's tracker records a
seven-row synthetic child Expedite grid and user-confirmed exports, but defers
other controls, source dispositions and performance. It does not establish
six-page acceptance on the April heavy fixture. No blanket cherry-pick is needed.

Read-only native probes of the deployed3005 backend used the existing broad
fixture actor, empty filters and page1/50. They exclude browser/gateway time,
are single observations under current load, not matched performance baselines:

| Entry request | Observed result |
|---|---|
| Overview |503 planning_nonempty_transit_projection_not_published;10.384s|
| GIT parent grid |same503;10.712s|
| GIT child chart |same503;10.080s|
| Expedite parent chart |503 fixture_binding_unavailable:closing/bpr/BPRMaster;21.210s|
| Expedite child chart |same503;24.683s|
| Excess chart |200;67.795s;466536 bytes|
| Fulfillment chart |200;18.947s;432218 bytes|

The sealed fixture contains ExcessInventoryRow921651 historical records,
ExpediteRow4722, PickPostRow8063, FulfillmentSummaryRow12720 and
FulfillmentDetailRow10256. Retained InTransitData and
GoodsInTransitTransporterMaster each contain zero rows. No GoodsInTransitMaster
source table or closing/bpr/BPRMaster image appears in their current roster.

Current `planning_read.terminal_git_reports` supports only terminal-zero GIT.
It refuses positive rationed GIT, which the April fixture contains. The overview
depends on it before computing any category counts. This is read-path/source
coverage failure, not justification to make all counts zero.

Canonical retained scripts establish two narrowly derivable sources:
- `Scripts/BPR/GenerateGoodsInTransitMaster.sql`: positive-GIT rationed rows
  INNER JOIN importer standard attributes, exact native fields, then IsParent
  assignment from SKU/location-to-parent relationships. This needs no invented
  shipment records or allocation-engine replay.
- `Scripts/BPR/01. ImportData.sql`: BPRMaster copies SKUCode,WhCode,Norm,
  ParentWhCode,SKUIntroDate from importer MasterData. The retained importer
  image exists. Qualify exact corresponding-day values, conversions and bags
  against legacy before admitting a derived read-only master; never silently
  substitute a displayed BPR row or unrelated DBM master.

Transporter details instead require real InTransitData, TransporterMaster and
settings. The existing zero source is legitimate zero shipment-detail evidence,
not proof of zero aggregate GIT. Do not fabricate truck rows to populate charts.

## Six-destination reuse and gap map

| Destination | Reusable inputs | Required presentation correction/dependency |
|---|---|---|
| GIT From Parent |rationed report, standard attributes, importer dimensions|Produce the canonical typed GIT master once; prepare exact parent-view eligibility/references; scope/filter/count/page in SQL.|
| GIT To Child |same GIT master; retained transporter/transit sources|Separate location grain from shipment/transporter grain; independently serve valid charts/counts/location reads. Existing combined child SQL207/8120 is an explicit inherited defect needing an exact disposition; no automatic repair.|
| Expedite From Parent |Expedite4722, PickPost8063, dimensions, NMS, standards|Admit the verified derived BPR master for genuine parent dependencies; prepare repeated dispatch/parent eligibility and pre/post ingredients once. Preserve approved receiving-label exception only where its scope demonstrably transfers.|
| Expedite To Child |same Expedite/PickPost inputs|Remove irrelevant parent-master dependencies where actual field use proves they are unnecessary; preserve direction-specific location permissions. OpenExpediteRequests admission is June17-only and does not transfer to April7. Qualify the real source before any request/transit-dependent grid.|
| Excess Review |existing current-day ExcessInventoryRow and dimensions|Prepare/reuse exact current-day presentation occurrences for grid/count; chart has different description-before-attribute aggregation grain. Serve SQL aggregates/page directly, without rebuilding all Python bags. Guided historical Excess relation is partial ingredient reuse, not a drop-in full grid.|
| Order Fulfillment Review |existing12720 summary and10256 order detail records|Keep separate summary/detail grains and order identities. Prepare only repeated dimension membership; scoped SQL chart aggregation, grid paging and selected-key details. Never infer order records from aggregate BPR rows.|

BPR prepared candidates are six-owner LEFT join occurrences with BPR-specific
fields. Guided Availability uses BTR attributes/exact matching and historical
colour facts. Guided Excess carries compact importer-based history references
and amount. None is a universal Planning table: required fields, INNER/LEFT
joins, duplicate expansion and aggregation timing differ. Reuse underlying
typed producers, source-resolution/seal patterns and qualified dimensions;
reuse prepared rows only after proving the exact consumer grain and fields.

## Authorized bounded execution

1. **Qualify all six contracts together.** Reuse main's existing components,
   configs, proof and exceptions. Create one fixed consumer matrix including
   landing counts, default destination, existing grid/chart toggles, subtabs,
   filtered counts, pagination, selected details and supported exports. Resolve
   GIT-master and BPR-master preparation from canonical retained sources as
   above; bind source/day/run/digest. Identify actual OpenExpediteRequests source
   and disposition of inherited invalid queries. No restoring databases or
   adding facts. This is a finite qualification step, not a general inventory.
   Freeze this matrix once, classify each consumer as available, source-derived,
   or exact inherited dependency, then implement. Do not repeatedly inventory
   main or expand to every route in the application.
2. **Implement one coherent preparation/read batch.** Prepare stable source
   matching and display ingredients once for the existing April7 data, using
   existing typed projections plus only missing narrow source-specific
   projections. Keep permissions/filter/paging/request-dependent aggregation
   live. Preserve NULLs, multiplicity, canonical comparison expressions, order,
   distinct count grains and exact numeric/wire types. No universal giant table,
   global per-user totals or filter-combination snapshots.
3. **Connect the existing Planning UI as one batch.** Current branch already
   settles independent count/grid requests together. Preserve that work and
   avoid duplicate source/date/config fetches. Remove only proven redundant
   conversion/copying after API values are typed. Keep category dependencies
   separate: a GIT gap must not block available Excess/Fulfillment reads or be
   represented as an empty count. Preserve count wire contract; any per-family
   unavailable presentation needs an explicit narrow contract decision if full
   source qualification cannot resolve the shared overview.
4. **Inspect module by module and close end to end.** Focused complete-value
   broad/restricted and affected duplicate/NULL/order proofs, needed migration
   checks/build, one bounded matched heavy-data click-to-usable comparison per
   destination, then only attributable fixes. Both default charts and populated
   grid/detail use matter. Verify actual supported exports and no redundant
   row-modal regression using completed modal evidence where reusable. Deploy
   3005; document preparation cost, remaining dependencies, rollback and commit/
   push. A blocked source/legacy-invalid consumer is not six-page completion.

No new daily pipeline/scheduler, engine replay/rule changes, synthetic source
substitution, DB copies/reset, integer keys, framework/cache/service, grid
replacement, action/request workflow implementation, resource increase or3004
cutover. Simulate preparation once from existing data; later daily publication,
refresh/retry/retention integration remains separate programme work.

## Prepared-read acceptance: the BTR method

Preparation is one explicit operation on the existing retained April7 dataset,
simulating the final output of the current daily cadence. It must produce typed,
run/source-bound rows or references containing stable source matching, required
display values, filter-owner references, eligibility and exact occurrence order.
Use the existing preparation/receipt patterns; no generic preparation framework.
Do not mutate the sealed source roster to pretend a derived source was imported.
Bind new derived presentation outputs separately to their verified source inputs.

Before writing a derived table, specify its grain, actual consumers, missing
fields and which repeated work it removes. Existing correctly prepared rows
with the right grain need only reader correction; efficient paths may remain.
Do not require six new tables, but do not substitute request-time Python or SQL
reconstruction for required preparation. For grids apply scope/filter/order/page
before expensive response expansion, preserving native key-bag paging where
required. Charts must aggregate the correct scoped source grain in SQL, not
transfer the entire population to Python. Serialize once at the API boundary.
Fulfillment selected details must read real order identities and preserve their
separate grain. A metadata digest or HTTP200 is not prepared-read acceptance.

Request-time work is limited to live permission eligibility, supported filters,
scope-dependent aggregates, paging, current external overlays and selected
details. Do not freeze command/request state merely to achieve performance.
Endpoint-specific canonical filter behavior, including ignored filters, remains
unchanged unless the human authorizes an exact exception.

## Fixed verification and delivery boundary

For each available consumer retain one complete legacy/current reference and
compare prepared outputs, including all values/types/NULLs/duplicates/order.
Use one broad and one relevant restricted case per family, one meaningful
filter/page check and selected Fulfillment details. Reuse existing semantic
tests; add only absent affected join/NULL/multiplicity cases. Required migrations,
readback and builds are not permission for a new test programme.

On existing databases with the existing bounded matched-resource mechanism,
capture one before and one final legacy/modern default journey for each of the
six destinations, plus one final grid toggle/detail inspection per destination
where supported. Reuse legacy reference when unchanged and valid. Record usable
screen completion, request timings and actual row counts; backend gains alone
cannot close a destination. Default configured page size is retained, not tuned
to make the result favorable. At most one additional diagnostic/recheck for an
identified failed/noisy consumer after an attributable fix; no favorable
resampling, percentiles, repeated passing proofs or enlarged matrix. Restore
limits even on failure. Blocked/legacy-invalid consumers receive an exact
dependency disposition, not invented performance success.

Final delivery is on3005, committed/pushed, with a six-destination matrix in
MIGRATION.md distinguishing prepared/read-wired, functionally proved, UI
performance proved and exact unresolved dependencies. Six-page completion
requires all authorized exits or precise human-approved exceptions. Partial
delivery must be labelled partial. Publish usable available families while
retaining genuine blockers; do not let an independent inherited defect prevent
their implementation. Stop after this bounded pass and report any unmet exit.

## Source and inherited-defect decision boundary

The source-derived presentation build can be bounded to retained inputs. The
remaining potential approval boundary is handling legacy-invalid combined GIT
and Expedite/unpaged/custom contracts and April request-history admission.
Keep their valid independent consumers available; obtain a precise disposition
for an actual unresolved contract rather than silently repairing it or declaring
the whole destination complete. This implementation authorization permits
canonical source-derived GIT/BPR master presentation preparation and existing
reader/frontend wiring. It does not authorize correcting legacy-invalid SQL,
inventing an empty April request history or widening a previous exception.
Consult the canonical retained source/available database once for each missing
input; prefer bounded read-only source acquisition if exact data exists, without
database copies/restores. If no source is proved, retain the dependency and
continue independent permitted work. Request a precise disposition only when
needed for that consumer, with actual code/evidence ready for review.
