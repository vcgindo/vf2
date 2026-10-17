# VectorFLOW operator runbook

This describes the exported Linux/amd64 Docker assembly. Installation and UI evidence are recorded in the development tracker; commands documented here are not claims that a recovery rehearsal has passed. Do not execute these instructions against a sealed development database or another application's resources. Installation creates empty databases; it imports no demonstration inputs, calculated state, accounts or passwords.

## Release and host preparation

Obtain the source ZIP and its SHA256 from the approved release manifest, verify the digest, and extract into a new release directory. Alternatively, on a clean machine with Git and Python 3, clone the approved repository and export the exact reviewed commit with the existing standard-library exporter:

```sh
git clone https://github.com/yurtse/freshvcf.git /srv/vectorflow/source
cd /srv/vectorflow/source
git fetch origin
RELEASE_COMMIT=REPLACE_WITH_APPROVED_FULL_40_CHARACTER_COMMIT
git checkout --detach "$RELEASE_COMMIT"
test "$(git rev-parse HEAD)" = "$RELEASE_COMMIT"
python3 -m release.export --repository /srv/vectorflow/source \
  --revision "$RELEASE_COMMIT" --output "/srv/vectorflow/releases/$RELEASE_COMMIT"
cd "/srv/vectorflow/releases/$RELEASE_COMMIT"
```

Replace the commit placeholder before running; the destination must not already exist. Repository access must use the operator's normal Git credentials, never credentials embedded in these commands. The exporter reads committed files and excludes validation populations/runners and secrets; copying the whole checkout is not a production export. Verify `release-source.json` names the approved full commit, then follow the external configuration, image build/load and installation steps below. No application Python dependencies are required merely to run this exporter.

Use Docker Engine with Linux containers and Docker Compose v2. Images and Python dependencies are pinned in `images.lock.json` and `requirements-*.lock`; frontend dependencies use the retained `package-lock.json`. Other CPU architectures and native Windows service installation are not declared supported. The release directory must contain `release-source.json`, the service sources, native SQL/migrations and this directory. No development checkout mount is required.

Record the complete source commit and built image IDs in the deployment inventory. Build from the exported root, not an arbitrary working tree. Keep the preceding export, image IDs, nonsecret configuration and separately protected secrets for rollback. Do not run dependency upgrade commands during installation.

Copy `release/.env.example` to a private operator configuration location. Set `VF_RELEASE`, `VF_PROJECT`, `VF_SECRETS_DIR`, public HTTP(S)/WebSocket origins and explicit allowed hosts. Use absolute secret-file paths when the operator configuration is outside `release/`. MTA and MTO default to separate `vectorflow_mta` and `vectorflow_mto` databases; auth uses a separately owned `identity` schema in the MTO database. Choose all names before provisioning. They are not rename instructions for an existing deployment.

The examples below run from the exported root. Replace `/srv/vectorflow/operator.env` and other operator paths with the actual private deployment paths. Define a shell function to keep the project, configuration and Compose files consistent:

```sh
vf() { docker compose --env-file /srv/vectorflow/operator.env -f release/compose.yaml "$@"; }
```

For external HTTPS, add `-f release/compose.tls.yaml` to that function, set `VF_TLS_MODE=https`, provide the certificate chain/private-key files, and use matching HTTPS/WSS origins. The gateway listens on container port 80 even in TLS mode; `VF_HTTP_PORT` selects the host port. Plain HTTP is restricted to loopback. Local development verification is restricted to its already authorized port; example port values grant no permission to open additional ports.

Only the gateway publishes a port. PostgreSQL, Redis and service listeners remain on the private application network. For a separately administered PostgreSQL server, set `DB_HOST`/`DB_PORT` and include `compose.db-tls.yaml` with `VF_DB_CA_FILE`: clients then require `verify-full`. That override configures clients, not server TLS. The bundled private PostgreSQL service does not automatically obtain or install server certificates. Do not claim TLS server verification from rendering the override alone.

## Secrets and image builds

Build the auth image first, using its pinned Dockerfile. Use that image's `release.prepare_secrets` command to generate a **new** secret directory under a private host parent, mounted only for that command. It refuses an existing destination. For example, after choosing the actual image tag:

