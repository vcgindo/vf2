# Cohort2 operational outputs and recoverability

This handoff covers the isolated generic O1–O9 side-effect path. Final acceptance
status and run identities are recorded in `docs/MIGRATION.md`; that is the only
status tracker. This document defines coverage, evidence and operator commands.

The two-date acceptance passes with exactly two calculations and zero extra
calculation on replay/recovery. Each date has19 exact core comparisons,35 file
receipts and14 local alert dispositions. June6 applies two suggested identities;
June7 consumes those exact actions. No designated Sleep target was suggested.

| Date | Calculation owner | Operational attempt |
|---|---|---|
| June6 | `77731d95-03f4-4a82-8498-404f944df73b` | `e0918a5d-2ce5-489a-8ef5-32b9ce605e88` |
| June7 | `1b83fdca-d0ad-47d5-8694-414257ae68be` | `2a6dbb31-3d1a-4f7b-aa55-6f710f85fc7d` |

Image: `sha256:a8d606b23e65f85b326d87fd86e960f343af4789eec69b03deee70341cf98ebd`.
The982-file source manifest is unchanged. `real-source-20261008-001/closure-proof.json`
indexes128 evidence files; its SHA256 is
`01278f44616e40abe73c74d6c896588769ee954df5efaa189ca1cdf273ad8ae0`.

## Delivered boundary

`execute_day` remains the only calculation boundary. An explicit new-run profile
captures requirement bands/advance allocations, four post-BPR input tables and
three pre-clear force sources into typed PostgreSQL rows in its existing atomic
commit. Accepted runs cannot be backfilled. The operational command consumes
the committed owner and its own accepted predecessor; it never calculates.

The O1–O9 runner writes BOR and histories, BPR exceptions, parent-Norm files,
the ten-member physical/processed input archive, eight upload-log archives,
enabled Norm reports, fourteen local alert dispositions, a consistent PG dump
and fresh-target logical restore, then verifies whole-attempt completion.
Every attempt, operation, file, member, intent and backup is bound to its exact
run, date, configuration, sources and actions. Missing or changed proof denies
completion. A session advisory lease excludes concurrent workers; explicit
retry/repair retains failed attempts and original successful receipts.

## Qualifications and limits

- BOR history alone uses complete typed row bags; the generated SOB input-table
  export alone uses exact header plus complete exported-row bags. Strict sequence
  failures remain retained. All other existing ordering assertions stay exact.
- Missing mapped report ZIPs prefer an exact surviving copy. If all copies are
  missing, approved regeneration requires exact ordered members and decompressed
  content, preserving original and replacement hashes separately. This is
  qualified archive restoration, not exact container-byte parity. Plain files,
  backups, traces and arbitrary archives do not inherit it.
- PG restore is qualified logical restore for the exact eleven approved CHECK
  cast pairs, independently checked in every backup. Rows, NULLs, duplicates,
  ordinals, sequences and other schema metadata remain exact. SQL full/differential
  backup fixtures use separately owned databases; SQL/PG physical backup bytes
  and methods are not equivalent.
- Alerts are durable local evaluations only; no email is sent. Explicitly absent
  transport and unavailable sanitation attachments retain their declared
  dispositions. Empty histories, queues and log openings certify only their
  approved domain. Populated SOB/MOQ approval workflows and active NMS remain
  unsupported. Native `IsBatchFileExecuted=0` and the separate enabled-writer
  successor qualification remain unchanged.
- The real-source trial is one SKU at ten locations on June6–7. It does not
  establish independent full-day legacy parity, performance, publication, UI,
  deployment, active client hooks or full temporal readiness. Serving resources,
  the stopped temporal run and all prior seals remain outside this delivery.

## Evidence locations

All evidence is external to Git under
`D:/freshvcf-build/evidence/cohort2-20261008-001`.

| Boundary | Evidence |
|---|---|
| Frozen raw inputs, supplement and initial populations | `closure-proposal-v1/proposal.json` and its pinned files |
| Candidate image/source/config/tool identity | `real-source-20261008-001/frozen.json`, `candidate-source.json`, `image-id.txt`, `configuration-template.json`, `setup.json` |
| Qualified retained ordering | `real-source-20261008-001/qualified-ordering.json`; original strict failures remain in `bor-native-a002/a003.json` and `input-files-a003.json` |
| Native attachment/report bytes | `alert-native-a002.json`, `remaining-files-a002.json`, `bor-files-a001.json`, upload/input export proofs |
| Restore qualification | `backup-runtime-cast-proof-a001.json`; each runtime attempt retains complete compressed source/restored images and dump |
| Zero-calculation retry and repair | `integrated-retry-a001.log`, `approved-zip-repair-a002.log`, real-source receipts and requests |
| Fresh schema and identity | `fresh-schema-a002.json/.log`, `baseline-closure-a001.log` |

The initial fresh-schema harness falsely skipped database creation; its receipt
is explicitly invalid for fresh-schema proof and retained unchanged. The corrected
proof applied all95 migrations to a verified fresh database before six tests.
The first real-source harness used the wrong reader for a validation family;
its failed receipt and successful read-only diagnosis are retained. The approved
reader correction resumes the existing June6 owner without recalculation.

## Operator procedure for this retained delivery

Use PowerShell in `F:/freshvcf`. Execute steps 1–4 in order. Stop on any nonzero
exit; do not substitute another database, run, request or image. The private
compose file contains local credentials and must remain outside Git. These
commands reuse the completed requests and verify the retained delivery; they
do not authorize a new business date or new restore target.

1. Set the exact retained compose path:

   ```powershell
   $Cohort2Compose = 'D:/freshvcf-build/evidence/cohort2-20261008-001/real-source-20261008-001/compose.private.json'
   ```

2. Verify/reuse June6's completed materialization and its explicit repair:

   ```powershell
   docker compose -f $Cohort2Compose run --rm worker /app/manage.py cohort2_operational materialize --request /cohort2/real-source-20261008-001/materialize-000.json
   if ($LASTEXITCODE -ne 0) { throw 'June6 materialization verification failed' }
   docker compose -f $Cohort2Compose run --rm worker /app/manage.py cohort2_operational recover --request /cohort2/real-source-20261008-001/recover-000.json
   if ($LASTEXITCODE -ne 0) { throw 'June6 repair verification failed' }
   ```

3. Verify/reuse June7's completed materialization and explicit repair:

   ```powershell
   docker compose -f $Cohort2Compose run --rm worker /app/manage.py cohort2_operational materialize --request /cohort2/real-source-20261008-001/materialize-001.json
   if ($LASTEXITCODE -ne 0) { throw 'June7 materialization verification failed' }
   docker compose -f $Cohort2Compose run --rm worker /app/manage.py cohort2_operational recover --request /cohort2/real-source-20261008-001/recover-001.json
   if ($LASTEXITCODE -ne 0) { throw 'June7 repair verification failed' }
   ```

4. Run the final read-only CLI check against the exact successor attempt:

   ```powershell
   docker compose -f $Cohort2Compose run --rm worker /app/manage.py cohort2_operational check --attempt 2a6dbb31-3d1a-4f7b-aa55-6f710f85fc7d
   if ($LASTEXITCODE -ne 0) { throw 'Cohort2 final check failed' }
   ```

Each command prints its attempt identity, status, run and owned file root.
The final CLI invocation passed in `cli-check-day-001.log`. Do not rerun the calculation harness.
Unexpected missing files or failed attempts require a separately explicit
request with the exact lineage; do not edit or overwrite the retained requests.
