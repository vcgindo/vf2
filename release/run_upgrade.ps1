#requires -Version 5.1
<#
Upgrade an existing populated installation without intake, calculation or report replay.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
#>
[CmdletBinding()]
param([switch]$Build, [string]$Image, [switch]$InspectOnly, [switch]$Resume, [string]$BackupDirectory)
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $false
. "$PSScriptRoot/powershell_compat.ps1"
if ($Build -and $Image) { throw 'Choose -Build or -Image, never both' }
if (-not $Resume -and -not $Build -and -not $Image) { throw 'Usage: ./vf.ps1 upgrade -Build (or -Image supplied-image)' }
if ($env:COMPOSE_FILE -or $env:COMPOSE_PATH_SEPARATOR) { throw 'Keep Compose configuration in the existing private .env; shell overrides are unsupported' }
$projectRoot = (Get-Location).Path
$privateConfig = $null
$lock = $null
$journal = $null
$journalPath = $null
$operationRoot = $null
$ownsJournal = $false
function DockerCall([string[]]$Arguments, [switch]$Json) {
    $start = New-Object Diagnostics.ProcessStartInfo
    $start.FileName = 'docker'; $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true; $start.RedirectStandardError = $true
    $start.WorkingDirectory = $projectRoot
    Set-VfProcessArguments $start $Arguments
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $start; $null = $process.Start()
    $outTask = $process.StandardOutput.ReadToEndAsync(); $errTask = $process.StandardError.ReadToEndAsync()
    $process.WaitForExit()
    $text = $outTask.GetAwaiter().GetResult(); $diagnostic = $errTask.GetAwaiter().GetResult()
    $code = $process.ExitCode; $process.Dispose()
    # Resolved config can contain secrets. Never log its contents or command arguments.
    if ($operationRoot -and $Arguments -notcontains 'config' -and $Arguments -notcontains 'inspect') {
        Add-Content -LiteralPath (Join-Path $operationRoot 'commands.log') -Encoding utf8 -Value ($text + "`n" + $diagnostic + "`nEXIT=$code")
    }
    if ($code -ne 0) { throw "Upgrade Docker operation failed (exit $code); preserve the upgrade journal and diagnostics" }
    if ($Json) { return ConvertFrom-VfJson $text }
    return $text.Trim()
}
function ComposeCall([string[]]$Arguments, [switch]$Json) {
    return DockerCall -Arguments (@('compose','--profile','install','--profile','daily','-f',$privateConfig) + $Arguments) -Json:$Json
}
function SaveJournal {
    $temporary = $journalPath + '.tmp'
    Write-VfUtf8 $temporary ($journal | ConvertTo-Json -Depth 60)
    if (Test-Path -LiteralPath $journalPath) { [IO.File]::Replace($temporary,$journalPath,[NullString]::Value) }
    else { [IO.File]::Move($temporary,$journalPath) }
}
function WriteSnapshot { Write-VfUtf8 $privateConfig ($config | ConvertTo-Json -Depth 100) }
function UpgradeFileHash([string]$Path) {
    # Windows PowerShell 5.1 Get-FileHash cannot open a valid nested backup
    # path at MAX_PATH. Stream the same SHA256 through the extended Win32 path.
    $full = [IO.Path]::GetFullPath($Path)
    if ($full.StartsWith('\\')) { $full = '\\?\UNC\' + $full.Substring(2) }
    else { $full = '\\?\' + $full }
    $stream = [IO.File]::OpenRead($full)
    $hash = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($hash.ComputeHash($stream)).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $hash.Dispose() }
}
function BackupFiles([string]$Root) {
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { throw 'Physical upgrade backup directory is missing' }
    $result = @{}
    foreach ($file in Get-ChildItem -LiteralPath $Root -Recurse -Force) {
        if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Physical backup cannot contain symbolic links' }
        if (-not $file.PSIsContainer) {
            $name = Get-VfRelativePath $Root $file.FullName
            if ($name -notin @('base.tar.gz','pg_wal.tar.gz','backup_manifest') -or $file.Length -eq 0) {
                throw 'Unsupported physical backup file/tablespace layout; dedicated cluster prerequisites require diagnosis'
            }
            $result[$name] = @{bytes=$file.Length;sha256=(UpgradeFileHash $file.FullName)}
        }
    }
    if (-not $result.ContainsKey('base.tar.gz') -or -not $result.ContainsKey('backup_manifest')) { throw 'Physical cluster backup is incomplete' }
    return $result
}
function ApplicationFiles([string]$Root) {
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) { throw 'Matching application recovery files are missing' }
    $result = @{}
    foreach ($file in Get-ChildItem -LiteralPath $Root -Recurse -Force) {
        if ($file.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Application backup cannot contain symbolic links' }
        if (-not $file.PSIsContainer) {
            $name = Get-VfRelativePath $Root $file.FullName
            $result[$name] = @{bytes=$file.Length;sha256=(UpgradeFileHash $file.FullName)}
        }
    }
    foreach ($name in @('original.env','binding.json','compose.original.private.json','mta-work/selection.json')) {
        if (-not $result.ContainsKey($name)) { throw 'Matching application recovery files are incomplete' }
    }
    return $result
}
function CaptureApplicationBackup {
    $root = $journal.application_directory
    foreach ($name in $journal.original_files.Keys) {
        $path = Join-Path $root $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or
            (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $journal.original_files[$name]) {
            throw 'Original private recovery files changed after inspection'
        }
    }
    # A harmless same-image restart between inspection and maintenance can
    # replace the container ID. Reconcile its actual image after stopping it.
    $container = ComposeCall -Arguments @('ps','-a','-q','mta')
    if (-not $container) { throw 'Stopped MTA is missing; preserve backup and diagnose' }
    $old = @(DockerCall -Arguments @('inspect',$container) -Json)[0]
    if ($old.State.Running -or $old.Image -ne $journal.previous_image) { throw 'Original MTA must be stopped before its recovery files are captured' }
    $work = Join-Path $root 'mta-work'
    if (Test-Path -LiteralPath $work) { throw 'Unreceipted MTA work backup exists; preserve and diagnose it' }
    $null = New-Item -ItemType Directory -Path $work
    $null = DockerCall -Arguments @('cp',($container + ':/var/lib/vectorflow/.'),$work)
    return @{path=$root;files=(ApplicationFiles $root)}
}
function VerifyBackup {
    $backup = $journal.backup
    if ($backup.format -ne 'postgres-basebackup-tar-gzip-fetch-v1' -or $backup.project -ne $journal.project -or
        $backup.initialization -ne $journal.initialization -or $backup.previous_image -ne $journal.previous_image) {
        throw 'Existing upgrade backup ownership/format differs'
    }
    $application = ApplicationFiles $backup.application.path
    if ($application.Count -ne $backup.application.files.Count) { throw 'Application backup file roster changed' }
    foreach ($name in $application.Keys) {
        if (-not $backup.application.files.ContainsKey($name) -or $application[$name].bytes -ne $backup.application.files[$name].bytes -or
            $application[$name].sha256 -ne $backup.application.files[$name].sha256) { throw 'Application backup file bytes changed' }
    }
    $actual = BackupFiles $backup.path
    if ($actual.Count -ne $backup.files.Count) { throw 'Physical backup file roster changed' }
    foreach ($name in $actual.Keys) {
        if (-not $backup.files.ContainsKey($name) -or $actual[$name].bytes -ne $backup.files[$name].bytes -or
            $actual[$name].sha256 -ne $backup.files[$name].sha256) { throw 'Physical backup file bytes changed' }
    }
}
function SaveDeploymentEnvironment([string]$Files) {
    $path = Join-Path $projectRoot '.env'
    $text = [IO.File]::ReadAllText($path)
    foreach ($entry in @(@('COMPOSE_FILE',$Files),@('COMPOSE_PATH_SEPARATOR',';'))) {
        $name,$value = $entry
        if ($value -match '[\r\n"$`]') { throw 'Unsupported Compose path characters' }
        $line = $name + '="' + $value + '"'
        $pattern = '(?m)^\s*' + $name + '\s*=.*$'
        if ([regex]::IsMatch($text,$pattern)) { $text = [regex]::Replace($text,$pattern,[Text.RegularExpressions.MatchEvaluator]{param($m) $line}) }
        else { $text += "`n$line`n" }
    }
    $candidate = Join-Path $projectRoot ('.env.upgrade-' + [guid]::NewGuid().ToString('N'))
    try {
        Write-VfUtf8 $candidate $text
        $null = DockerCall -Arguments @('compose','--profile','install','--profile','daily','--env-file',$candidate,'config','--quiet')
        [IO.File]::Replace($candidate,$path,[NullString]::Value)
    } finally { Remove-Item -LiteralPath $candidate -Force -ErrorAction SilentlyContinue }
}
function DatabasePhase([string]$Phase) {
    $null = ComposeCall -Arguments @('run','--rm','--no-deps','-T','-v',"${operationRoot}:/upgrade",'provision',
        '-m','release.upgrade_database','--phase',$Phase,'--initialization',$journal.initialization,
        '--previous-release','/upgrade/previous-native.json','--receipt','/upgrade/database.json')
    $receipt = ConvertFrom-VfJson ([IO.File]::ReadAllText((Join-Path $operationRoot 'database.json')))
    $expected = @{inspect='UPGRADE_DATABASE_INSPECTED';apply='UPGRADE_DATABASE_APPLIED';verify='UPGRADE_DATABASE_VERIFIED'}[$Phase]
    if ($receipt.status -ne $expected -and -not ($Phase -eq 'verify' -and $receipt.status -eq 'UPGRADE_DATABASE_APPLY_REQUIRED')) {
        throw "Database $Phase did not reach its required checkpoint"
    }
    return $receipt
}
try {
    # Profile resolution starts no service and includes all installer references.
    $config = DockerCall -Arguments @('compose','--profile','install','--profile','daily','config','--format','json') -Json
    $daily = $config['x-vectorflow-daily']
    if (-not $daily.state_dir -or -not $daily.binding_file) { throw 'Upgrade requires the existing daily state and binding configuration' }
    $stateRoot = Resolve-VfProjectPath $projectRoot $daily.state_dir
    $bindingFile = Resolve-VfProjectPath $projectRoot $daily.binding_file
    $binding = ConvertFrom-VfJson ([IO.File]::ReadAllText($bindingFile))
    $bindingHash = (Get-FileHash -LiteralPath $bindingFile -Algorithm SHA256).Hash.ToLowerInvariant()
    if (-not $binding.initialization_id) { throw 'Existing initialization binding required; upgrade never initializes data' }
    $null = New-Item -ItemType Directory -Force -Path $stateRoot
    $lock = [IO.File]::Open((Join-Path $stateRoot 'daily.lock'),'OpenOrCreate','ReadWrite','None')
    $journalPath = Join-Path $stateRoot 'upgrade.json'
    if (Test-Path -LiteralPath $journalPath) {
        $journal = ConvertFrom-VfJson ([IO.File]::ReadAllText($journalPath))
        if ($journal.project -ne $config.name -or $journal.initialization -ne $binding.initialization_id) { throw 'Upgrade journal belongs to another installation' }
        if ($Resume) {
            if ($journal.binding_sha256 -ne $bindingHash) { throw 'Resume initialization binding bytes differ' }
            if ($Image -and $Image -ne $journal.requested_image -and $Image -ne $journal.target_image) { throw 'Resume target differs from the admitted upgrade' }
            if ($BackupDirectory -and (Resolve-VfProjectPath $projectRoot $BackupDirectory) -ne $journal.backup_directory) { throw 'Resume backup location differs' }
            $ownsJournal = $true
        } elseif ($journal.status -eq 'COMPLETE') {
            Write-VfUtf8 (Join-Path $journal.operation_root 'completed-journal.json') ($journal | ConvertTo-Json -Depth 60)
            $journal = $null
        } else { throw 'Upgrade already has a journal; use -Resume after diagnosis, never readmit it' }
    } elseif ($Resume) { throw '-Resume requires an existing upgrade journal' }
    if (-not $journal) {
        $operationRoot = Join-Path $stateRoot ('upgrade-' + [guid]::NewGuid().ToString('N'))
        $null = New-Item -ItemType Directory -Path $operationRoot
        $journal = @{schema='vectorflow-upgrade-v1';status='ADMITTED';phase='ADMISSION';project=$config.name;
            initialization=$binding.initialization_id;operation_root=$operationRoot;requested_image=$Image;
            build=[bool]$Build;maintenance=$false;apply_started=$false;applied=$false;binding_sha256=$bindingHash}
        $sourcePrefix = [IO.Path]::GetFullPath($projectRoot).TrimEnd([char[]]'\/') + [IO.Path]::DirectorySeparatorChar
        $defaultBackup = $operationRoot
        if ([IO.Path]::GetFullPath($operationRoot).StartsWith($sourcePrefix,[StringComparison]::OrdinalIgnoreCase)) {
            # A normal installation keeps operations under data/operations.
            # Select an external sibling automatically, without operator wiring.
            $defaultBackup = Join-Path (Join-Path (Split-Path $projectRoot -Parent) ($config.name + '-backups')) (Split-Path $operationRoot -Leaf)
        }
        $journal.backup_directory = if ($BackupDirectory) { Resolve-VfProjectPath $projectRoot $BackupDirectory } else { $defaultBackup }
        $backupPrefix = [IO.Path]::GetFullPath($journal.backup_directory).TrimEnd([char[]]'\/') + [IO.Path]::DirectorySeparatorChar
        if ($backupPrefix.StartsWith($sourcePrefix,[StringComparison]::OrdinalIgnoreCase)) {
            throw 'Keep production backups outside the source distribution; configure external operations storage or pass -BackupDirectory'
        }
        # Only inspect an actual existing running MTA before any unique-tag build.
        $mta = DockerCall -Arguments @('compose','--profile','install','--profile','daily','ps','-q','mta')
        if (-not $mta) { throw 'Existing running MTA required for new upgrade admission' }
        $running = @(DockerCall -Arguments @('inspect',$mta) -Json)[0]
        if (-not $running.State.Running -or $running.Image -notmatch '^sha256:[0-9a-f]{64}$') { throw 'Cannot authenticate current running MTA image' }
        $journal.previous_image = $running.Image
        $journal.previous_container = $mta
        # Retain the original private deployment before source-image overrides.
        # These recovery files are never printed and stay outside Git.
        $journal.application_directory = Join-Path $journal.backup_directory ('application-' + (Split-Path $operationRoot -Leaf))
        $null = New-Item -ItemType Directory -Force -Path $journal.application_directory
        Write-VfUtf8 (Join-Path $journal.application_directory 'compose.original.private.json') ($config | ConvertTo-Json -Depth 100)
        [IO.File]::Copy((Join-Path $projectRoot '.env'),(Join-Path $journal.application_directory 'original.env'),$false)
        [IO.File]::Copy($bindingFile,(Join-Path $journal.application_directory 'binding.json'),$false)
        $journal.original_files = @{}
        foreach ($name in @('compose.original.private.json','original.env','binding.json')) {
            $journal.original_files[$name] = (Get-FileHash -LiteralPath (Join-Path $journal.application_directory $name) -Algorithm SHA256).Hash.ToLowerInvariant()
        }
        $journal.retained_services = @{}
        foreach ($service in @('frontend','auth','mto')) {
            if ($config.services[$service]) {
                $container = DockerCall -Arguments @('compose','--profile','install','--profile','daily','ps','-q',$service)
                if (-not $container) { throw "Existing $service must remain running" }
                $retained = @(DockerCall -Arguments @('inspect',$container) -Json)[0]
                if (-not $retained.State.Running -or $retained.Image -notmatch '^sha256:[0-9a-f]{64}$') { throw "Cannot authenticate existing $service image" }
                $journal.retained_services[$service] = @{container=$container;image=$retained.Image}
            }
        }
        $journal.target_tag = if ($Build) { $config.name + '/mta:upgrade-' + [guid]::NewGuid().ToString('N') } else { $Image }
        $ownsJournal = $true
        SaveJournal
    }
    $operationRoot = $journal.operation_root
    if (-not (Test-Path -LiteralPath $operationRoot -PathType Container)) { throw 'Upgrade artifacts are missing; refusing reconstruction' }
    $privateConfig = Join-Path $operationRoot 'compose.private.json'
    # Existing native source authentication is retained for the original producer.
    $inspectCode = "import json,pathlib,runpy; p=pathlib.Path('/opt/vectorflow/image_entrypoint.py'); runpy.run_path(str(p))['configure']() if p.is_file() else None; from release.native_identity import require_current; print(json.dumps(require_current(),sort_keys=True))"
    if (-not (Test-Path -LiteralPath (Join-Path $operationRoot 'previous-native.json'))) {
        $previous = DockerCall -Arguments @('run','--rm','--network','none','--entrypoint','python',$journal.previous_image,'-c',$inspectCode) -Json
        Write-VfUtf8 (Join-Path $operationRoot 'previous-native.json') ($previous | ConvertTo-Json -Depth 60)
    }
    $previousNativeHash = (Get-FileHash -LiteralPath (Join-Path $operationRoot 'previous-native.json') -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($journal.previous_native_sha256 -and $journal.previous_native_sha256 -ne $previousNativeHash) { throw 'Original authenticated native descriptor was changed' }
    $journal.previous_native_sha256 = $previousNativeHash
    SaveJournal
    if (-not $journal.target_image) {
        if ($journal.build) {
            $config.services.mta.image = $journal.target_tag
            # Persisted deployment overrides may retain a deleted source folder
            # from an earlier handoff. -Build owns the current checkout's MTA
            # recipe; it must not inherit that historical build context.
            $config.services.mta.build = @{context=$projectRoot;dockerfile='release/compose.Dockerfile';target='mta'}
            WriteSnapshot
            $null = ComposeCall -Arguments @('build','mta')
        }
        $target = @(DockerCall -Arguments @('image','inspect',$journal.target_tag) -Json)[0]
        if ($target.Id -notmatch '^sha256:[0-9a-f]{64}$') { throw 'Target image must be available locally with an immutable identity' }
        $journal.target_image = $target.Id
        SaveJournal
    }
    $native = DockerCall -Arguments @('run','--rm','--network','none','--entrypoint','python',$journal.target_image,
        '/opt/vectorflow/image_entrypoint.py','python','-c',"from pathlib import Path; print(Path('/app/release-native-source.json').read_text())") -Json
    if ($journal.target_commit -and $journal.target_commit -ne $native.source_commit) { throw 'Target source identity differs from admitted image' }
    $journal.target_commit = $native.source_commit
    Write-VfUtf8 (Join-Path $operationRoot 'target-native.json') ($native | ConvertTo-Json -Depth 60)
    # Preserve all service settings and mounts; change only MTA-family image ownership.
    foreach ($service in @('mta','daily','mta-install','provision')) {
        if (-not $config.services[$service]) { throw "Required existing service missing: $service" }
        $config.services[$service].image = $journal.target_image
        $config.services[$service].pull_policy = 'never'
        foreach ($key in @('VF_NATIVE_RELEASE_COMMIT','VF_NATIVE_RELEASE_SHA256','VF_SOURCE_MANIFEST_SHA256')) {
            $config.services[$service].environment[$key] = 'image'
        }
    }
    $config.services.provision.entrypoint = @('python','/opt/vectorflow/image_entrypoint.py')
    WriteSnapshot
    SaveJournal
    $databaseFile = Join-Path $operationRoot 'database.json'
    $database = if (Test-Path -LiteralPath $databaseFile) { ConvertFrom-VfJson ([IO.File]::ReadAllText($databaseFile)) } else { $null }
    if ($journal.backup) {
        VerifyBackup
    }
    if ($journal.apply_started -or $database.status -in @('UPGRADE_DATABASE_APPLIED','UPGRADE_DATABASE_VERIFIED')) {
        # A lost post-commit response is reconciled from actual DB state by the
        # read-only helper. Failure never causes automatic application replay.
        $database = DatabasePhase 'verify'
        if ($database.status -eq 'UPGRADE_DATABASE_APPLY_REQUIRED') {
            if (-not $Resume) { throw 'Database proved an atomic rollback; inspect evidence then explicitly resume the upgrade' }
            $journal.applied = $false
            $journal.apply_started = $false
        } else { $journal.applied = $true }
    } else {
        $database = DatabasePhase 'inspect'
    }
    if (-not $database.selected.run_id -or -not $database.selected.output_digest) { throw 'Populated selected run/output required for upgrade serving proof' }
    if ($journal.selected -and (($journal.selected.run_id -ne $database.selected.run_id) -or
        ($journal.selected.output_digest -ne $database.selected.output_digest) -or
        ($journal.selected.business_date -ne $database.selected.business_date))) { throw 'Selected publication differs from admitted upgrade' }
    $journal.selected = $database.selected
    $journal.phase = if ($journal.applied) { 'DATABASE_VERIFIED' } else { 'INSPECTED' }
    SaveJournal
    if ($InspectOnly) {
        if ($journal.maintenance) { throw 'Upgrade is in maintenance; inspection does not release it' }
        $journal.status='INSPECTED'; SaveJournal
        Write-Output "Upgrade inspected. Existing MTA remains active. Continue with ./vf.ps1 upgrade -Resume. Journal: $journalPath"
        return
    }
    if (-not $journal.applied) {
        $journal.maintenance=$true; $journal.phase='MAINTENANCE'; SaveJournal
        $null = ComposeCall -Arguments @('stop','mta')
        if ($journal.backup) {
            VerifyBackup
        } else {
            $null = New-Item -ItemType Directory -Force -Path $journal.backup_directory
            $backupPath = Join-Path $journal.backup_directory ('postgres-' + (Split-Path $operationRoot -Leaf))
            if (Test-Path -LiteralPath $backupPath) { throw 'Unreceipted backup exists; preserve and diagnose it' }
            $remote = '/tmp/vectorflow-backup-' + [guid]::NewGuid().ToString('N')
            $admin = $config.services.provision.environment.PG_ADMIN_USER
            $databaseName = $config.services.provision.environment.MTA_DB_NAME
            if (-not $admin -or -not $databaseName) { throw 'Existing PostgreSQL admin/database configuration required' }
            try {
                $null = ComposeCall -Arguments @('exec','-T','postgres','sh','-ec',
                    'export PGPASSWORD="$(cat "$POSTGRES_PASSWORD_FILE")"; pg_basebackup --host=127.0.0.1 --username="$1" --format=tar --gzip --wal-method=fetch --checkpoint=fast --pgdata="$2" --no-password',
                    'upgrade-backup',$admin,$remote)
            } catch { throw 'Physical PostgreSQL backup failed. Verify existing replication/WAL/tablespace prerequisites; no logical-dump fallback or settings change is permitted.' }
            $postgres = ComposeCall -Arguments @('ps','-q','postgres')
            if (-not $postgres) { throw 'Existing PostgreSQL container missing' }
            $null = DockerCall -Arguments @('cp',($postgres + ':' + $remote),$backupPath)
            $backupFiles = BackupFiles $backupPath
            $applicationBackup = CaptureApplicationBackup
            $journal.backup = @{path=$backupPath;files=$backupFiles;application=$applicationBackup;format='postgres-basebackup-tar-gzip-fetch-v1';
                recovery='Offline coordinated restore of this dedicated PostgreSQL cluster with its MTA work/configuration/secrets; never restore automatically';
                database=$databaseName;project=$journal.project;initialization=$journal.initialization;previous_image=$journal.previous_image}
            $journal.phase='BACKED_UP'; SaveJournal
        }
        $journal.apply_started=$true; $journal.phase='APPLYING'; SaveJournal
        $database = DatabasePhase 'apply'
        $journal.applied=$true; $journal.phase='DATABASE_APPLIED'; SaveJournal
    }
    if (-not $journal['settings_adopted']) {
        $journal.phase='SETTINGS_ADOPTION'; SaveJournal
        $settingsAdoption = ComposeCall -Arguments @('run','--rm','--no-deps','-T','mta-install',
            '-m','release.execution_settings_command','adopt') -Json
        if ($settingsAdoption.status -ne 'ADOPTED') { throw 'Exact current settings adoption did not complete' }
        $journal['settings_adopted']=$true; $journal['settings']=$settingsAdoption.settings; SaveJournal
        $database = DatabasePhase 'verify'
        if ($database.status -ne 'UPGRADE_DATABASE_VERIFIED') { throw 'Settings adoption did not preserve the accepted installation' }
    }
    # One fixed image override; preserve the original private Compose file list.
    $deployment = Join-Path $stateRoot 'compose.deployment.json'
    if (-not $journal.deployment_saved) {
        $imageServices = @{}
        foreach ($service in @('mta','daily','mta-install','provision')) {
            $imageServices[$service] = @{image=$journal.target_image;pull_policy='never';environment=@{
                VF_NATIVE_RELEASE_COMMIT='image';VF_NATIVE_RELEASE_SHA256='image';VF_SOURCE_MANIFEST_SHA256='image'}}
        }
        foreach ($service in $journal.retained_services.Keys) {
            $imageServices[$service] = @{image=$journal.retained_services[$service].image;pull_policy='never'}
        }
        $previousDeployment = Join-Path $operationRoot 'previous-deployment.json'
        if ((Test-Path -LiteralPath $deployment) -and -not (Test-Path -LiteralPath $previousDeployment)) { [IO.File]::Copy($deployment,$previousDeployment,$false) }
        Write-VfUtf8 $deployment (@{services=$imageServices} | ConvertTo-Json -Depth 12)
        $envText = [IO.File]::ReadAllText((Join-Path $projectRoot '.env'))
        $match = [regex]::Matches($envText,'(?m)^\s*COMPOSE_FILE\s*=(.*)$')
        $files = if ($match.Count) { $match[$match.Count-1].Groups[1].Value.Trim().Trim('"').Trim("'") } else { 'compose.yaml' }
        $separatorMatch = [regex]::Matches($envText,'(?m)^\s*COMPOSE_PATH_SEPARATOR\s*=(.*)$')
        if ($separatorMatch.Count -and $separatorMatch[$separatorMatch.Count-1].Groups[1].Value.Trim().Trim('"').Trim("'") -ne ';') { throw 'Windows Compose path separator must remain ;' }
        $deploymentPath = $deployment.Replace('\','/')
        $fileList = @($files -split ';' | Where-Object { $_.Replace('\','/') -ne $deploymentPath })
        SaveDeploymentEnvironment (($fileList + $deploymentPath) -join ';')
        $journal.deployment_saved=$true; $journal.phase='DEPLOYMENT_SAVED'; SaveJournal
    }
    $null = ComposeCall -Arguments @('up','-d','--no-deps','--no-build','--force-recreate','--wait','mta')
    $container = ComposeCall -Arguments @('ps','-q','mta')
    $actual = @(DockerCall -Arguments @('inspect',$container) -Json)[0]
    if (-not $actual.State.Running -or $actual.Image -ne $journal.target_image) { throw 'Running MTA does not use the admitted immutable target image' }
    $journal.phase='SERVING_CHECK'; SaveJournal
    $proof = ComposeCall -Arguments @('exec','-T','mta','python','-m','release.daily_serving_check',
        '--run-id',$journal.selected.run_id,'--output-digest',$journal.selected.output_digest) -Json
    if (-not $proof.ready -or $proof.run_id -ne $journal.selected.run_id -or $proof.output_digest -ne $journal.selected.output_digest) { throw 'Upgraded MTA did not prove the existing selected run/output' }
    foreach ($service in $journal.retained_services.Keys) {
        $container = ComposeCall -Arguments @('ps','-q',$service)
        if ($container -ne $journal.retained_services[$service].container) { throw "Protected $service container changed during upgrade" }
        $retained = @(DockerCall -Arguments @('inspect',$container) -Json)[0]
        if (-not $retained.State.Running -or $retained.Image -ne $journal.retained_services[$service].image) { throw "Protected $service image changed during upgrade" }
    }
    $journal.serving=$proof; $journal.maintenance=$false; $journal.status='COMPLETE'; $journal.phase='COMPLETE'
    $journal.Remove('error'); SaveJournal
    Write-Output "MTA upgrade complete; selected business data retained. Journal: $journalPath"
} catch {
    $failure = $_
    if ($ownsJournal -and $journal -and $journalPath -and $operationRoot) {
        $journal.status='STOPPED'; $journal.error=$_.Exception.Message
        SaveJournal
        if ($journal.maintenance -and $privateConfig -and (Test-Path -LiteralPath $privateConfig)) {
            try { $null = ComposeCall -Arguments @('stop','mta') } catch { Write-Warning 'Could not confirm MTA stopped; inspect its existing container.' }
        }
    }
    throw $failure
} finally {
    if ($lock) { $lock.Dispose() }
    if ($privateConfig) { Remove-Item -LiteralPath $privateConfig -Force -ErrorAction SilentlyContinue }
}
