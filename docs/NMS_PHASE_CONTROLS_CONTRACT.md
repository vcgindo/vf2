# Masters7–9 phase controls: source-mapped port

> Retained family-source contract from25b4fad. Historical proof and approval statements below apply to that original delivery. Current3005 integration proof and limits are in [MDM_3005_CODE_DELIVERY.md](MDM_3005_CODE_DELIVERY.md); no fixture approval or runtime acceptance transfers implicitly.

9 October 2026. **Source-mapped port delivered, UNVERIFIED.** Combined ADD-only
AddPO7, AddPIPO8 and AddTargetNorm9 approved in controller
turn01a11d9e-7a45-7c13-bff1-a8f6eee3ab5f, from1b837a7 on codex/nms-sob-moq.
MIGRATION.md is the sole tracker; the retained plan's pending-approval wording
was superseded by that human approval. No runtime acceptance is implied.

## Source identities

Canonical root: F:/VFlow_Local/local-runtime/mta-engine. Deployed DLL SHA256:
0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346.
Matched extractions are in D:/freshvcf-build/evidence/nms-sob-moq-20261008-001.

| Source | SHA256 |
| --- | --- |
| MDMProcessor.deployed.cs | f46e2fc1db36007ee29ea2de4574eca2017ceea268db55eea6b62fa9b16779c8 |
| TaskStatusProcessor.deployed.cs | 37d67850dcf255961643435b9079df858929a51876b5c6bad12d1e9761c6bc76 |
| MasterMapper_2.0.sql | f6c3c800e643fd01101397c864bfc21eddf2f7fbb374287068d39aef83ceb967 |
| UI_MDMConfig_2.0.sql | ffda9ff6f3395746303432eb24ef2f4aa63aa1cc7ba0a403d11fea8a3c6131dc |
| ValidatePhaseout.sql | 81ad0e7a1cbc22889177944b97b12aafd0c61aa430d0060e2cc5b3b1723f7e9c |
| ValidatePhaseInNorms.sql | aba39a9f1590db4ae75a6da3dd0738a47fe1cb5273a154a40c5921d807b82f2e |
| NMSTaskStatusUpdate.sql | 99836bcf74c618350924bf02e21dea30cbe4cc9d6022f859f5c1c6cfca10dbe8 |

Modern mta/config/mdm_phase_controls.json retains three mapper and eight config
rows, including IsDownload=false. Each owner receipt pins its byte SHA256.

## Operation and ownership map

Modern paths below are relative to mta.

| Operation | Canonical authority | Modern implementation |
| --- | --- | --- |
| ADD config:7 sc/wc,8 sc/wc/pi,9 sc/wc/tn | Mapper41/47/53; UI config158–180 | mdm/phase_controls_configuration.py, add_po/add_pipo/add_target_norm facades and families.py |
| No current/count route | GetData/GetDataCount omit7–9 | Facades retain empty response; no current/filter/pagination API invented |
| Shared draft save/read/delete | DraftAddPIPOMaster DDL4310; draft handlers | MdmDraftAddPipo and existing mdm/drafts.py: per-master write aliases, raw reload, text TargetNorm, no IsSelected |
| Submission, validation, forwarding, assignment | UploadPIPO1606; DataValidation1037; GetValuesSPF1162 | mdm/phase_controls_tasks.py: pair/hierarchy validation, first-row columns, batches999, task/subtask owners |
| Review/count/page/download/history | TaskStatusProcessor review822–899, download2246–2298 and shared history methods | mdm/phase_controls_reads.py: aliases, NULL omission, join multiplicity, ordering and date predicates |
| Decisions/comments/status/approved queue | UpdateApprovedData2624–2661 | phase_controls_tasks.py: shared MdmPhaseOutRequested/History/Queue for7/8; separate MdmPhaseInNormRequested/History/Queue for9 |
| Importer prerequisites | ValidateAndProcessInputData.bat33/35 and selected validators | application/phase_input_validation.py, opted-in temporal/chain.py step before seasonal validation and phase calculation |
| Frozen input and clear | PhaseOut/PhaseInNorms schema; Collect/ProcessPhaseOut, Collect/ProcessPhaseIn, ClearPhaseInPhaseOutData | mdm/phase_controls_source/capture/revisions.py, daily_input.py, runtime/temporal.py; unchanged r1_phase_out/r1_phase_in/r1_phase_entry/timeline_controls engines |
| Daily task completion/retention | NMSTaskStatusUpdate259–286 and completed-task prune | PhaseOut history snapshot and existing daily completion/prune infrastructure |

