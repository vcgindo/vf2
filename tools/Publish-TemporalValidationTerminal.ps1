[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ExecutionId,[string]$TransitionFile='',[string]$TransitionSha256='',[switch]$RestorePrevious,[switch]$ReleasePublication)
$ErrorActionPreference='Stop'
$runnerArgs=@('publish','--execution-id',$ExecutionId)
if ($TransitionFile -or $TransitionSha256) { $runnerArgs += @('--transition-file',$TransitionFile,'--transition-sha256',$TransitionSha256) }
if ($RestorePrevious) { $runnerArgs += '--restore' }
if ($ReleasePublication) { $runnerArgs += '--release-publication' }
& 'D:/freshvcf-build/venv/Scripts/python.exe' "$PSScriptRoot/offline_temporal_validation.py" @runnerArgs
exit $LASTEXITCODE
