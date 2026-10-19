# Windows: deploy the blank production application, then load data separately

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

For repository-owned CSV daily processing after onboarding, see [CSV_DAILY_RUN.md](CSV_DAILY_RUN.md). It reuses the native calculation and presentation preparation; no daily work occurs during installation.

This replaces the historical bd309169/8080 destructive reinstall procedure. Run each numbered step manually, in order, in the same PowerShell session on a NEW target. Stop at the first failure and retain its output. Do not reset, reprovision, adopt an old installation or replay an accepted day.

**Part A is deployment:** six prebuilt production components, empty application schemas, system metadata, a new administrator and normal authenticated access. It stops before business registration, master/opening ingestion, daily calculation or publication. **Part B is optional data onboarding and daily operation.** Business reports need data; a blank installation must not fabricate report results.

The administrator created by the current installer has full page/action permissions and dynamic data access across MTA and MTO. Gateway requests use all IDs in the current per-application permission catalogue for that authenticated administrator; they do not require manually seeded product/location/order grants. This is included in images built from the corrected source, not retroactively added to an older immutable package. Ordinary users retain explicit roles and data scopes. Empty applications still have no report rows, and an unavailable catalogue fails with503. Do not rerun blank installation to repair an existing administrator: update only the auth/gateway image to the verified version while preserving its environment, credentials and volumes. Frontend and MTO images remain unchanged.

**Acceptance status:** the initialized connected application/workflows/cold recovery passed Step5. These blank-install commands have source, syntax and configuration checks. The HUMAN OPERATOR must execute and validate the blank six-component installation; that runtime checkpoint remains PENDING. Static checks are not a fresh-install PASS.

## A. Deploy and validate a blank installation

### 1. Obtain the final runtime and current Windows documentation

Use Windows with Docker Desktop in Linux/amd64 mode, Compose v2, Python3 and PowerShell. Declared running-service RAM caps total approximately8.25GiB, plus Docker/Windows overhead; provide disk for images, volumes, logs and backups. These are small-data limits, not production-volume sizing.

- Runtime: `vectorflow-step5-local-3c1dcf93.zip`,494874161bytes; SHA256 `7fb66c10bbcfa5dfb8c71df21f82390f46951398838081a2a2f0dbecac6b9056`.
- Current documentation companion or the current remote documentation commit: this runbook, `windows-final-release.json`, `windows-final-images.yaml` and final handoff. Check the companion's independently supplied ZIP hash before extracting it into `$DocsRoot`.
- Optional raw-input ZIP: named and pinned in `windows-final-release.json`. Keep it unopened throughout Part A. It contains synthetic raw masters/opening, two supplied days and matching scope catalogue; no account, password, database or calculated output.

Keep the runtime ZIP immutable. Its enclosed handoff predates final archive verification; the current companion records the subsequent PASS. Use THIS runbook instead of the old runbook inside its source ZIP. Git contains documentation/source, not Docker layers or private backups. No application rebuild is needed.

