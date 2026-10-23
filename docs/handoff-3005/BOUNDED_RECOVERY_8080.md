# Existing 8080 stack: bounded recovery

Use http://localhost:8080 and the existing fixture login
`benchmark-admin@vectorconsulting.invalid`. Its verified password remains in
the local fixture secret; credentials and CAPTCHA behavior were not changed.

The frontend, authentication, MTO, PostgreSQL and Redis containers remain the
existing stack. Only its internal MTA endpoint was replaced. No new host port
or calculation/report preparation is needed for UI testing.

## Exact serving artifact

- Product commit: `9536085a86d49de0e9b8504e3dcbba462b02adb0`.
- Branch: `codex/bounded-ui-recovery`; subsequent test/document commits do not
  change the deployed product bytes.
- Image: `sha256:faf14c49fea086d7ac6aa31f95516673db0f1728db18e509b1352d3a8d5e7e83`.
- Container: `vectorflow-mta-ui-latency-20261023`, ID
  `01b6ad69ed4925c63b031900ec49999a910eb4f2117f5a74a9690aadf2bc9cec`.
- Internal network/alias: existing `vectorflow_application`, `mta`.
- Accepted run: `49efa557-a31f-4ea8-9089-b510f2856d30`, April 8, 2026.
- Output: `ee1f58bb9e2161b6bca5ebf5bdbb0993ae75a060e5e9312d2181b750782949ad`.
- Attempt `bace2905-69a9-4e76-ab43-6343bb626b54` was acknowledged once through
  the supported command and is `PUBLISHED/FINISHED`.

Do not rerun selection, preparation, execution or acknowledgement for this
already published attempt. The normal read-only checker is:

```powershell
docker exec vectorflow-mta-ui-latency-20261023 python -B -m release.daily_serving_check --run-id 49efa557-a31f-4ea8-9089-b510f2856d30 --output-digest ee1f58bb9e2161b6bca5ebf5bdbb0993ae75a060e5e9312d2181b750782949ad
```

## Why these changes

The running-server checker now compares independent bindings, selection and
actual readiness without repeating the offline exclusive admission. Full cold
startup admission remains intact; the latest startup took about 11 minutes
29 seconds.

Successful native publication identity metadata is reused only across an
unchanged PostgreSQL snapshot, physical connection, process and session.
Database changes, reconnects and full/offline/write checks revalidate. Report
rows, permissions and workflow state are not cached.

BOR reads only its authenticated policy component rather than unpacking the
day's unrelated facts. MDM's optional upload-audit receipt now proves a missing
policy from authenticated object structure and owner references. An existing
capture or present/unsupported policy still follows the original full path.
Full input audits retain responsibility for all input values. No readiness
result cache was introduced.

## Preservation and rollback

Evidence is under
`D:/freshvcf-build/evidence/bounded-ui-recovery-20261023`, with the last
deployment and acknowledgement in `latency/`. The original database backup was
restored into the separately owned `VFTEST_Fresh_UIRecovery_20261023` database
and reconciled before deployment. The accepted business state and prepared
publications remain unchanged. Only the intended publication acknowledgement
fields/files changed; ten previous archives remain byte-identical.

The previous backend `vectorflow-mta-ui-recovery-20261023`
(`46468e90b96d0f7a74c9fa41c6db1843efa0ae6e8b075ced9502d54e1bfc6740`,
image `sha256:0b9faee3ed59520a1ece4124a091270c2bb233a6184569645b2047deb00decda`)
is stopped and retained. A coordinated rollback would stop only the new MTA
and start that exact previous backend, allowing its full audit to finish.
Never run both with the `mta` alias. No database restore, volume deletion,
Docker restart or recalculation is part of this rollback.

The sole acceptance/status authority remains `docs/handoff-3005/TRACKER.md`
in the controller checkout. Readiness and publication acknowledgement alone
do not establish browser latency acceptance.
