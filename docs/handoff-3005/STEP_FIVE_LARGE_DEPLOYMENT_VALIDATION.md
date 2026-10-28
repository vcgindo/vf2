# VectorFLOW — deploy and run

Fresh installation only. Use an unused project name and fresh input/operation folders. Keep 3005/8080 unchanged. Run each command separately and stop on an error.

## 1. Clone

Skip cloning if you already have this tag; use that clone's folder.

```powershell
git clone --depth 1 --single-branch --branch vectorflow-generic-scope-20261028 git@github.com:yurtse/freshvcf.git D:/VectorFLOW-Small
cd D:/VectorFLOW-Small
```

## 2. Choose one dataset

Small starter:

```powershell
Expand-Archive -LiteralPath I:/VectorFLOW-input/vectorflow-starter-csv-complete-20261019.zip -DestinationPath D:/VectorFLOW-Trial-Input
```

Or large v2:

```powershell
Copy-Item -LiteralPath I:/data/vectorflow-synthetic-97097-20261027-v2 -Destination D:/VectorFLOW-Trial-Input -Recurse
```

For another qualified CSV package, copy its unbound folder instead. Do not reuse a folder containing another installation's `binding.json`. The already-prepared `D:/VectorFLOW-Small-Input` can be used directly: skip extraction and set that path in `.env`.

## 3. Configure

```powershell
Copy-Item .env.example .env
New-Item -ItemType Directory D:/VectorFLOW-Trial-Operations
@('services:', '  auth:', '    environment:', '      VF_AUTH_SITE_CACHE_URL: redis://redis:6379/1', '      VF_AUTH_SITE_KEY_NAMESPACE: vectorflow-trial') | Set-Content D:/VectorFLOW-Trial-Operations/vectorflow.yaml -Encoding ASCII
notepad .env
```

Set these entries, replacing existing values. Enter your administrator email/name; leave the password blank for the install prompt. Keep other defaults.

```dotenv
VF_PROJECT=vectorflow-trial
VF_IMAGE_PREFIX=vectorflow-trial
VF_HTTP_PORT=8091
PG_ADMIN_USER=postgres
MTA_DB_NAME=vectorflow_mta
MTO_DB_NAME=vectorflow_mto
VECTORFLOW_SCOPE_POLICY=generic
VF_ADMIN_EMAIL=
VF_ADMIN_NAME=
VF_ADMIN_PASSWORD=
VF_CSV_INPUT_DIR=D:/VectorFLOW-Trial-Input
VF_DAILY_STATE_DIR=D:/VectorFLOW-Trial-Operations
COMPOSE_PATH_SEPARATOR=;
COMPOSE_FILE=compose.yaml;D:/VectorFLOW-Trial-Operations/vectorflow.yaml
```

The small YAML file supplies this release's auth cache settings. Database passwords are generated automatically into private Docker volumes.

## 4. Build, install, start

Run one command at a time; continue only after success.

```powershell
docker compose build
docker compose run --rm install
docker compose up -d --no-build --wait
```

Open **http://127.0.0.1:8091** and sign in with your administrator account.

## 5. Initialize and run

Initialize once:

```powershell
.\vf.ps1 csv-init
```

Choose a date from your package, then run Full:

```powershell
$Day = '2026-10-18'
.\vf.ps1 csv-day $Day
```

Wait for **PUBLISHED**, check reports/downloads, then change `$Day` to the next date and repeat.

| Dataset | Run dates, in order |
| --- | --- |
| Small | 2026-10-18, 2026-10-19 |
| Large v2 | 2026-04-08, 2026-04-09, 2026-04-10, 2026-04-11 |

For split comparisons, use a separate fresh installation/input copy and substitute one pair for Full. Run the prefix, check its reports, then run its tail:

```powershell
.\vf.ps1 csv-scope $Day -Scope UptoBPR
.\vf.ps1 csv-scope $Day -Scope PostBPR
```

or:

```powershell
.\vf.ps1 csv-scope $Day -Scope UptoDBM
.\vf.ps1 csv-scope $Day -Scope PostDBM
```

Do not mix Full and split producers on one initialized date.

On failure, stop and retain the operation records. Never repeat initialization, reset volumes or replay an accepted day. A committed preparation/serving failure may use the same command with `-Resume` after diagnosis; interrupted/uncertain calculation needs reconciliation first.

MTA stops during processing, so login can return **503** until publication finishes. Small data is useful for fixed-overhead checks but does not prove large-data performance; the current performance issues remain unresolved. Keep this guide outside the tagged clone so the build source remains clean.
