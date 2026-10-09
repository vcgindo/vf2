# MDM addition to working 3005: code delivery

9 October 2026. This delivers selective eight-group MDM integration for the
working 3005 application. It is ready for a separate deployment review. Nothing
was deployed to 3005 or 3006. `docs/MIGRATION.md` is the sole status tracker.

## Source and target

The checkout foundation is `88b6eb735754a504dcc466e66ae8d376528d629b`;
family ports are from `25b4fadc19cf5adf86286b3f04c3f54690ffe5e7`.
`051229d9f240b67becde0d55e2cb8057cb9ead5d` is reference only.
The running 3005 preservation baseline is image
`1192c35d8d1789dc1d2dc8a240ad71b2afc43eb2fd54b5e753730c10c85ad9ed`,
database `test_freshvcf_stage2_vm_20261003_002`, MTA migration0052,
fixture run `bfd75b4b-a9df-4a08-82d3-852e3324b623` (7 April2026),
and installed MDM families1–3. It has no selected accepted DAILY_CHAIN source.

The deployed checkpoint is d17925c;481 of485 inspected deployed files match it
after line-ending normalization. Its four differences are retained in the source
comparison. The foundation is not assumed to equal that deployment:111 files
differ. Named fixture dispatch/read paths were reconciled, including the absent
Buffer metadata-batching experiment. No working reader was rewritten.
The exact code/source/hunk identities are in
[the delivery manifest](evidence/MDM_3005_CODE_MANIFEST.json).

## Included code and preserved behavior

The added groups are SOB, MOQ, StopPIPO, shared Phase controls, Seasonality and
Force alongside the existing SKU, Location and SKU–Location workflows. Native
master IDs1–13 retain their dispatch, typed queues/current/history, drafts,
review decisions, scopes, downloads and configuration. These are grouped business
flows, not thirteen independently onboarded production sources.

Family capture and finalization use the existing single day boundary, source
lock, own predecessor and typed input tables. Frozen source identity and roster
checks remain strict. Finalization uses actual calculated output and the same
transaction as persisted closing state. This delivery executed no business day.

| Boundary | Preservation/proof |
|---|---|
| Existing families1–3 | Exact seeded owner and typed-row upgrade comparison; current, draft, actor/scope, review and delayed approval workflow tests. |
| BPR/BTR/Guided/Planning | No product reader edits. PostgreSQL typed-value differentials cover BPR grids/counts/analytics, BTR fixture SQL, Guided current/history and Planning source SQL. |
| DBM/Norm0–2, suspension, ordering, Pick and Apply/Sleep | Calculation/command modules unchanged; family-only native input validation and capture seams retained from the source port. No new runtime acceptance claim. |
| SQL access, auth, frontend and MTO | Existing code unchanged except MDM route wrapping and one seasonal graph route. Gateway authentication/payload checks remain outermost; family routes run under the source lock. No browser/performance claim. |
| Operational files, completion, backup, alerts and recovery | Foundation code retained. No combined3006 policy, receipt compatibility, publication-order repair, bootstrap or restore exception imported. |
| Source receipts and typed state | No historical receipt rewritten. Family-specific input paths preserve NULLs, duplicates, ordinals and revision guards; existing text-vehicle mapping stays first. |

## Schema and verification

Family migrations0082–0101 and the foundation's operational0082–0102 remain
byte-identical to their respective Git sources. Empty0103 joins these two leaves;
it has no operations. Combined3006-only0104/0105 are excluded.

New exclusively owned database `fresh_mdm_3005_proof_20261009_001` used the existing
isolated PostgreSQL resource. A real fresh migration reached0052, representative
component rows were inserted, and a real upgrade reached0103. Full rows from the
source, family receipts and SKU/Location/SKU–Location typed tables matched exactly,
including duplicate occurrences, NULLs, zero and decimal values. This is a
representative migration proof, not a copy or full rehearsal of the serving DB.

- Django check, migration drift check and migration plan passed.
- 48 PostgreSQL capture, finalization, revision, rollback and ownership tests passed.
- 88 reader, family dispatch and workflow tests passed, with no skips.
- Nine host runner/configuration tests passed with mocked execution dependencies.
- All387 pinned baseline resources remain unchanged; this is identity verification.
- Independent bounded source review found no actionable defect.

Evidence root: `D:/freshvcf-build/evidence/mdm-btr-integration-20261009-001/target3005`.
The hash index covers the terminal logs and exact package. It retains the failed
setup field-name attempt, missing test-fixture/host-path attempts, the stale BPR
test-message failure, and the pre-correction0105 proof. None is represented as a
successful test. The BPR test now expects the existing rejection text; product
behavior did not change. The earlier unshipped Buffer experiment tests were not
used to require a reader change.

## Isolated proof commands

These steps use the already-created owned proof database and package. They do not
target either serving database. Execute steps1–3 in order for a focused recheck;
stop on a nonzero exit. Do not run the one-time database setup scripts again.

1. In PowerShell at `F:/freshvcf`, set the proof compose path:

   `$proofCompose = 'D:/freshvcf-build/evidence/mdm-btr-integration-20261009-001/target3005/compose-reader.private.json'`

2. Run `docker compose -f $proofCompose run --rm --no-deps worker check`.

3. Run `docker compose -f $proofCompose run --rm --no-deps worker makemigrations --check --dry-run`.

The exact bounded test commands, fixture bindings and logs are retained in
`resume_proof.py`, `corrected_reader_proof.py` and `reader-workflow-corrected.log`.
Those scripts document the completed acceptance; they are not deployment steps.
Worker limits remain4GiB/2CPU, restart=no, no host ports; PostgreSQL remains1GiB/1CPU.

## Remaining deployment and input limits

1. This commit adds code and schema support. A separate reviewed release must
   authorize packaging, backup/rehearsal, migration and deployment to3005. No
   running schema, source, grants, credentials, selection or service was changed.
2. The running three-family fixture is not an accepted same-source DAILY_CHAIN
   owner. New optional owners and an integration seal were not installed. Existing
   configuration exposes installed families only; code support does not activate
   the remaining menus or fabricate eligible inputs.
3. Positive Force/Seasonality ownership remains gated. Their historical fixtures,
   supplements and approvals cannot be transferred or combined implicitly. General
   onboarding is not supplied by this delivery.
4. Retain the native family limitations in the imported contracts and
   LEGACY_EXCEPTIONS, including Phase master9 completion, source-bound Force and
   Season eligibility, native ordering/NULL/duplicate behavior and residual MOQ/
   retail route coverage. Existing qualified parity and blocked routes remain.
5. Changed adapters and code identities require exact admission/revalidation at
   any later activation. Old seals remain immutable. Browser, full-data upgrade,
   concurrency under serving load, new dates and performance were not tested here.

Delivery ends after the single cohesive commit, push and upstream hash check.
No automatic deployment, next goal, source installation or temporal continuation.
