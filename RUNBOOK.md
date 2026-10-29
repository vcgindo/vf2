# VectorFLOW — clone, build and run CSV days

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

Use Docker Desktop with Linux containers, Git, and PowerShell 5.1 or 7. Run each command separately and stop if it fails. Choose an unused installation directory, Docker project and HTTP port; this creates a fresh installation.

## 1. Clone and copy your CSV package

The first two variables are local parameters. The example selects the retained V3 package and a new checkout beside the existing `I:/VectorFLOW` installation.

```powershell
$InstallDirectory = 'I:/VectorFLOW-8089'
$CsvPackage = 'I:/data/vectorflow-synthetic-97097-knownstock-20261029-v3'
git clone --depth 1 --single-branch --branch codex/bounded-ui-recovery git@github.com:yurtse/freshvcf.git $InstallDirectory
Set-Location $InstallDirectory
git rev-parse HEAD
New-Item -ItemType Directory data
Copy-Item -LiteralPath $CsvPackage -Destination ./data/input -Recurse
Copy-Item .env.example .env
notepad .env
```

Copy an **unbound** package, not another installation's `binding.json`, operation records or database. Keep the original package. `data/input` is the default CSV location; `data/operations` is created by the execution scripts. Both are excluded from Git and the Docker build context. Absolute external paths remain supported through `.env`.

## 2. Set local parameters in `.env`

Replace these entries in the copied file. Enter your administrator email and name; leave the password blank for the private installation prompt.

```dotenv
VF_PROJECT=vectorflow-local-8089
VF_HTTP_PORT=8089
VF_ADMIN_EMAIL=
VF_ADMIN_NAME=
VF_ADMIN_PASSWORD=
```

For the V3 package shown above, also replace these archive-policy entries with its existing bounded large-package values. Its opening JSON alone is 438,786,807 bytes, larger than the standard 256 MiB archive expansion allowance:

```dotenv
VF_INPUT_ARCHIVE_MAX_UNCOMPRESSED_BYTES=2147483648
VF_INPUT_ARCHIVE_MAX_COMPRESSED_BYTES=268435456
```

These are input-download archive size limits, not RAM allocations. Other packages keep the standard defaults unless their size requires an explicit policy.

Keep the other defaults. Image names, HTTP/WebSocket origins and the auth cache namespace follow these parameters. The default binding is localhost. Data paths are relative to this checkout; `csv-init` records their resolved paths automatically. Use a fresh PowerShell window without inherited `COMPOSE_FILE`, `COMPOSE_PATH_SEPARATOR` or `COMPOSE_PROJECT_NAME` shell overrides. Do not copy the old installation's `.env`.

For an explicit subnet, uncomment/set these entries in `.env`. The YAML already comes from the clone:

```dotenv
COMPOSE_PATH_SEPARATOR=;
COMPOSE_FILE=compose.yaml;compose.local.yaml
VF_NETWORK_SUBNET=100.127.240.32/27
```

This subnet was unused on the inspected Windows/Docker/WSL environment on 29 October 2026. Choose another unused subnet if your network/VPN changes or you create another installation. Without this optional override, Docker allocates its normal bridge subnet. The tracked YAML contains no machine-specific paths or project names. Do not change shared Docker/WSL settings or remove another installation to make room.

## 3. Build, install and start

```powershell
docker compose --profile '*' config --quiet
docker compose build
docker compose run --rm install
docker compose up -d --no-build --wait
docker compose ps
```

Continue only after each command succeeds. Build uses the clean committed source for all application images and may reuse valid build cache. Set the port before building because the frontend socket origin is compiled into the image. Installation generates private database/signing secrets and creates the new administrator. It does not initialize business data or run a day.

No runtime CPU/RAM ceilings or forced serial build are added by the standard configuration. Docker Desktop/WSL's actual allocation still applies. PostgreSQL and Redis have no host port mapping; the frontend uses `http://127.0.0.1:8089` for these parameters.

## 4. Initialize once

```powershell
.\vf.ps1 csv-init
```

Wait for success. The script initializes the opening and masters, writes the binding/access configuration and prepares master-data serving. It preserves the selected Compose files. Do not initialize the same package again.

## 5. Run the daily batches in order

For V3, day one and day two are:

```powershell
.\vf.ps1 csv-day 2026-04-08
.\vf.ps1 csv-day 2026-04-09
```

Run the second command only after the first returns **PUBLISHED**. The same command handles subsequent supplied dates, in order:

```powershell
.\vf.ps1 csv-day 2026-04-10
.\vf.ps1 csv-day 2026-04-11
```

Each command owns staging, full-day calculation, persistence, report/archive preparation, selection, MTA startup, built-in readiness and publication acknowledgement. No manual preparation/selection/acknowledgement commands are needed. Other CSV packages use their own actual dates. Do not run another day from a second terminal or the browser concurrently.

## 6. Check the browser

After a daily command returns **PUBLISHED**, open **http://127.0.0.1:8089**, sign in with the installed administrator and check the selected date's reports, filters and downloads. During daily processing MTA is stopped; login/report requests may return 503 until publication finishes. A blank installation has no calculated reports.

On an error, retain the output and `data/operations` records, then diagnose the failed phase. Do not reset volumes, repeat initialization or recalculate a committed day. Use `-Resume` only after reconciling that state. A normal later restart uses `docker compose stop` followed by `docker compose up -d --no-build --wait` with this same `.env` and data.

Detailed installation/SMTP reference: [release/SOURCE_BUILD.md](release/SOURCE_BUILD.md). Daily recovery reference: [release/CSV_DAILY_RUN.md](release/CSV_DAILY_RUN.md). Retained prebuilt packages: [release/RUNBOOK.md](release/RUNBOOK.md). The prior captured-input recovery is separate from measuring this fresh build/ingestion/browser run.
