# Fresh Git installation with Docker Compose

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

Requires Git, Windows PowerShell7 and Docker Desktop with Linux/amd64 containers and Compose2.24.4 or later. Host Python/Node and the old image ZIP are not needed. This is a NEW blank installation, not an upgrade/reset of an existing deployment.

## 1. Clone and configure

```powershell
git clone --depth 1 --single-branch --branch codex/3006-logistics-integration `
  git@github.com:yurtse/freshvcf.git C:/VectorFLOW
cd C:/VectorFLOW
Copy-Item .env.example .env
notepad .env
```

Choose a NEW `VF_PROJECT` and a free `VF_HTTP_PORT`. Leave the documented database/role defaults unless you are deliberately configuring a different installation. Both HTTP and WebSocket origins derive from that port before building. The frontend is unchanged and still compiles the socket origin at build time; changing the port later requires a matching rebuild.

Set `VF_ADMIN_EMAIL` and `VF_ADMIN_NAME`. You may leave `VF_ADMIN_PASSWORD` blank to enter/confirm it privately during installation, or put your NEW password in this ignored local env file. The existing password policy requires at least8 characters, an uppercase letter and a special character; common/similar passwords are rejected. No default/demo users are installed. Real signing/database/RSA secrets are generated privately by installation and are not build arguments or image contents. Do not commit `.env`.

The accepted MTO BM-report page size remains5000 through `VF_MTO_BM_REPORT_ROWS_PER_PAGE`; no frontend or MTO code is changed.

The chosen port must be free; do not replace another serving instance. Use an actual fresh clone with a `.git` directory. Committed source is exported automatically during Docker build; a dirty tracked checkout is rejected. Record `git rev-parse HEAD` for the installed revision.

## 2. Build

```powershell
docker compose build
if ($LASTEXITCODE -ne 0) { throw 'Build failed; stop and retain output' }
```

The build automatically prepares committed source, native manifests and pinned dependencies, then builds MTA, auth, MTO and frontend. PostgreSQL and Redis use their pinned official images. All four application images come from the SAME Git commit. No hand-created source context, image-ID override or helper outside the repository is required.

Normal build/install/up imposes no container CPU, memory or swap ceiling and does not force serial Compose builds. Docker Desktop/host allocations and normal tool defaults still apply; this is not automatic capacity sizing. Worker counts, database timeouts and security controls are unchanged. Keep adequate disk space for dependencies, images and build cache.

Optional resource-controlled testing uses `release/compose.resource-test.yaml`. Explicitly add `-f compose.yaml -f release/compose.resource-test.yaml` to the same build/install/up commands ONLY for that test. It restores finite test ceilings and constrained compiler settings; it is never loaded by default. For build-only tuning without runtime ceilings, optionally set `FRONTEND_BUILD_HEAP_MIB` in `.env`; blank uses Node's default. These are test/operator choices, not production minimums. Do not use an optional test override when deploying without resource ceilings.

## 3. Install the blank application — ONE command

```powershell
docker compose run --rm install
if ($LASTEXITCODE -ne 0) { throw 'Installation failed; stop, retain state and inspect the error' }
```

This explicitly generates private per-service secrets, creates new databases/least-privilege roles, applies real migrations, installs the existing application roles with their page/feature permission mappings, and creates your new administrator. Enter any administrator fields not supplied in `.env` when prompted. Application role definitions are system metadata; no operational users, business scopes or role assignments are seeded. It does NOT register an opening, load masters/facts, calculate a day or prepare/publish reports. Existing databases/roles/users are not reset or overwritten; an already-installed target is refused.

## 4. Start and verify

```powershell
docker compose up -d --no-build --wait
docker compose ps
```

Open `http://127.0.0.1:<VF_HTTP_PORT>` and sign in normally with your new administrator, including CAPTCHA. Expect six healthy services and original navigation/installation metadata. A blank MTA has `/healthz`200; `/readyz`503 and unavailable data reports are expected until real onboarding/publication. Crashes,500s or a failed normal login are installation failures.

For a restart use `docker compose stop`, followed by the SAME `docker compose up -d --no-build --wait`. Restart never provisions, migrates, loads data or rotates secrets. Never use `down -v` to fix an error. Volumes contain the installation database, private keys, files and receipts; retain them together for recovery.

## Separate operation: master/opening loading and daily execution

Run the blocks below **in order, in the same PowerShell7 session, from your clone directory**, after completing steps1–4. They use your existing `.env`, project, port and built images. **No build or repeat installation is needed.** This is the first data load into that NEW blank installation, not a reset/replay procedure.

