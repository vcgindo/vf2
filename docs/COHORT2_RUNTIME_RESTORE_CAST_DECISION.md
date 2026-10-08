# Cohort2 runtime restore — proposed bounded qualification

Approved by direct human reply `call_949f22a0325346ac8095e2766efd8001`,
“Approve bounded eleven-constraint runtime qualification”,8 October2026.
`docs/MIGRATION.md` remains the only status tracker.
The approved seven-constraint exception remains unchanged and does not cover
this proposal automatically.

The actual runtime backup attempt `531d0ad3-be71-436c-971b-98cd748cc20f`
restored its dump into a new owned database. All typed rows, duplicate
occurrences, ordinal values, sequence values and other captured definitions
match across 674 relations. Strict comparison fails at eleven CHECK definitions.
Seven are the already reviewed expression pairs; four belong to new operational
tables: `op_intent_disposition`, `op_attempt_status`, `op_restore_status` and
`op_operation_status`.

Read-only native verification of all eleven pairs proves identical text-array
operands, column type/collation, constraint metadata and predicate results.
The sole text difference is PostgreSQL spelling the constant-array cast on each
element after restoration rather than on the entire array.

Approved scope:

1. Pin all eleven exact schema/table/constraint names, before/after expression
   pairs and the verified column/constraint metadata from this evidence.
2. Permit these exact pairs for subsequent owned Cohort2 runtime backups only
   when each backup retains its own complete source/restored images and verifies
   the same metadata and all other logical values/definitions exactly. A changed
   pair, extra difference, changed metadata or missing evidence must fail.
3. Record each result as **qualified logical restore**, never exact schema-text
   parity. Retain strict differences and per-backup image digests. No general
   expression normalization or ignored constraints is allowed.
4. Preserve the failed attempt and its status. Any later qualification of its
   retained evidence is a separate audit receipt; it cannot turn that failed
   operational attempt into a successful whole delivery.

This proposal does not authorize new business dates, calculation replay,
accepted-run writes, serving changes or a broader schema exception.

Evidence under `D:/freshvcf-build/evidence/cohort2-20261008-001/`:

- `backup-runtime-a001/receipt.json` — failed operation identity and zero extra
  calculation calls.
- `backup-runtime-a001/531d0ad3-be71-436c-971b-98cd748cc20f/` — retained dump,
  complete compressed images and strict difference list.
- `backup-runtime-cast-proof-a001.json` — all eleven exact pairs and read-only
  native semantic/metadata proof.
- `verify-runtime-constraint-casts-a001.py` — verifier used for that proof.

Source image digest:
`8f532b2acc889cda5bec9b57680cfba749d46980af566a882b9391b4cd29768e`.
Restored image digest:
`4dcaf8921434f1e2043b86e15966eb4a1526a573a7df833ae64319e8ac0a05f7`.
