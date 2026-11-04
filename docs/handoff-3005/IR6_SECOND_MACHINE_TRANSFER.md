# IR6 Apr 10 transfer and validation

IR6 closed for human review on verified outputs. The next full-size validation
is deferred. Use the retained **Apr 8–9** starting state for that validation.
The already published Apr 10 runs and their measurements remain separate
evidence. The [existing tracker](TRACKER.md) records the decision and status.

## What passed and what remains

- The 97,097-pair Apr 10 baseline and original candidate matched all five
  typed persisted outputs, independently verified 20 report layers, the
  retained Apr 8–9 prefix and both full BTR CSVs. Each CSV is 19,729,878 bytes
  with SHA-256 `08867932b4a426c1ee92680c7dc375e92598b373a5fcbd33a5d791ad4592cbc9`.
- Original baseline/candidate operator clocks were 4,308.655/5,901.189 s,
  reporting 1,396.996/1,137.861 s, BTR preparation 518.380/121.960 s,
  database growth 3,541,655,552/3,012,861,952 bytes and WAL
  4,714,090,563/4,942,074,321 bytes. Peak observed process RSS was
  7,948,206,080/7,955,578,880 bytes. A matched baseline cgroup peak is unavailable.
- Migration `fresh_mta.0287_bound_rationing_lifetime_seal` fixes the
  stale-statistics commit plan. The old named constraint timed out at 15.002 s
  and the corrected constraint finished in 0.187 s on the same 97,097-fact
  rollback fixture. Seven PostgreSQL guard cases passed. The installed fix
  retained all three accepted run records, the Apr 10 selection and both
  exact exports. Post-fix full-size operator time is unmeasured.
- On the matched 12-pair, 94-day opening fixture, Oct 18 took 78.726/78.625 s.
  Oct 19 took 81.518/87.092 s. Its extra 5.573 s includes 2.904 s in report
  preparation, 1.252 s in input capture, 0.839 s in atomic persistence and
  0.578 s across the remaining work. BTR preparation accounts for 0.911 s
  within the reporting increase. The stage and CPU clocks show where time
  accrued. A single pair does not isolate an individual cause or establish
  timing variability. The candidate wrote zero physical BTR history rows
  on Oct 19, referencing 1,075 retained occurrences and 12 current ones.
  Its exact outputs and both CSVs matched. Mature elapsed-time improvement
  remains unmet and is recorded separately from the accepted correctness.

## Pinned private bundle

Transfer `ir6-apr10-e06b187e-20261105` through the approved local transfer
channel. It contains 91 files totaling 1,389,790,298 bytes excluding the
manifest. It has no credential files. The physical backup contains the
isolated database, including its role verifiers, and must be handled privately.

| Item | Identity |
|---|---|
| Starting MTA source | `1e0c64de5ffad8ca61dcf331c5b7bcaa9156dd86` |
| Starting MTA image | `sha256:0e028ddfe9a697e388009d201be5d012e5d14420af437135659eff7787a91628` |
| Part 1 baseline source | `ecada293649c10f172bb6c8be95fa1d41d562406` |
| Part 1 baseline image | `sha256:16c8bf24e816683c7ee143f7202d6bcd1afc70491c1d35a08f8ee0b122c331f0` |
| Fixed IR6 runtime source | `e06b187ede6de0b01ec36dabb626a7c1143501bf` |
| Fixed IR6 MTA image | `sha256:425bab9d65999baf84630bbc5c2360b8df04517080b09c5ea60eb62e8f293758` |
| PostgreSQL 16.15 image | `sha256:721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea` |
| Bundle manifest SHA-256 | `f917f19ca88e1df870f56cb6415c4fa5da59b62d84b590fdd31a5583286f86b4` |
| Apr 9 selected run | `851bc07e-0a86-4226-8e7e-6f9432b49c67` |
| Apr 9 output digest | `42e484dcd0081469a85904e60db872dd1fd99554e15b8f39f4e874a8fd2305bd` |
| Apr 9 selection digest | `6d667eb215aa68753822b385c71f0979796dbd46282957592fea5e0d2dfd397d` |

`postgres/` holds the original verified PostgreSQL base archive and backup
manifest. `work/` is the exact 64-file Apr 9 work tree.
`input/` contains the bound opening, permissions and frozen Apr 10 batch.
`images.tar` carries the four pinned images. `evidence/` carries the comparison
and seal receipts. `compose.transfer.json` is a path-parameterized copy of the
qualified MTA/PostgreSQL configuration. Keep the bundle read-only. Put working
Compose, secret and operation files in separate local directories.

## Preflight on each machine

1. Use a clean checkout of the handover branch. From it, run
   `python tools/verify_ir6_transfer.py <bundle-directory>` with Python 3.11
   or newer. Retain the success output with that machine's receipts. Run
   `docker image load -i <bundle-directory>/images.tar` and verify the four
   exact image IDs and Linux/amd64 platform with `docker image inspect`.
   The qualified environment uses Docker Desktop's containerd image store.
   If a different store resolves the archive to different IDs, stop at
   image verification.
