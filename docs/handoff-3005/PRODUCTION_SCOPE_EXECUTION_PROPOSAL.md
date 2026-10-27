# VectorFLOW: isolated scope proof resources

**Approved, with sizing superseded by direct human direction on 28 October 2026.** The original approved version is retained at commit `2c5add06`, SHA256 `a18cdbca3883b4713478ac1b7599f70cec369d84bd4700e375b91e20e4942b66`. The human subsequently authorized practical RAM and disk sizing from actual capacity, without further small-slice approval loops (controller turn `01a17f1a-4714-7153-93b2-b7cc6132d188`).

Current bounded profile: **6 GiB additional operation storage**, one active builder or worker at **4 GiB / 2 CPU**, and isolated PostgreSQL at **512 MiB / 1 CPU**. Memory-plus-swap equals each memory limit. Fresh observations showed about 10.8 GiB available engine memory and C:51.10/D:58.96 GiB free; require ample remaining host/engine headroom before launch. The original two-build and ten-logical-day/fourteen-producing-invocation limits remain binding. Keep existing spending, baselines, global reserve and protected services. Record actual use with the existing measurements; the former 2 GiB and individual disk slices below are historical planning values and no longer block the approved finite proof. Adjust practical sizing only from fresh measured need, without unbounded growth or consuming other owners' capacity.

The large Terra/manual clean installation and final exercised-command acceptance belong to the human and are outside the agent goal. Candidate image, small real PostgreSQL/native proof and an accurate manual guide remain required. This authorizes no 8080 change.

## Requested operation

Provision one isolated PostgreSQL container, one private network and owned volume, and run one proof worker at a time. Use real normal database names in that isolated server: `vectorflow_baseline`, `vectorflow_mta`, `vectorflow_placement`, `vectorflow_bpr`, `vectorflow_dbm`. Each has its own registered namespace, restricted roles, initialization and predecessor chain. None shares data with a serving database. Create no public port mappings. Use restart policy `no` throughout.

Names: `vectorflow-generic-scope-pg-20261028`, network `vectorflow-generic-scope-private-20261028`, volume `vectorflow-generic-scope-pgdata-20261028`, and sequential workers prefixed `vectorflow-generic-scope-proof-20261028-`. Refuse any existing name or conflicting ownership. New receipts and private working inputs go only under `D:/freshvcf-build/evidence/production-generic-scope-20261028`. Credentials are generated into protected external files and never printed or committed.

PostgreSQL uses the already retained PG16 image `721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea`, capped at **384 MiB / 0.5 CPU**, `shared_buffers=32MB`, `max_connections=16`, `max_wal_size=32MB`, `min_wal_size=32MB`. The one active native worker is capped at **4 GiB / 2 CPU**, without swap expansion. No simultaneous producer workers. Retain all containers/volumes/evidence after stopping them; no prune, deletion or reclaim is authorized.

## Original disk allocation (superseded sizing)

Request **2,048 MiB additional cumulative allocation**, charged to the same accounting basis as the existing protected baseline. This would raise the total ceiling from 6,068 to **8,116 MiB** and cumulative growth from 2,372 to **4,420 MiB**. The existing **512 MiB global reserve**, original baseline **3,853,159,872 bytes**, frozen Step 4 reservation **192,686,244 bytes**, previous failure evidence and all existing spending remain charged. This is not permission to spend their unused reserves.

| New allocation | Maximum MiB |
| --- | ---: |
| At most two retained candidate image generations, including all newly attributable layers | 1,024 |
| Newly attributable build cache/export work | 128 |
| Five small databases, schema and non-WAL PostgreSQL files | 480 |
| WAL | 64 |
| Compressed proof evidence and failed-attempt diagnostics | 128 |
| Worker/container writable files and bounded logs | 64 |
| Private input copies, configuration and secret files | 64 |
| Unspent operation reserve | 96 |
| **Total** | **2,048** |

