# BTR daily reporting layer: prepared next intervention

Requested by the human on4 October2026. Planning only: this document does not
authorize storage implementation, serving changes or a second active work queue.
Status belongs only in docs/MIGRATION.md. Finish or explicitly disposition the
current benchmark dependency before opening this intervention.

## Decision and boundary

Assess a BTR-specific, typed, publication-bound reporting projection while keeping
accepted engine state authoritative. Compare the accepted reader with a narrow
selection/join-reference structure first; test full prejoined serving rows only
if the narrow design leaves measured repeated work. Adopt the simplest design
that preserves outputs and meets matched heavy-VM legacy performance gates.
No general report framework, DBM/workflow redesign, engine change or F2 replay.

Both Physical Inventory and Dispatch are required. Count, grid and export may need
different relations because their native join semantics differ; they share one
generation identity, not an artificially unified row definition. Retain duplicate
source identities, NULLs, full filter fields and defined ordering. A SKU/location
pair is not assumed unique. The rejected key-prefix optimization's tied-row
failures are mandatory adversarial cases, not permission to invent a tie-break.

## Daily refresh contract

Align refresh with the existing successful daily calculation/publication cycle,
not a new timer, hourly refresh or per-request rebuild. execute_day remains the
sole production calculation boundary. After the day's authoritative output has
committed and passed existing admission, build the corresponding BTR generation
from those committed inputs. Reporting construction must not alter calculation
results or retroactively mark a successful calculation failed.

Identify a generation by source kind, run/date, output/input identity and projection
version. Persist typed report rows with source references and duplicate ordinals.
Build privately, validate complete required populations and both branches, then
atomically activate the complete generation. No partially refreshed grid/count/
export mix. Bind related requests to the same selected generation using the
existing run-selection contract where possible; if that cannot provide consistency
across a daily switch, identify the required API/UI contract change before adopting
the design. Do not silently add a frontend token or mix dates.

Failed build leaves the prior admitted generation intact for explicit selection;
never label it as the new day's data or silently serve it for a requested new run.
Expose accurate selected date/readiness through existing contracts. Retry the same
source/version idempotently, retain failed-attempt evidence, and validate existing
completed generations rather than recomputing accepted outputs. On restart resume
or discard only owned incomplete reporting work; never reset engine state.

Retain current and previous complete reporting generations for rollback at minimum.
Historical BTR and retained evidence obligations remain: do not delete old data
merely because two active generations suffice for a rollback mechanism. Define
retention/garbage collection separately before any automated deletion.

Live identity grants and request filters remain read-time authorities. Precompute
stable business joins and scope attributes, not per-user entitlements. Establish
whether any BTR input changes intraday: if so, document its existing visibility
contract and stop before silently replacing that behavior with daily staleness.
Daily refresh is the intended cadence, not permission to conceal live mutations.

Fixture and modern outputs use the same reporting/query contract where equivalent,
with separate source adapters and provenance. The immutable April7 fixture gets
one explicitly built generation for benchmarking; no invented daily fixture replay
or fabricated accepted calculation receipt. Normal retained outputs are functional
compatibility proof, not scale-performance baselines.

## Finite assessment sequence

1. Reuse the verified heavy-data copy, canonical legacy consumer, resource budget
   and measurements from the current BTR task. Do not repeat source discovery.
   Record the expensive work and exact source dependencies for grid/count/export.
2. Specify the narrow typed relation, indexes, source identity, ordering behavior,
   generation lifecycle and expected storage/build cost. Map daily refresh onto
   the existing publication orchestration; no separate scheduling platform.
3. In owned resources only, implement a bounded prototype when implementation is
   explicitly opened. Compare complete results for both branches, scopes, filters,
   horizons, first/later pages, exports and adversarial duplicates/ties/NULLs.
   Preserve the Category alias-order qualification only in its approved fixture
   scope. A failed semantic comparison rejects the candidate irrespective of speed.
4. Measure matched legacy/Fresh API and browser performance on the full VM dataset,
   using the established warm/cold/concurrency protocol and comparable resources.
   Also measure generation build time, peak memory, additional storage, restart,
   retry, atomic switch and rollback. Establish the available daily refresh window
   from the actual schedule rather than inventing a build-time SLA.
5. Decide: retain existing reads, adopt the narrow projection, or adopt a precisely
   justified prejoined BTR structure. Deliver one decision with schema/lifecycle,
   comparative evidence, remaining limits and rollout/rollback boundary. No
   automatic adoption or extension to other report families.

## Adoption gates

Complete correctness and permission proof; Fresh median/p95 no worse than legacy,
throughput at least equal and errors no worse under matched resources; practical
daily build/storage costs; no partial-generation visibility; safe restart/retry
and rollback; functional consumption of normal modern outputs; preserved serving
limits and bounded overlap/login behavior. Missing equivalent measurement remains
UNPROVED. A benchmark pass is not whole-page Stage2 acceptance.

Any later schema implementation requires real migrations, Django check,
makemigrations --check, migration plan and migration-enabled PostgreSQL tests.
No serving3005 rollout, new port, F1/F2 mutation or broader Stage2–5 work is
authorized by preparing this plan.
