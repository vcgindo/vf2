# Accepted daily/MDM baseline review — 13 October 2026

This is an implementation/proof record. `MIGRATION.md` owns status. The containing
commit on `codex/btr-ready-snapshot-trial` is the reviewed baseline for subsequent
production-handoff work; it does not certify production deployment.

## Accepted implementation

Retain the active-NMS finalization, own-predecessor intake, complete MDM family
composition, typed atomic current-master publication, guarded operational
acceptance, shipment binding and isolated approval-workflow transport. Commit
their dependencies and tests together. The active path remains limited to its
previously approved registered artifact and three-date domain.

Three defects are corrected:

- Standard-attribute rows with canonical NULL SKU/location identities survive
  transit tagging unchanged. SQL equality never matches NULL on either side;
  non-NULL matching, Seasonality/PIPO precedence, duplicates and tags are retained.
- The temporal command forwards the configured finalization policy instead of
  defaulting an active-NMS input to the inactive policy.
- The approval-day execution package uses the complete reporting coordinator,
  records the Planning summary identity and requires both layers and summary READY.

The committed Planning migration previously depended on untracked0112/0110.
Those unchanged additive schema/model prerequisites are included, together with
MDM0107–0109 and graph merges0111/0113/0116. No applied migration is rewritten.
Guided reader/cache/frontend changes are excluded. The six isolated
gateway transport tests cover the separate workflow capability and denial bounds.

## Verification

The exact staged source is exported under
`D:/freshvcf-build/evidence/daily-mdm-baseline-review-20261013-001/`.
Focused unit/command, shipment/package, supplier/source-preservation, gateway,
Planning and permission-denial tests pass. An exclusively owned PostgreSQL16
container has no host ports, restart=no,1GiB/1CPU; verification workers use
4GiB/2CPU and the candidate source, never serving database bindings.

Fresh migrations through0116, Django check, model-drift check and empty final
migration plan pass. Eight real PostgreSQL accepted-closing/current-owner tests
pass, including full typed rows/ordinals, invalid-write denial and rollback.
Thirty-six consumption/admission tests pass against the migrated isolated DB.
All396 pinned resources verify unchanged. There is no repository-wide test claim.

Preserve the first admission-test failure: old mocked receipts omitted the newly
explicit policy/qualification. Fixtures now declare the exact supported policy;
validators and assertions remain intact. Exported-package checking also exposed
Git newline conversion of the approved input map; `.gitattributes` now preserves
the original decision/map bytes and hashes. No input or receipt was regenerated.

## Limits and preservation

No business-day call, legacy-engine invocation, task submission, serving restart,
deployment, selection change or paused-trial resumption was performed. The earlier
FAILED June6 run/capture and all receipts remain unchanged. PostgreSQL proofs are
component fixtures, not accepted business-day receipts.

3005's existing images, container start identities, configuration bindings and
selected April7 fixture remain unchanged. Unrelated working-directory changes
remain uncommitted. No production-handoff branch is created by this review.

General master/opening ingestion, fixture-independent admission, required
BOR/BOROA output producers, portable operator/deployment packaging, legacy
validation separation, consecutive production-day acceptance and capacity remain
the subsequent handoff scope. These are not hidden by this baseline commit.
