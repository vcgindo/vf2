# Operator procedure: retained temporal validation

## Execute now — steps 1–3 only

**The full run `temporal-full-001` is on human hold. Execute steps 1–3 below,
then stop. Do not execute the held procedure H1–H8.** The authoritative status is
[docs/MIGRATION.md](MIGRATION.md), under “Integrated daily execution refinement”
and “Full run on human hold”. The separately authorized maintainer refinement
and single legacy day-three retry do not release the full run.

### 1. Open PowerShell in the checkout

```powershell
Set-Location F:/freshvcf
$ErrorActionPreference = 'Stop'
```

Continue to step 2. Do not start, restart or configure any service.

### 2. Read the retained execution summary

```powershell
$summaryJson = ./tools/Get-TemporalValidationSummary.ps1 -ExecutionId temporal-full-001
if ($LASTEXITCODE -ne 0) { throw 'STOP: summary failed. Give the output to the maintainer; do not retry execution.' }
$summary = $summaryJson | ConvertFrom-Json
$summary | Select-Object execution_id, accepted_dates, required_days, attempts, legacy_captures, publication | ConvertTo-Json -Depth 20
```

This command reads existing receipts; it does not run either engine. On exit
code 0, continue to step 3. On any error, give the output to the maintainer and
stop. Do not execute a resume command suggested by the underlying summary's
`next_safe_command` field: that field does not account for the human hold.
Likewise, `unselected; terminal command required` is a stored selection-status
label, not an instruction to publish. Continue to step 3 for either label.

### 3. Hand over the summary and stop

Give the maintainer the step-2 output and this evidence directory:
`D:/freshvcf-build/daily-3006/runtime/offline-temporal-full-001`.
Preserve all files and failed attempts. Leave 3005 and the current 3006 selection
unchanged. **There is no further operator execution step in the current scope.**

## Verified mode commands — reference only; do not execute now

The maintainer already executed the following calls in the separately owned
refinement database. Operators must still execute only steps1–3 above. These
commands document mode behavior; they are not a release of the held full run.
Do not repeat them or provision their databases.

Production command (called through Django `call_command` by the retained timing
probe; this is the equivalent CLI argument list):

```text
manage.py run_daily /input/full-input.json
  --sha256 ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56
  --day-index 0 --revision refine-production-001 --evidence-mode production
  --mdm-source 2
  --mdm-source-digest fe2548f936c8b17133a37ea1adb491fcbbd71ea1d58bc42633da0e4a1477a0cb
  --bpr-remark-horizon 90
```

It executes exactly one day and commits required operational rows. It does not
infer Apply/Sleep decisions, generate comparison archives, prepare terminal
reports or select a serving run. Success alone is not independent parity.

Verified validation day-one retry (the named failed capture is retained):

```text
manage.py run_temporal /input/full-input.json
  --sha256 ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56
  --revision refine-validation-001-day1-a002
  --evidence /proof/modern-day1-a002 --through 0
  --automatic-actions --bounded-one-day --mdm-source 1
  --mdm-source-digest 098cb331bcf2f0a68d050d1858298eafeeb255120149959d7d4f82d7d6fe740f
  --bpr-remark-horizon 90 --mdm-retry 38fe4bee-20e8-4ead-ab94-36e38a1a180b
```

`run_temporal` explicitly uses validation evidence, retains full checkpoints and
applies only the pinned automatic action policy. Legacy capture/comparison and
`record_parity` remain separate operations. Both commands preserve typed rows,
input identity, ordered state and atomic daily completion. Neither command is a
serving deployment command. Evidence and the private isolated compose file are
under `D:/freshvcf-build/refinement/integrated-001/`; credentials stay outside Git.

## Held procedure — H1–H8 must not be executed now

The following is retained reference for a future full-run release. Before an
operator can use it, the maintainer must record explicit human authorization to
resume and reconcile the source/image/runner pins in `docs/MIGRATION.md`, then
issue an updated executable runbook. Successful optimization tests, restored SQL
access and permission for mandatory diagnostic capture are not that release.

This held procedure covers 1,240 pairs for June 6–26, 2026, terminal report checks
on 3006 and restoration of the previous selection. The full run already has
retained attempts; it is not an unstarted execution.

Use `temporal-full-001` throughout. **Do not rerun the accepted ten-pair trial,
regenerate inputs or repeat database setup.** On failure, follow the named
recovery instruction before continuing.

## H1. Open PowerShell

```powershell
Set-Location F:/freshvcf
$ErrorActionPreference = 'Stop'
```

