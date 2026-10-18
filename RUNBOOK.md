# Production installation entry point

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

Use [release/SOURCE_BUILD.md](release/SOURCE_BUILD.md) for a clean Git build, or [release/RUNBOOK.md](release/RUNBOOK.md) for the retained image package. Blank installation is separate from optional master/opening loading and daily execution. The Git route is still under independent verification; no new installation PASS is implied.

Everything below is retained **historical development material**, including its old dates, services, holds and status statements. It is not the current production installation checklist and must not override the linked procedures or current human authorization. Do not execute its startup/setup commands for a new deployment.

---

# Historical development runbook

## Operator entry point — 7 October 2026

**Execute only steps 1–3 in the [temporal validation operator procedure](docs/OFFLINE_TEMPORAL_VALIDATION_RUNBOOK.md), then stop.**
The full `temporal-full-001` run is on human hold. Those three steps read retained
status and hand over evidence; they do not resume calculation or publish a run.
Do not execute the held H1–H8 procedure or startup/setup commands below.
The remaining sections retain earlier deployment instructions and provenance;
they are not the current operator checklist. Current authorization and acceptance
status are maintained only in [docs/MIGRATION.md](docs/MIGRATION.md).

This build is not the application served on3004. An isolated F3 work-in-progress
preview is available on3005; it is NOT full F3 acceptance or a3004 cutover.
Do not run copied historical startup scripts.

## Isolated daily-publication shell on3006 (6 October2026)

The accepted April fixture remains on **http://localhost:3005**. The separately
owned **http://localhost:3006** shell is for the authorized daily connection work.
It has no selected run or business dataset: MTA health is200, readiness and report
requests are503. Normal login was verified as `stage2.broad@vectorflow.local`;
the existing password remains in
`D:/freshvcf-build/preview/secrets/stage2-fixture-accounts.json`. The restricted
identity was also preserved. Use normal CAPTCHA login, without credential reset.

Owned deployment config/secrets are outside Git under
`D:/freshvcf-build/daily-3006/`; compose project is `freshvcf-daily3006`, database
`daily_3006`, volume `freshvcf-daily3006_daily-db`, network
`freshvcf-daily3006_daily`. Separate identity and MTO schemas and Redis prevent
writes into3005. Only the frontend maps127.0.0.1:3006. All restart policies are
`no`; MTA remains4GiB/2CPU. No whole-database or calculated-row copy was used.

Use `D:/freshvcf-build/venv/Scripts/python.exe tools/daily_stack_verify.py --label NEW_LABEL`
for read-only shell/isolation proof. This initial-shell check deliberately requires
zero daily runs/publications and must not be reused as a later populated-run check.
Focused commands run through `tools/daily_stack_check.py --label NEW_LABEL` followed
by `manage.py` and its arguments; they use only the owned3006 database. Labels
cannot overwrite earlier evidence. Do not run `daily_stack_setup.py prepare`
against existing configuration or import the identities again.

Future daily input entry remains `mta.runtime.temporal.execute_day`, with explicit
`mdm_source` for a fresh capture or `mdm_retry` naming a failed capture. A retry
uses a new execution revision and the same frozen request. No scheduler or latest
run selection exists. Unsupported pair-grain DBMActive exclusion changes fail
before consuming queues. See LEGACY_EXCEPTIONS.md for the exact boundary.

After a separately authorized genuine daily execution and independent parity
acceptance, prepare explicitly with `manage.py prepare_daily_ui --run-id UUID
--output-digest DIGEST`. An incomplete result exits unsuccessfully and retains
per-layer diagnostics and reusable successful rows. Once the complete roster is
ready, `manage.py check_daily_selection --run-id UUID --output-digest DIGEST`
validates parity/source/config/row seals and prints the matching selection fields.
It does not write config or restart anything. Apply those fields together only
to the owned3006 config, alongside its exact permissions/catalogue bindings, then
start the owned MTA process with admission enabled. Never insert a parity PASS,
reuse April qualification, or select an earlier run to fill an empty grid.

Current blockers are BPR remarks, a genuine shipment ledger, normal BOR Black/full
supplier sources, full opening BOROA allocation/requirements/remarks, daily
Expedite request rows and pair-grain MDM exclusions. The lower-level BOROA result
does not provide all41 allocation fields; opening SOB/MOQ cannot substitute it.
Therefore no complete publication can currently be selected. MTO startup here
does not establish MTO business acceptance.

The next10-pair smoke is **not released by steps1&2**. Its handoff must first pin
owned attempt/registered inputs, exact scope and source-gap disposition. Then use
the existing execute_day boundary, prove complete readback and each layer's exact
result, failure/retry and unchanged selection; do not broaden to1240 pairs or
report/browser acceptance without the next authorization. Current source and
evidence status is only in `docs/MIGRATION.md`.