```sh
docker build --platform linux/amd64 -f release/auth.Dockerfile -t vectorflow/auth:RELEASE .
docker run --rm --network none --user 0:0 --entrypoint python \
  --mount type=bind,src=/srv/vectorflow/private,dst=/private \
  vectorflow/auth:RELEASE -m release.prepare_secrets --directory /private/secrets
```

The host parent must exist with access restricted to the deployment operator. The generated directory is mode 0700; files are read-only and separately mounted only into the services that need them. Enforce equivalent host ACLs on Windows; Linux mode bits do not establish Windows ACL protection. Save the returned **public** client cipher key as `VF_CLIENT_CIPHER_KEY`. It must match the frontend build and auth service. Database passwords, signing secrets and RSA private keys must never appear in frontend build arguments or images. Back up the private files separately; regeneration is credential/key rotation, not restart.

`REACT_APP_AG_GRID_LICENSE_KEY` is an optional public build override; blank retains the exact original corporate key. Confirm deployment entitlement with the corporate license owner. The embedded key text does not establish the current contract. Build the remaining images and inspect the complete rendered assembly before installing:

```sh
vf config --quiet
vf build mta auth mto frontend
vf config --images
```

For offline installation, transfer these exact built images with Docker image save/load and verify their IDs. Pulling a tag with a matching name is not sufficient identity verification.

## Windows PowerShell: clean-folder path

Python 3, Docker Desktop in Linux-container mode and Compose v2 must already be installed. This is a new-install procedure: choose a new export folder, private operator folder and explicitly approved project/port. Do not run it over the preserved trial or another deployment. The following reads the versioned delivery manifest; it does not rely on controller drive paths. The source ZIP and manifest must come from the same approved delivery.

