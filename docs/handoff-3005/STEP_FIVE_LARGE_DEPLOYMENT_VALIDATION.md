# VectorFLOW — Stage 5 manual orchestration

You run these commands on a new installation. This guide covers application setup and operation. The input package is being prepared separately; its path, manifest and business dates are pending.

**Status:** source-reviewed instructions, not an exercised Stage 5 installation. Step 6 will record the commands that actually succeed during your run.

## 1. Release and folders

| Item | Version or location |
| --- | --- |
| Git release for this Full-run procedure | `022e9ef2b5e33e8f762ab52fc01f75acd33e613d` |
| MTA application source represented by that release | `ba32643250c1c3b916cd400fd801ae88b57122c6` |
| Frontend/auth corrections included | `c63161ed35955add4ffdddf07042e131d484ca15` |
| Project | `vectorflow` |
| Clone and private environment file | `D:/VectorFLOW` and `D:/VectorFLOW/.env` |
| This installation's input copy | `D:/VectorFLOW-Input`, outside Git |
| Configuration and operation records | `D:/VectorFLOW-Operations`, outside Git |
| Application address | `http://127.0.0.1:8091` |

Build all four application images from the pinned release. Record their actual image IDs after building; do not substitute a retained image or database.

The earlier installation is `I:/VectorFLOW`. Its runbooks are `release/SOURCE_BUILD.md`, `release/CSV_STARTER_RUN.md` and `release/CSV_DAILY_RUN.md`. The completed large-data G1 handoff is recorded in `docs/handoff-3005/BOUNDED_RECOVERY_8080.md`, documentation checkpoint `c53cab1d`, MTA source `67aebd28`. These are historical references. Leave that installation and the current fast 8080 baseline unchanged.

## 2. Check the target

Requires Git, PowerShell 5.1 or 7, Docker Desktop using Linux/amd64 containers, Compose 2.24.4 or later, repository access and internet access for the first build. The data package is offline; the application build downloads pinned dependencies and base images.

The name `vectorflow` is already used on the current shared Docker host. Use a clean target computer or independent Docker environment. Do not remove existing resources to reuse the name.

```powershell
$ErrorActionPreference = 'Stop'
$InstallDir = 'D:/VectorFLOW'
$InputDir = 'D:/VectorFLOW-Input'
$OperationsDir = 'D:/VectorFLOW-Operations'
foreach ($Path in @($InstallDir, $InputDir, $OperationsDir)) {
    if (Test-Path -LiteralPath $Path) { throw "Existing target: $Path. Do not overwrite it." }
}
docker version
if ($LASTEXITCODE -ne 0) { throw 'Docker is unavailable' }
docker compose version
if ($LASTEXITCODE -ne 0) { throw 'Compose is unavailable' }
$Existing = docker ps -aq --filter label=com.docker.compose.project=vectorflow
if ($LASTEXITCODE -ne 0 -or $Existing) { throw 'Existing vectorflow containers' }
$Existing = docker volume ls -q --filter label=com.docker.compose.project=vectorflow
if ($LASTEXITCODE -ne 0 -or $Existing) { throw 'Existing vectorflow volumes' }
$Existing = docker network ls -q --filter label=com.docker.compose.project=vectorflow
if ($LASTEXITCODE -ne 0 -or $Existing) { throw 'Existing vectorflow network' }
if (Get-NetTCPConnection -State Listen -LocalPort 8091 -ErrorAction SilentlyContinue) {
    throw 'Port 8091 is occupied'
}
```

Check Docker/host memory and free space on the Docker, source, input and records drives:

```powershell
docker info --format 'Docker CPUs={{.NCPU}} MemoryBytes={{.MemTotal}}'
Get-CimInstance Win32_OperatingSystem |
    Select-Object TotalVisibleMemorySize, FreePhysicalMemory
Get-PSDrive -PSProvider FileSystem |
    Select-Object Name, @{Name='FreeGiB';Expression={[math]::Round($_.Free / 1GB, 1)}}
```

