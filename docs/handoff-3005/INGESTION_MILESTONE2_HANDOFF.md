# Ingestion milestone2 — one-pass initialization and typed storage

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

21 October 2026. Delivered on `codex/3006-logistics-integration`, based on
milestone1 `81071f22d78776b703b41265d58430e2b899a1e1`. The sole status/decision
tracker remains `F:/freshvcf/docs/handoff-3005/TRACKER.md`. This document records
the implementation and proof; it is not another work queue.

## Delivered behavior

- `vf.ps1 csv-init` retains its existing operator interface. One image-owned
  process, `release.initialize_csv`, reads the CSV pack and runs the complete
  native validator once. The private, single-use preparation object transfers
  the normalized opening and master projections into initialization. Invalid
  inputs retain the detailed preflight diagnostics; there is no public skip flag.
- Normal onboarding no longer automatically invokes validate-only, inspect,
  initialize and a separate family bootstrap over the same input. Those explicit
  low-level commands remain available. The JSON/CSV management initializer keeps
  its base-initialization contract and shares the same preparation owner.
- Opening snapshots, live initial masters, exclusions, all thirteen MDM families,
  integration seal, certification and initial master revision commit together.
  One final exhaustive audit derives its expectations independently from typed
  PostgreSQL rows after clearing prepared caches. It checks complete current
  masters, exclusions, family bags, duplicates, order and provenance.
- Registrar activation is a separate final trusted transaction. Only the exact
  current native release can activate this fresh certificate. Installer and
  runtime cannot forge registrar authority. No existing role or credential is
  changed by the new process.
- Explicit resume reconciles the recorded pack, database/OID, namespace,
  implementation, configuration and input. It also handles a process dying
  between a database commit and receipt write. A lost opening checkpoint receives
  an independent full persisted audit. Already certified/recorded openings resume
  activation/configuration/serving without parsing CSV or loading masters again.
  Unknown or consumed ownership stops; there is no automatic reset or day replay.

## Versioned storage

New initialization snapshots use `fresh-daily-input-manifest-v3`; default daily
storage stays v2 until its separately scoped integration. Old v2 manifests keep
their original reader and digest meaning.

V3 stores a uniform row shape once instead of writing one shape row per record.
Mixed shapes and nested children retain explicit shape/link ownership. A finite
same-opening alias map can share settings or description images only after exact
typed, ordered equality. Different populations remain separate. Reads bind the
manifest to the actual database name/OID, source and immutable owner UUID, reject
dangling/chained/foreign/mutable references, and reconstruct the full logical
input. There are no cross-day references, generic JSON state payloads or new
business defaults. No schema migration was added in this milestone.

## Proof

74 distinct affected unit checks passed across preparation/diagnostics,
initialization contracts and CSV, v2/v3 typed readers, large current/history
collections, authenticated source exports, and the real launcher under Windows
PowerShell5.1 and PowerShell7. The additional large v3 uniform test checks a
reiterable 10,001-row population with one physical value image and no shape image.

One disposable database, `vf_ingestion_m2_20261021`, on the existing owned
PostgreSQL received genuine migrations. A real scoped-credential PostgreSQL test
passed registration, exact typed opening/all13-family completion, final-audit
rollback, family-write rollback, base-only checkpoint completion, both
commit-before-receipt recovery cases, activation idempotency and certified
re-entry. Its normal successful acceptance used one current-master audit and
**162 distinct typed image reads with no repeated image read**. It created zero
daily runs. Runtime readiness was checked without an opening scan.

The PostgreSQL fixture substitutes only a declared native source identity because
this milestone deliberately does not build an image. It uses the actual
registration, native guards, typed writer/reader, installer credential, family
producers, certification and registrar activation. Source-file authentication has
separate focused negative/export tests. This proves the changed source boundary,
not final image installation or large-dataset throughput.

Django system check, migration drift check against PostgreSQL, Compose boundary
resolution, compilation and diff whitespace checks passed. The Compose check
confirms the existing MTA data volume, matching independent native source pins,
read-only root and no new ports. Independent review found and resolved prepared
cache leakage into certification, two crash receipt gaps and invalid atomic
readiness re-entry. A follow-up review found no residual defect in those remedies.

Focused results are under
`D:/freshvcf-build/evidence/ingestion-m2-20261021`. The proof database was dropped
afterward; its sessions and all `--rm` proof containers are gone. No image was
built, copied or retained for this work.

## Preserved state and delivery limit

The six working containers retain their original IDs and are healthy. The loaded
opening `ebed3913-8e83-4da2-ae07-0c02f3b0beca`, input
`27b3893b0f8a0f0db0197439c760677e9dc6dca07ad00f26fc4297781dd57a70`, content
`9be120d9971642698f1dd90c0ff5e218adb7e4bfc837ce9359906515d45bae59`,
165 migration records and zero daily runs are unchanged. The working deployment
remains at `687adcf`; milestone2 was not installed over its source-bound opening.
3005, legacy, unrelated projects, frontend, MTO and auth remain untouched.

Milestone3 accepted facts/master-context integration and milestone4 final image,
supported existing-opening upgrade, connected acceptance and the sole April8
trial remain outside this delivery. No daily benchmark or next milestone starts
automatically.