```powershell
$ErrorActionPreference = 'Stop'
Get-Command python, docker | Out-Null
$ManifestFile = (Resolve-Path (Read-Host 'Path to release-artifacts-<version>.json')).Path
$Release = Get-Content -LiteralPath $ManifestFile -Raw | ConvertFrom-Json
$DeliveryDir = Split-Path -Parent $ManifestFile
$SourceZip = Join-Path $DeliveryDir $Release.source_archive.file
if ((Get-FileHash -LiteralPath $SourceZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Release.source_archive.sha256) { throw 'Source ZIP differs' }
$ExportRoot = Read-Host 'New absolute export folder'
if (Test-Path -LiteralPath $ExportRoot) { throw 'Preserve existing folder; do not overwrite it' }
Expand-Archive -LiteralPath $SourceZip -DestinationPath $ExportRoot
$ExportRoot = (Resolve-Path $ExportRoot).Path
$Source = Get-Content -LiteralPath (Join-Path $ExportRoot 'release-source.json') -Raw | ConvertFrom-Json
if ($Source.source_commit -ne $Release.source_commit) { throw 'Source/manifest commit differs' }
Set-Location -LiteralPath $ExportRoot
$DockerInfo = docker info --format '{{json .}}' | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $DockerInfo.OSType -ne 'linux') { throw 'Docker Linux containers are required' }
docker compose version
if ($LASTEXITCODE -ne 0) { throw 'Compose v2 is required' }
$PrivateRoot = Read-Host 'New absolute private operator folder outside the export'
if (Test-Path -LiteralPath $PrivateRoot) { throw 'Never replace existing secrets/configuration' }
New-Item -ItemType Directory -Path $PrivateRoot | Out-Null
$PrivateRoot = (Resolve-Path $PrivateRoot).Path
if ($PrivateRoot.StartsWith($ExportRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Private configuration must be outside the build context' }
$OperatorIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls $PrivateRoot /inheritance:r /grant:r "${OperatorIdentity}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F'
if ($LASTEXITCODE -ne 0) { throw 'Private folder ACL setup failed' }
$Commit = $Source.source_commit
$AuthImage = "vectorflow/auth:$Commit"
docker build --platform linux/amd64 -f release/auth.Dockerfile -t $AuthImage .
if ($LASTEXITCODE -ne 0) { throw 'Auth image build failed' }
$SecretReceipt = docker run --rm --network none --user 0:0 --entrypoint python --mount "type=bind,src=$PrivateRoot,dst=/private" $AuthImage -m release.prepare_secrets --directory /private/secrets | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'New secret generation failed; preserve partial files' }
$OperatorEnv = Join-Path $PrivateRoot 'operator.env'
$EnvText = Get-Content -LiteralPath 'release/.env.example' -Raw
$Project = Read-Host 'Unique approved Compose project name'
$HttpPort = Read-Host 'Explicitly approved free loopback HTTP port'
$Values = [ordered]@{
  VF_RELEASE = $Commit
  VF_PROJECT = $Project
  VF_HTTP_PORT = $HttpPort
  VF_PUBLIC_URL = "http://127.0.0.1:$HttpPort"
  VF_PUBLIC_WS_URL = "ws://127.0.0.1:$HttpPort"
  VF_SECRETS_DIR = (Join-Path $PrivateRoot 'secrets').Replace('\','/')
  VF_CLIENT_CIPHER_KEY = $SecretReceipt.public_client_cipher_key
}
foreach ($Key in $Values.Keys) {
  if ([string]::IsNullOrWhiteSpace($Values[$Key]) -or $Values[$Key] -match '[\r\n]') { throw "Missing/invalid $Key" }
  $EnvText = [regex]::Replace($EnvText, "(?m)^$Key=.*$", [Text.RegularExpressions.MatchEvaluator]{ param($Match) $Key + '=' + $Values[$Key] })
}
[IO.File]::WriteAllText($OperatorEnv, $EnvText, [Text.UTF8Encoding]::new($false))
function vf {
  & docker compose --env-file $OperatorEnv -f (Join-Path $ExportRoot 'release/compose.yaml') @args
  if ($LASTEXITCODE -ne 0) { throw 'Compose command failed; preserve the failure and resources' }
}
python -m release.preflight --env-file $OperatorEnv
if ($LASTEXITCODE -ne 0) { throw 'Read-only configuration preflight failed' }
vf build mta auth mto frontend
$Images = @(vf config --images | Sort-Object -Unique | ForEach-Object {
  $Image = @(docker image inspect $_ | ConvertFrom-Json)[0]
  if ($LASTEXITCODE -ne 0) { throw 'Image inspection failed' }
  @{ tag = $_; image_id = $Image.Id; platform = ($Image.Os + '/' + $Image.Architecture) }
})
$ImageManifest = Join-Path $PrivateRoot 'built-image-identities.json'
[IO.File]::WriteAllText($ImageManifest, (@{ source_commit=$Commit; images=$Images } | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
python -m release.preflight --env-file $OperatorEnv --images-manifest $ImageManifest
if ($LASTEXITCODE -ne 0) { throw 'Release/image/port preflight failed' }
```

The first preflight explicitly reports `image_identity_verified=false`; the second checks every configured local image against the recorded build IDs. A local source build is recorded as such, not asserted to have the delivery archive's image IDs. Keep the generated image inventory with the source ZIP hash. For loading prebuilt images instead, verify the runtime archive and image override hashes from the same delivery, use `docker image load --input` and its supplied image-ID override, and pass the delivery manifest to preflight. Its public frontend cipher/WebSocket build values must match the operator configuration; a changed origin requires the documented frontend build with that origin, not a silent image claim.

Continue using the same `vf` function for **One-time empty installation** below; the commands are identical in PowerShell (enter each command on one line). Create the bootstrap administrator with the interactive `createsuperuser` command, start the application, then use the existing role/user workflows. Expected empty readiness is 503 with explicit application availability, not a command failure to repair by selecting arbitrary data. `Invoke-WebRequest` in PowerShell may throw on that expected 503; retain its response body or use `curl.exe -i` when available.

If Docker reports automatic address-pool exhaustion, it is not a port conflict. Read `docker network ls`, `docker network inspect` and host/VPN routes (`Get-NetRoute`) before choosing any subnet. Preserve all existing networks. An administrator may separately approve an unused private subnet, add `VF_APPLICATION_SUBNET` to the operator env, and include `-f release/compose.network-subnet.yaml` in both `vf` and `release.preflight --compose-file` calls. Preflight rejects overlap with existing Docker networks; the operator must also compare host/VPN routes. Do not prune, restart Docker/WSL, delete networks or silently choose a fallback subnet. No supplied example allocates another public port or authorizes changing an existing serving resource.