```powershell
$ErrorActionPreference = 'Stop'
$InstallRoot = [IO.Path]::GetFullPath('C:/VectorFLOW-Clean')
$DocsRoot = [IO.Path]::GetFullPath('C:/Transfers/vectorflow-step5-windows-docs')
$RuntimeZip = 'C:/Transfers/vectorflow-step5-local-3c1dcf93.zip'
$Release = Get-Content -Raw -LiteralPath "$DocsRoot/release/windows-final-release.json" | ConvertFrom-Json
$ImageOverridePath = "$DocsRoot/release/windows-final-images.yaml"
if (Test-Path -LiteralPath $InstallRoot) { throw 'Use a NEW directory; do not overwrite' }
if ((Get-FileHash -LiteralPath $RuntimeZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Release.runtime_archive_sha256) { throw 'Runtime ZIP differs' }
New-Item -ItemType Directory -Path $InstallRoot | Out-Null
$BundleRoot = Join-Path $InstallRoot 'bundle'
$AppRoot = Join-Path $InstallRoot 'source'
$PrivateRoot = Join-Path $InstallRoot 'private'
$ReceiptsRoot = Join-Path $InstallRoot 'receipts'
Expand-Archive -LiteralPath $RuntimeZip -DestinationPath $BundleRoot
python "$BundleRoot/verify-package.py"
if ($LASTEXITCODE -ne 0) { throw 'Package verification failed' }
$SourceZip = Join-Path $BundleRoot $Release.source_archive
if ((Get-FileHash -LiteralPath $SourceZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Release.source_archive_sha256) { throw 'Source ZIP differs' }
Expand-Archive -LiteralPath $SourceZip -DestinationPath $AppRoot
New-Item -ItemType Directory -Path $PrivateRoot,$ReceiptsRoot | Out-Null
function Invoke-VFDocker {
  $Result = & docker @args
  if ($LASTEXITCODE -ne 0) { throw 'Docker failed: stop and preserve the command/output' }
  $Result
}
Invoke-VFDocker info --format '{{.OSType}}/{{.Architecture}}'
Invoke-VFDocker compose version
# Require Linux/amd64 (Docker may spell it linux/x86_64).
Invoke-VFDocker load --input "$BundleRoot/runtime-images.tar.gz"
foreach ($Property in $Release.images.PSObject.Properties) {
  $Actual = Invoke-VFDocker image inspect $Property.Value --format '{{.Id}}'
  if ($Actual -ne $Property.Value) { throw "Wrong loaded image: $($Property.Name)" }
}
```

The component revisions intentionally differ: MTA9e312c04, frontend3c1dcf93, authb4e4baf6, unchanged MTO bd309169, PostgreSQL16.15 and Redis7.4. Never substitute the documentation commit for a runtime/native identity. Preserve the extracted source bytes; installer helpers use this verified source, not an arbitrary checkout.

### 2. Generate private secrets and configure the new target

Choose the installation host port in `VF_HTTP_PORT` in the private env file; the default is8080. Compose maps that variable to frontend container port80. HTTP API/download paths are relative to the browser origin. The retained frontend's MTO WebSocket origin, however, is compiled as `ws://127.0.0.1:8080`: selecting another port changes the HTTP listener and public URL, but does not rewrite that WebSocket origin. Full MTO socket use at a different port requires a separately approved matching frontend artifact from unchanged source. This documentation does not build/change frontend or MTO. Public HTTPS/WSS additionally needs destination/TLS decisions.

The supplied `public_client_cipher_key` is intentionally PUBLIC configuration compiled into the browser. Auth must match it. It is not a database/signing/RSA secret. Generate new private values below; never copy the existing trial's secrets or accounts.

```powershell
$OperatorIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $PrivateRoot /inheritance:r /grant:r "${OperatorIdentity}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F'
if ($LASTEXITCODE -ne 0) { throw 'Private ACL setup failed' }
Invoke-VFDocker run --rm --network none --user 0:0 --entrypoint python `
  --mount "type=bind,source=$PrivateRoot,target=/private" $Release.images.auth `
  -m release.prepare_secrets --directory /private/secrets --public-client-cipher-key $Release.public_client_cipher_key
$OperatorFile = Join-Path $PrivateRoot 'operator.env'
Copy-Item -LiteralPath "$BundleRoot/operator.env.template" -Destination $OperatorFile
notepad $OperatorFile
```

Set `VF_HTTP_PORT` to your free host port (1–65535), save and close the editor before continuing. Leave `VF_BIND_ADDRESS=127.0.0.1` for this local build. Edit the env file rather than Compose or application code.

