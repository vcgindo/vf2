# Fresh build runbook

This build is not the application served on3004. An isolated F3 work-in-progress
preview is available on3005; it is NOT full F3 acceptance or a3004 cutover.
Do not run copied historical startup scripts.

## Open the isolated F3 preview

Use **http://127.0.0.1:3005/login**. The loopback host deliberately differs from
localhost:3004 so browser login cookies cannot overwrite the3004 session.
http://localhost:3005 also serves the app, but shares localhost cookies across
ports; use127.0.0.1 or a separate browser profile when comparing instances.

Verified newly created **local/test-only** account:

- Username: `fresh.preview@vectorflow.local`
- Password: `F3!2e77659192`
- Complete the displayed CAPTCHA. This is a disposable preview credential,
  never a production/external account. No existing user's password was reset.

The browser login and11 authenticated gateway reads were verified against3005,
not inferred from3004. The existing frontend, authentication and MTO sources are
reused unchanged. DBM, BTR, history, insights, RRR and Planning implementation
is partial: the accepted terminal day has no pending DBM suggestions. The
user-approved presentation hierarchy supplement now fills only SL1–3/LL1–3
from the retained200-SKU/20-location permission catalogue. The preview test
account has retained root permissions71001/72001 for MTA application2.
Native engine state and F2 receipts remain unchanged; without this explicit
supplement the original NULL hierarchy still denies scope. Detailed transit
consumers, full filters/actions/downloads and the
Expedite unordered-parent-label qualification remain open. Do not use this
preview to submit business actions or claim complete application acceptance.

The DBM column/layout connection is evidenced separately in
`D:/freshvcf-build/evidence/f3-ui-state-comparison-001/receipt.json` and
`f3-ui-state-http-002/receipt.json`:16 visible typed columns,10 selected layout
steps and authenticated readback. A remaining frontend column-state warning is
still tracked under F3.3; these receipts do not close full screen acceptance.

### Restart or stop ONLY this preview

RRR selective-read checkpoint: open the existing sidebar's SCIH → Rationed
Requirement Report. Click **Show All**:17 Jun2026,14 retained rows. Supply Chain
Node → For Location → Agen shows3; Reset Filters then Show All restores14.
Page Size5 and next page show5 rows with total14. Real3005 filter/clear/paging
and isolated MTA restart-readback were verified; final gateway reads <=0.556s
and four concurrent requests0.5593s on the local warm database. No cold-disk or
legacy timing claim. Evidence is in
`D:/freshvcf-build/evidence/f3-rrr-selective-ui-010/receipt.json` and
`f3-rrr-selective-final-gateway-016/receipt.json`.

RRR **CSV Export is connected** through GetExportDataAsync. It exports the entire
filtered, permission-scoped result regardless of grid page, using the deployed
visible/saved-column rules. Ten independent SQL/header/CSV cases pass exact bytes;
actual3005 root14 and Depo4 HTTP files match legacy and survive MTA restart.
Evidence: `f3-rrr-export-comparison-001`, `f3-rrr-export-gateway-003` and
`f3-rrr-export-restart-001` under the evidence root. Actual toolbar-click/file
proof awaits browser reconnection; full RRR/F3 acceptance remains open. Other
report exports and selective-read work remain pending. Full publication integrity
is checked explicitly at validation/restart, not on every RRR request.

```powershell
Set-Location F:\freshvcf
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml up -d --no-build
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml restart
# Reversible rollback: stop the preview; preserve its database and secrets.
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml stop
```

Never use a blanket Docker restart, `down -v`, prune or delete a data directory.
No command above addresses3004 or its project. Onlyfrontend publishes a port,
bound to127.0.0.1:3005. MTA/auth/MTO/Redis are internal. All three services use
the already-owned `freshvcf-test-postgres-1`, database`freshvcf`, separate
`mta`/`mta_state`, `identity` and`mto` schemas. Do not stop that database while
the preview or a Fresh validation worker needs it. The preview does not connect
to an integrated/demo database or import their data.

Explicit publication: `ac1612c8-0e49-4155-83c3-f59f41422293`, business date
17 June2026, output digest
`bd1c522f3df299d2fc3841aed7f66d48e4307e6967450b2d8a5463dc7867d33d`.
This remains the frozen12-day F2 result. HTTP reads use relational state/report
rows. Only the immutable InputSnapshot is mounted for input-identity validation;
no internal output traces, demo fixtures or fallback dataset are mounted.
The read-time hierarchy binding is `baseline/presentation-hierarchy-v1.json`,
SHA256 `d69c63804798b3cf31f98849341d7a61d38a37fe73c05e627aef1237e5ecfc6a`.
Current DBM recommendations are correctly zero on17-Jun-2026. Historical
SuggestionsLog has132 records; it must not be used as current recommendations.
The preview keeps `VF_MTA_ACTIONS_ENABLED=0`. Positive workflow trials are isolated
under F3.2, using the unchanged retained representative artifact and fixed scenario
clock. Their run IDs are never substituted for this preview's terminal run.

