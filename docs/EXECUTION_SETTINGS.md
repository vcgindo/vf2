# Execution settings

Execution settings give operators one typed catalogue and one supported command
for inspecting the controls used by this installation. Existing calculations,
settings conversion rules, duplicate-row rules and runtime state owners remain
unchanged.

## Operator commands

Run these commands in the installation directory using Windows PowerShell 5.1
or PowerShell 7:

```powershell
.\vf.ps1 settings
.\vf.ps1 settings -OnDate 2026-04-10
.\vf.ps1 settings -Export 'D:\Transfer\settings.csv'
```

The default date is the installation's next business date, derived from its own
accepted closing or initialized opening. It is not the computer's calendar date.
The display separates the effective revision from future scheduled revisions.

To change a qualified control, export the current revision, edit only its
`Value` cell, and apply the complete file:

```powershell
.\vf.ps1 settings -Apply 'D:\Transfer\settings.csv' `
    -EffectiveDate 2026-04-10 -Reason 'Enable existing automatic DBM acceptance'
```

The file includes its version, revision, exact types, occurrence numbers and
control definitions. Keep those columns and every row. An old export, foreign
installation, missing row, invalid value or locked control is refused atomically.
Use a new filename for each export. The destination directory must already exist.

Apply only to an unadmitted future business date after current daily/scoped work
has finished. Once a run captures its settings, its continuation and recovery
retain that version. Applying the same file again after a lost response identifies
the exact already-applied revision without creating another change.

## What can change in Part 1

| Classification | Behavior |
|---|---|
| Editable supported control | `AutoDBMActive`, under `delivery/batch`, accepts integer `0` or `1`. It selects the existing automatic DBM acceptance behavior for an eligible future run. |
| Fixed profile control | The supplied initialized value is adopted exactly. Source mode, environment, phase and other locked controls cannot be enabled through a CSV edit. |
| Fixed Importer/DBM control | The exact present setting rows are adopted, including their types, NULLs, order and duplicate occurrences. Existing consumers receive the same row shapes through compatibility projections. Activation changes remain locked. |
| Existing-owner reference | Operational settings, MDM task-status configuration, report registration and scope policy remain with their existing owners and are shown as read-only references. |
| Runtime state | Completion markers, queues, accepted Norms, actions, suspensions, histories and calculated outputs remain runtime state. They are not editable management settings. |
| Unsupported scenario | Visibility of a setting does not implement its alternate workflow. Those behavioral changes belong to Part 2 and remain on hold. |

Fixed outside-profile controls include `NMSActive`, `DBMActive`,
`TaskStatusLogHorizon`, `FNC_MatchMasterNorm`, `SpikeRuleHorizon`,
`SpikeRuleParCount`, `NormZeroOneRuleActive`, `DelistingofNormRuleActive`,
`DBMDelistingDataPointPercent`, `SuperDelayFactor` and first-replenishment
percentage. Their logical owner matters: similarly named Importer, DBM and
profile rows are not interchangeable.

An absent source stays absent. An empty or legitimately cleared runtime bag is
not refilled with a default. Consumers retain their original numeric casts,
COUNT predicates, NULL handling and duplicate semantics.

## Storage and ownership

| Object | Purpose |
|---|---|
| `mta.fresh_mta_executionsettingsversion` | Installation, parent, revision, effective business date, format, value/profile digests, actor, reason and commit status. |
| `mta.fresh_mta_executionsetting` | Ordered cells with path, module, parameter, source occurrence, exact scalar type, value text and VALUE/NULL/ABSENT state. |
| `mta.execution_settings_current` | Read-only view of the latest committed version. That version may be scheduled for a future date; use the operator command for date-effective selection. |

The trusted management process appends a complete version in one transaction.
Committed headers and values are immutable. The serving role can read them but
cannot insert, update, delete or truncate them. Do not update these tables with
ad hoc SQL or give installer credentials to a serving process.

Definitions and activation restrictions live in the small code-owned catalogue;
deployment values live in the versioned tables. Business parsers remain with
their existing consumers. Adding an arbitrary row does not add executable logic.

## Initialization, upgrade and history

Fresh CSV initialization adopts the supplied values after normal certification
and activation. A normal `vf.ps1 upgrade` adopts the actual current values when
upgrading a pre-feature installation. It does not replace customer settings with
sample defaults. Repeated adoption preserves existing customer revisions.

The original initialization, certificate, accepted runs, typed data and producer
identities remain unchanged. A separate settings reference identifies the
effective projection used by a new run. Existing configuration watches and
revision ownership remain enforced. Historical inputs without that reference
retain their original decoding path.

## Execution and performance

A newly admitted native operation loads its effective version and ordered cells
with one batched values query. Its locked capture rechecks the immutable header
so a concurrent edit cannot replace the inspected snapshot. Calculations use
in-memory values; there are no settings queries in SKU/location loops.

Scoped stages and failed-capture retries read their recorded immutable version,
not the current management selection. Report-only recovery reuses accepted
calculation and unaffected READY reports. Historical report requests continue to
use the selected run and prepared report owners.

Settings resolution and projection inspect only the small control catalogue.
Separate input-integrity checks still authenticate the complete mutable input
graph at their existing boundaries. Those checks must not be replaced with
object-identity caches.

## Code map

| Area | Source |
|---|---|
| Types and finite definitions | `mta/runtime/execution_setting_values.py`, `execution_setting_catalogue.py`, `execution_setting_owners.py` |
| Models, selection, atomic management | `mta/runtime/execution_setting_models.py`, `execution_settings.py` |
| Current owners and compatibility projections | `mta/runtime/execution_settings_sources.py`, `execution_setting_projection.py` |
| CSV exchange and command | `mta/runtime/execution_settings_csv.py`, `release/execution_settings_command.py`, `release/run_settings.ps1` |
| Native capture and continuation | `mta/runtime/production_daily.py`, `temporal.py`, `captured_recovery.py`, `scoped_final.py` |

Part 2 must qualify missing behavioral scenarios individually before unlocking
their selectors. Part 1 does not certify previously untested alternate paths.

See [Part 1 qualification](EXECUTION_SETTINGS_QUALIFICATION.md) for the completed
upgrade, preservation, recovery and settings-cost checks and their limits.
