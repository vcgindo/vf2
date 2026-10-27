# Step3 functional corrections — source checkpoint

This checkpoint addresses only the two retained functional defects after window4. The sole status authority remains `F:/freshvcf/docs/handoff-3005/TRACKER.md`. No build, deployment, new test window, calculation replay or additional database is performed by this checkpoint.

## BTR stylesheet

Human reply `call_6f34c8e79c124b828e5188faeed1d60f/0` approves the exact one-line `import "allotment/dist/style.css";` at the BTR entry. The source diff is verified to contain that import only for the frontend. CSS values, markup, data, visual design and MTO remain unchanged.

The same-data browser diagnosis found that direct entry/reload omitted Allotment's core stylesheet and collapsed the combined view. Visiting Guided loaded the existing stylesheet and restored the BTR layout; reloading reproduced the collapse. These observations explain the dependency correction, but do not qualify the corrected bundle.

## Auth process continuity

Retained refresh failures report `Invalid site token` after refresh-token parsing. The packaged default cache is process-local. Isolated native processes reused their own daily keys but generated different keys from each other.

Only the daily site key gains an explicitly configured shared owner. `VF_AUTH_SITE_CACHE_URL` (or its `_FILE` counterpart) and `VF_AUTH_SITE_KEY_NAMESPACE` must both be supplied. The namespace must remain stable across processes serving the same authentication identity and distinct from other installations. Default permission caching is unchanged. Atomic cache initialization selects one winner; connection errors propagate without a local fallback. UTC daily rotation, 25-hour key TTL, access/refresh lifetimes, signature, site-key, permission and revocation checks remain unchanged.

Unconfigured installations retain the old behavior and are not continuity-qualified. Compose currently supplies neither new setting, so the source correction is inactive until deployment wiring is explicitly supplied and verified. The first move from LocMem cannot preserve keys from the old process: establish a normal initial login on the configured candidate, then prove continuity through subsequent supported transitions. Do not mix old and new auth workers, transfer private process keys, or alter token claims.

The existing Redis is the proposed owner; no Redis infrastructure or runtime configuration has been changed. Redis retention is a dependency: loss or eviction of the daily key still invalidates sessions. This correction does not claim continuity through cache loss or the existing UTC daily rotation.

## Verification and remaining proof

Fifteen focused tests pass, covering explicit configuration, secret-file configuration, concurrent initialization, permission-cache separation, daily rotation and fail-closed cache errors. Python syntax, production-export inclusion and `git diff --check` pass. Independent bounded review found no actionable source defect and confirmed that deployment wiring and native proof remain outstanding.

Before functional closure, qualify the actual Redis-backed auth image with separate processes, supported replacement, expired-access refresh followed by the existing read/export, fresh permissions, invalid/expired/revoked denials and cache outage/recovery. No action replay is needed. On the corrected frontend bundle, verify fresh entry/reload, both combined orientations, on-hand/pipeline, visible headers/rows, scrolling, lock/splitter/resize and unchanged data.

Build and serving boundaries remain separately governed; the closed window4 is not reopened. Reuse qualified MTA and retained completed databases. Do not rebuild MTA or create fixtures for these corrections. Step3 and the overall goal remain incomplete; latency acceptance remains deferred.

Evidence directory: `D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/runtime-step3-20261027`.

- `functional-btr-import-approval.json`
- `functional-btr-cause-and-proposed-patch.json`
- `functional-refresh-retained-errors.json`
- `functional-refresh-cache-source.json`
- `functional-refresh-key-lifetime.json`
- `functional-source-checks.json`
