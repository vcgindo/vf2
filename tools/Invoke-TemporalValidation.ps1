[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ExecutionId,
    [ValidateSet('trial','full')][string]$Scenario='trial',
    [ValidateSet('combined','modern-only','legacy-only','compare-retained')][string]$Mode='combined',
    [string]$ScenarioManifest='F:/freshvcf/baseline/offline-temporal-scenarios-v1.json',
    [string]$TransitionFile='',
    [string]$TransitionSha256='',
    [string]$Image='freshvcf-daily3006-mta:offline-temporal-003',
    [switch]$Resume,
    [switch]$ReleaseCalculations
)
$ErrorActionPreference='Stop'
$runnerArgs=@('run','--execution-id',$ExecutionId,'--scenario',$Scenario,'--mode',$Mode,
    '--scenario-manifest',$ScenarioManifest,'--image',$Image)
if ($TransitionFile -or $TransitionSha256) { $runnerArgs += @('--transition-file',$TransitionFile,'--transition-sha256',$TransitionSha256) }
if ($Resume) { $runnerArgs += '--resume' }
if ($ReleaseCalculations) { $runnerArgs += '--release-calculations' }
& 'D:/freshvcf-build/venv/Scripts/python.exe' "$PSScriptRoot/offline_temporal_validation.py" @runnerArgs
exit $LASTEXITCODE
