# Bounded BTR query and access-path improvement

Authorized by the human in the successor migration control chat on 4 October
2026. Executor: `01a10098-1a4b-7e03-a9d3-77542504632b`. This is an implementation
contract; `docs/MIGRATION.md` remains the only status tracker.

## Starting point and objective

### Latest human override: existing databases only

The human directs stopping database replication, recovery/repopulation and
copy-verification work and advancing with the EXISTING legacy SQL Server and
EXISTING Fresh PostgreSQL databases. This supersedes all copy/restore approvals
and isolation prerequisites below for continuation. Safely stop owned copy/scan
jobs, preserve partial artifacts inertly, and do not delete or finish them as a
benchmark prerequisite. Reuse retained data identity and response comparisons.

Temporary reversible CPU/memory resource matching is authorized on both existing
database runtimes, including the PostgreSQL instance serving3005. Capture original
settings/effective limits, apply comparable hardware-appropriate budgets, alternate
legacy/Fresh measurements and restore original settings afterward or on failure.
No data/schema reset, reload, volume replacement, engine replay, grant changes or
shared Docker/WSL restart. Use online resource controls where supported. A new
disruptive infrastructure choice beyond this resource configuration requires
explicit human approval. Observe background workloads without killing unrelated
processes. Verify existing legacy application availability and measure BTR now;
copy completion and full database rescanning are not required.

Future replication/restores, replacement infrastructure or similar scope expansion
must receive explicit human approval BEFORE adoption. Do not infer that permission
from a performance objective or superseded copy approvals. Current priority is
the actual matched-resource comparison, preserving correctness and the existing
bounded BTR scope. Reporting-layer implementation remains unopened.

### Human clarification: performance authority

The human clarified that the full original VM dataset governs reporting scale
and that performance acceptance must compare the canonical legacy application
with Fresh on that same logical dataset. This supersedes the earlier provision
below that deferred matched-legacy acceptance. Fresh before/after timings remain
diagnostic evidence, not the final performance gate. Accepted normal F1/F2
publications are functional integration regressions only: do not benchmark their
smaller population or reopen engine parity. Preserve completed useful work.

For the bounded BTR journey, reuse verified owned legacy VM-data clones and the
canonical deployed consumer under the existing exclusive oracle ownership rules.
Match date, scope/hierarchy, branch, horizon, filters, page/columns/export, full
output population, resource budget and request pattern. Apply the sampling protocol
below to legacy versus Fresh candidate; require Fresh median/p95 no worse,
throughput at least equal and errors no worse, with complete output equivalence.
Retain a bounded Fresh before/after comparison to attribute the correction without
duplicating the full benchmark campaign. Measure API and actual BTR browser
journeys at equivalent boundaries. SQL-only timing is query evidence, not full
application latency acceptance. If the equivalent legacy application path or
resource conditions cannot be obtained safely, state the exact missing boundary
and mark comparative performance UNPROVED; never substitute synthetic normal
results or Fresh-before timings. No new ports, engine replay, borrowed databases
or protected-service mutations are authorized by this clarification.

Continue the current candidate and complete its affected correctness proof.
Normal-publication checks protect correct consumption of modern engine outputs;
they must not become a second scale-optimization programme. Any fixture-only
optimization still needs an explicit statement of operational applicability.

Accept `7b40ba6` for the bounded report-contention exit. Its delivery receipt
records the pushed commit, clean tree and deployed MTA image761719e96c0f95ccdb5f0ad79f7e96125b172ab79fafac72e3a3790615bc952a.
Three nine-request bursts passed in50.565/53.155/54.376s with all27 complete
responses unchanged. Login, security, restart, rollback and drain evidence is
retained. This is not general latency or whole-page acceptance. Preserve the
observed SPA profile-link failure during BTR loading; address navigation is not
equivalent proof that the SPA link works.