The optional Git example `examples/starter-data/vectorflow-starter-inputs-v1.zip` is the unchanged approved RAW synthetic pack:200SKU/20location definitions, a small active population, opening17October2026 and daily facts for18–19October2026. It contains no account, password, database, calculated output or automatic loader; it is excluded from production image export. These steps run **only18October/day1**. Historical facts show loading/calculation/reporting; they do not become today's facts or automatically prove current-date Apply/Sleep/reviewer workflows.

### 5. Extract the starter inputs outside Git

```powershell
$ErrorActionPreference = 'Stop'
$Project = (docker compose config --format json | ConvertFrom-Json).name
if ($LASTEXITCODE -ne 0 -or -not $Project) { throw 'Compose configuration failed' }
$SampleZip = (Resolve-Path './examples/starter-data/vectorflow-starter-inputs-v1.zip').Path
if ((Get-FileHash $SampleZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne '71bb16ec321d7ee683ddfca718f129451a36df9ee5540abdb4b2329ba1a5b63f') { throw 'Starter pack differs' }
$InputRoot = Join-Path $env:LOCALAPPDATA "VectorFLOW/$Project/starter"
if (Test-Path $InputRoot) { throw 'Starter directory exists; reconcile previous work instead of loading again' }
if (Select-String -Path .env -Pattern '^\s*COMPOSE_(FILE|PATH_SEPARATOR)\s*=' -Quiet) { throw 'Existing Compose override: merge deliberately; do not overwrite it' }
Expand-Archive -LiteralPath $SampleZip -DestinationPath $InputRoot
$InputRoot = (Resolve-Path $InputRoot).Path.Replace('\','/')
$Receipts = New-Item -ItemType Directory -Path "$InputRoot/receipts"
$OpeningHash = (Get-FileHash "$InputRoot/initialization.json" -Algorithm SHA256).Hash.ToLowerInvariant()
$DayHash = (Get-FileHash "$InputRoot/day-01.json" -Algorithm SHA256).Hash.ToLowerInvariant()
$PermissionHash = (Get-FileHash "$InputRoot/permissions.json" -Algorithm SHA256).Hash.ToLowerInvariant()
$ConfigurationDigest = 'c3e2e2f1395ca40b0557b0edaceb96a01c2c02b37d8f962e6b732586a9d5d27c'
$RecipeDigest = 'bec684bfefa570e7d86dbbed2b8ae580d04d50787549b6dff5e9a8f7be2185e6'
```

Keep this input/receipt directory for restart/recovery. Do not edit input dates, facts or digests. If any following command fails, **stop and retain the error/receipts**; do not repeat registration, reset volumes or replay an accepted day. `--help` only displays usage; `--inspect` only checks the supplied operation.

### 6. Register this opening and load its masters/opening ONCE

Only the MTA API is stopped while its explicit worker owns the data operation. PostgreSQL, auth, frontend and MTO remain installed; MTO is not changed. `provision -m release.register_mta` below is the registration subcommand, **not** another blank installation. Keep the image's default entrypoint: it supplies its baked source identity.

```powershell
docker compose stop mta
if ($LASTEXITCODE -ne 0) { throw 'Could not stop the MTA API' }
docker compose run --rm --no-deps provision -m release.register_mta --input-sha256 $OpeningHash
if ($LASTEXITCODE -ne 0) { throw 'Registration failed; do not repeat or reset' }
docker compose run --rm --no-deps -v "${InputRoot}:/input:ro" mta-install manage.py initialize_production /input/initialization.json --sha256 $OpeningHash --configuration-digest $ConfigurationDigest --recipe-digest $RecipeDigest --inspect
if ($LASTEXITCODE -ne 0) { throw 'Opening inspection failed' }
$InitJson = docker compose run --rm --no-deps -v "${InputRoot}:/input:ro" mta-install manage.py initialize_production /input/initialization.json --sha256 $OpeningHash --configuration-digest $ConfigurationDigest --recipe-digest $RecipeDigest
$InitExit = $LASTEXITCODE
$InitJson | Set-Content "$Receipts/initialization.json" -Encoding utf8
if ($InitExit -ne 0) { throw 'Initialization failed; preserve state' }
$Init = $InitJson | ConvertFrom-Json
if ($Init.status -ne 'INITIALIZED') { throw 'Expected one NEW initialization; reconcile existing state' }
```

### 7. Persist the matching access configuration, then execute day1

