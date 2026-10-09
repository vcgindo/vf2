# Force Norm Change contract

> Retained family-source contract from25b4fad. Historical proof and approval statements below apply to that original delivery. Current3005 integration proof and limits are in [MDM_3005_CODE_DELIVERY.md](MDM_3005_CODE_DELIVERY.md); no fixture approval or runtime acceptance transfers implicitly.

Master13 only. Status and acceptance live exclusively in MIGRATION.md. This
document maps contracts, not another queue. Approved plan is retained byte-for-byte
in NMS_FORCE_NORM_DELIVERY_PLAN.md.

Authority: deployed VectorFlowAPIs.dll SHA256
0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346,
canonical ImportForceNormChange.sql, UpdateForceChangedNorms.sql,
UpdateNormChanges.sql, ClearForceNormChange.sql and NMSTaskStatusUpdate.sql.
The deployed-method extraction retained with the SOB/MOQ evidence is reused.
Native schema/config rows are independently verified against the retained stage2
manifest in D:/freshvcf-build/evidence/nms-force-norm-20261008-001/contract-pins-001.json
(SHA256 ee026fab3f180c484bfccf647dc3bc4eaa28ab4019d0390621afb0ed940483db).

| Operation | Authoritative owner / consumer | Required semantics and permitted seam |
|---|---|---|
| Configuration / eligibility | MasterMapper13 / UI_MDMConfig13 | Modify only. All sc/wc/nn visible and downloadable; only nn editable. New mta/config/mdm_force.json and families.py dispatch. |
| Current / filter / count / page / download | NMSAllItems.Norm, deployed MDMProcessor cases13 | Map Norm to nn; both permission scopes; RANK over selected fields preserves tied ranks. Reuse typed MdmSkuLocCurrent, no arbitrary report fallback. New force.py. |
| Modify / upload / validation / progress | UploadForceNormChange and DataValidation(action2) | sc/wc identify existing pairs; nn is int32. Keep native rejection and task forwarding. Existing unchanged ViewModify template includes all three fields. New force_tasks.py through existing endpoints. |
| Draft save / reload / delete | DraftFNCMaster | Native text nn retains malformed input and error/warning text. Existing draft machinery with typed master13 dispatch. |
| Submission / old values / assignment | TaskForceNormChange / TaskForceNormChangeHistory / UIUploadLogFNC | RequestedBy is user ID; history NewNorm snapshots NMSAllItems.Norm; exact native leaf assignment and task/subtask effects. Approval does not change DBM Norm. |
| Review / partial / comments / decisions | TaskStatusProcessor master13 | Existing requested/history joins and assigned scope. Preserve approve/reject/revert statuses, comments and native autocommit effects. New force_reads.py and force_tasks.py. |
| Approved request | ForceNormChange | Insert approved missing keys; existing rows update only NewNorm through ISNULL(NULLIF(value,''),old). Zero/NULL fallback and duplicate occurrences require native proof; do not infer Approved or RequestedBy updates. |
| Status / history / downloads | Existing tasks and native family13 history joins | Keep owner/approver authorization, date predicates and before/after wire values. Existing MasterUpdater/MasterApprover omit history screen; direct authenticated reads are distinct evidence. No new role grant or backdated task. |
| Frozen daily input | execute_day / daily_input / typed input tables | Capture master13 independently of inactive NMS import gate. One source-owned generation, own predecessor, frozen retry. New force_capture.py and typed runtime owners; minimal existing storage seam. |
| Calculation / export / diagnostics | timeline_controls → control_carry → r1_norm_updates | Use actual selected route unchanged: import, accepted stage, force stage, reason101, Norm/MinNorm export, failed-force diagnostics and canonical clear. No substitute calculator. |
| Publication / clear / task completion | Existing atomic finish boundary | Persist actual closing queue; clear only captured generations, retain later approvals including same-key/zero/NULL. Native clear may remove unapproved rows matching resulting Norm. Completion LEFT JOIN is independent of actual norm application; prove these separately. |
| Restart / rollback / retry | Typed relational input and output / existing run identity | Failed finalization rolls back owner effects; retry consumes same frozen image; completed readback runs no calculations. |

Typed native request, history, queue and upload-log fields retain NULLs and
occurrence order. Queue and request business keys are not unique constraints.
Internal source row IDs/revisions are metadata and cannot replace native fields.
Migrations follow0089 with unique names; existing applied migrations stay intact.

The proposed integration fixture is the registered scenario004 trial artifact,
ten retained SKU6120/location pairs, opening5June2026 and facts6/7June2026.
Its retained NMSActive=0 and FNC_MatchMasterNorm=1 would accept only matching raw
norm requests; all ten raw norms equal opening DBM norms. Direct human approval
to question call_41c8e71cd567475fbcb750bf95fc6e7b authorizes fixture-only
FNC_MatchMasterNorm=0. Freeze this one override in both modern/native inputs;
retain NMSActive=0 and the complete-day gate. This is not an engine change.
No calculated opening/closing values are synthesized. Test requested NewNorm is
an external command; date2 consumes date1's own persisted predecessor.

Upfront UI feasibility is source-established, not yet positive browser proof:
ViewModify excludes the column sidebar for ForceNormChange but its upload-modal
export selects displayed isDownload fields, which include sc/wc/nn. Existing
private frontend/auth/browser facilities and owned requester/approver may be
reused; separately owned master13 source and tasks are required. Actual template,
payload, malformed draft, approval and consumer evidence remains required under
the approved proof roster. Known native history restrictions remain limitations.

## Consolidated fixture and remaining-path qualification

Four direct human decisions bind source67: FNC_MatchMasterNorm=0 only;
retained consumer SL1–3/LL1–3; separate immutable ten-row current display; and
the same display values as the current-Norm input for one new submission's
native history UPDATE. The last proposal SHA is
32f4d257abbf2b008be5f59bcacd8b1fa9cb92bced4413765c9156c6c7a7dddd,
approved at call_862fe2dd4f914140aac62f5f86eb9521. Enable
VF_MTA_FORCE_HISTORY_FIXTURE with that exact SHA only for the new submission,
then disable it. Source identity and immutable display receipt are validated;
ordinary sources retain native NMSAllItems. Earlier task4_20261008215131 is
explicitly excluded and preserved. Operational NMSAllItems remains empty.

The complete remaining path was traced before the new submission: assigned
approver5 has both exact leaves; review joins requested/history by task and pair;
decisions scope each pair and insert only approved requests. The two requested
pairs have no retained phase/season blocks, import_non_nms=false, and both
NonNMS=false. The actual timeline route captures the complete queue, updates
Norm/log101/MinNorm/export, then applies canonical clear. Task completion is a
separate native status operation, never evidence of application by itself.
Date2 binds the same source to its own successful predecessor and queue/log
digests; raw facts remain retained and new_force_requests is empty on both days.
Missing optional report producers remain unavailable, without synthetic owners.
Requester task status and its decision download are reachable existing routes;
the role-hidden history screen remains explicitly unavailable. The display is
an opening fixture, so it cannot prove changed closing Norms; typed run/readback
and task status/download carry that proof. No additional concrete prerequisite
has been identified in this trace; execution and browser proof remain required.


Final acceptance: the remaining execution/browser proofs above are now recorded
in delivery-proof-index-004.json, two-date-terminal-proof-004.json and
final-consumer-proof-004.json. Both dates and their native control comparisons
passed. The unchanged download emits requested/old values with blank Comments
and Status cells; UI completion and typed decisions are separately evidenced.
All four explicit fixture qualifications and inactive-NMS scope still apply.