## One-time empty installation

Confirm the target cluster is exclusively owned by this installation. Preserve existing resources; do not use prune, reset, volume deletion or an existing database as an installation shortcut. Provisioning refuses any target database or role that already exists, including its registrar roles. A failure after database creation can leave partial new resources: preserve the failure and inventory, investigate it, and obtain a specific cleanup disposition rather than rerunning with different names until something passes.

```sh
vf up -d postgres redis
vf --profile install run --rm provision -m release.provision
vf --profile install run --rm provision -m release.provision --apply
vf --profile install run --rm mta-install manage.py migrate --plan
vf --profile install run --rm mta-install manage.py migrate --noinput
vf --profile install run --rm auth-install manage.py migrate --noinput
vf --profile install run --rm mto-install manage.py migrate --noinput
vf --profile install run --rm auth-install -m release.install_identity
vf --profile install run --rm provision -m release.grant_service AUTH
vf --profile install run --rm provision -m release.grant_service MTO
vf --profile install run --rm provision -m release.installed_application
```

MTA installation does not choose a trial input or register a namespace. The final command grants the dedicated runtime schema USAGE and SELECT on exactly the migration/initialization/source/run identity tables. It creates no source, initialization or business population. Installed source bytes, completed migrations, owner/session attributes and this finite grant profile are checked at startup. Keep all MTA selection/source/permission/hierarchy settings blank on this first empty start.

```sh
vf up -d mta auth mto frontend
curl PUBLIC_ORIGIN/healthz
curl -i PUBLIC_ORIGIN/readyz
```

Expect liveness 200 and data readiness 503 with `application.available=true`, `installed=true`, `initialized=false`, `publication_selected=false`, `state=installed`. Normal login and assigned screen definitions work in this state; no trial, fake scope, report date or calculated result is required. Missing/altered configured selections, inconsistent initialized state, source drift and unexpected grants remain failures, not empty success. A namespace is registered only after the operator separately chooses the optional initialization below or another explicitly approved native input.

Only the installation profile receives the provisioning credential. Runtime roles have no database/schema ownership or migration authority. Auth/MTO runtime grants are confined to their respective schemas; MTA uses its stricter immutable capability catalogue. A normal serving restart checks migrations without applying them.

Identity catalogue installation creates retained application/permission/feature metadata and empty/default client configuration only. Create an operator-approved account with the existing interactive command if required, then assign actual approved application permissions/scopes through existing administration procedures. No fixture account is installed:

```sh
vf --profile install run --rm auth-install manage.py createsuperuser
```

Do not place account passwords on the command line. An account does not by itself grant product/location/application scope. Keep CAPTCHA and authentication enabled.

Once the empty application is serving, sign in normally as that bootstrap administrator. Use **Vector Admin → Manage Roles** (`/vector-admin/manage-roles`) to create the operator-approved MTA roles from the installed permission catalogue. Select the actual application and existing URL/function entries; use the approved role codes and names, not the development fixture's numeric IDs. The installer deliberately creates no requester/reviewer roles or assignments. A reviewer is an ordinary user with the specifically approved review permissions, not a second superuser.

Open **Profile → Manage Users → Add User** to create each approved requester/reviewer through the existing registration form. Select the relevant application role, then its Product and Location permissions (including the required hierarchy levels) and any specifically approved data permissions. Use the form's existing password/notification process and configured mail service; do not seed fixture credentials or mark every account as admin. For an existing account, use the same Manage Users edit workflow. These screens call the retained `/api/user/add-role/`, `/api/user/register/` and `/api/user/edit-user` contracts; role definitions and user scope assignments are separate operations. Before a business population exists, legitimate empty product/location lists contain no assignable IDs. An upstream catalogue failure is a separate 503 error. Application/URL roles may be configured with no population scope; assign only the approved actual hierarchy after initialization/catalogue configuration. Do not invent IDs, select a different run or bypass a denial.

Sign in as each ordinary account and check **Profile → Permissions**, its intended report/MDM menu, and the allowed product/location subset. Confirm the requester lacks reviewer actions and an out-of-scope read/action is denied. Reauthenticate after changing assignments so the issued session reflects them. Keep the native MTA permission/hierarchy files and their configured SHA256 values consistent with that approved deployment; creating an auth account does not generate or replace those files. These are operator setup instructions derived from the existing forms/models, not a completed fresh-account onboarding or business-workflow rehearsal. No users, passwords, roles or scope assignments are automatically imported by this package.

