# Pick operator runbook

This runbook covers the positive Pick fixture approved in human controller turn
`01a11ad1-c612-7e62-aea1-985a531c709b`. The two authorized modern dates have
already been calculated. The normal operator procedure below is read-only. It
must not execute another business date, repeat a native Pick stage, start or stop
the database, migrate schema, deploy, benchmark, or activate serving.

## Pinned identity

| Item | Value |
|---|---|
| Current compose definition | `D:/freshvcf-build/complete-daily-assessment/pg/compose.pick-final.private.json` |
| Compose project | `freshvcf-complete001` |
| Current worker image | `sha256:eefbecff9083ad670224c841ed91a57c44c75b8b8e869e79451847ea0a85d783` |
| Historical calculation/recovery image | `sha256:eed864f13836bd017f053ce9a6992524372550075c80de100c15637b0d0ba41d` |
| Evidence mount | host `D:/freshvcf-build/evidence/pick-closure-20261008-001`, worker `/pick-evidence` |
| Input | `positive/input-v1.json`, SHA256 `7e60ef1b3d73a36889b25a43995234ec5839a5bb646da5b782328189a1b2699d` |
| Pick configuration | `positive/config-v1.json`, SHA256 `19a7b9f9dd840389d0d948ef21ed740bad2f0f55d01c286b3678da06c1e53a45` |
| Revision | `pick-positive-20261008-001` |
| Policy | `canonical-tied-order-v1` |
| Pick file root | host `D:/freshvcf-build/evidence/pick-closure-20261008-001/positive/files`, worker `/pick-evidence/positive/files` |
| Day 1 | 6 June 2026, run `9607a6ec-07e9-4be7-9be9-2d204b7ecebc` |
| Day 2 | 7 June 2026, run `39dd7880-2ba4-42bd-9e90-40428f4b1ede` |

The frozen input retains facts through 26 June only for the required
three-times-maximum-RLT horizon. Dates 8–26 June are not authorized for
execution. The earlier empty June 6 timeline and all its evidence remain
separate and preserved.

## Current operator procedure: read-only verification

Run steps1–6. If step4 finds a missing report file, use recovery step7, then
repeat steps1–6. If all files exist, skip recovery and stop after step6.
Any other failure is a stop for investigation; do not change an identity,
regenerate an artifact, or invoke calculation.

1. Bind paths and verify immutable input, configuration, image and mount.

   ```powershell
   $Compose = 'D:/freshvcf-build/complete-daily-assessment/pg/compose.pick-final.private.json'
   $Owned = 'D:/freshvcf-build/evidence/pick-closure-20261008-001/positive'
   $Definition = Get-Content -LiteralPath $Compose -Raw | ConvertFrom-Json
   if ($Definition.name -ne 'freshvcf-complete001') { throw 'Compose project differs' }
   if ($Definition.services.worker.image -ne 'sha256:eefbecff9083ad670224c841ed91a57c44c75b8b8e869e79451847ea0a85d783') { throw 'Worker image differs' }
   if ($Definition.services.worker.volumes -notcontains 'D:\freshvcf-build\evidence\pick-closure-20261008-001:/pick-evidence') { throw 'Evidence mount differs' }
   if ((Get-FileHash -Algorithm SHA256 -LiteralPath "$Owned/input-v1.json").Hash.ToLowerInvariant() -ne '7e60ef1b3d73a36889b25a43995234ec5839a5bb646da5b782328189a1b2699d') { throw 'Input differs' }
   if ((Get-FileHash -Algorithm SHA256 -LiteralPath "$Owned/config-v1.json").Hash.ToLowerInvariant() -ne '19a7b9f9dd840389d0d948ef21ed740bad2f0f55d01c286b3678da06c1e53a45') { throw 'Pick configuration differs' }
   ```

2. Verify the completed identities and predecessor relationship from immutable
   execution evidence.

   ```powershell
   $Day1 = Get-Content -LiteralPath "$Owned/day1/execution.json" -Raw | ConvertFrom-Json
   $Day2 = Get-Content -LiteralPath "$Owned/day2/execution.json" -Raw | ConvertFrom-Json
   if ($Day1.days.Count -ne 1 -or $Day1.days[0].date -ne '2026-06-06' -or [string]$Day1.days[0].run_id -ne '9607a6ec-07e9-4be7-9be9-2d204b7ecebc') { throw 'Day 1 identity differs' }
   if ($Day2.days.Count -ne 2 -or $Day2.days[1].date -ne '2026-06-07' -or [string]$Day2.days[1].run_id -ne '39dd7880-2ba4-42bd-9e90-40428f4b1ede') { throw 'Day 2 identity differs' }
   if ([string]$Day2.days[1].predecessor_id -ne '9607a6ec-07e9-4be7-9be9-2d204b7ecebc') { throw 'Day 2 predecessor differs' }
   if ($Day1.revision -ne 'pick-positive-20261008-001' -or $Day2.revision -ne 'pick-positive-20261008-001') { throw 'Revision differs' }
   if ($Day1.artifact_sha256 -ne '7e60ef1b3d73a36889b25a43995234ec5839a5bb646da5b782328189a1b2699d' -or $Day2.artifact_sha256 -ne $Day1.artifact_sha256) { throw 'Artifact identity differs' }
   ```

