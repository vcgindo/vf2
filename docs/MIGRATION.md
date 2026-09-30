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
| F2 Temporal MTA | Complete configured DBM + controls/workflows + BTR/history; independent own-state shallow then full-estate replay over 3×max RLT; required actions and next-day consequences | ACTIVE — bounded1240-pair relational storage correction verified; eight fresh day-one boundaries PASS; continuation held at pre-existing temporal Pick-input divergence (14 modern versus0 legacy remaining rows) |
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
PostgreSQL data at D:/freshvcf-build/postgres,1GiB/1CPU; one-shot MTA4GiB/2CPU,
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
Correction to the earlier limited inventory: both retained v1 timelines DO
contain explicit ledger conservation and half-RLT dated shipments. Independent
validation of their unchanged bytes passes: representative39identities/1073fact
rows/899shipments; sizeable1240identities/34682fact rows/32909shipments. Each
opening BPR/DBM historical fact and every future input matches its stock/GIT
ledger; receipts equal dated shipments; transit is positive half-up rounded
RLT/2;12consecutive computed days equal3×maxRLT4. Receipts are
`D:/freshvcf-build/evidence/f2-ledger-representative-001.json` and
`f2-ledger-sizeable-001.json`. No generation or input substitution is needed.
Their four fixed day0 Apply/Sleep commands do not establish daily automatic
acceptance. The remaining trial-policy work uses these SAME external inputs,
with each engine deriving actions from its own computed recommendations.
F3 application delivery remains pending. Existing serving applications unchanged.

### F2 fresh oracle and automatic trial checkpoint

- Fresh canonical SQL completed the same39-identity/12-day fixed-action timeline:
  **348/348 comparisons PASS** (8complete boundaries +20current-day contracts
  +complete emitted reports each day). Modern counterparts are the prior fresh
  PostgreSQL readbacks, not seeded legacy answers. SQL uses only owned Fresh
  databases, restricted principal and exclusive replay lease. Canonical business
  SQL and its132daily source receipts are unchanged.
- Fresh receipt: `D:/freshvcf-build/evidence/f2-fresh-sql-012/replay.json`, SHA256
  `e0b34436dcf4ead6603532d0d08c75a557443df6096ac093891d216b766415fd`.
  Day0 is retained in its verified prefix `f2-fresh-sql-002`. Initial permission
  failure remains in `f2-fresh-sql-001`; SQL CHECKIDENT required db_ddladmin only
  in the owned Fresh BPR database. No live/other database or server grant added.
- Independent review tightened exact nested capture rosters, stage multiplicity,
  complete dependency hashes and continuation guards. Recomparison of all12full
  SQL captures passes348/348 in `f2-fresh-sql-012-recomparison.json`; this is an
  updated comparison of fresh captures, not another claimed SQL execution.
- The same unchanged representative external facts now ran12days through fresh
  PostgreSQL with explicit policy `own-recommendations-daily-apply-retained-sleep-v1`.
  Retained Sleep events act on their exact declared dates; all other own computed
  recommendations are submitted through the real Apply command. This does NOT
  enable canonical `AutoDBMActive`; no cooling/suspension behavior is invented.
  Every persisted action-state digest and next predecessor is recorded in
  `f2-auto-representative-001`. Policies now have distinct durable opening and
  idempotency identities. The complete shallow SQL result is recorded below;
  this does not yet establish full-estate automatic parity.
- Automatic SQL comparison stopped once at day1 on a comparison-harness regression:
  wrapping reports in a list accidentally made nested row order significant.
  Exact ordered stage/multiplicity assertions remain; per-stage report rows again
  use typed bags preserving duplicates. Original failure `f2-auto-sql-001` remains.
  Rechecking both complete captures passes62/62, including action selection/state,
  in `f2-auto-sql-001-recomparison`. `f2-auto-sql-012` resumes from its OWN verified
  legacy close; no repeated modern calculation or copied legacy state.
