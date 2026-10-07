# Offline temporal validation

Integrated implementation: `8e1569d`, pushed on
`codex/btr-ready-snapshot-trial`. Frozen scenario checkpoint: `9c2218d`.

This package uses the approved 1,240-pair catalogue and one shared June6–26,2026
execution horizon. Every pair has 21 daily inputs. The ten-pair acceptance trial
uses June6–8 from its separately registered 21-day subset. Input generation is
complete; input validity does not establish calculation or report parity.

The status and trial acceptance live in `docs/MIGRATION.md`. Preserve the
original12-day artifact, accepted F2 receipts, accepted3006 smoke, failed history
attempts and3005. Full execution is a subsequent human-operated action; this
implementation task runs only the small trial.

The retained trial passed93 comparisons across June6–8, separate daily RRR
source proofs and terminal typed readback. All18 prepared layers reached READY.
Broad-account browser verification covered BPR and shipment drill-down, both BTR
inventory views, empty current DBM suggestions, empty RRR and empty RRR colour-band.
The colour-band menu click did not navigate; its documented direct route did.
The original3006 selection was restored and checked ready, with protected services
unchanged against the explicitly approved external-recovery baseline.

## Local requirements

Run PowerShell in `F:/freshvcf`. Python is
`D:/freshvcf-build/venv/Scripts/python.exe`. Docker Desktop and the existing
owned `freshvcf-daily3006` stack must be available. The local SQL instance needs
the existing Windows-authenticated oracle provisioning access and healthy
storage. Credentials stay in the existing external3006 private configuration;
the scripts do not reset passwords or import secrets into Git.

The candidate is `freshvcf-daily3006-mta:offline-temporal-003`. Preflight resolves
the verified image ID
`sha256:0408073029940316a695ff4384cacaace211269500fbd4a90c6e0963018abfe2`;
the tag is retained for the commands below. Preflight resolves
its immutable image ID and compares all runtime Python and governing JSON bytes
inside that image against the checkout. Input, catalogue, generator dependencies,
ledger, resource limits, SQL lease/storage, PostgreSQL health and storage reserve
must pass. A tag or running SQL process alone is insufficient.

```powershell
./tools/Test-TemporalValidationPreflight.ps1 -ExecutionId temporal-smoke-001 -Scenario trial
./tools/Invoke-TemporalValidation.ps1 -ExecutionId temporal-smoke-001 -Scenario trial -Mode combined
./tools/Get-TemporalValidationSummary.ps1 -ExecutionId temporal-smoke-001
```

The retained `temporal-smoke-001` execution already exists. Use its `-Resume`
command below to verify/reuse it; the initial command above deliberately refuses
to overwrite that owner. Do not generate a new ID merely to rerun accepted days.

After the package is accepted, the human-operated full command is:

```powershell
./tools/Test-TemporalValidationPreflight.ps1 -ExecutionId temporal-full-001 -Scenario full
./tools/Invoke-TemporalValidation.ps1 -ExecutionId temporal-full-001 -Scenario full -Mode combined
./tools/Get-TemporalValidationSummary.ps1 -ExecutionId temporal-full-001
```

The full command has not been executed by this implementation task. It runs one
new day per worker, sequentially, stopping at the first failure. Each engine uses
its own persisted predecessor and own suggestions for the approved eligible-Sleep
policy. All31 comparisons and independent RRR source checks precede the next day.
Missing day-one Sleep targets are explicitly unexercised; they are never invented.

## Resume and independent modes

```powershell
./tools/Invoke-TemporalValidation.ps1 -ExecutionId temporal-smoke-001 -Scenario trial -Mode combined -Resume
./tools/Invoke-TemporalValidation.ps1 -ExecutionId temporal-full-001 -Scenario full -Mode combined -Resume
```

Resume requires unchanged image, code, inputs, action policy, source owner and
serving configuration. A successful modern day is reused after a legacy failure.
Attempts and accepted receipts are immutable. Resolve a failure before resuming;
never use a new execution ID to hide a divergence or force the same accepted day
through a different contract. Interrupted RUNNING attempts need ownership and
committed-state reconciliation before retry; do not blindly restart them.

