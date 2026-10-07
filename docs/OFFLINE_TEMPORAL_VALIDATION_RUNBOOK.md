# Operator procedure: full 21-day validation

**Execute steps 1–8 in order.** This runs 1,240 pairs for June 6–26, 2026,
compares both engines, checks terminal reports on 3006, and restores the previous
3006 selection. The operator executes the full run; the agent has not run it.

Use `temporal-full-001` throughout. **Do not rerun the accepted ten-pair trial,
regenerate inputs or repeat database setup.** On failure, follow the named
recovery instruction before continuing.

## 1. Open PowerShell

```powershell
Set-Location F:/freshvcf
$ErrorActionPreference = 'Stop'
```

Use the existing Windows account with SQL oracle access. Keep the computer awake
and connected to power through step 8. Docker Desktop, MSSQL and the existing
`freshvcf-daily3006` stack must be running; step 2 checks them. Do not change
source files, images, credentials or configuration during the run.

## 2. Run preflight

```powershell
./tools/Test-TemporalValidationPreflight.ps1 -ExecutionId temporal-full-001 -Scenario full
if ($LASTEXITCODE -ne 0) { throw 'STOP: preflight failed. Follow recovery A.' }
```

Continue only on exit code 0 and `PASS`. This checks input/source/image identity,
the ledger, SQL access/ownership, PostgreSQL health, resource limits and storage.

## 3. Execute the full run

Run this block exactly. It chooses initial execution or resume automatically.

```powershell
$packagePath = 'D:/freshvcf-build/daily-3006/runtime/offline-temporal-full-001/package.json'
if (Test-Path -LiteralPath $packagePath) {
    ./tools/Invoke-TemporalValidation.ps1 -ExecutionId temporal-full-001 -Scenario full -Mode combined -Resume
} else {
    ./tools/Invoke-TemporalValidation.ps1 -ExecutionId temporal-full-001 -Scenario full -Mode combined
}
if ($LASTEXITCODE -ne 0) { throw 'STOP: execution failed. Follow recovery A.' }
```

Leave PowerShell running until the command returns. Each day runs both engines
independently, then requires 31 comparisons and the daily RRR source proof before
advancing. Workers use 4 GiB and two CPUs. Serving selection stays unchanged.

Continue only on exit code 0. On failure or interruption, follow **recovery A**;
do not immediately rerun the block.

## 4. Verify all 21 accepted dates

```powershell
$summary = ./tools/Get-TemporalValidationSummary.ps1 -ExecutionId temporal-full-001 | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'STOP: summary failed. Follow recovery A.' }
$expectedDates = 0..20 | ForEach-Object { ([datetime]'2026-06-06').AddDays($_).ToString('yyyy-MM-dd') }
if (($summary.accepted_dates -join ',') -ne ($expectedDates -join ',')) {
    throw 'STOP: accepted dates are incomplete. Follow recovery A.'
}
if ($summary.required_days -ne 21 -or $summary.population.pairs -ne 1240) {
    throw 'STOP: population or horizon differs. Follow recovery A.'
}
$summary | ConvertTo-Json -Depth 20
```

Continue only if every check passes. Calculated days alone do not count as accepted.

## 5. Publish June 26 on 3006

```powershell
./tools/Publish-TemporalValidationTerminal.ps1 -ExecutionId temporal-full-001
if ($LASTEXITCODE -ne 0) { throw 'STOP: publication failed. Follow recovery B.' }
```

This verifies the accepted prefix, prepares and seals all 18 layers, activates
access/hierarchy, and selects the terminal day on 3006. Readiness waits up to
180 seconds. It does not change 3005 or cut over 3004.

Continue only on exit code 0 and `SELECTED`. On failure, follow **recovery B**.

## 6. Check the terminal reports

Open `http://localhost:3006/login`. Use `stage2.broad@vectorflow.local` and its
existing password from
`D:/freshvcf-build/preview/secrets/stage2-fixture-accounts.json`.
Complete the normal login challenge if shown. Do not reset credentials or grants.

Perform all five checks below. Choose **Show All** when the filter dialog opens.
Record each displayed date, row count and error in
`D:/freshvcf-build/daily-3006/runtime/offline-temporal-full-001/operator-ui-check.txt`.

| Order | URL | Required check |
|---|---|---|
| 6.1 | `http://localhost:3006/mta/supply-chain-intelligence-hub/bpr` | Grid finishes loading and shows 26 Jun 2026. Selecting a row loads shipment data or an explicit empty result. |
| 6.2 | `http://localhost:3006/mta/insights-and-trends/buffer-trend-report` | Both On-Hand and Pipeline views finish loading and show 26 Jun 2026. |
| 6.3 | `http://localhost:3006/mta/dbm/dbm-norm-suggestions` | Grid finishes loading and shows 26 Jun 2026. Zero suggestions is valid after automatic APPLY. Do not submit additional Apply/Sleep actions. |
| 6.4 | `http://localhost:3006/mta/supply-chain-intelligence-hub/rrr` | Grid finishes loading and shows 26 Jun 2026. An empty result is valid; an error or persistent loading indicator is not. |
| 6.5 | `http://localhost:3006/mta/supply-chain-intelligence-hub/rrr-color-bandwise` | Use this direct URL; the retained menu click did not navigate in the trial. Grid must finish loading, including a valid empty result. This screen has no date label. |