## Current three-family MDM preview (6 October 2026)

The current3005 selection is the isolated April7 fixture run
`bfd75b4b-a9df-4a08-82d3-852e3324b623`. SKU, Location and SKU–Location are the
released MDM families. Later sections retain older preview provenance; they do
not authorize replacing this selected run or starting daily publication.

Verified test actors are `stage2.broad@vectorflow.local` (reviewer, user2) and
`stage2.restricted@vectorflow.local` (requester, user3). Existing passwords remain
in `D:/freshvcf-build/preview/secrets/stage2-fixture-accounts.json`, outside Git.
Use normal login/CAPTCHA; do not reset credentials or expand scopes.

Direct MTA routes under `/mta/master-data-management/` are
`control-panel/view-modify`, `control-panel/add`, `control-panel/delete`,
`saved-drafts`, `task-pending`, `task-status` and `data-modification-history`.
Choose the family in the unchanged field picker, then apply a filter or Show All.
The broad account's installed current populations are234 Location and97,097
SKU–Location rows; requester3 sees6 and5,076 respectively. Browser grid filters
work and both new-family Excel exports are human-confirmed. The retained menu
visibility gap remains documented; use the direct routes.

Location/SKU–Location approvals persist typed pending inputs. Their current grids
remain unchanged until the canonical daily consumer executes; this tranche does
not authorize that execution. History's selector excludes later-today tasks by
the retained midnight cutoff. Mixed-family drafts remain unqualified. Location
modify-review old values use the explicitly approved history correction;
Location and SKU–Location modify downloads retain the native old-value defect
documented in `docs/LEGACY_EXCEPTIONS.md`.

Current image tags: `freshvcf-preview-mta:mdm-families-20261006-003` and
`freshvcf-preview-user:mdm-families-20261006-001`. Migration0052 is additive and
already applied; do not alter applied migrations or reinstall family source rows.
Builds overlay only MDM onto the accepted SKU image because unrelated HEAD report
changes are not an accepted serving baseline. Each service retains its own
Compose config chain from its container labels. Never assemble a new chain from
historical examples or build whole HEAD for deployment.

Evidence and guarded deployment/restart scripts are in
`D:/freshvcf-build/evidence/mdm-location-skuloc-20261006-001`. Refer to
`docs/MIGRATION.md` for the current acceptance status. Restart only the owned MTA
container and allow startup admission to finish before requesting routes; never
restart shared Docker/WSL, reset a database, or replace3004.

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
supplement the original NULL hierarchy still denies scope. The approved June17
terminal-only empty transit/initial remarks supplement now connects BPR count/grid
reads; it does not certify nonempty logistics. Planning GIT detail views, other
detailed transit consumers, full filters/actions/downloads and the
Expedite unordered-parent-label qualification remain open. Do not use this
preview to submit business actions or claim complete application acceptance.

The DBM column/layout connection is evidenced separately in
`D:/freshvcf-build/evidence/f3-ui-state-comparison-001/receipt.json` and
`f3-ui-state-http-002/receipt.json`:16 visible typed columns,10 selected layout
steps and authenticated readback. A remaining frontend column-state warning is
still tracked under F3.3; these receipts do not close full screen acceptance.

### Restart or stop ONLY this preview

Stage1 publication admission runs once in the MTA Gunicorn master with
`--preload`, before opening its listener or forking either worker. It checks
the explicit accepted run/input/native output,
complete command state, opted-in permission/hierarchy/terminal configuration and
the five existing typed report projections. It retains only an identity digest,
not publication rows. Missing/corrupt input, projection or supplement aborts
startup with a nonzero exit: no listener or worker starts and readiness cannot
succeed. The gateway consequently reports an unavailable upstream. Database
connections are closed before fork; both workers inherit the same admission.
Ordinary reads check only bounded identity metadata/files, plus their unchanged
reader checks. Changes to that identity revoke admission until an MTA restart;
restoring a setting does not silently admit it. Investigate the startup error,
restore the exact pinned identity/source, and restart MTA. Never switch to a trial
run, replay accepted days, enable actions or weaken a validator to obtain readiness.

For an authorized MTA-only deployment/restart, use the existing commands:

```powershell
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml build mta
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml up -d --no-deps --no-build mta
# For a restart of the same image only:
docker compose --env-file D:/freshvcf-build/preview/preview.env -f compose.preview.yaml restart mta
docker logs --tail 20 freshvcf-preview-mta-1
docker exec freshvcf-preview-mta-1 python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/readyz',timeout=30).read().decode())"
```