The read-time catalogue defines the sample product/location groups; it does **not** grant any user access. Freeze its hash and source digest before preparing reports. This small override stays outside Git; `.env` records it so ordinary subsequent Compose commands/restarts keep the populated configuration. Do not remove that `COMPOSE_FILE` entry after loading data. The semicolon separator is explicit for this Windows procedure.

```powershell
$DataCompose = "$InputRoot/compose.starter.json"
$Access = @{
  VF_MDM_SOURCE_DIGEST = $Init.source_digest
  VF_MTA_PERMISSIONS_FILE = '/access/permissions.json'
  VF_MTA_PERMISSIONS_SHA256 = $PermissionHash
}
$PermissionMount = @{type='bind'; source="$InputRoot/permissions.json"; target='/access/permissions.json'; read_only=$true}
$Data = @{services=@{
  mta = @{environment=$Access.Clone(); volumes=@($PermissionMount)}
  'mta-install' = @{environment=$Access.Clone(); volumes=@($PermissionMount)}
}}
$Data | ConvertTo-Json -Depth 8 | Set-Content $DataCompose -Encoding utf8
Add-Content .env "`nCOMPOSE_PATH_SEPARATOR=;`nCOMPOSE_FILE=`"compose.yaml;$DataCompose`""
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Populated Compose configuration failed' }

# The native preflight requires an existing owned Pick output directory.
docker compose run --rm --no-deps mta-install python -c "from pathlib import Path; Path('/var/lib/vectorflow/pick').mkdir(parents=True, exist_ok=True)"
if ($LASTEXITCODE -ne 0) { throw 'Pick output directory could not be created' }

$Revision = 'starter-day1-' + (Get-Date -Format 'yyyyMMddTHHmmss')
$DayArgs = @('manage.py','run_production_day','/input/day-01.json','--sha256',$DayHash,
  '--initialization',$Init.opening_id,'--source-digest',$Init.source_digest,
  '--configuration-digest',$ConfigurationDigest,'--revision',$Revision,
  '--pick-output-root','/var/lib/vectorflow/pick')
