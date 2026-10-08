# Cohort2 PostgreSQL restore cast qualification

Approved by direct human reply `call_c3c9dbe4c033483dae660166286f5429`,
“Approve this seven-constraint qualification”,8 October2026.
This document records one bounded acceptance exception;
`docs/MIGRATION.md` remains the status tracker.

The retained backup of owned `fresh_complete` was restored into the new owned
`fresh_cohort2_restore_accepted_20261008_001`. Complete typed rows and sequence
values match across 613 relations. Strict schema comparison failed at exactly
seven CHECK definitions. The source spells a constant varchar array followed by
an array-level text cast; PostgreSQL restores the same expression with text
casts on its individual constant elements.

Read-only verification confirmed, for all seven exact expression pairs:

- Identical checked column, left-hand text cast and `= ANY` operator.
- Identical evaluated constant arrays, including element order, both of type
  `text[]`. Consequently the predicate receives identical operands for every
  value of the checked column, including NULL.
- Identical column type/collation and constraint validation, inheritance,
  deferrability and initial-deferment metadata.
- Matching native predicate results for NULL, empty text, valid members,
  nonmembers, case variants and trailing-space variants.

Proposed acceptance: qualify only these seven named relation/constraint pairs
and their exact before/after definitions, bound to the retained source/restored
logical images. Preserve every strict failure and mark the result **qualified
logical restore**, never exact schema-text parity. All other schema definitions,
typed values, NULLs, duplicates, ordinals, sequences and existing checks remain
exact. No general expression normalization, ignored constraints, source mutation
or changed report/calculation acceptance is authorized by this proposal.

The implementation must reject any additional difference or different expression
pair. A future backup requires its own exact evidence binding; this decision does
not automatically accept newly encountered schema differences.

Evidence under `D:/freshvcf-build/evidence/cohort2-20261008-001/`:

- `pg-backup-accepted-a001/strict-restore-failure-receipt.json`
- `pg-backup-accepted-a001/strict-restore-differences.json`
- `pg-constraint-cast-proof-a001.json`
- `verify-constraint-casts.py` (read-only verifier)

This does not close SQL full/differential backup proof, operational orchestration,
or Cohort2. No calculation, serving change or new database is requested.
