# Cohort6: exact unsealed configuration correction

Approved by direct user reply9October2026, "approved, proceed with the goal": the single configuration-digest transition below
through a transaction-scoped guarded exception in the owned Cohort6 database.
The ordinary publication guard must be restored before commit. No trigger is
disabled, no READY receipt is changed, and no calculation is repeated.

## Observed failure and retained state

The runner passed read-time hierarchy/access settings into native preparation.
That created an INCOMPLETE publication with an access-bound configuration digest.
Three native builders correctly refused it. Two further layers ran before their
RRR prerequisite; the other13 layers completed. Native rollback proof passes all
five missing layers after RRR exists, with all previous metadata unchanged.

The application-only correction was rejected by
`mta.guard_daily_ui_publication`: configuration identity is immutable even when
INCOMPLETE. The attempted update rolled back. Read-only equality proves the entire
publication and its FAILED attempt remain identical to the original snapshot.
The previous review missed this database guard; its earlier assessment that no
additional decision was needed is superseded by this native failure.

June6 calculation and its authenticated action remain committed. Operational
attempt `aa939337-78b8-476b-b3b4-1df5f563d1b6` passed O1–O9 and qualified restore;
its failed predecessor remains preserved. There is no activation, acceptance or
publication seal. Calls remain2/3, both June6; June7 has never been called.

## Exact permitted transition

- Database: `fresh_cohort6_20261009_001` only.
- Run: `71a5addc-dcb7-49ca-811d-6cd93886d4e5` only.
- Output: `7075127ea7fc6fa3d3d05f00bcb6e771eb1bf6401a811cbf2c97158e5976235b`.
- Source: `c121b63cb503afa7e4ecef7bd1dcbd408689a437e5016c035c5bd3b67ea4a6a2`.
- Recipe: `3695c411a7f6252ae064e97940f35b2c2d2e14006c42c9fbfb26522bcbb0c149`.
- Prior configuration: `5966067dbbc4037f58f722b4c16f98ad02ead9c0bc59ebeced82026aea1b3eee`.
- Native configuration: `5cc3659af6b12b183000844f73088ef3798dd75a3a379ed30b52677a20ad8f34`.
- Full prior publication/attempt snapshot SHA256:
  `7414b88f8638109b456ab8e264a0893659b07e3880e0d2d35a32ade781416bac`.

The only updated column is `configuration_digest`. Both old/new rows must be
INCOMPLETE, with an empty seal and NULL sealed_at, and identical in every other
column. There must be no activation or operational acceptance. The exact failed
attempt and all13 READY layer receipts remain unchanged. Live identities and
the complete snapshot must match before the transition.

## Authorized execution if approved

1. Prove denial for another run/database, a READY/sealed/activated/accepted row,
   changed receipt, unrelated configuration or source/recipe drift. Verify the
   installed guard against its retained exact definition.
2. Lock the publication and guard within one owned database transaction. Retain
   the full original snapshot. Install a temporary guard variant that keeps every
   ordinary guard and allows only the exact transition above under the dedicated
   owned issuer. Never disable a trigger or grant new privileges.
3. Update the one column, prove all other fields and failed-attempt records match,
   restore the exact original guard definition, verify restoration, then commit.
   Any failure rolls back the entire transaction, including the guard change.
4. Repackage the corrected runner. Resume native preparation with empty access
   settings, reverify/reuse the13 READY layers, and prepare RRR before dependent
   layers on June7. Bind the approved read-time access only during acceptance.
5. Complete root acceptance and unselected checks. Only then consume the one
   remaining June7 call and finish its original gates. Preserve all qualifications
   and failures, make one cohesive commit/push, and stop.

This is an explicit exception to the existing immutable identity rule, not an
ordinary retry or a claim that the rejected transition succeeded. It does not
authorize calculation changes, source omissions, another business date, serving
changes, a general publication-rebinding API or further calculation invocations.

Evidence root:
`D:/freshvcf-build/evidence/cohort6-prerequisites-20261009-001/continuation-003`:
`execute-once.log`, `execute-exit.txt`, `guard-failure-readonly.log`,
`guard-failure-receipt.json`, `original-publication.json` and packaged proofs.

Execution result: the exact transition committed in continuation004/two-date-006.
The original guard was restored before commit and confirmed by final readback.
All other original fields and the failed preparation attempt were preserved.
Both dates subsequently passed final supported operational acceptance.
