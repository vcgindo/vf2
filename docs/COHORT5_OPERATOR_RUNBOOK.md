# Cohort5 operator runbook

**Execute steps1–4 below, in order, then stop.** These are read-only delivery audit
steps. Do not execute the held issuance procedure. Copy commands inside blocks
only, without Markdown fences. No elevated PowerShell session is required.
Any thrown error means stop and retain its output.

1. Select the delivered checkout and index.

```powershell
Set-Location F:/freshvcf
$ErrorActionPreference = 'Stop'
$c5Index = Get-Content docs/COHORT5_EVIDENCE_INDEX.json -Raw | ConvertFrom-Json
if ($c5Index.disposition -ne 'QUALIFIED_ADMISSION_FIXTURE_PROOF') { throw 'Wrong delivery' }
```

2. Verify every retained evidence file and the delivered application source overlay.

```powershell
foreach ($c5File in $c5Index.files.PSObject.Properties) {
    $c5Path = Join-Path $c5Index.evidence_root $c5File.Name
    if ((Get-FileHash -LiteralPath $c5Path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $c5File.Value) {
        throw "Evidence mismatch: $($c5File.Name)"
    }
}
$c5Sources = Get-Content (Join-Path $c5Index.evidence_root 'source-overlay.json') -Raw | ConvertFrom-Json
foreach ($c5Source in $c5Sources.files.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath $c5Source.Name -Algorithm SHA256).Hash.ToLowerInvariant() -ne $c5Source.Value) {
        throw "Source mismatch: $($c5Source.Name)"
    }
}
Write-Output 'Cohort5 evidence and source identities verified'
```

3. Read COHORT5_HANDOFF.md. Record the result as **qualified admission fixture
proof**. There was no new business-day run. Native flag0, strict parity default,
the two blocked503 routes and all prior qualifications/failures remain.

4. Stop. Do not start a day, restore, issue a real receipt, select a run or change a
service. No command below is released for execution by this delivery.

## Held issuance and selection contract — do not execute

This is the exact future operator sequence after a separate frozen input/resource
release and completed run/operations/preparation. It is not the executable audit
above. A later release must replace every uppercase token with its approved value.
Do not guess a UUID, path, digest, opening or predecessor.

1. Package the delivered Cohort5 revision and migrate the newly approved owned
   database through0100. Provision the offline issuer privileges using
   packaging/cohort5/offline-issuer.sql. The deployment owner must supply a
   separately protected issuer connection; serving roles must not be owners,
   superusers or issuer members. Do not change existing serving accounts here.
2. Verify the authorized run/output, complete finalization/artifact files, own
   operation/repair chain, all native sources, hierarchy/catalogue and READY
   publication. Keep the candidate unselected. Configure the offline worker with
   VF_MTA_OPERATIONAL_POLICY=supported-synthetic-operational-v1,
   VF_MTA_DAILY_PUBLICATION=1, VF_MTA_SYNTHETIC_ROSTER=core-without-bor-v1,
   actions disabled, and blank Cohort3/fixture/terminal/history-extension settings.
   Mount exact source/evidence files read-only. Missing sources mean stop.
3. Execute exactly one issuance command in that owned worker:

   `python -m django accept_daily_operational --run-id RUN_UUID --output-digest OUTPUT_SHA --attempt ATTEMPT_UUID --artifact ARTIFACT_PATH --finalization-config FINALIZATION_PATH`

   If and only if the approved request names an existing completed repair leaf,
   append `--repair REPAIR_UUID`; any repair lineage must be explicit and verified.
   Require exit0 with policy, qualification, receipt, activation and selected=false.
   This command creates receipt and access together. **Do not separately execute
   activate_daily_ui for this operational path.** On failure both writes roll back.
   Retrying the identical request reverifies/reuses; a changed tuple is denied.
4. Execute the read-only selection check in the same policy/access configuration:

   `python -m django check_daily_selection --run-id RUN_UUID --output-digest OUTPUT_SHA`

   Require exit0 and retain the complete JSON: VF_MTA_PUBLISHED_RUN,
   VF_MTA_PUBLISHED_DIGEST, VF_MTA_DAILY_PUBLICATION,
   VF_BTR_REPORTING_GENERATION, VF_MTA_OPERATIONAL_POLICY,
   VF_MTA_OPERATIONAL_RECEIPT, configuration_digest and publication_seal.
   This command edits no environment, file or service. Do not assemble values from
   different owners or reuse a receipt after source/code/configuration drift.
5. Stop at the selection-check receipt. Installing the coherent tuple, restarting
   a service and authenticated browser verification require a separate serving
   release. Preserve the last valid serving configuration after every failure.
   The future serving startup must reverify the same code/files/owners with the
   selected policy/receipt/generation; per-request drift must deny service.

Blank operational policy preserves strict independent-parity admission. It is not
a fallback for a failed operational check. Existing Cohort3 two-owner admission
remains its separate exact contract. No latest-run fallback or extra UUID is valid.

## Proof resource reference — already executed; do not repeat

The exclusive proof database is fresh_cohort5_20261009_001 in the existing owned
freshvcf-complete001-postgres resource. No business-day rows remain after fixture
rollbacks. Source-mounted proof used the pinned Cohort4 runtime, no ports and
restart=no. Logs/index document actual migration, test and denial results.
Do not run proof.py setup again: database creation is intentionally one-time.
The private compose contains credentials; keep it outside Git and support bundles.
