# Daily ingestion and report preparation

The live delivery status and acceptance evidence are recorded only in
`F:/freshvcf/docs/handoff-3005/TRACKER.md`. This document describes the code;
component proofs do not qualify a native installation or a V3 run.

## Daily ownership

CSV parsing owns cell types, NULL handling, widths and original archive bytes.
A private parser handoff lets native preparation reuse that work. Supplied JSON
continues through its normal intake decoder. The joint input boundary includes
the existing master/supplier/daily rejection producers, controls, order input
reconciliation and dependency-closed R1 preparation. Their rejection and business
calculation rules are unchanged.

The resulting private accepted-input handoff stays with the calculation and
atomic publication. Production readers decode the accepted typed populations
without another full content audit. Independent diagnostic readers retain their
exhaustive checks. Track A preparation moves into one calculation and releases
its reference, avoiding an extra retained copy.

Every business date uses the same producer. The most recent unique successful
same-source predecessor before the requested date supplies its persisted closing
state; calendar gaps do not generate predecessor transactions. With no accepted
predecessor, the initialized starting facts and current supplied facts remain the
actual owners. No missing histories or calculated openings are invented.

Full and the BPR/DBM cuts share their producers. Typed phase snapshots carry the
accepted-input handoff and preparation result through continuation. Finalization
does not replay predecessor completion or accepted earlier phases.

## Current tables and reports

Large admitted current-table writes stage expected typed rows once. A narrow
metadata query identifies changed columns; writes retain primary keys, duplicate
ordinals, the original 500-row thresholds, changed-field groups and statement
ordering. Existing revision producers remain installed. The owner-only SQL
context avoids repeated pure current-write guard queries inside that command;
unadmitted and restricted-role paths retain the original guards.

Reports prepare and seal each distinct generation once. Normal publication and
selection use its prepared identities; full row audits remain explicit tools.
BTR v1 count/export grain and v2 display grain remain distinct. V2 scope
dimensions are stored once per source ordinal instead of rediscovered from the
wide grid for every page. DBM joins index each source bag once per assembly while
retaining duplicate combinations and their order. The existing frontend cancels
obsolete BTR requests and retains its existing grid/filter/export contracts.

## Migration register

| Migration | Purpose | Transition |
| --- | --- | --- |
| 0244 | Owner-only accepted current-write transaction context | Reversible RunPython; verifies and preserves the exact predecessor function bodies, owners, ACLs, OIDs and triggers |
| 0245 | Typed BTR scope dimensions | Generated model migration plus reversible SQL guards; backfills existing READY v2 dimensions once before attaching immutability guards |

Applied migration identities are not rewritten or faked. Fresh PostgreSQL
application, Django checks, model-drift checks and migration planning are part of
qualification. Operator commands remain `vf.ps1 csv-init`, `csv-day` and
`csv-scope`; installation paths and resources belong to the isolated instance.
