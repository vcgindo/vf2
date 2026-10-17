# Windows deployment runbook

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

Reinstall **only the 8080 trial** at `I:/VectorFLOW-Trial` using the corrected `bd309169` package. Run each step manually, in order, in the same PowerShell session.

- **1. Prepare Windows** — Start Docker Desktop in Linux-container mode. Check that Python 3 and the approved source ZIP/runtime archive are available.
- **2. Remove the old trial** — Remove its six containers, eight volumes and network; archive its folder. **This permanently deletes the trial databases and accounts. The folder archive is not a database backup.** Other deployments and Docker images stay untouched.

<details>
<summary>Show cleanup commands</summary>

```powershell
$ErrorActionPreference = 'Stop'
$TrialRoot = [IO.Path]::GetFullPath('I:/VectorFLOW-Trial')
if ($TrialRoot.TrimEnd('\','/') -ne 'I:\VectorFLOW-Trial') {
  throw 'Unexpected absolute cleanup root'
}
if (-not (Test-Path -LiteralPath "$TrialRoot/operator.env" -PathType Leaf)) {
  throw 'Original trial folder not found; do not guess another target'
}
$TrialProject = 'vectorflow-localtrial'
$TrialNetwork = 'vectorflow-localtrial_application'
$ExpectedServices = @('auth','mta','frontend','mto','postgres','redis')
$ExpectedVolumes = @(
  'vectorflow-localtrial_auth_data',
  'vectorflow-localtrial_auth_logs',
  'vectorflow-localtrial_mta_data',
  'vectorflow-localtrial_mto_data',
  'vectorflow-localtrial_mto_downloads',
  'vectorflow-localtrial_mto_logs',
  'vectorflow-localtrial_postgres_data',
  'vectorflow-localtrial_redis_data'
)
function Invoke-TrialDocker {
  $OutputLines = & docker @args
  if ($LASTEXITCODE -ne 0) { throw 'Docker command failed; stop and inspect' }
  $OutputLines
}
$TrialContainerIds = @(Invoke-TrialDocker ps -aq --filter "label=com.docker.compose.project=$TrialProject")
if ($TrialContainerIds.Count -ne 6) { throw 'Expected exactly six trial containers' }
$TrialContainers = @(Invoke-TrialDocker inspect @TrialContainerIds | ConvertFrom-Json)
$ActualServices = @($TrialContainers | ForEach-Object { $_.Config.Labels.'com.docker.compose.service' })
if (Compare-Object ($ExpectedServices | Sort-Object) ($ActualServices | Sort-Object)) {
  throw 'Unexpected service roster'
}
$ActualVolumes = @(Invoke-TrialDocker volume ls -q --filter "label=com.docker.compose.project=$TrialProject")
if (Compare-Object ($ExpectedVolumes | Sort-Object) ($ActualVolumes | Sort-Object)) {
  throw 'Unexpected volume roster'
}
$VolumeRows = @(Invoke-TrialDocker volume inspect @ExpectedVolumes | ConvertFrom-Json)
foreach ($VolumeRow in $VolumeRows) {
  if ($VolumeRow.Labels.'com.docker.compose.project' -ne $TrialProject) {
    throw 'Volume ownership differs'
  }
}
$NetworkRows = @(Invoke-TrialDocker network inspect $TrialNetwork | ConvertFrom-Json)
if ($NetworkRows.Count -ne 1 -or $NetworkRows[0].Labels.'com.docker.compose.project' -ne $TrialProject) {
  throw 'Network ownership differs'
}
$AllContainerIds = @(Invoke-TrialDocker ps -aq)
$AllContainers = @(Invoke-TrialDocker inspect @AllContainerIds | ConvertFrom-Json)
foreach ($ContainerRow in $AllContainers) {
  if ($ContainerRow.Config.Labels.'com.docker.compose.project' -eq $TrialProject) { continue }
  $SharedVolumes = @($ContainerRow.Mounts | Where-Object { $_.Type -eq 'volume' -and $_.Name -in $ExpectedVolumes })
  $SharedNetwork = @($ContainerRow.NetworkSettings.Networks.PSObject.Properties.Name) -contains $TrialNetwork
  if ($SharedVolumes.Count -gt 0 -or $SharedNetwork) {
    throw "Another container references trial resources: $($ContainerRow.Name)"
  }
}
$TrialContainers | Select-Object Name, @{Name='Service';Expression={$_.Config.Labels.'com.docker.compose.service'}}
$ExpectedVolumes
$TrialNetwork
if ((Read-Host 'Permanently delete this trial database, accounts and files? Type DESTROY-8080') -cne 'DESTROY-8080') {
  throw 'Cleanup cancelled'
}
# Exact validated container IDs only; no other project's container is selected.
Invoke-TrialDocker container stop --time 30 @TrialContainerIds
Invoke-TrialDocker container rm @TrialContainerIds
Invoke-TrialDocker volume rm @ExpectedVolumes
Invoke-TrialDocker network rm $TrialNetwork

# Verify removal. A partial failure is a stop, not permission for global cleanup.
if (@(Invoke-TrialDocker ps -aq --filter "label=com.docker.compose.project=$TrialProject").Count) {
  throw 'Trial containers remain'
}
if (@(Invoke-TrialDocker volume ls -q --filter "label=com.docker.compose.project=$TrialProject").Count) {
  throw 'Trial volumes remain'
}
if (@(Invoke-TrialDocker network ls -q --filter "label=com.docker.compose.project=$TrialProject").Count) {
  throw 'Trial network remains'
}
if (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue) {
  throw '8080 is still occupied; identify its owner, do not kill an unrelated process'
}

# Preserve original sources/operator files/secrets privately, rather than delete them.
# Resolve both absolute paths and require the same intended parent before moving.
$TrialParent = Split-Path -Parent $TrialRoot
$RetiredRoot = [IO.Path]::GetFullPath((Join-Path $TrialParent ("VectorFLOW-Trial.retired-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))))
if ((Split-Path -Parent $RetiredRoot) -ne $TrialParent -or $RetiredRoot -eq $TrialRoot -or (Test-Path -LiteralPath $RetiredRoot)) {
  throw 'Unsafe or existing archive destination'
}
Set-Location -LiteralPath $TrialParent
Move-Item -LiteralPath $TrialRoot -Destination $RetiredRoot
Write-Host "Old folder preserved at $RetiredRoot; it contains private secrets, not a database backup."
```

