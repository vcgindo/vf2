# Ingestion milestone4 — same-opening upgrade and one large daily run

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

21 October2026. **M4 incomplete; operation stopped and user-directed browser pause applies.**
Implementation source `be480eb412ace0e7d86b7dedf396910f0818746e`,
branch `codex/3006-logistics-integration`, following M3 `77d44f1a`.
The sole live status/decision record is `F:/freshvcf/docs/handoff-3005/TRACKER.md`.
This handoff records evidence; it is not a second execution queue.

## Scope

Preserve the existing April7 opening and all original seals; upgrade its ingestion
contract, then execute only the frozen April8 CSV workload:97,097 SKU/location
pairs,2,189 SKUs,235 locations,10,256 established opening orders and necessary
operating state. No inherited daily BPR history, extra date or legacy rerun.
No changed facts, calculation policy, frontend, MTO, auth or production resource
ceiling. Normal installation, master initialization and daily execution remain
separate operations.

## Upgrade and package

- The transition accepts only original commit `687adcf024ea9bffe0c90b3de2bb67e25019ec4a`
  and native manifest `2b7346f3382d78e3ea2d8c352f9854b6f59b5e13cf53d27aa9fa68216f478818`.
  The original image verified complete typed opening/current masters/exclusions
  and all13 families in503.111seconds. Its full audit is retained outside Git.
- The candidate independently verified the exact old catalogue and ten forward
  migrations0144–0153. Upgrade owns one transaction for migrations, finite grants,
  full certification, compatibility receipt and final registrar activation.
  Heavy immutable audit work occurs before the DDL transaction; original seals
  and current masters are rechecked under locks. There is no reseal, register,
  initialize, load or forced hash/config override.
- New admission recognizes the original producer only through this pinned,
  joined activation. New runs record their actual implementation; old source,
  namespace, capability, initialization and integration receipts stay original.
  Physical v2 initialization references retain their original manifest/content
  hashes and use the versioned reader. Run references remain v3-only.
- Focused verification:92tests PASS+5skips,44 additional compatibility tests PASS,
  independent review of origin/authority/atomicity seams and v2 reference tests.
- Built only MTA from the committed export and existing eight pinned Linux
  wheels, offline, without resource changes. Image
  `sha256:cc8db971956c64a1e7a250486ae9ab2dbd94a2837fdb2f72bfb773be494353bf`,
  native manifest `bddc23bcb4fab53a504d1994ee56e0ddee2622e0176b8f69bbd680c4ba7d271c`,
  source export `8c02047a8e44f6f654800f680572bf8610670902491dddd11e229b5855270de0`.
  Actual image source/dependency admission passed; the transition command is
  explicitly included in the finite image roster.

The temporary rollback set is at
`I:/VectorFLOW-benchmark-20261020/ingestion-m4-checkpoint`: a consistent physical
PostgreSQL base backup with WAL, matching MTA files, private secrets/configuration
and operator receipt. `pg_verifybackup` verified file checksums and WAL. This
online physical checkpoint preserved OIDs/roles without stopping auth/MTO's PG
service. No restore was executed. Keep it until successful acceptance.

## Actual acceptance and measurements

The same-opening transition committed successfully. Native transition time was
361.785seconds; the external command observer measured372.819seconds, exit0,
with no guard failure. Certification is
`3cb8d3fcef9acd2e68838cb08f529c793fc97687ba58d43fadf0e190962e4058`.
The original initialization/source/content/namespace/capability receipts and
typed data were preserved. All175 migration records are present.

The upgraded MTA admitted all13 master families in1.4988seconds/68queries with
zero opening-image reads (the test actively denied such reads). Existing private
metadata endpoints retained their gateway-identity denial. The source-side
onboarding receipt was reconciled to READY without loading data or changing its
original initialization provenance.

The soleApril8 CSV operation stopped at its existing120-minute deadline. Attempt
`819ffecb-ffc1-4284-94fc-d4b81a8d515a` sealed its accepted input batch as
`VALIDATED`:97,097 daily rows,7,661 non-NMS master rows,333 order rows,
12,671 order-feed rows and216 stock overrides. The remaining frozen feed and
optional consumer groups are empty. Native preflight/bootstrap passed in
266.895075seconds. Input capture then committed in2151.978705seconds
(35minutes52seconds), and calculation began for
`383104fe-3cf8-4666-bbe1-5156e767d0d7`. Its input root is
`652680b13c8260b5dcdd753338f1adcd96a14583ce4be6ff72e612a16fa2f116`.
Calculation did not return before the bound. There is no committed calculation
result, output checkpoint, report generation or UI publication.

The committed v3 capture contains28 physical populations/204,906 rows,
11 immutable references to the accepted fact batch and two direct references to
the original v2 initialization's opening/profile. Those two references retain
the original manifest `87cab144` and content `9be120d9`; no opening was copied or
resealed. Physical populations include97,464 prepared raw-master rows and97,097
MDM SKU/location attribute rows. Raw daily97097, prepared master97464 and eventual
calculation populations are distinct counts, not interchangeable throughput units.

