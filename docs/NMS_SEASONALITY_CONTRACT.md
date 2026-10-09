# Seasonality native contract and feasibility

> Retained family-source contract from25b4fad. Historical proof and approval statements below apply to that original delivery. Current3005 integration proof and limits are in [MDM_3005_CODE_DELIVERY.md](MDM_3005_CODE_DELIVERY.md); no fixture approval or runtime acceptance transfers implicitly.

Latest human scope (9 October 2026, controller turns01a11d68-bcaf and01a11d68-e701)
supersedes remaining trial/test requirements below: deliver only the direct
source-mapped port, document limits, commit/push and stop. Historical proof rosters
and plans describe earlier scope; they authorize no further execution.
**Source-mapped port delivered; unverified under latest human scope.**


Scope authority: NMS_SEASONALITY_DELIVERY_PLAN.md, pinned SHA
fa4a28f9dafa35305f344e27a0938260bec4b70ae8062693253e6074fb9d3f38.
Status is maintained ONLY in MIGRATION.md. This document is a contract map.
The three scoped fixtures below are approved; none is installed yet and no
business date has executed for this cohort.

## Existing calculation and storage boundary

The registered scenario004 opening is5June2026, with empty Importer season
requests and DBM Seasonality, original NMSActive0 and FNC_MatchMasterNorm1.
Keep those flags; the Force flag exception is neither needed nor transferred.
Ten retained SKU6120/location identities remain the candidate population.
User season requests are external facts; calculated OrigNorm/NewNorm/Type/Status/
LastProcessedOn and histories must be produced by the existing engine.

ValidateAndProcessInputData.bat places ValidateSeasonalityData after master/daily,
accepted/force/exclusion/phase validations and before NormChangesRun. The current
temporal chain has collect/process/apply, but lacks this importer validation.
Its exact201/202/204/205/206 rejection rows, deletion order, approved-input early
return, NULL comparisons and scratch effects require a bounded direct port and
native fixture proof. Existing season processing arithmetic is reused unchanged.

chain.py refreshes shared controls from prior DBM state, including Seasonality;
therefore a status action must update the authoritative working producer state,
not a discarded controls-only copy. timeline_controls.py executes CollectSeasonality,
ProcessSeasonality, ApplySeasonality before force controls. Closing state already
has typed DBM Seasonality, control seasonality, control_aux season_requests/status,
NormChangeLogTbl, DailyConsumption, LastBatchRunTbl and ReasonCodes. Graph readers
must use this explicit owned publication and full native joins, never fabricated
history or an older convenient run.

## Workflow distinctions

ADD11/12 approval writes Importer.Seasonality. New rows default ActivateDBM0;
existing six seasonal fields use native zero/NULL fallback. Daily validation and
collector consume those requests; approved history alone is not an effect proof.

STOP/RESUME10 approval updates existing DBM.Seasonality Status/Comment directly
from its requested status snapshot (stop23, resume-1). Its child task is immediately
DB Updated4/5, unlike ADD11/12 children2/3 awaiting daily completion. Daily task
completion11/12 checks approved history, not successful Norm application. Owner
reconciliation must retain the committed calculation state, layer only approved
status changes in live typed state, freeze them for the next calculation and
preserve decisions arriving after capture. It may not replace Norm/history.

## Reuse and fixed proof boundaries

retained-season-proof-scope-001.json binds existing current-day, exact-EndDate
and phase-conflict receipts. Their r1_seasonality.py source hash exactly matches
f085beeb76076df509b18d7b43071589a63a9a390a10294aca516b3a10642665.
They prove selected collector/process/apply checkpoints, not importer validation,
UI approvals or the new temporal integration. Reuse only their exact scope.
The six S3 groups in the approved plan are the fixed proof roster.

## Admitted prerequisites and route matrix

Direct human answer "Approve consolidated Seasonality fixtures" to
call_b54a0359e44d4719885a37c5f695ee9f:0 admits only proposal
93ecfb5222e60759eedd9c84a0e2fb6496b35660a444f2d04bb9f4b0301f6763:
request-scoped June5 noon validation clock for ADD11/12; retained SL1-3/LL1-3
consumer hierarchy; immutable opening ten-pair Norms for upload eligibility only.
No current-display/history substitution, calculation-input change or grant change.
Actual task/approval/database clocks remain real. Current and graph use actual
owned outputs. NMSActive0/FNC_MatchMasterNorm1 remain original.

