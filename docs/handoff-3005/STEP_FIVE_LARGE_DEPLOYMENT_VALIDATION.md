# VectorFLOW — Step Five: Large Deployment Validation

This is the manual installation and validation guide. **You run the commands.** The application project is named `vectorflow`. The code, offline input data and generated operation records stay in separate folders.

These commands have not yet been exercised as a new large-data installation. This document does not claim a completed Step Five validation.

## 1. Folders

| Location | Contents |
| --- | --- |
| `D:/VectorFLOW` | Fresh Git clone and its private `.env` file |
| `I:/VectorFLOW-Data` | Prepared offline opening, master data, raw facts and installation configuration templates; outside Git |
| `I:/VectorFLOW-Operations` | Receipts and operation records created when you initialize/process the data |

The offline folder is already prepared. Copy the **whole folder** to the installation computer; change the paths in `.env` if its drive/location differs. Do not place it inside the Git clone.

```text
I:/VectorFLOW-Data/
  opening/                     Master, configuration and opening-state CSV files
  2026-04-08/                   Retained daily raw CSV files
  opening-original.json        Required original opening for the existing importer
  binding-template.json       Import configuration; installer fills its own identity
  consumer-opening.json       Initial report/workflow input
  permissions.json            Product/location catalogue
  config/
    vectorflow.env.example
    vectorflow.compose.yaml
  STEP_FIVE_LARGE_DEPLOYMENT_VALIDATION.md
```

The pack contains about97,000 product/location pairs, opening7April2026 and one currently available fact date, **8April2026**. The agreed additional dates, **9–10April**, have not been generated or included yet. Do not run those dates until their complete raw batches are supplied. Do not copy or rename8April to fabricate another date.

Keep the provided internal control files and CSV filenames intact. You do not need to enter reference IDs or checksums manually.

## 2. Check the installation environment

Requires Git, PowerShell5.1 or7, Docker Desktop running Linux containers, Compose2.24.4 or later, and internet access for Git, base images and build dependencies. The **data** is offline; the first application build is not an air-gapped build.

Use a clean Docker environment. The project name `vectorflow` is already used on the current shared computer. **Do not install over it, remove its resources or stop the existing8080 application.** The same normalized name is suitable on a clean target computer/Docker environment.

Check that the destination folder does not exist, the project name is unused and port8091 is free:

```powershell
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath D:/VectorFLOW) { throw 'D:/VectorFLOW already exists' }
docker version
if ($LASTEXITCODE -ne 0) { throw 'Docker is unavailable' }
docker compose version
$ExistingContainers = docker ps -aq --filter label=com.docker.compose.project=vectorflow
if ($LASTEXITCODE -ne 0 -or $ExistingContainers) { throw 'Project unavailable; use a clean Docker target' }
$ExistingVolumes = docker volume ls -q --filter label=com.docker.compose.project=vectorflow
if ($LASTEXITCODE -ne 0 -or $ExistingVolumes) { throw 'Existing project volumes; stop' }
$ExistingNetworks = docker network ls -q --filter label=com.docker.compose.project=vectorflow
if ($LASTEXITCODE -ne 0 -or $ExistingNetworks) { throw 'Existing project network; stop' }
if (Get-NetTCPConnection -State Listen -LocalPort 8091 -ErrorAction SilentlyContinue) { throw 'Port8091 is occupied' }
```

If any project resources or a listening8091 connection appear, stop here and use a clean target. Do not use `down -v`, prune, reset or delete an existing installation.

Large-data capacity is not proved by the small starter. The provided finite test configuration allows8GiB for initialization/daily work. Before starting, allow that worker plus the other services and at least2GiB host headroom; keep at least52GiB free on the Docker/build backing disk. Do not increase limits or repeat a failed calculation to force completion. This is a validation configuration, not a production sizing recommendation.

## 3. Clone VectorFLOW

```powershell
git clone --single-branch --branch codex/bounded-ui-recovery `
  git@github.com:yurtse/freshvcf.git D:/VectorFLOW
