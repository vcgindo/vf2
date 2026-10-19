# Administrator data access verification — 19 October 2026

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

The installed administrator already had every page/action permission, but gateway report requests used only stored business grant rows. The blank installer intentionally creates no business grants. That mismatch produced empty administrator reports while scoped operators could read the same publication.

The shared authentication gateway now resolves the authenticated administrator's full current MTA/MTO catalogue on each request. Ordinary users retain their exact stored grants and immediate revocation. No wildcard, new role, grant seed, browser-supplied admin flag or stale scope cache is used. Invalid/unavailable catalogues fail closed with503. MTO's retained LEG-015 header-identity contract is unchanged; expansion additionally requires its subject to match the authenticated administrator. This change does not repair that separate inherited contract.

## Source and installer

Implementation commit: `0a8084057d48ab4c384312d00d8cf42d10794912`.
The normal source build includes the helper in the auth image, and blank installation records policy `authenticated-admin-current-catalogue-v1`. Installer-created administrators need no separate business-scope grant. Sample loading and daily execution remain separate. Existing installed databases must not be blank-installed again.

## Verification

- 28 affected tests passed inside the actual new production auth image, with networking disabled and temporary SQLite identity fixtures. They cover fresh installer-admin creation without role/business-grant seed, current/new catalogue IDs, local/remote MTA catalogues, populated/blank MTO responses, ordinary-user revocation, mismatched/spoofed subjects, invalid catalogue/timeout/HTTP failure, existing gateway identity/download/MDM enrichment contracts.
- Current I:/VectorFLOW auth image: `sha256:c0f12c00051438ef2321c2a3d06c7a5e6ebce75a51825ea17d5702c1675fd77b`, built from committed source using release/auth.Dockerfile. Only auth was rebuilt/recreated. Its persistent local Compose override binds that exact image; all earlier Compose overrides and private env settings are retained.
- Actual existing administrator login: Planning19October dashboard shows excess4/order-fulfilment12; excess grid renders4 rows. BPR renders12 rows. DBM opens the selected19October report and correctly has0 suggestions, matched by backend count0.
- Real gateway-to-MTA read-only verification returns200 for Planning, BPR count/body and DBM count/body with all7 current MTA catalogue scope IDs, despite admin having no stored business grants.
- Real gateway-to-MTO DDQ analytics returns200/zero orders. The installed MTO catalogue is genuinely empty. Populated MTO catalogue expansion is covered by focused contract fixtures, not a claim of populated live MTO report testing. No MTO facts were loaded.
- Identity users/password hashes/roles/permission links/product-location grants are byte-equivalent by ordered-value digest before/after. Selected MTA publication bytes are identical. All11 non-auth existing project containers retain exact IDs/images/start times/running state; all6 serving services are healthy. Frontend, MTO, MTA, databases, original3005 and unrelated services were not rebuilt or restarted.

Evidence outside Git: `D:/freshvcf-build/evidence/admin-full-access-20261019` (packaged-tests.log, live-read-only-proof.json, activation-configuration-proof.json, identity-preservation-before/after.json, preservation-after.json, admin-planning.png, admin-bpr.png, admin-dbm.png). No secrets or database dumps are committed. This is access-control verification, not calculation replay, new legacy parity or production-capacity acceptance.
