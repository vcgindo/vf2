# Ingestion milestone 1 — ownership and compatibility foundation

20 October 2026. Source baseline `687adcf024ea9bffe0c90b3de2bb67e25019ec4a`, branch `codex/3006-logistics-integration`. This is a proof record; `F:/freshvcf/docs/handoff-3005/TRACKER.md` remains the sole live tracker.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

## Delivered boundary

Explicit immutable `PreparedRunInputs`, population-reference and five-generation contracts separate masters, configuration, facts, operational state and actions. References contain identities, counts and digests, not business payloads. Unknown master fields are rejected. Norm remains operational. Existing mixed master tables conservatively invalidate the master/configuration cut on other structural/configuration changes; a Norm-only update advances only the operational generation.

Four metadata models hold immutable certification, accepted master revisions, compatibility audit and separately mutable generations. Four forward migrations, `0144`–`0147`, create these objects and their guards. `0145` installs statement guards; `0146` preserves any existing generations while separating them from immutable certificates; `0147` freezes explicit supplier/exclusion/configuration, approved-action and captured-fact ownership. No historical migration was changed after application.

Each participating SQL statement advances its generation in the same transaction. Rollback restores it. Unchanged updates and empty statements do not advance it. Opening/source seals cannot be rewritten. Certification can be invalidated but cannot be reactivated or edited. Supplier SOB/MOQ raw owners and current pair-exclusion rows are configuration; pair exclusions remain mutable through the existing daily writer. Approved queues and workflow history are actions; captured input/task/history/archive rows are facts. Other typed results and projections remain operational.

`certify_current()` performs the existing complete native opening/current-master/pair-exclusion/all-13-family audit in an installer-owner maintenance transaction before issuing metadata. It supports a current-release opening and cannot relabel an older producer. It does not execute a day. Integration with one-pass CSV initialization belongs to milestone 2.

A separate registrar-owned append-only authority activates a precisely bound release transition last. Application-owner metadata alone cannot activate compatibility. The original namespace and application capability remain unchanged. Admission checks their exact production policy, producer/registration chain and original commit/manifest tuple, then the independently admitted current release, current schema/grants/guards, certificate, accepted master/configuration cut and fresh generations. Missing, stale, foreign, corrupt and partial authority fails closed.

Certified read-only source/installation/family metadata paths use this bounded admission. Uncertified installations retain the original full verifier. No environment skip, silent old-path fallback after certification, timeout relaxation or historical receipt rewrite was added. The only admitted definer is the exact frozen revision-trigger body with fixed search path and revoked public execution. Ordinary registration validates its full trigger shape separately from the unchanged logistics guards.

## Verification performed

- **35 unit checks passed; one existing auth-dependency check skipped.** Modules: `test_ingestion_ownership`, `test_native_binding_reads`, `test_installation_metadata`, `test_native_release_capability`, `test_native_release_identity`.
- **10 PostgreSQL cases passed** in disposable database `vf_ingestion_m1_20261020` on the existing owned PostgreSQL. All 169 migration records were genuinely applied from empty; all four metadata tables had the dedicated owner. There were 4,124 statement guards covering 1,031 physical participants.
- The PostgreSQL cases exercised rollback, Norm-only and structural changes, an actual MOQ raw-table change invalidating configuration, immutable receipts, runtime/application-owner denial, missing/foreign/partial authority, and disabled/missing writer or privilege drift.
- Complete small-fixture flow passed: fresh native registration → typed initialization → all 13 families → full certification → rejected admission before activation → registrar activation → runtime readiness/source access. Original initialization/source seals stayed unchanged; zero daily calculations. Only source-authentication metadata was mocked for this uncommitted-source fixture; native manifest/file authentication was checked separately by the existing release-identity tests. This is not a packaged-image or live-upgrade claim.
- Certified metadata admission measured **0.847 seconds / 29 queries** on this host. Captured SQL contained no opening payload, opening-population or business-state-population reads. It is a readiness measurement, not initialization or daily-calculation throughput.
- Django system check, `makemigrations --check --dry-run`, and migration plan passed: no issues, model drift or pending operations.

An additionally inspected historical `test_logistics_capability` module still errors because it references removed historical catalogue/export helpers (and its old connection fixture). Those helpers/modules were already absent at baseline `687adcf`; the test file is unchanged. They were not restored or assertions weakened. The current native-registration/logistics guard path passed the real PostgreSQL flow above. Auth code/dependencies were not changed to resolve the separate inherited skip.

## Preservation and stopping point

The working `I:/VectorFLOW` clone remains at `687adcf`, on the same six healthy containers. Opening `ebed3913-8e83-4da2-ae07-0c02f3b0beca`, input SHA `27b3893b0f8a0f0db0197439c760677e9dc6dca07ad00f26fc4297781dd57a70`, all existing loaded data and zero daily runs were retained. Its 165 migration records remain unchanged; no new certification table was installed there. No image was built, application service restarted, master reloaded, browser session used, or frontend/MTO/auth/business rule changed. 3005, legacy and unrelated resources were untouched.

Temporary proof containers used `--rm`; the single disposable proof database is removed at handoff. No comparison stack or image is retained. The current release's required original manifest pin is `2b7346f3382d78e3ea2d8c352f9854b6f59b5e13cf53d27aa9fa68216f478818` in addition to its full baseline commit.

This milestone does **not** claim that the loaded large opening is upgraded/certified, that final target release identities are frozen, or that daily runtime is improved. The controlled original-producer audit and same-opening upgrade remain milestone 4; one-pass initialization/storage and accepted fact/prepared-context integration remain milestones 2–3. No later milestone or daily run starts automatically.