This first-day/root case has no computed predecessor and includes the frozen
non-NMS feed. Its capture explicitly records `qualified_master_reuse=false` and
uses the complete canonical producer. Do not claim that this trial proves the
qualified unchanged-master/successor speedup; M3's focused root/successor proof
covers that separate boundary. The substantial physical capture cost remains an
actual performance finding, not an optimized-away cost or CSV parsing time.
During calculation the database connection was observed idle outside a
transaction. The command observer terminated the worker after its deadline;
Docker recorded SIGTERM, then SIGKILL and exit137. No Docker OOM event was
observed. This is a controlled interruption, not an observed calculation
exception or a completed-day timing. The exact internal calculation bottleneck
is unproved because the existing log reports the calculation phase at return.

| Boundary | Actual result / time |
|---|---|
| Original-image full opening/family audit | PASS503.111s; separate maintenance proof |
| Forward upgrade / certification | PASS361.785s native,372.819s observed command |
| Certified master readiness | PASS1.4988s,68queries,zero opening-image reads |
| CSV stage and transition to execution | About619.6s between the two worker starts; includes transition, not a pure parser timing |
| Native preflight/bootstrap | PASS266.895075s |
| Prepared input capture | Committed2151.978705s |
| Calculation | No return after at least4154.399854s (69m14s), measured to the stop request |
| Whole daily operator | Interrupted7216.485379s (120m16s), exit1 / deadline guard |
| Output commit, reports, selection, downloads and UI | Not reached / unproved |

The Docker host exposes16 CPUs and16,594,960,384 bytes of memory. Both workers
had CPU/memory limits0; no benchmark resource ceilings or host increase were
introduced. Sampled container peaks were1.198GiB for staging,7.349GiB for native
execution and1.328GiB for PostgreSQL. Calculation typically used approximately
one core. Other working frontend/auth/MTO/Redis services remained present in the
samples; these are observed timings, not an isolated hardware capacity guarantee.

Post-stop reconciliation proves the same original initialization and all five
original seal/hash fields against the pre-upgrade audit,175 migrations,one run,
zero output checkpoints,zero UI publications and a CAPTURED,unconsumed MDM input.
No database clients/transactions or daily workers remain. The database run and
feed-attempt headers still say RUNNING/VALIDATED; these are interrupted records,
not evidence of a live process. They were not rewritten or retried. MTA remains
stopped in maintenance; the original five other services remain healthy with
the same container identities. No new database, master load, image or date was
created after the stop.

Compact actual command logs/resources are under
`D:/freshvcf-build/evidence/ingestion-m4-20261021`. The repository operation is
`I:/VectorFLOW-benchmark-20261020/current-operations/20261021T024435654-e49dd6e50d314744bd6bce77e487f06b`.
The compact final evidence is `terminal-proof.json`, `daily-measurement.json`,
`capture-proof.json`, `native-worker-checkpoint.log`, resource samples and the
operation's `commands.log`. The terminal proof preserves the successful
post-stop Docker event receipt; Docker's bounded event cache later evicted it.
After a Codex restart, reconcile this stopped operation before any execution.
No automatic calculation replay, master reload or deadline extension is released.
Publication-only `-Resume` requires a SUCCEEDED run and is inapplicable here.

Browser control was checked again after the stop and still reports disabled.
The user says restoring it requires an app restart and directs a pause at that
boundary. Execution is paused at this preserved checkpoint. Browser availability
is an additional outstanding condition; restarting Codex will not resolve the
uncompleted calculation. M4 remains incomplete. The single physical rollback set
and original rollback image remain necessary until acceptance; no extra failure
stack or worker was retained.

The original blank-install receipt identifies this clean benchmark installation's
administrator as `benchmark-admin@vectorconsulting.invalid`. That account remains
active. It was not installed as `admin`/`admin@vectorconsulting.id`; the auth,
frontend and MTO container identities and credentials remain unchanged.

## Operational boundary

For routine production use, the existing command stays `./vf.ps1 csv-day YYYY-MM-DD`.
Masters are initialized once; a successor uses its own persisted predecessor and
that date's CSV facts. Do not rerun `csv-init` after a daily failure.

The low-level `release.upgrade_ingestion` command is a restricted maintenance
transition for this known baseline, not a generic upgrade or ordinary daily
operator step. It requires the independently verified original audit, original
database/role identities, maintenance exclusion and a trusted provisioning
session. An unknown origin or unsupported migration prefix stops without activation.
An atomic failure rolls back; an already committed matching transition is checked
without reloading/reissuing certification. An old image must not be started over
a committed incompatible schema; recovery requires the retained complete physical
set and matching original files/configuration/image under explicit operator control.

Saved legacy timing remains qualified context: inherited history and split-phase
execution prevent an apples-to-apples whole-day speedup claim. This trial measures
the fresh-start modern workload. Public deployment and capacity guarantees for
larger workloads are outside this acceptance.
