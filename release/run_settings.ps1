#requires -Version 5.1
[CmdletBinding()]
param([string]$Export, [string]$Apply, [string]$EffectiveDate, [string]$Reason, [string]$OnDate)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
. "$PSScriptRoot/powershell_compat.ps1"
if ($Export -and $Apply) { throw 'Choose -Export or -Apply' }
if (($EffectiveDate -or $Reason) -and -not $Apply) { throw '-EffectiveDate and -Reason belong to -Apply' }
if ($OnDate -and ($Export -or $Apply)) { throw '-OnDate belongs to the settings display' }
if ($Apply -and (-not $EffectiveDate -or -not $Reason)) { throw 'Apply requires -EffectiveDate YYYY-MM-DD and -Reason' }
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
$lock = $null
try {
    $text = & docker compose --profile install --profile daily config --format json
    if ($LASTEXITCODE -ne 0) { throw 'Compose configuration failed' }
    $config = ConvertFrom-VfJson ($text -join "`n")
    $state = $config['x-vectorflow-daily']['state_dir']
    if ($state) {
        $state = Resolve-VfProjectPath $root $state
        Assert-VfUpgradeIdle $state
    }
    $arguments = @('compose','--profile','install','run','--rm','--no-deps','-T')
    $command = @('-m','release.execution_settings_command')
    if ($Export -or $Apply) {
        $file = if ($Apply) { $Apply } else { $Export }
        $full = [IO.Path]::GetFullPath($file)
        $parent = Split-Path $full -Parent
        if (-not (Test-Path -LiteralPath $parent -PathType Container)) { throw 'Settings file directory must already exist' }
        if ($Apply -and -not (Test-Path -LiteralPath $full -PathType Leaf)) { throw 'Exported settings file is missing' }
        if ($Export -and (Test-Path -LiteralPath $full)) { throw 'Choose a new export filename; existing exports are retained' }
        $arguments += @('-v',"${parent}:/settings-transfer")
        if ($Apply) {
            if (-not $state) { throw 'Configured daily state directory is required for settings apply' }
            $lock = [IO.File]::Open((Join-Path $state 'daily.lock'),'OpenOrCreate','ReadWrite','None')
            $command += @('apply','--file',('/settings-transfer/' + (Split-Path $full -Leaf)),
                          '--effective-date',$EffectiveDate,'--reason',$Reason)
        } else { $command += @('export','--file',('/settings-transfer/' + (Split-Path $full -Leaf))) }
    } else {
        $command += 'show'
        if ($OnDate) { $command += @('--business-date',$OnDate) }
    }
    $result = & docker @arguments mta-install @command
    if ($LASTEXITCODE -ne 0) { throw 'Settings operation failed; values were not partially applied. Preserve the export and diagnostic.' }
    $value = ConvertFrom-VfJson ($result -join "`n")
    if ($value.status -eq 'SETTINGS') {
        Write-Output "Effective settings for business date $($value.business_date) ($($value.date_basis)); revision $($value.effective.revision)."
        $value.rows | Where-Object { $_.path -notmatch '/(Parameter|Description)$' } |
            Select-Object module,parameter,ordinal,value_state,value_kind,value_text,activation | Format-Table -AutoSize
        if ($value['references']) {
            Write-Output 'Existing immutable owners (read-only references; managed by their original workflows):'
            $value.references | Select-Object module,parameter,ordinal,value_state,value_kind,value_text,source_owner | Format-Table -AutoSize
        }
        foreach ($scheduled in $value.scheduled) {
            Write-Output "Scheduled revision $($scheduled.revision), effective $($scheduled.effective_date)."
        }
    } else { Write-Output ($value | ConvertTo-Json -Depth 15) }
} finally {
    if ($lock) { $lock.Dispose() }
    Pop-Location
}