Next active item: reduce the measured BTR grid/count database work and latency
using query correction and justified indexes over existing typed relations.
Both On Hand/PhysicalInv and Dispatch branches, and their existing count semantics,
are in scope. Preserve full responses and verify applicability to normal accepted
publications as well as the large fixture. Deploy, commit/push and stop for review.

Evidence: `D:/freshvcf-build/evidence/3005-report-contention-20261004-001/`,
especially validation.json, db-attribution/*, and response-comparison.json.
BTR paired reads varied19.16–46.87s. Observed PG work included37096 block reads,
10.58MB temporary files and CPU throttling under the existing1CPU/1GiB limit.
Earlier matching PG counters are absent: do not attribute variance to host/cache
conditions as an established cause. The grid's retained second plan spends about
14.6s before first output. Inspect expensive plan nodes rather than treating an
index or SQL rewrite as the predetermined answer.

## Scope and exclusions

### Latest human amendment: existing development SQL Server

The human explicitly authorizes using and making necessary reversible benchmark
resource changes to the existing local development SQL Server instance, despite
its other hosted databases. This supersedes the shared-SQL resource-change
prohibition below for this bounded BTR comparison. The presence of61 other
databases is no longer an authorization blocker or a reason by itself to require
a separate SQL restore. Prefer the simplest valid setup; inspect already-started
copy work before changing direction and preserve completed copies/evidence.

Capture original SQL CPU/affinity/memory settings and effective limits, choose
hardware-appropriate comparable budgets, apply reversible settings, and restore
original settings after the benchmark window (also on failure/interruption).
A SQL service restart is authorized only if indispensable to apply the selected
settings; prefer online changes, drain benchmark work first, and verify recovery.
This permission does not authorize deleting/resetting other databases, changing
their contents or credentials, killing unrelated sessions, or restarting shared
Docker/WSL. Observe competing activity; an idle database consumes no query CPU,
but active background workloads must be measured and cannot be ignored in a
parity claim. Match enforceable resource opportunity, not merely setting labels.

The approved modern benchmark copy/resource configuration remains available;
serving3005 keeps its existing allocation and accepted image. Use the existing
canonical legacy app against the verified retained VM clones; no new public port,
engine execution or semantic change. Comparable application budgets, alternating
runs, full-output equivalence and legacy/Fresh median/p95/throughput/error gates
remain mandatory. Do not stop at the superseded shared-instance blocker; execute
the comparison and continue correct bounded query/index work as needed. Report
the measured outcome honestly if parity is not achieved. All other scope and data
protections remain, including the45GiB cap for any approved copies retained.

### Human amendment: matched benchmark resources

### Subsequent copy authorization

Direct human approval in this executor chat on4 October2026 authorizes owned
benchmark database copies under `C:/freshvcf-btr-benchmark`, capped at45GiB:
restore the four retained legacy databases and consistently copy the modern
fixture. This supersedes only the prohibition on these copies/restores and their
named storage. Use isolated serial benchmark resources and no new host ports;
shared SQL Server, serving3005, authentication permissions and F1/F2 remain
unchanged. Verify source identities and complete data equivalence before treating
the copies as comparable. All correctness and matched-performance gates remain.

On4 October2026 the human authorizes resource matching for this bounded legacy
versus Fresh benchmark. This supersedes the fixed-budget prohibition ONLY for
explicitly owned isolated benchmark processes/containers. It does not resize the
3005 serving stack, F2 execution resources, shared SQL Server/WSL/Docker services,
or protected3002/3003/3004. A task-owned database on a shared server does not grant
ownership of server-wide CPU/memory settings.

First inspect actual local physical/logical CPUs, available RAM, runtime/VM caps,
storage placement and existing host load. Verify each database's effective CPU
quota/affinity and memory ceiling; exposed16 CPUs alone is not effective usage.
Select and document one common feasible database CPU/memory budget with host
headroom, and comparable application-tier budgets and total stack opportunity.
Do not guess a number, allocate all host capacity, or optimize budgets separately
to favor one engine. Count SQL Server buffer/process memory and PostgreSQL
shared/per-query/process memory within comparable aggregate enforced ceilings;
identical configuration knob values are not required. Keep the selected budgets
fixed throughout each matched series and record actual utilization/throttling.

Use the existing single owned test arrangement, reconfigured serially where
necessary, without parallel competing benchmark stacks or additional host ports.
Starting/recreating exclusively owned benchmark containers/processes and assigning
their CPU/memory limits is authorized. Reuse existing retained dataset resources
and canonical application artifacts. If safe matching requires a new data copy,
restore, volume, shared-service change or protected runtime mutation outside the
existing authorization, report the exact dependency rather than proceeding.
Do not repurpose a serving resource merely by labelling it a benchmark.

Run alternating legacy/Fresh observations without simultaneous benchmark load;
drain work between samples and observe background host load. Match storage/cache
conditions where practical, record unavoidable differences and uncertainty, never
flush shared caches. Keep application-cold distinct from disk-cold. Resource
matching is not a blanket license for engine tuning or relaxed correctness.

Report separately: (a) legacy-versus-Fresh parity at the declared matched budget;
(b) Fresh behavior at the existing3005 deployment limits. The original fixed-limit
overlap/login/drain regression still applies. A speedup caused only by giving
Fresh more resources is not a query optimization result; compare Fresh baseline
and candidate under the SAME declared budget. No serving resource increase or
deployment-capacity acceptance is implied by a benchmark pass.

Preserve the failed key-prefix candidate and its10/30 adversarial mismatches as
rejected evidence. Do not deploy or benchmark it as a valid improvement, invent
a tie-break, or relax ordering/value comparisons. Continue only with correct
query/index candidates; the accepted3005 image remains the rollback baseline.

- Begin at the unchanged April7 fixture and accepted normal publication identities.
  No import, replay, new fixture population, grant reassignment or calculated-state
  writes. Reuse retained inputs and independent/reference consumer evidence.
- Primary boundary: `mta/presentation/btr_sql.py`, directly used BTR predicates,
  image-query/access helpers where evidenced, focused tests, migrations for
  justified indexes, and existing deployment/restoration tooling.
- Preserve count's full report projection versus grid's requirement projection,
  duplicate joins, NULL/string semantics, canonical filters, scopes, horizons,
  ordering/ties, paging, types, envelopes, both branches and downloads. Earlier
  approved exceptions apply only in their exact scope. No assertion weakening.
- Do not optimize unrelated RRR/BPR/DBM/Guided routes, unify all fixture readers,
  redesign the frontend, fix independent navigation behavior, introduce caching,
  materialized projections or new operational storage, or change canonical SQL,
  engines, execute_day or F1/F2 receipts. Broader Stage2–5 remains paused.
- Necessary isolated3005 MTA build/deploy/restart and bounded owned index migration
  are authorized. Gateway/frontend changes only if indispensable for existing
  selection/rollback coordination, not as a new optimization surface. Preserve
  catalogue binding and login isolation. No new port or protected service changes.
- Keep serving PostgreSQL1CPU/1GiB, MTA4GiB/2CPU/two workers, gateway1GiB, current
  deadlines, restart=no and all dataset/page-size/field populations. Only owned
  benchmark budgets may change under the explicit amendment above; no serving
  capacity increase, reduced load or shared cache flush.

## One implementation sequence

1. Confirm active tracker item and runtime identities. Reuse retained plans and
   capture only missing comparable baseline evidence. Attribute BTR key selection,
   joins, counts, wide-row reconstruction and serialization separately where
   measurable. Record buffers, spills, row estimates/actuals and CPU throttling.
2. Implement the smallest correction to dominant work. Consider pruning unused
   columns, avoiding repeated joins/materialization, and semantics-preserving
   indexed comparisons only when the actual plan supports them. Do not assume
   counts and grids have interchangeable joins. Inspect effects on shared helpers.
3. For each change explicitly document fixture and normal-publication execution
   paths. Prefer a common BTR query improvement when valid. Do not leave an
   applicable improvement fixture-only without a specific contract reason.
   Normal data need not have equal scale, but use real populated retained normal
   BTR cases for complete correctness proof; empty-only tests cannot prove positive
   compatibility. If required retained data is unavailable, record that limitation
   and stop before claiming both paths accepted; do not manufacture engine output.
4. Differentially compare complete responses against retained pre-change and
   independent/reference readers for both branches, both/name selection, broad and
   restricted scopes, positive/empty/NULL/duplicate cases, horizons, filters,
   first/later pages, count and affected full exports. Preserve exact order where
   defined and exact existing tie dispositions. Compare values, not just counts.
5. Prove query/index changes on exclusively owned test resources before deployment.
   Schema/index migrations require Django check, makemigrations --check, migration
   plan and migration-enabled PostgreSQL verification. Do not alter sealed source
   rows or disable immutability triggers. Use bounded lock acquisition for serving
   index deployment; if the permitted safe path is unavailable, report the blocker.
6. Deploy the verified candidate, complete the acceptance pass, update MIGRATION
   and the operational handoff, commit/push the coherent result and stop. Reuse
   unaffected proof; no repeated provenance inventory or additional plan layers.

## Required proof and stopping boundary

The direct human reply `call_AGGtUEgL9nSvOJpm7AQWemMi` approves only the retained
April7 fixture's Category alias-order exception recorded in LEGACY_EXCEPTIONS.
Compare exact alias multisets including duplicate multiplicity, retain original
strings, and keep every other field/type/row position strict. This changes only
the scoped evidence comparison; it does not authorize rewriting responses or
transferring the exception to normal publications.

- Compare baseline and candidate with identical dataset/date/scopes, full5000-row
  BTR requests, branches/horizons/filters, resources and request patterns. Use five
  warmups and30 measured interleaved warm observations for the principal BTR paired
  grid/count journey; retain raw failures, median/p95, throughput, bytes, PG buffers/
  spills/CPU and gateway/MTA resources. Compare application-cold behavior across
  five repetitions in owned isolated resources; never flush shared disk caches.
  Cover concurrency1/4. If candidate/baseline schema differs, use explicitly owned
  test arrangements or bounded reversible index operations; do not repeatedly
  rebuild the serving stack for each sample. Label cold-app versus cold-disk honestly.
- Show lower BTR median and p95 under comparable measurements and reduced dominant
  database work, without worse failures or throughput. If variance prevents that
  conclusion, mark improvement unproved and investigate only the disputed measure.
  Do not invent a speedup percentage or treat a single fast query as acceptance.
  Fresh before/after measurements attribute the improvement. Final performance
  acceptance is the matched full-VM legacy-versus-Fresh gate specified above;
  unrelated reports and broader Stage2 acceptance remain outside this assignment.
- Repeat three nine-request bursts with full exact responses under60s and no
  restart/cache clear between them. Preserve the preceding eight-request proof
  unless a relevant change requires repeating it. Login/profile must remain
  responsive while reports are pending; observe resource drain and no OOM.
- Browser BTR: both branches, grid/count/filter/horizon/paging consistency,
  affected downloads, navigation away while pending and return. Retain the known
  SPA-link disposition explicitly; do not broaden this assignment into UI repair.
  Repeat affected scopes/denials and normal-publication checks in owned tests.
- Record exact source/image/index versions, migration state, startup/readiness,
  selection/catalogue consistency, unchanged F1/F2/protected/grant identities and
  rollback procedure. Rollback must account for indexes as well as image and avoid
  deleting retained evidence or operational state. Verify restart/recovery.

If query and index corrections cannot establish an improvement without changed
business semantics, a new projection/storage model or additional capacity, stop
with the expensive plan nodes, attempted bounded corrections, measured effects
and a concrete next decision. Do not implement level-three storage changes under
this authorization. Deliver PASS or the precise consolidated unmet exit; never
mark the whole migration or Stage2 complete.