- Positive Rule4 coverage is not inferred from the cohort name: it is shadowed
  in the connected representative timeline. Two unchanged earlier Rule4 inputs
  (`sequence-rule4-wins`, `threshold-inclusive`) were freshly computed in Python
  against qualified retained canonical captures: **12/12 tables PASS**, with
  positive Type4 suggestions. Receipt `f2-retained-rule4-001/comparison.json`, SHA256
  `43563c8d0470e5a9ae65929154e90713ec4418972e79208d1032b80d20cf05e5`.
  This is supplementary rule-seam proof, not a claim of Type4 activity in every
  connected population or fresh SQL execution for those two cases.
- 35 focused tests pass. Final bounded re-review has no actionable findings in the
  revised oracle guards/report comparator/daily action-policy boundary.

Final shallow automatic result: **372/372 comparisons PASS** across all12days,
including own-derived selection and complete post-action state every day. The
trial executes24Apply selections and2Sleep selections; later days consume their
own resulting acceptance/cooling state. Receipt:
`D:/freshvcf-build/evidence/f2-auto-sql-012/replay.json`, SHA256
`316070183c5be144042736e314dfb0eb95a83e4833ae4882457a5bf4ac55dfd5`.
Terminal PostgreSQL run: `1b3dbf1a-ddc7-4970-bb80-489248fd81e0`; output digest:
`9bcf8f4c66578c51e28fbc55c49c8f5d58f776bcad3c43ef39ce24309ab95ebe`.
Earlier two-day failed/recompared receipts remain linked, not overwritten.

Remaining within F2: run the SAME accepted automatic policy on unchanged1240-pair
full estate, compare every required daily population,
reports, actions and terminal persisted state. Do not generate replacement facts,
change legacy logic, broaden inactive profiles or begin F3 prematurely.

Full-estate execution reached the known Norm0 occurrence-order guard on day0.
`f2-auto-sizeable-001` is a preserved FAILED attempt, not a calculation mismatch
or accepted day. Active F2 boundary now includes transferring only
LEG-NORM0-OCCURRENCE-ORDER's explicit non-parity presentation disposition from
the identical retained artifact. Keep all other comparisons exact, independently
derive affected keys from canonical state, preserve raw text, and carry a visible
legacy-flaw status instead of declaring the affected field passed. No data
regeneration, source repair, new queue or whole-report skip is permitted.

Full-estate attempt `f2-auto-sizeable-002` was killed by its2GiB memory cgroup
at2026-09-30T22:00:51+05:30 before publishing any checkpoint. Its source receipt
and RUNNING database record remain preserved, not accepted or silently retried.
The kernel records Python PID3344668, container19ab93954799ef8291b3a9bb7914c94961d8816f27f97404ea20f80232cbb1fc.
Active F2 correction: canonical streaming checksums and checkpoint-at-a-time
serialization inside the SAME atomic publication transaction; no output roster
or values removed. The own one-shot worker now has4GiB RAM/no added swap,2CPUs;
PostgreSQL and all serving resources unchanged. Prove checksum equivalence,
transactional readback/tamper/rollback, then retry the full unchanged population.

The next attempt `f2-auto-sizeable-003` computed day0 but PostgreSQL's1GiB
backend was killed while parsing the full50-stage DBM trace into one JSONB
value. The transaction rolled back; this FAILED attempt is not parity. No
serving database was involved. The evidenced storage correction keeps every
checkpoint and checksum: large row arrays are gzip-compressed JSONL in a nullable
binary column, decoded before all existing integrity/parity checks. Small JSON
checkpoints and all existing rows remain readable unchanged. New migration0004
is additive, with a database constraint against conflicting encodings; no earlier
migration is rewritten. Release verified predecessor/export graphs before the
next calculation/action so unused full traces do not multiply memory.