Do not expect trial row counts or create data to populate empty reports.
Write `UI PASS` only if all five checks pass; otherwise write `UI FAILED` and the
failed check. **In either case, execute step 7.**

## 7. Restore the previous 3006 selection

Run this even when a browser check failed:

```powershell
./tools/Publish-TemporalValidationTerminal.ps1 -ExecutionId temporal-full-001 -RestorePrevious
if ($LASTEXITCODE -ne 0) { throw 'STOP: restoration failed. Follow recovery C.' }
```

This restores the recorded previous configuration and waits for readiness. It
refuses to overwrite configuration changed by another operator.
Continue only on exit code 0. On failure, follow **recovery C**.

## 8. Check the final summary and stop

```powershell
$final = ./tools/Get-TemporalValidationSummary.ps1 -ExecutionId temporal-full-001 | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'STOP: summary failed. Follow recovery A.' }
if ($final.publication -ne 'trial verified; previous selection restored') {
    throw 'STOP: restoration is not confirmed. Follow recovery C.'
}
$final | ConvertTo-Json -Depth 20
```

The current summary uses the literal label `trial verified; previous selection
restored` for a restored full run too. It reports selection state, not the
operator's browser result. Keep the entire evidence directory and
`operator-ui-check.txt`; invocation summaries are already saved there.

Report completion only when steps 2–8 passed and browser evidence says `UI PASS`.
For `UI FAILED`, hand over the evidence after restoration and report that UI
acceptance is outstanding. **Stop. Do not start another run or leave June 26 selected.**

## Recovery A — preflight, execution or summary failure

1. Stop issuing execution commands. Keep the same execution ID and all evidence.
2. Give the maintainer the command output and
   `D:/freshvcf-build/daily-3006/runtime/offline-temporal-full-001`.
   Early failures may be under `D:/freshvcf-build/evidence/offline-runner-failures`.
3. Wait for the maintainer to resolve the cause and confirm the same execution is
   safe to resume. Interrupted workers require committed-state reconciliation;
   changed pins or service identities require explicit reconciliation. Do not
   edit receipts, delete attempts, reset databases or increase memory.
4. After that confirmation, return to **step 2**. Step 3 reuses accepted captures.

## Recovery B — publication failure

1. Stop before browser verification. Give the maintainer the publication output
   and evidence directory from recovery A.
2. A known first-pass issue can leave only `planning_expedite_charts` and
   `planning_expedite_transit` failed because RRR is prepared later in the same
   attempt. The maintainer must confirm those exact failures and a READY RRR
   prerequisite before authorizing a retry. Other failures require diagnosis.
3. After the maintainer confirms retry is safe, repeat **step 5** with the same ID.
   Successful layers and identical receipts are reused. Do not repeat calculation.

## Recovery C — restoration failure

1. Stop and contact the maintainer immediately with the output and evidence
   directory. Preserve the previous configuration and selection receipt.
2. Do not edit `compose.json`, restart other services or issue another publication.
3. After the maintainer reconciles serving configuration, repeat **step 7**, then
   **step 8**. Do not declare completion before restoration passes.

## Reference — no commands to execute

- Implementation `8e1569d`; handoff `7dc193b`; scenario `9c2218d`, on
  `codex/btr-ready-snapshot-trial`.
- Image `freshvcf-daily3006-mta:offline-temporal-003`, ID
  `sha256:0408073029940316a695ff4384cacaace211269500fbd4a90c6e0963018abfe2`.
- The completed ten-pair June 6–8 trial passed 93 comparisons, daily RRR proofs,
  terminal readback and 18-layer preparation. Its previous selection was restored.
- Focused suite: 31 tests passed; 387 pinned resources unchanged. Migrations
  0074/0075 and a fresh 75-migration database were verified. The whole suite has
  six failures and 19 errors also present in the baseline.
- `package.json`, `modern-*`, `legacy-*`, `compare-*` and `summary-*` preserve pins
  and evidence. Keep failed attempts. Independent engine modes are maintainer
  tools, not part of this operator procedure.
- RRR's MTO=0 invocation is an approved synthetic gate exception. BOR/BOROA and
  Guided Excess rolling history remain deferred. Retained GIT SQL207, ordering
  and custom-report limitations remain. Empty orders do not prove positive order
  workflows; absent Sleep targets stay unexercised. This is not MTO integration
  or production cutover acceptance.
