[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ExecutionId)
$ErrorActionPreference='Stop'
& 'D:/freshvcf-build/venv/Scripts/python.exe' "$PSScriptRoot/offline_temporal_validation.py" summary --execution-id $ExecutionId
exit $LASTEXITCODE