The earlier large calculation approached 8 GiB for one worker. That is not a whole-installation requirement or proof that the new package fits. Builds, PostgreSQL, serving processes and other jobs also need memory. Keep at least 2 GiB host memory and 20 GiB disk free on the relevant backing drives during work. Do not start large initialization until the delivered package's storage/history footprint and resource fit are confirmed. Do not resize Docker, raise a limit or stop another owner's services to force a fit.

Normal Compose defaults impose no application CPU/RAM ceiling. The optional 4 GiB test overlay is not qualified for this large package. This guide changes no resource allocation.

## 3. Clone and configure

```powershell
git clone --single-branch --branch codex/bounded-ui-recovery `
  git@github.com:yurtse/freshvcf.git D:/VectorFLOW
if ($LASTEXITCODE -ne 0) { throw 'Clone failed' }
Set-Location D:/VectorFLOW
git checkout --detach 022e9ef2b5e33e8f762ab52fc01f75acd33e613d
if ($LASTEXITCODE -ne 0) { throw 'Release checkout failed' }
git rev-parse HEAD
git status --porcelain
```

Expect the release above and an empty tracked-change status. The fixed checkout avoids unfinished work at the branch tip.

```powershell
Copy-Item -LiteralPath .env.example -Destination .env
New-Item -ItemType Directory -Path D:/VectorFLOW-Operations
notepad D:/VectorFLOW/.env
```

Maintain these values in **`D:/VectorFLOW/.env`**. Keep the other template entries, including the native identity settings set to `image`.

```dotenv
VF_PROJECT=vectorflow
VF_IMAGE_PREFIX=vectorflow
VF_RELEASE=source
VF_BIND_ADDRESS=127.0.0.1
VF_HTTP_PORT=8091
VF_PUBLIC_URL=http://127.0.0.1:8091
VF_PUBLIC_WS_URL=ws://127.0.0.1:8091
PG_ADMIN_USER=vectorflow_admin
MTA_DB_NAME=vectorflow_mta
MTO_DB_NAME=vectorflow_mto
VF_ADMIN_EMAIL=
VF_ADMIN_NAME=
VF_ADMIN_PASSWORD=
VF_CSV_INPUT_DIR=D:/VectorFLOW-Input
VF_DAILY_STATE_DIR=D:/VectorFLOW-Operations
COMPOSE_PATH_SEPARATOR=;
COMPOSE_FILE=compose.yaml;D:/VectorFLOW-Operations/vectorflow.yaml
```

Enter your new application administrator email/name. Leave `VF_ADMIN_PASSWORD` blank to enter and confirm it privately during installation. If you keep it in `.env`, keep the file private. Editing these fields after installation does not reset an account. The password policy requires at least eight characters, an uppercase letter and a special character, and rejects common/similar passwords.

Database passwords are generated on the first install. The administrator is `vectorflow_admin`. The default service users are:

| Service | Installer user | Runtime user |
| --- | --- | --- |
| MTA | `vectorflow_mta_installer` | `vectorflow_mta_runtime` |
| Authentication | `vectorflow_auth_installer` | `vectorflow_auth_runtime` |
| MTO | `vectorflow_mto_installer` | `vectorflow_mto_runtime` |

Owner roles do not have login passwords. Generated passwords and signing keys live in private Docker secret volumes and are routed only to the services that need them. The admin password is `source/postgres_admin_password` in `vectorflow_secret_store`, mounted as `/secrets/private/source/postgres_admin_password` by secret initialization. Adding `PG_ADMIN_PASSWORD` or `POSTGRES_PASSWORD` to `.env` does not configure this installer.

Create the deployment configuration:

```powershell
notepad D:/VectorFLOW-Operations/vectorflow.yaml
```

Save this content. It gives this installation its own shared authentication site-key namespace without changing permission caching or session expiry.

```yaml
services:
  auth:
    environment:
      VF_AUTH_SITE_CACHE_URL: redis://redis:6379/1
      VF_AUTH_SITE_KEY_NAMESPACE: vectorflow