</details>

- **3. Extract the package** — Verify its hashes, extract to the new folder and load the images. Copy only the old network override; do not reuse old image or upgrade overrides.

<details>
<summary>Show package commands</summary>

```powershell
$PackageDirectory = 'D:/freshvcf-build/evidence/handoff3005-s2-20261013-001/s4-deployment-gap-implementation-20261017'
$SourceZip = Join-Path $PackageDirectory 'vectorflow-stage4-source-bd309169.zip'
$RuntimeArchive = Join-Path $PackageDirectory 'export-bd309169/vectorflow-stage4-runtime.tar.gz'
if ((Get-FileHash -LiteralPath $SourceZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne '2afce44024bad553249fb38dbfb4796b38a77cd56b2bb318b82c29a4d5a807ad') {
  throw 'Source ZIP differs'
}
if ((Get-FileHash -LiteralPath $RuntimeArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne '8d5d2c5db40c3cac9a5b4cf7f14faade8afc37e82a376953c4eeb5c338790520') {
  throw 'Runtime archive differs'
}
if (Test-Path -LiteralPath $TrialRoot) { throw 'Fresh destination already exists' }
Expand-Archive -LiteralPath $SourceZip -DestinationPath $TrialRoot
Copy-Item -LiteralPath $RuntimeArchive -Destination "$TrialRoot/vectorflow-stage4-runtime.tar.gz"
# Reuse the known local subnet configuration, NOT an old image/upgrade override.
Copy-Item -LiteralPath "$RetiredRoot/network-local.yaml" -Destination "$TrialRoot/network-local.yaml"
$SourceManifest = Get-Content -Raw -LiteralPath "$TrialRoot/release-source.json" | ConvertFrom-Json
if ($SourceManifest.source_commit -ne 'bd309169b8f494ed8c93f47302327d74c341923b') {
  throw 'Wrong release'
}
Invoke-TrialDocker load --input "$TrialRoot/vectorflow-stage4-runtime.tar.gz"
```