User storage mandate supersedes the preceding compressed-in-PostgreSQL remedy:
keep calculate_day, inputs and comparison semantics unchanged. PostgreSQL owns
run/input/predecessor/action identity, required closing state, consumer outputs
and checksums. Internal traces, including all8 major boundaries, are compressed
validation files referenced by immutable checkpoint metadata, not production
JSON values. No additional memory increase. Before the12-day continuation,
prove atomic rollback plus exact1240-pair day-one persistence/readback. Applied
0004 remains immutable;0005 removes its unused binary column (zero retained
rows used it) and adds external-evidence metadata. Both failed attempts remain.

### Current F2 storage correction — supersedes JSON/blob operational storage

- No calculation, canonical SQL, synthetic fact or automatic-action change.
  `calculate_day` remains byte-unchanged. No further memory increase: own worker
  remains4GiB/2CPU, PostgreSQL1GiB/1CPU, no public ports or serving changes.
- Canonical schema descriptor: `baseline/production-state-schema.json`,337
  bindings/300 existing source-table schemas (including the frozen scratch
  closing roster). Types/column order/length/precision/scale/nullability come
  from the already pinned, schema-verified Fresh oracle, not sampled data.
  Canonical descriptor digest:
  `89201eca8c797bcd70a9f87d9dce31cc2be27636eccc0f6cee027a8bcf09d7aa`.
- New typed `mta_state` relations have run FK, image owner, ordinal and explicit
  business columns. Bulk writes share the single day-publication transaction.
  No unique SKU/location constraint discards duplicates. Per-image manifests
  contain shapes/counts/checksums only and have a1MiB size guard. Required
  selected report exports use relational cells, not row JSON; all other report
  projections use their canonical typed columns. No internal stage graph is an
  operational PostgreSQL checkpoint.
- Closing-state reconstruction and committed Apply/Sleep deltas read these rows;
  source input facts and complete validation traces are immutable compressed
  files. Run/checkpoint metadata retains their owner paths, SHA256, logical
  checksums and complete roster. The comparator reads each of the8 boundaries
  separately, preserving its previous exact typed-bag comparisons and the sole
  qualified Norm0 text limitation. Production reads do not reload parity traces.
- Migration register: fresh_mta0004 was applied during the superseded experiment
  and remains immutable; no retained row used its binary field.0005 removes it
  and adds bounded production/evidence/action manifests.0006 creates explicit
  typed relations through generated RunSQL. All are on the same PostgreSQL DB.
  No migration fake/squash/history rewrite. Named-schema initialization now runs
  before migration for fresh Django-created test databases as well as deployment.
- Active gate: `prove_sizeable_storage` runs the unchanged1240-pair day twice:
  injected mid-write rollback with failed evidence retained, then actual complete
  publication/readback, exact next-opening/action-state reconstruction, readable
  projections and8 emitted boundaries. It is NOT legacy parity by itself; the
  fresh SQL day-one comparator must then pass before continuing the same12days.
  F3 remains PENDING. No new phase or recovery ID has been introduced.

### F2 bounded storage gate evidence

- `D:/freshvcf-build/evidence/f2-relational-day-one-005/storage-proof.json`
  SHA256 `71aab3f7f052645a4eb4a03f844091208f0df513ac125c55d7563a012be2af16`:
  **STORAGE_GATE_PASS_NOT_YET_LEGACY_PARITY**. The unchanged1240-pair artifact
  retains SHA256 `0f3084b7a6fb60b84edbd7c4dc01fef3c4b40f1a7c389ec82f88b9ad22519546`.
- Successful run `14685c6c-7e24-49bb-8c70-2b325ce64907`, business date2026-06-06:
  87,060 typed operational rows including three committed actions; exact
  production/report readback and committed next-opening DBM state. All19 complete
  output populations remain externally available, including all8 internal
  boundaries. All19 database checkpoint rows contain metadata with empty row
  payloads; `mta_state` contains no JSON/JSONB/bytea state columns.
