# Operator procedure: retained temporal validation

## Execute now — steps 1–4 only

**Run steps 1–4 in order, then stop. Do not execute H1–H8 now.** The DBM-refined
source/image transition passed live non-calculating preflight on 8 October 2026.
Calculation and publication still require separate direct human releases.
`docs/MIGRATION.md`, “DBM-refined offline readiness”, is the sole status tracker.
Use the existing Windows account with SQL access. Keep Docker Desktop, MSSQL and
the owned stack running. Do not change services, credentials or source files.

### 1. Open PowerShell and load the exact pins

```powershell
Set-Location F:/freshvcf
$ErrorActionPreference = 'Stop'
$Pins = @{
    ExecutionId = 'temporal-full-001'
    TransitionFile = 'D:/freshvcf-build/daily-3006/runtime/offline-temporal-full-001/readiness-dbm-v1/transition-v006.json'
    TransitionSha256 = '4dc6f1acd7f8fd47e2c6893a39e12e1c607f0392c5d2656b0efbf70fcb2cc29d'
}
$CandidateImage = 'sha256:8cd55a876595f37398eaa25828f4d51ecd07b737d25b9208498686732ab7abb2'
```

Continue to step 2. Keep this PowerShell session for subsequent steps.

### 2. Read the accepted-prefix summary

```powershell
$summaryJson = ./tools/Get-TemporalValidationSummary.ps1 @Pins
if ($LASTEXITCODE -ne 0) { throw 'STOP: summary failed. Follow recovery A.' }
$summary = $summaryJson | ConvertFrom-Json
$summary | ConvertTo-Json -Depth 20
if ($summary.required_days -ne 21 -or $summary.population.pairs -ne 1240) {
    throw 'STOP: population or horizon differs. Follow recovery A.'
}
```

The verified prefix is June 6–8, 2026, with no calculated-only day. Day 4
(June 9) is the next calculation; do not calculate it in this section.
Day 3 uses its original modern run and the approved repaired legacy capture;
the failed legacy attempt remains preserved. Calculated-only days do not count
as accepted. On exit code 0, continue to step 3; on failure follow recovery A.

### 3. Run the non-calculating preflight

```powershell
./tools/Test-TemporalValidationPreflight.ps1 @Pins -Scenario full -Image $CandidateImage
if ($LASTEXITCODE -ne 0) { throw 'STOP: preflight failed. Follow recovery A.' }
```

This verifies the frozen input/ledger, source/image/runner pins, owned SQL and
PostgreSQL, storage, resources and persisted prefix/actions. It reads retained
outputs; it does not calculate a day or change serving selection. On `PASS`,
continue to step 4.

### 4. Hand over the output and stop

Give the maintainer the step-2/3 output and
`D:/freshvcf-build/daily-3006/runtime/offline-temporal-full-001/readiness-dbm-v1`.
**Do not run H1–H8 now.** Successful preflight is not a calculation or publication
release. Leave 3005 and the existing 3006 selection unchanged.

## After a direct human calculation release — H1–H4 only

Enter this section only after the human explicitly releases the held full run
and the maintainer records that release in `docs/MIGRATION.md`. The release must
name `temporal-full-001` and these exact pins. It does not release publication.
No setup, reset, new execution ID, input generation or accepted-day replay is
part of this procedure.

### H1. Load the pins

Execute **step 1** above. Keep the computer awake and connected to power until
H4 finishes. Continue to H2.

### H2. Verify readiness

Execute **steps 2 and 3** above. On `PASS`, continue to H3. On failure follow
recovery A. The preflight checks the current contiguous prefix, so the same
procedure works after an authorized retry.

### H3. Resume the existing execution

```powershell
./tools/Invoke-TemporalValidation.ps1 @Pins -Scenario full -Image $CandidateImage -Mode combined -Resume -ReleaseCalculations
if ($LASTEXITCODE -ne 0) { throw 'STOP: execution failed. Follow recovery A.' }
```

Leave PowerShell open until the command returns. The runner reuses accepted
receipts, starts at the next unaccepted day, and stops at the first failed check.
Each modern and legacy day uses its own persisted predecessor and the frozen
Apply/Sleep policy. A fresh comparison worker checks only the next day; accepted
prefix receipts remain hash-verified. All 31 comparisons and independent RRR
are required before advancing. Modern and Windows workers stay at 4 GiB/2 CPUs.

This is **validation mode**: mandatory trace compression, hashing, normalization,
legacy capture and real pinned actions remain enabled. The 70.2-second modern
production sample omitted validation work, actions and two initialized empty
workflow sources. A separate untimed acceptance run proved complete source
equality. That timing is not the combined offline duration per day, a full-run
ETA or matched-resource legacy performance proof. Required daily relational state, actions,
histories and report sources persist; expensive report preparation runs only
at terminal publication. No selection occurs during H3. Continue to H4 only
on exit code 0. On interruption or failure follow recovery A.

