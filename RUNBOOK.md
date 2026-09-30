# Fresh build runbook

This build is not yet the application served on3004. Do not run copied historical
startup scripts; deployment wiring is pending in F3.

Source: F:/freshvcf. Remote: git@github.com:yurtse/freshvcf.git, branch main.
User-authorized storage: D:/freshvcf-build. Git's objects directory is a junction
to D:/freshvcf-build/git-objects because F: filled during initialization. Back up
both locations or clone the pushed remote to obtain a self-contained checkout.
Dependencies: D:/freshvcf-build/venv. Generated evidence/artifacts belong on D:,
not in the source repo or another task's output folders.

```powershell
Set-Location F:\freshvcf
$env:VF_SECRET_KEY = '<supply a local secret; never commit it>'
& D:\freshvcf-build\venv\Scripts\python.exe manage.py check
& D:\freshvcf-build\venv\Scripts\python.exe -m unittest discover -s tests -v
python tools/baseline.py verify
```

The health route deliberately reports NOT_CERTIFIED for the whole migration.
A successful framework check is not migration parity.

## Isolated calculation/persistence verification

```powershell
docker compose -f compose.test.yaml up -d postgres
docker compose -f compose.test.yaml build mta
docker compose -f compose.test.yaml run --rm --no-deps mta python manage.py migrate --noinput
docker compose -f compose.test.yaml run --rm --no-deps mta python manage.py test mta.runtime --noinput
```

The test Compose publishes NO host port. Credentials in that file are disposable
isolated-test credentials, not serving login credentials. It creates one new
PostgreSQL database with mta/mto/identity schemas and touches no existing service.
Do not add a serving port or point it at an accepted application's database.

Copy the registered retained artifact without alteration to
D:/freshvcf-build/inputs/retained-sizeable.json. Verify its byte SHA256 is
8ea842061fc03687eafb30b152e3228e91632fb00914e894c1957cf049f753ec.

```powershell
docker compose -f compose.test.yaml run --rm --no-deps mta python manage.py run_current_day /inputs/retained-sizeable.json --revision <explicit-revision> --evidence /evidence/<new-directory>
& D:\freshvcf-build\venv\Scripts\python.exe -m parity.verify_current_day D:\freshvcf-build\evidence\<new-comparison-directory> --persisted-output D:\freshvcf-build\evidence\<new-directory>\outputs.json
```

Use a new revision after a relevant code/input contract change. Retries of the
same revision verify stored input/output integrity; they are not fresh execution
of changed code. A failed/running attempt cannot be silently promoted by retry.

When idle: `docker compose -f compose.test.yaml stop postgres`.
Never use down -v, delete the data directory or stop another task's containers.
