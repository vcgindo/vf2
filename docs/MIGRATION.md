# Fresh migration — authoritative delivery tracker

## Frozen objective

Complete deployed MTA behavior, not merely DBM: input/control/order handling,
planning and rationing, ordered DBM, computed rollover, workflows, reports/API
and unchanged UI. Preserve MTO business behavior. Runtime uses Python/Django
and PostgreSQL, never SQL Server/.NET as a calculation dependency. Legacy SQL
Server remains only the independent validation oracle.

Canonical reference is the local deployed runtime, matched to its preserved
deployment. Selected settings determine enabled branches. Conditional customer
hooks and dormant features must be classified rather than silently imported or
dropped. Existing proven modern functions may be reused with explicit provenance;
old acceptance does not automatically transfer to a changed build.

## Finite logical phases

| Phase | Delivery and exit | State |
|---|---|---|
| F0 Foundation | Pinned source/config/input register; direct-port frontend/MTO/auth snapshot; runnable clean Django service; source/framework checks | COMPLETE — framework check, 3 tests, 376 resources, direct-port byte correspondence |
| F1 Current-day MTA | Input/controls/orders → requirement/rationing/PSO/advances/Pick → persisted report inputs. Full typed comparison on retained positive and sizeable artifacts; readback | COMPLETE for the selected registered contracts — evidence below; not universal branch/customer coverage |
| F2 Temporal MTA | Complete configured DBM + controls/workflows + BTR/history; independent own-state shallow then full-estate replay over 3×max RLT; required actions and next-day consequences | ACTIVE — complete connected engine implemented; retained 39-identity/12-day regression96/96, fresh and ledger-governed acceptance pending |
| F3 Application delivery | Required API/UI surfaces, navigation/scopes/actions/downloads; single-PostgreSQL deployment, fresh-start/restart/retry, MTO regression, runbook and coordinated 3004 delivery | PENDING |

Active F2 unmet exit: independently computed daily DBM/state and workflow outputs,
persisted predecessor lineage and complete shallow/full-estate temporal comparison.
Dependencies: F1 current-day pipeline verified; retained rule/temporal inputs are
registered. Permitted edits: pure DBM/state functions, the connected daily-chain
orchestrator, run persistence needed for own-state replay, and affected proofs.
Do not import the old ORM/audit hierarchy or open a per-script recovery programme.
Proof: each engine computes from its own prior state; all required boundaries and
actions compare over 3×max RLT. Keep complete API/UI acceptance in F3.

## Executable flow and ownership

```text
versioned external facts + previous OWN committed closing state
  → input validation / daily scratch reset / ordered control application
  → master/order/supplier processing
  → BPR: stock, requirements, rationing, PSO, advances, Pick
  → DBM import → suspensions → ordered rules → suggestions/reports
  → BTR/history → durable closing state
  → published read models → deployed API contracts → unchanged frontend
                          ↘ Apply/Sleep/controls → next OWN daily run
```

The diagram describes dependency order, not permission to skip a producer.
Persisted outputs, report projections and API consumers share a run identity.
Compare fixed major boundaries plus the required current-day output roster.
Stop debugging at the earliest divergence, preserving its receipt. Do not reload
legacy state into modern midway or retry by narrowing the fixture.

## Synthetic and acceptance resources

`baseline/manifest.json` is a generated immutable inventory of existing source
and artifact identities. It distinguishes raw, processed, temporal and report
inputs. The existing full artifact is reused, not regenerated as a fresh small
demo. New shallow cases explicitly select retained identities; their passing
results do not close full-population acceptance.

One physical PostgreSQL database is the target, with separate service schemas
where necessary to preserve MTO/auth migration histories. Do not force incompatible
Django migration namespaces together or rewrite MTO calculations to consolidate.

## Evidence and checkpoints

No fresh-build parity is claimed yet. See `baseline/manifest.json` for inherited
resources; inherited receipt status is not fresh execution status. The statement
above describes the F0 baseline only; F1 results below now establish bounded
current-day calculation/readback parity, not whole-MTA acceptance.
The prior checkout is pinned at `66a77735d3f3f9a9becf4c87a08ae7827900cf84`;
its uncommitted work is excluded. No service cutover is authorized by this tracker.