3. Verify both read-only route receipts. Day 1 and day 2 must retain exact typed
   state, five source digests and both file copies as recorded by the readback
   verifier.

   ```powershell
   $Day1Readback = Get-Content -LiteralPath "$Owned/day1-readback.json" -Raw | ConvertFrom-Json
   $Day2Readback = Get-Content -LiteralPath "$Owned/day2-readback.json" -Raw | ConvertFrom-Json
   if ($Day1Readback.status -ne 'PASS' -or $Day1Readback.days.Count -ne 1 -or [string]$Day1Readback.days[0].run_id -ne '9607a6ec-07e9-4be7-9be9-2d204b7ecebc') { throw 'Day 1 readback differs' }
   if ($Day2Readback.status -ne 'PASS' -or $Day2Readback.days.Count -ne 2 -or [string]$Day2Readback.days[1].run_id -ne '39dd7880-2ba4-42bd-9e90-40428f4b1ede') { throw 'Day 2 readback differs' }
   if (@($Day1Readback.days[0].source_digests.PSObject.Properties).Count -ne 5 -or @($Day2Readback.days[1].source_digests.PSObject.Properties).Count -ne 5) { throw 'Five-source proof differs' }
   if ($Day1Readback.days[0].file_copies.Count -ne 8 -or $Day2Readback.days[1].file_copies.Count -ne 8) { throw 'Eight-copy proof differs' }
   ```

4. Open and hash the four owned reports for each completed run. Require the
   `output` and `download` copies to be byte-identical; never rebuild or filter a
   partial CSV during verification.

   ```powershell
   $Reports = @('LogisticPickListReport.csv','LogisticRemainingQtySummary.csv','LogisticRemainingQtyDetails.csv','TransportReqSummaryRpt.csv')
   $RunIds = @('9607a6ec-07e9-4be7-9be9-2d204b7ecebc','39dd7880-2ba4-42bd-9e90-40428f4b1ede')
   foreach ($RunId in $RunIds) {
     foreach ($Report in $Reports) {
       $Output = "$Owned/files/$RunId/output/$Report"
       $Download = "$Owned/files/$RunId/download/$Report"
       $Bytes = [System.IO.File]::ReadAllBytes($Download)
       if ($Bytes.Length -eq 0) { throw "Empty report: $Download" }
       if ((Get-FileHash -Algorithm SHA256 -LiteralPath $Output).Hash -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $Download).Hash) { throw "Output/download bytes differ: $RunId/$Report" }
       [pscustomobject]@{RunId=$RunId; Report=$Report; Bytes=$Bytes.Length; SHA256=(Get-FileHash -Algorithm SHA256 -LiteralPath $Download).Hash.ToLowerInvariant()}
     }
   }
   ```

5. Verify both consumed native receipts without invoking native SQL.

   ```powershell
   $NativeDay1Path = 'D:/freshvcf-build/complete-daily-assessment/pick-positive-native-day1-a002.json'
   $NativeDay2Path = 'D:/freshvcf-build/complete-daily-assessment/pick-positive-native-day2.json'
   $NativeDay1 = Get-Content -LiteralPath $NativeDay1Path -Raw | ConvertFrom-Json
   $NativeDay2 = Get-Content -LiteralPath $NativeDay2Path -Raw | ConvertFrom-Json
   if ($NativeDay1.status -ne 'PASS' -or $NativeDay1.date -ne '2026-06-06' -or [string]$NativeDay1.run_id -ne '9607a6ec-07e9-4be7-9be9-2d204b7ecebc' -or $NativeDay1.native_pick_invocations -ne 1) { throw 'Day 1 native receipt differs' }
   if ($NativeDay2.status -ne 'PASS' -or $NativeDay2.date -ne '2026-06-07' -or [string]$NativeDay2.run_id -ne '39dd7880-2ba4-42bd-9e90-40428f4b1ede' -or $NativeDay2.native_pick_invocations -ne 1) { throw 'Day 2 native receipt differs' }
   ```

   That call used owner `fdc5bc5e-4d68-4b3a-b8e6-d2754df0e2f4` through
   `tools.offline_windows_worker.run` with4GiB/twoCPU limits. Its single permitted day 1 native
   invocation is consumed. The day 2 receipt consumes the only permitted native
   invocation for that date. No native rerun command belongs in this runbook.

