# Cohort2 BOR history sequence decision

Approved on 8 October 2026 through the four-item consolidated closure decision.
Status remains in `docs/MIGRATION.md`.

The positive native fixture in
`D:/freshvcf-build/evidence/cohort2-20261008-001/bor-native-a002.json`
matches BORWithOrderAllocation, all exported header/data cells, the RRR history
population and the execution flag exactly. BOR_OrderAllocationHistory matches
all 27 typed fields and both complete rows, but fails strict sequence comparison.
Native reads June 6 then March 9; modern retains March 9 then appends June 6.
All touched tables and Intermediate populations were restored by rollback.

Canonical CollectBOR_OrderAllocationHistory.sql deletes today's rows and rows
at or beyond the 90-day cutoff, then inserts today's BOR population without an
ORDER BY. Its pinned SHA256 is
`4a58bb30a2b94c48693297852cafe0f48748f62f76c09178c0c2996e83298340`.
The native verification SELECT also has no ORDER BY. Native physical row order
is therefore not an expressed history ordering contract.

Proposed bounded qualification: compare only this BOR history table as complete
typed row bags. Keep all fields, NULLs, duplicates, retention dates and counts
exact. Preserve strict sequence failures, modern stored ordinals and exact
reconstruction. Do not add a sort or alter the history algorithm. No transfer to
BOR current collection, report/export order, RRR history, APIs, grids, allocation
calculations or the existing four Pick files is proposed.

The preserved strict sequence failures remain failures under exact ordering.
Only complete typed row-bag acceptance is qualified by this decision; it does
not independently establish Cohort2 completion.
