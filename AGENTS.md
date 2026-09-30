# Fresh VectorFLOW migration

## Mandate

Port canonical deployed MTA into Django/Python and PostgreSQL. Priority:
calculation/state parity, presentation, then complete application acceptance;
maintain a runnable connected application throughout. Retain the existing
frontend and direct-port MTO; do not redesign either business contract.

Canonical runtime: `F:/VFlow_Local/local-runtime/mta-engine` and
`F:/VFlow_Local/local-runtime/mta-latest`. Preserved counterpart:
`F:/VFlow_Source_Backup/deployed-demo/MTA`. Deployed API DLL SHA256:
`0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346`.
Actual BAT/SQL/config/deployed API govern; recovered C# is not authority unless
matched to that DLL. Hashes and retained inputs are in `baseline/manifest.json`.

NEVER repair legacy flaws, invent tie-breaks/defaults, hide incomparable fields,
replace the oracle, weaken assertions or report excluded behavior as parity.
Record source, input and affected contract in `docs/LEGACY_EXCEPTIONS.md`, then
continue independent work. A presentation exception cannot authorize a changed
calculation. Previously approved exceptions require their exact scope to transfer.

## Lean execution

Use lean-code-orchestrator. Primary owns scope, code, integration and proof;
default direct execution. Delegate only for concrete independent benefit, at most
two bounded children, no grandchildren. Preserve the user's model choice.
The ONLY status tracker is `docs/MIGRATION.md`. The source manifest/DAG is a
contract map, not a second queue. Before mutation identify active phase, unmet
exit, boundary and proof. Close or explicitly block a phase before moving on.
Implement complete business flows, then debug earliest divergence; do not create
per-script recovery programmes or repeatedly rediscover accepted provenance.
Run focused affected proofs; broaden only for relevant change or failure.
Commit/push at logical phase exits or requested checkpoints. Never infer a goal
token budget. A checkpoint or imported code is not acceptance.

## Synthetic independence

Retain the approved 200-SKU/20-location catalogue, names, hierarchy and scopes.
Reuse exact registered artifacts, separately identifying processed inputs, raw
fixtures, shallow timelines, full-depth facts, historical openings and receipts.
One artifact does not certify another boundary. No silent regeneration or
substitution. Existing receipts are evidence only after provenance reconciliation.
New shallow cases use retained identities with explicit rule-boundary overrides.
Temporal horizon is 3 times maximum RLT in the selected population. Transit time
is half RLT rounded with a declared rule, not Python's implicit banker rounding.
External daily facts are synthetic and ledger-conserving; DBM recommendations,
accepted Norms, suspension/cooling/history and next-day state are computed.
Each engine uses its own persisted predecessor. Never copy legacy outputs into
modern state or seed calculated outputs as facts. Apply/Sleep use real workflow
transitions under explicit test policy. Preserve typed values, NULLs, duplicates,
and deterministic source order. No count-only parity claims.

## Boundaries and safety

Only mutate this checkout and its explicitly owned isolated test resources.
`F:/vflow_integrated` is read-only reuse/evidence input; do not touch its dirty
work, services, databases or goal. `F:/new_vflow` remains excluded.
Protect legacy live DBs and existing 3002/3003/3004 services. No new public ports.
3004 remains the eventual delivery address; cutover requires readiness and
explicit coordination, never an automatic replacement of another task's service.
One isolated test stack, restart=no, bounded resources, no host port mapping.
No shared Docker/WSL restart, prune, database reset or volume deletion.
Fresh SQL replay must use verified unique VFTEST_Fresh_* databases and exclusive
ownership; never borrow/reset another task's VFTEST databases.
Secrets stay outside Git. Do not import .env files, live data dumps or credentials.

## Commands

Use `D:/freshvcf-build/venv/Scripts/python.exe` for local commands.
Build storage and Git objects are on D: by user authorization; source remains
in F:/freshvcf. Do not remove the Git object junction or D: backing directory.
`python -m unittest discover -s tests` is the focused repository suite.
`python tools/baseline.py verify` checks pinned source/input identity.
Fresh schema changes require Django check, makemigrations --check, migrate plan,
and migration-enabled PostgreSQL verification. Never fake migrations.
