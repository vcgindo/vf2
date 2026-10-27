# Remaining Step3 browser window and restoration proposal

Prepared for controller review after the retained-execution qualification.
This document does not authorize a window or change the sole tracker.

## Exact deployment

Use the qualified MTA image
`sha256:c2f91e4e96207b7956fd0e9fa9956837f59b0ca9263f5e8637fa9cc72823a762`
from source `3ed8c93f3c0e3fa3ddf8da2d690af6e3b1bc5de5`, with the existing auth
image `sha256:e1d1799408deafd33881af5d230aa7d4fe5ee08587f3dd974ce3a98ed71350ad`.
No additional image build, database, fixture, port or schema change is proposed.

| Resource | Exact identity and treatment |
| --- | --- |
| Original PG | `407fda1021836b322c9db248f9f91fab8ffc73c8351b6b0fb7ae2081b9b6a110`; preserve and temporarily stop only under the new window approval |
| Original MTA | `a17ae5637866d369bd2926126bbbce54d1e6915ad0304bf0165edbc503feb52f`; preserve and temporarily stop with its PG namespace |
| Existing temporary PG | `be20e1e0b0cf9293b5ce647d1e6a125cdf9608eb5e914d3b15a2aa6564c74283`; reuse, same image/volume, max_connections=16 |
| Existing baseline companion | `076707c60bc93e165f85102a04a6d35ac50ed5d13ebdf3cc89bcb7c014c782f1`; unchanged original MTA image in temporary PG namespace |
| Exclusive PG volume | `vectorflow-uptodbm-private-pg-20261025`; never run both PG containers against it |
| Frontend/gateway | `0b8926f73e3c60a01ffc3ee27ab8c3349b9dd9dd0dc5036497e6238ecb26e5f0`; change only the existing auth upstream during the window |
| Original auth | `f4910b8204c2b2a64589941bbe57eb64cc759b917a24f039150dd2c5835c937f`; preserve running |
| BPR database | `vftest_fresh_runtime_step3_bpr_20261027`, OID 737629 |
| DBM database | `vftest_fresh_runtime_step3_dbm_20261027`, OID 763077 |
| Auth database | `vftest_fresh_runtime_step3_auth_20261027`, OID 789829 |

PG remains 384 MiB/0.5 CPU; each MTA process/worker remains 4 GiB/2 CPU;
auth remains 512 MiB/0.5 CPU. Keep the current 5.5 GiB total/1,936 MiB growth
caps and 512 MiB reserve. Reuse internal networks and existing ports only,
restart=no, and exact owned-resource labels. Stage new containers from these
existing images only; retain all old containers and images.

## Preflight and window control

Before any serving mutation, recheck the qualified image/native manifest,
exact database identities, accepted phases and current action revisions,
original selected references, capacity and absence of another Step3 worker.
Check actual complete MTA/auth environments and roles; credentials remain in
existing secret files. Neither a successful HTTP health check nor a source
recipe test substitutes for selected-run readiness.

Prepare a new, uniquely named window record and restoration record. Do not
reuse old completed window2 or pg16 completion markers: their restore helpers
deliberately return once the historical DONE file exists. Adapt the existing
helpers to the new image, actual native identity, current limits, existing PG16
identity and fresh record names before activation. Preserve the old helpers
and their evidence. Old `continue-step3-terminal.py` also pins the superseded
18b9 image and must be adapted before use; do not run it unchanged.

Propose one 60-minute window. Start an independent hidden restoration watchdog
before stopping original PG/MTA. The same expiry governs the PG replacement
and gateway, with no implicit extension. Confirm exclusive volume ownership,
temporary PG health and unchanged baseline companion readiness before staging
the test services. Confirm candidate runtime/auth readiness and exact selected
run before nginx validation and the single upstream change. On preparation
failure, restore immediately. Capture PG memory/connections during the window;
prior PG16 observations do not establish new capacity or latency acceptance.

## Finite journey

1. On UptoBPR26, use Chrome browser controls only for positive Apply, Sleep and
   remark, refresh/readback and existing report interactions. Capture the
   actual trusted actor, action revision and immutable original publication
   preservation. Reuse unaffected supplier/research/guided/download evidence.
2. Stop candidate services before the worker. Continue that same run through
   PostBPR26 with current action revision and accepted-phase digest. Preserve
   the accepted prefix and all original files; verify terminal owner, outputs,
   histories, exact retry and next opening. Publish/select via existing owners
   and start fresh processes with the complete terminal environment.
3. Run only the already approved invalid27 diagnostic case on the BPR lineage.
   Verify its failed leaf, original diagnostic output and retained selected26
   readiness. Do not introduce a corrected successor or another fixture.
4. Switch through fresh complete configurations to the independent UptoDBM26
   database. Complete its browser actions/refreshed reads, then PostDBM through
   its existing terminal owner, preservation/readback and exact retry.
5. Restore the original stack and record the exact remaining matrix outcomes.

Record unprofiled click-to-usable-screen times for actions, Planning and export
interactions. Separate API/SQL timing from browser usability and tool gaps.
Do not claim matched legacy/large-dataset latency or scale acceptance from the
small retained fixture. Preserve the two approved NULL-amount/type-label limits.

## Exact restoration and stop conditions

Use a single restoration lock shared by manual failure and watchdog paths.
Restore the byte-identical original gateway, then stop only the current owned
test services/workers. Restore the original HBA bytes on the exclusively
mounted volume, stop the baseline companion and temporary PG, and verify PG16
is stopped before reconnecting/starting original PG. Restore its original
internal IP/alias and max_connections=10, then start original MTA. Confirm
original gateway/HBA hashes, original image/config/volume identities, all
unaffected service start identities and 8080 readiness. Record the two expected
PG/MTA restart timestamps explicitly.

The gateway's original file SHA256 is
`428ad8901a3356391143e53aec5502b4ce11156be4aae41365f16b4b1681d014`.
The existing original HBA file and its hash are pinned in the qualification
index. Never overwrite an unexpected gateway/HBA configuration.

Stop and restore on expiry, resource-limit failure, identity/ownership drift,
unexpected service failure, lost exclusive volume ownership or a failed required
business/preservation assertion. Retain partial evidence and accepted work;
do not reset, replay, expand fixtures or claim Step3 complete. Positive recovery
and terminal acceptance must be demonstrated by the actual ordered journey,
not inferred from the earlier rollback-only component checks.
