# CSV starter: three operator commands

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

After blank installation steps1–4, use this path instead of the JSON starter steps. Run from your clone in Windows PowerShell5.1 (the default Windows shell) or PowerShell7. No shell upgrade is needed. The repository launcher calls Docker internally and handles the required MTA lifecycle; application containers are not given Docker-daemon access. Frontend, MTO, auth and PostgreSQL stay unchanged.

Run one command at a time. Wait for its success before entering the next; stop at any error. After initialization succeeds, never repeat `csv-init` to recover a daily-run failure.

## 5. Choose the CSV pack once

For an existing CSV pack, set only its absolute path in your ignored `.env`:

```dotenv
VF_CSV_INPUT_DIR=I:/VectorFLOW-input/starter-csv-complete-20261019
```

For a new copy of the repository's optional RAW starter sample instead, this command creates the pack outside Git and configures that path automatically. It does not load the database:

```powershell
.\vf.ps1 csv-sample
```

An existing pack is never overwritten. A pack with `binding.json` belongs to its recorded database; do not reuse it for a different blank installation. With unset CSV/state paths, `csv-sample` chooses an unused pack and its own receipt directory automatically. If you explicitly configured old paths in `.env`, choose new `VF_CSV_INPUT_DIR` and `VF_DAILY_STATE_DIR` values for the new installation. Deleting containers or cloning Git does not delete external packs/receipts. Source images built before this launcher need `git pull --ff-only` and `docker compose build mta` ONCE while MTA is still unregistered/blank. Do not rebuild frontend/MTO or reinstall. A fresh build from this revision already includes the required commands.

## 6. Load CSV masters/opening once

```powershell
.\vf.ps1 csv-init
```

The command validates the entire CSV pack before stopping MTA, registers the fresh namespace, invokes the existing atomic initializer, completes all13 native MDM families from that same opening, and records the actual receipt. It writes the daily binding/access configuration, preserves existing `.env`/Compose settings and restarts MTA with initialized master-data access. Calculated reports become available after day1 publishes. No UUID, hash, JSON file or report policy is entered manually. Other services remain running; registration/initialization are never silently repeated.

## 7. Execute day1 through selected UI reports

```powershell
.\vf.ps1 csv-day 2026-10-18
```

Expect `PUBLISHED`,18October and the actual run/output IDs. CSV intake, validation, calculation, existing report preparation, selection, MTA restart and serving verification happen internally. MTA is in maintenance during execution/publication and returns automatically after success. Administrator login also depends on its permission catalogue and may return503 during that window; wait for `PUBLISHED` before signing in.

## 8. Execute day2 using its own persisted predecessor

```powershell
.\vf.ps1 csv-day 2026-10-19
```

Expect `PUBLISHED` and19October. No predecessor ID is copied. Refresh your normal administrator session, then open BPR → Show All, Planning → category → Grid View, RRR and DBM. Ordinary users still require their explicit roles/scopes. Do not repeat initialization or edit dates to create future days.

The unchanged sample contains200SKU/20location definitions,12active master pairs, opening17October,16daily records/date and10CSV feeds/date. Many of its165explicit opening/configuration/carry populations are legitimately empty header-only CSVs. Empty DBM/Pick populations are not positive scenario proof or a capacity test. Business rows are CSV; JSON control/checksum/receipt/provenance files are generated internally. The generated native-opening artifact supports existing archive/binding provenance, not manual JSON ingestion.

## Failure handling

Stop at the first error; preserve its named receipt. A CSV-format failure before registration can be corrected and submitted again, retaining the rejection. Registration/initialization failures preserve the checkpoint and refuse blind repeats or reset. If initialization committed but MDM completion/configuration/serving did not finish, run `./vf.ps1 csv-init -Resume`. This verifies the live database, namespace, opening and input against its receipt, completes the existing MDM bootstrap and restores initialized master access. It never reloads/registers/reseals, and refuses once any daily run/input capture exists. A receipt from another installation is rejected before stopping MTA; retain it and select the matching state directory. This is not daily-run recovery. A committed daily preparation/serving failure may be resumed after its cause is resolved:

```powershell
.\vf.ps1 csv-day 2026-10-18 -Resume
```

Resume never recalculates an accepted day. A genuinely failed calculation requires diagnosis; no automatic business retry. Existing fully published dates are not replayed. For the latest still-selected published date, `-Resume` also recovers a stopped MTA and verifies serving; it checks the selected identity first and refuses to switch back to an older date. Keep `.env`, the entire CSV pack, generated binding/access files, receipts and daily state with matched database/files/secrets backups. See [CSV_DAILY_RUN.md](CSV_DAILY_RUN.md) for the detailed CSV schema and diagnostics, not extra routine commands.

The final serving check is a read-only repository operator executed inside MTA. It loads the container's own image identity and verifies admission, selected run and readiness before recording `PUBLISHED`. A verifier-only correction can be used without rebuilding or modifying an already initialized image; it cannot bypass native admission or change calculations.

This lifecycle repair is host orchestration only. An already initialized installation can pull these launcher changes and use its existing source-bound MTA image; do not rebuild/reinstall that database to apply the repair. Publication selection is configured only after the first native selection succeeds, and persists for subsequent restarts. Missing/corrupt publication after a daily run remains an error.