## Optional retained initialization-only bootstrap

This procedure is separate from installation. It requires an explicitly approved, untouched trial target; it must not be applied to a sealed development case, an exhausted ledger or the preserved user installation. It contains no day sequence and does not execute Stage Five. The default source export includes only `release/optional-initialization.json`, not the external input pack.

The separate `vectorflow-optional-initialization-input-pack.zip` is SHA256 `a404eb8a3cefb610f81d2d73082afed43bca63efba8e15a34013a6fb8fe6327c`. Its `manifest.json` is SHA256 `137abb72235b2fa1803839909a66813f629e95a8e62888456f7eafa4e13db295`. The input `inputs/initialization.json` is 621390 bytes, SHA256 `3a4bf3a699c57fab7f00e6820f43c0e1b661386c9cf3aa4f21fd4081e110bdbe`; configuration digest `c3e2e2f1395ca40b0557b0edaceb96a01c2c02b37d8f962e6b732586a9d5d27c`; recipe digest `bec684bfefa570e7d86dbbed2b8ae580d04d50787549b6dff5e9a8f7be2185e6`. Opening identity is `HANDOFF3005-G3-CONSOLIDATED-20261015`, date 12 October 2026, with declared initial facts/history and retained Norm overrides, not a later calculated closing. Exact master counts and recipe identity are in the shipped JSON manifest.

Extract the verified external ZIP to a new operator folder. Bind only that folder read-only for the transfer command; never bind a development checkout. The destination is a new file in the durable MTA data volume. Both transfer and bootstrap refuse repeats; preserve failed partial transfers rather than overwriting them. In PowerShell, define `$InputDir` as the absolute extracted pack directory and use:

```powershell
$Pack = (Resolve-Path (Read-Host "Path to the separate initialization ZIP")).Path
if ((Get-FileHash -LiteralPath $Pack -Algorithm SHA256).Hash.ToLowerInvariant() -ne "a404eb8a3cefb610f81d2d73082afed43bca63efba8e15a34013a6fb8fe6327c") { throw "Input pack differs" }
$InputDir = Read-Host "New absolute folder for this pack"
if (Test-Path -LiteralPath $InputDir) { throw "Preserve existing folder; choose a new input destination" }
Expand-Archive -LiteralPath $Pack -DestinationPath $InputDir
if ((Get-FileHash -LiteralPath (Join-Path $InputDir "manifest.json") -Algorithm SHA256).Hash.ToLowerInvariant() -ne "137abb72235b2fa1803839909a66813f629e95a8e62888456f7eafa4e13db295") { throw "Pack manifest differs" }
vf --profile install run --rm --no-deps --volume "${InputDir}:/operator-input:ro" mta-install -m release.optional_initialize --input /operator-input/inputs/initialization.json --stage-to /var/lib/vectorflow/inputs/optional-initialization.json
vf --profile install run --rm --no-deps mta-install -m release.optional_initialize --input /var/lib/vectorflow/inputs/optional-initialization.json --inspect
```

For a POSIX shell, the corresponding transfer is `vf --profile install run --rm --no-deps --volume "$INPUT_DIR:/operator-input:ro" mta-install -m release.optional_initialize --input /operator-input/inputs/initialization.json --stage-to /var/lib/vectorflow/inputs/optional-initialization.json`. Inspect uses the same arguments as PowerShell. Inspect must return `OPTIONAL_INITIALIZATION_INSPECTED_NOT_APPLIED` and native installation eligibility true. Day eligibility remains false because no day facts were supplied. Inspect creates no registration or input rows.

After separately choosing this input, register the existing current-source namespace once and apply initialization. Registration refuses an existing registration; no replacement/reseal path is provided. The wrapper uses the unchanged native initializer and existing typed opening-owner bootstrap for families 1-13, inside one transaction. It refuses any existing initialization/source/run/task/capture before mutation. It does not call execute_day, accept a workflow, create a recommendation or publish a report.

