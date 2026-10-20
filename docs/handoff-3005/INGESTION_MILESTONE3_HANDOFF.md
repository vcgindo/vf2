# Ingestion milestone3 — persistent masters and accepted daily inputs

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

21 October 2026. Same branch `codex/3006-logistics-integration`, from M2
`b678263110c3c88b4f5920080dec3d32ee6f6246`. Status: M3 source implementation and focused proof complete.
The sole live status/decision tracker remains
`F:/freshvcf/docs/handoff-3005/TRACKER.md`. This is the source handoff, not another queue.

## Delivered implementation

- Normal certified CSV staging copies and hashes each original once, parses one
  native graph, and stores accepted facts in nineteen fixed, attempt-owned typed
  tables. Metadata records the source/database/OID/initialization, field types,
  exact ordered digest and revision cut. NULLs, duplicates, dates and lexical
  timestamp forms survive full reconstruction. No business population is stored
  in the metadata JSON. Duplicate submissions reuse their original attempt.
- A private preparation object carries the successful native validation into
  inspection and execution. Invalid input still receives the original detailed
  diagnostics. Execution reconstructs the sealed typed facts and checks live
  authority instead of reparsing the archive and running a second full preflight.
  CSV and JSON use the same native producer and early preparation boundary.
- Certified successors read configuration and their own persisted predecessor;
  they do not rebuild the original opening for admission. The bounded certified
  handle survives release of the heavy opening cache and expires with the
  operation. Capture and commit still check source and all five generation
  counters. Uncertified paths and explicit administrative audits retain full
  verification. A prepared predecessor output read verifies immutable roots and
  its actual typed outputs; explicit input audits remain exhaustive.
- An unchanged active-NMS day reuses canonical typed importer masters with the
  latest predecessor Norms and operating state. It does not call the full
  `nms_master_raw`, `compose` or master producer. Required raw/canonical compatibility
  rows are lazy projections using the same factored overlays and normalizer,
  including orphan catalogue entries, NULLs, duplicates, source order, padding,
  parent descriptions and date-sensitive introductions. This is not another
  calculation engine.
- Approved master changes use the existing full producer over a proven complete
  SKU/location/parent dependency component. Global, unqualified, inactive,
  NonNMS, no-Norm, date-sensitive, full-closure and early-return cases explicitly
  retain the full canonical producer and its rejection/table-transition result.
  Accepted revision metadata points to existing committed typed partitions;
  operational Norms continue to come from the direct predecessor.
- New certified daily v3 inputs reference the original initialization, accepted
  static master owners and their own typed fact batch. References bind exact
  database/OID/source/initialization and immutable manifest/content roots. Static
  references are flattened to one physical owner. A changed canonical form is
  captured once rather than falsely referencing a pre-normalized root. NMS compatibility binds the
  direct predecessor output, not an accumulating delta chain. Existing v2 and
  M2 v3 manifests retain their original interpretation.
- Native InputData archives retain complete original/captured JSON files. Their
  new v2 manifest distinguishes the prepared reference root from the expanded
  captured-file hash and verifies both; old v1 archive behavior remains intact.
- Current-master publication retains equal rows/primary keys and writes only
  changed fields or added/removed ordinal tails in bounded batches. Unchanged
  partitions issue no business DML. Six forward migrations add staging/seals and
  allow occurrence-preserving UPDATE only under the existing consumed RUNNING
  day markers. Source/id/partition/ordinal moves remain denied, and location
  updates require the existing pending native publication receipt.
- `execute_day` and `finish_run` remain the only capture and atomic publication
  boundaries. Calculations, normal supplier/daily validation, queued actions,
  effective dates, histories, Pick outputs and report preparation remain owned by
  their existing producers. No timeout/capacity increase, bypass environment flag,
  alternate engine or new operator ceremony was introduced.

## Verification

Final PostgreSQL proof passed. This is M3 source/contract acceptance, not M4
packaged-image, live-upgrade, browser or large-data performance acceptance.

