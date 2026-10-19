# Production CSV intake and daily operation

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

Installation stays blank. Register and initialize authentic masters/opening once using the existing native onboarding procedure. CSV intake is the subsequent dated operation; it never installs a database, initializes again or creates users/scopes. This release supports fresh installation with its new metadata migration and current-source registration. An existing sealed installation needs a separately verified upgrade; do not run migrations/reseal it by copying these instructions.

## Configure once after onboarding

Keep the original initialization file and first-day consumer opening in a private onboarding directory. Create `binding.json` from its reviewed template with the actual initialization UUID, source/configuration digests, exact original opening SHA256, native intake schema, explicit report policy/horizons, first-day report opening and validation flags. Relative `opening_file` and `consumer_opening_file` references stay inside this directory and carry SHA256 checksums. Never insert calculated outputs or approval requests into this binding. Changing a binding while a day is pending is refused.

The developer helper `tools/create_daily_csv_example.py` converts the retained **raw** starter pack to two dated CSV batches and a binding template. It performs no calculation and is excluded from production images. For local examples only, run it with host Python from the clone:

```powershell
python -m tools.create_daily_csv_example --output C:/VectorFLOW-input/csv-example
```

Alternatively invoke the same repository helper through the already built MTA image:

```powershell
$ExampleParent = (New-Item -ItemType Directory -Force C:/VectorFLOW-input).FullName
$Helper = (Resolve-Path ./tools/create_daily_csv_example.py).Path
$RawZip = (Resolve-Path ./examples/starter-data/vectorflow-starter-inputs-v1.zip).Path
docker compose run --rm --no-deps -v "${Helper}:/helper.py:ro" -v "${RawZip}:/starter.zip:ro" -v "${ExampleParent}:/examples" mta-install /helper.py --source /starter.zip --output /examples/csv-example
if ($LASTEXITCODE -ne 0) { throw 'Example conversion failed; preserve the directory' }
```

This mounts the helper and raw ZIP read-only and its new parent output directory read-write; an existing destination is refused. Python is not a host prerequisite for installation or routine daily processing. The example contains18/19October2026 raw facts, not a general production-data generator. Do not change their dates to fabricate further days.

After native initialization, copy `binding-template.json` to `binding.json` and set `initialization_id` and `source_digest` from the initialization receipt. All other template values bind the same retained originals/configuration; verify rather than replacing hashes. Retain `initialization.json`, `consumer-opening.json`, `permissions.json` and the receipt. Configure the same permissions/source digest for the MTA service before preparation, using existing onboarding instructions. Permissions catalogue files do not grant a user access.

Add three absolute private host paths to `.env`:

```dotenv
VF_DAILY_INPUT_DIR=C:/VectorFLOW-input/csv-example
VF_DAILY_BINDING_FILE=C:/VectorFLOW-input/csv-example/binding.json
VF_DAILY_STATE_DIR=C:/VectorFLOW-private/daily-operations
MTA_SELECTION_FILE=/var/lib/vectorflow/selection.json
```

Use a state directory private to this deployment. Its exclusive host lock complements the database initialization lock. The optional Compose `daily` service uses the same MTA image and the existing trusted **installer CLI** credential already used for manual `run_production_day`; it has no listener and is never started by normal `compose up`. Keep this credential private. The serving runtime does not gain calculation, metadata-write or schema privileges. The worker inherits only the configured presentation/source settings and read-only access files; its own selection variables are cleared to avoid loading yesterday's generation. It writes only the owned MTA volume and receipts. No Docker socket is mounted.

## Hand over a complete batch

The supplier writes `<INPUT_DIR>/<YYYY-MM-DD>/` and adds an empty `READY` file **last**. It must not edit files after declaring completion. Every batch contains `batch.json`, all explicitly PRESENT files, and no undeclared files. Empty populations still have a header-only CSV; absence is never inferred as empty. Only the supported `OrderFeed.csv` may explicitly say `MISSING`.

`batch.json` has exactly `schema` (`vectorflow-daily-csv-v1`), nonempty `batch_id`, `business_date` and `feeds` (each required filename mapped to `PRESENT` or the supported `MISSING`). `csv-schema.json` from the helper, or `process_daily_csv schema --binding ...`, supplies the complete ordered column/type/null/width contract for the chosen native intake mode.

