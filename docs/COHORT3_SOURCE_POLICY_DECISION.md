# Cohort3 publication policy decision

Approved directly by the human in call_00b781455b944ead8db06860fbc55b06:
"Approve all four bounded choices." This document fixes the decision required
by P1 of COHORT3_PUBLICATION_CONSUMPTION_PLAN.md. MIGRATION.md remains the tracker.
The accepted source tuples and complete source digests are in
COHORT3_SOURCE_PINS.json. No calculation, preparation, activation or serving
selection has been performed for Cohort3.

## 1. Explicit qualified operational admission

Permit `cohort2-qualified-consumption-v1` only for these existing owners:

| Date | Run | Output SHA256 |
|---|---|---|
| June6 | 77731d95-03f4-4a82-8498-404f944df73b | 4956672dd7174c805888ccd8957764be51b31a561af57befbb844454b75c2849 |
| June7 | 1b83fdca-d0ad-47d5-8694-414257ae68be | 24cb05541ac807ac8c5c4afbc8e4c5c27c1d5023d2fd4fcc67be05b734fab1d3 |

Retain native IsBatchFileExecuted=0 and empty parity_summary. Never write PASS
or describe this as full legacy parity or full-batch completion. Admission must
verify the accepted typed run/output/input, own predecessor, exact current
actions, operational configuration, successful O1–O9 attempt and repair lineage,
actual files/intents/restore dispositions, immutable source receipts, all required
prepared layers, BTR generation, catalogue and access seals. Caller-supplied
metadata alone cannot establish acceptance. Missing, stale, partial, changed or
failed components deny admission. Strict migration parity stays the default.

The proposed roster is the existing 18-layer `core-without-bor-v1`, plus the four
existing Pick streams. Retain BOR/BOROA denial and GuidedExcess rolling-history
unavailability outside proved coverage. This does not declare those reports
complete. All Cohort2 qualifications and product gates remain in force.

## 2. Two explicit presentation-only empty source bindings

Both dates have 28 typed transit rows and three opening SOB/MOQ rows. Neither
date has a source receipt for BPRReport_RemarkDetails or OpenExpediteRequests.
Absence is currently unavailable, not empty. BPR and expedite preparation cannot
pass the existing 18-layer contract without these inputs.

Proposed decision: declare exactly those two populations empty for each listed
publication, in a new immutable presentation supplement bound to run, date,
output, production digest and policy. This is a new synthetic test-input
declaration, not a claim that their historical values were empty. Do not alter
accepted inputs, DailySourceReceipt, calculation rows or operational receipts.
Use the existing typed schemas, verify zero owned rows, and reject nonempty or
unbound supplements. Preserve all native report formulas and source checks.
No ColorSequence, BOR requirement, remark write or other missing source is
implicitly supplied. Any additional mandatory gap remains a blocker.

This enables testing BPR/expedite consumption with explicitly empty remarks and
requests; it does not prove populated request/remark behavior. If declined, these
sources remain unavailable and the 18-layer positive publication exit is blocked.

## 3. Run-bound retained hierarchy transfer

Permit the existing read-time SL1–3/LL1–3 projection for exactly the two tuples
above, including Pick's consumed importer attributes. Reuse unchanged retained
200-product/20-location catalogue bytes with SHA256
`18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356`.
Pin a new two-owner manifest; retain unknown-entity/conflict/duplicate checks,
native checksums, row order and multiplicity. Without the exact opt-in, native
NULL hierarchy continues to deny access. This does not change product/location
grants, native attributes or the earlier terminal-only hierarchy manifest.

## 4. Isolated download entitlement

The retained two-account contract SHA256 is
`52f698f99e87cbfca6959ce3ec4b4bed91fb255e4a6d5ee6c597640428ecca3e`.
Its persisted roles contain no `mta-report-urls` permission. The unchanged
gateway requires that entitlement for all four Pick streams.

Permit the existing `mta-report-urls` permission on a new Cohort3-only role
assigned only to the copied broad fixture actor, user2, application2, in the
new owned in-process identity namespace. Keep copied restricted user3 without
that entitlement to prove denial. Preserve credentials and all product/location
scopes. Do not grant either serving account access or change any serving role.

## Fixed delivery boundary

Use actual cookie JWT issuance, persisted actors/grants and the real gateway.
The gateway currently uses HTTP requests; a bounded in-process transport adapter
is required for the already authorized no-port proof. It must preserve actual
MTA URL resolution, middleware, identity injection and streaming responses.
No mock, forced authentication or trusted-header-only test can close that exit.

Approval permits only these four dispositions and their focused implementation
and proof. It does not itself establish READY. Zero new business calculations,
legacy calls, serving changes, benchmarks or temporal continuation are permitted.
An unresolved mandatory source or failed invariant stops dependent acceptance.