F0 proof (30 September2026): `manage.py check` passes; three foundation tests pass;
`tools/baseline.py verify` confirms376 pinned resources. Of2230 pinned frontend/
MTO/auth files,2227 have exact Git blob/mode correspondence. The three excluded
files are unused icon ZIP archives (`forced/excel (1).zip`, `manual/Group 473.zip`,
`manual/plus.zip`), not business code. No MTA application functions or old runtime
models were imported in F0. There are no fresh MTA migrations yet; persistence
and PostgreSQL-enabled migration checks are part of F1.

Storage: F: filled during dependency installation. User authorized D: build
storage; dependencies and Git objects now live in D:/freshvcf-build. Source stays
in the requested checkout. Existing services and source worktrees were untouched.

### F1 working calculation/persistence checkpoint

- Foundation committed/pushed: `4d5ffdb` on main.
- Extracted31 pure calculation/input dependency modules and7 projection functions
  from pinned66a7773. Removed ORM reads from those7 by passing produced rows;
  did not import the old run/audit/model hierarchy. Exact mechanical provenance:
  `baseline/calculation-reuse.json`. These functions are editable local code.
- Fresh sizeable calculation: **20/20** typed contracts pass, then **20/20** pass
  again against the actual PostgreSQL readback. Retained1240 populations and1685
  remaining-Pick rows match. The source oracle is retained, not freshly replayed;
  input logical identity and each SQL hash match both preserved and local runtime.
- Raw-source comparisons: daily/order/auxiliary stock119/119; control diagnostics
  24/24; transit tags23/23. Exact existing fixtures, no regenerated populations.
- Connected-inputs-controls receipt predates remaining-Pick capture. It remains
  **RECEIPT_INCOMPLETE** as historical evidence; see fresh replacement below.
  Neither the older receipt nor its failed comparison was overwritten.
- Fresh PostgreSQL initial migration applied;4 migration-enabled transaction
  tests pass (readback/retry, row tamper, missing output, durable failed attempt).
  Six framework/pure-input tests pass. Django reports no missing migrations.
- Evidence directories under `D:/freshvcf-build/evidence`:
  `f1-sizeable-001`, `f1-persisted-001`, `f1-persisted-comparison-001`,
  `f1-raw-001` (retained failed receipt-compatibility attempt), `f1-raw-002`.
- Durable sizeable run: `fe5fd4dd-12e5-4415-a33f-16c1434c82f6`.
  Output checksum: `1edd822a2b6167e6002d0936c7112bdbd1d81bbaa616a300fdc3406a5689bd69`.

### F1 fresh SQL / positive population verification

- Dedicated `VFTEST_Fresh_*` schema created from pinned canonical DDL, with MDF/
  LDF files exclusively under `D:/freshvcf-build/sqlserver`. Existing databases
  and serving instances untouched. Exclusive replay lease and physical-path
  guards are required; original/default/Block2 runner connections unavailable.
- `f1-fresh-sql-001`: connected-inputs-controls119, physical PSO16, stock advance15,
  GIT advance15 and Pick groups15 comparisons all PASS (180 total). Fresh SQL
  includes the previously absent remaining-Pick checkpoint. All five fixtures
  are unchanged retained inputs, not newly invented replacement baselines.
- `f1-positive-persisted-001`: the same180 comparisons all PASS on actual fresh
  PostgreSQL readback. These include nonempty PSO, stock/GIT allocation, formed
  Pick and remaining Pick. This is not temporal or API acceptance.
- Bootstrap attempts are not parity: Windows SQL Server rejected forward-slash
  MDF paths; native paths fixed this. Transactional DDL then hit an existing
  duplicate CREATE and rolled back; schema-only duplicate/absent-DROP conditions
  now match the retained provisioner's known exceptions before execution.
  Per-database schema receipts list every exception. No business SQL was changed.
