[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ExecutionId,
    [ValidateSet('trial','full')][string]$Scenario='trial',
    [string]$ScenarioManifest='F:/freshvcf/baseline/offline-temporal-scenarios-v1.json',
    [string]$Image='freshvcf-daily3006-mta:offline-temporal-003'
)
$ErrorActionPreference='Stop'
& 'D:/freshvcf-build/venv/Scripts/python.exe' "$PSScriptRoot/offline_temporal_validation.py" preflight --execution-id $ExecutionId --scenario $Scenario --scenario-manifest $ScenarioManifest --image $Image
exit $LASTEXITCODE
