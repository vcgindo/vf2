# Login/profile independence from MTA report workers

Authorized by the human in the command-centre chat on 4 October 2026.
Implementation owner: dataset chat `01a10098-1a4b-7e03-a9d3-77542504632b`.
This is a bounded implementation contract, not another status tracker.
Record progress and disposition only in `docs/MIGRATION.md`.

## Objective and stop boundary

Make real login and profile retrieval on3005 independent of the MTA report-worker
queue while preserving the current identity, permission and frontend contracts.
Deploy and prove one coherent correction, commit/push, provide a handoff and stop.
General Stage2 completion, report-query tuning and Stages3–5 remain paused.

The previous stabilization checkpoint is `612a629`. Retain its streaming fix,
full VM fixture, runtime limits and evidence. Its memory correction is accepted
within the measured boundary; its login-under-load exit remains unsatisfied.

## Evidence and decision

`ResponseUser.response()` and `ResponseProfile.response()` in
`user-service/api/core.py` call `ALL_PERMISSIONS.get_combined_permissions()`.
The MTA branch in `user-service/common/api_gateway_utils.py` fetches
`/api/mta/GetAllPermmision` synchronously through the two report workers.
In the retained stress evidence profile reached51.47s and a real login probe
exceeded30s. This is queue coupling, despite the corrected gateway memory use.

`mta/presentation/views.py::all_permissions` constructs its response from
`mta/presentation/context.py::permission_catalogue`: an existing registered file
validated by configured SHA256, version and unique IDs. Fixture admission also
binds that catalogue to the dataset manifest. User grants remain in the identity
database; the catalogue is not a replacement for those grants.

Use a small explicit local catalogue reader in the3005 user-service, consuming
the SAME registered read-only artifact and identity used by MTA. Preserve the
existing MTA catalogue response shape and mapping. Remove the synchronous MTA
HTTP fetch from the configured local login/profile path. This delivery-boundary
change is authorized; changes to authentication or permission rules are not.

## Implementation boundary

1. Reuse the existing normal and fixture catalogue artifacts. Do not regenerate
   them, infer missing definitions, create a second editable catalogue, or add
   a general snapshot/cache/refresh service. Load only this small metadata.
2. Pin the selected mode, catalogue version/checksum and existing publication or
   fixture identity in the deployment configuration. Both services must select
   the same catalogue. Reuse existing binding information; do not build another
   admission framework or call report workers on every login to validate it.
3. Coordinate selection and rollback through the existing deployment/restoration
   tooling. Validate consistency before serving the new selection; reject missing,
   corrupt or mismatched configured inputs explicitly. No silent stale-catalogue,
   empty-permission success or network fallback that restores the queue coupling.
   Exercise normal/fixture selection and mismatch behavior in owned tests; avoid
   unnecessary live serving switches merely to repeat already retained proof.
4. Keep live user grants, roles, account state and revocation behavior in the
   identity database. Do not cache effective user permissions or widen access.
   Preserve IDs, hierarchy values, NULLs, ordering and response envelopes; retain
   the authenticated gateway's identity injection and backend scope enforcement.
5. Limit changes to the MTA catalogue branch, affected login/profile assembly,
   focused tests and3005 configuration/restoration. Preserve MTO behavior and
   unrelated deployments. Existing deployments without this explicit local mode
   must not accidentally start consuming the3005 fixture catalogue.
6. Trace the observed profile-screen Loading symptom. Fix only a directly
   attributable response/loading/error-handling defect needed for this login/
   profile exit; do not redesign the profile page or other UI surfaces. If it is
   an independent issue outside this boundary, report its exact cause and blocker.

If the registered artifact cannot preserve the current catalogue semantics,
stop with the specific evidence. Do not substitute worker pools, extra workers,
new services, ports or a broad authorization redesign without a new decision.

## One consolidated acceptance pass

- Compare the complete MTA catalogue payload from the new reader with the retained
  endpoint for the same selection, including IDs, hierarchy and types. Compare
  login/profile identity and permission content before/after, excluding only
  inherently fresh token/time fields. Cover broad and restricted accounts.
- Prove configured login/profile makes no MTA catalogue HTTP request. Cover valid,
  missing, tampered and wrong-selection metadata, with clear failure behavior.
  Verify live grant/revocation behavior in an isolated identity test database;
  do not reassign serving users' grants merely for proof. Retain forged-scope,
  unauthenticated and normal-versus-fixture denial checks.
- Reuse the full-page stress probe and retained dataset. Observe fresh login and
  profile both unloaded and while the eight RRR/BPR/BTR/DBM grid/count requests
  overlap, including the retained Chronic contention pattern. Record all observed
  failures and latency, with gateway/MTA memory and CPU under unchanged limits.
  Prove identity responses no longer await report completion. Raising client or
  server timeouts, reducing data or moving work outside the observation is not proof.
- Verify real browser login, profile completion (or an exact independent blocker),
  navigation to the populated pages and login/profile during pending report reads.
  Reuse unchanged report-value/export proofs; repeat only affected regressions.
  Report performance and Chronic limits remain explicit and are not reopened here.
- Verify restart/startup selection, readiness and rollback consistency for the
  changed components. Record source commit, deployed image identities and the
  exact rollback procedure; preserve the accepted dataset and protected resources.

No arbitrary new latency SLA or full benchmark campaign is required. Acceptance
requires removing the demonstrated queue dependency and completing identity
interactions under the retained load, with actual timings and honest limitations.

## Authority, delivery and handoff

The human authorizes implementation and necessary build/deploy/restart of the
isolated3005 user-service/gateway and frontend, plus bounded MTA configuration/
restart only if indispensable for catalogue selection consistency. Keep resource
limits, two MTA workers, timeouts and restart policies unchanged. Preserve F1/F2
engines/accepted state, immutable data, credentials, serving grants,3002/3003/3004,
other services and shared infrastructure. No dataset import, engine execution,
database reset/repopulation or broader schema migration.

Pursue this as one bounded goal with no inferred token budget. Do not reopen or
mark the larger F3 migration complete. Use the existing evidence root and focused
checks; avoid repeated discovery, per-click milestones or additional plan layers.
At the logical exit commit/push the plan and implementation together with the sole
tracker update. Hand off PASS or the precise unmet exit, verified serving state,
evidence, image identities and rollback. Stop for command-centre review.
