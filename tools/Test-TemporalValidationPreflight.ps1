[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ExecutionId,
    [ValidateSet('trial','full')][string]$Scenario='trial',
    [string]$ScenarioManifest='F:/freshvcf/baseline/offline-temporal-scenarios-v1.json',
    [string]$TransitionFile='',
    [string]$TransitionSha256='',
    [string]$Image='freshvcf-daily3006-mta:offline-temporal-003'
)
$ErrorActionPreference='Stop'
$runnerArgs=@('preflight','--execution-id',$ExecutionId,'--scenario',$Scenario,'--scenario-manifest',$ScenarioManifest,'--image',$Image)
if ($TransitionFile -or $TransitionSha256) { $runnerArgs += @('--transition-file',$TransitionFile,'--transition-sha256',$TransitionSha256) }
& 'D:/freshvcf-build/venv/Scripts/python.exe' "$PSScriptRoot/offline_temporal_validation.py" @runnerArgs
exit $LASTEXITCODE
