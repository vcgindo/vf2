#requires -Version 5.1
<#
One repository-owned CSV-to-selected-application operation. Run in the deployment directory.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^\d{4}-\d{2}-\d{2}$')][string]$BusinessDate,
    [string]$InputDirectory,
    [switch]$InspectOnly,
    [switch]$Resume
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
. "$PSScriptRoot/powershell_compat.ps1"
$null = [datetime]::ParseExact($BusinessDate, 'yyyy-MM-dd', [cultureinfo]::InvariantCulture)
# Resolve every declared service so optional dependencies on inactive installer
# profiles remain defined in the snapshot. This config command starts nothing;
# execution below still enables only daily and always uses --no-deps.
$configText = & docker compose --profile '*' config --format json
if ($LASTEXITCODE -ne 0) { throw 'Compose configuration failed' }
$config = ConvertFrom-VfJson ($configText -join "`n")
$daily = $config['x-vectorflow-daily']
foreach ($key in @('input_dir','binding_file','state_dir')) {
    if (-not $daily[$key] -or -not (Test-VfAbsolutePath $daily[$key])) {
        throw "Set an absolute VF_DAILY_$($key.ToUpperInvariant()) in the private env file"
    }
}
$inputRoot = [IO.Path]::GetFullPath($daily.input_dir)
$bindingFile = Get-Item -LiteralPath $daily.binding_file
if ($bindingFile.PSIsContainer) { throw 'Binding must be a file' }
$stateRoot = [IO.Path]::GetFullPath($daily.state_dir)
Assert-VfUpgradeIdle -StateRoot $stateRoot
$null = New-Item -ItemType Directory -Force -Path $stateRoot
$lock = $null
$maintenance = $false
$executing = $false
$operationRoot = Join-Path $stateRoot ([datetime]::UtcNow.ToString('yyyyMMddTHHmmssfff') + '-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $operationRoot
$receiptFile = Join-Path $operationRoot 'operation.json'
$overrideFile = Join-Path $operationRoot 'compose.daily.json'
$attempt = $null
function ComposeCall([string[]]$Arguments, [switch]$Json, [string]$InputText) {
    $start = [Diagnostics.ProcessStartInfo]::new('docker')
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.RedirectStandardInput = $PSBoundParameters.ContainsKey('InputText')
    $start.WorkingDirectory = (Get-Location).Path
    Set-VfProcessArguments $start (@('compose','--profile','daily','-f',$overrideFile) + $Arguments)
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    $null = $process.Start()
    $outTask = $process.StandardOutput.ReadToEndAsync()
    $errTask = $process.StandardError.ReadToEndAsync()
    if ($start.RedirectStandardInput) {
        $bytes = [Text.Encoding]::UTF8.GetBytes($InputText)
        $process.StandardInput.BaseStream.Write($bytes, 0, $bytes.Length)
        $process.StandardInput.BaseStream.Close()
    }
    $process.WaitForExit()
    $text = $outTask.GetAwaiter().GetResult()
    $diagnostic = $errTask.GetAwaiter().GetResult()
    $exit = $process.ExitCode
    $process.Dispose()
    Add-Content -LiteralPath (Join-Path $operationRoot 'commands.log') -Value ($text + "`n" + $diagnostic + "`nEXIT=$exit") -Encoding utf8
    if ($exit -ne 0) { throw "Daily operation failed (exit $exit). Read $operationRoot/commands.log; state is retained." }
    if ($Json) { return ConvertFrom-VfJson $text }
}
function Worker([string[]]$Arguments) {
    return ComposeCall -Arguments (@('run','--rm','--no-deps','-T','daily','manage.py','process_daily_csv') + $Arguments) -Json
}
try {
    $lock = [IO.File]::Open((Join-Path $stateRoot 'daily.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    # Materialize the already-resolved deployment privately. This preserves its
    # exact project/networks/TLS configuration without changing COMPOSE_FILE/.env.
    # Never print this resolved file: it may contain existing private env values.
    $config.services.daily.image = $config.services.mta.image
    $config.services.daily.pull_policy = 'never'
    $config.services.daily.Remove('build')
    foreach ($key in @($config.services.mta.environment.Keys)) {
        if ($key -match '^VF_(MTA_|BPR_|RRR_|GUIDED_|HISTORY_REPORTS_|RESEARCH_AVAILABILITY_|MDM_SOURCE_DIGEST)') {
            $config.services.daily.environment[$key] = $config.services.mta.environment[$key]
        }
    }
    foreach ($key in @('VF_MTA_SELECTION_FILE','VF_MTA_PUBLISHED_RUN','VF_MTA_PUBLISHED_DIGEST','VF_BTR_REPORTING_GENERATION')) {
        $config.services.daily.environment[$key] = ''
    }
    $config.services.daily.environment.VF_MTA_ALLOW_UNSELECTED_STARTUP = '1'
    $config.services.daily.environment.VF_DAILY_BINDING_FILE = '/onboarding/' + $bindingFile.Name
    $volumes = @($config.services.daily.volumes)
    foreach ($mount in $config.services.mta.volumes) {
        if ($mount.target -notin @('/run/secrets','/var/lib/vectorflow') -and $mount.read_only) {
            $volumes = @($volumes | Where-Object { $_.target -ne $mount.target }) + @($mount)
        }
    }
    $config.services.daily.volumes = $volumes + @(
        @{type='bind';source=$inputRoot;target='/incoming';read_only=$true},
        @{type='bind';source=$bindingFile.DirectoryName;target='/onboarding';read_only=$true})
    $selection = $config.services.mta.environment.VF_MTA_SELECTION_FILE
    if ($selection -notin @('', '/var/lib/vectorflow/selection.json')) { throw 'Unsupported MTA selection path; existing configuration retained' }
    $config.services.mta.environment.VF_MTA_SELECTION_FILE = '/var/lib/vectorflow/selection.json'
    Write-VfUtf8 $overrideFile ($config | ConvertTo-Json -Depth 100)
    ComposeCall -Arguments @('config','--quiet')
    if (-not $InputDirectory) { $InputDirectory = Join-Path $inputRoot $BusinessDate }
    $source = [IO.Path]::GetFullPath($InputDirectory)
    $relative = Get-VfRelativePath $inputRoot $source
    if ($relative -eq '..' -or $relative.StartsWith('../') -or (Test-VfAbsolutePath $relative)) {
        throw 'Input directory must stay inside VF_DAILY_INPUT_DIR'
    }
    $sourceArgs = @('--date',$BusinessDate,'--input-directory',('/incoming/' + $relative))
    if ($InspectOnly) {
        $attempt = Worker -Arguments (@('inspect') + $sourceArgs)
    } else {
        $stageArgs = @('stage') + $sourceArgs
        if ($Resume) { $stageArgs += '--resume' }
        $attempt = Worker -Arguments $stageArgs
        if ($attempt.status -eq 'PUBLISHED') {
            # Do not select an older completed day or rerun its calculation.
            $attempt['message'] = 'Already published; no calculation, selection or restart performed.'
            if ($Resume) {
                $verifier = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'daily_serving_check.py'))
                # Use the runtime role in a disposable no-port process. Native
                # admission must prove this is STILL the selected latest day
                # before touching the serving container. Never rewrite selection.
                $null = ComposeCall -Arguments @('run','--rm','--no-deps','-T','--entrypoint','python','mta','-',
                    '--run-id',$attempt.run_id,'--output-digest',$attempt.output_digest,'--admission-only') -InputText $verifier -Json
                if (-not $selection) { Write-VfEnvironment -Root (Get-Location).Path -Changes @{MTA_SELECTION_FILE='/var/lib/vectorflow/selection.json'} }
                $maintenance = $true
                ComposeCall -Arguments @('up','-d','--no-deps','--no-build','--force-recreate','--wait','mta')
                $null = ComposeCall -Arguments @('exec','-T','mta','python','-','--run-id',$attempt.run_id,
                    '--output-digest',$attempt.output_digest) -InputText $verifier -Json
                $maintenance = $false
                $attempt['message'] = 'Existing selected publication serving verified; no calculation or selection replay.'
            }
        } else {
            if ($attempt.status -in @('FAILED','REJECTED')) { throw 'Preserved failed/rejected attempt requires diagnosis; automatic retry is forbidden.' }
            if ($attempt.phase -ne 'VALIDATED' -and -not $Resume) { throw 'Existing committed/pending attempt: rerun with -Resume after reviewing its receipt.' }
            $attemptArgs = @('--attempt',$attempt.attempt_id)
            ComposeCall -Arguments @('stop','mta')
            $maintenance = $true
            $executing = $true
            if ($attempt.status -ne 'PREPARED') {
                $executeArgs = @('execute') + $attemptArgs
                if ($Resume) { $executeArgs += '--resume' }
                $attempt = Worker -Arguments $executeArgs
            }
            $attempt = Worker -Arguments (@('select') + $attemptArgs)
            # Persist only after successful native selection, so initialized
            # metadata works before day one and future restarts use this selection.
            if (-not $selection) { Write-VfEnvironment -Root (Get-Location).Path -Changes @{MTA_SELECTION_FILE='/var/lib/vectorflow/selection.json'} }
            ComposeCall -Arguments @('up','-d','--no-deps','--no-build','--force-recreate','--wait','mta')
            # Run the repository-owned read-only check without patching or
            # rebuilding the sealed image that owns this committed run.
            $verifier = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'daily_serving_check.py'))
            $proof = ComposeCall -Arguments @('exec','-T','mta','python','-','--run-id',$attempt.run_id,'--output-digest',$attempt.output_digest) -InputText $verifier -Json
            $attempt = Worker -Arguments (@('acknowledge') + $attemptArgs + @('--proof',($proof | ConvertTo-Json -Depth 20 -Compress)))
            $maintenance = $false
        }
    }
    Write-VfUtf8 $receiptFile ($attempt | ConvertTo-Json -Depth 100)
    $attempt | ConvertTo-Json -Depth 100
} catch {
    $failure = $_
    Write-VfUtf8 $receiptFile (@{status='STOPPED';business_date=$BusinessDate;maintenance=$maintenance;execution_invoked=$executing;
      attempt=$attempt;error=$_.Exception.Message} | ConvertTo-Json -Depth 30)
    # After entering the native boundary, old selection may no longer represent
    # current mutable state. Never pretend a file rollback undoes a committed day.
    if ($maintenance) {
        # A service may have started before readiness failed, or an operator may
        # have started it during the day. Maintenance must be actual, not prose.
        try { ComposeCall -Arguments @('stop','mta') }
        catch { Write-Warning 'Could not confirm MTA stopped; inspect the named container before further work.' }
        Write-Warning 'Publication/serving is unverified. MTA stop requested; preserve state and use explicit -Resume after diagnosis.'
    }
    throw $failure
} finally {
    if ($lock) { $lock.Dispose() }
    # The resolved deployment can contain private settings. Retain diagnostic
    # receipts, never retain a second copy of passwords in the operation folder.
    Remove-Item -LiteralPath $overrideFile -Force -ErrorAction SilentlyContinue
}
