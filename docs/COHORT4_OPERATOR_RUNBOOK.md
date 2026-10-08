# Cohort4 operator runbook

Cohort5 adds a separately approved operational admission path; see
[COHORT5_OPERATOR_RUNBOOK.md](COHORT5_OPERATOR_RUNBOOK.md). This Cohort4 document
retains its historical strict-path evidence. Do not use its separate activation
step for the new atomic operational receipt/access path. New runs and serving
changes remain held.

**Execute steps 1–5, in order, then stop.** These are the delivered audit steps.
They do not calculate, restore, prepare, activate or start a service. Copy only
the commands inside each block, without the Markdown fence lines. No elevated
PowerShell session is required. A thrown error means stop and retain the output.

## Delivered audit: execute now

1. Open PowerShell and select the retained delivery.

```powershell
Set-Location F:/freshvcf
$ErrorActionPreference = 'Stop'
$c4Index = Get-Content docs/COHORT4_EVIDENCE_INDEX.json -Raw | ConvertFrom-Json
if ($c4Index.disposition -ne 'QUALIFIED_OPERATIONAL_PACKAGING') { throw 'Wrong delivery' }
$c4Root = $c4Index.evidence_root
```

2. Verify the package archive and every indexed proof file. This reads files only.

```powershell
foreach ($c4File in $c4Index.files.PSObject.Properties) {
    $c4Path = Join-Path $c4Root $c4File.Name
    $c4Hash = (Get-FileHash -LiteralPath $c4Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($c4Hash -ne $c4File.Value) { throw "Evidence mismatch: $($c4File.Name)" }
}
Write-Output "Verified $($c4Index.files.PSObject.Properties.Name.Count) Cohort4 files"
```

3. Verify the installed immutable image and the completed command audit.

```powershell
$c4Image = docker image inspect --format '{{.Id}}' freshvcf-cohort4:operational-004
if ($LASTEXITCODE -ne 0 -or $c4Image -ne $c4Index.image) { throw 'Runtime image mismatch' }
$c4Audit = Get-Content (Join-Path $c4Root 'command-audit.json') -Raw | ConvertFrom-Json
if (-not $c4Audit.passed -or $c4Audit.checks.Count -ne 11) { throw 'Incomplete command proof' }
if (@($c4Audit.checks | Where-Object { -not $_.passed }).Count -ne 0) { throw 'Command proof failed' }
$c4Denied = @($c4Audit.checks | Where-Object name -eq 'strict-selection-denial')
if ($c4Denied.Count -ne 1 -or $c4Denied[0].exit_code -ne 1) { throw 'Strict admission changed' }
Write-Output 'Package checked; qualified owner remains denied by strict selection'
```

4. Read `docs/COHORT4_HANDOFF.md`, especially its readiness matrix. Record this
result as **qualified operational packaging**, never production-ready or full
legacy parity. The two Cohort3 consumer receipts remain FAILED with their two
approved 503 routes. The original Cohort1/2 qualifications also remain.

5. Stop. Do not execute any commands in the held procedures below. There is no
automatic next date, benchmark, publication, restore or service cutover.

## Commands already executed for this delivery — reference, do not repeat

The private compose is
`D:/freshvcf-build/evidence/cohort4-20261009-001/compose.private.json`.
It was rendered from `packaging/cohort4/compose.template.yaml` using existing
owned credentials/mounts. It contains secrets and must never enter Git or a
support attachment. It has no ports, no restart, 4 GiB/two CPUs, read-only mounts
and root filesystem, and blank consumption policy/selection with actions off.
The image entrypoint is `python -m django`; **do not append manage.py**.

The audit ran `docker compose -f PRIVATE_COMPOSE run --rm --no-deps worker`
with each following argument list exactly once:

| Arguments | Required result / recorded proof |
|---|---|
| `check` | Exit0, `django-check.log` |
| `makemigrations --check --dry-run` | Exit0/no changes, `migration-drift.log` |
| `migrate --plan` | Exit0/no planned operations, `migration-plan.log`; no migration executed |
| Each of `run_daily`, `cohort2_operational`, `prepare_daily_ui`, `activate_daily_ui`, `check_daily_selection`, `install_daily_input_source`, followed by `--help` | Six exit0 parser checks, corresponding `*-help.log` |
| `cohort2_operational check --attempt 2a6dbb31-3d1a-4f7b-aa55-6f710f85fc7d` | Exit0/SUCCEEDED, `operations-check.log`; reads existing rows/files/backup receipts, no new backup or restore |
| `check_daily_selection --run-id 1b83fdca-d0ad-47d5-8694-414257ae68be --output-digest 24cb05541ac807ac8c5c4afbc8e4c5c27c1d5023d2fd4fcc67be05b734fab1d3` | **Expected exit1**, `strict-selection-denial.log`: independently accepted calculation required. This is not an instruction to retry or waive admission. |