```powershell
$PortLine = @(Get-Content -LiteralPath $OperatorFile | Where-Object { $_ -match '^VF_HTTP_PORT=' })
if ($PortLine.Count -ne 1) { throw 'One VF_HTTP_PORT setting is required' }
[int]$HttpPort = 0
if (-not [int]::TryParse(($PortLine[0] -split '=',2)[1], [ref]$HttpPort) -or $HttpPort -lt 1 -or $HttpPort -gt 65535) { throw 'Invalid VF_HTTP_PORT' }
$PublicUrl = "http://127.0.0.1:$HttpPort"
function Set-OperatorValue([string]$Name, [string]$Value) {
  $Lines = @(Get-Content -LiteralPath $script:OperatorFile)
  $Pattern = '^' + [regex]::Escape($Name) + '='
  if (@($Lines | Where-Object { $_ -match $Pattern }).Count -ne 1) { throw "Missing/duplicate setting: $Name" }
  $Lines = @($Lines | ForEach-Object { if ($_ -match $Pattern) { "$Name=$Value" } else { $_ } })
  [IO.File]::WriteAllLines($script:OperatorFile, $Lines, [Text.UTF8Encoding]::new($false))
}
$Project = 'vectorflow-clean'
$Settings = @{
  VF_PROJECT=$Project; VF_RELEASE=$Release.code_commit
  VF_NATIVE_RELEASE_COMMIT=$Release.component_sources.mta
  VF_NATIVE_RELEASE_SHA256=$Release.native_manifest_sha256
  VF_SOURCE_MANIFEST_SHA256=$Release.mta_source_manifest_sha256
  VF_SECRETS_DIR=(Join-Path $PrivateRoot 'secrets').Replace('\','/')
  VF_CLIENT_CIPHER_KEY=$Release.public_client_cipher_key
  VF_BIND_ADDRESS='127.0.0.1'
  VF_PUBLIC_URL=$PublicUrl; VF_PUBLIC_WS_URL="ws://127.0.0.1:$HttpPort"
  MTA_WORKERS='1'
  MTA_SELECTION_FILE=''; MTA_PERMISSIONS_FILE=''; MTA_PERMISSIONS_SHA256=''
  MTA_HIERARCHY_FILE=''; MTA_HIERARCHY_SHA256=''
}
foreach ($Name in $Settings.Keys) { Set-OperatorValue $Name $Settings[$Name] }
# Clear only keys declared in this new env file in this PowerShell session:
# shell environment otherwise overrides Compose's operator file.
foreach ($Line in Get-Content -LiteralPath $OperatorFile) {
  if ($Line -match '^([A-Z][A-Z0-9_]*)=') { Remove-Item -LiteralPath "Env:$($Matches[1])" -ErrorAction SilentlyContinue }
}
$ComposeArguments = @('--project-name',$Project,'--env-file',$OperatorFile,
  '-f',"$AppRoot/release/compose.yaml",'-f',$ImageOverridePath)
$DataComposeFile = $null
function vf {
  $DockerArguments = @('compose') + $script:ComposeArguments
  if ($script:DataComposeFile) { $DockerArguments += @('-f',$script:DataComposeFile) }
  $DockerArguments += $args
  $InputLines = @($input)
  if ($InputLines.Count) {
    $Result = $InputLines | & docker @DockerArguments
    if ($LASTEXITCODE -ne 0) { throw 'Docker failed: stop and preserve the command/output' }
    $Result
  } else { Invoke-VFDocker @DockerArguments }
}
```

The override pins all six runtime services AND four installer profiles, including provision. MTA installer/daily workers run sequentially with the serving MTA stopped; the current Compose files and image override impose no CPU/memory/swap ceiling. Keep default separate `vectorflow_mta` / `vectorflow_mto` logical databases and service roles on this new cluster. Auth has a separate identity schema in the MTO database. No frontend/MTO source or image change is involved.

The current Git configuration removes resource-test defaults; historical immutable delivery archives and running installations are not rewritten. Use the current configuration files when applying this updated resource policy. Docker/host allocations still bound available compute. Worker counts, timeouts, security and application behavior remain unchanged.

### 3. Verify configuration and absence before creation

