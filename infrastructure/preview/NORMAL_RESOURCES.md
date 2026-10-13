# Normal serving resources

These settings size the existing local 3005 installation independently of
comparison harnesses. They do not select data, change images, or migrate storage.
Matched benchmark limits belong in a separately invoked comparison harness.

## Apply limits to the existing running installation

Execute steps 1–3 in PowerShell from `F:/freshvcf`. Do not copy Markdown fences.

1. Copy `infrastructure/preview/normal-resources.env.example` to
   `D:/freshvcf-build/preview/normal-resources.env` and set the intended limits.
   This file contains resource values only, never credentials. The supplied
   values are the normal settings applied on 13 October 2026.
2. Run the following commands. Each record path must be new; retain old receipts.

```powershell
$stamp = Get-Date -Format yyyyMMdd-HHmmss
$python = 'D:/freshvcf-build/venv/Scripts/python.exe'
$settings = 'D:/freshvcf-build/preview/normal-resources.env'
& $python tools/normal_serving_resources.py --container freshvcf-preview-mta-1 --service mta --settings $settings --record "D:/freshvcf-build/evidence/normal-resources-$stamp-mta.json" --apply
if ($LASTEXITCODE -ne 0) { throw 'MTA resource update failed' }
& $python tools/normal_serving_resources.py --container freshvcf-test-postgres-1 --service pg --settings $settings --record "D:/freshvcf-build/evidence/normal-resources-$stamp-pg.json" --apply
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL resource update failed' }
```

3. Confirm the login page returns HTTP 200 and MTA readiness is true:

```powershell
curl.exe -f -s -o NUL -w '%{http_code}' http://localhost:3005/login
docker exec freshvcf-preview-user-service-1 python -c "import urllib.request; print(urllib.request.urlopen('http://mta:8000/readyz',timeout=20).read().decode())"
```

The helper updates CPU/RAM/combined RAM-plus-swap only and checks all captured
non-resource configuration remains unchanged. Its receipt includes rollback
arguments. Equal RAM and combined-swap limits disable swap. It does not change
worker counts or restart containers. Ordinary container restarts retain limits.

## Required configuration for subsequent container recreation

Keep the installation's complete existing Compose file list, image overrides,
selection, mounts and private environment file. Add the resource environment file
as a second `--env-file`, and append `normal-resources.compose.yaml` **last** for
the preview project. For its PostgreSQL project, append
`normal-postgres-resources.compose.yaml` last instead. Paths are relative to
`F:/freshvcf/infrastructure/preview`. Do not launch the base Compose file alone:
it does not represent the currently selected installation. Existing historical
overrides may override base resource settings, which is why the last overlay is
required. Render with `docker compose ... config --quiet` before deployment;
do not print resolved configuration containing credentials.

Worker/timeout values are used when the affected application is next recreated:
MTA defaults to two Gunicorn workers, 180-second timeout; auth defaults to one
Uvicorn worker. MTO retains its single Daphne process. Auth/MTO defaults are
1 CPU/1 GiB RAM/2 GiB combined RAM+swap; frontend and Redis each default to
0.5 CPU/128 MiB RAM/256 MiB combined. MTA is 3 CPU/4 GiB with no swap;
PostgreSQL is 2 CPU/2 GiB with no swap. Environment overrides are independently
configurable. No concurrency change or recreation was needed for this delivery.

## Preserved storage and qualifications

Modern PostgreSQL data and WAL remain on the disk-backed
`D:/freshvcf-build/postgres` bind mount. Legacy 3002 uses native processes with
all 16 logical CPUs available, without observed benchmark caps. Legacy SQL
database data/log files remain on D: NTFS; its local PostgreSQL data/WAL remain
on F: ReFS. No database relocation or shared SQL Server setting changed.
The shared SQL instance has effectively unbounded maximum server memory; this
delivery does not establish exclusive legacy memory allocation or capacity parity.

The existing preview images and selected fixture still include validation assets.
These resource-only files do not remove those assets or establish clean production
packaging. Health and configuration proof is not workload capacity, authenticated
workflow, or matched performance acceptance.