## New-day execution — BLOCKED; do not execute

The current template is an audit configuration with retained sources mounted
read-only. It does not supply a writable production output root, an arbitrary
MDM installer, general input bindings, or a general admission waiver.

The release owner must first approve one frozen input/configuration/MDM and
opening-or-predecessor/action package, enabled workflow scope, exclusive resource
ownership, finite date count, output paths and acceptance contract. Admission
must use independent parity or a separately approved and implemented general
policy. Do not extend the two-owner Cohort3 exception.

After that separate release, its operator executes these gates sequentially
using the exact arguments in `COHORT4_COMMAND_CONTRACT.md`:

1. Verify input SHA, configuration/tool pins, MDM binding and owned predecessor
   plus real action chain. Stop on a missing owner; never default an absent input
   to empty. Installation is limited to the registered synthetic input domain.
2. Invoke `run_daily` once for the authorized index. Retain run UUID, date,
   revision and all input/output/action digests. Stop unless SUCCEEDED. Never
   recalculate an accepted owner or copy another engine's state.
3. Invoke `cohort2_operational materialize --request` with the released request;
   then `cohort2_operational check --attempt` on its returned UUID. Stop unless
   both succeed; retain operational lineage and native flag0 where applicable.
4. Invoke `prepare_daily_ui` for the exact run/output. Stop unless READY, and
   retain its publication seal. Missing consumer sources remain unavailable.
5. Invoke `activate_daily_ui` with the exact run/output/seal. This binds access
   but does not select. Invoke `check_daily_selection`; stop on any nonzero exit.
6. Only the separately authorized serving owner may install the coherent checked
   run/digest/BTR-generation tuple and restart its owned service. Require startup
   admission and scoped reader checks; preserve the prior valid selection on
   failure. Cohort4 authorizes none of these serving actions.

## Failure, retry and restore procedure — held until an exact request is released

On any unexpected failure: **stop the chain, retain the failed receipt/log and
original request, keep the last valid serving tuple, and report the first failed
gate.** Do not reset the database, edit a success receipt, rerun calculation,
overwrite files, or use a different owner to conceal the failure.

| Observed boundary | Required existing procedure after explicit release |
|---|---|
| Failed/interrupted operational attempt | Create a new request/key/root bound to the same committed calculation/config/output and explicit `retry_of_id`; include `interrupted_attempt_id` only for the exact interrupted owner. Use `cohort2_operational recover --request`. Existing worker lease/lineage checks govern, then run `check`. No calculation. |
| Missing supported files from a successful attempt | New request with `repair_of_id` and exact `repair_file_ids`, original sources, no new `openings`/`abort_opening`. Use `recover`, then `check`. Retain original and replacement receipts. Exact surviving copies are preferred; only approved mapped ZIPs have qualified member/content regeneration. |
| Backup or restore mismatch | Stop. Preserve dump, hashes, source/restored images and original failure. Existing owned PG logical restore allows only the eleven approved CHECK-cast pairs; all rows/sequences/other metadata stay exact. SQL full/differential methods belong to separately owned SQL fixtures. No generic environment restore command is released by this package. |
| Process restart or admission failure | The CLI worker is disposable/restart=no. Do not start a web service from it. Later serving restart must re-admit the same checked tuple; existing Cohort3 restart/denied-candidate receipts are proof only for its two owners. |

These procedures reuse `COHORT2_HANDOFF.md` recovery/restore evidence and
`COHORT3_HANDOFF.md` admission evidence. They do not authorize another recovery
campaign. New deployment credentials, email delivery and backup destinations
require their own named owners; none are invented here.

## Package reproduction — reference, not an audit step

The exported `runtime-image.tar` is hash-pinned in the evidence index. The pinned
local bases and retained Git commit in `packaging/cohort4/runtime-lock.json` are
required to rebuild; this is not a claim of a clean Internet dependency build.
`build.py --output NEW_EXTERNAL_DIRECTORY --tag freshvcf-cohort4:NEW_TAG` verifies
both bases and 848 source files, builds offline from them and audits real imports
and PostgreSQL tool startup. Its output directory must be new; preserve failed
attempts. `private.env.example` has no credentials. Copy it outside Git and supply
only explicitly owned values when a later release requires configuration.
