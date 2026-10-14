# Request26: location publication and one explicit adapter transition

**Proposal for controller review; retained C05 execution remains on hold.**
Status is recorded only in `F:/freshvcf/docs/handoff-3005/TRACKER.md`.
Request25 is complete at pushed checkpoint8b1016e. Request26 has not been
submitted, and day3 has not run. No transition has been registered or activated.

## Exact problem

The deployed master2 Add path writes attributes/descriptions to Importer, BPR,
BTR and DBM, then completes the task and clears its queue. Modern
`location_tasks.approve` omits those effects. The separately authorized immediate
correction needs its own source/task/request/history/queue-backed INSERT guard,
with the same statement, duplicate, NULL, ordinal and failure boundaries already
proved for SKU. The SKU guard must remain separate.

The next-day gap is also concrete. `daily_current.closing_owners` calls the
installation `owner_batches`, which emits location rows only for Importer.
For LP002, canonical BPR and DBM imports copy the validated Importer rows; c4–c15
therefore become empty strings on July3. Merely adding the missing synchronous
publication would leave the consumer current rows at NULL. `master_owners` is
part of the initialization digest and `daily_current` is part of the adapter
digest. The original integration seal rejects a changed adapter.

The proposed correction does **not** change `master_owners`, the opening image,
initialization digest, engine formulas, inputs, date policy or accepted runs.

## Closing projection component

The unwired `mta/mdm/location_projection.py` returns six additional partitions of
the two existing MDM location models. The existing Importer partitions stay in
the old projection. It performs no database writes and has no production caller.

| Owner | Attribute/description source | Required boundary |
|---|---|---|
| BPR | Complete `closing.importer` location bags | Preserve every field, NULL, duplicate and source occurrence order |
| DBM | Complete `closing.dbm` location bags | Require complete bag equality with Importer; preserve DBM source order |
| BTR | `closing.btr` location bags | Use the already computed BTR population, including empty; never substitute Importer |

Canonical BTR import refreshes from BPR, then retains only locations present as
child or parent in retained BPR history. LP002 is outside that population in the
frozen case and must disappear from the BTR current projection on day3. BTR also
has `WhType`, `IsChild`, and `IsParent`, which the existing MDM base-attribute
model does not contain. The proposed explicit mapping keeps those three fields
in their existing typed BTR closing table and binds its **complete** field roster,
row count and source digest in the new projection receipt. It projects only the
existing MDM model's base fields. Unknown extra columns, missing derived columns
or incorrect derived types fail. This mapping needs controller approval; it is
not a claim of full BTR-table acceptance or permission to hide those fields.

Four pure component tests pass: full values/NULLs/duplicate order and BTR subset;
unknown/missing/type denial; DBM missing-duplicate and NULL/empty denial; and an
explicitly empty BTR bag. They leave component database values unchanged. They
do not prove publication, transition authorization, rollback, migration or C05
execution. No existing runtime file has been changed for this proposal.

## One transition, not an accepted-digest list

Use exactly one immutable registrar-owned row in this owned database, for this
source and effective boundary. Do not make the application owner capable of
issuing its own compatibility approval. Follow the existing namespace registrar
trust boundary, without changing its original registration or verifier.

The proposed relation is `mta.native_location_transition`, owned by the existing
namespace registrar, with SELECT only for the existing issuer/consumer as
appropriate. Using the existing `mta` schema avoids changing the frozen namespace
ACL verifier's special allowance for `fresh_control.owned_namespace`. Prove the
actual resulting ACLs against the unchanged verifier before any retained use.
Registrar DDL/registration is a separate reviewed operation; the application
migration must not mint this row. A singleton constraint and immutable update,
delete and truncate guards prohibit chaining another transition through it.

The exact registration record must contain:

| Field | Required value or binding |
|---|---|
| transition/version | A fresh UUID; exactly `native-closing-locations-v2` |
| database/namespace | Existing database OID/name and original namespace registration UUID |
| source | `af2288263b7938d0e177092406ace5a5ac6fe9bc8801a1892d4ffb860cc70c81` and its physical source ID |
| initialization | `c5fe5b52-2f7e-4081-bf68-bc46a6584d72`, unchanged seal/content/configuration digests |
| old adapter | `2c68c72139980129723b1faa65f173d614e66979ac5ac67ff38ec29066c71ee6` |
| old source manifest | Frozen request25 runtime manifest `38924a0f54418d2477b6cefc82097988580f004bd848793a8ff14303e60909ae` and its archive/hash |
| new adapter/source manifest | Exact hashes calculated from the final reviewed implementation; not yet assigned or registered |
| boundary predecessor | `388a7810-ad96-4473-9104-8accb48f95b3` |
| boundary predecessor output | `f116c2581e0c8e9539fc19d6043a5d7580afbeacda6343c78a4c8b28f278384a` |
| first effective day | `2026-07-03`; component design is bounded to the remaining frozen C05 chain |
| old accepted prefix | Exact day1/day2 run IDs and original receipt/readback hashes |
| review evidence | Exact expectation amendment, code diff, component proof and controller release hashes |

Registration must be a literal reviewed old-to-new record, never “register
whatever code is currently installed.” Under the existing source lock it checks
that day2 remains the unique successful leaf, no day3 or successor attempt
exists, and the recovered request25 state is unchanged. The new manifest is
created **after** the final code is fixed; it is not embedded into the files it
hashes, avoiding a self-referential hash. The registrar binds its exact reviewed
hash. Ordinary issuer attempts to insert/change a registration must fail.

## Admission and verification rules

1. Keep the original initialization/source/family seals and namespace registry
   untouched. Reconstruct the original adapter digest from the exact original
   path-to-file-hash manifest and verified retained archive; do not execute old
   archived Python or accept only a supplied digest string. Require the current
   initialization implementation digest to remain exactly unchanged.
2. Reconstruct the original integration receipt with that verified old adapter
   identity and compare it in full to the stored receipt/digest. Continue all
   existing family/configuration/ownership checks. This branch is available only
   when the one exact registrar record passes every check.
3. Separately hash the complete installed new source manifest, including every
   new transition, projection, model, migration, receipt and command file, plus
   all existing adapter paths. Compare every hash and the resulting new adapter
   digest to the registrar record. No omitted files or arbitrary allowed values.
4. Before daily execution, require either the exact day2 predecessor/output for
   July3, or a successful descendant carrying this same immutable transition
   receipt. Reject another source, initialization, date, predecessor, branch,
   runtime or transition. A missing registration must retain the existing strict
   mismatch denial; it must not silently select the new behavior.
5. Read-only verification of the two pinned old runs uses the **old** projection
   recipe. Live-leaf verification uses the leaf's recorded version. Never use
   the six new partitions to recertify old days. A new successful run without its
   required v2 receipt fails verification; absence does not imply v1.

## New per-run identity and atomicity

Add one small managed `MdmClosingProjectionReceipt` table, keyed by `run_id`,
with transition UUID, version, source digest, adapter/source-manifest hashes,
capture identity and bounded partition/source metadata. Link source ownership
through the run's existing capture; do not copy business state into JSONB.

Inside the existing `finish_run` transaction, after consumption and before any
current-location replacement, `daily_current.publish` validates the run against
the transition and creates its owned pending receipt. It publishes the original
partitions plus the six location partitions, verifies complete rows and exact
ordinals, and seals the receipt once with the complete partition/source digests.
All current rows, receipt, queue consumption and calculated output roll back
together on failure. No new surrounding transaction changes approval semantics.

An additive database guard on the two location models must require this owned
receipt for post-boundary **daily** writes when a transition is registered.
The separate approved synchronous Location Add branch stays distinct. This
prevents an older application binary from silently publishing old daily location
semantics after activation. Bootstrap, SKU authorization and other tables retain
their existing rules. The pending receipt must match a real consumed RUNNING
capture and the fixed transition, not merely a caller-set marker.
Enforcement must also cover zero-row daily DELETE statements; a row trigger
alone cannot prove that boundary. The component proof must exercise it explicitly.