```powershell
vf config --quiet
vf --profile install config --images
$Configuration = vf --profile install config --format json | ConvertFrom-Json
$Expected = @{}
foreach ($Property in $Release.images.PSObject.Properties) { $Expected[$Property.Name]=$Property.Value }
$Expected['mta-install']=$Release.images.mta
$Expected['auth-install']=$Release.images.auth
$Expected['mto-install']=$Release.images.mto
$Expected['provision']=$Release.images.mta
foreach ($Name in $Expected.Keys) {
  if ($Configuration.services.$Name.image -ne $Expected[$Name]) { throw "Wrong image: $Name" }
}
foreach ($Secret in $Configuration.secrets.PSObject.Properties) {
  if (-not (Test-Path -LiteralPath $Secret.Value.file -PathType Leaf)) { throw "Missing secret: $($Secret.Name)" }
}
if (Get-NetTCPConnection -LocalPort $HttpPort -State Listen -ErrorAction SilentlyContinue) { throw 'Chosen VF_HTTP_PORT occupied; do not replace another deployment' }
if (@(Invoke-VFDocker ps -aq --filter "label=com.docker.compose.project=$Project").Count) { throw 'Project containers exist; do not adopt/reset' }
if (@(Invoke-VFDocker volume ls -q --filter "label=com.docker.compose.project=$Project").Count) { throw 'Project volumes exist; do not adopt/reset' }
if (@(Invoke-VFDocker network ls -q --filter "label=com.docker.compose.project=$Project").Count) { throw 'Project network exists; do not adopt/reset' }
```

Do not run the older single-source `release.preflight` build gate against contradictory source3c1/MTA9e pins. This composite release is checked using the immutable archive/source and each prebuilt component's own identity. Docker allocates the new project's network; address-pool/host-route conflicts require explicit subnet review, not copying old networks or restarting/pruning Docker.

### 4. Install empty schemas and system metadata only

```powershell
vf up --no-build --pull never -d --wait postgres redis
vf --profile install run --rm --no-deps provision -m release.provision
vf --profile install run --rm --no-deps provision -m release.provision --apply
vf --profile install run --rm --no-deps mta-install manage.py check --database default
vf --profile install run --rm --no-deps mta-install manage.py migrate --plan
vf --profile install run --rm --no-deps mta-install manage.py migrate --noinput
vf --profile install run --rm --no-deps auth-install manage.py migrate --noinput
vf --profile install run --rm --no-deps mto-install manage.py migrate --noinput
vf --profile install run --rm --no-deps auth-install -m release.install_identity
# grant_service is an operator helper, excluded from the minimal MTA runtime.
# Mount just that verified file outside /app for this offline provisioner.
$GrantHelper = "$AppRoot/release/grant_service.py"
vf --profile install run --rm --no-deps -v "${GrantHelper}:/operator/grant_service.py:ro" provision /operator/grant_service.py AUTH
vf --profile install run --rm --no-deps -v "${GrantHelper}:/operator/grant_service.py:ro" provision /operator/grant_service.py MTO
vf --profile install run --rm --no-deps provision -m release.metadata_access
vf --profile install run --rm --no-deps provision -m release.metadata_access --apply
```

Provisioning refuses existing names; never repeat it over a partial install. Identity installation creates application/permission/feature/configuration definitions only. Do not run `seed_users_and_roles`, restore development data or register MTA against a dummy input hash. Business registration belongs in Part B, when the real opening input exists.

Set bounded defaults ONLY for the two MTA login roles in their new DB; no global or other-role timeout change:

```powershell
@'
ALTER ROLE vectorflow_mta_runtime IN DATABASE vectorflow_mta SET idle_in_transaction_session_timeout='300s';
ALTER ROLE vectorflow_mta_runtime IN DATABASE vectorflow_mta SET statement_timeout='300s';
ALTER ROLE vectorflow_mta_runtime IN DATABASE vectorflow_mta SET lock_timeout='5s';
ALTER ROLE vectorflow_mta_installer IN DATABASE vectorflow_mta SET idle_in_transaction_session_timeout='300s';
ALTER ROLE vectorflow_mta_installer IN DATABASE vectorflow_mta SET statement_timeout='300s';
ALTER ROLE vectorflow_mta_installer IN DATABASE vectorflow_mta SET lock_timeout='5s';
'@ | vf exec -T --user postgres postgres psql -U postgres -d postgres -v ON_ERROR_STOP=1
```

### 5. Create the new administrator and start the production services