```

Keep `.env`, secrets, inputs and operation records outside Git. Do not print or retain resolved Compose configuration; it can contain private values.

## 4. Build, install and start

From `D:/VectorFLOW`, run one command at a time:

```powershell
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Configuration is invalid' }
docker compose build
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
docker compose images
docker compose run --rm install
if ($LASTEXITCODE -ne 0) { throw 'Installation failed; retain the error before any recovery' }
docker compose up -d --no-build --wait
if ($LASTEXITCODE -ne 0) { throw 'Startup failed' }
docker compose ps
```

The single install command generates secrets, creates the new databases/roles, applies real migrations and creates your administrator. It does not load masters, register an opening or calculate a day. Do not run a separate migration command against another installation.

Expect six running/healthy services. Open `http://127.0.0.1:8091` and sign in with your new administrator and normal CAPTCHA. A blank installation has no business results. Keep build/installation output and actual image IDs with your operation records.

## 5. Connect the package and initialize once

**Pending data handoff:** fill these details from its delivery note. Do not invent dates or use another installation's bound folder.

```powershell
$InputPackage = '<ABSOLUTE_OFFLINE_PACKAGE_PATH>'
$BusinessDates = @('<DATE_1>', '<DATE_2>', '<DATE_3>')
```

The package must supply an unbound native CSV opening, `opening/opening-manifest.json`, its required original/control files and complete dated raw batches with `batch.json` and `READY`. Its manifest/date roster and source/site compatibility come from the data handoff. The launcher checks internal identities; you do not enter UUIDs or checksums manually.

```powershell
if ($InputPackage.StartsWith('<') -or -not (Test-Path -LiteralPath $InputPackage)) {
    throw 'Wait for the data package and enter its delivered path'
}
if ($BusinessDates.Count -ne 3 -or ($BusinessDates | Where-Object { $_ -notmatch '^\d{4}-\d{2}-\d{2}$' })) {
    throw 'Enter the three business dates from the data handoff'
}
if (Test-Path -LiteralPath (Join-Path $InputPackage 'binding.json')) {
    throw 'That package is already bound to an installation'
}
if (Test-Path -LiteralPath D:/VectorFLOW-Input) { throw 'Working input folder already exists' }
Copy-Item -LiteralPath $InputPackage -Destination D:/VectorFLOW-Input -Recurse
Set-Location D:/VectorFLOW
.\vf.ps1 csv-init
if ($LASTEXITCODE -ne 0) { throw 'Initialization failed; preserve its receipt' }
```

Expect `INITIALIZED` and `READY_FOR_FIRST_CSV_DAY`. The command registers/certifies this opening, loads the native master families and configures master serving. It writes binding/access files into the working copy. The original offline package stays reusable. Do not repeat initialization after a daily run.

## 6. Run one date at a time

```powershell
.\vf.ps1 csv-day $BusinessDates[0]
if ($LASTEXITCODE -ne 0) { throw 'First daily operation failed; stop' }
```

Wait for **PUBLISHED**. The command freezes/validates CSV, executes the native day, prepares reports, selects that generation, restarts only its MTA and verifies serving. MTA reports may be unavailable during processing.

Before the next date, check the browser:

- Displayed date and selected run match the completed operation.
- BPR and RRR have readable results, correct counts/filters and actual CSV downloads.
- BTR works on direct reload, standalone view and both combined orientations, including scrolling.
- Applicable Planning/Guided grids and graphs load; master screens remain readable.
- Record click-to-usable time, filter/page behavior, export completion, rejection diagnostics and unavailable/empty results. Check values and files against the run's supplied/produced records; a count or HTTP 200 alone is not acceptance.

Record the run/output identities from the receipt, then continue:

```powershell
.\vf.ps1 csv-day $BusinessDates[1]
if ($LASTEXITCODE -ne 0) { throw 'Second daily operation failed; stop' }
# Check the second date's reports before continuing.
.\vf.ps1 csv-day $BusinessDates[2]
if ($LASTEXITCODE -ne 0) { throw 'Third daily operation failed; stop' }
```