</details>

The copied subnet is `198.18.57.0/28`. Check `docker network ls/inspect` and `Get-NetRoute` for overlap before reusing it. Do not prune networks or change Docker daemon settings.

- **4. Create settings and secrets** — Generate new private keys/passwords. Keep the public cipher that matches the unchanged frontend. Use the new package's `loaded-images.yaml`.

<details>
<summary>Show configuration commands</summary>

```powershell
$PublicBuild = Get-Content -Raw -LiteralPath "$TrialRoot/public-build.json" | ConvertFrom-Json
$RuntimeImages = Get-Content -Raw -LiteralPath "$TrialRoot/runtime-images.json" | ConvertFrom-Json
$PrivateRoot = New-Item -ItemType Directory -Path "$TrialRoot/private" -ErrorAction Stop
$OperatorIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $PrivateRoot.FullName /inheritance:r /grant:r "${OperatorIdentity}:(OI)(CI)F"
if ($LASTEXITCODE) { throw 'Private directory ACL setup failed' }
Invoke-TrialDocker run --rm --network none --user 0:0 --entrypoint python --mount "type=bind,src=$($PrivateRoot.FullName),dst=/private" $RuntimeImages.services.auth.image_id -m release.prepare_secrets --directory /private/secrets --public-client-cipher-key $PublicBuild.client_cipher_key
Copy-Item -LiteralPath "$TrialRoot/release/.env.example" -Destination "$TrialRoot/operator.env"
# Edit only the new operator configuration, not application code.
$OperatorLines = @(Get-Content -LiteralPath "$TrialRoot/operator.env")
$TrialSettings = @{
  VF_PROJECT = 'vectorflow-localtrial'
  VF_RELEASE = 'bd309169b8f494ed8c93f47302327d74c341923b'
  VF_SECRETS_DIR = "$TrialRoot/private/secrets"
  VF_CLIENT_CIPHER_KEY = $PublicBuild.client_cipher_key
  VF_BIND_ADDRESS = '127.0.0.1'
  VF_HTTP_PORT = '8080'
  VF_PUBLIC_URL = 'http://127.0.0.1:8080'
  VF_PUBLIC_WS_URL = 'ws://127.0.0.1:8080'
}
foreach ($SettingName in $TrialSettings.Keys) {
  $Pattern = '^' + [regex]::Escape($SettingName) + '='
  if (@($OperatorLines | Where-Object { $_ -match $Pattern }).Count -ne 1) {
    throw "Missing or duplicate setting: $SettingName"
  }
  $OperatorLines = @($OperatorLines | ForEach-Object {
    if ($_ -match $Pattern) { "$SettingName=$($TrialSettings[$SettingName])" } else { $_ }
  })
  # Compose shell environment overrides its env file. Remove stale values for this session.
  Remove-Item -LiteralPath "Env:$SettingName" -ErrorAction SilentlyContinue
}
$OperatorLines | Set-Content -LiteralPath "$TrialRoot/operator.env" -Encoding utf8
```

</details>

- **5. Install and start** — Run preflight, create the empty databases, apply migrations and metadata grants, then create a new administrator. **Stop at the first failure; do not rerun provisioning over a partial install.**

<details>
<summary>Show installation commands</summary>