```powershell
vf --profile install run --rm --no-deps auth-install manage.py createsuperuser
# Supply your own email/name/password and required tc field interactively.
vf up --no-build --pull never -d --wait mta auth mto frontend
vf ps
Invoke-WebRequest -UseBasicParsing "$PublicUrl/healthz"
Start-Process $PublicUrl
```

Complete normal login/CAPTCHA yourself. No default trial, supplier or reviewer is installed. Add ordinary users/roles through existing administration when needed. Keep credentials outside Git/images. Optional auth-worker/auth-beat maintenance profiles are unchanged; they are not a seventh component required to make the six runtime services healthy.

### 6. Validate the BLANK checkpoint, then stop

```powershell
@'
import django,json
django.setup()
from django.db import connection,transaction
from mta.runtime.models import ProductionInitialization,MdmSource,CalculationRun,RunCommand,DailyUiPublication
with transaction.atomic():
 with connection.cursor() as c:c.execute('SET TRANSACTION READ ONLY')
 counts={m.__name__:m.objects.count() for m in (ProductionInitialization,MdmSource,CalculationRun,RunCommand,DailyUiPublication)}
 assert not any(counts.values()),counts
 with connection.cursor() as c:
  c.execute("SELECT to_regclass('fresh_control.owned_namespace')")
  assert c.fetchone()[0] is None,'Blank deployment must not register business inputs'
print(json.dumps({'blank_business_counts':counts,'business_registration':False}))
connection.close()
'@ | vf --profile install run --rm --no-deps -T --entrypoint python mta-install -
@'
import django,urllib.request,urllib.error
django.setup()
from django.db import connection
from mta.presentation.installation_metadata import require_installation
assert require_installation() is None
with connection.cursor() as c:
 c.execute("SELECT current_user,current_database(),current_setting('idle_in_transaction_session_timeout'),current_setting('statement_timeout'),current_setting('lock_timeout')")
 assert c.fetchone()==('vectorflow_mta_runtime','vectorflow_mta','5min','5min','5s')
assert urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=10).status==200
try:
 urllib.request.urlopen('http://127.0.0.1:8000/readyz',timeout=10)
except urllib.error.HTTPError as e:
 assert e.code==503
else:raise AssertionError('Blank target cannot claim a published business generation')
print('PASS installation metadata; no business publication selected')
'@ | vf exec -T mta python -
```

Record actual results in `$ReceiptsRoot`, then report them against the sole handoff tracker:

- Six intended services healthy, exact images selected, only the intended frontend listener published. No backend/PG/Redis host listener.
- New administrator login works; original navigation and MDM family configuration load. No sample users, masters, opening, accepted runs, workflows or publication.
- `/healthz`200 and the finite installation-metadata check PASS. MTA `/readyz` is **503 until publication**. Data-dependent reports/masters remain explicitly unavailable. This is not populated-report acceptance or permission to return invented empty200s.
- Unexpected auth failures, missing installed metadata, crashes,500s or missing required routes are failures to report, not successful deployment because a container is running.
- `vf stop`, then `vf up --no-build --pull never -d --wait` restarts this SAME new project. Login and blank checks still work; it performs no provisioning/migration/import/calculation. Never use `down -v`.

**Part A ends here.** It remains PENDING until you execute and record these checks. Do not include sample loading or daily runs in blank deployment. Functions needing data are verified after the separate data operation.

## B. Optional: load masters/opening, then execute a supplied day

This is a deliberate operator action, not startup. Use the separately pinned raw sample pack or a separately reviewed real onboarding packet. The sample is opening17Oct2026/days18–19Oct2026,200SKU/20location definitions and a small active population, including the already-approved positive shipment/order/consumption facts. No calculated outputs are supplied. Do not change dates/quantities/rules to manufacture eligibility. Historical data can prove loading/calculation/reports; current-date Apply/Sleep/reviewer tests need a date-compatible input/action case.

### 1. Verify real inputs, register their opening hash and initialize once