Use the existing Windows account with SQL oracle access. Keep the computer awake
and connected to power through step H8. Docker Desktop, MSSQL and the existing
`freshvcf-daily3006` stack must be running; step H2 checks them. Do not change
source files, images, credentials or configuration during the run.

## H2. Run preflight

```powershell
./tools/Test-TemporalValidationPreflight.ps1 -ExecutionId temporal-full-001 -Scenario full
if ($LASTEXITCODE -ne 0) { throw 'STOP: preflight failed. Follow recovery A.' }
```

Continue only on exit code 0 and `PASS`. This checks input/source/image identity,
the ledger, SQL access/ownership, PostgreSQL health, resource limits and storage.

## H3. Execute the full run

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

## H4. Verify all 21 accepted dates

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

## H5. Publish June 26 on 3006

```powershell
./tools/Publish-TemporalValidationTerminal.ps1 -ExecutionId temporal-full-001
if ($LASTEXITCODE -ne 0) { throw 'STOP: publication failed. Follow recovery B.' }
```

This verifies the accepted prefix, prepares and seals all 18 layers, activates
access/hierarchy, and selects the terminal day on 3006. Readiness waits up to
180 seconds. It does not change 3005 or cut over 3004.

Continue only on exit code 0 and `SELECTED`. On failure, follow **recovery B**.

## H6. Check the terminal reports

Open `http://localhost:3006/login`. Use `stage2.broad@vectorflow.local` and its
existing password from
`D:/freshvcf-build/preview/secrets/stage2-fixture-accounts.json`.
Complete the normal login challenge if shown. Do not reset credentials or grants.

Perform all five checks below. Choose **Show All** when the filter dialog opens.
Record each displayed date, row count and error in
`D:/freshvcf-build/daily-3006/runtime/offline-temporal-full-001/operator-ui-check.txt`.

| Order | URL | Required check |
|---|---|---|
| H6.1 | `http://localhost:3006/mta/supply-chain-intelligence-hub/bpr` | Grid finishes loading and shows 26 Jun 2026. Selecting a row loads shipment data or an explicit empty result. |
| H6.2 | `http://localhost:3006/mta/insights-and-trends/buffer-trend-report` | Both On-Hand and Pipeline views finish loading and show 26 Jun 2026. |
| H6.3 | `http://localhost:3006/mta/dbm/dbm-norm-suggestions` | Grid finishes loading and shows 26 Jun 2026. Zero suggestions is valid after automatic APPLY. Do not submit additional Apply/Sleep actions. |
| H6.4 | `http://localhost:3006/mta/supply-chain-intelligence-hub/rrr` | Grid finishes loading and shows 26 Jun 2026. An empty result is valid; an error or persistent loading indicator is not. |
| H6.5 | `http://localhost:3006/mta/supply-chain-intelligence-hub/rrr-color-bandwise` | Use this direct URL; the retained menu click did not navigate in the trial. Grid must finish loading, including a valid empty result. This screen has no date label. |

Do not expect trial row counts or create data to populate empty reports.
Write `UI PASS` only if all five checks pass; otherwise write `UI FAILED` and the
failed check. **In either case, execute step H7.**

## H7. Restore the previous 3006 selection

Run this even when a browser check failed:

```powershell
./tools/Publish-TemporalValidationTerminal.ps1 -ExecutionId temporal-full-001 -RestorePrevious
if ($LASTEXITCODE -ne 0) { throw 'STOP: restoration failed. Follow recovery C.' }
```

This restores the recorded previous configuration and waits for readiness. It
refuses to overwrite configuration changed by another operator.
Continue only on exit code 0. On failure, follow **recovery C**.

## H8. Check the final summary and stop

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

Report completion only when steps H2–H8 passed and browser evidence says `UI PASS`.
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
4. After that confirmation, return to **step H2**. Step H3 reuses accepted captures.

## Recovery B — publication failure

1. Stop before browser verification. Give the maintainer the publication output
   and evidence directory from recovery A.
2. A known first-pass issue can leave only `planning_expedite_charts` and
   `planning_expedite_transit` failed because RRR is prepared later in the same
   attempt. The maintainer must confirm those exact failures and a READY RRR
   prerequisite before authorizing a retry. Other failures require diagnosis.
3. After the maintainer confirms retry is safe, repeat **step H5** with the same ID.
   Successful layers and identical receipts are reused. Do not repeat calculation.

## Recovery C — restoration failure

1. Stop and contact the maintainer immediately with the output and evidence
   directory. Preserve the previous configuration and selection receipt.
2. Do not edit `compose.json`, restart other services or issue another publication.
3. After the maintainer reconciles serving configuration, repeat **step H7**, then
   **step H8**. Do not declare completion before restoration passes.

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
