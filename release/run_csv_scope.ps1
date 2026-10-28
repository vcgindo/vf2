#requires -Version 5.1
<# Manual CSV scope validation over the existing native engine. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^\d{4}-\d{2}-\d{2}$')][string]$BusinessDate,
    [Parameter(Mandatory)][ValidateSet('Full','UptoBPR','PostBPR','UptoDBM','PostDBM')][string]$Scope,
    [switch]$InspectOnly,
    [switch]$Resume,
    [switch]$Reconcile
)
$ErrorActionPreference = 'Stop'
if ($Reconcile -and ($Resume -or $InspectOnly)) { throw 'Reconcile separately, then inspect or resume the exact scope' }
. "$PSScriptRoot/powershell_compat.ps1"
if ($env:COMPOSE_FILE -or $env:COMPOSE_PATH_SEPARATOR) { throw 'Use .env for Compose settings; shell overrides would hide the persisted scope selection' }
$null = [datetime]::ParseExact($BusinessDate,'yyyy-MM-dd',[cultureinfo]::InvariantCulture)
$configText = & docker compose --profile '*' config --format json
if ($LASTEXITCODE -ne 0) { throw 'Compose configuration failed' }
$config = ConvertFrom-VfJson ($configText -join "`n")
$daily = $config['x-vectorflow-daily']
$scopePolicy = if ($daily.scope_policy) { $daily.scope_policy } else { 'retained-test' }
if ($scopePolicy -notin @('retained-test','generic')) { throw 'Set VECTORFLOW_SCOPE_POLICY=generic for supported generic scope processing' }
foreach ($key in @('input_dir','binding_file','state_dir')) {
    if (-not $daily[$key] -or -not (Test-VfAbsolutePath $daily[$key])) { throw "Configure the absolute daily $key first; run csv-init once" }
}
$inputRoot = [IO.Path]::GetFullPath($daily.input_dir)
$binding = Get-Item -LiteralPath $daily.binding_file
$profile = Join-Path $binding.DirectoryName 'config/scope-validation.json'
if ($scopePolicy -eq 'retained-test' -and -not (Test-Path -LiteralPath $profile -PathType Leaf)) { throw 'The retained-test mode requires config/scope-validation.json; choose generic explicitly for the packaged production profile' }
$stateRoot = [IO.Path]::GetFullPath($daily.state_dir)
$null = New-Item -ItemType Directory -Force -Path $stateRoot
$operationRoot = Join-Path $stateRoot ('scope-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $operationRoot
$privateConfig = Join-Path $operationRoot 'compose.private.json'
$receiptFile = Join-Path $operationRoot 'operation.json'
$lock = $null
$maintenance = $false
function ComposeCall([string[]]$Arguments, [switch]$Json) {
    $start = [Diagnostics.ProcessStartInfo]::new('docker')
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.WorkingDirectory = (Get-Location).Path
    Set-VfProcessArguments $start (@('compose','--profile','daily','-f',$privateConfig) + $Arguments)
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    $null = $process.Start()
    $outTask = $process.StandardOutput.ReadToEndAsync()
    $errTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $text = $outTask.GetAwaiter().GetResult()
    $errorText = $errTask.GetAwaiter().GetResult()
    $code = $process.ExitCode
    $process.Dispose()
    Add-Content -LiteralPath (Join-Path $operationRoot 'commands.log') -Value ($text + "`n" + $errorText + "`nEXIT=$code") -Encoding utf8
    if ($code -ne 0) { throw "Scope command failed ($code). Preserve $operationRoot and the named MTA volume; no automatic replay." }
    if ($Json) { return ConvertFrom-VfJson $text }
}
function Worker([string]$Operation, [string]$Service = 'daily', [string]$Run, [string]$SelectionDigest, [string]$Proof) {
    $arguments = @('run','--rm','--no-deps','-T',$Service,'-m','mta.runtime.csv_scope_operator',$Operation,
        '--date',$BusinessDate,'--scope',$Scope,'--policy',$scopePolicy,'--binding',('/onboarding/' + $binding.Name))
    if ($Resume) { $arguments += '--resume' }
    if ($Run) { $arguments += @('--run',$Run) }
    if ($SelectionDigest) { $arguments += @('--selection-digest',$SelectionDigest) }
    if ($Proof) { $arguments += @('--proof',$Proof) }
    return ComposeCall -Arguments $arguments -Json
}
try {
    $lock = [IO.File]::Open((Join-Path $stateRoot 'daily.lock'),'OpenOrCreate','ReadWrite','None')
    $config.services.daily.image = $config.services.mta.image
    $config.services.daily.pull_policy = 'never'
    $config.services.daily.Remove('build')
    foreach ($service in @('daily','provision')) {
        foreach ($key in @($config.services.mta.environment.Keys)) {
            if ($key -match '^VF_(MTA_|BPR_|RRR_|GUIDED_|HISTORY_REPORTS_|RESEARCH_AVAILABILITY_|MDM_SOURCE_DIGEST)') {
                $config.services[$service].environment[$key] = $config.services.mta.environment[$key]
            }
        }
        foreach ($key in @('VF_MTA_SELECTION_FILE','VF_MTA_PUBLISHED_RUN','VF_MTA_PUBLISHED_DIGEST',
                'VF_BTR_REPORTING_GENERATION','VF_MTA_PHASE_SELECTION_FILE','VF_MTA_SCOPE_DELIVERY_FILE',
                'VF_MTA_SCOPE_DELIVERY_SHA256','VF_MTA_SCOPE_ARTIFACT_SHA256')) {
            $config.services[$service].environment[$key] = ''
        }
        $config.services[$service].environment.VF_MTA_ALLOW_UNSELECTED_STARTUP = '1'
        $config.services[$service].environment.VF_RUNTIME_REPORT_PUBLISH = '1'
        $mounts = @($config.services[$service].volumes)
        foreach ($mount in $config.services.mta.volumes) {
            if ($mount.target -notin @('/run/secrets','/var/lib/vectorflow') -and $mount.read_only) {
                $mounts = @($mounts | Where-Object { $_.target -ne $mount.target }) + @($mount)
            }
        }
        $mounts = @($mounts | Where-Object { $_.target -notin @('/incoming','/onboarding') })
        $config.services[$service].volumes = $mounts + @(
            @{type='bind';source=$inputRoot;target='/incoming';read_only=$true},
            @{type='bind';source=$binding.DirectoryName;target='/onboarding';read_only=$true})
    }
    Write-VfUtf8 $privateConfig ($config | ConvertTo-Json -Depth 100)
    if ($Reconcile) {
        # Reconciliation verifies existing database ownership and journals the
        # observed cut. It never registers, calculates, stops or starts MTA.
        $result = Worker -Operation 'reconcile'
    } else {
      $null = Worker -Operation 'preflight' -Service 'provision'
      $before = Worker -Operation 'inspect'
      if ($InspectOnly) {
        $result = $before
    } elseif ($before.status -eq 'EXISTING') {
        $result = $before
        $result['message'] = 'Existing published operation retained; no calculation, selection or restart.'
        if ($Resume) {
            # Admit the actual CURRENT selection before touching the service.
            $null = ComposeCall -Arguments @('run','--rm','--no-deps','-T','mta','-m','mta.runtime.csv_scope_operator','serving',
                '--run',$before.run_id,'--selection-digest',$before.selection_digest,'--admission-only') -Json
            $maintenance = $true
            ComposeCall -Arguments @('up','-d','--no-deps','--no-build','--force-recreate','--wait','mta')
            $result = ComposeCall -Arguments @('exec','-T','mta','python','-m','mta.runtime.csv_scope_operator','serving','--run',$before.run_id,
                '--selection-digest',$before.selection_digest) -Json
            $maintenance = $false
        }
    } else {
        # Actual registration follows complete read-only input admission and
        # still precedes any stop. Existing published operations remain reads.
        $null = Worker -Operation 'register' -Service 'provision'
        ComposeCall -Arguments @('stop','mta')
        $maintenance = $true
        $result = Worker -Operation 'execute'
        if ($result.status -ne 'PREPARED') { throw 'Scope/report preparation is incomplete; no serving change' }
        foreach ($key in @($result.environment.Keys)) { $config.services.mta.environment[$key] = $result.environment[$key] }
        # Persist only the public selection configuration, never resolved secrets.
        $servingFile = Join-Path $stateRoot 'vectorflow.scope.json'
        Write-VfUtf8 $servingFile (@{services=@{mta=@{environment=$result.environment}}} | ConvertTo-Json -Depth 20)
        $files = @('compose.yaml')
        $fileLine = @(Get-Content -LiteralPath .env | Where-Object { $_ -match '^\s*COMPOSE_FILE\s*=' })
        if ($fileLine.Count) { $files = (($fileLine[-1] -split '=',2)[1].Trim().Trim('"').Trim("'")) -split ';' }
        $servingPath = $servingFile.Replace('\','/')
        $files = @($files | Where-Object { $_ -ne $servingPath }) + @($servingPath)
        Write-VfEnvironment -Root (Get-Location).Path -Changes @{COMPOSE_PATH_SEPARATOR=';';COMPOSE_FILE=($files -join ';')}
        Write-VfUtf8 $privateConfig ($config | ConvertTo-Json -Depth 100)
        ComposeCall -Arguments @('up','-d','--no-deps','--no-build','--force-recreate','--wait','mta')
        $proof = ComposeCall -Arguments @('exec','-T','mta','python','-m','mta.runtime.csv_scope_operator','serving','--run',$result.run_id,
            '--selection-digest',$result.selection_digest) -Json
        $result = Worker -Operation 'acknowledge' -Run $result.run_id -SelectionDigest $result.selection_digest -Proof ($proof | ConvertTo-Json -Depth 10 -Compress)
        $maintenance = $false
    }
    }
    Write-VfUtf8 $receiptFile ($result | ConvertTo-Json -Depth 100)
    $result | ConvertTo-Json -Depth 100
} catch {
    Write-VfUtf8 $receiptFile (@{status='STOPPED';business_date=$BusinessDate;scope=$Scope;maintenance=$maintenance;error=$_.Exception.Message} | ConvertTo-Json -Depth 20)
    if ($maintenance) {
        try { ComposeCall -Arguments @('stop','mta') } catch { Write-Warning 'Confirm the named MTA service is stopped' }
        Write-Warning 'Preserve this operation; use explicit -Resume only after preparation/serving diagnosis. No calculation retry is automatic.'
    }
    throw
} finally {
    if ($lock) { $lock.Dispose() }
    Remove-Item -LiteralPath $privateConfig -Force -ErrorAction SilentlyContinue
}