6. Verify final consumer and accepted recovery receipts without binding or
   mutating a publication, grant, or selected run.

   ```powershell
   $ConsumerProof = Get-Content -LiteralPath "$Owned/consumer-final-proof.json" -Raw | ConvertFrom-Json
   if ($ConsumerProof.status -ne 'PASS' -or $ConsumerProof.checks.Count -ne 8 -or $ConsumerProof.publication_or_grant_mutations -ne 0) { throw 'Final consumer proof differs' }
   if (@($ConsumerProof.checks | Where-Object { $_.native_hierarchy_scope_denial -ne 'PASS' -or $_.missing_entitlement_status -ne 403 -or $_.unaccepted_publication_status -ne 503 }).Count -ne 0) { throw 'Consumer denial contract differs' }
   $ConsumerUnitLog = Get-Content -LiteralPath "$Owned/consumer-final-unit.log" -Raw
   if ($ConsumerUnitLog -notmatch 'Ran 10 tests' -or $ConsumerUnitLog -notmatch '(?m)^OK\s*$') { throw 'Final consumer unit proof differs' }
   $AcceptedRecovery = Get-Content -LiteralPath "$Owned/recovery/recovery-proof.json" -Raw | ConvertFrom-Json
   if ($AcceptedRecovery.status -ne 'PASS' -or $AcceptedRecovery.calculation_calls -ne 0 -or -not $AcceptedRecovery.run_and_action_identity_unchanged -or -not $AcceptedRecovery.exercise_missing_file) { throw 'Accepted recovery proof differs' }
   if (@($AcceptedRecovery.files_before.PSObject.Properties).Count -ne 16 -or @($AcceptedRecovery.files_after.PSObject.Properties).Count -ne 16) { throw 'Accepted recovery file population differs' }
   ```

   The final consumer image changes only the two Pick catalogue bindings in
   `mta/presentation/selective.py`; all calculation files have the same hashes as
   the image that calculated the two dates. The actual PostgreSQL proof and log
   are `positive/consumer-final-proof.json` and `positive/consumer-final.log`;
   the ten-test log is `positive/consumer-final-unit.log`. The final proof
   positively opens all eight report/date download paths. Direct `open_report`
   correctly denies the fixture's native NULL hierarchy, HTTP denies a missing
   entitlement with 403, and an authorized header without an accepted
   publication receives `publication_acceptance_required` with 503. No
   application port was bound.

## Step7 — recover a missing file only

Recovery is retrieval proof, not authorization for another business-day or
native invocation. The pinned guard owns the supported `run_temporal` call,
patches calculation to raise, and proves the same run rows, digests, action IDs
and files with zero calculation calls. A routine operator does not pass
`--exercise-missing-file`; that one-time acceptance branch is separate.

The one-time missing-file branch has passed at
`positive/recovery/recovery-proof.json`: zero calculation calls, the same two run
and action identities/digests, and all 16 files restored or unchanged. Routine
recovery may use the current final compose because its pinned guard prevents
calculation and the calculation files are unchanged.

Verify the guard and invoke it with a fresh direct child evidence directory:

```powershell
$RecoveryGuard = "$Owned/recover_completed.py"
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $RecoveryGuard).Hash.ToLowerInvariant() -ne '80b1997985a1f8b774b0f86a286700911076f9aa7dd2014e28530ea535fded50') { throw 'Recovery guard differs' }
$RecoveryName = 'operator-recovery-' + [guid]::NewGuid().ToString()
$RecoveryEvidence = "/pick-evidence/positive/$RecoveryName"
docker compose -p freshvcf-complete001 -f $Compose run --rm --no-deps worker /pick-evidence/positive/recover_completed.py --evidence $RecoveryEvidence
if ($LASTEXITCODE -ne 0) { throw 'Completed-identity recovery guard failed; preserve evidence and stop' }
$RecoveryProof = Get-Content -LiteralPath "$Owned/$RecoveryName/recovery-proof.json" -Raw | ConvertFrom-Json
if ($RecoveryProof.status -ne 'PASS' -or $RecoveryProof.calculation_calls -ne 0 -or -not $RecoveryProof.run_and_action_identity_unchanged -or $RecoveryProof.exercise_missing_file) { throw 'Recovery proof differs' }
```