| Operation | Native authority and owner | Required handoff/proof |
| --- | --- | --- |
| Config/template | MasterMapper and UI_MDMConfig10/11/12 | Exact three mapper/30 config rows; untouched client headers |
| ADD validation/progress/draft | Existing absolute/percentage schemas; shared DraftSeasonalityMaster | Request clock only11/12; malformed error export, draft recovery; backend progress and native generic loading |
| Submit/forward/assignment | UploadSeasonality; TaskSeasonality/History | Original six/seven input fields, NULL ActivateDBM default0, scoped pairs, assigned approvers |
| Review/partial decisions/comments/revert | UpdateApprovedData; typed requested/history/Importer Seasonality | Native NULL/zero fallback, reject/revert; browser approve/reject, revert focused transaction only |
| STOP/RESUME10 | StopResumeSeasonality; TaskSeasonalityStopResume/History | Full actual state snapshot, old history; exact stop23/other-1, status/comment only approval |
| Frozen input | Own source/revisions and latest persisted predecessor | Full approved queue and live status state, typed capture, exact replay and later-decision preservation |
| Calculation | ValidateSeasonalityData then Collect/Process/Apply | Canonical validation placement, unchanged arithmetic; actual positive date1 and stopped own date2 |
| Atomic closing | execute_day/typed run rows/source owner | Consumed generations and new current state advance only on success; rollback/frozen retry proofs |
| Current/filter/count/page | GetMasterData SeasonalityStatus | Actual DBM.Seasonality+DBMMaster/scoped descriptions, ROW_NUMBER sc,wc, native NULLs |
| Graph | GetSeasonalityDetails -> GetSeasonalityGraph | Actual NormChangeLog/Seasonality/LastBatchRun/ReasonCodes/DBMMaster and TOP180 daily rows; preserve missing-source response |
| Status/history/download | NMSTaskStatusUpdate and existing task readers | ADD children2/3 until daily completion; status actions4/5 immediately; actual bytes/cells |

Exact method IL/source hashes are pinned by seasonality-method-provenance-001.json
SHA5c0642b251b4eb041ebfe8682099b7decea97dc56fe0b460adda77ada0c92eef.
Canonical config receipt canonical-config-read-001.json SHA
b884040a7d524c1d0aa54bf69ef6338c50e7597fa7731bc1469af3aec70d32fb
executes exact INSERT statements against canonical DDL in connection-private SQL
temporary tables; no persistent database writes. Existing stored actor scopes
(requester4/approver5 root71001/72001) cover all retained ten pairs; no grants.

Positive candidate requests: SKU6120/DP010290 absolute201; SKU6120/DP020819
percentage20 cap200; both June6-June20 and buildup6. SKU6120/AG515802 is the
separate rejected control. These are synthetic user requests, not output seeds.
After produced date1 use actual eligible status for STOP, then date2 own
predecessor. RESUME proof follows date2 with no third business invocation.
Freeze inputs only after typed implementation and focused gates are ready.

Unchanged UI qualifications: use generic Add/View cards (named Seasonality button
is a no-op); default roles do not expose history navigation; detailed progress
polling is disabled; browser review offers approve/reject but not revert.
Downloads preserve native blank Comments/Status where applicable. These are
acceptance qualifications, not silently repaired behavior.

ADD11/12 saved drafts return native raw column names because their configuration
has no IsDownload columns. The unchanged browser expects aliases and reopens
blank cells. Exact native projection and retained save/read rows pass; usable
draft recovery does not. Direct human approval call_26586e466f4840d2820b9e4e66cc1dba:0
accepts this limitation and fresh uploads for the trial, with all other exits
retained. Evidence: native-draft-projection-001.json in the Seasonality evidence
directory; source disposition is recorded in LEGACY_EXCEPTIONS.md.

Fixed S3 proof roster is exactly the plan's six groups. Reuse the pinned math
receipts only for their shown cases; cover missing validation/types/NULL/cap cases
with bounded native transactions. No full-day or active-NMS parity claim.

