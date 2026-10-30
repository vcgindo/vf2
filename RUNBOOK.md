# VectorFLOW — clean clone, build, initialize and run CSV scopes

**Preserve the existing frontend and MTO. No redesign or business-rule changes.**

Updated 31 October 2026 for `codex/initialization-bulk-optimization`. Code reviewed: `5437c5b2cf4854b480e0d822fcc3af1077c705d4`, including the transit, InputData, report-configuration and GIT read corrections. Record the actual cloned commit: a later branch tip is a different build.

Requires Git, PowerShell 5.1 or 7, and Docker Desktop with Linux/amd64 containers and Compose 2.24.4 or later. No host Python/Node or prebuilt image ZIP is needed. This procedure creates a **new installation**; it does not upgrade/reset 8089, 8090, 8091 or another existing instance. Run one command at a time and stop on any error.

## 1. Clone and copy the unbound CSV package

Choose a new directory. The example uses the exact V3 known-stock package from the latest optimized April 8/9 test, not the earlier V2 or small October starter.

```powershell
$InstallDirectory = 'I:/VectorFLOW-clean-20261031'
$CsvPackage = 'I:/data/vectorflow-synthetic-97097-knownstock-20261029-v3'

if (Test-Path -LiteralPath $InstallDirectory) { throw 'Choose a new installation directory' }
if (Test-Path -LiteralPath "$CsvPackage/binding.json") { throw 'Use the original unbound package' }
git clone --depth 1 --single-branch --branch codex/initialization-bulk-optimization git@github.com:yurtse/freshvcf.git $InstallDirectory
if ($LASTEXITCODE -ne 0) { throw 'Clone failed' }
Set-Location $InstallDirectory
git rev-parse HEAD

New-Item -ItemType Directory data | Out-Null
Copy-Item -LiteralPath $CsvPackage -Destination ./data/input -Recurse
Copy-Item .env.example .env
notepad .env
```

Keep the original package unchanged. Copy neither a serving installation's `binding.json` nor its operations/database. Each independent installation needs its own working package, project, port, volumes and receipts. `data/input` and `data/operations` are excluded from Git and Docker build context.

V3 has an April 7 opening, 97,097 processed SKU/location pairs, 97,464 raw master rows and supplied April 8–11 daily batches. All 246 inventoried files were verified identical between the retained source and optimized installation on 30 October. Do not regenerate facts, change dates or import another engine's calculated outputs.

## 2. Configure the new installation

Replace these entries in the copied `.env`. `8092` is only an example: check that your chosen port and project name are unused. Enter your administrator email/name; leave the password blank for the private installation prompt.

```dotenv
VF_PROJECT=vectorflow-clean-20261031
VF_HTTP_PORT=8092
VF_ADMIN_EMAIL=
VF_ADMIN_NAME=
VF_ADMIN_PASSWORD=
VF_CSV_INPUT_DIR=./data/input
VF_DAILY_STATE_DIR=./data/operations
VECTORFLOW_SCOPE_POLICY=generic
```

For this V3 package, replace the archive-policy values too. Its opening JSON is 438,786,807 bytes, exceeding the standard 256 MiB expanded-archive allowance:

```dotenv
VF_INPUT_ARCHIVE_MAX_UNCOMPRESSED_BYTES=2147483648
VF_INPUT_ARCHIVE_MAX_COMPRESSED_BYTES=268435456
```

These are download archive-size policies, **not RAM allocations**. Keep other defaults. Set the port before building: the original frontend's socket origin is compiled into the image. Secrets are generated privately during installation; never commit `.env` or share resolved Compose configuration.

Use a fresh PowerShell session without inherited `COMPOSE_FILE`, `COMPOSE_PATH_SEPARATOR` or `COMPOSE_PROJECT_NAME` shell overrides. The launcher persists its own resolved paths/Compose overrides in `.env`; keep those for subsequent operations.

If an explicit bridge subnet is needed, the clone already contains `compose.local.yaml`. Set these entries in `.env`, using a genuinely unused, non-overlapping subnet:

```dotenv
COMPOSE_PATH_SEPARATOR=;
COMPOSE_FILE=compose.yaml;compose.local.yaml
VF_NETWORK_SUBNET=100.127.240.32/27
```