2. Make a local copy of the tracked operator checkout or a separate worktree.
   Copy `compose.transfer.json` beside `vf.ps1` as `compose.private.json`.
   Set the values below in that checkout's private `.env` using absolute
   local paths. Each host must choose a unique project, dedicated private
   network, fresh named data/work volumes and a separate operations directory.
   Use PowerShell 7 for the matched protocol. The baseline and fixed MTA
   runtime commits are pinned independently of the documentation commit.

   ```dotenv
   COMPOSE_FILE=compose.private.json
   COMPOSE_PATH_SEPARATOR=;
   IR6_LOCAL_PROJECT=vf-ir6-next-unique-host
   IR6_LOCAL_SECRETS_DIR=D:/private/ir6-secrets
   IR6_TRANSFER_INPUT_DIR=D:/private/ir6-bundle/input
   IR6_LOCAL_OPERATIONS_DIR=D:/private/ir6-operations
   ```

3. Place the matching **isolated restore credentials** in the private local
   secrets directory using the filenames in the Compose `*_FILE` settings.
   Follow the [operator secret handling guidance](../../release/RUNBOOK.md).
   The values for existing database logins must match the archived roles.
   Obtain them separately from the authorized operator. A fresh password
   file alone cannot change a restored role. If the matching credentials are
   unavailable, stop before starting MTA. Do not reset roles or use production
   credentials. The backend validation requires no browser user or public port.
4. Verify capacity before creating volumes. The starting PG archive expands
   to about 6.69 GiB, plus 123 MiB of work files. Allow at least 13 GiB for
   that machine's growing validation volumes and reserve space for the
   required upgrade backup, image load and external receipts. Retain the
   42 GiB owned-volume and 52 GiB task stops and the 35/20 GiB free C:/D:
   floors. Record host/Docker VM resources and the qualified daily 9 GiB/2 CPU
   and PostgreSQL 1 GiB/1 CPU limits, with no extra swap. Confirm
   `docker compose --profile install --profile daily config --quiet`.
5. Follow the coordinated physical restore in [UPGRADE.md](../../release/UPGRADE.md).
   Use only the new owned volumes. Extract `base.tar.gz` into the empty data
   volume with the pinned PostgreSQL image, copy in `backup_manifest`, and run
   `pg_verifybackup` against that volume before starting PostgreSQL. Copy the
   full `work/` tree into the new work volume and verify the exact 64 file
   hashes. The work tree must be readable by UID/GID 10001. Preserve the
   archived database name `vftest_fresh_btr_copy64_9g_20261101` inside its own
   isolated cluster. Physical database identities must survive restore.
6. Start only the owned PostgreSQL first. From its private network, require
   an authenticated SQL query to the restored database confirming the
   database name, `pg_is_in_recovery() = false` and
   `transaction_read_only = off`. Then start the original MTA and run the
   existing `release.daily_serving_check` against the pinned Apr 9 run and
   output digest. Require readiness and the exact selection digest above.
   Use the [normal upgrade](../../release/UPGRADE.md) with
   `./vf.ps1 upgrade -Image <assigned-image-id>`. Verify the same Apr 9
   readiness and selected output afterward, and retain the backup and journal.
   For the fixed arm, confirm migration 0287 is present. There is no
   initialization on a restored cluster.

   ```powershell
   docker compose exec -T mta python -m release.daily_serving_check --run-id 851bc07e-0a86-4226-8e7e-6f9432b49c67 --output-digest 42e484dcd0081469a85904e60db872dd1fd99554e15b8f39f4e874a8fd2305bd
   ```

## Two-machine start gate

Both machines must record the exact bundle verification, loaded image IDs,
backup and work verification, cold restore, original and target Apr 9
readiness, and ownership/capacity checks **before either starts Apr 10**.
The controller records the two assigned image IDs and the intended comparison
before releasing one independently isolated full-size validation per machine.
If the two machines run different images or have different hardware, disclose
those conditions when interpreting wall time. A parallel result across
different hosts cannot isolate the software's timing effect.

Run `./vf.ps1 csv-day 2026-04-10` once in each released clone. Use the
[normal daily run and recovery rules](../../release/CSV_DAILY_RUN.md).
Retain the operator clock, per-stage clocks, database growth, WAL, process
RSS and cgroup observations. Keep independent readback outside the operator
clock. Require PUBLISHED/FINISHED and run-bound HTTP readiness, then verify
all five outputs, the 20-layer audit, both full CSVs and the preserved prefix.
For an interrupted upgrade or post-commit publication failure, reconcile
the actual journal and database first and use the supported resume on that
same clone. No automatic calculation retry, day replay, reset, public
exposure or Part 2 work follows from this handover.