### H4. Verify all 21 dates, then stop before publication

```powershell
$summaryJson = ./tools/Get-TemporalValidationSummary.ps1 @Pins
if ($LASTEXITCODE -ne 0) { throw 'STOP: summary failed. Follow recovery A.' }
$summary = $summaryJson | ConvertFrom-Json
$expectedDates = 0..20 | ForEach-Object { ([datetime]'2026-06-06').AddDays($_).ToString('yyyy-MM-dd') }
if (($summary.accepted_dates -join ',') -ne ($expectedDates -join ',')) {
    throw 'STOP: accepted dates are incomplete. Follow recovery A.'
}
if ($summary.required_days -ne 21 -or $summary.population.pairs -ne 1240) {
    throw 'STOP: population or horizon differs. Follow recovery A.'
}
$summary | ConvertTo-Json -Depth 20
```

Hand over the summary. **Stop here until a separate direct human publication
release is recorded.** Calculation release does not authorize H5.

## After a separate direct human publication release — H5–H8

### H5. Prepare and publish June 26 on 3006

Execute step 1 to load the same pins, then run:

```powershell
./tools/Publish-TemporalValidationTerminal.ps1 @Pins -ReleasePublication
if ($LASTEXITCODE -ne 0) { throw 'STOP: publication failed. Follow recovery B.' }
```

This verifies terminal acceptance, prepares and seals all 18 layers, activates
approved access/hierarchy and selects the terminal day on 3006. For only the
known two expedite layers failing because RRR was not yet prepared, it retries
once and verifies all previous READY receipts remain identical. All other
failures stop. Readiness waits up to 180 seconds. It does not change 3005 or
cut over 3004. On exit code 0 and `SELECTED`, continue to H6.

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
./tools/Publish-TemporalValidationTerminal.ps1 @Pins -RestorePrevious
if ($LASTEXITCODE -ne 0) { throw 'STOP: restoration failed. Follow recovery C.' }
```

This restores the recorded previous configuration and waits for readiness. It
refuses to overwrite configuration changed by another operator.
Continue only on exit code 0. On failure, follow **recovery C**.

## H8. Check the final summary and stop

```powershell
$final = ./tools/Get-TemporalValidationSummary.ps1 @Pins | ConvertFrom-Json
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
2. The runner already retries once for the exact known RRR prerequisite failure,
   retaining every READY layer. It stops for any other failure or a failed retry.
3. Wait for the maintainer to identify the cause and confirm retry is safe. Then
   repeat **H5** with the same pins and ID. Do not repeat calculation.

## Recovery C — restoration failure

1. Stop and contact the maintainer immediately with the output and evidence
   directory. Preserve the previous configuration and selection receipt.
2. Do not edit `compose.json`, restart other services or issue another publication.
3. After the maintainer reconciles serving configuration, repeat **step H7**, then
   **step H8**. Do not declare completion before restoration passes.

## Evidence and limits — no operator commands

- Frozen input: `D:/freshvcf-build/synthetic/rlt-4-7-v1/scenario-004/full-input.json`,
  SHA256 `ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56`.
  All 1,240 pairs and all 21 days (June 6–26) are unchanged.
- Original package/image/source pins and every accepted/failed attempt remain
  preserved. Versioned readiness receipts describe the additive transition;
  they do not overwrite `package.json`. Version 6 links the immutable prior
  `readiness-v1/transition-a005.json` and admits only the three DBM source changes
  from `d004dc1`, the exact image above and the pinned host admission guard.
  The fixed image retains the earlier runtime-compatible approval envelope;
  the host validates the new approval and exact parent/hash/delta before dispatch.
  This readiness update made no schema change. Existing migrations remain intact.
- Verified evidence: `readiness-dbm-v1/readiness-result.json`,
  `operator-summary.log`, `operator-preflight.log`, `candidate-content.json`,
  `reused-proof-pins.json`, `sql-ownership.json` and unchanged PostgreSQL before/
  after snapshots. Candidate bytes match 610 runtime files; normal Windows/Git
  CRLF-to-LF checkout normalization is recorded separately from raw image pins.
- Day-three comparison is already accepted. Do not rerun `compare-next` or any
  accepted day. The version-6 transition preserves all three original accepted
  receipts; subsequent comparisons use one fresh bounded worker for the next day.

- RRR's MTO=0 invocation remains the approved synthetic gate exception.
  BOR/BOROA and Guided Excess rolling history remain deferred. Existing GIT
  SQL207, ordering and custom-report limitations remain. Missing Sleep targets
  stay unexercised; empty orders do not prove positive-order workflows.
- Login, product/location scopes, permissions, existing report contracts and
  the original publication seal remain protected. This is not MTO integration,
  matched-resource performance, browser acceptance or production cutover proof.
- Private compose files and credentials remain outside Git. Never print or copy
  their secret values into logs, documentation or commits.
