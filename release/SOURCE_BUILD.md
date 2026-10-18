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

This explicitly generates private per-service secrets, creates new databases/least-privilege roles, applies real migrations, installs system/permission metadata and creates your new administrator. Enter any administrator fields not supplied in `.env` when prompted. It does NOT register an opening, load masters/facts, calculate a day or prepare/publish reports. Existing databases/roles/users are not reset or overwritten; an already-installed target is refused.

## 4. Start and verify

```powershell
docker compose up -d --no-build --wait
docker compose ps
```

Open `http://127.0.0.1:<VF_HTTP_PORT>` and sign in normally with your new administrator, including CAPTCHA. Expect six healthy services and original navigation/installation metadata. A blank MTA has `/healthz`200; `/readyz`503 and unavailable data reports are expected until real onboarding/publication. Crashes,500s or a failed normal login are installation failures.

For a restart use `docker compose stop`, followed by the SAME `docker compose up -d --no-build --wait`. Restart never provisions, migrates, loads data or rotates secrets. Never use `down -v` to fix an error. Volumes contain the installation database, private keys, files and receipts; retain them together for recovery.

## Separate operation: master/opening loading and daily execution

These are supported explicit native commands, not installation/startup effects:

```powershell
docker compose run --rm --no-deps mta-install manage.py initialize_production --help
docker compose run --rm --no-deps mta-install manage.py run_production_day --help
```

Use a separately reviewed input/access packet, register its actual opening hash once, initialize masters/opening, then run an actual supplied day through its own persisted predecessor. `--help` above loads no data. [RUNBOOK.md Part B](RUNBOOK.md#b-optional-load-mastersopening-then-execute-a-supplied-day) describes the native operation parameters, preparation and selection contracts for the retained package; its prebuilt-file/env setup is NOT needed by this root Compose installation. Root `provision` and `mta-install` supply their own baked image identity automatically. Keep real inputs outside Git and mount them read-only only for the explicit operation. Do not copy calculated outputs, old database seals or demo accounts into a blank installation.

## Release boundary

Root `compose.yaml` is this source-build route. `release/compose.yaml` remains the retained prebuilt/advanced assembly; its immutable package is unchanged. Frontend/MTO application source and behavior are unchanged. Build/blank-install verification evidence belongs in the existing handoff tracker; public HTTPS/WSS, production data, capacity and cutover are separate decisions. This guide does not itself claim those have passed.
