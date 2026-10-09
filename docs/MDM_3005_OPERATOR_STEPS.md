# 3005 MDM operator steps

All eight MDM families are installed on3005. `MIGRATION.md` is the status authority.
The fixture proves requests and review decisions; it is not an accepted daily run.

## Execute a request and verify its decision

Execute steps1–9 in order. Use the branch explicitly named for your operation in
step3. Do not run deployment, migration or calculation commands in this workflow.

1. Open `http://localhost:3005`. Sign in as requester
   `stage2.restricted@vectorflow.local` using its retained password from the local
   private fixture-account record. The credentials remain in
   `D:/freshvcf-build/preview/secrets/stage2-fixture-accounts.json`; do not reset them.
2. Open MDM → Control Panel. Use View / Modify Records for existing SKU, Location,
   SKU–Location, SOB, MOQ, Stop PIPO, Seasonality Status or Forced Norm Changes.
   Use Add Records for new SOB, MOQ, Phase Out, PIPO, Target Norm, Absolute
   Seasonality or Delta Percentage Seasonality. Select that exact variant and
   press Submit. Apply the scoped filter and load the grid; confirm its count warning.
3. Follow the operation's row below, then continue to step4.

   | Operation | Required action |
   |---|---|
   | Stop PIPO or Seasonality Stop/Resume | Select the existing scoped row, invoke its Stop or Resume action, inspect the requested row and submit it. Do not upload a file. |
   | Other named variants | Download that variant's template, fill its existing columns, select the XLSX through the plus control, press Upload and resolve every validation error. Retain XLSX; this frontend rejects CSV as invalid ZIP data. Save/reopen the draft for variants with usable native reopening, then submit. |
   | Absolute or Delta Seasonality | Use the XLSX upload branch above and submit from the validated upload. Do not rely on reopening its saved draft: the native projection shows blank cells. |

4. Open Task Status. Record the new task ID and verify its assigned broad reviewer.
   The restricted fixture's eligible requests assign that reviewer automatically.
   If no reviewer is listed, stop and report the task ID; do not count it as approved.
5. Sign out. Sign in as reviewer `stage2.broad@vectorflow.local` using its retained
   password. Open Tasks Pending and click the task's activity/name.
6. Inspect all requested values. Scroll horizontally for hidden columns. If pinned
   keys obscure values, use the key column menu → Pin Column → No Pin. Approve or
   reject the rows according to the intended decision. For a whole-page decision,
   press Approve All or Reject All, select current page, confirm and press Submit.
   Repeat this step for each remaining page, then verify the task leaves Tasks Pending.
7. Sign out and return as the restricted requester. Open Task Status and click the
   chevron beside the recorded task ID. Verify the reviewer decision and timestamp.
   Press Download and verify the XLSX saves with the requested keys and values.
   Nine tested variants show Approved plus DB Update Pending. Seasonality Status
   shows Approved plus DB Updated. The parent header can still say Pending.
8. For an already completed task, open Modification History, select its family/key
   and the native date window. New pending headers are excluded; today's midnight
   cutoff and90-day restriction remain. An empty history grid is not lost approval:
   use step7's actual task decision. Seasonality Resume's review label says Stop in
   the native frontend; the stored request and downloaded resumed status are retained.
9. Stop. Approval does not authorize a business-day run. Do not run a source installer,
   migration, calculation or serving selection. Existing April7 reports stay selected;
   pending requests do not certify changed calculated Norms or engine recommendations.

Verified evidence includes all ten new task downloads (masters4–13), separate real
requester/reviewer sessions, existing three-family reads/exports and retained reports.
No permission, password, account, frontend or business-rule change was made.

## Rollback when the deployment admission or a preserved workflow regresses

Run steps 1–4 in order when deployment admission or a preserved workflow fails.

1. Stop submitting MDM changes and retain the failing URL, action and error.
2. Run this exact command in PowerShell, without Markdown fence markers:

   `docker compose -f D:/freshvcf-build/evidence/mdm3005-deployment-20261009-001/compose.previous.private.json up -d --no-deps --no-build mta`

3. Check the restored image:

   `docker inspect --format '{{.Image}}' freshvcf-preview-mta-1`

   Required result: `sha256:1192c35d8d1789dc1d2dc8a240ad71b2afc43eb2fd54b5e753730c10c85ad9ed`.
   Check readiness:

   `docker exec freshvcf-preview-mta-1 python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/readyz',timeout=10).read().decode())"`

   A startup-time failure is not readiness. If it fails, retain the output and
   report the failed rollback; do not restart other services.
4. Retain the additive schema and all evidence. Do not reverse migrations or
   restore over the database. If row-preservation fails before admission, the
   deployment guard deliberately leaves MTA stopped for a reviewed disposition.

The full pre-deployment archive is
`D:/freshvcf-build/evidence/mdm3005-deployment-20261009-001/before-deployment.private.dump`.
It is 1,223,815,894 bytes, SHA256
`054ce7390084fef0cd47e59136b386414ed26f87a8ab9859292f3b9b5e9465a2`.
Its 2,948-line restore catalogue was read successfully. This is not a claimed
restore rehearsal. Configuration manifests and archive stay outside Git.