`receipt_integrity.source_receipts` includes the sealed new receipt only when
applicable, so new output identities bind it and old source-receipt maps remain
unchanged. Reading old runs must not create/backfill any receipt.

A failed day retains its original failed capture and no committed projection
receipt/current replacement. Its retry must have the same frozen request, source,
parent, transition UUID/version, new source manifest and adapter identity. It
must also use a **distinct `execution_revision`**, as the existing retry contract
requires; the attempt identity is separate from the unchanged code identity.
Changing either frozen provenance or the required distinct-attempt rule is denied.
Registration itself remains immutable across failure/retry. No accepted day is
replayed. Reverting application code after registration must fail closed.

## Minimal proposed integration diff

These edits are **not applied**. The unwired projector/tests are the only current
component changes. Final implementation and exact hash manifest remain review
items before any retained registration or execution.

| File/boundary | Proposed edit |
|---|---|
| `mdm/location_tasks.py` + dedicated statement helper | Canonical master2 synchronous eight INSERTs, completion and queue clear; preserve existing approval/denial/partial-failure sequence |
| additive location guard migration | Separate master2 exact row validation for two location models; retain SKU/day/bootstrap protections |
| `mdm/production_families.py` | Add only the exact old/new manifest transition branch to integration validation; hash all new relevant files |
| new `mdm/location_transition.py` | Read and strictly validate the one registrar record, manifests and prefix/descendant boundary |
| `mdm/daily_current.py` | Explicit versioned closing projection, receipt and full-row verification; preserve v1 historical recipe |
| `runtime/production_daily.py` | Check the exact transition/predecessor before invoking unchanged `execute_day` |
| new receipt model + import + additive migration | Owned pending-to-sealed run receipt and immutability/daily-write enforcement |
| `runtime/receipt_integrity.py` | Bind the new receipt into applicable new run source identities; no empty-key addition to old maps |
| isolated registrar operation | Reviewed table ownership/ACL and exact immutable one-row registration; no original registry update |
| focused tests | Real migration, approval, admission, old-run identity, transaction rollback and frozen retry proof |

No changes to `initialization.py`, `master_owners.py`, `owned_namespace.py`,
`temporal.py`, `services.py`, engine modules, original migration files or stored
seals are proposed. If integration cannot respect those boundaries, return the
exact dependency for review rather than expanding them.

## Exact expectation proposal and remaining proof

External directory `c05-request26-proposal-v1` preserves the original frozen
files and contains separate candidate files and recursive diffs. Proposal SHA:
`a331e10a27940c446b68db3ccaca68e0abb85225a1942b3d24d8a540a4f7cedb`.

It changes five immediate paths: task status1→7, subtask2→4, DBUpdatedDate
NULL→`03/07/2026 08:01AM`, approved-queue append→empty, and the added eight-row
synchronous expectation. Importer ordinals are20; BPR/BTR/DBM ordinals1, derived
from frozen day2 bags and the original installation/publication contract.
Eight July3–10 retained DBUpdatedDate values change from12:00PM to08:01AM.
All requested/history/audit rows, facts, actions, dates and other expectations
remain byte-value identical. A proposed workflow-checker diff adds exact master2
model/queue handling; it is not installed or executed.

Before C05 may continue, prove migration and registrar ACLs, exact original and
new manifest verification, arbitrary-code/source/predecessor denial, actual
Location Add eight rows/denials/completion, old receipt/readback identity,
post-boundary receipt/source hashing, injected late rollback, frozen retry and
old-binary fail-closed behavior on the existing component database. None of those
transition proofs are claimed by the four pure projector tests.

After controller review of the final diff, exact manifests, expectation amendment
and component proof, obtain the separate retained-upgrade release already required
by the tracker. Only then register, submit request26 once, run remaining frozen
day3 requests, and calculate day3 from388a7810. Keep3005 unchanged; stop beforeS3.