Approval inserts approved missing pairs against the old target:7 selects NULL
PhaseInSKUCode,8 selects non-NULL. Incoming duplicates survive that anti-join.
Existing target rows are not updated; reject/revert does not remove queued input.
Approval joins use only SKU/location, not pi/tn. Native requested/history ActionType2
under ADD/action1 headers is retained. Both histories use nullable text ApprovedBy.

Importer validation trims only specified columns, applies DISTINCT, removes blank
rows, records native warnings/rejections and whole-feed rejection for NULL keys,
same phase-in/out SKU, multiple phase-in rows, stop conflicts and invalid target
rows. A PhaseOut/PhaseOutStop conflict clears both feeds. Only new explicitly owned
capture opts in; earlier accepted runs and standalone master6 are not replayed or
automatically opted in. Formulas, phase mapping, stock/GIT rules, Norm calculation
and reason102/103 logs are unchanged.

The native daily “Phase In Norm” status step joins TaskPhaseOutHistory. Normal
master9 history alone therefore does not advance its subtask to DB Updated. This
limitation is preserved. PhaseOut task completion has no successful-output predicate
and does not prove successful phase calculation.

## Ownership and integration limits

Explicit phase_controls_source.bind requires an admitted source, accepted selected
publication, same-source consumed capture, no accepted direct successor and no
pending capture. All three owners bind together from that source's remaining own
closing input. No phase/Norm/history output is seeded. No binding was executed.
Root onboarding remains registered-fixture-only; general production onboarding and
an accepted same-source publication remain prerequisites. Strict readers and seals
are unchanged. Previous fixture exceptions do not transfer. The exact1b837a7 adapter
identity remains recognized; new families need their own additional receipt.

Capture freezes every queue occurrence, task revision and own-predecessor run/output/
closing digest. It feeds control_requests.phase_requests/phase_in_requests once,
replacing corresponding carry to avoid double input. Existing frozen retry reuses
the snapshot. Finalization records original typed occurrences and reconstructs only
the actual remaining input after normalization/clear; later additions remain pending.
Later decisions defer affected task completion. Reconstruction does not invent a
winning original ordinal for DISTINCT results.

Hand-authored migration0100 follows0099: eleven Django models and three typed input
tables, with source decision/generation, immutable input and owned-consumption guards.
JSON holds bounded binding metadata only. Shared files: family dispatch, daily_source/
daily_input, model registration, typed input mapping, runtime temporal handoff and the
opted-in importer step. The shared prune roster includes every declared family owner,
including existing master6. Migration0100 is unapplied and unverified.

Inherited requester/reviewer/scope checks go beyond crafted direct DLL calls.
Conflicting duplicate decisions and collation-equal DISTINCT rows with different
values remain incomparable; no unsupported winner is chosen. The existing ASCII
SQL comparison boundary remains. pi gets no extra membership validation; target
input uses int32 conversion and empty text becomes zero. Broader SQL literal/coercion
behaviour is not certified. Raw draft field names and native UI limitations remain.
Frontend UI/UX is untouched.

## Delivery qualification

Selected-source comparison and Git packaging only. No tests/test development,
Django checks, migrations, native/browser comparisons, preflights, business days,
fixtures, benchmarks or profiling were executed. No runtime parity, usability,
migration-success or production-ready claim. Prior receipts/failed attempts and
protected resources remain untouched. One cohesive commit/push, remote identity and
clean tree conclude scope; no deployment, mainline merge or next family follows.
