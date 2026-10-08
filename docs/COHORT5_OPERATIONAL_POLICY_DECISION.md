# Cohort5 consolidated operational policy decision

Approved exactly by the direct human reply on 9 October 2026:
"Approve supported-synthetic-operational-v1 exactly as documented. Implement and
prove A2–A4 within the existing Cohort 5 goal." No additional omissions are allowed.
MIGRATION.md remains the only tracker. This proposal authorizes no calculation,
legacy run, consumer campaign, backup/restore, serving change or real input run.

## Approved decision

The approved separately named policy `supported-synthetic-operational-v1` requires
all requirements below. It is operational integrity acceptance, **not independent
legacy parity or canonical full-batch completion**. Missing any requirement denies
acceptance. A separate explicit operational-policy setting is required; it must
not overload the existing Cohort3 consumption-policy setting. Blank operational
policy keeps the current independent-parity default; the old
Cohort3 two-owner policy and its exact source supplements remain separate.

1. **Exact supported domain.** A SUCCEEDED DAILY_CHAIN must bind its registered
   frozen synthetic artifact, full input/profile digest, execution revision,
   output/production manifest, native typed closing state, exact MDM source and
   installed three-family receipts. Use existing registration/binding validators;
   do not introduce arbitrary production input registration or new hardcoded run
   UUIDs. The current installer recognizes only its existing
   `block3-sizeable-input-v1` artifact pin (`daily_source.ARTIFACT_SHA`), also
   registered in baseline/manifest.json. This proposal does not expand that
   installer or claim the existing artifact already supplies every required
   finalization/source population. Missing bindings still deny; a later input
   acceptance proposal must resolve that concrete input gate. Require
   `generic-finalization-v1`, explicit inactive NMS, the existing
   `cohort2-integrated-materialization-v1` operational roster and
   `core-without-bor-v1` presentation roster. Unsupported client/profile sources,
   active NMS or populated SOB/MOQ approval queues deny. Declared empty populations
   must have actual typed owners and matching frozen provenance; absence is not
   empty. Existing opt-in/source qualifications do not automatically transfer.

2. **Native completion qualification.** Preserve `IsBatchFileExecuted=0`,
   `parity_summary` and every canonical flag row unchanged. Reuse
   `daily_finalization.verify_successor`/`finish`: exact pinned flag roster;
   explicit `NMSActive='0'`; BPR completion='1'; current business-date stamp;
   every enabled critical script complete. Only `NMSImportData.sql` and
   `NMSClearInputTables.sql` may be skipped critical scripts, and both remain
   false. Record `inactive-nms-critical-flags-remain-false` in the acceptance
   qualification. A different false critical flag, missing setting, stale date,
   changed roster or inconsistent lineage denies; never relabel native0 as PASS.

3. **Own predecessor and actual actions.** First date must have its explicitly
   bound opening and no predecessor. Each successor must consume its own exact
   preceding run and operational predecessor, verified closing/opening identity,
   date chain and ordered real action digest/before/after chain. No copying another
   engine's state or manufacturing Apply/Sleep. No prior operational receipt may
   be inferred from a publication: require a valid receipt under this policy for
   a successor's operationally admitted predecessor. Action drift invalidates
   acceptance. Initial serving under this policy has actions disabled; existing
   already-applied actions are verified, not omitted.

4. **All enabled operational effects.** Bind one explicit SUCCEEDED operational
   attempt for the same run/date/output/configuration/source/actions/predecessor.
   Require the exact nine-group O1–O9 roster and all required operations SUCCEEDED.
   Reuse `validate_configuration`, `verify_attempt` and their native population,
   expected file/member, history, fourteen local alert disposition and backup
   receipt checks. Explicitly bind any verified repair lineage and its original
   receipts. No DISABLED/UNAVAILABLE/empty group may stand in for an enabled
   critical group. Preserve existing narrow CSV/ZIP/eleven-CHECK restore
   qualifications; reject every unapproved difference. No external alert-delivery
   claim, new repair or new backup/restore is authorized by acceptance.

