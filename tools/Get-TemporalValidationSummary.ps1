[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ExecutionId,[string]$TransitionFile='',[string]$TransitionSha256='')
$ErrorActionPreference='Stop'
$runnerArgs=@('summary','--execution-id',$ExecutionId)
if ($TransitionFile -or $TransitionSha256) { $runnerArgs += @('--transition-file',$TransitionFile,'--transition-sha256',$TransitionSha256) }
& 'D:/freshvcf-build/venv/Scripts/python.exe' "$PSScriptRoot/offline_temporal_validation.py" @runnerArgs
exit $LASTEXITCODE
