# Upgrade an existing MTA installation

Use [vf.ps1](../vf.ps1) for a compatible MTA patch on an already initialized, populated installation. Windows PowerShell 5.1 and PowerShell 7 are supported. Docker Desktop and the existing Compose project must be available, with MTA and the unchanged frontend/auth/MTO services running. Finish any active daily, calculation or action work first.

**Qualification status:** the command is implemented; initial real populated-upgrade, recovery and next-day acceptance remain pending until the release owner closes them. This document does not certify production acceptance.

## Prepare the update

Update the application's tracked source to the supplied release in the existing installation folder. Preserve the installation's private `.env`, secrets, input packs, bindings, operations/journals, selected publication and Docker volumes. Keep the supplied Git metadata for a source build and use an unchanged tracked checkout. Do not copy a sample `.env` over the installed configuration or run installation/initialization again.

Backups stay outside the source folder. If operations storage is inside it, the command automatically chooses a sibling `<project>-backups` folder. Use `-BackupDirectory` only when another backup location is required. The database uses a physical PostgreSQL cluster backup: the deployment must own that dedicated cluster and meet its existing replication/WAL and tablespace prerequisites. A prerequisite failure stops the upgrade; it does not switch to a logical dump or change PostgreSQL settings.

Open a normal PowerShell window in the installation folder. Keep Compose settings in the existing `.env`; do not set shell-level Compose file/path overrides.

## Inspect, then upgrade

Choose one target. Build the updated source:

```powershell
.\vf.ps1 upgrade -Build -InspectOnly
```

Or use the supplied MTA image, already loaded or pulled locally:

```powershell
.\vf.ps1 upgrade -Image 'supplied-mta-image:release-tag' -InspectOnly
```

Use the image reference provided with the release. No manually entered hashes, initialization IDs, SQL or Compose overrides are required. To choose a different backup location, add `-BackupDirectory 'E:\VectorFLOW-backups'` to the first command.

Inspection authenticates the images and checks the existing installation, schema and selected business data while MTA remains active. With `-Build`, it also builds the target under a unique tag, retaining the current image for recovery. Inspection saves an upgrade journal. Continue that same operation with:

```powershell
.\vf.ps1 upgrade -Resume
```

To perform inspection and upgrade together, omit `-InspectOnly` from the chosen first command.

## What the command does

The command holds the existing daily-operation lock, stops only MTA for maintenance, creates and records the physical cluster backup together with the stopped MTA work files, original deployment configuration and input binding, and verifies the original installation and accepted data. A code-only patch adds no per-release database permission row. An actual schema change uses packaged forward atomic MTA Django migrations, checks existing ownership/guards and installs the required guards for new tables. Serving workers do not receive migration or registrar authority.

It then pins the MTA-related commands to the authenticated immutable image, starts MTA and checks that the actual server is ready for the same selected run and output. Frontend, auth and MTO retain their running containers/images. The upgrade does not initialize, ingest inputs, recalculate accepted days, rebuild reports or change selection to another day.

Wait for `MTA upgrade complete`. Retain the journal, diagnostics, previous image/configuration and backup. Then use the normal next business-date command with that date's genuine input batch:

```powershell
.\vf.ps1 csv-day YYYY-MM-DD
```

See the [root runbook](../RUNBOOK.md), [daily-run guide](CSV_DAILY_RUN.md) and [operations runbook](RUNBOOK.md) for normal operation.

## If an upgrade stops

Preserve its journal, logs and backup. Diagnose the reported failure, then use `upgrade -Resume` for the same target. The command reconciles actual database migration state before continuing; a failed startup does not authorize repeating accepted days. If maintenance has begun, a failure leaves MTA stopped and daily commands remain blocked until the upgrade is resolved. Do not delete the journal, reinstall or initialize to bypass it.

Rollback is a diagnosed recovery decision, not an automatic command action. Before new business work, restoring the previous image/configuration is valid only when that image supports the installed schema and persisted formats. A physical backup requires a coordinated offline restore of the dedicated PostgreSQL cluster together with its captured MTA work files and configuration, retained read-only input/access files and existing external secrets; this preserves physical database identities. It is not a per-database logical restore or an automatic rollback. After new work has been accepted, never blindly restore an older backup and discard it.

The initial qualification of this upgrade mechanism includes independent populated installations, realistic continuation and failure/recovery proofs. That initial gate is not a mandatory large three-day replay for every future patch. Each release author must supply focused evidence for the changed behavior, migration and reader compatibility, plus the relevant upgrade/readiness checks. Routine operators do not replay historical days to validate deployment.
