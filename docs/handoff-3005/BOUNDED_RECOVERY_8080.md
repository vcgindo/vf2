# Existing 8080 stack: bounded recovery

Use http://localhost:8080 and the existing fixture login
`benchmark-admin@vectorconsulting.invalid`. Its verified password remains in
the local fixture secret; credentials and CAPTCHA behavior were not changed.

The existing stack serves localhost:8080. The bounded recovery updates only
its MTA reader, frontend lifecycle handling and authentication catalogue delivery.
MTO, PostgreSQL and Redis services are retained. No calculation or report
preparation is needed.

## Exact serving artifact

- Product commit: `94280b0be4e2d52f51581465acf2ae6815fa4b89`.
- Branch: `codex/bounded-ui-recovery`; subsequent test/document commits do not
  change the MTA/frontend bytes; auth has its separate pin below.
- Image: `sha256:c9abc28b7e8dba12fca9a982fbd96e28c4bbfc2ecddfb47ed1e1c4318a912408`.
- Container: `vectorflow-mta-ui-final-20261023`, ID
  `5155ae87e717ab94e18cb60980c168896cd59b66647bb798ead89223adf404ea`.
- Internal network/alias: existing `vectorflow_application`, `mta`.
- Frontend product commit: `94280b0be4e2d52f51581465acf2ae6815fa4b89`.
- Frontend image: `sha256:11e5e56ce5602432344fa6f00fa4c95572583d46e35027b10714329a2da1adbd`.
- Frontend container: `vectorflow-frontend-ui-final-healthy-20261023`, ID
  `0b8926f73e3c60a01ffc3ee27ab8c3349b9dd9dd0dc5036497e6238ecb26e5f0`.
  Its original runtime environment and sole127.0.0.1:8080binding are retained.
- Accepted run: `49efa557-a31f-4ea8-9089-b510f2856d30`, April 8, 2026.
- Output: `ee1f58bb9e2161b6bca5ebf5bdbb0993ae75a060e5e9312d2181b750782949ad`.
- Attempt `bace2905-69a9-4e76-ab43-6343bb626b54` was acknowledged once through
  the supported command and is `PUBLISHED/FINISHED`.

Authentication reuses 3005's local permission-definition reader, extended for
the checksum-pinned native selection. Auth commit
`d1a777dd3eb9e49db9ca5fbf181c77ff9b6b61a8` is deployed as image
`sha256:1cf5f5df68ef821c517a056eec2957c2134272a0432591e13464d4c9647d6409`,
container `vectorflow-auth-native-login-20261023`, ID
`d9434881b829adefbea684408acae54a40c4f938780adec1c386e44b93db9fd0`.
It retains private `auth:10016`, the original identity database, secrets,
log/data volumes, security and health settings, with no host port. It reads the
same permission file and shared selection volume read-only. Both file checksums
are verified on every use; changed selection requires coordinated pins. Live
grants, administrator scope checks, mandatory profile and CAPTCHA remain intact.
No effective permission result is cached; strict MTA admission is unchanged.

Independent preflight matched the complete MTA catalogue payload (7,862 bytes,
SHA256 `9fa909ab9f2c7a57264f3a2787cfd899c5e2f3c2a61e432d124ea4fdbab583cd`);
local reading took 0.0048 seconds. Actual browser Submit-to-visible-landing
improved from 7.540 to 2.322 seconds. This is one matched fixture trial, not a
concurrency benchmark. Forty focused authentication tests pass in a
network-isolated in-memory database, including live revocation and native
selector tampering, mixed-mode and atomic-replacement denials.

Auth rollback: stop only `vectorflow-auth-native-login-20261023`, then start
retained `vectorflow-auth-1` (`54e2e60686de4074f69c14bc3cf7f897d8538dc321657f719cbf008ada18390e`,
image `sha256:3c1c867bb9106b6876c14e778d5c3aa4cf9e652fc78b553babfbaa597b3bd435`).
Never run both with the `auth` alias. No database restore/reset is needed.

Do not rerun selection, preparation, execution or acknowledgement for this
already published attempt. The normal read-only checker is:

```powershell
docker exec vectorflow-mta-ui-final-20261023 python -B -m release.daily_serving_check --run-id 49efa557-a31f-4ea8-9089-b510f2856d30 --output-digest ee1f58bb9e2161b6bca5ebf5bdbb0993ae75a060e5e9312d2181b750782949ad
```

## Why these changes

The running-server checker now compares independent bindings, selection and
actual readiness without repeating the offline exclusive admission. Full cold
startup admission remains intact; the final MTA startup took about 14 minutes
44 seconds. The auth-only login correction needs no MTA restart or full audit.

Successful native publication identity metadata is reused only across an
unchanged PostgreSQL snapshot, physical connection, process and session.
Database changes, reconnects and full/offline/write checks revalidate. Report
rows, permissions and workflow state are not cached.