The retained smoke trial includes explicitly approved host-runner transitions
and a start-time-only external-recovery qualification. Their immutable receipts
remain beside the original `package.json` and protected snapshot. These receipts
are specific to that trial; other changed sources are still rejected. A new full
execution freezes the delivered runner directly and needs no trial transition.

For separately operated engines, use the same new execution ID and scenario with
`-Mode modern-only`, then `-Mode legacy-only -Resume`, then
`-Mode compare-retained -Resume`. Reverse engine order is also supported. Those
captures remain unaccepted until comparison and source proofs pass. No mode copies
modern state or action choices into legacy.

Modern workers use one4GiB/two-CPU Docker process per day. Predecessor verification
runs in a child under that same bound after unused input is released. Legacy
Python workers enter a Windows job limited to4GiB and two permitted CPUs before
task code starts. The existing SQL service and protected services are unchanged.

## Terminal publication

Calculation, parity, preparation and selection are distinct states. Daily typed
state, histories and canonical sources persist throughout; expensive prepared
presentation layers are built only for the complete accepted terminal prefix.

```powershell
./tools/Publish-TemporalValidationTerminal.ps1 -ExecutionId temporal-full-001
```

That explicit command verifies every accepted day/source, prepares all required
layers, seals, binds the exact retained access/hierarchy, admits Planning/RRR and
checks selection before changing only owned3006's MTA image/configuration. A
partial prefix cannot be selected. Preparation failure preserves serving state;
selection/readiness failure restores the prior tuple.

The retained preparation coordinator can initially report missing RRR projection
dependencies for two Expedite layers, then create that prerequisite later in the
same attempt. Inspect the layer receipt before retrying the same publication
command. Its existing retry path verifies and reuses successful layers; it does
not recalculate days or discard failed attempts. This ordering limitation was
observed and the retry verified in the three-day trial.

The acceptance trial uses the same command and then restores its prior selection:

```powershell
./tools/Publish-TemporalValidationTerminal.ps1 -ExecutionId temporal-smoke-001
./tools/Publish-TemporalValidationTerminal.ps1 -ExecutionId temporal-smoke-001 -RestorePrevious
```

Verify the finite terminal UI journey between these commands. Restoration checks
that the selected config has not been changed by another operator before replacing
it. Neither command cuts over3004 or changes the3005 big-data demo.

Startup readiness waits at most180seconds. Repeating the same terminal selection
preserves its identical selection receipt; a different existing tuple is rejected
before changing serving configuration. Restoration has its own immutable receipt,
and the summary distinguishes restored state from a currently selected terminal.

## Evidence and limitations

Each execution is under
`D:/freshvcf-build/daily-3006/runtime/offline-<ExecutionId>`. `package.json` pins
source/input/image/configuration. `modern-*` holds execution metadata and compressed
archives; `legacy-*` holds independently captured closing state; `compare-*` holds
all comparison differences, RRR proof and parity attachment. Failed attempts stay
beside later attempts. `summary-*.json` and Markdown reports distinguish computed,
accepted and selected states. Early invocation failures have separate durable
reports under `D:/freshvcf-build/evidence/offline-runner-failures`.

RRR's MTO=0 producer invocation is the approved synthetic gate exception, not
canonical gating parity. BOR/BOROA and Guided Excess rolling history remain
deferred. Retained GIT SQL207, native ordering and custom report limitations remain.
Empty orders/advance populations do not prove positive order workflows. Trial
completion does not establish full-population memory/performance, MTO integration,
whole-application acceptance or production cutover readiness.

Final focused suite:31 tests PASS; baseline387resources unchanged. Additive
PostgreSQL migrations0074/0075 and a fresh75-migration database were verified.
The whole suite is not green:6 failures and19 errors reproduce in the untouched
baseline by failing test name. See `unit-baseline-comparison-001.json` rather than
interpreting focused success as whole-repository acceptance.
