# Approved isolated legacy benchmark variant

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

`GenerateLogisticPickList.vehicle_options.patch` records the19October2026 human-approved legacy-only correction. It is not loaded by the modern application and does not alter the canonical deployed source or its manifest pin. Each configured vehicle option retains its own cumulative/boundary/residual/load-type identity; no raw quantity, dimension, capacity or numeric precision is changed. The isolated Intermediate `PickListOfTruckFull` also requires a trailing `VehicleName nvarchar(100)` column.

Canonical SQL SHA256: b5044bcb979e57c270d944fdcf3a7998bee33484a384dae89aaaf414c7d05dfb. Approved proposed SQL SHA256 is recorded in the immutable decision and human receipt under `D:/freshvcf-build/evidence/large-data-day1-benchmark-20261019/pick-correction-proposal/` and `corrected-legacy-attempt-01/`. The external SQLCMD bridge accepts the exact approved variant only for this producer, while still verifying the unchanged canonical source pin. Every call identifies the corrected baseline. No general oracle-edit bypass is provided.

Use the existing benchmark report and sole handoff tracker for results/authority. The original failed day and corrected attempt are separate. This variant creates a corrected-legacy baseline; it is not unchanged-legacy parity or authority to change/run the modern engine.
