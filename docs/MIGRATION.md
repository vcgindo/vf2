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
| F1 Current-day MTA | Input/controls/orders → requirement/rationing/PSO/advances/Pick → persisted report inputs. Full typed comparison on retained positive and sizeable artifacts; readback | ACTIVE |
| F2 Temporal MTA | Complete configured DBM + controls/workflows + BTR/history; independent own-state shallow then full-estate replay over 3×max RLT; required actions and next-day consequences | PENDING |
| F3 Application delivery | Required API/UI surfaces, navigation/scopes/actions/downloads; single-PostgreSQL deployment, fresh-start/restart/retry, MTO regression, runbook and coordinated 3004 delivery | PENDING |

Active F1 unmet exit: independently calculated current-day outputs with fresh
PostgreSQL persistence and retained canonical comparisons. Dependencies: F0
checks pass; source/profile/retained processed input are pinned. Permitted edits:
pure input/planning functions, their application orchestration, runtime schema,
parity comparison and affected tests. Keep API/UI acceptance in F3.
Proof: retained positive raw cases plus all required sizeable current-day fields,
typed row multiplicity, persistence/readback and explicit invalid input failure.

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
  **RECEIPT_INCOMPLETE**, not PASS, and modern results/old receipt are preserved.
  Next: refresh only needed canonical receipts in dedicated VFTEST_Fresh_* DBs;
  include positive PSO/advances/formed-Pick cases and the selected customer adapter.
- Fresh PostgreSQL initial migration applied;4 migration-enabled transaction
  tests pass (readback/retry, row tamper, missing output, durable failed attempt).
  Six framework/pure-input tests pass. Django reports no missing migrations.
- Evidence directories under `D:/freshvcf-build/evidence`:
  `f1-sizeable-001`, `f1-persisted-001`, `f1-persisted-comparison-001`,
  `f1-raw-001` (retained failed receipt-compatibility attempt), `f1-raw-002`.
- Durable sizeable run: `fe5fd4dd-12e5-4415-a33f-16c1434c82f6`.
  Output checksum: `1edd822a2b6167e6002d0936c7112bdbd1d81bbaa616a300fdc3406a5689bd69`.

F1 remains ACTIVE. These proofs do not establish temporal DBM, raw ingestion for
the whole sizeable estate, UI acceptance or branch-wide parity. No inherited
empty output is credited as positive order/advance/formed-truck coverage.

Test-resource owner: this fresh migration task. Compose project `freshvcf-test`,
PostgreSQL data at D:/freshvcf-build/postgres,1GiB/1CPU; one-shot MTA2GiB/2CPU,
restart=no, no host ports. One-shot containers use --rm. Stop this project's
idle PostgreSQL at checkpoint/handoff; preserve its data for next invocation.
