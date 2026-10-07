# Daily execution ownership and evidence map

This is the contract map for the approved integrated refinement. Status and
acceptance remain exclusively in `MIGRATION.md`. Calculation order follows
`mta/temporal/chain.py`; the rows below describe ownership, not a replacement DAG.

| Input / operation | Consumer and final writer | Required persistence | Timing category |
|---|---|---|---|
| Captured MDM queues, configuration, tasks/history and pair exclusions | `runtime/temporal.py`, `mdm/daily_input.py`; `finalize_consumption` | Typed frozen input images and MDM occurrence/archive rows; completion consumes in the output transaction | Input capture / mandatory persistence |
| Persisted predecessor and ordered Apply/Sleep commands | `read_outputs`, `command_state`; current `execute_day` | Run-owned closing images, command receipts and changed typed action images | Input verification / loading |
| Raw master/daily/supplier inputs; validation and reconciliation; SOB/MOQ refresh | `r1_master_input`, `r1_daily_input`, `r1_supplier_input`, `entry_inputs` | Typed daily input; final importer/supplier closing state, supplier opening sources | Import/loading |
| Controls, accepted/forced Norms, phase-in/out and seasonality | `control_carry`, `timeline_controls`; importer and DBM ingestion | Closing control/importer/DBM histories and settings; required control reports | Shared controls |
| Spike orders, due dates and closing | `order_closing`; closing orders and downstream Pick input | Typed closing order histories, final standard attributes | Order calculation |
| Requirements, reservations, sourcing, rationing, Pick and logistics; RRR | `calculate_current_day` before late BPR; `CalculationOutputs` feeds projection writers | Required Pick/Fulfillment/Expedite/Pick-post typed projections, closing delivery state and offline RRR source | Calculation / mandatory sources |
| Consumption, penetration, colour, BlueRequirement, UpdateBPR | `bpr_construction`; late BPR feeds DBM and BTR | Final BPR and rationed report typed images; colour sequence source | BPR calculation / mandatory sources |
| DBM ingestion, suspension, cooling, suggestions and Norms | DBM selected/connected chains and rules | Final DBM images, histories and action eligibility | DBM calculation |
| Norm0/1/2 reports, details/advisory, norm-change export/history | DBM report stages; copied before a later stage overwrites them | Typed report images and ordered typed export cells/row lengths | DBM reports / persistence |
| BTR trends, ageing, insights and standard attributes | `btr_finalization`, after DBM; final closing writer | Typed BTR and final standard-attribute images | BTR calculation |
| ClosingState, consumer context and Lineage | `save_daily` within `finish_run` | Ordered typed images, bounded manifest/root; exact reconstruction | Mandatory persistence/readback |
| Supplier opening, colour, request/remark capture and transit | `daily_sources.write_sources`; `offline_rrr.write` | Run-owned typed rows plus bounded source receipts; unavailable remains distinct from empty | Mandatory sources |
| Terminal report preparation | `daily_publication.prepare` after accepted daily completion | Separate prepared rows/seals; never predecessor input | Outside daily calculation timing |

## Evidence policy

Validation retains the complete original comparison roster: MasterValidation,
Supplier/Daily/Control/Order stages, CalculationInput/Outputs/Run, BPR/DBM/BTR
stages/finals, Reports, MajorBoundaries, Lineage, PublicationContext and ClosingState.
It writes compressed evidence outside PostgreSQL and verifies its independent
validation digest. Required operational rows are persisted in both modes.

Production consumes intermediate generator stages without diagnostic snapshots.
It keeps final state, required report slices before overwrite, CalculationOutputs
until all projection writers finish, and an eight-boundary completion roster.
It does not build intermediate checkpoint tables or normalize the whole output
graph. Typed image checksums, input identity, ordered actions, source receipts and
atomic completion remain mandatory. The operational output root binds the input,
manifest, required roster and boundary roster; it is distinct from validation's
whole-evidence checksum. Version-one accepted receipts remain readable.

## Working-set ownership and limits

The current engine still owns full calculation state and dependency groups;
cross-pair allocation is not arbitrarily partitioned. This refinement does not
certify million-pair execution or eliminate that baseline working set.
Diagnostic snapshots no longer multiply it in production. Required DBM report
slices are copied only until their typed persistence completes.

DBM candidate lookups use disposable SQLite indexes containing business codes
and source ordinals, with 2 MiB cache per indexed table and batches of 256 matches.
Original rows remain with their calculation owner. Duplicate occurrences, NULL
keys and original order survive lookup. The index closes on success or failure;
it is neither operational truth nor a recovery store. No oversized group is
silently truncated: matching rows stream in bounded batches.

Relational inserts batch 500 rows. Input adapters borrow source populations;
typed image validation streams canonical checksums and fetches 500 rows at a
time. Export manifests hold counts/checksums, with row lengths stored relationally.
Reader APIs that explicitly request an entire state still materialize that state;
selective MDM readers reconstruct only the requested input component. PostgreSQL
driver buffering and full engine state remain limitations to measure and disclose.