docker compose run --rm --no-deps -v "${InputRoot}:/input:ro" mta-install @DayArgs --inspect
if ($LASTEXITCODE -ne 0) { throw 'Day1 inspection failed' }
$DayJson = docker compose run --rm --no-deps -v "${InputRoot}:/input:ro" mta-install @DayArgs
$DayExit = $LASTEXITCODE
$DayJson | Set-Content "$Receipts/day-01.json" -Encoding utf8
if ($DayExit -ne 0) { throw 'Day1 failed; preserve the attempt instead of replaying' }
$Day = $DayJson | ConvertFrom-Json
if ($Day.status -ne 'SUCCEEDED') { throw 'Day1 did not succeed; do not continue' }
```

This loads the supplied daily operational facts and calculates the distribution day from its own initialized opening. A successful calculation is not yet the serving/UI selection.

### 8. Prepare/select day1 and start its UI backend

```powershell
docker compose run --rm --no-deps mta-install manage.py prepare_daily_ui --run-id $Day.run_id --output-digest $Day.output_digest
if ($LASTEXITCODE -ne 0) { throw 'Report preparation incomplete; preserve partial receipts' }
docker compose run --rm --no-deps -v "${InputRoot}:/input:ro" mta-install manage.py prepare_native_input_archive --run-id $Day.run_id --output-digest $Day.output_digest --opening-file /input/initialization.json --daily-file /input/day-01.json
if ($LASTEXITCODE -ne 0) { throw 'Native input download preparation failed' }
# Explicit one-off override: a CLI -v override can retain the inherited RO flag.
# Only this runtime-role selection writer gets RW; normal serving remains RO.
$SelectionCompose = "$InputRoot/compose.selection-writer.json"
@{services=@{mta=@{volumes=@(@{type='volume'; source='mta_data'; target='/var/lib/vectorflow'; read_only=$false})}}} | ConvertTo-Json -Depth 8 | Set-Content $SelectionCompose -Encoding utf8
docker compose -f compose.yaml -f $DataCompose -f $SelectionCompose run --rm --no-deps mta manage.py check_daily_selection --run-id $Day.run_id --output-digest $Day.output_digest --selection-file /var/lib/vectorflow/selection.json
if ($LASTEXITCODE -ne 0) { throw 'Selection validation failed' }
$Data.services.mta.environment['VF_MTA_SELECTION_FILE'] = '/var/lib/vectorflow/selection.json'
$Data | ConvertTo-Json -Depth 8 | Set-Content $DataCompose -Encoding utf8
docker compose up -d --no-build --wait mta
if ($LASTEXITCODE -ne 0) { throw 'Populated MTA startup failed; inspect logs' }
docker compose ps
```

The serving MTA retains its read-only data mount; the installer keeps its own secrets. No frontend build, MTO operation, parity hook, fixture mode or historical activation command is involved. Keep the same `.env`, data override, input/receipt directory and named volumes together.

### 9. Create a normal scoped MTA user and open the results

1. Open the **same URL/port chosen in `.env`** and sign in normally with the administrator you created during installation. No demo login is added.
2. In **Manage Users → Add New User**, enter a new operator name/email/password. Under **Distribution**, select the existing **BPRManager** role for starter Planning/BPR access, then **Next**. Do not assign Orders/MTO roles. The protected installation administrator is deliberately excluded from its own management table and cannot be edited there; do not change that protection.
3. In the normal advanced product/location permission steps, select the starter hierarchy and complete **Add User**. For complete starter coverage include all three product entries: `B1 Product` root71001, `Selected/Leaf`71002 and `Other/Leaf`71003; and all four location entries: `B1 Location` root72001, `Parent/Leaf`72002, `Receiving/Leaf`72003 and `Other/Leaf`72004. These are explicit real MTA data grants on YOUR NEW installation. Administrator status alone does not supply them. If SMTP is disabled, the existing UI can report that the user was created without an email; retain the password you entered and check the table before attempting creation again.
4. Sign in normally as that operator in a separate browser session. Open Distribution's **BPR** and **Planning** screens. In BPR's initial Filter dialog, **Show All** loads the account's authorized rows. Planning requires choosing a report category; its **Grid View icon** opens the row view. Verify the last run is18October2026 and scoped starter rows appear. MDM additionally requires the existing **MasterUpdater** or **MasterApprover** role for its respective workflow; those roles are not needed for this report-access check. Whole-input `InputData.zip` remains administrator-only and uses native JSON/typed-capture format. An empty/denied grid is not success: check the selected run and saved MTA scopes; do not load the inputs again.

If an earlier blank install has an empty role selector, update the clone and run this **missing-system-metadata repair only** from its directory. It uses the trusted checked-out installer with the existing auth installer's DB authority, adds missing original role definitions/mappings, refuses conflicting definitions, and does not change users/passwords/scopes or existing assignments. Do not rerun blank installation or historical fixture/account seeders.

```powershell
git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw 'Git update failed' }
$IdentityTools = (Resolve-Path './release').Path.Replace('\','/')
docker compose run --rm --no-deps -v "${IdentityTools}:/repair:ro" auth-install /repair/install_identity.py --repair-missing-roles
if ($LASTEXITCODE -ne 0) { throw 'Role metadata differs; preserve state and inspect the error' }
```

Refresh **Manage Users** afterwards. No build/service replacement, frontend/MTO change or data replay is needed for this repair. New installations include these role definitions automatically. The retained source has three unresolved role-link references (`/` twice and `intercept-task-status` once); the original seeder skipped them, and this catalogue preserves that behavior without inventing new routes or grants.

Optional read-only checks (no extra calculation):

```powershell
$Url = (docker compose config --format json | ConvertFrom-Json).services.mta.environment.VF_PUBLIC_URL
Invoke-RestMethod "$Url/readyz"
docker compose logs --tail 40 mta
```

Afterwards, ordinary `docker compose stop` / `docker compose up -d --no-build --wait` keep the selected data because `.env` retains the override. To continue another time, recover `$Init`/`$Day` from saved receipts; do not rerun steps5–7. A separately requested day2 would use `day-02.json`, its own hash/new revision, and `--predecessor $Day.run_id --predecessor-output-digest $Day.output_digest`; these steps deliberately do not execute it. Production onboarding requires its own authentic input/access packet, not this sample. The [advanced/prebuilt runbook Part B](RUNBOOK.md#b-optional-load-mastersopening-then-execute-a-supplied-day) remains a separate route; do not mix its `vf`, `$Release` or native pins with this source-built procedure.

## Release boundary

Root `compose.yaml` is this source-build route. `release/compose.yaml` remains the retained prebuilt/advanced assembly; its immutable package is unchanged. Frontend/MTO application source and behavior are unchanged. Build/blank-install verification evidence belongs in the existing handoff tracker; public HTTPS/WSS, production data, capacity and cutover are separate decisions. This guide does not itself claim those have passed.