The native active-NMS v1 roster is `DailyDataRaw.csv`, `MasterDataRawNonNMS.csv`, `NoNormMasterRaw.csv`, `AcceptedNorms.csv`, `OrderData.csv`, `OrderFeed.csv`, `DistributorTransactions.csv`, `VendorTransactions.csv`, `InTransitRaw.csv` and `Transporters.csv`. Native v2 additionally requires `MasterDataRaw.csv`, `SOBDataRaw.csv`, `MOQDataRaw1.csv` and `MOQDataRaw2.csv`. V1 current masters/supplier controls and approval queues retain their database owners; CSV cannot replace them. Use only the intake mode supported by the initialized configuration.

CSV is UTF-8 (optional initial BOM), comma-separated, LF or CRLF, ordinary quoted fields including embedded commas/newlines. Headers must match the published names **and order**. `\N` means NULL; empty text stays empty text. Codes stay text, including leading zeros. Integer ranges, exact decimal precision/scale, finite floats, text widths, dates and timestamp timezone rules are validated; no trimming, deduplication, guessed defaults, numeric-to-NULL repair or column reordering occurs. Record/physical-line mappings preserve duplicate occurrence order. Native business cleaning and rejection/carry-forward rules remain unchanged after format validation.

## One operation, manually or scheduled

Run in the deployment directory with the same `.env`/Compose configuration used to start it:

```powershell
pwsh -NoProfile -File ./release/run_daily.ps1 -BusinessDate 2026-10-18
```

The normal operation freezes original files, validates CSV and native prerequisites, uses its own immediate persisted predecessor, stops **only MTA**, executes the native day once, prepares the existing full report roster/Planning/guided aggregates and native input download, validates admission, atomically selects that generation, restarts only MTA and verifies the actual process admitted the exact run/output before recording PUBLISHED. It does not rewrite report algorithms or load calculated fixtures. Auth, frontend, MTO, Redis and PostgreSQL remain running. The first day uses the initialized opening; later days use their own prior successful output. No manual predecessor UUID is required.

Optional `-InspectOnly` performs a read-only CSV/native preflight without reservation, snapshot or execution. It requires the owned Pick output directory to exist (normal staging creates it automatically). A first inspection may therefore report this genuine prerequisite; normal processing still validates before stopping MTA. Inspect is not a substitute for execution or publication.

For the retained successor, place its completed batch and run the SAME command with `-BusinessDate 2026-10-19`. Repeating identical published input returns the original receipt and performs no calculation/selection/restart; it does not select an older day over a newer one. Changed input for an already committed date is refused. A manual/scheduled invocation uses exactly this entry point. Windows Task Scheduler can execute `pwsh -NoProfile -File <absolute-clone>/release/run_daily.ps1 -BusinessDate <explicit-business-date>` with its **Start in** set to the deployment directory. The upstream scheduler must supply the business date; do not guess today's civil date for historical/delayed business feeds. No Celery beat/cron service is installed by this feature.

## Diagnose and resume safely

Format/native preflight rejection happens before stopping serving or creating a calculation. Durable MTA attempt directories hold original files/checksums, generated native input, record-line mappings, preflight, validation/business rejection CSVs, phase log, selection candidate and result. Malformed batch declarations without a usable identity receive a separate rejected intake receipt. The host state directory holds operation receipts and command output; it never retains its temporary resolved Compose configuration containing private settings. Keep both with the database/volume backup.

Native rules may reject rows or carry prior values while completing the day. These are reported as actual business rejections, not automatically waived or turned into format errors. A genuine failed native run is retained and never automatically retried/replayed/reset. Diagnose it before authorizing a corrected attempt. Unfinished attempts block later dates.

If calculation committed but preparation/startup failed, preserve everything, resolve the exact problem and explicitly resume:

```powershell
pwsh -NoProfile -File ./release/run_daily.ps1 -BusinessDate 2026-10-18 -Resume
```

Resume uses the linked SUCCEEDED run and existing READY layers; it does **not** calculate the day again. Preserved input archives must validate byte-for-byte; an existing corrupt/partial archive is refused, never overwritten. A preparation failure remains pending until all layers pass. Selection/startup recovery uses the same complete generation. After entering calculation, MTA stays in maintenance on failure: copying yesterday's selection cannot undo current master/queue/history changes. Do not restart an old generation as a claimed data rollback. Full rollback/recovery requires the matched cold database/files/configuration/secret backup documented in the existing operations runbook.

The final receipt establishes ingestion, native output, preparation and actual MTA serving separately. Original authenticated UI acceptance, scope coverage and production-volume performance are distinct checks; a PUBLISHED receipt is not an automatic claim that every user/workflow or dataset size was tested.
