# Owned UptoBPR delivery evidence — 25 October 2026

This is an evidence appendix, not a status queue. The sole status and decision authority remains `F:/freshvcf/docs/handoff-3005/TRACKER.md`. This delivery concerns the retained owned TEST UptoBPR stop on localhost:8080. It does not qualify PostBPR, UptoDBM, PostDBM, general production configuration, or G3 continuous availability.

## Selected delivery and preserved owners

| Boundary | Exact identity |
|---|---|
| MTA source / image | `9bc51168d217983de4d88545a06ef4a30bf78f53` / `sha256:a43348f78c96124ef63a692b894694ae8e5250e83abe40db27913842ee2e7b48` |
| MTA container | `vectorflow-mta-uptobpr-9bc51168`, ID `91e38b4ceaa68477d632e735ecc4d7f9288e6a1f2b545c50c75f75a14b26f2b2` |
| Auth source / image | `ee0b5471c01aa2eeee8e43220c3e0b2c77746deb` / `sha256:f69f5b39fa76ed9d1c5e533bab83e5fbdef5a0fb3fca4841a8ae9609e1936059` |
| Auth container | `vectorflow-auth-uptobpr-ee0b5471`, ID `5fddae62c1bc1d7eb4c5b5e2a2ebd23b51784f3e8729be3188ae5d2224ebef02` |
| Frontend | Existing `vectorflow-frontend-ui-final-healthy-20261023`, image `11e5e56ce5602432344fa6f00fa4c95572583d46e35027b10714329a2da1adbd`; no frontend source/component/style change |
| Gateway config SHA256 | `7be3b790b6947be4b9321c6dcc93efcc40609b798194698bac19184ddb40ea28` |
| PostgreSQL | Same container `5476f2e5a1b89320924b6902a8729433cc882949cd7d5ee5718c75ee0f356c45`, database `vftest_fresh_lifecycleg2_uptobprui_20261025`, OID402363, schema222 |
| UptoBPR run / BPR phase | `e0735ad3-b98d-45c5-9bad-38bc5b0e5df8` / `486ffe8a-ae78-4de9-90e5-0f01eb6ede97` |
| Phase digest / snapshot | `863bcc7fd80bd4089bee87142afddc5fe1d8d1da840f099819e5efe9f486006d` / `2a06bf63b58ed68f1833f2e30ba18b471266b4c30051db3cfcb07b427fcea3ed` |
| Successful physical predecessor | `ee2c37c6-923f-47f8-adc2-992a65dbb8dd`, 23 October, no terminal commands |
| Selection file / SHA256 | `phase-selection-9cc45ab8.json` / `35e203a78557735638220b7c0e017bea8049ce9e19628ea7822db6a13c9eb5d8` |
| Latest reference after browser remark | `1b96f2a1-1357-4b7c-a98a-e9d38df53c78` / `7594aa8eee31ed1a3df2c5cc5c069a7ed48e3947ca19289deb8ff0344a1d4302`; action revision12, remark highwater2 |

The accepted PRE/BPR calculations, frozen capture, original failed Full, successful predecessor, four Pick owners, and original Full49 remain retained. The scoped run remains RUNNING at its accepted BPR stop with no terminal output; it was not relabelled as completed Full. The last browser operation added one ordinary BPR remark through the existing writer. All eight action commands remain, latest ID12. No engine replay, input recapture, allocation-history invention, or MTO API change occurred.

Evidence paths below are relative to `D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/`. Browser evidence is in `uptobpr-ui-evidence/browser-resumed-readproof.json` and the earlier `browser-progress.json`; API evidence does not substitute for browser evidence.

## Finite report and file dispositions

The canonical BAT/SQL trace and inherited-source distinctions are retained in the reviewer’s `legacy-scoped-reports-ui-and-snapshots-review.md` (25 October). Exact typed source locators, counts, fields and digests for new files are sealed in `uptobpr-ui-evidence/scoped-batch-files-9cc45ab8/scoped-batch-files.json`, SHA256 `ba6ab3d46f46962619090524afc345164cb8baa69d24dac41b6afd3ed8b6b5e1`. That manifest records the canonical producer script hashes; it is not a new calculation owner.