```sh
vf --profile install run --rm --no-deps provision -m release.register_mta --input-sha256 3a4bf3a699c57fab7f00e6820f43c0e1b661386c9cf3aa4f21fd4081e110bdbe
vf --profile install run --rm --no-deps mta-install -m release.optional_initialize --input /var/lib/vectorflow/inputs/optional-initialization.json --apply
```

Save the JSON receipt: status `OPTIONAL_INITIALIZATION_APPLIED_NO_DAY`, real source/opening/integration digests, opening date and `accepted_day=false`. Set **only** `MTA_SOURCE_DIGEST` to the returned source digest in the private operator env; leave `MTA_SELECTION_FILE` blank. Recreate MTA with `vf up -d --no-deps mta`. Gateway readiness remains 503 with `state=initialized`; supported master reads now use the verified untouched initial opening, while reports still await a published day. A second wrapper apply must exit nonzero with `second initialization is refused` and preserve the first receipt, rows and zero runs. The lower-level native command retains its historical identical-input REVERIFIED behavior; this wrapper is the documented one-shot optional procedure.

No users, scope assignments, daily facts, generated PICK, accepted outputs or publications are in this pack. Loading it does not constitute an operational trial. Preserve the supplied file and emitted receipts.

## Separately approved operating inputs, day and span

Operator input artifacts, generated PICK files, evidence and publication selection belong in the durable `mta_data` volume under `/var/lib/vectorflow`. Copy supplied files into that volume using an explicitly owned one-off container or a dedicated volume transfer procedure; never mount a development checkout or dump a database into the package. Hash files after transfer. Preserve raw/processed provenance separately. Optional demonstration inputs must be separately selected and must contain external/master/opening/daily facts only, with no calculated outputs seeded as inputs.

Use the MTA installer command's writable data volume and retained installation authority for explicit native operations. These commands are documentation for an approved new operating population. They do not release replay of any previously accepted validation day or exhausted execution ledger.

```sh
vf --profile install run --rm mta-install manage.py initialize_production /var/lib/vectorflow/inputs/initialization.json \
  --sha256 INITIALIZATION_SHA256 --configuration-digest CONFIGURATION_SHA256 --recipe-digest RECIPE_SHA256 --inspect
vf --profile install run --rm mta-install manage.py initialize_production /var/lib/vectorflow/inputs/initialization.json \
  --sha256 INITIALIZATION_SHA256 --configuration-digest CONFIGURATION_SHA256 --recipe-digest RECIPE_SHA256
```

Save the emitted initialization ID, source/configuration identities and receipt. For one day, inspect first using the same arguments plus `--inspect`, then invoke the existing native day boundary:

```sh
vf --profile install run --rm mta-install manage.py run_production_day /var/lib/vectorflow/inputs/day.json \
  --sha256 DAY_SHA256 --initialization INITIALIZATION_ID --source-digest SOURCE_SHA256 \
  --configuration-digest CONFIGURATION_SHA256 --revision UNIQUE_OPERATION_REVISION \
  --pick-output-root /var/lib/vectorflow/pick
```

For each successor, additionally supply `--predecessor RUN_ID --predecessor-output-digest OUTPUT_SHA256` from its own preceding successful receipt. Successor inputs must not supply another consumer opening. A span is this same command executed sequentially for an explicitly approved ordered set of consecutive daily artifacts: inspect each day's actual persisted predecessor, run exactly once, save its receipt, then advance. Stop on the first nonzero exit or non-SUCCEEDED status; do not continue later days, switch predecessors or automatically retry a failed capture. There is no second span calculation engine or scheduler. A retry requires the existing explicit `--retry-capture` identity and its frozen input/contract; do not substitute a new file or revision to hide the failure.

## Publication, selection and serving

Calculation success is separate from report preparation, activation and serving selection. Preserve the generated output digest; do not edit rows/seals or select an earlier run to populate a grid.

```sh
vf --profile install run --rm mta-install manage.py prepare_daily_ui --run-id RUN_ID --output-digest OUTPUT_SHA256
vf --profile install run --rm mta-install manage.py activate_daily_ui --run-id RUN_ID --output-digest OUTPUT_SHA256 --publication-seal PUBLICATION_SEAL
vf --profile install run --rm mta-install manage.py check_daily_selection --run-id RUN_ID --output-digest OUTPUT_SHA256 \
  --selection-file /var/lib/vectorflow/selection.json
```