```powershell
$OptionalZip = Join-Path 'C:/Transfers' $Release.optional_raw_inputs.archive
if ((Get-FileHash -LiteralPath $OptionalZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Release.optional_raw_inputs.sha256) { throw 'Raw input pack differs' }
$InputRoot = Join-Path $PrivateRoot 'inputs'
if (Test-Path -LiteralPath $InputRoot) { throw 'Inputs already exist; do not overwrite' }
Expand-Archive -LiteralPath $OptionalZip -DestinationPath $InputRoot
foreach ($Property in $Release.optional_raw_inputs.files.PSObject.Properties) {
  if ((Get-FileHash -LiteralPath (Join-Path $InputRoot $Property.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Property.Value) { throw "Input differs: $($Property.Name)" }
}
vf stop mta
$NativePins = @('-e',"VF_NATIVE_RELEASE_COMMIT=$($Release.component_sources.mta)",'-e',"VF_NATIVE_RELEASE_SHA256=$($Release.native_manifest_sha256)")
$OpeningHash = $Release.optional_raw_inputs.files.'initialization.json'
$ConfigurationDigest = $Release.optional_raw_inputs.configuration_digest
$RecipeDigest = $Release.optional_raw_inputs.recipe_digest
vf --profile install run --rm --no-deps @NativePins provision -m release.register_mta --input-sha256 $OpeningHash
vf --profile install run --rm --no-deps -v "${InputRoot}:/input:ro" mta-install manage.py initialize_production /input/initialization.json --sha256 $OpeningHash --configuration-digest $ConfigurationDigest --recipe-digest $RecipeDigest --inspect
$InitJson = vf --profile install run --rm --no-deps -v "${InputRoot}:/input:ro" mta-install manage.py initialize_production /input/initialization.json --sha256 $OpeningHash --configuration-digest $ConfigurationDigest --recipe-digest $RecipeDigest
$InitJson | Set-Content -LiteralPath "$ReceiptsRoot/initialization-result.json" -Encoding utf8
$Initialization = $InitJson | ConvertFrom-Json
if ($Initialization.status -ne 'INITIALIZED') { throw 'Expected one new initialization; reconcile before proceeding' }
```

Registration is one-time source/schema/input binding, deferred until real input is supplied. Separate native MTA installations need separate PG clusters because canonical acceptor membership is cluster-wide. No reset/reregistration/reseal or running a different source/image against the old sealed database. Restarts never register or initialize.

### 2. Freeze matching access/source configuration

The sample `permissions.json` is a read-time catalogue, NOT a user grant. Assign appropriate scopes to users on YOUR NEW identity installation through normal administration. Sample product root71001/leaves71002–71003 and location root72001/leaves72002–72004 describe the retained sample; do not add them to unrelated accounts. For production use real authoritative catalogue/actors. Freeze access hash, native hierarchy, timezone/actions and reader flags BEFORE preparation.

```powershell
$PermissionPath = (Join-Path $InputRoot 'permissions.json').Replace('\','/')
$PermissionHash = $Release.optional_raw_inputs.files.'permissions.json'
$SourceDigest = $Initialization.source_digest
$DataComposeFile = Join-Path $PrivateRoot 'data-configuration.yaml'
@"
services:
  mta:
    environment:
      VF_MDM_SOURCE_DIGEST: "$SourceDigest"
      VF_MTA_PERMISSIONS_FILE: /access/permissions.json
      VF_MTA_PERMISSIONS_SHA256: "$PermissionHash"
    volumes:
      - type: bind
        source: "$PermissionPath"
        target: /access/permissions.json
        read_only: true
  mta-install:
    environment:
      VF_MDM_SOURCE_DIGEST: "$SourceDigest"
      VF_MTA_PERMISSIONS_FILE: /access/permissions.json
      VF_MTA_PERMISSIONS_SHA256: "$PermissionHash"
    volumes:
      - type: bind
        source: "$PermissionPath"
        target: /access/permissions.json
        read_only: true
"@ | Set-Content -LiteralPath $DataComposeFile -Encoding utf8
vf config --quiet
```

Keep this override on subsequent `vf` calls/restarts. Do not enable historical fixtures/rosters, prepare with empty access then change its hash, or use `activate_daily_ui`.

### 3. Inspect and execute the first daily input ONCE