The guard's internal supported call deliberately omits `--bounded-one-day` and
`--continue-from` and keeps `--through 1`. Do not call `run_temporal` directly,
substitute another script, reuse an evidence directory, or add
`--exercise-missing-file` during routine recovery.

After successful recovery, repeat steps1–6. Do not run the historical commands below.

## Historical execution audit — do not rerun

The following are the exact modern commands already used. They are retained as
audit text only. Their stdout/stderr are in `positive/day1.log` and
`positive/day2.log` under the owned evidence root.

```powershell
$HistoricalCompose = 'D:/freshvcf-build/complete-daily-assessment/pg/compose.pick-candidate.private.json'
```

Day 1:

```powershell
docker compose -p freshvcf-complete001 -f $HistoricalCompose run --rm --no-deps worker manage.py run_temporal /pick-evidence/positive/input-v1.json --sha256 7e60ef1b3d73a36889b25a43995234ec5839a5bb646da5b782328189a1b2699d --revision pick-positive-20261008-001 --evidence /pick-evidence/positive/day1 --through 0 --automatic-actions --computation-only --bounded-one-day --complete-pick-policy canonical-tied-order-v1 --pick-output-root /pick-evidence/positive/files --pick-config /pick-evidence/positive/config-v1.json --pick-config-sha256 19a7b9f9dd840389d0d948ef21ed740bad2f0f55d01c286b3678da06c1e53a45
```

Day 1 readback:

```powershell
docker compose -p freshvcf-complete001 -f $HistoricalCompose run --rm --no-deps worker /pick-proof/readback.py --execution /pick-evidence/positive/day1/execution.json --output /pick-evidence/positive/day1-readback.json
```

Day 2:

```powershell
docker compose -p freshvcf-complete001 -f $HistoricalCompose run --rm --no-deps worker manage.py run_temporal /pick-evidence/positive/input-v1.json --sha256 7e60ef1b3d73a36889b25a43995234ec5839a5bb646da5b782328189a1b2699d --revision pick-positive-20261008-001 --evidence /pick-evidence/positive/day2 --through 1 --continue-from /pick-evidence/positive/day1 --automatic-actions --computation-only --bounded-one-day --complete-pick-policy canonical-tied-order-v1 --pick-output-root /pick-evidence/positive/files --pick-config /pick-evidence/positive/config-v1.json --pick-config-sha256 19a7b9f9dd840389d0d948ef21ed740bad2f0f55d01c286b3678da06c1e53a45
```

Day 2 readback:

```powershell
docker compose -p freshvcf-complete001 -f $HistoricalCompose run --rm --no-deps worker /pick-proof/readback.py --execution /pick-evidence/positive/day2/execution.json --output /pick-evidence/positive/day2-readback.json
```

## Proof and access boundary

The fixed calculation roster contains 16 cases: 13 exact or approved-qualified
passes and three approved fail-closed conflicting-update denials. The tied-row
receipt is `pick-tie-witness-a005.json`; 60 focused unit checks passed. These
proofs preserve exact quantities, ranks, truck fields, NULLs, types and duplicate
multiplicity. Only final relation retrieval order and approved four-file row
order are qualified.

The native source adapter explicitly supplies NULL for six unused nullable
VehicleMaster metadata columns (Length, Width, Height, ToleranceInWeight,
ToleranceInVolume, TransportLoadTypeCutOff). Canonical Pick SQL does not read
these columns. All produced source values are compared after exact SQL decimal
scale restoration; no rounding, consumed default or omitted value is accepted.

Each positive date produced seven formed rows and one residual row. Each formed
six full trucks carrying 60 units; the day 1 residual quantity is one and the
day 2 residual quantity is five. Both matched-input native receipts pass.

Each completed run owns these four files in both its `output` and `download`
directories: `LogisticPickListReport.csv`,
`LogisticRemainingQtySummary.csv`, `LogisticRemainingQtyDetails.csv`, and
`TransportReqSummaryRpt.csv`.

The existing authenticated routes are:

- `/api/mta/DownloadReports/LogisticPickListReport`
- `/api/mta/DownloadReports/LogisticRemainingQtySummary`
- `/api/mta/DownloadReports/LogisticRemainingQtyDetails`
- `/api/mta/DownloadReports/TransportReqSummaryRpt`

API download requires the stored `mta-report-urls` entitlement, an accepted
`DAILY_CHAIN`/`SUCCEEDED` selected publication with its pinned digest, and full
permission coverage for every contributing SKU, source, destination and logistic
location. This fixture retains native NULL hierarchy values, so its authenticated
API scope check denies access. The local owned files are verified, but this is no
positive serving, frontend, deployment or cutover claim.
