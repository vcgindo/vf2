# Deployment and operations reference

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

Use [RUNBOOK.md](RUNBOOK.md) for the Windows 8080 checklist. This file holds Linux deployment commands, operating limits and recovery details. Shell blocks below use a POSIX shell, not PowerShell.

- [Ubuntu / public VPS checklist](#ubuntu--public-vps-checklist)
- [Linux assembly and roles](#release-and-host-preparation)
- [Step Five execution](#stage-five-reference-input-ownership-initialization-day-and-span)
- [Backup and restore](#durable-storage-backup-and-restore)
- [Upgrade and rollback](#upgrade-and-rollback)
- [Network and failure diagnostics](#network-and-failure-diagnostics)
- [Optional input procedure](#separate-optional-initialization-only-procedure--packaged-not-executed-in-stage-four)

Step Five commands are references only. The Windows reinstall does not authorize sample loading, initialization, daily execution, publication or recovery testing. Historical development compatibility settings are not fresh-install defaults.

## Cleanup Step6 MTA artifact — build/inspect only

- **Verify the immutable receipt** — Match source ZIP/image archive SHA256 and actual imageID. The complete operator-source descriptor and finite MTA-native descriptor each require an independently supplied pin. The image includes root manage.py/requirements.txt, all native migrations,24commands and required native SQL/schema/resources; build/inspection/operator helpers and optional dated data stay outside it.
- **Build from an admitted export** — Use a new owned context and the exact eight LinuxCPython3.11amd64 wheels. The builder uses the pinned official Python base, networknone during build,4GiB/2CPU per build step, no old application-image base. Its final stage receives only verified native files and hash-pinned installed dependencies. Preserve build/inspection receipts and failed attempts; do not prune shared Docker state.
- **Preserve existing services** — No frontend/MTO/auth rebuild or existing-instance upgrade is authorized. Compose no longer builds MTA from a raw context. Use a separately approved MTA image override/new-install assembly only after checking its target and all other retained imageIDs. Current old sealed installations require their original source/images/registrations.
- **Retain public-origin limits** — Ubuntu packaging proof does not qualify the existing browser bundle for a public HTTPS/WSS origin. The compiled-origin stop condition below remains binding; no frontend rebuild or VPS deployment certification follows.

```sh
python3 -B -m release.build_mta --source-root /srv/vectorflow/approved-export \
  --context /srv/vectorflow/owned/new-mta-context --wheelhouse /srv/vectorflow/approved-wheels \
  --commit APPROVED_FULL_COMMIT --source-sha256 APPROVED_SOURCE_MANIFEST_SHA256 \
  --native-sha256 APPROVED_NATIVE_MANIFEST_SHA256 --image vectorflow/mta:APPROVED_TAG
```

Set VF_NATIVE_RELEASE_COMMIT/VF_NATIVE_RELEASE_SHA256/VF_SOURCE_MANIFEST_SHA256 from the independent reviewed receipt. Do not copy a replacement manifest's own hash as authority. Step7/initialization/business execution and live deployment remain separately released.

## Ubuntu / public VPS checklist

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

**Status: TLS wiring checked locally; public deployment not yet qualified.** The delivered `bd309169` frontend is built for localhost8080. Its scheduling chunk `2.95dd74e4.chunk.js` opens `ws://127.0.0.1:8080/ws/scheduler/{runId}/`. Setting `VF_PUBLIC_WS_URL` at runtime does not change that JavaScript. Most HTTP calls are relative and can use the public host; the confirmed blocker is the compiled scheduling WebSocket origin.

**Stop before public installation until an approved frontend artifact matches the intended HTTPS/WSS domain.** A configuration-only frontend rebuild still needs an explicit exception to the freeze. This guide does not authorize or perform it. Do not patch assets, disable browser checks, expose localhost8080 publicly or claim the current bundle supports public WSS.

- **1. Prepare the VPS** — Use Ubuntu on x86_64/amd64, Docker Engine and Compose v2, Python3, Git if cloning, and OpenSSL. Follow [Docker's Ubuntu installation instructions](https://docs.docker.com/engine/install/ubuntu/). Point the domain's A/AAAA records to this VPS. Keep SSH access; allow only the intended HTTPS listener through the provider firewall. Docker-published ports can bypass UFW rules: see [Docker firewall guidance](https://docs.docker.com/engine/network/packet-filtering-firewalls/). Do not publish PostgreSQL, Redis, auth, MTA or MTO ports.
- **2. Transfer the approved release** — Verify its source/runtime SHA256 values against the approved release manifest. Extract into a new `/srv/vectorflow/releases/...` folder. Include `release-source.json`, `runtime-images.json`, `loaded-images.yaml` and `public-build.json`. A Git export needs these companions too; the current localhost archive is not a public-origin release.
- **3. Configure the domain and certificates** — Create a private `/srv/vectorflow/operator.env` from `release/.env.example`. Set the values below for the actual domain, not the example. Keep MTA/MTO database names separate. Supply a trusted certificate full chain and matching private key through the existing TLS secrets; certificate issuance/renewal is an operator task.

<details>
<summary>Show public configuration</summary>

```dotenv
VF_PROJECT=vectorflow-production
VF_RELEASE=REPLACE_WITH_APPROVED_FULL_SOURCE_COMMIT
VF_BIND_ADDRESS=0.0.0.0
VF_HTTP_PORT=443
VF_PUBLIC_URL=https://vectorflow.example.com
VF_PUBLIC_WS_URL=wss://vectorflow.example.com
VF_ALLOWED_HOSTS=vectorflow.example.com,localhost,127.0.0.1,mta,mto,auth
VF_TLS_MODE=https
VF_TLS_CERTIFICATE_FILE=/srv/vectorflow/private/tls/fullchain.pem
VF_TLS_PRIVATE_KEY_FILE=/srv/vectorflow/private/tls/privkey.pem
VF_SECRETS_DIR=/srv/vectorflow/private/secrets
VF_CLIENT_CIPHER_KEY=REPLACE_WITH_PUBLIC_BUILD_CLIENT_CIPHER
MTA_DB_NAME=vectorflow_mta
MTO_DB_NAME=vectorflow_mto
DB_HOST=postgres
DB_SSLMODE=disable
```

Keep `DB_SSLMODE=disable` only for the bundled private PostgreSQL network. An external PostgreSQL server requires its separate verify-full/CA configuration. The TLS override makes NGINX listen with TLS on **container80**, mapped to **host443**. No host HTTP80 listener or automatic HTTP redirect is configured; use HTTPS directly. Certificate-renewal ports depend on the operator's chosen issuance method.

</details>

- **4. Check frontend compatibility** — Run this non-mutating gate before creating resources. It must reject the currently delivered localhost package for a public domain.

<details>
<summary>Show origin gate and image loading</summary>

```sh
set -eu
ReleaseRoot=/srv/vectorflow/releases/APPROVED_RELEASE
OperatorFile=/srv/vectorflow/operator.env
cd "$ReleaseRoot"
python3 - "$OperatorFile" <<'PY'
import json, sys
from pathlib import Path
from urllib.parse import urlsplit
from release.preflight import environment, configuration
v = environment(sys.argv[1])
configuration(v)
source = json.loads(Path("release-source.json").read_text())
build = json.loads(Path("public-build.json").read_text())
images = json.loads(Path("runtime-images.json").read_text())
host = urlsplit(v["VF_PUBLIC_URL"]).hostname
if v["VF_PUBLIC_URL"].startswith("http:") or host in ("localhost", "127.0.0.1", "::1") or host.endswith(".example.com"):
    raise SystemExit("STOP: configure the actual public HTTPS domain")
if v["VF_RELEASE"] != source["source_commit"]:
    raise SystemExit("STOP: VF_RELEASE differs from the approved source manifest")
if build.get("public_origin") != v["VF_PUBLIC_URL"] or build.get("websocket_origin") != v["VF_PUBLIC_WS_URL"]:
    raise SystemExit("STOP: frontend was not built for this public HTTPS/WSS origin; explicit build approval required")
if build.get("frontend_image") != images["services"]["frontend"]["image_id"] or build.get("client_cipher_key") != v["VF_CLIENT_CIPHER_KEY"]:
    raise SystemExit("STOP: frontend identity/public cipher mismatch")
print("Public build metadata matches; actual VPS/browser tests are still required")
PY
# Only after verifying the archive hash against the approved manifest:
docker load --input "$ReleaseRoot/vectorflow-stage4-runtime.tar.gz"
```

</details>

- **5. Create secrets and install the empty application** — Use a NEW owned cluster/volume set. Never provision into the existing trial or a sealed database. Keep the public cipher from the approved frontend build; generate new private database/signing/RSA secrets. Stop on any failure.

<details>
<summary>Show HTTPS install commands — only after the origin gate passes</summary>

```sh
set -eu
umask 077
install -d -m 700 /srv/vectorflow/private
AuthImage=$(python3 -c 'import json; print(json.load(open("runtime-images.json"))["services"]["auth"]["image_id"])')
PublicCipher=$(python3 -c 'import json; print(json.load(open("public-build.json"))["client_cipher_key"])')
docker run --rm --network none --user 0:0 --entrypoint python \
  --mount type=bind,src=/srv/vectorflow/private,dst=/private "$AuthImage" \
  -m release.prepare_secrets --directory /private/secrets --public-client-cipher-key "$PublicCipher"
chmod 600 "$OperatorFile"
# TLS files must already exist and be readable by the frontend through their secret mounts.
test -s /srv/vectorflow/private/tls/fullchain.pem
test -s /srv/vectorflow/private/tls/privkey.pem
VpsDomain=$(python3 -c 'from release.preflight import environment; from urllib.parse import urlsplit; import sys; print(urlsplit(environment(sys.argv[1])["VF_PUBLIC_URL"]).hostname)' "$OperatorFile")
openssl x509 -in /srv/vectorflow/private/tls/fullchain.pem -noout -checkhost "$VpsDomain"
openssl x509 -in /srv/vectorflow/private/tls/fullchain.pem -noout -checkend 86400
openssl pkey -in /srv/vectorflow/private/tls/privkey.pem -noout -check
DeploymentProject=$(python3 -c 'from release.preflight import environment; import sys; print(environment(sys.argv[1])["VF_PROJECT"])' "$OperatorFile")
vf() {
  docker compose --project-name "$DeploymentProject" --env-file "$OperatorFile" \
    -f "$ReleaseRoot/release/compose.yaml" -f "$ReleaseRoot/loaded-images.yaml" \
    -f "$ReleaseRoot/release/compose.tls.yaml" "$@"
}
python3 release/preflight.py --source-root "$ReleaseRoot" --env-file "$OperatorFile" \
  --compose-file "$ReleaseRoot/release/compose.yaml" --compose-file "$ReleaseRoot/loaded-images.yaml" \
  --compose-file "$ReleaseRoot/release/compose.tls.yaml"
vf config --quiet
vf up -d --wait postgres redis
vf --profile install run --rm --no-deps provision -m release.provision
vf --profile install run --rm --no-deps provision -m release.provision --apply
vf --profile install run --rm --no-deps mta-install manage.py migrate --plan
vf --profile install run --rm --no-deps mta-install manage.py migrate --noinput
vf --profile install run --rm --no-deps auth-install manage.py migrate --noinput
vf --profile install run --rm --no-deps mto-install manage.py migrate --noinput
vf --profile install run --rm --no-deps auth-install -m release.install_identity
vf --profile install run --rm --no-deps provision -m release.grant_service AUTH
vf --profile install run --rm --no-deps provision -m release.grant_service MTO
vf --profile install run --rm --no-deps provision -m release.metadata_access --apply
vf --profile install run --rm --no-deps auth-install manage.py createsuperuser
vf up -d --wait mta auth mto frontend
```

Use the same Compose file order for every command, including renewal/restart. No frontend or MTO build command is part of this procedure. Clear conflicting shell configuration values before preflight; shell variables override the env file. Host secret directories must remain private; Compose file secrets are mounts, not a substitute for host access controls. See [Docker's secrets documentation](https://docs.docker.com/compose/how-tos/use-secrets/).

</details>

- **6. Verify from outside the VPS** — Check trusted TLS, normal login/CAPTCHA, original MDM families and reload. Check the browser Network panel: API calls use the public host, no mixed-content errors, and scheduling uses `wss://YOUR_DOMAIN/ws/scheduler/...`, never the visitor's localhost. Do not disable CAPTCHA, use `curl -k` or invent a scheduling run. A successful scheduling session needs its legitimate run/data; that operational proof belongs to Step Five.

<details>
<summary>Show TLS and service checks</summary>

```sh
# Run these on the approved VPS after startup:
vf exec -T frontend nginx -t -c /tmp/vectorflow.conf
vf ps
vf logs --tail 50 frontend auth mta
# Run these from an external machine with the real domain:
curl --fail --show-error https://YOUR_DOMAIN/healthz
curl --show-error --output /dev/null --write-out '%{http_code}\n' https://YOUR_DOMAIN/readyz
# Expected before publication: health200, readiness503.
```

</details>

- **7. Record the release and stop** — Record source/image IDs, domain, certificate expiry/renewal ownership and test results. Keep backups/rollback available. Sample loading, daily execution, publication and recovery rehearsal remain Step Five. Renew certificates before expiry and recreate/reload only the approved gateway after checking the certificate; no automatic renewal job is shipped here.

**Verification on 17 October 2026:** local Compose rendering confirmed only frontend host443→container80, TLS secret names and HTTPS auth origin. The shipped scheduling chunk independently confirms the localhost WebSocket constant. No VPS hostname, DNS access, SSH credentials or real certificate was supplied; public reachability, live certificate trust and public-origin login/WSS have **not** been tested. Do not label this a verified public production deployment.

## Release and host preparation

Obtain the source ZIP and its SHA256 from the approved release manifest, verify the digest, and extract into a new release directory. Alternatively, on a clean machine with Git and Python 3, clone the approved repository and export the exact reviewed commit with the existing standard-library exporter:

```sh
git clone https://github.com/yurtse/freshvcf.git /srv/vectorflow/source
cd /srv/vectorflow/source
git fetch origin
RELEASE_COMMIT=REPLACE_WITH_APPROVED_FULL_40_CHARACTER_COMMIT
git checkout --detach "$RELEASE_COMMIT"
test "$(git rev-parse HEAD)" = "$RELEASE_COMMIT"
python3 -m release.export --repository /srv/vectorflow/source \
  --revision "$RELEASE_COMMIT" --output "/srv/vectorflow/releases/$RELEASE_COMMIT"
cd "/srv/vectorflow/releases/$RELEASE_COMMIT"
```

Replace the commit placeholder before running; the destination must not already exist. Repository access must use the operator's normal Git credentials, never credentials embedded in these commands. The exporter reads committed files and excludes validation populations/runners and secrets; copying the whole checkout is not a production export. Verify `release-source.json` names the approved full commit, then follow the external configuration, image build/load and installation steps below. No application Python dependencies are required merely to run this exporter.

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

For a separately authorized new installation, use the retained exact auth image's `release.prepare_secrets` command to generate a **new** secret directory under a private host parent, mounted only for that command. It refuses an existing destination. Cleanup Step6 reuses the already approved auth image and does not build auth or generate/rotate existing secrets. The following is an installation reference, not Step6 execution:

```sh
# Reuse the separately approved exact auth image. No auth build in cleanup Step6.
docker run --rm --network none --user 0:0 --entrypoint python \
  --mount type=bind,src=/srv/vectorflow/private,dst=/private \
  vectorflow/auth:RELEASE -m release.prepare_secrets --directory /private/secrets \
  --public-client-cipher-key PUBLIC_CIPHER_FROM_DELIVERED_PUBLIC_BUILD_JSON
```

The host parent must exist with access restricted to the deployment operator. The generated directory is mode 0700; files are read-only and separately mounted only into the services that need them. Enforce equivalent host ACLs on Windows; Linux mode bits do not establish Windows ACL protection. For the frozen-frontend package pass the exact public cipher from delivered public-build.json through the existing --public-client-cipher-key option; do not choose a new browser cipher. Save that same **public** client cipher key as `VF_CLIENT_CIPHER_KEY`. It must match the frontend build and auth service. Database passwords, signing secrets and RSA private keys must never appear in frontend build arguments or images. Back up the private files separately; regeneration is credential/key rotation, not restart.

`REACT_APP_AG_GRID_LICENSE_KEY` is an optional public build override; blank retains the exact original corporate key. Confirm deployment entitlement with the corporate license owner. The embedded key text does not establish the current contract. Build the remaining images and inspect the complete rendered assembly before installing:

```sh
vf config --quiet
# Build MTA only through the authenticated cleanup Step6 builder above.
# Reuse the separately approved exact auth image; no auth build in Step6.
# Load the exact retained frontend/MTO images from the approved runtime archive.
# No frontend rebuild or MTO change is part of this release.
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

Install finite read-only MTA metadata access without choosing a business artifact:

```sh
vf --profile install run --rm provision -m release.metadata_access
vf --profile install run --rm provision -m release.metadata_access --apply
```

This grants SELECT on exactly django_migrations, ProductionInitialization, MdmSource, CalculationRun and UserReportLayout in the mta schema, plus schema USAGE. It creates no input/source/run, account, permission population or registry. Runtime validation rejects additional business-table privileges, role inheritance, schema creation and temporary-object privileges. The command refuses an existing registered target rather than changing its immutable catalogue. The existing registered runtime instead validates its original namespace/capability read-only; no new grant or registration is needed for that path.

Input-bound MTA registration is **not an empty-install step**. Obtain the exact approved input SHA only if separately selecting the optional initialization procedure. It remains a one-time operation on an untouched target with exclusive cluster authority; no dummy SHA or re-registration.

Only the installation profile receives the provisioning credential. Runtime roles have no database/schema ownership or migration authority. Auth/MTO runtime grants are confined to their respective schemas; MTA uses its stricter immutable capability catalogue. A normal serving restart checks migrations without applying them.

Identity catalogue installation creates retained application/permission/feature metadata and empty/default client configuration only. Create an operator-approved account with the existing interactive command if required, then assign actual approved application permissions/scopes through existing administration procedures. No fixture account is installed:

```sh
vf --profile install run --rm auth-install manage.py createsuperuser
```

Do not place account passwords on the command line. An account does not by itself grant product/location/application scope. Keep CAPTCHA and authentication enabled.

After the approved population/catalogue is available and the application is serving, sign in normally as that bootstrap administrator. Use **Vector Admin → Manage Roles** (`/vector-admin/manage-roles`) to create the operator-approved MTA roles from the installed permission catalogue. Select the actual application and existing URL/function entries; use the approved role codes and names, not the development fixture's numeric IDs. The installer deliberately creates no requester/reviewer roles or assignments. A reviewer is an ordinary user with the specifically approved review permissions, not a second superuser.

Open **Profile → Manage Users → Add User** to create each approved requester/reviewer through the existing registration form. Select the relevant application role, then its Product and Location permissions (including the required hierarchy levels) and any specifically approved data permissions. Use the form's existing password/notification process and configured mail service; do not seed fixture credentials or mark every account as admin. For an existing account, use the same Manage Users edit workflow. These screens call the retained `/api/user/add-role/`, `/api/user/register/` and `/api/user/edit-user` contracts; role definitions and user scope assignments are separate operations. Empty/unavailable product or location catalogues must be resolved through the approved population/configuration path before assigning scope; they are not permission to select a different run or bypass a denial.

Sign in as each ordinary account and check **Profile → Permissions**, its intended report/MDM menu, and the allowed product/location subset. Confirm the requester lacks reviewer actions and an out-of-scope read/action is denied. Reauthenticate after changing assignments so the issued session reflects them. Keep the native MTA permission/hierarchy files and their configured SHA256 values consistent with that approved deployment; creating an auth account does not generate or replace those files. These are operator setup instructions derived from the existing forms/models, not a completed fresh-account onboarding or business-workflow rehearsal. No users, passwords, roles or scope assignments are automatically imported by this package.

## Stage Five reference: input ownership, initialization, day and span

Stage Four packages these procedures only. Sample loading, initialization execution, day/span/calculation/action/publication and recovery execution require Stage Five release and an exact target/input decision. They are not Stage Four closure tests.

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

## Retained sealed development publication qualification

Fresh installations do not use historical compatibility declarations. The optional `VF_MDM_SEALED_EXPORT_SHA256` entry is restricted to the reviewed `9e353ff8` export lineage and the original development database/OID, source, initialization and seal already enforced by the retained ancestry validators. It requires the exact pinned declaration at `/proof/s4-20261016/sealed-export-compatibility.json` on a read-only mount, the unchanged older declarations and their pins. It authenticates all 721 actual native production files, exactly 187 fixed validation omissions, the two reviewed installation deltas and only the explicitly reviewed verifier descendants. Unexpected files, omissions, bytes, metadata or bindings fail admission. Reconstructed historical bytes are validation data only. No installation, registration replacement, reseal, publication or calculation is performed.

For the separately approved retained-development layout check only, `VF_MDM_SEALED_EXPORT_LAYOUTS=1` additionally admits exactly owner-issued INSERT/DELETE on `mta.fresh_mta_userreportlayout` and USAGE on its ID sequence for the existing consumer. It requires the exact original database and export opt-in. The complete current privilege catalogue and all original capability identities, guards and catalogue rows remain checked; only those three authenticated ACL rows are removed for the unchanged historical comparison. UPDATE, TRUNCATE, grant option, PUBLIC access and other objects are not admitted. Disable this option for fresh installations: their existing production profile already specifies this finite preference access. This qualification is not a general database-copy, source-override or upgrade mechanism; the immutable development declaration and development proof resources are not shipped as production inputs.

The optional initialization input pack is not a complete execution trial. Step Five must define and freeze a coherent daily input sequence before any complete input-to-successor execution claim. No daily sequence or accepted output has been fabricated or replayed during packaging.



## Network and failure diagnostics

An occupied gateway port is a listener/ownership problem. “All predefined address pools” is Docker bridge allocation exhaustion, not a port conflict or a reason to change application algorithms. Inspect docker network ls/inspect and Windows Get-NetRoute before choosing an explicitly approved private subnet. The preflight optional --network-subnet checks Docker overlap, but host routes must also be reviewed. Use a small operator override declaring that checked subnet on the existing application network for a NEW install only; include it consistently after the base file. No global prune, shared engine/WSL restart, automatic new port or network replacement. Preserve existing project subnet/network/volumes.

Health200 means liveness. Ready503 with no publication is expected; it must not be relabelled ready to clear a screen. Metadata now requires installed schema/role/config authority but no business day. Real original MDM family options/environment/report definitions can load while data views stay unavailable. Planning requires an actual businessDate; its initialization opening date is not a report date. BPR's columns/layout/date/data calls have different prerequisites. Preserve original blank/unavailable behavior rather than add new UI, fake dates/metrics or blanket empty200.

For a reported500 record the exact method/path, HTTP status, envelope status/body, corresponding backend stack/prerequisite and actual role/scope. The initial BPR500 report lacked an attributable retained stack; inspected metadata failures were503 publication_not_admitted before BPR handler execution. That is an expected unavailable disposition, not a claim that an arbitrary500 was fixed. Retained legacy description/filter500 paths are separate limitations. Anonymous401, URL/function403, failed upstream permission503 and valid empty population catalogues remain distinct. No hidden catalogue omission, blanket grant or scope widening.

Roles/URL entries are installed metadata; product/location definitions and assignments are separately approved real configuration. The unchanged ordinary-user form requires legitimate MTA scope selections; role-only empty-population onboarding is not introduced. SMTP and existing password/notification behavior remain external dependencies. No account/scope generation is part of package installation.

## Separate optional initialization-only procedure — packaged, not executed in Stage Four

The optional pack is separate from the production source ZIP/image/default install. Its original optional-initialization.json pins ZIP/input/configuration/recipe identities and provenance; optional_initialize.py is retained byte-exact beside it. The operator pack can be assembled by release.optional_package from the exact approved commit and retained input ZIP, without loading data. It contains supplied initial facts/history/opening, never a later calculated closing, day outputs, accounts or credentials. Execution needs separate target/input authority; Step6 does not grant it.

Under a separately released target/input decision, verify the pack ZIP and input SHA from the manifest. Transfer inputs/initialization.json to a chosen /var/lib/vectorflow/inputs path in the owned writable mta_data volume; a staging container or other transfer mechanism needs explicit resource authority. For an existing approved mta-install transfer process, copy with docker cp to that exact process/volume and verify SHA inside it. Do not start a helper/container merely because this paragraph describes transfer. Never mount the development checkout or a DB dump. Keep raw artifact bytes/provenance unchanged.

Before registration inspect the actual cluster-wide fresh_operational_acceptor membership: exactly the one intended installer may be its member, as enforced by the unchanged validator. A second database in the same cluster does not isolate roles. Do not amend another registration, add another acceptor member, use a dummy SHA, or change a guard. The empty metadata install has no input-bound registration; this explicit OPTIONAL stage registers once after actual input selection and exclusive authority are established. If that authority is absent, stop and obtain an exact target decision.

```sh
# Stage Five / separate target-and-input release required; NOT Stage Four execution.
vf --profile install run --rm provision -m release.register_mta --input-sha256 3a4bf3a699c57fab7f00e6820f43c0e1b661386c9cf3aa4f21fd4081e110bdbe
# Mount the separate exact operator package read-only at /operator only after
# explicit target/input/container authority. This code is not in the image.
vf --profile install run --rm mta-install /operator/optional_initialize.py /var/lib/vectorflow/inputs/initialization.json
vf --profile install run --rm mta-install /operator/optional_initialize.py /var/lib/vectorflow/inputs/initialization.json --apply
```

The first optional_initialize invocation only inspects the existing native contract using exact input/configuration/recipe digests. The second explicitly applies once, validates existing native ownership, initializes only supplied masters/opening and binds the complete optional family owners in one transaction. Save its source/opening/content/implementation/receipt identities and independently read back exact typed input/master state. Verify zero calculation/capture/task and no publication. A second apply is refused before mutation; native initialization's underlying identical REVERIFIED policy remains unchanged. Preserve any failed target/receipt; no reset/reseed/registration replacement or automatic retry. Selecting a source for initialized master reads does not create a report publication or permissions.


## MTA/auth-only correction of an existing registered empty trial

Preserve source/images/config/secrets/account/scope/registration/database identities first. Verify new code against the existing immutable namespace/capability using read-only runtime connections. Do not rerun provision, migrations, grants or registration against that sealed target. Keep its original frontend/MTO/PG/Redis/container network/port/volumes/start states. Select only reviewed MTA/auth image IDs in a final operator override and replace only those two services with --no-deps --no-build --pull never; one necessary MTA/auth restart/reload is the persistence proof. Preserve old images/export/override and compatible rollback; do not select an old image over changed schema or silently re-enable the withdrawn setup release. Current approved correction does not change schema or the original registration.