| Surface / output | Owner, enabling disposition and observed result | Consumer / action boundary |
|---|---|---|
| BPR | Current accepted BPR, 24-Oct marker,8 rows; empty SKU filter0 and clear restores8; export request200 | Existing grid/count/export, descriptions and remarks. Actual browser remark save and subsequent history display; typed journal/reference readback. |
| RRR | Current accepted BPR,4 rows, local empty filter and restoration; export request200 | Existing rationed grid/count/export. No new allocation-history owner. |
| BOR | Same accepted SupplierDispatchReq and DispatchColor plus pinned TEST projection;1 row, Z9/PARENT dispatch11; empty filter0/restore1; CSV success | Existing BORData/config/count/export contracts. BOR writes are not qualified. |
| BOR allocation | Same accepted BOROARequirement/BPRMaster/rationed rows; exact missing parent reconstruction with key/parent checks, no default;1 browser row | Existing GetBOROrderAllocationReportData/count/export; supplier/allocation writes and history continuation unsupported. |
| RRR allocation | Accepted production/RRR_OrderAllocation,5 rows, including separate WH8 order allocations and DIST/DMS/VENDOR norm rows | Existing GetRRROrderAllocationReportData/count/export. No fabricated history. |
| InTransit Whereabouts | Accepted current shipment O-1,23-Oct dispatch,qty4;1 row in browser; genuine captured contacts/history empty in packaged proof; final browser history modal says No data to show | Existing transit grid/count/contact/history reads. Logistics writes remain unavailable. |
| Open Expediting Requests | Genuinely captured empty population,0 rows, no loading indicator in browser | Existing GetOpenExpediteRequest/config; empty is not a failed query fallback. |
| Planning Fulfillment | Current phase,8 rows; chart and grid render | Read-only existing interactions. |
| Planning Excess | Current phase,0; chart No Data/grid0 settle | No fabricated positive rows. |
| Planning Expedite | Parent empty/grid0; child PRE/POST chart values render and its grid0 settles | Native chart/grid predicates differ; no invented count equivalence. |
| Planning GIT child | Existing explicit error for nonempty shipment case | Approved `LEG-GIT-CHILD-TRANSPORTER-INVALID-SQL207/8120`, direct approval `call_d2cf547683b94376b8cd74ea91487794`; not healthy grid acceptance or permission to repair legacy SQL. Parent graph remains explicitly unsupported. |
| BTR | Current24-Oct joins with physical predecessor trends dated23-Oct;8 rows, actual latest date, daily graph/descriptions,14→13→14 horizon, genuine empty norm history; actual CSV confirmed | No fallback to an earlier run to populate DBM. Initializer-owned BTR and terminal-command predecessors remain unsupported by approved boundary. |
| MDM | Same certified source;8 families,SKU4; Seasonality valid empty warning then0/no spinner. Pending-review says No data to approve; Task Status shows0 rows, both settled without mutation | Existing read/task contracts, not qualification of every MDM write family. |
| Four Pick CSVs | Original accepted Pick owner and original bytes preserved | All four actual Chrome downloads confirmed by human `call_5ac0dcb981744d3a90a34a11ce044f68`. |
| InputData.zip | Explicit enabled five-physical/four-processed-table archive contract;10 members,3466bytes,SHA256 `983c21ceda425ec4e536d7eb383f8d7d83c87acbb188545919561d791861787c` | Same human confirmed actual download. No regeneration for this reader update. |
| BOR_OrderAllocation.csv | Canonical GenerateBOR_OrderAllocation path,4 source rows;862bytes,SHA256 `c5faa9403560ab607d31ec4a7efd3145973feda8c981f754307bf30886191033` | Existing dynamic download menu plus fixed entitlement/scope-checked gateway path; actual Chrome download confirmed `call_1b8e9567c0e84778acdbd6fceeaa08de`. |
| Failed-force diagnostic | Canonical day-named `24-FailedForceNormChanges.csv`,zero cases,38bytes | Batch output; not claimed as a new UI menu download. |
| Parent-norm diagnostic | Canonical empty `NoNormParentReport.csv`,0bytes/no ZIP | Batch output, source-derived zero cases. |
| BPRExceptionReport | Canonical no-file branch because actual exception population is empty | No placeholder success file. |
| Optional outputs | Explicit test-only IsMTOEnvironment0; ModifiedRRR,DistSpecialOrder,DistTransaction/horizon excluded by `call_448be42a8362445786890445b9ade3fe` | Preserved capture unchanged; not production defaults. Empty RuntimeReports roster remains separately approved. |

