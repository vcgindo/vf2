[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ExecutionId,
    [ValidateSet('trial','full')][string]$Scenario='trial',
    [ValidateSet('combined','modern-only','legacy-only','compare-retained')][string]$Mode='combined',
    [string]$ScenarioManifest='F:/freshvcf/baseline/offline-temporal-scenarios-v1.json',
    [string]$Image='freshvcf-daily3006-mta:offline-temporal-003',
    [switch]$Resume
)
$ErrorActionPreference='Stop'
$runnerArgs=@('run','--execution-id',$ExecutionId,'--scenario',$Scenario,'--mode',$Mode,
    '--scenario-manifest',$ScenarioManifest,'--image',$Image)
if ($Resume) { $runnerArgs += '--resume' }
& 'D:/freshvcf-build/venv/Scripts/python.exe' "$PSScriptRoot/offline_temporal_validation.py" @runnerArgs
exit $LASTEXITCODE
