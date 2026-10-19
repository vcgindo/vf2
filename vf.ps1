#requires -Version 7.0
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
Push-Location $PSScriptRoot
try {
    function WriteEnvironment([hashtable]$Changes) {
        $path = Join-Path $PSScriptRoot '.env'
        $text = [IO.File]::ReadAllText($path)
        foreach ($Name in $Changes.Keys) {
            $Value = [string]$Changes[$Name]
            if ($Value -match '[\r\n"$`]') { throw "Unsupported characters in $Name" }
            $pattern = '(?m)^\s*' + [regex]::Escape($Name) + '\s*=.*$'
            $line = $Name + '="' + $Value + '"'
            if ([regex]::IsMatch($text,$pattern)) { $text = [regex]::Replace($text,$pattern,[System.Text.RegularExpressions.MatchEvaluator]{param($m) $line}) }
            else { $text += "`n$line`n" }
        }
        $candidate = Join-Path $PSScriptRoot ('.env.csv-' + [guid]::NewGuid().ToString('N'))
        try {
            [IO.File]::WriteAllText($candidate,$text,[Text.UTF8Encoding]::new($false))
            $diagnostic = & docker compose --env-file $candidate config --quiet 2>&1
            if ($LASTEXITCODE -ne 0) { throw 'Generated CSV environment failed Compose validation; original .env is unchanged' }
            [IO.File]::Replace($candidate,$path,[NullString]::Value)
        } finally { Remove-Item -LiteralPath $candidate -Force -ErrorAction SilentlyContinue }
    }
    $configText = & docker compose --profile daily config --format json
    if ($LASTEXITCODE -ne 0) { throw 'Compose configuration failed' }
    $config = ($configText -join "`n") | ConvertFrom-Json -AsHashtable
    if ($Operation -eq 'csv-day') {
        if (-not $BusinessDate) { throw 'Usage: ./vf.ps1 csv-day YYYY-MM-DD' }
        & "$PSScriptRoot/release/run_daily.ps1" -BusinessDate $BusinessDate -InspectOnly:$InspectOnly -Resume:$Resume
        return
    }
    if ($env:COMPOSE_FILE -or $env:COMPOSE_PATH_SEPARATOR) { throw 'Use .env for Compose file settings; shell overrides would hide the persisted CSV configuration' }
    if ($Operation -eq 'csv-sample') {
        if ($BusinessDate -or $InspectOnly -or $Resume) { throw 'csv-sample takes no date, InspectOnly or Resume argument' }
        $sample = $config['x-vectorflow-csv']['input_dir']
        if (-not $sample) { $sample = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) "VectorFLOW/$($config.name)/csv-input" }
        if (-not [IO.Path]::IsPathFullyQualified($sample)) { throw 'CSV input directory must be absolute' }
        if (Test-Path -LiteralPath $sample) { throw 'CSV directory already exists; use csv-init or reconcile, never overwrite a pack' }
        $parent = (New-Item -ItemType Directory -Force -Path (Split-Path $sample -Parent)).FullName
        $leaf = Split-Path $sample -Leaf
        $helper = Join-Path $PSScriptRoot 'tools/create_daily_csv_example.py'
        $source = Join-Path $PSScriptRoot 'examples/starter-data/vectorflow-starter-inputs-v1.zip'
        & docker compose run --rm --no-deps -T -v "${helper}:/helper.py:ro" -v "${source}:/starter.zip:ro" -v "${parent}:/examples" mta-install /helper.py --source /starter.zip --output "/examples/$leaf" --csv-onboarding
        if ($LASTEXITCODE -ne 0) { throw 'CSV sample creation failed; preserve its directory' }
        if (-not (Test-Path -LiteralPath (Join-Path $sample 'opening/opening-manifest.json'))) { throw 'CSV helper did not produce the opening manifest; preserve its output' }
        WriteEnvironment @{VF_CSV_INPUT_DIR=$sample.Replace('\','/')}
        Write-Output "CSV sample prepared at $sample. No database loading occurred. Next: ./vf.ps1 csv-init"
        return
    }
    if ($BusinessDate -or $InspectOnly -or $Resume) { throw 'csv-init takes no date, InspectOnly or Resume argument' }
    $root = $config['x-vectorflow-csv']['input_dir']
    if (-not $root -or -not [IO.Path]::IsPathFullyQualified($root)) {
        throw 'Set VF_CSV_INPUT_DIR in .env to the absolute CSV pack directory, then rerun ./vf.ps1 csv-init'
    }
    $root = (Resolve-Path -LiteralPath $root).Path.Replace('\','/')
    $state = $config['x-vectorflow-daily']['state_dir']
    if (-not $state) { $state = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) "VectorFLOW/$($config.name)/daily-operations" }
    if (-not [IO.Path]::IsPathFullyQualified($state)) { throw 'Daily state directory must be absolute' }
    $null = New-Item -ItemType Directory -Force -Path $state
    $lock = [IO.File]::Open((Join-Path $state 'daily.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    $receiptPath = Join-Path $state 'onboarding.json'
    try {
        if (Test-Path -LiteralPath $receiptPath) {
            $previous = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
            if ($previous.status -eq 'STOPPED' -and $previous.phase -eq 'CSV') {
                # Only a pre-database format failure may be attempted again.
                Move-Item -LiteralPath $receiptPath -Destination (Join-Path $state ('onboarding-rejected-' + [guid]::NewGuid().ToString('N') + '.json'))
            } else {
                throw "Onboarding already has a receipt at $receiptPath. Do not register/load twice; use csv-day or reconcile the recorded failure."
            }
        }
        $manifest = Join-Path $root 'opening/opening-manifest.json'
        $opening = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json -AsHashtable
        $manifestHash = (Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant()
        $binding = Get-Content -LiteralPath (Join-Path $root 'binding-template.json') -Raw | ConvertFrom-Json -AsHashtable
        foreach ($entry in @(@('opening',$opening.native_input_sha256), @('consumer_opening',$binding.consumer_opening_sha256))) {
            $prefix,$expected = $entry
            $relative = $binding[$prefix + '_file']
            if (-not $relative -or [IO.Path]::IsPathFullyQualified($relative) -or $relative -match '(^|[/\\])\.\.([/\\]|$)') {
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
        $receipt = @{status='VALIDATING';phase='CSV';input_dir=$root;manifest_sha256=$manifestHash;project=$config.name}
        function SaveReceipt { $receipt | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $receiptPath -Encoding utf8 }
        function Compose([string[]]$Arguments, [switch]$Json) {
            $text = & docker compose @Arguments 2>> (Join-Path $state 'onboarding-docker.log')
            $code = $LASTEXITCODE
            if ($text) { Add-Content -LiteralPath (Join-Path $state 'onboarding-docker.log') -Value $text }
            if ($code -ne 0) { throw "Docker operation failed (exit $code); see $state/onboarding-docker.log and onboarding.json" }
            if ($Json) { return ($text -join "`n") | ConvertFrom-Json -AsHashtable }
        }
        SaveReceipt
        try {
            $initArguments = @('run','--rm','--no-deps','-T','-v',"${root}:/input:ro",'mta-install','manage.py','initialize_production','/input/opening','--csv',
                '--sha256',$manifestHash,'--configuration-digest',$opening.configuration_digest,'--recipe-digest',$opening.recipe_digest)
            $validated = Compose -Arguments ($initArguments + '--validate-only') -Json
            if ($validated.status -ne 'INPUT_VALIDATED_NO_DATABASE_CHANGE' -or $validated.input_sha256 -ne $opening.native_input_sha256) {
                throw 'CSV pack validation did not confirm the bound native input'
            }
            $receipt.phase='REGISTRATION'; SaveReceipt
            Compose -Arguments @('stop','mta')
            $registration = Compose -Arguments @('run','--rm','--no-deps','-T','provision','-m','release.register_mta','--input-sha256',$opening.native_input_sha256) -Json
            $receipt.registration = $registration; $receipt.phase='INITIALIZATION'; SaveReceipt
            $null = Compose -Arguments ($initArguments + '--inspect') -Json
            $initial = Compose -Arguments $initArguments -Json
            if ($initial.status -ne 'INITIALIZED' -or $initial.input_sha256 -ne $opening.native_input_sha256) { throw 'Expected one NEW matching initialization' }
            $receipt.initialization=$initial; $receipt.phase='CONFIGURATION'; SaveReceipt
            $binding.initialization_id=$initial.opening_id; $binding.source_digest=$initial.source_digest
            $binding | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath (Join-Path $root 'binding.json') -Encoding utf8
            $access=@{VF_MDM_SOURCE_DIGEST=$initial.source_digest;VF_MTA_PERMISSIONS_FILE='/access/permissions.json';VF_MTA_PERMISSIONS_SHA256=$permissionHash}
            $mount=@{type='bind';source=$permissionFile.Replace('\','/');target='/access/permissions.json';read_only=$true}
            $data=@{services=@{mta=@{environment=$access.Clone();volumes=@($mount)};'mta-install'=@{environment=$access.Clone();volumes=@($mount)}}}
            $override=Join-Path $root 'compose.csv.json'
            $data | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $override -Encoding utf8
            # Preserve the effective existing Compose files instead of replacing overrides.
            WriteEnvironment @{COMPOSE_PATH_SEPARATOR=';';COMPOSE_FILE=($files + ';' + $override.Replace('\','/'));
                VF_DAILY_INPUT_DIR=$root;VF_DAILY_BINDING_FILE="$root/binding.json";
                VF_DAILY_STATE_DIR=$state.Replace('\','/');MTA_SELECTION_FILE='/var/lib/vectorflow/selection.json'}
            $receipt.status='INITIALIZED';$receipt.phase='READY_FOR_FIRST_CSV_DAY'; SaveReceipt
            Write-Output "CSV masters/opening initialized. Run ./vf.ps1 csv-day YYYY-MM-DD. MTA remains stopped until the first day publishes. Receipt: $receiptPath"
        } catch {
            $receipt.status='STOPPED';$receipt.error=$_.Exception.Message; SaveReceipt
            throw
        }
    } finally { $lock.Dispose() }
} finally { Pop-Location }