Wait for one **Publication admitted** message before **Listening at**, then
two **Booting worker** messages and successful readiness. Do not
raise the existing180-second timeout,2-worker/2CPU/4GiB settings to mask failure.
Container `Started` is insufficient: during admission the unchanged gateway can
return500 for connection refusal. Stage2 Buffer Trends retained such an early
probe; start acceptance requests only after readiness succeeds.
Stage1 proved the unchanged June17 identity before/after MTA-only restart,
ten byte-identical authenticated gateway responses, actual Planning/RRR/DBM
navigation and invalid publication aborting two-worker startup before binding.
Evidence: `D:/freshvcf-build/evidence/f3-stage1-admission-002/receipt.json`
and `f3-stage1-preload-004/receipt.json`; initial001 is retained and superseded
for startup behavior. After successful startup, metadata mismatch returns503
for MTA/readiness until restart. Transient database connection failure also
rejects that request; recovery compares identity again before serving without
repeating full validation. `/healthz` remains a process-only check.
This is selective-serving integrity and smoke evidence, not full application
or legacy performance acceptance. Read-only fault probes patch only returned
in-process values and use PostgreSQL read-only sessions, never persisted rows.

After a bulk publication, inspect PostgreSQL planner statistics before diagnosing
a slow report as a calculation or resource problem. The Stage2 BTR investigation
found no analysis on its13 consumed typed tables: one-row estimates caused1240
nested-loop iterations and a receiving-scope query exceeded45seconds. A bounded
`ANALYZE` of only those owned tables changed the identical root-query plan from
7.527seconds to0.077seconds, with publication and command fingerprints unchanged.
Exact table allowlist, command, before/after statistics and plans are retained in
`D:/freshvcf-build/evidence/f3-stage2-btr-statistics-001` (receipt SHA256
`aea8706feb0080bf38d9eb45f4d2650f8ca8b8602737f7e943ac58e599b5257d`).
This is an observed PostgreSQL plan improvement, not matched legacy performance.
Do not run maintenance per request, broaden it to shared databases, replay a
publication, or raise memory/timeouts. Refresh statistics only for an evidenced
affected owned-table set after relevant population changes; preserve the receipt.

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
proof also passes in `f3-rrr-export-ui-001`; full RRR/F3 acceptance remains open. Other
report exports and selective-read work remain pending. Full publication integrity
is checked explicitly at validation/restart, not on every RRR request.

DBM current/history selective reads now use named committed images. Current
June17 suggestions remain correctly empty. Existing BTR → Daily Data Graph on
SKU337/AG515802 displays computed series and Norm220→294 onJune12,294→392 onJune16.
All1,240 terminal graphs match retained legacy evidence. See
`f3-dbm-selective-004`, `f3-dbm-selective-ui-001` and restart001. This does not
close BTR exports or eligible-action UI acceptance; preview actions stay disabled.

Terminal BPR connection: `GetBPRDataCount` and `GetBPRData` read the seven required
native images, not the whole515-image publication. Explicit opt-in is configured
by VF_MTA_TERMINAL_FILE/SHA256 in compose.preview.yaml, pinning
`baseline/presentation-terminal-v1.json` to this run/date only. Full grid1,240,
permission bags and page2/out-of-range reads match deployed SQL and wire types;
actual cookie readback survives MTA-only restart. Evidence:
`f3-bpr-terminal-003`, `f3-bpr-wire-001`, `f3-bpr-gateway-001`, `f3-bpr-restart-001`.
Do not carry this supplement to another date or treat it as populated transit
acceptance. Active BPR server filters remain explicitly unavailable. Actual
browser BPR Show All shows1,240 rows, page size50, and next page51–100.
Research Insights loads the same1,240-row estate; client grid filters337 and
AG515802 select the retained pair (Norm392). Select its checkbox then Load
Insights for the summary/ageing read. These read-only steps were verified in
`f3-bpr-ui-001`; no business action or layout was saved. Known presentation
limitations: BPR's empty transit panel retains a select-row prompt; Research's
calendar opens at the machine month rather than the June17 report month.
Do not treat this as calendar-date/full screen parity. Remarks/actions,
downloads, remaining configuration and Planning GIT detail views remain pending.

Planning overview counts are now connected through `GetPlanningDataCount`:
June17 root scope returns GIT0/0/0, Expedite7/7/7, Excess85/85 and
Fulfilment1222/1222 (strings, as deployed). Forty independent count comparisons
and authenticated3005 read/restart checks pass. Actual Planning browser proof
is pending browser attachment recovery, not permission to sign in. GIT detail
grids/charts, active Planning filters and full screen acceptance remain open;
overview counts alone do not certify those branches. Evidence:
`f3-planning-overview-003`, `f3-planning-overview-gateway-001`,
`f3-planning-overview-restart-001` under D:/freshvcf-build/evidence.

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

Historical standalone test-only shutdown: `docker compose -f compose.test.yaml stop postgres`.
**Do not run that while3005 is in use**: the preview now depends on this same
owned PostgreSQL container. MTA-only restart does not require a database restart.
Never use down -v, delete the data directory or stop another task's containers.
