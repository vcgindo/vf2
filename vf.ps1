#requires -Version 5.1
<#
Operator entry point: keep Docker/configuration plumbing inside the repository.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory,Position=0)][ValidateSet('csv-sample','csv-init','csv-day')][string]$Operation,
    [Parameter(Position=1)][string]$BusinessDate,
    [switch]$InspectOnly,
    [switch]$Resume
)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
. "$PSScriptRoot/release/powershell_compat.ps1"
Push-Location $PSScriptRoot
try {
    $configText = & docker compose --profile daily config --format json
    if ($LASTEXITCODE -ne 0) { throw 'Compose configuration failed' }
    $config = ConvertFrom-VfJson ($configText -join "`n")
    if ($Operation -eq 'csv-day') {
        if (-not $BusinessDate) { throw 'Usage: ./vf.ps1 csv-day YYYY-MM-DD' }
        & "$PSScriptRoot/release/run_daily.ps1" -BusinessDate $BusinessDate -InspectOnly:$InspectOnly -Resume:$Resume
        return
    }
    if ($env:COMPOSE_FILE -or $env:COMPOSE_PATH_SEPARATOR) { throw 'Use .env for Compose file settings; shell overrides would hide the persisted CSV configuration' }
    if ($Operation -eq 'csv-sample') {
        if ($BusinessDate -or $InspectOnly -or $Resume) { throw 'csv-sample takes no date, InspectOnly or Resume argument' }
        $sample = $config['x-vectorflow-csv']['input_dir']
        if (-not $sample) {
            $sample = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) "VectorFLOW/$($config.name)/csv-input"
            # A fresh clone must not inherit another installation's external
            # pack/receipts simply because it uses the same Compose project name.
            if (Test-Path -LiteralPath $sample) { $sample += '-' + [guid]::NewGuid().ToString('N').Substring(0,8) }
        }
        if (-not (Test-VfAbsolutePath $sample)) { throw 'CSV input directory must be absolute' }
        if (Test-Path -LiteralPath $sample) { throw 'CSV directory already exists; use csv-init or reconcile, never overwrite a pack' }
        $parent = (New-Item -ItemType Directory -Force -Path (Split-Path $sample -Parent)).FullName
        $leaf = Split-Path $sample -Leaf
        $helper = Join-Path $PSScriptRoot 'tools/create_daily_csv_example.py'
        $source = Join-Path $PSScriptRoot 'examples/starter-data/vectorflow-starter-inputs-v1.zip'
        & docker compose run --rm --no-deps -T -v "${helper}:/helper.py:ro" -v "${source}:/starter.zip:ro" -v "${parent}:/examples" mta-install /helper.py --source /starter.zip --output "/examples/$leaf" --csv-onboarding
        if ($LASTEXITCODE -ne 0) { throw 'CSV sample creation failed; preserve its directory' }
        if (-not (Test-Path -LiteralPath (Join-Path $sample 'opening/opening-manifest.json'))) { throw 'CSV helper did not produce the opening manifest; preserve its output' }
        $changes = @{VF_CSV_INPUT_DIR=$sample.Replace('\','/')}
        if (-not $config['x-vectorflow-daily']['state_dir']) { $changes.VF_DAILY_STATE_DIR=$sample.Replace('\','/') + '-operations' }
        Write-VfEnvironment -Root $PSScriptRoot -Changes $changes
        Write-Output "CSV sample prepared at $sample. No database loading occurred. Next: ./vf.ps1 csv-init"
        return
    }
    if ($BusinessDate -or $InspectOnly) { throw 'csv-init takes no date or InspectOnly argument; -Resume only completes an existing opening' }
    $root = $config['x-vectorflow-csv']['input_dir']
    if (-not $root -or -not (Test-VfAbsolutePath $root)) {
        throw 'Set VF_CSV_INPUT_DIR in .env to the absolute CSV pack directory, then rerun ./vf.ps1 csv-init'
    }
    $root = (Resolve-Path -LiteralPath $root).Path.Replace('\','/')
    $state = $config['x-vectorflow-daily']['state_dir']
    if (-not $state) { $state = $root + '-operations' }
    if (-not (Test-VfAbsolutePath $state)) { throw 'Daily state directory must be absolute' }
    $null = New-Item -ItemType Directory -Force -Path $state
    $lock = [IO.File]::Open((Join-Path $state 'daily.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    $receiptPath = Join-Path $state 'onboarding.json'
    try {
        $resumeReceipt = $null
        if (Test-Path -LiteralPath $receiptPath) {
            $previous = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
            if ($previous.status -eq 'STOPPED' -and $previous.phase -eq 'CSV') {
                # Only a pre-database format failure may be attempted again.
                Move-Item -LiteralPath $receiptPath -Destination (Join-Path $state ('onboarding-rejected-' + [guid]::NewGuid().ToString('N') + '.json'))
            } elseif ($Resume -and ($previous.registration -or $previous.phase -eq 'REGISTRATION')) {
                $resumeReceipt = ConvertFrom-VfJson (Get-Content -LiteralPath $receiptPath -Raw)
            } else {
                throw "Onboarding already has a receipt at $receiptPath. Do not register/load twice. For an initialized opening before any daily work use csv-init -Resume; for another installation use a separate VF_DAILY_STATE_DIR and an unbound CSV pack. Daily failures use csv-day."
            }
        }
        if ($Resume -and -not $resumeReceipt) { throw '-Resume requires the recorded existing initialization; no database changes performed' }
        if (-not $resumeReceipt -and (Test-Path -LiteralPath (Join-Path $root 'binding.json'))) { throw 'CSV pack is already bound to an installation. Preserve it; use that installation receipt or a new csv-sample directory for a fresh installation.' }
        $manifest = Join-Path $root 'opening/opening-manifest.json'
        $opening = ConvertFrom-VfJson (Get-Content -LiteralPath $manifest -Raw)
        $manifestHash = (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant()
        $binding = ConvertFrom-VfJson (Get-Content -LiteralPath (Join-Path $root 'binding-template.json') -Raw)
        foreach ($entry in @(@('opening',$opening.native_input_sha256), @('consumer_opening',$binding.consumer_opening_sha256))) {
            $prefix,$expected = $entry
            $relative = $binding[$prefix + '_file']
            if (-not $relative -or (Test-VfAbsolutePath $relative) -or $relative -match '(^|[/\\])\.\.([/\\]|$)') {
                throw 'Invalid onboarding reference'
            }
            $hash = (Get-FileHash -LiteralPath (Join-Path $root $relative) -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($hash -ne $expected -or $binding[$prefix + '_sha256'] -ne $expected) { throw "Onboarding original checksum differs: $prefix" }
        }
        if ($binding.configuration_digest -ne $opening.configuration_digest) { throw 'Opening and daily configuration differ' }
        $permissionFile = Join-Path $root 'permissions.json'
        $permissionHash = (Get-FileHash -LiteralPath $permissionFile -Algorithm SHA256).Hash.ToLowerInvariant()
        $null = Get-Content -LiteralPath $permissionFile -Raw | ConvertFrom-Json
        $lines = @(Get-Content -LiteralPath .env | Where-Object { $_ -match '^\s*COMPOSE_FILE\s*=' })
        $files = if ($lines.Count) { ($lines[-1] -split '=',2)[1].Trim().Trim('"').Trim("'") } else { 'compose.yaml' }
        $separatorLines = @(Get-Content -LiteralPath .env | Where-Object { $_ -match '^\s*COMPOSE_PATH_SEPARATOR\s*=' })
        if ($separatorLines.Count -and ($separatorLines[-1] -split '=',2)[1].Trim().Trim('"').Trim("'") -ne ';') { throw 'Windows Compose path separator must be ;' }
        $packPins = @{'binding-template.json'=(Get-FileHash -LiteralPath (Join-Path $root 'binding-template.json') -Algorithm SHA256).Hash.ToLowerInvariant();'permissions.json'=$permissionHash}
        $receipt = @{status='VALIDATING';phase='CSV';input_dir=$root;manifest_sha256=$manifestHash;project=$config.name;pack_pins=$packPins}
        function SaveReceipt { Write-VfUtf8 $receiptPath ($receipt | ConvertTo-Json -Depth 30) }
        function Compose([string[]]$Arguments, [switch]$Json, [string]$InputText) {
            $preference = $ErrorActionPreference
            try {
                $ErrorActionPreference = 'Continue'
                if ($PSBoundParameters.ContainsKey('InputText')) {
                    $text = $InputText | & docker compose @Arguments 2>> (Join-Path $state 'onboarding-docker.log')
                } else { $text = & docker compose @Arguments 2>> (Join-Path $state 'onboarding-docker.log') }
                $code = $LASTEXITCODE
            } finally { $ErrorActionPreference = $preference }
            if ($text) { Add-Content -LiteralPath (Join-Path $state 'onboarding-docker.log') -Value $text }
            if ($code -ne 0) { throw "Docker operation failed (exit $code); see $state/onboarding-docker.log and onboarding.json" }
            if ($Json) { return ConvertFrom-VfJson ($text -join "`n") }
        }
        $helper = Join-Path $PSScriptRoot 'release/csv_onboarding.py'
        if ($resumeReceipt) {
            if ($resumeReceipt.manifest_sha256 -ne $manifestHash -or $resumeReceipt.project -ne $config.name -or
                ($resumeReceipt.pack_pins -and (($resumeReceipt.pack_pins['binding-template.json'] -ne $packPins['binding-template.json']) -or
                    ($resumeReceipt.pack_pins['permissions.json'] -ne $packPins['permissions.json'])))) { throw 'Receipt pack/project differs; no changes performed' }
            $receipt = $resumeReceipt
        }
        SaveReceipt
        try {
            # One repository-owned process parses once, writes all families,
            # certifies, then activates. It records committed checkpoints itself.
            $initializeArguments = @('run','--rm','--no-deps','-T','-v',"${state}:/onboarding",'-v',"${root}:/input:ro",
                'provision','-m','release.initialize_csv','--input-directory','/input','--manifest-sha256',$manifestHash,
                '--configuration-digest',$opening.configuration_digest,'--recipe-digest',$opening.recipe_digest,
                '--receipt','/onboarding/onboarding.json')
            if ($resumeReceipt) { $initializeArguments += '--resume' }
            $receipt = Compose -Arguments $initializeArguments -Json
            $initial = $receipt.initialization
            if (-not $initial -or $receipt.families.status -ne 'MDM_FAMILIES_READY' -or $initial.input_sha256 -ne $opening.native_input_sha256) {
                throw 'Native initialization/certification did not complete'
            }
            Compose -Arguments @('stop','mta')
            $receipt.phase='CONFIGURATION'; SaveReceipt
            $binding.initialization_id=$initial.opening_id; $binding.source_digest=$initial.source_digest
            Write-VfUtf8 (Join-Path $root 'binding.json') ($binding | ConvertTo-Json -Depth 100)
            $access=@{VF_MDM_SOURCE_DIGEST=$initial.source_digest;VF_MTA_PERMISSIONS_FILE='/access/permissions.json';VF_MTA_PERMISSIONS_SHA256=$permissionHash}
            $mount=@{type='bind';source=$permissionFile.Replace('\','/');target='/access/permissions.json';read_only=$true}
            $data=@{services=@{mta=@{environment=$access.Clone();volumes=@($mount)};'mta-install'=@{environment=$access.Clone();volumes=@($mount)}}}
            $override=Join-Path $root 'compose.csv.json'
            Write-VfUtf8 $override ($data | ConvertTo-Json -Depth 8)
            # Preserve the effective existing Compose files instead of replacing overrides.
            $fileList = @($files -split ';' | Where-Object { $_ -ne $override.Replace('\','/') })
            Write-VfEnvironment -Root $PSScriptRoot -Changes @{COMPOSE_PATH_SEPARATOR=';';COMPOSE_FILE=(($fileList + $override.Replace('\','/')) -join ';');
                VF_DAILY_INPUT_DIR=$root;VF_DAILY_BINDING_FILE="$root/binding.json";
                VF_DAILY_STATE_DIR=$state.Replace('\','/');MTA_SELECTION_FILE=''}
            $receipt.phase='MASTER_SERVING'; SaveReceipt
            Compose -Arguments @('up','-d','--no-deps','--no-build','--wait','mta')
            $receipt.serving = Compose -Arguments @('exec','-T','mta','python','-','check') -InputText ([IO.File]::ReadAllText($helper)) -Json
            if ($receipt.serving.status -ne 'INITIALIZED_MASTER_SERVING_READY') { throw 'Initialized master serving did not pass' }
            $receipt.Remove('error')
            $receipt.status='INITIALIZED';$receipt.phase='READY_FOR_FIRST_CSV_DAY'; SaveReceipt
            Write-Output "CSV masters/opening initialized. Run ./vf.ps1 csv-day YYYY-MM-DD. MTA is serving all initialized MDM families; calculated reports become available after day one. Receipt: $receiptPath"
        } catch {
            # The driver may have committed a checkpoint before failing. Never
            # overwrite its receipt with the launcher's older in-memory copy.
            $failureMessage=$_.Exception.Message
            if (Test-Path -LiteralPath $receiptPath) { $receipt=ConvertFrom-VfJson (Get-Content -LiteralPath $receiptPath -Raw) }
            $receipt.status='STOPPED';$receipt.error=$failureMessage; SaveReceipt
            throw
        }
    } finally { $lock.Dispose() }
} finally { Pop-Location }
