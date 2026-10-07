[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ExecutionId,[switch]$RestorePrevious)
$ErrorActionPreference='Stop'
$runnerArgs=@('publish','--execution-id',$ExecutionId)
if ($RestorePrevious) { $runnerArgs += '--restore' }
& 'D:/freshvcf-build/venv/Scripts/python.exe' "$PSScriptRoot/offline_temporal_validation.py" @runnerArgs
exit $LASTEXITCODE
