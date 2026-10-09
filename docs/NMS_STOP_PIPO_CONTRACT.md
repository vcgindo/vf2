# StopPIPO master6 source port

> Retained family-source contract from25b4fad. Historical proof and approval statements below apply to that original delivery. Current3005 integration proof and limits are in [MDM_3005_CODE_DELIVERY.md](MDM_3005_CODE_DELIVERY.md); no fixture approval or runtime acceptance transfers implicitly.

9 October 2026. **Ported, unverified.** This is the bounded MODIFY-only port
approved in controller turn01a11d76-5270-7b12-99b5-9565f779d6cf, from64b9be1 on
codex/nms-sob-moq. MIGRATION.md is the sole status tracker. The retained proposal
records scope; its approval-pending text was superseded by that human decision.

## Authority and operation map

Canonical root: F:/VFlow_Local/local-runtime/mta-engine. Deployed API:
F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll, SHA256
0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346.
MDMProcessor.deployed.cs and TaskStatusProcessor.deployed.cs refer to the retained
matched extraction in D:/freshvcf-build/evidence/nms-sob-moq-20261008-001.
MDMProcessor extraction SHA256:
f46e2fc1db36007ee29ea2de4574eca2017ceea268db55eea6b62fa9b16779c8.

| Contract | Canonical source | Modern implementation |
| --- | --- | --- |
| Master6 MODIFY only; twelve fields | MasterMapper_2.0.sql master6; UI_MDMConfig_2.0.sql master6 | mta/config/mdm_stop_pipo.json; mdm/stop_pipo.py; families.py |
| Current, count, filters, requested download fields | MDMProcessor GetData case6 (706), GetDataCount case6 (7271), GetSubQuerySql | stop_pipo.py reads actual closing PhaseOutTbl, PhaseInTbl, descriptions, phase_map and reason102 history, plus owned live stop queue |
| Draft save/read/delete | DraftPIPOMaster schema; shared deployed draft methods | mdm/drafts.py and MdmDraftStopPipo; native aliases, nullable typed int/date columns and IsSelected |
| Submission and assignment | MDMProcessor StopPhaseOut (1291), DataValidation (1037) | stop_pipo_tasks.py; exact sc/wc projection, Importer pair/scope validation, batches, approvers and shared task/subtask owners |
| Review, count, download, history | TaskStatusProcessor master6 review (753), download (2217), shared history methods | stop_pipo_reads.py through existing authenticated mdm_views dispatch |
| Approve/reject/revert, comments and status | TaskStatusProcessor UpdateApprovedData master6 (2605), shared task-status methods | stop_pipo_tasks.py; requested flags, history, approved missing-pair insert and subtask transitions |
| Approved stop input and clearing | Importer PhaseOutStop; existing phase collector; ClearPhaseInPhaseOutData.sql | stop_pipo_capture.py, daily_input.py and execute_day hook in temporal.py; unchanged application/r1_phase_out.py and r1_phase_entry.py |

Current reads preserve join multiplicity and NULLs. Native ordering is only
isPOActive, sc; no extra tie-break is added. Reason102 RN=1 exposes only the latest
date, so ties project the same value. Native current pagination is ignored;
review/download pagination follows the joined row numbers. Reject/revert changes
request/history flags but does not remove an already queued stop. The insert
anti-joins the old target, preserving incoming duplicates and SQL NULL nonmatches.
There is no resume operation or phase-creation path. StopPhaseOut.sql is a report
writer, not the stop calculator.

## Ownership and integration limits

stop_pipo_source.bind is explicit onboarding only: existing root source receipt,
accepted selected publication, same-source consumed capture, no accepted direct
successor and no pending capture. It copies only that source's remaining closing
phase_stops into its new owner. No binding was executed and no fixture installer
or production source was created. Existing source onboarding remains restricted
to registered fixture inputs; a general production onboarding path is still absent.
The current reader requires strict selected_run admission and the owner's latest
publication. An unaccepted calculation cannot populate it.

Capture freezes typed queue occurrences and task revisions against the own
predecessor run/output/closing digest. execute_day substitutes that frozen feed;
the existing collector calculates and clears it. Finalization records each owned
occurrence, clears only consumed captured rows and leaves later approvals pending.
Late decision revisions defer task completion. Existing daily task completion and
pruning apply to master6. No canonical algorithm or SQL was edited.

Migration0099 follows0098 and adds seven Django owners plus two typed input-image
tables. It reuses existing source decision locks, immutable input guards and
owned consumption guards. Row payloads remain relational; JSON holds bounded
binding metadata. Shared changes are confined to family/draft dispatch, model
registration, daily capture/finalization, typed input mapping and temporal input
handoff. The exact prior Seasonality adapter hash remains readable for its original
base family roster; master6 requires its own additional immutable binding. This
does not transfer any earlier fixture exception or publication approval.

The authenticated modern wrapper retains requester/reviewer checks and rejects
conflicting duplicate decisions rather than inventing a native UPDATE winner.
Draft date conversion covers ISO input and the native empty-string date; broader
SQL Server locale-dependent coercions are not reproduced or certified. Existing
history-role and UI limitations remain. Frontend UI/UX is untouched.

## Delivery qualification

Source comparison and Git packaging review only. Migration0099 is hand-authored
and unapplied; Django checks, migration checks, tests, native/browser comparisons,
preflights and business-day execution were not run under the approved scope.
No runtime parity, usable-screen acceptance, production readiness or activation
is claimed. Protected services, selections, prior evidence and failed attempts
were not changed. No deployment, mainline merge or next-family work is included.