- Ten focused tests pass. Next unmet F1 exit: selected GulfOil adapter proof and
  final source/persistence review; no expansion of CSV formats or other customers.

The earlier F1 working checkpoint was not closure. The final acceptance below
closes its selected current-day obligations only, not temporal DBM, raw ingestion
for the whole sizeable estate, UI acceptance or branch-wide parity. No inherited
empty output is credited as positive order/advance/formed-truck coverage.

Test-resource owner: this fresh migration task. Compose project `freshvcf-test`,
PostgreSQL data at D:/freshvcf-build/postgres,1GiB/1CPU; one-shot MTA2GiB/2CPU,
restart=no, no host ports. One-shot containers use --rm. Stop this project's
idle PostgreSQL at checkpoint/handoff; preserve its data for next invocation.

### F1 final acceptance (30 September 2026)

- Fresh sizeable SQL replay: `f1-sizeable-fresh-sql-001`, **20/20 PASS** against
  independent fresh Python execution. Exact retained200-SKU/20-location input;
  1240 selected SKU-location rows;1685 remaining-Pick rows. Final PostgreSQL
  comparison: `f1-sizeable-final-persisted`, **20/20 PASS**. This supersedes any
  suggestion that the sizeable comparison relies only on an older SQL receipt.
- Five positive/raw fixtures: fresh SQL and PostgreSQL both **180/180 PASS**;
  additional retained raw receipts166/166. Refer to exact directories above;
  counts describe contract comparisons, not percentages of the whole migration.
- Selected GulfOil: `f1-gulfoil-003`, **126/126 calculation**, **13/13 adapter-table**
  and **7/7 parser-case** comparisons PASS against retained canonical receipts.
  `f1-gulfoil-persisted-001`:126/126 PASS after fresh PostgreSQL readback, with
  original raw file bundle and generated standard-boundary lineage persisted.
  This is the retained approved five-SKU raw extension, not sizeable raw coverage.
- Parser qualification: deployed `ReadDailyDataToInterface.py` hash
  `dd94826491cc045259d02c20168de0f24c0540bc1f91b855015161bf5cf55e3f` differs
  from preserved `6b232a259f72fe55fa41aeb741f871442256593dab6bab3cd4cf1dc9026c50dd`.
  Connection certificate handling and metadata `ORDER BY MappingId` are the
  differences. All executed parser/insert functions match by AST; a read-only
  configuration query proves all83 retained mapping rows in that exact order.
  The qualification is in the successful evidence, not a waived hash assertion.
- Retained failed attempts: `f1-gulfoil-001` source discrepancy;
  `f1-gulfoil-002` SQL INT-vs-Decimal serialization and OrderID field spelling.
  Comparator now applies only declared INT conversion (rejects fractions/range
  errors), retains NULL/multiplicity/all fields, and explicitly maps OrderId.
  No calculation or synthetic input changed to obtain these passes.
- Independent review: runtime now calculates from its exact durable source
  snapshot, not the caller's mutable object. SQL calculations run under disabled
  login `freshvcf_oracle_replay`, impersonated WITH NO REVERT, with control only
  on the eight owned Fresh databases. Server privilege/live DB access are denied.
  Thread ownership and live schema fingerprints are checked before each replay.
  `f1-isolation-final.json` proves restrictions and transactional schema-drift
  detection/restoration; restricted connected replay119/119PASS is retained in
  `f1-restricted-oracle-003`. Earlier guard false-positive attempts remain.
- **14 focused tests +6 PostgreSQL transaction tests PASS**; migrations unchanged.
  No serving application, legacy business data or other test estate was modified.

Explicit remaining F3 runtime obligation: interrupted/failed-run retry currently
fails closed and preserves its record. F3 must add a bounded, evidence-preserving
restart/recovery policy. Successful-run immutable retry is verified; crash recovery
is NOT claimed. This does not change or reopen F1 calculation parity.

### F2 connected temporal checkpoint (30 September2026)