Each command must pass its real prerequisites; the command list does not bypass unsupported capabilities, missing ancillary inputs, denied permissions or unprepared report layers. Configure the approved permission/hierarchy files and their hashes, set `MTA_SELECTION_FILE=/var/lib/vectorflow/selection.json`, and retain the prior configuration/selection for backout. Apply the whole selection configuration together:

```sh
vf up -d mta auth mto frontend
vf ps
curl --fail PUBLIC_ORIGIN/healthz
curl --fail PUBLIC_ORIGIN/readyz
vf logs --tail 100 mta auth mto frontend
```

`/healthz` is process/gateway liveness. `/readyz` verifies identity database and selected MTA dependencies. Before legitimate publication it returns 503; a validated empty or initialized application also reports its separate nonsecret `application` availability/setup state. A broken configuration does not receive that successful setup state. Container health alone is not whole-application readiness and the gateway readiness response does not certify MTO scheduler output. Verify MTO routing/WebSocket integration separately without inventing scheduler runs. No scheduler execution or MTO output validation is introduced by installation.

For status, retain `vf ps`, readiness bodies, the last operation/publication receipts and bounded logs. Check actual run status/output/publication against the explicit selection through the existing application/API; HTTP 200 or a row count alone is insufficient. After a source-compatible restart, require the same selected run/output/publication and usable affected report/layout interactions:

```sh
vf restart mta auth mto frontend
vf ps
vf logs --tail 100 mta auth mto frontend
```

A source change is an upgrade, not an ordinary restart. Never point a new export at an older sealed source without its exact approved compatibility proof.

## Durable storage, backup and restore

Inventory the actual project volumes: PostgreSQL data, Redis persistence, MTA data/selection/evidence/PICK files, auth data/logs, MTO data/downloads/logs. Capture the Compose configuration without secret contents, release manifest/image IDs, private secret inventory and database identities. MTA integrity bindings include database OIDs and registrar ownership; a logical dump restored into a newly created database is not automatically an admissible replacement. Do not repair that mismatch by editing a receipt or resealing calculated state.

For a consistent cold recovery set, schedule downtime, quiesce explicit operations and stop all application services, Redis and PostgreSQL using `vf stop`. Confirm no worker/job/transaction remains. Back up the **whole stopped PostgreSQL cluster volume**, all companion durable volumes and the separately protected secrets/configuration as one identified set. Use a verified volume backup tool preserving numeric ownership, permissions and links. Hash and encrypt the backups and record the PostgreSQL16.15 image identity. Never tar a live PostgreSQL data directory or infer that a dump alone preserves OIDs/roles/capabilities.

Restore only into explicitly owned empty volumes with the original project mappings; preserve failed/current volumes for investigation. Restore the entire matching set with original numeric ownership and exact secrets. Start the same pinned PostgreSQL version first, then services; do not run provision, initialize, migrate or seed commands as part of recovery. Verify original database names/OIDs, roles/catalogue, accepted/FAILED headers, full state/readback identities, selection, readiness and affected UI before releasing traffic. The full cold-backup/restore/failure rehearsal is a separate acceptance step and is not claimed by this runbook.

## Upgrade and rollback

Before an upgrade, freeze new operations, retain the currently serving images/source export/configuration/selection, and take a consistent recovery set. Compare the exact source/admission contract and migration plan under the existing owner authority before changing anything. Migrations and changed grants/catalogue must be installed as a coordinated upgrade under code that authenticates the exact approved delta. Do not run additive DDL under a serving validator that rejects it, weaken a guard or overwrite an immutable capability.

Run only reviewed migrations explicitly with each install service; preserve their output. Verify owners, finite runtime privileges and denied cross-schema/DDL access, then start the approved new images/configuration. Confirm readiness and actual selected prepared reports after startup/restart; do not issue business actions to simulate a restore test.

If the source/schema remains compatible, roll back using retained exact images/configuration/selection and verify the same identities. If a migration is not safely reversible, keep traffic stopped and restore the complete consistent recovery set into separately authorized empty resources; an old image on a changed schema is not a rollback. Never automatically reverse migrations, reset credentials, delete data/volumes or replay accepted days. Preserve failure logs and stop when the exact recovery authority is missing.

