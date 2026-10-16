# VectorFLOW operator runbook

This describes the exported Linux/amd64 Docker assembly. Installation and UI evidence are recorded in the development tracker; commands documented here are not claims that a recovery rehearsal has passed. Do not execute these instructions against a sealed development database or another application's resources. Installation creates empty databases; it imports no demonstration inputs, calculated state, accounts or passwords.

## Release and host preparation

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
```

Before MTA registration, obtain the approved initialization artifact's SHA256. Registration binds that identity and the exact current implementation/catalogue; it imports no facts. Never substitute a test artifact merely to obtain readiness.

```sh
vf --profile install run --rm provision -m release.register_mta --input-sha256 INITIALIZATION_SHA256
```

Only the installation profile receives the provisioning credential. Runtime roles have no database/schema ownership or migration authority. Auth/MTO runtime grants are confined to their respective schemas; MTA uses its stricter immutable capability catalogue. A normal serving restart checks migrations without applying them.

Identity catalogue installation creates retained application/permission/feature metadata and empty/default client configuration only. Create an operator-approved account with the existing interactive command if required, then assign actual approved application permissions/scopes through existing administration procedures. No fixture account is installed:

```sh
vf --profile install run --rm auth-install manage.py createsuperuser
```

Do not place account passwords on the command line. An account does not by itself grant product/location/application scope. Keep CAPTCHA and authentication enabled.

## Input ownership, initialization, day and span

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

`/healthz` is process/gateway liveness. `/readyz` verifies identity database and selected MTA dependencies; it normally returns 503 before legitimate publication. Container health alone is not whole-application readiness and the gateway readiness response does not certify MTO scheduler output. Verify MTO routing/WebSocket integration separately without inventing scheduler runs. No scheduler execution or MTO output validation is introduced by installation.

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