5. **Actual sources and all eighteen layers.** Require native typed sources,
   source receipts and complete readback for the existing required report domain:
   dbm_sources, bpr, btr, planning_sources, planning_grids, planning_charts,
   planning_custom, planning_git, planning_expedite_grids,
   planning_expedite_custom, planning_expedite_transit, planning_expedite_charts,
   rrr, history, research_availability, guided_history, guided_dbm and
   guided_chronic. Require READY seals and actual `verify_layer` checks plus native
   output/projection verification; caller-declared READY is insufficient.
   Remarks and expedite requests require their real run-owned capture receipts,
   including explicit zero-row captures where applicable. No transfer of Cohort3
   presentation-only empties or terminal supplements, no historical backfill and
   no use of another day's source. Existing history coverage limits remain.
   BOR/BOROA remain excluded. The approved order-fulfillment custom and combined
   GIT-child 503 contracts remain explicitly blocked; their sealed diagnostics
   are not positive route acceptance and must stay disclosed in the policy.

6. **Exact access and coherent selection.** Require the retained catalogue and
   explicit run-bound hierarchy using existing access/attribute conflict checks;
   no new grants, inferred NULL access or changed scope. Bind the unchanged
   publication seal, access activation, configuration digest and exact BTR
   generation. One explicit policy/run/output/generation/receipt tuple only:
   no latest fallback, mixed generation, fixture-policy mixing or global bypass.
   Selection checks emit values only after full verification. Startup rechecks
   the receipt and required native validators; per-request identity detects
   bound identity drift and denies service. A failed candidate cannot modify
   serving configuration or the prior valid selection.

7. **Durable verification evidence and retry.** Add a typed, immutable run-bound
   operational acceptance receipt through the existing Django model/migration
   path. Bind policy/validator-code identity, input/profile/revision/output,
   predecessor/actions, operational configuration/attempt/repair identities,
   source receipt, publication/layers, access activation and BTR generation.
   Bounded metadata may contain digests/qualifications only, never state payloads.
   Issue only after complete verification and before/after identity agreement.
   Exact retries reverify and reuse the same receipt; changed tuples deny rather
   than replace it. Database guards must reject invalid status/owner/lineage and
   immutable receipt edits. No user-supplied verification result or forged parity.

## Implementation and acceptance limits

The smallest design extends existing selection/startup checks with an explicit
operational mode and a verified typed receipt. In one atomic transaction, lock
the run/publication/operation/repair owners, perform full pre-activation native,
seal, layer and access verification, and compute the deterministic expected
activation digest. Insert the immutable receipt bound to that digest, then insert
the matching activation. The activation database guard must join that actual
receipt and compare the complete tuple; a caller-set policy flag alone is never
authority. A failure rolls both inserts back. An exact retry reverifies and reuses
both rows. Selection requires both committed rows. Pre-activation verification
uses the existing direct seal/layer/access checks and must not recursively require
an activation or make a final receipt a prerequisite of publication preparation.
Existing strict and exact two-owner paths remain unchanged. Code/version drift
fails closed; no silent resealing of accepted rows.

Proof in this cohort uses focused owned persistence/validator fixtures for the
positive receipt path, omissions and every affected identity/denial/idempotence
boundary. No call to execute_day or legacy engine is permitted, even in a fixture.
No modification or re-admission of accepted Cohort1–4 owners is required. Their
receipts are reused evidence; in particular, the two Cohort3 owners lacking
native remark/request captures are not automatically eligible for this policy.

The resulting claim is reusable admission implementation with fixture correctness
proof. A real new supported daily run remains **UNPROVED and held** until a later
exact frozen input/configuration, opening/actions, finite count, exclusive
resources and acceptance proposal is approved. All wider application, active
NMS/approval/upload/client/sanitation, external alert, Sleep, history, scale and
cutover gaps remain outside this decision.