- Complete pure chain extracted from pinned66a7773: controls/master/supplier/
  orders → verified current-day calculation → BPR/BlueZone → DBM ingestion,
  suspensions, ordered selected rules and reports → BTR → closing state.
  `baseline/temporal-reuse.json` identifies49 extracted/reused records and their
  source transformations. Old ORM/run/audit hierarchy was not copied.
- `execute_day` consumes its own completed PostgreSQL predecessor and ordered
  immutable Apply/Sleep command log. Parent locking prevents late action loss
  and implicit branching; next-day input records parent checksum and command
  identities. One immutable calculation identity owns all outputs. Migration
  `0002_temporal_ownership` applied without changing0001.
- Unchanged representative artifact SHA256
  `458c7c661cc2e6b2e65f30415042b98ab889c6e151aeaf086c00029c6528c92f`:
  **96/96 complete boundary comparisons PASS** across39 retained identities and
  12 computed days, June6–17. **4/4 actions PASS** for input membership, exact
  resulting acceptance/sleep rows and persisted before/after digests. Following
  days consume these actions and match their legacy boundary fingerprints.
- Modern outputs are fresh PostgreSQL readbacks. The oracle for this checkpoint
  is retained canonical SQL evidence, not fresh SQL execution. The three retained
  full-output days(0,1,11) each reconcile132 script receipts against both local
  runtime and preserved deployment; remaining days use the retained exact typed
  bag fingerprints. API DLL hashes qualify the action receipts. No fields were
  excluded, coerced or normalized to achieve this connected result.
- Evidence: `D:/freshvcf-build/evidence/f2-connected-012/execution.json`, hash
  `3cabe70e3fa71232f84df1ea9e57c684321203715c8217788aef6fab1b1ee053`;
  `f2-connected-012-final-comparison/comparison.json`, hash
  `fc45a82a2e1815ce77b4ed01b09b0017bccf6344b9e84112c57f55056756ecdb`.
  Terminal durable run: `83940672-749c-4728-b36a-26c29ea0dc61`.
  Terminal output digest:
  `d4d2863dd520c1ec7d22599ef432de86ef68d6773aa227aaede9df165bc2c759`.
- Harness development failures are retained, not calculation failures: source
  paths used both relative and absolute forms; representative action receipts
  have a different wrapper from full-estate receipts; action membership is the
  SQL Suggestions/latest-log/ReasonCodes projection, not raw Suggestions rows.
  Exact source-backed mappings corrected these checks; inputs/calculations did
  not change. Final comparator refuses ambiguous latest-log TOP1 values.
- Independent review identified and resolved three ownership gaps: action dates
  now stay within their parent/next-run chronological boundary; an opening and
  execution revision have one unique root key; publication rechecks the locked
  input against the exact digest calculated. Migration0003 backfills the existing
  initial run's root key without changing business inputs or outputs. The bounded
  re-review found no remaining issue in these corrections.
- After those safeguards, `f2-ownership-001` freshly recomputed the affected first
  two days:16/16 boundaries and4/4 actions PASS in
  `f2-ownership-001-comparison/comparison.json`. This is a targeted2-day pass,
  not another12-day claim. The unchanged business functions retain their prior
  96-comparison evidence. The command now captures executed Python source hashes.
- **15 migration-enabled persistence tests +17 focused tests PASS**, including
  all6 F1 runtime tests; Django check and migration-drift check PASS. All376
  baseline resources unchanged. `baseline/temporal-regression.json` freezes the
  retained ledger and original fresh comparison receipt identities.

Remaining F2 exit, without a new queue: fresh isolated canonical temporal SQL
replay; explicit ledger-governed shallow then200-SKU/20-location/1240-pair trial,
3×maxRLT, half-RLT transit and automatic workflow policy; compare all required
daily calculations, emitted reports, action effects and final persisted state.
The retained v1 timelines encode the12-day horizon and fixed actions but do NOT
declare the later ledger conservation/half-RLT/automatic-action policy. They
remain regression inputs; do not relabel them as that final trial. Any extension
must preserve retained catalogue identity and have one explicit input manifest.
F3 application delivery remains pending. Existing serving applications unchanged.
