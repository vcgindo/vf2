# CSV starter: master/opening, day1 and day2

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

Use these steps **instead of SOURCE_BUILD steps5 onward**, after blank installation steps1–4. Run the blocks in order in the **same PowerShell7 session**, from your clone. Do not mix this with the JSON starter path. Stop at the first error; retain files/receipts. No repeat blank installation or reset.

The unchanged RAW synthetic sample has200SKU/20location definitions,12 active master pairs, opening17October2026, and16 daily records on18October/day1 and19October/day2. Many required carry/history/scratch populations are legitimately empty header-only CSVs. This is not a production-volume or nonempty-every-workflow test.

All master/opening row populations and daily facts are CSV. Tools generate JSON **control manifests**, checksums, receipts and an internal native-opening artifact for provenance/downloads. Operators do not author or submit JSON business-input files. CSV delegates to the SAME native initializer, calculations and report preparation.

## 5. Prepare the pack

For a clone/image built before the CSV opening importer, first `git pull --ff-only`, then `docker compose build mta` and check its exit code. This builds **only MTA**, not frontend/MTO/auth, and does not reinstall or load data. It is safe here only while MTA is unregistered/blank; existing sealed installations need their own upgrade procedure. A fresh installation built from this revision already contains the importer.

```powershell
$ErrorActionPreference = 'Stop'
# Set this only when using an already prepared, verified CSV pack.
# Example: 'I:/VectorFLOW-input/starter-csv-complete-20261019'
$PreparedCsvPack = ''
$Project = (docker compose config --format json | ConvertFrom-Json).name
if ($LASTEXITCODE -ne 0 -or -not $Project) { throw 'Compose configuration failed' }
if (Select-String -Path .env -Pattern '^\s*COMPOSE_(FILE|PATH_SEPARATOR)\s*=' -Quiet) { throw 'Existing Compose override: merge deliberately, do not overwrite' }
$Parent = (New-Item -ItemType Directory -Force (Join-Path $env:LOCALAPPDATA "VectorFLOW/$Project")).FullName.Replace('\','/')
$InputRoot = if ($PreparedCsvPack) { (Resolve-Path $PreparedCsvPack).Path.Replace('\','/') } else { "$Parent/starter-csv" }
if (-not $PreparedCsvPack) {
  if (Test-Path $InputRoot) { throw 'CSV directory exists; reconcile, do not reload' }
  $Helper = (Resolve-Path ./tools/create_daily_csv_example.py).Path
  $RawZip = (Resolve-Path ./examples/starter-data/vectorflow-starter-inputs-v1.zip).Path
  docker compose run --rm --no-deps -v "${Helper}:/helper.py:ro" -v "${RawZip}:/starter.zip:ro" -v "${Parent}:/examples" mta-install /helper.py --source /starter.zip --output /examples/starter-csv --csv-onboarding
  if ($LASTEXITCODE -ne 0) { throw 'CSV pack preparation failed' }
}
$Receipts = New-Item -ItemType Directory "$InputRoot/receipts"
$Opening = Get-Content "$InputRoot/opening/opening-manifest.json" -Raw | ConvertFrom-Json
$ManifestHash = (Get-FileHash "$InputRoot/opening/opening-manifest.json" -Algorithm SHA256).Hash.ToLowerInvariant()
$PermissionHash = (Get-FileHash "$InputRoot/permissions.json" -Algorithm SHA256).Hash.ToLowerInvariant()
```

`opening/*.csv` are the actual one-time ingestion inputs. The manifest declares each population's path, columns/types, row count and checksum plus configuration/recipe. Keep the whole directory; do not edit a sealed pack/dates. CSV uses UTF-8, comma, normal quoting; `\N` means NULL; empty text remains empty; codes remain text. Column types are `text`, finite `number` (integer/decimal/exponent spelling preserves the native representation), or `bit` (true/false or0/1). Mixed numeric/text representations in one column and literal text `\N` are refused. Existing native type/range/width/date/ownership checks still apply. Header-only files explicitly represent empty populations; nothing is silently omitted.

## 6. Register and initialize CSV master/opening ONCE