BOR projections transfer only the two precisely approved amendments in `docs/LEGACY_EXCEPTIONS.md`: same-calculation DispatchColor Black/Red and15nullable supplier text attributes. Those amended fields are not claimed as canonical legacy parity. Allocation-history continuation is explicitly unsupported under `call_0078a68393104140849d8233bc72d745`.

## Action, failure and performance evidence

- Actual Chrome Apply12 records Z9/PARENT OldNorm36/NewNorm48; accepted phase Norm36/Suggestion48 remain, and the recommendation disappears canonically. `action12-typed-readback.json` proves the typed state. User `call_11b6e5b48d994c54ab5c0e6cdb45e2cd` accepts earlier positive runtime Sleep and final078 API no-op/rollback instead of fabricating final-browser targets. No positive final-browser Sleep/no-op or exact Apply-to-usable timing is claimed.
- Final MTA restart preserves run/phase/action/reference identities (`report-files-8080-activation-proof.json`); retained078 late-final-reference refusal rolls back atomically. The auth-only empty-assignee fix passes20focused tests and an actual existing-identity read; `empty-assignees-8080-activation-proof.json` records activation. The observed BPR history500 is resolved: actual Chrome displays empty history, then saves and reads the exact test remark. `final-browser-remark-readback.txt` records its new immutable reference and unchanged command count.
- Single-browser-call Planning timings:2809ms after BPR export,3355ms after an unavailable report returned403,3421ms after the final BOR download and remark. Workload:8 BPR rows,1 BOR row,5 allocation rows,one test tab active,other tab idle. MTA/auth host-capacity quotas and existing PostgreSQL16CPU/16594960384bytes. These are small-case usable-screen observations, not large-data performance acceptance or a measured login transition.
- BOR download packaged proof improved10.333→3.721seconds with the same862bytes in the512MiB/1CPU proof worker after one omitted request-reuse route was added. Scope/entitlement denial remained403. No cross-request cache or write reuse was introduced.
- A pre-replacement session subsequently failed refresh with `Invalid site token`; fresh manual login restored reads. Existing auth uses a cached random daily site key. Cross-replacement session continuity is unproved; no G3 fix or continuous-availability claim is made.
- Successful and denied downloads settle; a browser-cancelled download and matched large-data concurrency trial were not repeated in this finite delivery. Original G1/Full49 evidence remains preserved at its original boundary.

## Verification and rollback limits

79focused report/file tests (one Windows safe-open skip subsequently exercised onLinux),27packaged report/file requests,13request-scope freshness tests,7initial gateway tests and20final gateway tests passed. Three final affected Full-default tests preserve default BOR/BOROA,RRR allocation and logistics admission paths (`final-affected-full-read-defaults.log`). These are affected-regression proofs, not a new Full end-to-end acceptance.

The previous gateway configs and exact old containers/images are retained for rollback. Superseded owned MTA078/auth87/auth9bc were stopped by exact ID after final gateway validation; see `final-owned-pair-retention.json`. Only the owned8080 upstream changed; original Full/MTO and protected services remain untouched. No Docker prune, reset or volume deletion occurred. Rollback must use an identified retained config/pair; do not guess among Docker images. Business scope acceptance remains a human decision recorded only in TRACKER; this appendix does not release the next scope.

For ordinary UI review, open `http://localhost:8080`, use the existing fixture login, and select Planning or MDM. No Docker/image selection, initialization, input import, execution command or run replay is required. A session created before the last auth replacement may need a fresh sign-in when its access token expires; session-preserving service replacement remains outside this qualification.
