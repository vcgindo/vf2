# 3005 MDM deployment, source installation and UI acceptance

LATEST HUMAN CORRECTION: all five added groups are REQUIRED this pass under
MDM_3005_FIVE_GROUP_COMPLETION_PLAN.md. Three-family-only closure is superseded.
Retain backup/rollback/preservation gates below; source authority and any actual
new calculation proposal require exact decisions, not silent optional exclusion.

Direct human release: controller turn01a12181-43c9-7411-b909-b2bebaad0d54,
9 October2026. This finite plan governs the next stage; MIGRATION.md is the only
status tracker. Source commit12a8e71009fd1bfb82834d8f08e10c7eed5d9e2c is immutable.
Do not package the dirty working tree. Target is localhost3005 only.

## Fixed preservation boundary

Old MTA image1192c35d8d1789dc1d2dc8a240ad71b2afc43eb2fd54b5e753730c10c85ad9ed;
database test_freshvcf_stage2_vm_20261003_002 on freshvcf-test-postgres-1;
applied0052; source eccbec8cf5f61f87f80bdf65715dee350e616041e7957f27daead42bab4b975d;
selected April7 fixture bfd75b4b-a9df-4a08-82d3-852e3324b623;
BTR generation e5bdac30-bbd9-45d8-a93d-84a645fad73c.
Preserve exact effective environment/mounts/networks, fixture/permission bytes,
all existing rows/owners, authentication, credentials, frontend and MTO images.
Only replace the3005 MTA application service; do not recreate dependencies.
Retain4GiB/2CPU, restart=no and existing networks; create no host port.

No3006 mutation, new business days, legacy-engine calls, benchmarks, data reset,
blanket grant, flags, calculated Norm/history seed, shared restart or cleanup.
Existing source-specific approvals cannot transfer implicitly.

## Ordered execution and required gates

1. D1: Pin the running container/configuration/schema/selection and committed
   package. Save private effective configuration outside Git. Produce one new
   image from the committed MTA source and retained runtime dependencies; record
   its exact image/hash roster before any service replacement.
2. D2: Retain the old image and configuration; create a full custom PostgreSQL
   backup and verify successful pg_dump and readable pg_restore catalogue.
   Capture existing table/column/row identities and migration history. Check
   compatibility of the old application against the proved forward schema in an
   owned isolated proof process. A readable archive is not a restore rehearsal.
   Stop before serving mutation if backup or rollback feasibility is unproved.
3. D3: Record one consolidated source/input decision for optional families.
   Installation may proceed only for an exact authorized owner/input/configuration
   tuple. No missing bag is assumed empty. Do not weaken the daily predecessor,
   Force/Seasonality eligibility or existing fixture admission checks. D4 may
   proceed independently with the existing three-family source preserved.
4. D4: Stop only the3005 MTA application for the bounded maintenance window;
   retain D2's complete consistent backup and capture the final old-row snapshot;
   run the committed migration through
   empty0103 using its exact database identity. Compare every preserved old column
   and row, retaining new-schema additions separately. Start only MTA with the
   recorded image and unchanged effective configuration. Verify health/readiness,
   source/selection and all other container identities before UI work.
   Enforce prior migration retention and applied0103. Preserve each existing
   column's PostgreSQL type and nullability. Preserve existing Django content-type
   rows exactly; permit only metadata for the committed installed model roster.
   Every new business table must remain empty. Any post-start identity/configuration
   or admission failure restores the old image and checks its readiness.
5. D5: Use the existing real frontend and fixture accounts. Verify the matrix
   below, preserving native scope, payload, status, NULL/order/duplicate behavior.
   Downloads require an actual browser save or explicit user confirmation where
   the browser cannot observe saves. No fake identity headers or admission seals.
   Any workflow requiring a calculation day remains blocked pending a separate
   exact day-count/input/resource release.
6. D6: Record the deployed image/commit/schema/config/source identities, successful
   checks, failures and unexercised/blocked routes. Update the operator runbook
   with numbered commands and exact rollback triggers. Commit/push once, verify
   upstream and stop. No automatic next stage or production-readiness claim.

## Rollback contract

Before D4 save external `compose.previous.private.json` and
`compose.deployed.private.json` with only the MTA service and exact existing
networks/volumes/environment. The executable rollback is:

`docker compose -f <absolute compose.previous.private.json> up -d --no-deps --no-build mta`

Trigger it on startup/admission failure, lost fixture/source selection or an
attributable reader/workflow regression. Stop further writes first. Compatible
additive schema remains; do not reverse migrations or drop/overwrite any database.
If preserved row comparison fails, leave the affected application stopped and
report exact tables/differences plus the retained backup; restoration that would
replace data requires an exact reviewed target. Do not claim an unperformed
restore rehearsal. Final runbook replaces placeholders with retained exact paths.

## UI matrix and initial source limits

| Business group | Required positive checks | Current installation authority |
|---|---|---|
| SKU | Scoped current/filter/page/export, draft reopen, submit, assigned review, history | Existing installed source; preserve scope and credentials. |
| Location | Same workflow and location-scope checks | Existing installed source. |
| SKU–Location | Same workflow and both-scope checks | Existing installed source. |
| SOB/MOQ | Both formats/queues as supported; draft/submit/review/current/history/export | Exact three raw bags, format and upload-log authority must be reconciled; no invented empty owners. |
| StopPIPO | Draft/submit/review/current/history/export | Current fixture has no accepted same-source daily closing; binder remains blocked. |
| Phase controls | Shared7–9 draft/submit/review/history/export with native completion limits | Same predecessor boundary; no fabricated closing. |
| Seasonality | Eligible current/graph/upload/draft/review/history/export | Exact historical fixture supplement is not approved for current owner. |
| Force | Eligible current/draft/submit/review/history/export | Exact historical fixture/flags/hierarchy are not approved for current owner. |

Also verify BPR, BTR, Guided current/history and representative existing Planning,
Research, RRR and BOR routes in the unchanged frontend; preserve known explicit
blocked contracts. Menus, empty grids or denial responses are not positive family
workflow acceptance. Capture broad/restricted scope behavior with actual login.
