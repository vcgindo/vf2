# S2 native audit and final correction proof

The authoritative status remains `F:/freshvcf/docs/handoff-3005/TRACKER.md`.
This document records the bounded implementation and component evidence; it
does not close G2 or authorize Step 3.

## Changes

- Project working stock openings and policies onto current active master pairs,
  preserving retained values, duplicates and ordering. Removed pairs no longer
  cause a missing-key failure; new pairs still require valid supplied inputs.
- Publish master3 approval audit effects at each canonical 999-row chunk,
  preserving business publication, settings lookup, rejected audit, approved
  audit and final task-completion order.
- Capture the eight native upload audit families in typed PostgreSQL rows with
  run/source/initialization ownership, frozen retry origin and own predecessor.
  Publish retention and the audit seal inside the daily commit transaction.
  The existing reader admits these rows only after their complete identity and
  value checks. Explicit policy supplies the retention horizon, timezone and
  optional client folder; there is no empty fallback for missing captures.

No calculation formula, legacy SQL, global serializer, serving stack, frozen
external fact or accepted predecessor was changed by this batch.

## Additive migrations

| Migration | Dependency | Fresh-database purpose |
| --- | --- | --- |
| 0136_native_upload_audit | 0135_closing_projection_parent_guard | Native audit header and eight typed occurrence models; exact producer field types and nullability |
| 0137_native_audit_guards | 0136_native_upload_audit | Custom PostgreSQL ownership, frozen identity, consumption, retention, retry and immutability guards; narrowly permits captured expired-row deletion while preserving force OldNorm publication |

Both migrations were actually applied to the uniquely owned audit component
database. Django check, migration drift check and empty migration plan passed.
Applied migration files remain immutable. Earlier location migrations0132–0135
are documented in `S2_C05_LOCATION_COMPONENT_PROOF.md`.

## Component evidence

Evidence root: `D:/freshvcf-build/evidence/handoff3005-s2-20261013-001`.

- `s2-audit-component-proof-v3.json`: all11 real PostgreSQL tests pass, covering
  999/1000-row chunk effects and failure, eight typed populations, NULLs and
  duplicates, local cutoff, denied mutation, late rollback and frozen retry.
- `s2-native-audit-physical-schema.json`: all eight occurrence schemas exactly
  match their producer field types, nullability and collation. Header metadata
  is typed; audit payloads are not JSON blobs.
- The47 focused checks passed46 cases with one existing S3 skip.
- `s2-audit-durable-component-v5/failure2.json`: late failure after publication
  and audit sealing restores all165 discovered run-owned ORM populations and
  complete source-owned rows to their pre-finish values.
- `supplemental-raw-rollback-v1.json`: read-only catalogue of386 raw storage
  tables and497 direct run-like/FK columns;99 input images reconstruct exactly,
  with only2,025 original input rows remaining and no output/export rows.
  This supplements ORM ownership; arbitrary unlinked tables are not claimed.
- `s2-audit-qualified-component-v1/retry-readonly.json`: committed retry
  `e9a26d2e-36a8-4de0-a7c5-9dc8f16fe510` has its own parent and frozen failed
  origin, intact roots, complete audit/live/reader values and preserved failed
  attempt. Qualification is read-only; no successful day was replayed.
- `s2-audit-qualified-component-v1/consumer-acl.json`: exact nine-table
  nonowner readback and38 write/role/namespace denials pass.
- `s2-final-affected-reader-contracts-v2.log`: all32 affected existing
  native-binding, daily-feed and upload/export contract tests pass.

The stopped retry proof compared native datetime ISO text with a worksheet
that forced millisecond spelling. Controller approved a narrow expected-side
adapter for only the eight typed audit collections. Original worksheets and
STOP remain preserved; CSV byte expectations still require milliseconds.
No runtime serializer or actual value changed. The unit binding fixture was
also updated to construct the current seal; its real integration-identity and
single-frame/all-owner assertions remain active.

## Final integration boundary

The single final freeze contains879 runtime files in
`s2-final-source-20261014-001/runtime-source.json`, SHA256
`3fe9588e4bf3adbc487211dcdb4c5249e7c439eb903847f1ec0083537bba7cdb`.
Archive members match the source map. The human's finite closure instruction
supersedes the earlier21-day integration queues. Fresh C05 covers all38 requests
across13 families by day6 and its own successor through day7, with609 complete
declared comparisons. The shared enabled calculation/report/export case is
limited to July1–7. Its two BTR endpoints use independently frozen expectations;
no calculated history is seeded and no additional expiry campaign is required.
Consult the sole tracker and S2_CLOSURE_EVIDENCE.json for terminal qualification.

Retained C01/C02/C03/C04 evidence transfers only across unchanged relevant
contracts. The original `s2-final-diff-reuse-v1.json` is a preserved preparation
map; S2_CLOSURE_EVIDENCE.json reconciles its pending items with final evidence.
New July2 audit events do not reach expiry within July1–7; exact cutoff and own
cumulative expiry use the listed PostgreSQL components. A fully populated new
90-day BTR history is not claimed. This component proof is
not a heavy-data, user-interface, deployability or production-readiness claim.