Keep the serving MTA stopped during its exclusive daily worker. CPU/memory sizing belongs to the deployment, not this procedure. Ordinary execution owns ingestion/capture/calculation and inherent consumer writes; verify input/output findings separately afterward. On any failed/partial attempt preserve actual rows/files and reconcile before a reviewed retry; never repeat an accepted date.

```powershell
# Prebuilt route entrypoint is already Python; create only the owned output directory.
vf --profile install run --rm --no-deps mta-install -c "from pathlib import Path; Path('/var/lib/vectorflow/pick').mkdir(parents=True, exist_ok=True)"
if ($LASTEXITCODE -ne 0) { throw 'Pick output directory could not be created' }
$DayHash = $Release.optional_raw_inputs.files.'day-01.json'
$Revision = 'manual-first-day-' + (Get-Date -Format 'yyyyMMddTHHmmss')
$DayArguments = @('manage.py','run_production_day','/input/day-01.json','--sha256',$DayHash,
  '--initialization',$Initialization.opening_id,'--source-digest',$SourceDigest,
  '--configuration-digest',$ConfigurationDigest,'--revision',$Revision,
  '--pick-output-root','/var/lib/vectorflow/pick')
vf --profile install run --rm --no-deps -v "${InputRoot}:/input:ro" mta-install @DayArguments --inspect
$DayJson = vf --profile install run --rm --no-deps -v "${InputRoot}:/input:ro" mta-install @DayArguments
$DayJson | Set-Content -LiteralPath "$ReceiptsRoot/day-01-result.json" -Encoding utf8
$Day = $DayJson | ConvertFrom-Json
if ($Day.status -ne 'SUCCEEDED') { throw 'Preserve the failed execution; do not replay' }
```

Retain actual run/input/output/source IDs and complete typed input/capture/output audits; compare expected values. Counts/exit0 alone do not establish business acceptance. A successor uses `day-02.json` with its independent hash/new revision and adds **`--predecessor $Day.run_id --predecessor-output-digest $Day.output_digest`** to the same inspect/execute procedure. Use its own persisted predecessor; never copy another engine's outputs or run a span automatically.

### 4. Prepare, verify and select this actual run, then serve

```powershell
vf --profile install run --rm --no-deps mta-install manage.py prepare_daily_ui --run-id $Day.run_id --output-digest $Day.output_digest
vf --profile install run --rm --no-deps -v "${InputRoot}:/input:ro" mta-install manage.py prepare_native_input_archive --run-id $Day.run_id --output-digest $Day.output_digest --opening-file /input/initialization.json --daily-file /input/day-01.json
# One-off RUNTIME selection writer: this owned data volume is RW only here.
# The normal serving API stays RO; no installer/admin secret is added.
$SelectionComposeFile = Join-Path $PrivateRoot 'selection-writer.json'
@{services=@{mta=@{volumes=@(@{type='volume'; source='mta_data'; target='/var/lib/vectorflow'; read_only=$false})}}} | ConvertTo-Json -Depth 8 | Set-Content $SelectionComposeFile -Encoding utf8
vf -f $SelectionComposeFile run --rm --no-deps --entrypoint python mta manage.py check_daily_selection --run-id $Day.run_id --output-digest $Day.output_digest --selection-file /var/lib/vectorflow/selection.json
Set-OperatorValue 'MTA_SELECTION_FILE' '/var/lib/vectorflow/selection.json'
vf up --no-build --pull never -d --wait --force-recreate mta
vf restart auth frontend
vf ps
```

Preparation owns its per-layer transactions; do not put it inside outer atomic/READ ONLY, replay partial layers silently or fabricate READY rows. Require20native layers, Planning summary, Guided aggregates and exact output/config/selection. For later dates use that run/output and daily-file path, not day1 variables.

### 5. Validate populated functionality separately

MTA readiness must now be200/native admitted. With correctly scoped real actors, verify selected date, full expected report values, original filters/reload, supplier view, downloads and required requester/reviewer actions. InputData.zip has native opening/daily/captured JSON, schema and manifest (five members), replacing the legacy CSV-member archive. It is an administrator-only whole-input export. Compare actual files with admitted selected-run files. Retained NULL/availability/legacy-flaw qualifications are in the handoff; unexpected denials/errors are not empty successes.

