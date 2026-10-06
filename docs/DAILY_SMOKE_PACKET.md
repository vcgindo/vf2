# Daily ten-pair smoke preparation

This preparation selects ten retained `(SKUCode, WhCode)` identities from the
registered 1,240-pair temporal artifact. It does not execute a daily run and is
not a parity, publication, API, or UI acceptance result.

Run the preparation once from the repository root:

```powershell
D:/freshvcf-build/venv/Scripts/python.exe tools/prepare_daily_smoke.py
```

The tool verifies the unchanged source SHA and baseline registration, validates
the complete registered external-fact ledger, qualifies the selected pairs and
their parent closure, and writes the manifest with exclusive-create semantics to
`D:/freshvcf-build/evidence/daily-publication-3006-20261006-001/smoke-preparation-001.json`.
It never writes a derivative input artifact or touches a database or service.

## Qualified selection

SKU `6120` has exactly ten source-ordered raw-master pairs. Seven parent edges
close inside the ten pairs. The other three edges point from `LDC001`, `LDC002`
and `LDC006` to the same external parent location, `PL001`; that reference must
remain explicit. The selected pairs have no retained fixed command or day-one /
successor phase-request intersection. Their maximum RLT is four days, while the
registered fact ledger retains the full twelve-day `3 × max RLT` horizon.

The fixed boundaries are opening `2026-06-05`, day one `2026-06-06`, and
successor `2026-06-07`. The packet records exact row counts and canonical hashes
for selected raw master, shipments, reconciliation, both opening daily-fact
populations, and all retained daily raw facts. These are source qualifications,
not calculated outputs.

## Registered derivative

The explicit table-by-table reducer `tools/reduce_daily_smoke.py` has produced
`ten-pair-input-v1.json` in the same evidence directory, SHA256
`7ee7d940da3bab89ffeeddff94b4f2a7d9abace4aacdd589d698df6de85c24fc`.
It and `ten-pair-reduction-v1.json` are registered in `baseline/manifest.json`.
The unchanged external-ledger validator passes all twelve days: ten identities,
280 reconciliation rows and263 shipments. Full-estate identity assertions are
replaced by explicit derivative provenance. Values, row order and duplicate
occurrences are filtered without regeneration; settings, dependency directories
and the external parent are retained. Unknown populations or mixed dependencies
fail. No calculation or parity admission was executed.

## Why execution remains blocked

The derivative still lacks pinned daily MDM source/capture, pair-exclusion and
authenticated account/grant bindings. The existing `run_temporal` runner cannot
pass `mdm_source` into `execute_day`. Report readiness also requires the declared
shipment supplement and qualified nonempty consumers. The original preparation
receipt remains preserved with its then-current `BLOCKED` status; it is not an
execution command or acceptance receipt.

## Genuine admission path

An executable smoke now requires the remaining pinned MDM source revisions. An
MDM-aware root runner must execute day one with those revisions and execute the
successor only from day one's persisted close. The same registered derivative
then needs an independent canonical legacy replay and complete comparison before
`record_parity` can admit it. Prepared publication, explicit selection and the
authenticated UI check follow that admission. Until those identities exist,
there is intentionally no smoke execution command.