The subnet above is an example, not a current availability claim. Without this override Docker allocates its normal bridge. If address pools are exhausted, retain the error and configure an admitted unused subnet; do not prune networks, remove another installation or change shared Docker/WSL settings. This application needs its service network; the separate legacy benchmark's network-free SQL arrangement does not apply here.

## 3. Build, install and start

```powershell
docker compose --profile '*' config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose validation failed' }

docker compose build
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }

docker compose run --rm install
if ($LASTEXITCODE -ne 0) { throw 'Installation failed; preserve state' }

docker compose up -d --no-build --wait
if ($LASTEXITCODE -ne 0) { throw 'Startup failed' }

docker compose ps
```

All application images come from the same clean committed source. Installation creates new databases/least-privilege roles, private secrets, application metadata and your administrator; it loads no business data and calculates no day. Expect six healthy serving services. Blank MTA health is available, but report readiness remains unavailable until publication.

Standard Compose adds no runtime CPU/RAM ceilings or forced serial build. Docker Desktop/WSL's actual allocation still applies. Do not add `release/compose.resource-test.yaml` for an unrestricted run. PostgreSQL/Redis have no host ports. The example URL is **http://127.0.0.1:8092**.

## 4. Initialize once

```powershell
.\vf.ps1 csv-init
```

Expect `INITIALIZED` / `READY_FOR_FIRST_CSV_DAY` in `data/operations/onboarding.json`. The launcher validates the CSV opening, registers this installation, loads masters/opening, certifies them, binds access configuration and starts initialized master-data serving. No manual UUID, hash, JSON binding, grant or selection command is needed. Calculated reports follow a daily run. Do not initialize again to fix a daily failure.

## 5. Normal Full daily run

For this V3 package:

```powershell
.\vf.ps1 csv-day 2026-04-08
```

Wait for **PUBLISHED** before Day2:

```powershell
.\vf.ps1 csv-day 2026-04-09
```

Day2 uses this installation's own persisted Day1 closing. Subsequent supplied batches use the same command with `2026-04-10` and `2026-04-11`, in order. Other packages use their own actual dates; never guess the civil date.

Each command owns staging, validation, calculation, persistence, reports, InputData archive, selection, MTA restart, actual serving checks and publication acknowledgement. No manual report/selection/acknowledgement steps are needed. Do not launch competing daily/scope producers from another terminal or browser.

## 6. Alternative scoped paths

Choose **one path for each initialized date**. The following are alternatives, not steps to execute after section 5 or after one another. To compare Full versus split paths, use separate clean installations and unbound package copies. Never calculate the same date again merely to try another scope.

Keep `VECTORFLOW_SCOPE_POLICY=generic`. The initialized input must already declare the supported `generic-finalization-active-nms-v1` business policy and compatible report configuration. Admission checks this contract. Setting an environment key cannot enable an unsupported customer/site hook; do not rename a site or change input policies to bypass refusal.

| Path | Start | Finish the same date |
|---|---|---|
| Ordinary Full | `csv-day` | No continuation |
| Full with placement reporting | `csv-scope -Scope Full` | No continuation |
| Pause after BPR | `csv-scope -Scope UptoBPR` | `csv-scope -Scope PostBPR` |
| Pause after DBM | `csv-scope -Scope UptoDBM` | `csv-scope -Scope PostDBM` |

### A. Full with placement reporting

On a date not yet run in this installation:

```powershell
.\vf.ps1 csv-scope 2026-04-08 -Scope Full -InspectOnly
.\vf.ps1 csv-scope 2026-04-08 -Scope Full
```

### B. Pause after BPR, then finish

On an independent installation/date that has not started another path:

```powershell
.\vf.ps1 csv-scope 2026-04-08 -Scope UptoBPR -InspectOnly
.\vf.ps1 csv-scope 2026-04-08 -Scope UptoBPR
```

Wait for the BPR phase's **PUBLISHED** receipt. Review its available BPR/Planning views and complete any intended, authorized actions through the existing UI. Then continue the accepted phase; BPR is not repeated:

```powershell
.\vf.ps1 csv-scope 2026-04-08 -Scope PostBPR -InspectOnly
.\vf.ps1 csv-scope 2026-04-08 -Scope PostBPR
```

### C. Pause after DBM, then finish

On an independent installation/date that has not started another path:

```powershell
.\vf.ps1 csv-scope 2026-04-08 -Scope UptoDBM -InspectOnly
.\vf.ps1 csv-scope 2026-04-08 -Scope UptoDBM
```

Wait for the DBM phase's **PUBLISHED** receipt. Review phase-supported reports and, if intended, complete the existing authorized Apply/Sleep workflow. Continue the same accepted run:

```powershell
.\vf.ps1 csv-scope 2026-04-08 -Scope PostDBM -InspectOnly
.\vf.ps1 csv-scope 2026-04-08 -Scope PostDBM
```

`PostBPR` and `PostDBM` need their matching accepted prefix for the same date/installation. They bind its snapshots/action revision rather than replaying accepted stages. An `Upto...` phase being PUBLISHED means that phase is served; the **whole day** finishes only after its matching `Post...` completes. Start April 9 only after terminal completion; repeat your chosen split pair with `2026-04-09` for a split Day2.

`-InspectOnly` checks admission without calculating/selecting the phase. A pass is not execution success. Keep pending-day inputs/configuration/policy fixed. These supported commands do not constitute fresh browser or large-data acceptance of every scope on your new installation.

## 7. Open and check the UI

After the chosen command returns **PUBLISHED**, open **http://127.0.0.1:8092** (or your configured port) and sign in normally with CAPTCHA. Check the selected date **and phase**. Administrator access follows current data; ordinary users need their real roles and product/location scopes. While MTA is stopped for processing, login/report requests can return 503; wait for publication.

Check BPR → Show All; Planning → category → Grid View; and the reports available at the selected phase. For GIT, check From Parent / To Child and Location Wise / Transporter Wise. April 9 GIT can be validly empty; empty DBM/GIT is not proof that processing was skipped. Order Allocation uses its existing navigation; Elephant Order can legitimately be empty. InputData is an administrator download. Diagnostic/upload files exist only when their producing operation published them; missing captures are not fabricated as empty files.

New terminal daily selections carry the verified InputData ZIP checksum: downloads validate ownership, selection and compressed bytes without reconstructing every input fact. Older selection bundles keep their full audit. Publication proves built-in serving identity, not all browser workflows or response-time targets. Verify rows/counts/filters/actions/downloads separately.

## 8. Inspect, recover and restart

On error keep terminal output, `data/operations`, private input copy, generated overrides, `.env`, named volumes and private secrets. Diagnose the exact phase. Never reset volumes, run `down -v`, repeat initialization, import another binding or blindly repeat a failed calculation.

If the calculation/phase committed and only preparation/serving failed, resolve that cause and resume the matching recorded operation:

```powershell
# Ordinary Full day:
.\vf.ps1 csv-day 2026-04-08 -Resume

# Scoped operation: use the EXACT interrupted scope; PostBPR is an example:
.\vf.ps1 csv-scope 2026-04-08 -Scope PostBPR -Resume
```

Resume reuses accepted state/READY layers, including BTR when applicable; it does not authorize recalculation. An interrupted native scope may require explicit journal reconciliation first, separately from `-Resume`:

```powershell
.\vf.ps1 csv-scope 2026-04-08 -Scope PostBPR -Reconcile
```

Use this only for the diagnosed exact interrupted scope. Reconciliation verifies existing ownership/state and records the observed cut; it does not repair business rows or authorize uncertain replay. Follow its actual disposition. Ordinary Full `csv-day` failures use their daily receipt, not scope reconciliation. An interrupted opening before any daily capture can use `csv-init -Resume` to finish its recorded initialization/configuration; that is not daily recovery.

For a routine restart of this installation:

```powershell
docker compose stop
docker compose up -d --no-build --wait
docker compose ps
```

Keep the same clone, `.env`, input/access files and generated Compose overrides. Restart neither installs nor calculates. Do not apply `git pull` plus a rebuild to an initialized source-bound database as an undocumented upgrade; this is a clean-install guide.

Installation/SMTP details: [SOURCE_BUILD.md](release/SOURCE_BUILD.md). Small October sample: [CSV_STARTER_RUN.md](release/CSV_STARTER_RUN.md). Daily schema/recovery: [CSV_DAILY_RUN.md](release/CSV_DAILY_RUN.md). Prebuilt-package operations: [release/RUNBOOK.md](release/RUNBOOK.md).