Keep the installation administrator protected. Use **Manage Users → Add New User** to create an ordinary operator with the existing Distribution role (for example **BPRManager**) and explicitly assign its product/location scopes before signing in as that operator. The administrator cannot edit itself through this table. Original system roles/page/feature mappings belong to installation metadata; an empty role selector is an installer defect, not a reason to reseed accounts or bypass access checks. For an older source-built installation, the targeted metadata-only repair is documented in [source-build step9](SOURCE_BUILD.md#9-create-a-normal-scoped-mta-user-and-open-the-results).

Apply/Sleep/MDM actions must be genuine actor transitions accepted once and consumed by their own date-compatible successor. Do not force suggestions, backdate actions, bypass CAPTCHA or change facts to create eligibility. The historical sample is not an automatic current-date workflow campaign.

After metadata repair, reload the administrator's browser page so Manage Users fetches fresh role/permission data. Verify an ordinary user's **Edit → Next → Update User** using its existing selections; roles, scopes and password must remain unchanged. The protected administrator's self-edit restriction and the separate email-dependent password-reset operation are unchanged. See source-build step9 for troubleshooting; do not reinstall or reseed users.

## C. Restart, backup and rollback

### SMTP and password reset

Configure the ignored deployment env file's `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USER`, `EMAIL_PASS`, `EMAIL_FROM`, `EMAIL_NAME`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL` and `EMAIL_TIMEOUT`. STARTTLS normally uses587/TLS=true/SSL=false; implicit TLS uses465/TLS=false/SSL=true. Use your provider's actual values and authorized sender. Blank host leaves email/reset unavailable without blocking installation/login. No provider credentials are packaged or built into images. Keep env files/private resolved configuration outside Git. See the [complete source-build SMTP instructions](SOURCE_BUILD.md#configure-smtp-for-password-reset-and-account-notifications). For the prebuilt route, use this runbook's `vf up -d --no-deps --wait auth` and `vf exec -T auth python -m release.check_smtp` with the same env file and pinned updated auth image; no reinstall or frontend/MTO replacement. The check opens/closes SMTP with configured TLS/login but sends no email. Reset uses the existing admin action; missing configuration or delivery failure returns a useful error with no credential change. SMTP acceptance does not prove inbox delivery. Never reset a real user solely to test this configuration or use an `.invalid` address for external delivery.

- Restart this same project/image/DB-OID/volume/config/access/secret set; retain `$DataComposeFile` in `vf` after Part B. Startup never provisions, migrates, loads, calculates or prepares.
- Quiesce writes and stop the owned MTA worker/API and PG before cold capture. Preserve whole PG cluster plus matching MTA Pick/selection files, access/config/private secrets with hashes and numeric owners/modes. Auth/MTO share the separate MTO database; include their matching volumes/secrets for complete operational backup. Newly executed Step5 recovery covers MTA+PG/restored UI, not a new full auth/MTO disaster rehearsal.
- Restore into NEW empty owned volumes with matching PG/image/OIDs/roles/capabilities/files/secrets. Verify all bytes/owners first, then identities/full values and authenticated reports. A logical dump into a new OID plus reseal is not equivalent.
- Fresh install does not prove in-place sealed upgrade. Keep the original image+DB+MTA/config/secret pair; never use an old image on a newly registered DB. Protected-service replacement, destructive restore and public cutover remain separately coordinated.
- `vf stop` pauses this manual project. No `down -v`, volume/account reset, Docker prune or shared Docker/WSL restart. Leave existing8080/3005/3006/3002/3003/3004 untouched.

See [final connected handoff](../docs/handoff-3005/STEP5_CONNECTED_HANDOFF.md) for identities/evidence/limits. The sole live tracker is `F:/freshvcf/docs/handoff-3005/TRACKER.md`; the repository tracker is a pointer. Record **Part A manual blank validation** and **Part B optional populated validation** separately. No scheduled review is invoked by this runbook.
