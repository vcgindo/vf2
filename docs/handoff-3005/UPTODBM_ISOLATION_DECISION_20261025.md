# UptoDBM native trial isolation

This is a decision record, not a second tracker. Status and authorization belong
only to `F:/freshvcf/docs/handoff-3005/TRACKER.md`.

## Decision

The approved fresh 25 October UptoDBM trial must inherit the exact completed
24 October run `e0735ad3-b98d-45c5-9bad-38bc5b0e5df8` without invalidating the
terminal application currently serving 8080. Recommend one temporary private
physical PostgreSQL copy. Execution requires the resource exception below.

Advancing PRE_BPR in the serving database changes the force, season, stop/PIPO
and phase-control owners' last_run. `integration_source.require_current_run`
requires those owners to match the selected successful terminal run. Therefore
preserving the selection file alone would not preserve working MDM.

A logical restore preserves row contents but changes database OID/name; native
ingestion and namespace admission bind those identities. There is no supported
native relocation command. Rewriting registrations or recreating initialization
would introduce a larger, unqualified contract. A physical copy preserves the
database and role OIDs, registration, captured inputs and accepted predecessor.

## Exact source and proposed resources

Read-only inspection identified source PostgreSQL container
`5476f2e5a1b89320924b6902a8729433cc882949cd7d5ee5718c75ee0f356c45`,
image `sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea`,
PostgreSQL 16.15, started `2026-10-25T05:32:38.645519548Z`, volume
`vectorflow-lifecycle-test-pg-disk-20261024`, no public ports, restart=no.
Source PGDATA is approximately 974 MiB, with no external tablespaces.
Database `vftest_fresh_lifecycleg2_uptobprui_20261025` has OID 402363;
cluster system identifier is `7699958112730423333`.

Proposed exclusively owned names (must be absent before creation):

- Container `vectorflow-uptodbm-private-pg-20261025`, same pinned PG image,
  network=none, no ports or serving DNS alias, restart=no, 384 MiB, 0.5 CPU,
  128 PIDs, read-only root filesystem, shared_buffers=32MiB, max_connections=10.
- Volume `vectorflow-uptodbm-private-pg-20261025`.
- A bounded extraction/verification utility: 128 MiB, 0.25 CPU, no ports.
- A single native worker sharing only the clone network namespace: existing
  4 GiB/2 CPU ceiling, no ports and no simultaneous native worker.
- Archive/evidence under
  `D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/uptodbm-private-20261025`.
  Monitor a 4 GiB total ceiling for the new archive, restored volume and files;
  stop before exceeding it. Preserve partial evidence rather than deleting it.
- All new resources labelled for owner `01a168f1-c177-7f92-bf54-e73aae1d6f77`
  and this trial. No source resource increase.

Observed source limits are about 15.45 GiB/16 CPUs, different from the older
storage-move script. They are not the proposed clone limits and will not be
changed. Source max_connections=10 and a read-only snapshot observed 9 total
connections; fresh connection/headroom checks are required before capture.

## Capture and proof gates

1. Recheck exact source identity/start time, ownership, no active scoped writer,
   predecessor input/output/phase/history identities, absence of terminal
   commands, serving selection and 8080 readiness. Verify disk/headroom,
   connections, WAL retention and absence of new resource names. A mismatch
   stops before any mutation.
2. Source has pg_basebackup/pg_verifybackup, wal_level=replica and ten WAL senders,
   but no replication HBA rule. With explicit approval only, retain exact HBA
   bytes, temporarily add `local replication postgres trust`, reload (no
   restart), and verify parsed rules. Restore exact original bytes and reload
   immediately after capture, including failure cleanup. No credentials or
   roles change. Do not clobber a concurrent HBA edit: stop and report it.
3. Use matching pg_basebackup via the local socket: tar output, WAL fetch,
   spread checkpoint, SHA256 manifest, transfer cap 16 MiB/s, no password prompt,
   no replication slot or standby configuration. Stream to the new archive.
   WAL retention must be sufficient; no implicit wal_keep_size change is allowed.
4. Extract only into the new owned volume and verify the complete manifest with
   matching pg_verifybackup before starting the clone. Retain archive hash and
   verification output. Never mount the serving PGDATA into the clone.
5. Before calculations, verify system identifier, DB name/OID, role OIDs,
   namespace/authority/catalogue and all accepted predecessor/phase/history
   identities and native readback. Exact accepted file paths must remain visible
   read-only; new day output uses a separate owned root. No old output is copied
   into new input facts. Candidate migrations and supported code release
   transition affect only this clone.
6. Run only the approved fresh UptoDBM trial and its scoped read/action/retry
   proofs; do not run BTR, finalize, or implicitly release PostDBM. Stop the
   temporary resources after the test boundary and retain their volume/evidence.
   No automatic 8080 selection, route change or deployment follows.

Backup portability and native qualification remain proof gates, not claims.
This capture does not itself prove native Full/split equality, interrupted
execution recovery, scale performance or production site configuration.

The source reports wal_keep_size=0 and min/max_wal_size=32MB. The capture driver
does not alter these serving settings: it requires no active scope worker,
monitors WAL generation, aborts above an 8 MiB concurrent-write budget, and
requires successful complete backup/manifest verification before any clone can
start. This is fail-closed capture, not a claim of guaranteed WAL retention.
PostgreSQL documents that tar-to-stdout supports WAL fetch and that a fetch
backup fails if needed WAL has been recycled:
[PostgreSQL 16 pg_basebackup](https://www.postgresql.org/docs/16/app-pgbasebackup.html).

## Required exception

The project rule says "One isolated test stack". This proposal temporarily adds
one private PG resource, its bounded utility/worker and fresh storage, and makes
one reversible local replication HBA change on the owned source. It therefore
requires explicit human approval. All business data, source schema, credentials,
frontend design, MTO API, serving PG and 8080 remain preserved.
