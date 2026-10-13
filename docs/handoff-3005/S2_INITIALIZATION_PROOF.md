# Native initialization component proof

13 October 2026. This is evidence, not a second tracker. Live status is
`F:/freshvcf/docs/handoff-3005/TRACKER.md`.

The bounded H2 source unit from 903ed32 was adapted onto the accepted 3005
lineage. Native supplied masters/opening/configuration are validated and stored
in typed relational rows. The initializer creates no calculated day, uses no
DLL or legacy execution, and requires a provisioner-registered database owner,
issuer, input and implementation. Existing fixture installation remains separate.
Runtime state-schema table definitions are byte-value equivalent to the existing
baseline schema; only source-provenance metadata is omitted from the runtime copy.

Evidence root: `D:/freshvcf-build/evidence/handoff3005-s2-20261013-001`.
The internal network, no-port PostgreSQL/worker, mount boundaries and resource
limits are recorded in `resource-boundary.json` and `isolation-created.json`.
The database `handoff3005_s2_20261013_001` is reserved for this immutable component
binding. Dedicated owner/issuer/consumer roles and database OID are recorded in
`component-database-created.json` and `component-registration.json`.

| Proof | Result |
|---|---|
| Typed contract tests | All 8 pass. Invalid/incomplete/unknown fields, wrong hashes, forbidden calculated outputs, future history, duplicate JSON keys and nonfinite values denied. |
| Existing daily source binding regressions | All 4 pass. Existing artifact/DLL/family binding remains strict. |
| Django check / makemigrations --check --dry-run | No issues / no changes detected. |
| Fresh migration plan and actual PostgreSQL migration | Full historical chain plus additive 0117–0119 applied, no fake migrations. Plan/apply logs retained. |
| PostgreSQL component suite | All 6 pass: full frozen typed frame readback, NULLs, duplicate ordinals, retry identity, changed input denial, immutable rows and injected terminal failure rollback. |
| Role denial | Consumer cannot assume owner; provisioner session cannot claim registered issuer. Both denied through actual database connections. |
| Operator command / committed rows | `initialize_production` returns INITIALIZED then REVERIFIED with the same owner. Complete frozen typed readback matches; zero CalculationRun rows. |
| Serving protection | All six protected container IDs, image/configuration hashes, start times, mounts, ports and limits unchanged. |

Input and expected typed frame were frozen before application writes in
`component-input-manifest.json`, `operator-input.json`, `component-expected.json`.
The supplied component fixture deliberately exercises arbitrary identities and
historical values. It is **not** retained-catalogue business-flow evidence and
does not establish calculated history, Apply/Sleep, MDM effects or successor
correctness. Those still require small retained-identity cases and real daily
execution. No UI, production-capacity or whole-Step-2 acceptance is claimed.

The first pure fixture run referenced donor active-nms-v2, which the accepted
baseline rejects. The fixture was corrected to the accepted explicit v1 policy;
finalization logic was not changed. No failed result was counted as passing.