Before any allocation, refresh exact image/storage ownership, volume/database absence, host/engine capacity, protected service fingerprints and all existing cumulative accounting. The read-only preparation observed free space C:51.22/D:58.87/F:17.31/I:74.06 GiB; these observations are not a fresh execution gate. Docker reported 346 images/57.56 GB, 288 containers/1.743 GB, 136 volumes/47.26 GB and build cache 8.856 GB; none is reclaimable by this task's authority. Charge actual attributable storage, every retained candidate/failure and evidence write. Refuse before an operation if its remaining bound and reserve cannot fit. Never reset a baseline or silently exclude shared storage, failed output or logs.

## Inputs and finite proof

Use the retained repository package `examples/starter-data/vectorflow-starter-inputs-v1.zip`, SHA256 `71bb16ec321d7ee683ddfca718f129451a36df9ee5540abdb4b2329ba1a5b63f`, containing `initialization.json`, `day-01.json`, `day-02.json`, permissions and README (666,985 expanded bytes). Its opening explicitly uses `generic-finalization-active-nms-v1`. Use the existing supported CSV conversion, checking the complete reconstructed typed values against those retained files. No new business facts or larger dataset are generated. Supply the newly supported generic scope configuration as installation metadata using the qualified report roster. Preserve the source package and every independent installation's working inputs.

Run the frozen ordinary Full baseline, candidate ordinary Full, candidate placement Full, UptoBPR→PostBPR and UptoDBM→PostDBM on the same two dates, each independently initialized. The baseline uses an exact retained native release capable of the frozen Full contract; verify its source and command support before execution. If no retained release admits that contract, stop that arm and report the precise gap rather than silently using the candidate as its own before-image. Freeze the candidate commit, native source manifest, image identity and all commands before launch.

Bound producing work to **ten logical daily runs / fourteen Full-or-scope producer invocations** across those five arms. Each arm computes its own successor. Accepted old Step 3/4 calculations are never resumed or rerun. No manual business action is inferred; use retained input policy, and check nonempty relevant histories/actions in small focused tests where the fixture supports them. A missing witness remains a gap, not a count-based pass.

Include real fresh/forward migration checks and affected PostgreSQL tests; normal-name versus foreign OID/role/certificate/source/configuration rejection; exact phase/action/report/archive ownership; typed closing/history/NULL/duplicate/order and next-opening comparison; canonical representative rule checks; actual report count/filter/read/export bytes; and same-run stale selection rejection. Record the installed SQL bodies and preserve old serialized contracts.

Use transaction rollback for negative guard tests. Limit crash checkpoints to before the native call, after native commit/before local acknowledgement, during preparation, and after selection/before acknowledgement. Invoke only supported nonproducing reconciliation/serving recovery after a committed producer. Any uncertain native ownership stops that arm. The request does not authorize speculative producing retries, extra business dates, accepted-run resets or accepted-file regeneration to force comparison.

## Build and stop rules

First finish focused source checks and resolve the earliest contract failures. Then build one passing candidate. A second retained candidate build is allowed only for a concrete defect found by this finite proof, with the changed boundary and affected regression checks recorded first. At most two image generations, both charged and retained. If more changes/builds or producing invocations are needed, stop the affected operation and report the exact reason; do not start a broad rebuild campaign.

The worker may run the isolated MTA internally for native readiness/report checks on the private network. This request includes no frontend/auth replacement, host port, browser automation, production schedule or large-data producer. The human's manual Stage 5 installation/rehearsal and any later 8080 deployment retain their separate authority.

Stop producing work on a semantic/authorization mismatch, changed protected fingerprint, missing original source/input pin, unsupported client policy, resource pressure, exceeded slice, unexpected duplicate effect/file, or uncertain commit. Preserve failures. Stop only the newly owned worker/PG when finished or on an unsafe condition. Recovery may restore an admitted service selection only if its current business ownership is still valid; never restore/rewrite business data or downgrade an incompatible schema.

## Approval wording

Approve this single finite isolated resource and execution package: the additional 2,048 MiB cumulative allocation and exact slices above, one private PostgreSQL server with five owned normal-name databases, one bounded worker at a time, at most two candidate builds, and the specified two-date integrated/migration/recovery proof. Preserve all existing resources, data and evidence, keep GulfOil client processing excluded, and leave fast 8080 unchanged. The source implementation may continue while this operational decision is pending.