- Injected mid-write failure run `cb8f8e33-1818-49bc-9617-2c5dc97615e9`:
  FAILED, zero production rows, zero checkpoint records, zero commands and no
  output digest. Its files are retained and cannot be read as a publication.
- Worker peak2,785,918,976bytes under unchanged4GiB; PostgreSQL unchanged1GiB.
  PostgreSQL's historical OOM count stayed1 before/after: no new OOM occurred.
  Both original OOM attempts remain. The first gate's count-to-JSON harness
  failure also remains in `f2-relational-day-one-004`; only integral count
  encoding was corrected, not calculation or input behavior.
- Verification:18 migration-enabled PostgreSQL protocol tests passed;34 focused
  archive/serialization/Norm0/oracle/policy checks passed; the bounded receipt
  linkage test passed. Django schema drift check found no changes. Independent
  review's one finding—receipt import accepted a substituted contract name—was
  fixed with the full ordered29/31 contract roster and aggregate qualification
  check. No additional static storage blocker was identified.
- `record_parity` attaches the actual oracle receipt path/hash, complete8-boundary
  roster and per-contract statuses to the same run after verifying its identity,
  committed output digest and readback. It never imports comparison populations,
  computes parity or treats the qualified Norm0 flaw as PASS.
- Fresh same-day canonical SQL comparison is retained in
  `D:/freshvcf-build/evidence/f2-relational-sql-day-one-005/replay.json`, SHA256
  `2cabf1f2b91cb6878040e6e7c513f99efa0ab4b049f2e1d130f099b8c710cab3`.
  All8 internal boundaries PASS. The unchanged comparator then stops with
  **DIVERGENCE** at `calculation/pick_remaining`:0 legacy versus14 modern rows.
  This is not waived, not a new legacy-flaw exception and not F2 acceptance.
  `record_parity` records DIVERGENCE and explicit NOT_RUN statuses for contracts
  after the stopping point. Source captures and failed receipts remain immutable.

### Current F2 continuation constraint — no new queue

The storage correction is verified, but the latest instruction freezes calculation
behavior and the artifact. Therefore the12-day continuation has NOT resumed.

Read-only diagnosis of the retained captures established:

- The frozen opening and canonical closing importer have200 SKU attribute rows,
  all with `Weight=NULL` and `Volume=NULL`.
- Canonical `Scripts/BPR/Ration_Scripts/GenerateLogisticPickList.sql:81` filters
  these with `WHERE ([Weight] IS NOT NULL OR Volume IS NOT NULL)`. Zero remaining
  Pick rows is consequently consistent with the actual canonical input.
- The SAME artifact's calculation profile separately holds810 logistics items,
  with unit weights/volumes. `mta/temporal/chain.py:137` (`calculation_source`)
  retains that profile's logistics while refreshing other producer-owned fields.
  `mta/planning/projections.py:278` (`_pick_rows`) consumes those retained
  profile attributes, producing14 remaining rows. This discrepancy predates the
  storage changes; neither file was edited in this correction.
- A read-only re-evaluation of the already captured calculation outputs with
  the existing comparator confirms the other14 current-day calculation contracts
  match. This diagnostic does not replace/overwrite the first-divergence receipt
  or certify its remaining master/report/action checks.

Required authority before further implementation: permit one source-backed
correction of the existing temporal logistics-input projection so it consumes
canonical producer-owned SKU/location attributes and preserves the SQL's NULL
exclusion and multiplicity, rather than profile overrides. Do NOT repair the
legacy SQL, populate synthetic weights, regenerate the artifact, waive Pick,
change automatic actions, reopen unrelated F1 proofs, or add a recovery phase.
That calculation-input correction is outside this turn's explicitly frozen
calculation boundary, so it has NOT been implemented.

After authorisation, preserve this committed day/failed proof, prove the affected
day on the same frozen input under an explicit corrected execution revision,
and continue the same12-day horizon only after its required comparisons pass
with the sole already-qualified Norm0 text limitation. F3 stays PENDING.
