# VectorFLOW operator runbook

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

This describes the exported Linux/amd64 Docker assembly. Installation and UI evidence are recorded in the development tracker; commands documented here are not claims that a recovery rehearsal has passed. Do not execute these instructions against a sealed development database or another application's resources. Installation creates empty databases; it imports no demonstration inputs, calculated state, accounts or passwords.

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

Build the auth image first, using its pinned Dockerfile. Use that image's `release.prepare_secrets` command to generate a **new** secret directory under a private host parent, mounted only for that command. It refuses an existing destination. For example, after choosing the actual image tag:

```sh
docker build --platform linux/amd64 -f release/auth.Dockerfile -t vectorflow/auth:RELEASE .
docker run --rm --network none --user 0:0 --entrypoint python \
  --mount type=bind,src=/srv/vectorflow/private,dst=/private \
  vectorflow/auth:RELEASE -m release.prepare_secrets --directory /private/secrets \
  --public-client-cipher-key PUBLIC_CIPHER_FROM_DELIVERED_PUBLIC_BUILD_JSON
```

The host parent must exist with access restricted to the deployment operator. The generated directory is mode 0700; files are read-only and separately mounted only into the services that need them. Enforce equivalent host ACLs on Windows; Linux mode bits do not establish Windows ACL protection. For the frozen-frontend package pass the exact public cipher from delivered public-build.json through the existing --public-client-cipher-key option; do not choose a new browser cipher. Save that same **public** client cipher key as `VF_CLIENT_CIPHER_KEY`. It must match the frontend build and auth service. Database passwords, signing secrets and RSA private keys must never appear in frontend build arguments or images. Back up the private files separately; regeneration is credential/key rotation, not restart.

`REACT_APP_AG_GRID_LICENSE_KEY` is an optional public build override; blank retains the exact original corporate key. Confirm deployment entitlement with the corporate license owner. The embedded key text does not establish the current contract. Build the remaining images and inspect the complete rendered assembly before installing:

```sh
vf config --quiet
vf build mta auth
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


## Clean Windows folder: pinned acquisition, external config and image selection

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

These are operator commands for an explicitly authorized NEW deployment, not instructions to reset or repurpose an existing trial. The supported process platform remains Linux/amd64 Docker Engine/Compose on Windows. Native Windows services and another CPU architecture are unproved. Do not use PowerShell variables named HOME/CODEX_HOME or import secrets into Git. Replace the commit/path placeholders with the delivered manifest/operator choices before running.

```powershell
$SourceRoot = 'C:/VectorFLOW/source'
$ExportRoot = 'C:/VectorFLOW/releases/approved'
$ApprovedCommit = 'REPLACE_WITH_APPROVED_FULL_40_CHARACTER_COMMIT'
if ($ApprovedCommit -notmatch '^[0-9a-f]{40}$') { throw 'Choose the delivered full source commit first' }
git clone https://github.com/yurtse/freshvcf.git $SourceRoot
if ($LASTEXITCODE) { throw 'Clone failed; use normal Git credentials' }
git -C $SourceRoot fetch origin
git -C $SourceRoot checkout --detach $ApprovedCommit
if ($LASTEXITCODE) { throw 'Pinned checkout failed' }
if ((git -C $SourceRoot rev-parse HEAD).Trim() -ne $ApprovedCommit) { throw 'Commit differs' }
Push-Location $SourceRoot
try {
  python -m release.export --repository $SourceRoot --revision $ApprovedCommit --output $ExportRoot
  if ($LASTEXITCODE) { throw 'Export failed; preserve it rather than overwrite' }
} finally { Pop-Location }
```

Alternatively verify the delivered source ZIP SHA256 with Get-FileHash and Expand-Archive into a new folder. Both paths must produce the matching release-source.json and unchanged managed files. The source exporter needs only Python standard library and Git. A complete checkout is not the production export.

Copy release/.env.example to a private operator.env outside Git. Set VF_RELEASE to the delivered source tag/commit, VF_PROJECT to the chosen project, absolute VF_SECRETS_DIR, separate database/role names and matching HTTP/WS origins/hosts. A blank VF_RELEASE intentionally causes Compose's “Set pinned release”; an override image file does not supply every missing interpolation variable. Avoid conflicting shell environment values: Compose shell variables take precedence over the env file. Record the effective project/env/override list without printing secrets.

For this corrected8080 release the original frontend image and assets are frozen, including its existing public cipher and ws://127.0.0.1:8080 build configuration. Preserve the matching private auth configuration. A different frontend origin/cipher requires a separately authorized frontend build exception; changing only runtime environment cannot rewrite compiled assets. No such rebuild is performed or implicitly authorized here. Existing corporate AG Grid wiring is unchanged; no entitlement claim follows from embedded key text.

Choose one image path: load the verified delivered archive and exact loaded-images override; or build only MTA/auth from the exact export using consistent VF_RELEASE tags while loading the frozen frontend/MTO/PG/Redis images from that archive. Use Docker image inspect IDs, not matching tag names, as proof. Base dependencies remain pinned. Do not run a whole-assembly rebuild, npm update or pip upgrade. Build auth first if a new installation needs its existing prepare_secrets command; existing keys/passwords must never be regenerated for restart/upgrade. The private host parent must already exist with operator-only Windows ACLs; verify the directory remains outside Git.

```powershell
$ReleaseRoot = 'C:/VectorFLOW/releases/approved'
$OperatorFile = 'C:/VectorFLOW/private/operator.env'
$ImageOverride = "$ReleaseRoot/loaded-images.yaml"
$ProjectLine = @(Get-Content -LiteralPath $OperatorFile | Where-Object { $_ -match '^\s*VF_PROJECT\s*=' })
if ($ProjectLine.Count -ne 1) { throw 'Configure exactly one VF_PROJECT in operator.env' }
$DeploymentProject = ($ProjectLine[0] -split '=', 2)[1].Trim().Trim('"').Trim("'")
function vf {
  & docker compose --project-name $DeploymentProject --env-file $OperatorFile `
    -f "$ReleaseRoot/release/compose.yaml" -f $ImageOverride @args
  if ($LASTEXITCODE) { throw 'Compose failed; preserve the failure and state' }
}
# Load the approved companion runtime archive before preflight; verify its SHA256 first.
docker load --input "$ReleaseRoot/vectorflow-stage4-runtime.tar.gz"
if ($LASTEXITCODE) { throw 'Image load failed' }
# On a NEW installation only, prepare NEW private files under an operator-only ACL parent.
# Preserve existing secrets; this helper refuses an existing destination.
$PublicBuild = Get-Content -Raw -LiteralPath "$ReleaseRoot/public-build.json" | ConvertFrom-Json
$RuntimeImages = Get-Content -Raw -LiteralPath "$ReleaseRoot/runtime-images.json" | ConvertFrom-Json
$PrivateParent = 'C:/VectorFLOW/private'
docker run --rm --network none --user 0:0 --entrypoint python `
  --mount "type=bind,src=$PrivateParent,dst=/private" $RuntimeImages.services.auth.image_id `
  -m release.prepare_secrets --directory /private/secrets `
  --public-client-cipher-key $PublicBuild.client_cipher_key
if ($LASTEXITCODE) { throw 'New-secret preparation failed; never overwrite existing keys' }
# Configure operator.env with this public cipher, absolute secret directory and delivered origins.
# The function uses the exact VF_PROJECT read from operator.env.
python "$ReleaseRoot/release/preflight.py" --source-root $ReleaseRoot --env-file $OperatorFile `
  --compose-file "$ReleaseRoot/release/compose.yaml" --compose-file $ImageOverride
if ($LASTEXITCODE) { throw 'Read-only preflight refused; do not start installation' }
vf config --quiet
# These steps are ONLY for the separately authorized new deployment:
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
vf --profile install run --rm provision -m release.metadata_access --apply
# Existing interactive administrator command; never put its password in this script.
vf --profile install run --rm auth-install manage.py createsuperuser
vf up -d mta auth mto frontend
vf ps
```

The function derives VF_PROJECT from the private operator file; it does not import or print secret values. For an existing owned deployment preflight can explicitly allow its occupied port with --allow-existing-project; it verifies ownership, not just that the port responds. This flag does not authorize an upgrade. Fresh install must never borrow/reset the8080 trial or sealed development databases.

Preflight checks source digests, Linux/amd64, Compose, image IDs, required secret files, distinct database names, explicit HTTP/WS origins and port ownership. It never starts resources, pulls, builds, initializes or cleans up. Windows file ACLs and corporate licence entitlement remain operator checks. An offline host needs the complete matching image archive and all build dependencies if choosing source build; a local smoke check does not certify offline installation.

## Network and failure diagnostics

An occupied gateway port is a listener/ownership problem. “All predefined address pools” is Docker bridge allocation exhaustion, not a port conflict or a reason to change application algorithms. Inspect docker network ls/inspect and Windows Get-NetRoute before choosing an explicitly approved private subnet. The preflight optional --network-subnet checks Docker overlap, but host routes must also be reviewed. Use a small operator override declaring that checked subnet on the existing application network for a NEW install only; include it consistently after the base file. No global prune, shared engine/WSL restart, automatic new port or network replacement. Preserve existing project subnet/network/volumes.

Health200 means liveness. Ready503 with no publication is expected; it must not be relabelled ready to clear a screen. Metadata now requires installed schema/role/config authority but no business day. Real original MDM family options/environment/report definitions can load while data views stay unavailable. Planning requires an actual businessDate; its initialization opening date is not a report date. BPR's columns/layout/date/data calls have different prerequisites. Preserve original blank/unavailable behavior rather than add new UI, fake dates/metrics or blanket empty200.

For a reported500 record the exact method/path, HTTP status, envelope status/body, corresponding backend stack/prerequisite and actual role/scope. The initial BPR500 report lacked an attributable retained stack; inspected metadata failures were503 publication_not_admitted before BPR handler execution. That is an expected unavailable disposition, not a claim that an arbitrary500 was fixed. Retained legacy description/filter500 paths are separate limitations. Anonymous401, URL/function403, failed upstream permission503 and valid empty population catalogues remain distinct. No hidden catalogue omission, blanket grant or scope widening.

Roles/URL entries are installed metadata; product/location definitions and assignments are separately approved real configuration. The unchanged ordinary-user form requires legitimate MTA scope selections; role-only empty-population onboarding is not introduced. SMTP and existing password/notification behavior remain external dependencies. No account/scope generation is part of package installation.

## Separate optional initialization-only procedure — packaged, not executed in Stage Four

The separate optional pack is not in the production export or default install. release/optional-initialization.json pins its ZIP/input/configuration/recipe identities and provenance. It contains declared supplied masters/configuration/initial history/opening, never a later calculated closing. It includes no daily sequence, outputs, accounts or credentials. Full daily execution, action/successor/publication/retry and recovery rehearsal remain Stage Five.

Under a separately released target/input decision, verify the pack ZIP and input SHA from the manifest. Transfer inputs/initialization.json to a chosen /var/lib/vectorflow/inputs path in the owned writable mta_data volume; a staging container or other transfer mechanism needs explicit resource authority. For an existing approved mta-install transfer process, copy with docker cp to that exact process/volume and verify SHA inside it. Do not start a helper/container merely because this paragraph describes transfer. Never mount the development checkout or a DB dump. Keep raw artifact bytes/provenance unchanged.

Before registration inspect the actual cluster-wide fresh_operational_acceptor membership: exactly the one intended installer may be its member, as enforced by the unchanged validator. A second database in the same cluster does not isolate roles. Do not amend another registration, add another acceptor member, use a dummy SHA, or change a guard. The empty metadata install has no input-bound registration; this explicit OPTIONAL stage registers once after actual input selection and exclusive authority are established. If that authority is absent, stop and obtain an exact target decision.

```sh
# Stage Five / separate target-and-input release required; NOT Stage Four execution.
vf --profile install run --rm provision -m release.register_mta --input-sha256 3a4bf3a699c57fab7f00e6820f43c0e1b661386c9cf3aa4f21fd4081e110bdbe
vf --profile install run --rm mta-install -m release.optional_initialize /var/lib/vectorflow/inputs/initialization.json
vf --profile install run --rm mta-install -m release.optional_initialize /var/lib/vectorflow/inputs/initialization.json --apply
```

The first optional_initialize invocation only inspects the existing native contract using exact input/configuration/recipe digests. The second explicitly applies once, validates existing native ownership, initializes only supplied masters/opening and binds the complete optional family owners in one transaction. Save its source/opening/content/implementation/receipt identities and independently read back exact typed input/master state. Verify zero calculation/capture/task and no publication. A second apply is refused before mutation; native initialization's underlying identical REVERIFIED policy remains unchanged. Preserve any failed target/receipt; no reset/reseed/registration replacement or automatic retry. Selecting a source for initialized master reads does not create a report publication or permissions.

## Manual destruction and clean reinstall of the 8080 Windows trial

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

This is the user's explicitly requested **destructive local-trial reinstall** procedure for `I:/VectorFLOW-Trial`, project `vectorflow-localtrial`, on `127.0.0.1:8080`. It is not an upgrade or production rollback. This request permits removing/recreating this trial's MTO container and data as part of the whole trial; it does not permit editing MTO code/configuration or touching another MTO instance. Run these blocks manually in order in the same PowerShell session. Documentation validation does not mean these commands were executed.

Deleting the eight named volumes permanently removes the trial PostgreSQL cluster (both MTA/MTO databases, identity accounts, roles, sealed registration and the approved metadata-verification database/roles), Redis sessions, generated files, downloads and service logs. The subsequent installation creates new empty databases and requires a newly created administrator. The old `trial` account will not survive. Archiving the source folder below is **not a database backup**. If any database contents must be retained, stop here and arrange a database/volume backup first.

Keep Docker images, the approved source/runtime archives and the protected 3005/3006/3002/3003/3004 resources. Do not use Docker Desktop "delete all", `docker system prune`, `docker volume prune`, `docker network prune`, a shared Docker/WSL restart, or an unqualified fleet-wide remove command.

### 1. Verify the exact owned resources, then destroy only this trial

The inventory checked on 17 October 2026 contains six service containers, the eight volumes below and one network. These checks deliberately stop if that footprint has changed or another container uses any trial resource. Do not relax the checks to make deletion pass.

```powershell
$ErrorActionPreference = 'Stop'
$TrialRoot = [IO.Path]::GetFullPath('I:/VectorFLOW-Trial')
if ($TrialRoot.TrimEnd('\','/') -ne 'I:\VectorFLOW-Trial') {
  throw 'Unexpected absolute cleanup root'
}
if (-not (Test-Path -LiteralPath "$TrialRoot/operator.env" -PathType Leaf)) {
  throw 'Original trial folder not found; do not guess another target'
}
$TrialProject = 'vectorflow-localtrial'
$TrialNetwork = 'vectorflow-localtrial_application'
$ExpectedServices = @('auth','mta','frontend','mto','postgres','redis')
$ExpectedVolumes = @(
  'vectorflow-localtrial_auth_data',
  'vectorflow-localtrial_auth_logs',
  'vectorflow-localtrial_mta_data',
  'vectorflow-localtrial_mto_data',
  'vectorflow-localtrial_mto_downloads',
  'vectorflow-localtrial_mto_logs',
  'vectorflow-localtrial_postgres_data',
  'vectorflow-localtrial_redis_data'
)
function Invoke-TrialDocker {
  $OutputLines = & docker @args
  if ($LASTEXITCODE -ne 0) { throw 'Docker command failed; stop and inspect' }
  $OutputLines
}
$TrialContainerIds = @(Invoke-TrialDocker ps -aq --filter "label=com.docker.compose.project=$TrialProject")
if ($TrialContainerIds.Count -ne 6) { throw 'Expected exactly six trial containers' }
$TrialContainers = @(Invoke-TrialDocker inspect @TrialContainerIds | ConvertFrom-Json)
$ActualServices = @($TrialContainers | ForEach-Object { $_.Config.Labels.'com.docker.compose.service' })
if (Compare-Object ($ExpectedServices | Sort-Object) ($ActualServices | Sort-Object)) {
  throw 'Unexpected service roster'
}
$ActualVolumes = @(Invoke-TrialDocker volume ls -q --filter "label=com.docker.compose.project=$TrialProject")
if (Compare-Object ($ExpectedVolumes | Sort-Object) ($ActualVolumes | Sort-Object)) {
  throw 'Unexpected volume roster'
}
$VolumeRows = @(Invoke-TrialDocker volume inspect @ExpectedVolumes | ConvertFrom-Json)
foreach ($VolumeRow in $VolumeRows) {
  if ($VolumeRow.Labels.'com.docker.compose.project' -ne $TrialProject) {
    throw 'Volume ownership differs'
  }
}
$NetworkRows = @(Invoke-TrialDocker network inspect $TrialNetwork | ConvertFrom-Json)
if ($NetworkRows.Count -ne 1 -or $NetworkRows[0].Labels.'com.docker.compose.project' -ne $TrialProject) {
  throw 'Network ownership differs'
}
$AllContainerIds = @(Invoke-TrialDocker ps -aq)
$AllContainers = @(Invoke-TrialDocker inspect @AllContainerIds | ConvertFrom-Json)
foreach ($ContainerRow in $AllContainers) {
  if ($ContainerRow.Config.Labels.'com.docker.compose.project' -eq $TrialProject) { continue }
  $SharedVolumes = @($ContainerRow.Mounts | Where-Object { $_.Type -eq 'volume' -and $_.Name -in $ExpectedVolumes })
  $SharedNetwork = @($ContainerRow.NetworkSettings.Networks.PSObject.Properties.Name) -contains $TrialNetwork
  if ($SharedVolumes.Count -gt 0 -or $SharedNetwork) {
    throw "Another container references trial resources: $($ContainerRow.Name)"
  }
}
$TrialContainers | Select-Object Name, @{Name='Service';Expression={$_.Config.Labels.'com.docker.compose.service'}}
$ExpectedVolumes
$TrialNetwork
if ((Read-Host 'Permanently delete this trial database, accounts and files? Type DESTROY-8080') -cne 'DESTROY-8080') {
  throw 'Cleanup cancelled'
}
# Exact validated container IDs only; no other project's container is selected.
Invoke-TrialDocker container stop --time 30 @TrialContainerIds
Invoke-TrialDocker container rm @TrialContainerIds
Invoke-TrialDocker volume rm @ExpectedVolumes
Invoke-TrialDocker network rm $TrialNetwork

# Verify removal. A partial failure is a stop, not permission for global cleanup.
if (@(Invoke-TrialDocker ps -aq --filter "label=com.docker.compose.project=$TrialProject").Count) {
  throw 'Trial containers remain'
}
if (@(Invoke-TrialDocker volume ls -q --filter "label=com.docker.compose.project=$TrialProject").Count) {
  throw 'Trial volumes remain'
}
if (@(Invoke-TrialDocker network ls -q --filter "label=com.docker.compose.project=$TrialProject").Count) {
  throw 'Trial network remains'
}
if (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue) {
  throw '8080 is still occupied; identify its owner, do not kill an unrelated process'
}

# Preserve original sources/operator files/secrets privately, rather than delete them.
# Resolve both absolute paths and require the same intended parent before moving.
$TrialParent = Split-Path -Parent $TrialRoot
$RetiredRoot = [IO.Path]::GetFullPath((Join-Path $TrialParent ("VectorFLOW-Trial.retired-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))))
if ((Split-Path -Parent $RetiredRoot) -ne $TrialParent -or $RetiredRoot -eq $TrialRoot -or (Test-Path -LiteralPath $RetiredRoot)) {
  throw 'Unsafe or existing archive destination'
}
Set-Location -LiteralPath $TrialParent
Move-Item -LiteralPath $TrialRoot -Destination $RetiredRoot
Write-Host "Old folder preserved at $RetiredRoot; it contains private secrets, not a database backup."
```

The eight volumes remove the complete **trial-owned** PostgreSQL cluster, so no separate DROP DATABASE, DROP ROLE, migration reversal, registration edit or deletion of the verification database is needed. No old volume is reused for the new installation. Images are intentionally retained.

### 2. Extract the corrected package into a new folder

This subsection uses the exact already delivered local package. A future release must substitute its own approved manifest and hashes; do not substitute the withdrawn 701e package. The runnable application is pinned to `bd309169b8f494ed8c93f47302327d74c341923b`; a documentation-only follow-up commit does not require rebuilding the frozen frontend/MTO or these images.

```powershell
$PackageDirectory = 'D:/freshvcf-build/evidence/handoff3005-s2-20261013-001/s4-deployment-gap-implementation-20261017'
$SourceZip = Join-Path $PackageDirectory 'vectorflow-stage4-source-bd309169.zip'
$RuntimeArchive = Join-Path $PackageDirectory 'export-bd309169/vectorflow-stage4-runtime.tar.gz'
if ((Get-FileHash -LiteralPath $SourceZip -Algorithm SHA256).Hash.ToLowerInvariant() -ne '2afce44024bad553249fb38dbfb4796b38a77cd56b2bb318b82c29a4d5a807ad') {
  throw 'Source ZIP differs'
}
if ((Get-FileHash -LiteralPath $RuntimeArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne '8d5d2c5db40c3cac9a5b4cf7f14faade8afc37e82a376953c4eeb5c338790520') {
  throw 'Runtime archive differs'
}
if (Test-Path -LiteralPath $TrialRoot) { throw 'Fresh destination already exists' }
Expand-Archive -LiteralPath $SourceZip -DestinationPath $TrialRoot
Copy-Item -LiteralPath $RuntimeArchive -Destination "$TrialRoot/vectorflow-stage4-runtime.tar.gz"
# Reuse the known local subnet configuration, NOT an old image/upgrade override.
Copy-Item -LiteralPath "$RetiredRoot/network-local.yaml" -Destination "$TrialRoot/network-local.yaml"
$SourceManifest = Get-Content -Raw -LiteralPath "$TrialRoot/release-source.json" | ConvertFrom-Json
if ($SourceManifest.source_commit -ne 'bd309169b8f494ed8c93f47302327d74c341923b') {
  throw 'Wrong release'
}
Invoke-TrialDocker load --input "$TrialRoot/vectorflow-stage4-runtime.tar.gz"
```

Use the new package's `loaded-images.yaml`. Do **not** copy the retired `loaded-images.yaml`, `frontend-local.yaml`, either previous Stage4 image override, or the withdrawn 701e override. Those old overrides can pin old backend images. The network override carries only the previously selected subnet `198.18.57.0/28`; inspect `docker network ls/inspect` and `Get-NetRoute` before reusing it. If overlap exists, stop and choose a reviewed non-overlapping subnet. Do not change Docker daemon pools or prune other networks.

### 3. Create new private settings and run the empty installation

The databases and accounts are new. Generate new private signing/database/RSA secrets while retaining the public client cipher from `public-build.json`, which matches the unchanged frontend. Do not reuse the old secret directory by accident. A new administrator is created interactively below.

```powershell
$PublicBuild = Get-Content -Raw -LiteralPath "$TrialRoot/public-build.json" | ConvertFrom-Json
$RuntimeImages = Get-Content -Raw -LiteralPath "$TrialRoot/runtime-images.json" | ConvertFrom-Json
$PrivateRoot = New-Item -ItemType Directory -Path "$TrialRoot/private" -ErrorAction Stop
$OperatorIdentity = [Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $PrivateRoot.FullName /inheritance:r /grant:r "${OperatorIdentity}:(OI)(CI)F"
if ($LASTEXITCODE) { throw 'Private directory ACL setup failed' }
Invoke-TrialDocker run --rm --network none --user 0:0 --entrypoint python --mount "type=bind,src=$($PrivateRoot.FullName),dst=/private" $RuntimeImages.services.auth.image_id -m release.prepare_secrets --directory /private/secrets --public-client-cipher-key $PublicBuild.client_cipher_key
Copy-Item -LiteralPath "$TrialRoot/release/.env.example" -Destination "$TrialRoot/operator.env"
# Edit only the new operator configuration, not application code.
$OperatorLines = @(Get-Content -LiteralPath "$TrialRoot/operator.env")
$TrialSettings = @{
  VF_PROJECT = 'vectorflow-localtrial'
  VF_RELEASE = 'bd309169b8f494ed8c93f47302327d74c341923b'
  VF_SECRETS_DIR = "$TrialRoot/private/secrets"
  VF_CLIENT_CIPHER_KEY = $PublicBuild.client_cipher_key
  VF_BIND_ADDRESS = '127.0.0.1'
  VF_HTTP_PORT = '8080'
  VF_PUBLIC_URL = 'http://127.0.0.1:8080'
  VF_PUBLIC_WS_URL = 'ws://127.0.0.1:8080'
}
foreach ($SettingName in $TrialSettings.Keys) {
  $Pattern = '^' + [regex]::Escape($SettingName) + '='
  if (@($OperatorLines | Where-Object { $_ -match $Pattern }).Count -ne 1) {
    throw "Missing or duplicate setting: $SettingName"
  }
  $OperatorLines = @($OperatorLines | ForEach-Object {
    if ($_ -match $Pattern) { "$SettingName=$($TrialSettings[$SettingName])" } else { $_ }
  })
  # Compose shell environment overrides its env file. Remove stale values for this session.
  Remove-Item -LiteralPath "Env:$SettingName" -ErrorAction SilentlyContinue
}
$OperatorLines | Set-Content -LiteralPath "$TrialRoot/operator.env" -Encoding utf8
function vf {
  & docker compose --project-name vectorflow-localtrial --env-file "$TrialRoot/operator.env" `
    -f "$TrialRoot/release/compose.yaml" -f "$TrialRoot/loaded-images.yaml" `
    -f "$TrialRoot/network-local.yaml" @args
  if ($LASTEXITCODE) { throw 'Compose failed; stop at this step and preserve the failure' }
}
python "$TrialRoot/release/preflight.py" --source-root $TrialRoot --env-file "$TrialRoot/operator.env" `
  --compose-file "$TrialRoot/release/compose.yaml" --compose-file "$TrialRoot/loaded-images.yaml" `
  --compose-file "$TrialRoot/network-local.yaml"
if ($LASTEXITCODE) { throw 'Preflight refused; do not provision' }
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
vf --profile install run --rm --no-deps provision -m release.metadata_access
vf --profile install run --rm --no-deps provision -m release.metadata_access --apply
vf --profile install run --rm --no-deps auth-install manage.py createsuperuser
vf up -d --wait mta auth mto frontend
vf ps
Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8080/healthz'
Start-Process 'http://127.0.0.1:8080'
```

The private-directory ACL command restricts the new directory to the current Windows operator; inspect resulting ACLs on your filesystem before retaining secrets there. Check other stale `VF_*`, `MTA_*`, `MTO_*`, `AUTH_*` or `DB_*` process environment settings if Compose reports a different effective configuration; never print secret values as a diagnostic. Use a fresh PowerShell session if necessary and rerun only the non-destructive preparation before provisioning, not database creation after partial failure.

If any install step fails, stop at that step; do not paste the remainder or rerun provisioning blindly over partial databases. No automatic cleanup/retry is implied. On successful empty installation: health200, readiness503 without a publication, original MDM metadata/family definitions available, zero initialization/source/calculation rows, and no old login/session. Existing BPR/Planning no-publication limitations remain explicit. Do not load the separate optional input pack, register an input SHA, execute a day or publish a run as part of this reinstall. Those are separate Stage5 work.

A direct Git clone/export path remains documented in "Clean Windows folder". It must still use the matching approved runtime archive/public-build/loaded-image descriptors with the frozen frontend. This local reinstall block intentionally consumes the verified delivered ZIP; it does not pretend Git alone stores Docker image layers.

## MTA/auth-only correction of an existing registered empty trial

Preserve source/images/config/secrets/account/scope/registration/database identities first. Verify new code against the existing immutable namespace/capability using read-only runtime connections. Do not rerun provision, migrations, grants or registration against that sealed target. Keep its original frontend/MTO/PG/Redis/container network/port/volumes/start states. Select only reviewed MTA/auth image IDs in a final operator override and replace only those two services with --no-deps --no-build --pull never; one necessary MTA/auth restart/reload is the persistence proof. Preserve old images/export/override and compatible rollback; do not select an old image over changed schema or silently re-enable the withdrawn setup release. Current approved correction does not change schema or the original registration.