The affected unit command covers CSV/diagnostics, v2/v3 typed storage, immutable
fact batches, source and revision identities, unchanged compatibility, dependency
closures/rejections, incremental projections, shared preparation, certified
handle lifetime, supplier contracts and native finalization. Current result:
**210 checks run: 205 passed, five environment-dependent/inherited skips.**

The one disposable PostgreSQL database is `vf_ingestion_m3_20261021`, on the same
owned PG, with genuine migrations and no additional PG container or image build.
Its proof checks real guard denial, unchanged-row identity, late writer rollback,
complete staging/readback/seals, stale action cuts, a small root daily run and its
own successor, exact full-producer equivalence, zero unchanged-master business
DML/reconstruction, no successor opening reconstruction during preparation,
capture, calculation or commit, full input/output audits and the
existing report/selection/publication-resume contract. The acknowledgement is a
component fixture explicitly labelled `no-http-no-browser`; it is not UI proof.
GuidedHistory report preparation legitimately reads initial history; M3 does not
remove that report requirement or claim zero opening reads across all reports.

The fixture declares a substituted release identity because image production is
M4. It uses actual native registration, scoped installer credential, typed SQL,
full opening/all-thirteen-family certification, activation and existing engine.
The fixture omits only a redundant cluster-wide role GRANT, preserving existing
role memberships. No packaged-image or live-upgrade claim follows from this.

The final real PostgreSQL run passed both rollback-only SQL components plus the
root/successor integration test (186.205 seconds). All 175 migration records are
present; Django system check, `makemigrations --check --dry-run` and real-PG
`migrate --plan` passed with no drift or pending operations. Final SQL state was
exactly one initialization, two SUCCEEDED runs and two PUBLISHED feed attempts:

| Business date | Run | Output digest |
|---|---|---|
| 2026-10-18 | `185c5d6c-b7b1-4ab3-a593-d7c1b31e36c1` | `87a8776d26ed5393eaa24d809334c54b894fa6577a3954ea837299bbc1d2ea5e` |
| 2026-10-19 | `e4807b5c-e325-48a4-aa7e-7b5f0ee68634` | `ab604005ab778f49bd2affc8cc5fd187dbd5c083cc2d003d6a487db691114cdf` |

The second run owns the first as predecessor. This small contract fixture is
not a large-workload timing or speedup claim. Final review also proved that
partition identity cannot move during incremental UPDATE and that nullable
operational Norms fall back to the original canonical rejection path.

Integration failures were corrected at their affected boundaries: nullable joined
row locking; input reference resolution before the new manifest exists; retained
capture metadata during atomic output replacement; the old blanket current-row
UPDATE denial; certified-handle lifetime; and BOR/BOROA source/prepared verifiers
which rejected the new ingestion watches. Report guards now separate only watches
whose complete binding roster and exact function body independently verify; all
original report guards/functions still require exact equality.

Compact final evidence belongs under
`D:/freshvcf-build/evidence/ingestion-m3-20261021`.

## Operator and release boundary

The existing `vf.ps1 csv-init` and `vf.ps1 csv-day YYYY-MM-DD` interfaces and their
installation/sample/daily separation stay unchanged. No operator should patch
an environment file to bypass certification or manually repeat initialization.
M3 source is not installed into the existing loaded instance. The final image,
reviewed data-contract upgrade of that same opening, connected acceptance and
single large April8 performance trial remain M4 and require its separate release.
M3's new owner-reference optimization currently requires a v3 source manifest.
M4 must prove compatibility with the working instance's older v2 initialization
at the controlled same-opening upgrade boundary; that upgrade is not claimed here.

Frontend, MTO, auth, 3005/legacy/unrelated services, the six current working
containers and their loaded data remain unchanged. No benchmark has resumed.
After proof, the owned scratch database was removed with zero connected sessions;
all one-off workers auto-removed. The working opening remains `ebed3913`, input
`27b3893b`, content `9be120d9`, 165 migrations and zero daily runs, with all six
original container identities healthy. Its checkout remains clean at `687adcf`.
The source delivery commit and verified remote HEAD are recorded in the sole
live tracker when pushed.