BOR reads only its authenticated policy component rather than unpacking the
day's unrelated facts. MDM's optional upload-audit receipt now proves a missing
policy from authenticated object structure and owner references. An existing
capture or present/unsupported policy still follows the original full path.
Full input audits retain responsibility for all input values. Finite successful
CertifiedReadiness metadata is also reused only for an unchanged PostgreSQL
snapshot, connection, process, initialization, release and session settings.
Offline, write and transactional callers retain the original validation path.
No row population, permission or workflow result is cached.

Read-only MDM consumers now enter the existing finite certified owner scope,
preventing fallback to loading the entire opening. Seasonality batches the same
importer permission occurrence joins and consumes the complete master image
once, including its full value/type/order checksum. Duplicate rows and NULL
semantics are preserved. Independent actual-data diagnostic results match the
prior response bytes; repeat Seasonality reads remain about 5–6 seconds, so
these results do not establish a two-second browser target.

Frontend product commit94280b0be4e2d52f51581465acf2ae6815fa4b89 adds shared
60-second request deadlines and ten-minute download deadlines through body
processing. Refresh failures reject all waiters; refresh requests cannot queue
behind themselves. Loading owners settle in finally paths. Genuine empty
counts clear stale results; malformed counts remain errors. These changes do
not retry business actions or change their payloads. Existing resolved400/403
contracts and cookie authentication are preserved.115focused frontend and
76focused backend tests pass. The unchanged scalability export fixture failure
was independently reproduced on the accepted base; it is not reported as a
passing suite. Current deployment/browser proof is recorded in the tracker.

The mandatory profile verification is retained. Its verified user is committed
before a passive effect fetches environment configuration, preventing that
ancillary request from competing with the landing-blocking profile request.
Catalogue guard hashing uses an exact equivalent C JSON encoder for its finite
built-in metadata only; all three fresh catalogue scans remain. The same live
760,247-byte payload produced identical SHA256 with3.3MiBadditional peak memory.
The general calculation/streaming serializer is unchanged.

The frontend visual design and MTO API are fixed boundaries. Cumulative source
checks show no stylesheet, asset, font or style-module changes; the29modified
production frontend files retain identical JSX structure, static text and visual
style attributes. MTO service and API-client sources are unchanged. The existing
MTO container/image/mount/start identity remains protected.

## Final browser checks and limits

Actual View/Modify navigation to visible SKU family took 1.295 seconds. The
previous deployed Seasonality check populated 83 rows; an unmatched server-side
SKU filter cleared all rows/counts, showed the existing no-data warning and
ended the loader. Generic request/loader failure and timeout paths have focused
tests; these results do not mean every report completes within two seconds.

After the auth correction, RRR rendered its 7,904 accepted-day rows across two
pages (5,000 then 2,904); an unmatched grid filter showed zero filtered rows and
clearing it restored data. BOR rendered 1,197 rows and BOR Color Bandwise 1,200.
All show April 8, 2026. Earlier BPR verification populated its 97,097 population
and real 50-row page. No remark or business action was submitted in these checks.
RRR export returned HTTP 200 and 1,470,163 bytes; its download loader settled.
The downloaded file was not independently inspected: browser policy rejects
the Downloads page. This is not a claim of file-content verification.

The 40 auth tests supplement the 115 frontend and 76 backend focused checks.
Auth's installed package versions exactly match its retained predecessor.
Accepted producer/run/capture/publication/report state remains exact, as do all
11 archive metadata sets after the final auth replacement and browser login.
MTA, frontend, MTO and PostgreSQL retain their exact container/image/start pins.
Full cold startup remains slow and is outside this bounded login correction.

## Preservation and rollback

Evidence is under
`D:/freshvcf-build/evidence/bounded-ui-recovery-20261023`, with the last
acknowledgement in `latency/` and final frontend/backend qualification in
`settled-ui/final-pass/`. The original database backup was
restored into the separately owned `VFTEST_Fresh_UIRecovery_20261023` database
and reconciled before deployment. The accepted business state and prepared
publications remain unchanged. Only the intended publication acknowledgement
fields/files changed; ten previous archives remain byte-identical.

The previous backend `vectorflow-mta-ui-latency-20261023`
(`01b6ad69ed4925c63b031900ec49999a910eb4f2117f5a74a9690aadf2bc9cec`,
image `sha256:faf14c49fea086d7ac6aa31f95516673db0f1728db18e509b1352d3a8d5e7e83`)
is stopped and retained. A coordinated rollback would stop only the new MTA
and start that exact previous backend, allowing its full audit to finish.
Never run both with the `mta` alias. No database restore, volume deletion,
Docker restart or recalculation is part of this rollback.

The original frontend `0d282cc8ded58ee5ab938d95255bddd1e258c6b6f90efce14f7625858839e3fc`
is also stopped and retained. To roll back the UI, stop only the new frontend
before starting that exact predecessor on the same8080binding. Do not run both
frontends on the same host binding. Authentication, MTO and databases need no
replacement or restore.

The sole acceptance/status authority remains `docs/handoff-3005/TRACKER.md`
in the controller checkout. Readiness and publication acknowledgement alone
do not establish browser latency acceptance.
