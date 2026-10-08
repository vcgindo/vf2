# Cohort3 operator audit

Execute steps 1–4 in order in PowerShell. This audits the completed delivery;
do not rerun preparation, activation, consumer sweeps or calculations, and do not
start a serving stack. Copy the commands inside each block, without the Markdown
fence lines. A failed check means stop and report the mismatch; never regenerate
evidence to make the audit pass.

1. Select the checkout and load the delivered evidence index.

```powershell
Set-Location F:/freshvcf
$ErrorActionPreference = 'Stop'
$cohort3Index = Get-Content -LiteralPath docs/COHORT3_EVIDENCE_INDEX.json -Raw | ConvertFrom-Json
if ($cohort3Index.qualification -ne 'COHORT3_QUALIFIED_CLOSURE') { throw 'Unexpected disposition' }
```

2. Verify every indexed external file.

```powershell
foreach ($cohort3File in $cohort3Index.files.PSObject.Properties) {
    $cohort3Path = Join-Path $cohort3Index.evidence_root $cohort3File.Name
    $cohort3Hash = (Get-FileHash -LiteralPath $cohort3Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($cohort3Hash -ne $cohort3File.Value) { throw "Evidence mismatch: $($cohort3File.Name)" }
}
Write-Output "Verified $($cohort3Index.files.PSObject.Properties.Name.Count) evidence files"
```

3. Verify the local proof image and retained strict failure dispositions.

```powershell
$cohort3Image = docker image inspect --format '{{.Id}}' freshvcf-cohort3-proof:closure-003
if ($LASTEXITCODE -ne 0 -or $cohort3Image -ne $cohort3Index.image) { throw 'Proof image mismatch' }
foreach ($cohort3Receipt in @('consumer-day1-a007.json','consumer-day2-a002.json')) {
    $cohort3Result = Get-Content -LiteralPath (Join-Path $cohort3Index.evidence_root $cohort3Receipt) -Raw | ConvertFrom-Json
    if ($cohort3Result.status -ne 'FAILED' -or $cohort3Result.failures.Count -ne 2) { throw 'Strict failures changed' }
    $cohort3Labels = @($cohort3Result.failures.label | Sort-Object)
    if (($cohort3Labels -join ',') -ne 'git-child-GetPlanningDataGrid,orderFulfillment-custom') { throw 'Unapproved failure' }
    if (@($cohort3Result.failures | Where-Object actual -ne 503).Count -ne 0) { throw 'Failure status changed' }
}
Write-Output 'Qualified closure verified; both approved route blocks remain explicit'
```

4. Read `docs/COHORT3_HANDOFF.md` for supported scope and remaining product gates,
then stop. No next cohort, benchmark, temporal run or service cutover follows.

The executed acceptance commands and logs are indexed evidence. Private compose
files and fixture credentials remain outside Git. The original FAILED receipts
are intentional strict results, not instructions to repair or retry. A later
execution requires its own task scope and a new evidence filename.