## Diagnostics and operational limits

The optional `maintenance` profile transfers the existing Celery audit-retention
task and its existing 24-hour beat schedule; it is not an MTO scheduler. Defaults
start neither worker nor beat. If audit retention is approved for this new
installation, start `vf --profile maintenance up -d auth-worker auth-beat`.
Run exactly one beat instance. Its schedule persists in `auth_data`; both use the
existing auth runtime role, Redis and external auth secrets. The worker listens
only on `db_cleanup_queue`. The retained task deletes auth audit rows older than
90 days. Do not enable it against preserved development data or invoke the task
as a packaging test. Check bounded worker/beat logs and process health separately;
process health does not certify a cleanup result.

Pending migrations stop serving; use the explicit installation/upgrade path after checking ownership. Missing secrets, a mismatched client cipher key, bad origins or untrusted TLS certificates are configuration errors, not reasons to disable authentication/TLS. A 503 with an absent publication is expected on an empty install. A source/catalogue/receipt mismatch must be investigated at its exact layer; it cannot be waived by returning an empty grid. A 403 must be traced through the existing user/application/product/location scope, never bypassed.

Logs rotate with Compose's configured maximum size/count; service logs and downloads use declared volumes. `FRONTEND_BUILD_HEAP_MIB` configures the Node build process (default 4096MiB), separately from nginx's runtime container limit. A cold lint/build reached the former 2560MiB V8 heap limit; this is a build-resource requirement, not an application calculation change. Record actual memory/CPU limits when assessing an installation. They are deployment settings, not production-capacity proof. Existing preserved native positive transit and Planning submission coverage limitations remain explicit; do not manufacture shipments, recolour dispatches or treat component evidence as a fresh positive UI pass.

## Retained sealed development publication qualification

Fresh installations do not use historical compatibility declarations. The optional `VF_MDM_SEALED_EXPORT_SHA256` entry is restricted to the reviewed `9e353ff8` export lineage and the original development database/OID, source, initialization and seal already enforced by the retained ancestry validators. It requires the exact pinned declaration at `/proof/s4-20261016/sealed-export-compatibility.json` on a read-only mount, the unchanged older declarations and their pins. It authenticates all 721 actual native production files, exactly 187 fixed validation omissions, the two reviewed installation deltas and only the explicitly reviewed verifier descendants. Unexpected files, omissions, bytes, metadata or bindings fail admission. Reconstructed historical bytes are validation data only. No installation, registration replacement, reseal, publication or calculation is performed.

For the separately approved retained-development layout check only, `VF_MDM_SEALED_EXPORT_LAYOUTS=1` additionally admits exactly owner-issued INSERT/DELETE on `mta.fresh_mta_userreportlayout` and USAGE on its ID sequence for the existing consumer. It requires the exact original database and export opt-in. The complete current privilege catalogue and all original capability identities, guards and catalogue rows remain checked; only those three authenticated ACL rows are removed for the unchanged historical comparison. UPDATE, TRUNCATE, grant option, PUBLIC access and other objects are not admitted. Disable this option for fresh installations: their existing production profile already specifies this finite preference access. This qualification is not a general database-copy, source-override or upgrade mechanism; the immutable development declaration and development proof resources are not shipped as production inputs.

The optional initialization input pack is not a complete execution trial. Step Five must define and freeze a coherent daily input sequence before any complete input-to-successor execution claim. No daily sequence or accepted output has been fabricated or replayed during packaging.

The setup descendant `vectorflow-reviewed-sealed-export-setup-v1` keeps that same original 908-file ancestry, fixed 721-file reviewed projection and 187 omissions. It additionally admits only one exact added setup module and five exact changed source files (hashes committed in `release.sealed_export.SETUP_FILES`). Every supplied inverse must reconstruct the reviewed bytes; the added module must reconstruct an empty ancestor. Unknown bytes, paths, omitted files, a repinned unrelated change, namespace/receipt drift or a writable proof still fail. This is the existing opt-in read-only proof for the preserved development publication, not a fresh-install dependency or new registration/seal. The original declaration remains preserved separately; use the separately pinned setup declaration only for this exact descendant.