The two-date affected comparator records the clock representation boundary:
native Seasonality SQL reads current-day LastBatchRunTbl, while modern seasonal
functions receive the current date explicitly and retain the predecessor date
in the control carrier until control_stages advances it. Preserve both raw
carriers and verify the resolved business date; do not call those intermediate
carrier values equal. Compare LastBatch strictly after the canonical control
tail, along with the complete modeled affected bags and validation rejects.

Each business dispatch must use one exact-worker immediate DNS/auth/schema/source/
input/predecessor/evidence/finish preflight. No image-only readiness assumption.
Existing Force adapter2f8c7400d0a9a34790d881fc477067c050a189a9c6d6b664b3cff03d40c1a8eb
must remain admitted only for its original family roster after shared changes.

## Delivered source map and operator handoff

| Canonical operation | Modern implementation |
| --- | --- |
| MasterMapper/UI_MDMConfig10/11/12 | mta/config/mdm_season.json; mta/mdm/season_configuration.py; season.py, season_absolute.py, season_percentage.py |
| UploadSeasonality / StopResumeSeasonality / UpdateApprovedData | mta/mdm/season_tasks.py; season_revisions.py; typed requested/history/current owners |
| DraftSeasonalityMaster native projection | mta/mdm/drafts.py; mta/runtime/mdm_season_models.py |
| GetMasterData / GetSeasonalityGraph / task projections | mta/mdm/season_current.py; season_reads.py; presentation/mdm_views.py and urls.py |
| ValidateSeasonalityData.sql | mta/application/seasonality_validation.py; opt-in temporal/chain.py before existing Seasonality collector |
| Collect/Process/ApplySeasonality | Existing unchanged mta/application/r1_seasonality.py via timeline_control_stages |
| Approved input, own predecessor, atomic closing | mta/mdm/season_capture.py; daily_input.py; runtime/temporal.py; typed input_storage.py/input_tables.py |
| Source/config ownership and installation | mta/mdm/season_source.py; daily_source.py; families.py |

The source installer is deliberately limited to the approved registered source and
three approved fixture scopes. It is not a general production onboarding path.
Existing role and authenticated scope checks remain. Native zero/NULL fallback,
ActivateDBM default0, exact STOP23/RESUME-1 effects and native field ownership remain.
The frontend, canonical SQL and seasonal arithmetic are unchanged.

Migrations0096–0098 follow0095 and add typed seasonal owners, input/capture guards
and immutable eligibility guards. They must be reconciled with sibling migrations
before any mainline integration. Shared seams are families/drafts, daily source/input,
runtime model imports/typed input storage, execute_day and the graph URL. This
branch is not merged or deployed. Do not fake migrations or reset installed sources.

Reader availability: season_current.publication requires the existing strict
selected_run acceptance and the exact installed owner's last_run. The withdrawn
trial-only native-receipt fallback is not shipped. A computation-only June6 result
cannot enable current/graph or master10 review/download through this gate. Those
actual-output browser paths and June7/STOP/RESUME temporal acceptance are unverified.
Source-mapped implementation must not be represented as runnable product acceptance.

Preserved private facility: source68; PostgreSQL freshvcf_nms_sob_moq_001; API
freshvcf-nms-season-mta-001 uses python manage.py runserver 0.0.0.0:8000 --noreload,
base image sha256:be53e87caac650d9e51d045830e63f376421a21c8b45c65947752c49a0cf6ed0
plus this read-only checkout. It is not a standalone image or production server.
No publication is selected there. Existing private auth/frontend remain as last
used; browser authentication may expire. No public ports or protected serving
instances were changed. Do not execute prepared scripts or restart/cut over services
under this delivery; future operational execution requires a separate task scope.

At scope change the already-running June6 worker completed, run
049fa6af-78fd-4f3b-b876-3990d2569f75, COMPUTED_NOT_YET_PARITY. Its receipt and all
failed/prepared evidence remain under D:/freshvcf-build/evidence/nms-seasonality-20261009-001.
Modern invocation total1; native actual0; no June7 dispatch. Final Git source differs
from the trial worker pins after withdrawal of the cancelled admission helper/tests
and final documentation/formatting updates; do not reuse that worker receipt to certify the
final tree. No new tests were run after the scope change. Prior passing receipts
retain their original limited meaning and do not establish end-to-end parity.