if ($LASTEXITCODE -ne 0) { throw 'Git clone failed' }
Set-Location D:/VectorFLOW
git rev-parse HEAD
```

Keep the displayed revision with your validation results. The branch name identifies the existing delivery branch; the installation/project name remains `vectorflow`.

## 4. Create and maintain the environment file

Create **`D:/VectorFLOW/.env`** from the prepared template:

```powershell
Copy-Item -LiteralPath I:/VectorFLOW-Data/config/vectorflow.env.example -Destination .env
notepad .env
```

Edit the paths if needed. The important settings are:

```dotenv
VF_PROJECT=vectorflow
VF_IMAGE_PREFIX=vectorflow
VF_RELEASE=source
VF_HTTP_PORT=8091
PG_ADMIN_USER=vectorflow_admin
MTA_DB_NAME=vectorflow_mta
MTO_DB_NAME=vectorflow_mto
MTA_INSTALLER_ROLE=vectorflow_mta_installer
MTA_RUNTIME_ROLE=vectorflow_mta_runtime
AUTH_INSTALLER_ROLE=vectorflow_auth_installer
AUTH_RUNTIME_ROLE=vectorflow_auth_runtime
MTO_INSTALLER_ROLE=vectorflow_mto_installer
MTO_RUNTIME_ROLE=vectorflow_mto_runtime
VF_ADMIN_EMAIL=
VF_ADMIN_NAME=
VF_ADMIN_PASSWORD=
VF_CSV_INPUT_DIR=I:/VectorFLOW-Data
VF_DAILY_STATE_DIR=I:/VectorFLOW-Operations
```

The full template also contains the required public origins, native identity defaults and Compose configuration. Keep those entries. Change the port **before building** if needed.

**Application administrator:** enter your new email/name in `.env`. Leave `VF_ADMIN_PASSWORD` blank to enter and confirm it privately during installation, or maintain your chosen application-login password in this ignored `.env`. Do not use an existing deployment's credentials. Password policy requires at least8 characters, an uppercase letter and a special character, and rejects common/similar passwords.

**Database administrator and service passwords:** the current installer generates them automatically on the first install. The database admin username is `PG_ADMIN_USER`; service usernames are listed above. Passwords are stored in the private Docker volume **`vectorflow_secret_store`**, under `/secrets/private/source/` inside the secret-initialization container, including `postgres_admin_password` and the service-specific password files. Each service receives only its required files. They are not plaintext `.env` settings in this installation path. Adding `POSTGRES_PASSWORD` or `PG_ADMIN_PASSWORD` to `.env` does not configure the current installer. Keep the secret volumes with the database volumes for recovery; do not regenerate them.

Neither `.env`, the offline data, generated passwords nor operation records should be committed to Git.

## 5. Build, install and start

Run one command at a time from `D:/VectorFLOW`. Stop on any error.

```powershell
docker compose build
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
docker compose run --rm install
if ($LASTEXITCODE -ne 0) { throw 'Installation failed; do not repeat or reset' }
docker compose up -d --no-build --wait
if ($LASTEXITCODE -ne 0) { throw 'Startup failed' }
docker compose ps
```

The installer creates the new private databases/roles, applies migrations, generates secrets and creates your application administrator. It does not load business data or calculate a day. Open **http://127.0.0.1:8091** and sign in normally, including CAPTCHA.

## 6. Load the offline opening and master data once

```powershell
.\vf.ps1 csv-init
if ($LASTEXITCODE -ne 0) { throw 'Initialization failed; retain its receipt' }
```

Expect `INITIALIZED` and `READY_FOR_FIRST_CSV_DAY` in the operation receipt. Master-data screens should now have their initialized data; calculated reports require a completed day. The launcher writes its binding/access files automatically. Do not enter installation IDs manually or reuse this now-bound data folder for a different database.

## 7. Run a complete day and validate its reports

```powershell
.\vf.ps1 csv-day 2026-04-08
if ($LASTEXITCODE -ne 0) { throw 'Daily operation failed; retain its receipt' }
```

Wait for **PUBLISHED**. The command handles CSV intake, calculation, report preparation, selection and its own MTA restart. Do not interrupt it because reports are temporarily unavailable during processing.

After publication, sign in/refresh and check:

- BPR and RRR: visible results, matching counts, positive/zero-result filters and actual CSV downloads.
- BTR: direct reload, standalone view and both combined orientations; readable rows, scrolling and filters.
- Planning and Guided reports: relevant grids/graphs, filters and navigation.
- Master data: expected products, locations and attributes remain readable.
- Displayed run date is8April; record the operation's run identity, any rejection diagnostics, time to usable screens and export completion. An empty success response or a collapsed grid is not a pass.

Once the new9/10April raw batches have been supplied, run these separately, in order, checking the preceding day's reports before continuing:

```powershell
# NOT READY YET: run only when the corresponding complete batch is supplied.
.\vf.ps1 csv-day 2026-04-09
if ($LASTEXITCODE -ne 0) { throw '9April failed; stop' }
# Validate9April reports before entering the next command.
.\vf.ps1 csv-day 2026-04-10
if ($LASTEXITCODE -ne 0) { throw '10April failed; stop' }
```

Each date must use this installation's own preceding committed day. Never copy calculated outputs into the raw-data folder. Preserve operation receipts, original inputs and failures.

## 8. Run by scope using the same dataset

This is a separate execution choice, not an extra sequence to run after Full on the same date.

| Path | Meaning |
| --- | --- |
| Full | Execute the complete date in one operation |
| Up to BPR → Post BPR | Stop after accepted BPR work, then continue that same run through its remaining phases |
| Up to DBM → Post DBM | Stop after accepted DBM work, then continue that same run through its remaining phases |

All paths must accept the same offline opening/raw facts. Post BPR/Post DBM continue their accepted run; they do not import the date again. A fair comparison uses independent installations with their own persisted predecessors; it never resets one database or runs Full over an already accepted scoped date.

**Operator-command gap:** the present `vf.ps1 csv-day` accepts Full only. It has no `-Scope` option. The underlying report-placement scope commands exist, but require separate captured configuration, registration, stage/run identities, preparation and serving lifecycle. The older `run_production_post_bpr` / `run_production_post_dbm` commands also contain retained-test boundaries and must not be substituted as generic commands for this large pack.

This section is therefore not yet a runnable simple scoped procedure. The requested launcher support is awaiting your decision. No fictional `-Scope` command is provided as if it already works. After that support is implemented and verified, this section will contain the exact manual scope and continuation commands for the same data folder; you will execute them yourself.

## 9. Stop and retain results on failure

Stop at the first failed command, missing publication, wrong run/date, incorrect values, unreadable report or resource failure. Keep the data folder, `.env`, operation folder, Docker database/secret volumes and the error output. Do not repeat initialization, delete volumes, reset databases, replay a committed date or change passwords to recover.

The current shared8080 baseline and other installations remain untouched. A final exercised-command runbook can be completed from your actual successful results.