### Fresh preview initialization (not required for ordinary restart)

Prerequisite: the accepted Fresh PostgreSQL database and its F3 projections
already exist. This procedure does NOT generate or replay synthetic calculations.

```powershell
Set-Location F:\freshvcf
& D:/freshvcf-build/venv/Scripts/python.exe tools/preview_setup.py
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml build
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml run --rm --no-deps --entrypoint python mta manage.py migrate --noinput
docker run --rm --user 0 --entrypoint python --env USER_SERVICE_DATABASE_PASSWORD=isolated-test-only-not-a-serving-password --volume D:/freshvcf-build/preview/secrets:/run/secrets freshvcf-preview-user:f3 /usr/local/bin/user-service-key-init.py
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml run --rm --no-deps --entrypoint python user-service manage.py migrate --noinput
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml run --rm --no-deps --entrypoint python mto manage.py migrate --noinput
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml run --rm --no-deps --entrypoint python mto manage.py seed_all
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml run --rm --no-deps --entrypoint python user-service manage.py shell -c "from api.models import User; from django.core.management import call_command; assert not User.all_objects.exists(), 'Refuse to reset an existing preview identity'; call_command('bootstrap_stage7b')"
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml up -d --no-build
# Assign only retained MTA root scopes to the newly bootstrapped preview account.
& D:/freshvcf-build/venv/Scripts/python.exe tools/preview_assign_permissions.py D:/freshvcf-build/evidence/<new-assignment-receipt>
```

`preview_setup.py` preserves an existing config. In a genuinely new environment
it generates a different test password; use that environment's configured value
and verify login before documenting it. Never overwrite an existing environment
file or rerun bootstrap to reset accounts. Signing/encryption/private keys stay
outside Git under`D:/freshvcf-build/preview`; the frontend's transport key is
build-time matched to this local auth service, not copied from3004.

Evidence: `D:/freshvcf-build/evidence/f3-preview-http-002/receipt.json` records
actual image/container/config identities and route results. Protected-runtime
snapshots are in`f3-preview-001`; earlier failed wiring probes remain preserved.
`f3-preview-restart-002` proves login and12 reads after restart;
`f3-preview-two-worker-001` records the final two-worker/4GiB MTA configuration
and identical selected readback. The DBM shell and expanded existing sidebar
render. DBM's16 visible typed columns and selected sequential saved-layout
contract now have source-backed SQL/PostgreSQL proof, with migration0012 for
per-user preferences. Empty grids, full UI actions/downloads and other endpoint
gaps remain unaccepted. Quoted/conflicting layout edge cases are explicitly
qualified in`docs/LEGACY_EXCEPTIONS.md`; no legacy flaw is repaired silently.
An empty grid or visible menu is not proof that the feature is accepted.
The scoped hierarchy checkpoint adds `f3-hierarchy-rrr-comparison-002`: full
14-row/119-field RRR and declared order match isolated canonical SQL.
`f3-preview-hierarchy-http-001` verifies real gateway counts/content: RRR14,
Tech/Eco BTR1,240 each, day12 current DBM0, and nonempty daily history. Full
browser/filter/download acceptance remains open. `f3-action-http-retained-002`
proves62 comparisons through real Django action routes and own next-day state;
it is an isolated two-day trial, separate from the default publication. That
original receipt did not include the real gateway; the following proof does.
`f3-action-gateway-001` now closes that real-gateway action boundary: unchanged
encrypted-password/cookie login, stored identity/scope, unauthorized401 and
unknown-selection403/no writes, positive Apply/Sleep and62 full retained
comparisons with own next-day state. The two private workers expose no host
port and are removed on completion; no trial is selected by3005. Reproduce only
when a relevant change invalidates the proof, with a NEW evidence directory:

```powershell
& D:\freshvcf-build\venv\Scripts\python.exe tools/action_gateway_probe.py --evidence D:/freshvcf-build/evidence/<new-action-trial> --revision <unique-trial-revision>
```

