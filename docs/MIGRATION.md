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
resources; inherited receipt status is not fresh execution status.
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