```powershell
docker compose stop mta
if ($LASTEXITCODE -ne 0) { throw 'Could not stop MTA' }
docker compose run --rm --no-deps provision -m release.register_mta --input-sha256 $Opening.native_input_sha256
if ($LASTEXITCODE -ne 0) { throw 'Registration failed; stop, do not repeat/reset' }
$InitArgs = @('manage.py','initialize_production','/input/opening','--csv',
  '--sha256',$ManifestHash,'--configuration-digest',$Opening.configuration_digest,
  '--recipe-digest',$Opening.recipe_digest)
docker compose run --rm --no-deps -v "${InputRoot}:/input:ro" mta-install @InitArgs --inspect
if ($LASTEXITCODE -ne 0) { throw 'Opening CSV inspection failed' }
$InitText = docker compose run --rm --no-deps -v "${InputRoot}:/input:ro" mta-install @InitArgs
$InitExit = $LASTEXITCODE
$InitText | Set-Content "$Receipts/initialization.json" -Encoding utf8
if ($InitExit -ne 0) { throw 'Initialization failed; retain state' }
$Init = $InitText | ConvertFrom-Json
if ($Init.status -ne 'INITIALIZED' -or $Init.input_sha256 -ne $Opening.native_input_sha256) { throw 'Expected one NEW matching initialization; reconcile' }
```

Registration pins the reconstructed input; `--csv --sha256` pins the manifest and every CSV before entering the native initializer. Its transaction, typed storage, readback, ownership and no-output-seeding guards are unchanged. The receipt records native-input and CSV-manifest hashes. No daily calculation has occurred.

## 7. Bind the receipt, access catalogue and daily paths

```powershell
$Binding = Get-Content "$InputRoot/binding-template.json" -Raw | ConvertFrom-Json
$Binding.initialization_id = $Init.opening_id
$Binding.source_digest = $Init.source_digest
$Binding | ConvertTo-Json -Depth 100 | Set-Content "$InputRoot/binding.json" -Encoding utf8
$Access = @{VF_MDM_SOURCE_DIGEST=$Init.source_digest; VF_MTA_PERMISSIONS_FILE='/access/permissions.json'; VF_MTA_PERMISSIONS_SHA256=$PermissionHash}
$Mount = @{type='bind'; source="$InputRoot/permissions.json"; target='/access/permissions.json'; read_only=$true}
$DataCompose = "$InputRoot/compose.csv-starter.json"
@{services=@{mta=@{environment=$Access.Clone();volumes=@($Mount)}; 'mta-install'=@{environment=$Access.Clone();volumes=@($Mount)}}} | ConvertTo-Json -Depth 8 | Set-Content $DataCompose -Encoding utf8
$StateRoot = "$Parent/daily-operations"
Add-Content .env "`nCOMPOSE_PATH_SEPARATOR=;`nCOMPOSE_FILE=`"compose.yaml;$DataCompose`"`nVF_DAILY_INPUT_DIR=$InputRoot`nVF_DAILY_BINDING_FILE=$InputRoot/binding.json`nVF_DAILY_STATE_DIR=$StateRoot`nMTA_SELECTION_FILE=/var/lib/vectorflow/selection.json"
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'CSV/access configuration failed' }
```

The catalogue defines sample groups, not user grants. The real installed administrator has full current MTA access; ordinary users need explicit roles/scopes. Keep `.env`, override, complete CSV pack/receipts and state directory with matched database/files/secrets backups. Generated native-opening.json is an immutable provenance artifact derived from CSV, not the file submitted for initialization.

## 8. Day1 — CSV intake through selected reports

```powershell
pwsh -NoProfile -File ./release/run_daily.ps1 -BusinessDate 2026-10-18
if ($LASTEXITCODE -ne 0) { throw 'CSV day1 failed; retain receipt and stop' }
```

Expect `PUBLISHED`,18October and actual run/output IDs. Existing orchestration snapshots CSV originals, validates/ingests, calculates once, prepares the full existing report roster, selects the generation and restarts **only MTA**. No separate JSON-day/report/selection command is needed. Open the configured URL, refresh the administrator session, then BPR → **Show All**, Planning → category → **Grid View**, RRR and DBM. Expect18October. DBM may legitimately have0 suggestions; empty/header-only reports are not positive scenario proof.

## 9. Day2 — own persisted day1 predecessor

```powershell
pwsh -NoProfile -File ./release/run_daily.ps1 -BusinessDate 2026-10-19
if ($LASTEXITCODE -ne 0) { throw 'CSV day2 failed; retain receipt and stop' }
docker compose ps
```

Expect `PUBLISHED` and19October; refresh the same UI. No predecessor UUID is copied manually. Never repeat initialization, change dates or replay an accepted day. See [CSV_DAILY_RUN.md](CSV_DAILY_RUN.md) for rejection receipts/explicit resume of committed preparation/serving failures. Failed calculations are not automatically retried.
