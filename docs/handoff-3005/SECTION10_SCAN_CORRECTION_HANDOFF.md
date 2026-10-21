# Supplier, DBM and BTR scan correction — 21 October 2026

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

This is the tested source handoff for Section10 of the existing daily-calculation optimization plan. `F:/freshvcf/docs/handoff-3005/TRACKER.md` remains the sole status/decision tracker. The comparison baseline is commit `cfd73d6d90ada1e6334731ee27886c836122af47`. The human-stopped large April8 run is **not complete** and was not restarted for this correction.

## Delivered boundary

Thirteen production modules change only candidate lookup, equivalent grouped counts and resource lifetime:

| Boundary | Correction |
|---|---|
| Supplier dispatch | Index parent anti-existence, ordered topmost joins and attribute LEFT JOIN; retain every one of the28 fields and sourcing/master/attribute occurrence ordinals. |
| Production suggestions | Index plant/report/stock joins and reuse the exact grouping identity; retain statement order, native int assignment, duplicate multiplication, spelling conflicts and stock netting. |
| DBM D1–D3 | Exclusion/master, introduction membership and forced/accepted-stock history lookups. Retain duplicate membership factors, date windows, scalar conflicts and both accepted-stock operations. |
| DBM D4–D10 | Suggestion discard/log joins, Norm1 advisory, delisting, phase recommendations, Norm0/1/2 description/detail/parent joins, automatic acceptance and Norm-change metadata joins. |
| BTR B1/B2 | Index category history; count suggestion Type multiplicity once without changing the required joined history bag or age calculation. |

`OrderedIndex` is lazy and local to one unchanged input generation. It retains keys and source ordinals; text pair populations reuse the existing SQLite ordinal store with a2MiB cache. Scalar metadata indexes hold keys/ordinals, not row copies. Original residual predicates still own matching, eligibility, validation and errors. Unqualified/custom comparators use the original ordered scan. Missing or unsupported keys fall back to that residual rather than being cast or silently dropped. SQL JOIN NULL denial, GROUP NULL and existing raw tuple equality remain distinct.

Norm1 and phase recommendations keep their first eligible master's original complete date/key-validation pass. This preserves errors on unrelated observations and their precedence. Later masters reuse the validated immutable generation. Necessary duplicate join expansion and sequential business rules remain intact; this does not claim constant memory or linear work where the required result itself multiplies rows.

The index owns active cursors/iterators. On short circuit or an exception it closes them before SQLite, releases the temporary directory and preserves the original exception. A weak iterator registry avoids retaining completed/short-circuited cursor batches. Explicit tests cover `any()`, retained exception tracebacks, unstarted iterators, repeated probes and `sys.unraisablehook`.

No calculation formula, policy, input, schema, migration, recovery limit, authority, frontend, MTO, auth, account, serving configuration or resource ceiling changed. Optional `complete_daily_btr.py` remains excluded because it has no established native caller in this flow.

## Verification

- **137 focused tests passed**, including the existing50,000-row ordinal memory check and affected shared-index callers. That check observed138,205 bytes of traced Python index allocations; it is not total process RSS.
- **18 producer groups ×32/64/128 populations** matched the original committed producer's complete values/errors/order without source mutation, using real file-backed `RecordRows`. There are65 ordinary/invalid-key/date comparisons and44 missing-field comparisons. Per-group build/probe/candidate counts, CPU/wall and traced allocation peaks are recorded in the external evidence.
- Selected independent expected values were derived from six actual legacy SQL files, whose hashes match `baseline/manifest.json`: supplier28-column joins, production stock netting, BTR age/category, delisting and phase current-stock multiplicity. This is selected rule qualification, not a new full legacy campaign or a blanket parity claim.
- **28 tests passed in the final PostgreSQL worker**, including a positive native CSV→capture→controls→both R1 passes→allocation/Pick→DBM/BTR→typed commit/readback→reports/guided aggregates→InputData archive→admission/selection path. Positive allocation,38 Pick events, history/control effects and capture consumption were checked. Separate positive outputs from every changed producer group were saved/read through actual typed tables in rollback-only component transactions.
- Existing ownership, stale/foreign/duplicate/depth denials, filesystem rollback, late actual SQL rollback and compatible-release/original-certificate preservation were exercised. The final logs contain no ignored/unraisable cursor exception. Earlier successful proof receipts are retained separately; they do not qualify the later cleanup change.
- Final worker exit0/PID0/non-OOM, no guard failure, no scratch clients. Before/after working database metadata, role catalogue/memberships and original six service identities/states were identical. All20GiB C/D/I free-space reserves remained satisfied.
- The scratch database and worker were removed only after a verified external custom-format dump and terminal/ownership checks. No image was built and no unrelated/protected resource was removed.

At128 many-key rows, supplier residual joins fell from49,152 to256; production suggestions from73,664 to512; introduction key evaluations from98,560 to1,024; category key evaluations from49,536 to1,537. These are structural operation counts, **not a speedup ratio for the97,097-pair daily workload**. Small wall times include tracing, disk-backed indexing and shared-host noise; a small case can be slower despite fewer comparisons. BTR's required duplicate history expansion remains output-sensitive.

## Evidence and remaining execution boundary

External evidence root: `D:/freshvcf-build/evidence/daily-contract-audit-20261021/`.

| Evidence | Purpose |
|---|---|
| `section10-final-scan-proof.json` | Final13 production-file raw hashes, full baseline comparison, scaling, errors and missing fields. |
| `section10-native-expectations.json` | SQL pins and independently derived selected expected results. |
| `section10-terminal-focused.log` | Final137-test terminal result. |
| `section10-terminal-postgres.log` | Final28-test native SQL and positive producer results. |
| `section10-terminal-postgres-measurement.json` | Actual worker terminal/resource/preservation state. |
| `section10-terminal-cleanup.json` | Verified scratch-only archive/removal receipt. |
| `section10-terminal-pass.dump` | Retained small proof; SHA256 `a2bb404e78758c43cd386296f95c6d552ec921849bf5e2604be44c4ef45a1dae`. |

The loaded large opening and six attempted headers/captures remain unchanged. The latest human-stopped run `ddf9c21c-92d5-4832-9743-f3ad0ac10ef2` truthfully retains RUNNING/CALCULATE/CAPTURED metadata with no accepted output. The scan correction deliberately adds no status rewrite or continuation permission. The current default/terminal recovery contract does not admit another execution from that fifth-wrapper RUNNING leaf. Any next large execution needs a separately reviewed exact admission/reconciliation decision, one packaged candidate, one finite window and one attempt. Do not infer those permissions from this handoff or reuse the interrupted operation's historical clock.

There is no new full-day timing, connected UI acceptance, public deployment or production-capacity claim. Previously qualified legacy differences, unsupported scenarios and existing acceptance limits remain explicit.