Each date uses this installation's own preceding successful state. Do not substitute another arm's outputs or seed calculated results as inputs.

## 7. Full and split paths

| Path | Supported interface and boundary |
| --- | --- |
| Full | `vf.ps1 csv-day DATE`, as above |
| Up to BPR → Post BPR | Native report-placement entry and continuation exist for their qualified owned-test contract. No runnable GulfOil package procedure is released here. |
| Up to DBM → Post DBM | Same restriction; Post DBM must continue its own accepted DBM prefix. |

For interface reference after building/installing, these commands display help without calculating:

```powershell
docker compose --profile daily run --rm --no-deps -T daily manage.py run_production_report_placement --help
docker compose --profile daily run --rm --no-deps -T daily manage.py continue_production_report_placement --help
```

The first entry accepts Full/UptoBPR/UptoDBM; the continuation accepts PostBPR/PostDBM. They require a supported captured site/hook/report configuration, native ownership, registration and phase/action receipts. Do not fill parameters with trial IDs or bypass a guard.

**OPEN:** the retained large opening is GulfOil; the qualified scope profile is SUPPLIED-INSTANCE with explicit no-op test hooks. That pairing is rejected. Data generation or a database rename does not resolve it. The draft simple scope adapter is not an accepted part of the pinned release or a runnable GulfOil handoff.

Full/split comparisons need identical external inputs in independent initialized installations. Each computes its own predecessors. Post BPR resumes accepted BPR and completes the remaining tail; it is not followed by another Up to DBM call. Post DBM resumes accepted DBM. Never run Full and a split journey over one already-mutated date. Keep manual actions/remarks identical or absent for equivalence. Simultaneous workers require separate capacity.

This contract/command gap remains open without blocking the rest of the guide.

## 8. Stop, resume and restart

Stop at the first failed command, wrong run/date/value, missing publication, unreadable required report, failed export or resource pressure. Keep the input copy, `.env`, records and matched database/file/secret volumes. Do not reset/reseal, delete volumes, replay committed days, regenerate secrets or increase resources as recovery.

Use these existing recovery commands after diagnosing the recorded failure:

| Recorded state | Command and limit |
| --- | --- |
| Initialization committed but completion/configuration/serving failed; no daily run exists | `.\vf.ps1 csv-init -Resume`, completing the same checkpoint |
| Calculation committed but preparation/selection/serving failed | `.\vf.ps1 csv-day DATE -Resume`, using that receipt's date without accepted calculation replay |
| Latest published date, stopped MTA | Same dated `csv-day DATE -Resume`; it validates the current selection before service-only recovery and cannot reselect an older day |
| Failed/interrupted calculation | Stop for reconciliation; this guide provides no automatic calculation retry |

For a planned service restart after publication:

```powershell
docker compose restart mta
if ($LASTEXITCODE -ne 0) { throw 'MTA restart failed' }
docker compose ps
Invoke-RestMethod http://127.0.0.1:8091/readyz
```

Expect readiness and the same selected date/run in the browser. Restart does not install, migrate, reload inputs or calculate. For an orderly stop/start of this new installation, use `docker compose stop`, then `docker compose up -d --no-build --wait`. Do not delete volumes or use old 8080 recovery controllers.

## 9. Remaining acceptance

- **Data:** package path/manifest/dates, file checks, site compatibility and capacity. The separate data task owns this.
- **Contract:** supported GulfOil split scopes and a runnable operator procedure. Still open; this guide authorizes no extension or bypass.
- **Runtime:** the human's clean build/install/initialization, sequential execution, report/export/browser checks and supported restart/recovery results.
- **Step 6:** the final runbook of commands actually exercised successfully and their observed limits.

Keep product Git/image identity, external inputs and deployment/operation records separate. This is a completed orchestration guide, not Stage 5 runtime or Step 6 acceptance.
