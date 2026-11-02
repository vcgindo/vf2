# Upgrade an existing MTA installation

Use [vf.ps1](../vf.ps1) for a compatible MTA patch on an already initialized, populated installation. Windows PowerShell 5.1 and PowerShell 7 are supported. Docker Desktop and the existing Compose project must be available, with MTA and the unchanged frontend/auth/MTO services running. Finish any active daily, calculation or action work first.

**Qualification status:** populated upgrade, own next-day execution, scoped continuation, fresh installation and failure/recovery checks have passed in isolated real Docker/PostgreSQL installations. See [qualification and limits](UPGRADE_QUALIFICATION.md).

## Prepare the update

Update the application's tracked source to the supplied release in the existing installation folder. Preserve the installation's private `.env`, secrets, input packs, bindings, operations/journals, selected publication and Docker volumes. Keep the supplied Git metadata for a source build and use an unchanged tracked checkout. Do not copy a sample `.env` over the installed configuration or run installation/initialization again.

Backups stay outside the source folder. If operations storage is inside it, the command automatically chooses a sibling `<project>-backups` folder. Use `-BackupDirectory` only when another backup location is required. The database uses a physical PostgreSQL cluster backup: the deployment must own that dedicated cluster and meet its existing replication/WAL and tablespace prerequisites. A prerequisite failure stops the upgrade; it does not switch to a logical dump or change PostgreSQL settings.

Open a normal PowerShell window in the installation folder. Keep Compose settings in the existing `.env`; do not set shell-level Compose file/path overrides.

### 1. Check the existing source

The examples use the existing installation at `D:\VectorFLOW`. Run each block separately and stop on any error. Do not use `git reset --hard`, `git clean`, reinstall or initialize to resolve an upgrade error.

```powershell
$ErrorActionPreference = 'Stop'
Set-Location 'D:\VectorFLOW'

git diff --quiet HEAD --
if ($LASTEXITCODE -ne 0) {
    throw 'Preserve and resolve local tracked-source changes before upgrading'
}
```

### 2A. Update from a supplied local repository

Copy the supplied repository, including its hidden `.git` folder, to a separate folder such as `D:\VectorFLOW-update`. Keep it separate from the existing installation; do not overwrite the installation's private files with those from another machine. Then run:

```powershell
if (-not (Test-Path -LiteralPath 'D:\VectorFLOW-update\.git' -PathType Container)) {
    throw 'The supplied update must include its Git metadata'
}

git fetch --no-tags 'D:\VectorFLOW-update' HEAD
if ($LASTEXITCODE -ne 0) { throw 'Loading the supplied source update failed' }

git switch --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Switching to the supplied release failed' }
```

Git updates the tracked application files while preserving the existing untracked/ignored `.env`, data, bindings, secrets and operation receipts. Docker volumes are unaffected. Continue to **Upgrade** below.

### 2B. Update from Git remote `origin`

Use this alternative instead of 2A. The installation's `origin` must point to the repository supplied by the release owner. If no `origin` exists, configure it once with the actual repository URL:

```powershell
git remote add origin '<repository-url>'
if ($LASTEXITCODE -ne 0) { throw 'Configuring origin failed' }
```

Skip that block if `origin` is already configured; do not replace an existing remote blindly. Fetch the approved release branch or tag. The branch below contains the routine-upgrade implementation; use the release owner's approved reference for future updates.

```powershell
$ReleaseRef = 'codex/production-upgrade-simplification'
git fetch --no-tags origin $ReleaseRef
if ($LASTEXITCODE -ne 0) { throw 'Fetching the approved release failed' }

git switch --detach FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw 'Switching to the approved release failed' }
```

Both alternatives select the supplied commit without merging unrelated histories. A detached HEAD is intentional for this deployment. Git only updates source: **the upgrade command below is still required** to deploy it and perform the database/readiness checks.

## Upgrade

Choose one target. Build the updated source:

```powershell
.\vf.ps1 upgrade -Build
```

Or use the supplied MTA image, already loaded or pulled locally:

```powershell
.\vf.ps1 upgrade -Image 'supplied-mta-image:release-tag'
```

Use the image reference provided with the release. No manually entered hashes, initialization IDs, SQL or Compose overrides are required. To choose a different backup location, add `-BackupDirectory 'E:\VectorFLOW-backups'` to the first command.

The command checks, backs up and upgrades the installation. To preview the checks while MTA remains active, optionally add `-InspectOnly` to the chosen command. With `-Build`, this also builds the target under a unique tag, retaining the current image for recovery. The preview saves an upgrade journal; continue that same operation with:

```powershell
.\vf.ps1 upgrade -Resume
```

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