```powershell
function vf {
  & docker compose --project-name vectorflow-localtrial --env-file "$TrialRoot/operator.env" `
    -f "$TrialRoot/release/compose.yaml" -f "$TrialRoot/loaded-images.yaml" `
    -f "$TrialRoot/network-local.yaml" @args
  if ($LASTEXITCODE) { throw 'Compose failed; stop at this step and preserve the failure' }
}
python "$TrialRoot/release/preflight.py" --source-root $TrialRoot --env-file "$TrialRoot/operator.env" `
  --compose-file "$TrialRoot/release/compose.yaml" --compose-file "$TrialRoot/loaded-images.yaml" `
  --compose-file "$TrialRoot/network-local.yaml"
if ($LASTEXITCODE) { throw 'Preflight refused; do not provision' }
vf config --quiet
vf up -d --wait postgres redis
vf --profile install run --rm --no-deps provision -m release.provision
vf --profile install run --rm --no-deps provision -m release.provision --apply
vf --profile install run --rm --no-deps mta-install manage.py migrate --plan
vf --profile install run --rm --no-deps mta-install manage.py migrate --noinput
vf --profile install run --rm --no-deps auth-install manage.py migrate --noinput
vf --profile install run --rm --no-deps mto-install manage.py migrate --noinput
vf --profile install run --rm --no-deps auth-install -m release.install_identity
vf --profile install run --rm --no-deps provision -m release.grant_service AUTH
vf --profile install run --rm --no-deps provision -m release.grant_service MTO
vf --profile install run --rm --no-deps provision -m release.metadata_access
vf --profile install run --rm --no-deps provision -m release.metadata_access --apply
vf --profile install run --rm --no-deps auth-install manage.py createsuperuser
vf up -d --wait mta auth mto frontend
vf ps
Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8080/healthz'
Start-Process 'http://127.0.0.1:8080'
```

</details>

- **6. Sign in** — Open `http://127.0.0.1:8080` with the new administrator. The old `trial` account no longer exists.
- **7. Check the installation** — MDM family definitions should load. Health returns200. Readiness remains503 until publication. BPR/Planning may retain their original unavailable views because no business data has been loaded.
- **8. Stop here** — Sample loading, initialization, daily runs, publication and recovery testing belong to Step Five.

<details>
<summary>Show status and logs</summary>

```powershell
vf ps
vf logs --tail 50 mta auth
Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8080/healthz'
```

</details>

<details>
<summary>Optional: clone the pinned source instead of using its ZIP</summary>

```powershell
$SourceRoot = 'I:/VectorFLOW-Source'
$ExportRoot = 'I:/VectorFLOW-Export'
$ApprovedCommit = 'bd309169b8f494ed8c93f47302327d74c341923b'
git clone https://github.com/yurtse/freshvcf.git $SourceRoot
if ($LASTEXITCODE) { throw 'Clone failed' }
git -C $SourceRoot checkout --detach $ApprovedCommit
if ($LASTEXITCODE) { throw 'Pinned checkout failed' }
python "$SourceRoot/release/export.py" --repository $SourceRoot --revision $ApprovedCommit --output $ExportRoot
if ($LASTEXITCODE) { throw 'Export failed' }
```

Use new source/export folders. The export also needs the approved runtime archive and its `runtime-images.json`, `loaded-images.yaml` and `public-build.json` companions from the delivered package. Git does not contain Docker image layers. Step3's ZIP already supplies those companions.

</details>

**Quick checks**

- Missing `VF_RELEASE`: set it in `operator.env` and clear a conflicting shell value.
- Port8080 busy: identify its owner; do not terminate another deployment.
- Docker address pools exhausted: review the subnet override. This is not a port conflict.
- Accounts: no default users are installed. Create the administrator in Step5; ordinary users need real roles/scopes.
- Secrets: keep `private` restricted to the Windows operator. Keep passwords and private keys out of Git.
- Scope: only this trial may be removed/recreated. Frontend/MTO code and images stay unchanged.

[Ubuntu / public VPS checklist](OPERATIONS_REFERENCE.md#ubuntu--public-vps-checklist) — includes the public-origin stop condition and HTTPS commands.

[Operating commands, optional inputs, backup/restore and upgrade details](OPERATIONS_REFERENCE.md).