This creates new isolated trial rows; it does not rerun accepted F2 days, mutate
their actions or enable writes on the preview. Full browser/filter/download
acceptance remains open.
The isolated RRR filter checkpoint is `f3-rrr-filters-comparison-001`:44 valid
request cases match actual deployed DLL-generated SQL across all119 fields,
scopes, count/grid paging, raw NULLs, grouped filters and parent-join behavior.
Eight source-invalid SQL cases are flagged NOT_PARITY in LEGACY_EXCEPTIONS.md;
they are not repaired or credited as passing parity. Source and synthetic inputs
remain pinned. This code was verified in the isolated test worker; the3005 image
has NOT been rebuilt for this correction. Gateway filter/browser acceptance is
still pending; do not promote this consumer receipt into whole-application parity.
`f3-rrr-gateway-001` subsequently closes representative real-cookie-gateway
filter acceptance:14 full count/grid envelope comparisons match retained SQL-
validated responses, unauthorized401, and the source-flaw503 remains NOT_PARITY.
It reused existing roots and immutable publication without calculation/replay,
permission changes or preview replacement. Browser and other report acceptance
remain open. The existing private driver supports this read-only check with
`--rrr-filters`; use a new evidence directory only if relevant code changes
invalidate the retained proof. It creates no trial calculation/action rows.
The corresponding BTR isolated checkpoint is `f3-btr-filters-comparison-001`:
59 requests/118 count-grid contracts,104 strict PASS and14 source-invalid
contracts NOT_PARITY. Category/tags and history age/count joins are source-backed;
the legacy grid does not acquire Stock/GIT/PIC/OHIC fields simply because its
count query has them. `f3-btr-gateway-001` passes14 representative full-envelope
cookie-gateway comparisons plus401 and the Stock-grid503 source-flaw guard.
Its private driver uses `--btr-filters`, no host port/calculation/action writes.
Protected serving/publication snapshots are unchanged. These BTR changes are
committed source/private-worker acceptance, NOT a rebuilt3005 preview or3004
cutover. Remaining Planning/insight filters and full UI/MTO/runtime acceptance
stay in the finite F3 checklist in docs/MIGRATION.md.
DBM private checkpoint: `f3-dbm-filters-comparison-001`,82 strict count/grid
contracts PASS and26 attributable source-invalid contracts NOT_PARITY. Uses the
unchanged retained shallow day-zero pre-action population, not SuggestionsLog.
`f3-dbm-gateway-002` exports94 real cookie requests and14 private asserted leaf
scope reads (not leaf-login proof), followed by31 unchanged day-zero engine/action
comparisons. The `--dbm-filters` proof mode creates a newly owned retained trial;
it is NOT a serving startup command or a full-depth replay. Terminal default
current count0/gridNULL remains unchanged. Trial001 non-final reads are preserved.
These committed source/private-worker changes are not rebuilt preview/3004
acceptance. All F2 accepted receipts and protected serving identities remain intact.
Next authorized delivery checkpoint rebuilds/redeploys only3005 from committed
HEAD, retaining the F2 terminal publication and approved hierarchy. Every frontend
exit now requires authenticated real-screen3005 proof; backend/private evidence
alone cannot certify UI delivery.3003/3004 remain unchanged.
The default MTO settings catalogue is initialized, but no MTO business dataset
was invented; full direct-port MTO regression is still F3.4 work.

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

## Fresh legacy oracle (Windows, test-only)

Install `requirements-parity-windows.txt` in the D: virtual environment. With
MSSQLSERVER already running, provision only the dedicated Fresh databases:

```powershell
$env:VFTEST_PROFILE = 'fresh'
& D:\freshvcf-build\venv\Scripts\python.exe -m parity.provision_legacy
& D:\freshvcf-build\venv\Scripts\python.exe -m parity.replay_current_day D:\freshvcf-build\evidence\<new-directory> retained-sizeable
```

The create-only provisioner requires its MDF/LDF directory permission for the
SQL Server service identity. It never drops/rebuilds existing databases. A schema
fingerprint mismatch is a failure, not permission to overwrite its receipt.
The disabled SQL login `freshvcf_oracle_replay` has rights only in VFTEST_Fresh_*
and is impersonated WITH NO REVERT during calculations. Windows administrator
access is used only for owned provisioning, physical-path/schema checks and the
exclusive lease. Existing VFTEST/Block2/Demo databases are not replay targets.

Named retained fixtures can replace `retained-sizeable` in the command. This does
not authorize inventing/replacing synthetic data. Full source/input/failed-run
receipts remain in the unique output directory. For selected GulfOil retained
comparisons use `python -m parity.verify_gulfoil <new-evidence-directory>`; its
parser qualification performs only a fixed read-only mapping metadata query.

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
