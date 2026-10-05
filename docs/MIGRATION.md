# Fresh VectorFLOW migration — current baseline

Baseline date: 3 October 2026. Implementation checkpoint: `2d0cfde95606aef58a486e186bde1558802ef542` (pushed).

## Authority and current instruction

This is the **only migration status tracker**. Whole-page implementation remains
**PAUSED**, not complete, except the bounded holistic presentation batch below.
The separately authorized Stage2 dataset preparation
and bounded four-page availability correction are complete for the scope below:
RRR/BPR/BTR/DBM populated browser grids, counts, local filters and restricted reads
on3005. Engines, accepted F1/F2 state, replay, authentication permissions, other
pages and Stages3–5 were not changed. The isolated fixture remains serving after
window010's successful admission, security and protected-resource checks.

The previous 4,286-line tracker is preserved byte-for-byte in [the historical snapshot](archive/MIGRATION_2026-10-03_2d0cfde.md), SHA256 `a913419e34a3318d7ca09f11b163295c9d695b55d99e3060e87c23fadc84242b`. It contains provenance and exact earlier approvals, **not active instructions or a second queue**. Do not load the whole archive routinely; consult the relevant passage only when an unresolved contract requires it.

Current human instructions and applicable repository constraints govern execution. This baseline records their current status; it does not broaden an approval or waive a source contract. Historical “active”, “pending”, “unpublished”, “continue” and old outage statements do not override this baseline. Supporting plans describe contracts, not current authorization.

## Objective and architecture

Port the canonical deployed MTA behavior into Django/Python and PostgreSQL, connecting the retained frontend, authentication and direct-port MTO. Deliver a runnable application with calculation/state parity, correct presentation and complete application acceptance. SQL Server/.NET remains the independent validation oracle, not a modern production calculation dependency.

Canonical authority: deployed DLL/BAT/SQL/config at `F:/VFlow_Local/local-runtime/mta-engine` and `mta-latest`, preserved at `F:/VFlow_Source_Backup/deployed-demo/MTA`. API DLL SHA256: `0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346`. Pins are in `baseline/manifest.json`. Recovered source is authoritative only where matched to that deployment.

`execute_day` remains the production day boundary. Operational state, histories, actions and consumer projections are typed PostgreSQL rows linked to run identity, preserving duplicates and source order. JSON metadata or trace blobs do not replace operational state. MSSQL and PostgreSQL physical schemas must not be assumed identical.

## Programme status

### Buffer indexed-filter correction deployed; performance acceptance remains open

The human now instructs: “begin with the Buffer, we keep this version of RRR.”
Resume only Buffer Trends (Tech/Eco chart page). Retain RRR's restored08f58e4
reader, delivered in203bc68, and Research's accepted behavior. No renewed RRR
optimization, sampling or audit. The retained April7 fixture and normal resources
remain the boundary under RESEARCH_RRR_BUFFER_TRENDS_PLAN.md.

Buffer active exit: reuse sealed graph memberships and23-case history-family
proof, retained Tech/Eco observations and request/response contracts. Finish the
remaining supported populated filter, absolute/percentage switching, expanded
view, summary/availability and existing horizon semantics. Confirm the deployed
path once and correct only a measured missing defect. Preserve colour/NULL/bag
semantics, optional parent multiplicity and inherited invalid filter failures;
no new matrix, baseline, legacy/resource/modal campaign, engines, auth or RRR
changes. Complete required affected verification/deployment, restore temporary
instrumentation, consolidate the three-report handoff and commit/push.

The subsequently authorized focused investigation/correction/final check is
finished (6 October2026 local time). A measured filtered aggregate cost1.034s in
the diagnostic; EXPLAIN showed a parallel scan of the dispatch membership despite
the SKU predicate. The reader now qualifies stored normalized membership keys
through the existing buffer_graph_member_keys index before ordinal history
fetches. Only requests with an existing SKU/location key predicate use this path.
Unfiltered SQL is byte-identical to08f58e4; the bare OR predicate/parameter order
is unchanged. No schema, preparation, frontend or permission mutation occurred.
Deployed reader SHA25698af535b…1b7a; RRR remains exactly08f58e4 and Research unchanged.

| Buffer requirement | Final bounded result |
|---|---|
| Complete graph data | All nine complete frozen Buffer broad/restricted/filter/empty responses revalidated exactly on the final candidate. Both empty-scope HTTP403 denials remain separate from the frozen empty reader results. Reuse unchanged Research cases from the23-case family proof. No values, types, NULLs, duplicates, source or membership changed. |
| Tech/Eco usable screen | Retained30-day observations: Tech20.689→9.546s; Eco17.644→12.797s. Reuse these passing observations; no fresh timing campaign. |
| Supported populated filter | Eco/SKU21101151051000/30days/Absolute: retained before1.091s; earlier failed1.326/1.314s retained; one final indexed-candidate trial1.853s. Correct seven-series chart,353 Black summary,100% Black and0% availability. **Improvement criterion is unmet.** |
| Controls/summary/horizon | Both broad Tech/Eco modes toggle Absolute/Percentage using loaded data. Summaries and91.78/94.74% availability match retained responses. Submitting1day while in Percentage refreshes the chart to07-Apr-2026,100 Total,12 Black summary and0% availability; Absolute then shows12 Total. No stale30-day plot or doubled Total. This is a functional check, not another horizon benchmark. |
| Expanded view | No existing expansion control exists in either retained chart component or visible page. The unlabeled floating-tab button is its indicator, not an expansion action. Coverage is unavailable; no new UI feature was invented. |
| Operation | Backend build/startup admission,15 focused tests, query-boundary proof and nine-response PostgreSQL proof pass. Current admission5c90ae58…3e7 and readyz pass;48 protected containers unchanged. Nginx restored exactly to SHA256d1a70598…dc2a. Reuse unchanged11-test integrated frontend proof; no frontend build or migration needed. |

**Consolidated Buffer blocker:** the strict requirement that every changed
latency journey improve over its own before is not satisfied for
`GetBufferTrendGraphData`, Eco/30days/SKU21101151051000. Final screen readiness
is1.853s versus1.091s before (+762ms); the one final traced API request returns200,
4605 transferred bytes and costs1.467s (1.466s upstream). The remaining386ms
includes browser/control/observation overhead, not a measured render-only duration.
The index access path is proved, but its complete deployed latency improvement
is not. Further correction needs attributable gateway/admission/assembly/SQL
timing for this same path; cause of the residual cost/variation is not established.
Complete output correctness remains proved. No favourable resampling, weakened
acceptance or resource increase follows. The explicit focused allowance is
consumed; stop at this consolidated blocker. Expanded-view coverage remains
unavailable because the retained page has no such control; no feature was added.
No adjacent page opens and the goal is not claimed complete.

Goal disposition (6 October2026): **BLOCKED**, pending a direct human decision
on the already-requested bounded layered profile/correction/final-screen extension.
The same missing authorization has persisted for three consecutive goal turns;
the approved final trial is terminal and its allowance consumed. The latest
CAPTCHA approval permits that login challenge, not an additional performance
trial. No runtime request, serving mutation or adjacent report work follows this
status update. Preserve the deployed correction and all retained failed timings;
this is a consolidated blocker, not completed performance acceptance.

Read-only follow-up afterf6ecf34: the gateway's MTA interceptor performs two
authenticated permission-ID lookups, then forwards the request and decodes the
response. The retained pre-correction profile contains seven image-metadata
lookups and nine selected-run checks; fixture.image_metadata_batch already
provides a validated named-receipt batch primitive. These are possible next
measurement boundaries, not demonstrated causes of the final1.467s request.
No timings from separate requests are subtracted to infer gateway cost. A bounded
layered profile/correction/final-screen extension is now requested and pending;
no further runtime request or serving mutation is authorized by this follow-up.

Retained-trace follow-up (no new requests): before-request-timing.jsonl records
the filtered API at0.865s; buffer-final-request-timing.jsonl records1.092s, both
200/4605 transferred bytes. The227ms API increase accounts for the223ms observed
screen increase; the residual screen/observation interval is226ms before versus
222ms final. This attributes the remaining gap to the request path, not a
demonstrated chart-render regression. These pre-correction traces did not separate
admission/dimension setup and SQL execution. The focused profile subsequently
identified the membership scan above; it is a diagnostic, not another browser
baseline or percentile claim. The first proof harness incorrectly compared
authenticated empty-scope denial against unwrapped frozen reader responses;
that failure and original harness are retained. Its correction asserts the403
boundary separately and preserves exact reader comparison. The first unrestricted
key-join candidate is also retained; the final build confines the new path to
existing key predicates to preserve already measured unfiltered Tech/Eco SQL.

`buffer-delivery.json` consolidates the latest three-report handoff, with the
initial pass preserved in buffer-delivery-initial-pass.json. Focused profile,
before/indexed SQL plans, query-boundary proof,15-test log, nine-response proof,
final browser JSON/screenshot and buffer-indexed-final-request-timing.jsonl are
under the same evidence root. A subsequent /api/user/logout/ request occurs after
the measurement; no403 occurred in the matched graph request and no attribution
to this reader is inferred. RRR203bc68's implementation is kept exactly; the
current backend image contains only the additional bounded Buffer correction.

| Research requirement | Verified result |
|---|---|
| Complete initial page | 5000 configured rows,97097 count, headings/configuration and93.53/93.96/91.78 availability bands visible. Usable screen13.481→5.867s. |
| Current daily modal | Full eight-series chart,14-day horizon and selected SKU/location/Norm details populated;5.136→4.156s. Shared request identity/status/response RunDate are wired. No early loading strip. |
| Selected self/child/parent Tech/Eco history | Reuse unchanged exact source/reference proof and deployed Update2.655s observation. The earlier2.418s observation still included loading and does not prove complete readiness. |
| Values/scopes/filter/empty output | All14 full frozen Research responses and six shared BPR grid/count/analytics responses match exactly. Preserve every field,type,NULL,duplicate and order. |
| PostgreSQL preparation |97,299 exact per-occurrence availability rows pass full streaming source/readback and repeat verify(created=false). No existing history receipt or source fact replaced. |
| Schema/guards/operation | Django check, migration drift/plan, migrations0037–0042 and PostgreSQL proof pass. Sealed writes and disabled-guard admission are denied. Source/admission unchanged;48 protected containers unchanged. |
| Affected verification |11 PostgreSQL tests,17 preparation tests and seven modal frontend tests pass. Retained integrated frontend11-test proof is reused.376 pinned baseline resources unchanged. |
| Builds/deployment | Backend/frontend builds and startup admission pass; readyz retains admission5c90ae58…3e7. Temporary nginx instrumentation restored byte-exact to SHA256d1a70598…dc2a. |
| Downloads | Reuse the user's existing confirmations; no export exploration. |

Research corrections use the existing normalized BPR keys for bounded selected
page reconstruction;0039 covers physical-history availability without wide heap
lookups.0040 prepares six integer band counts per existing availability membership
with original case-sensitive SKU/location codes and exact occurrence grain;
live permission weights remain request-owned.0041 covers the existing count
predicate (239ms diagnostic SQL,index-only,zero heap fetches).0042 indexes the
modal's measured native pair/source-order Norm Change history scan. The Research
caller uses the existing ready-only loader and supplies its three shared props.
No calculation engine,input fact,accepted F1/F2 state,auth permission,resource cap,
legacy benchmark or other serving service changed.

Timings are single bounded current-modern browser observations, not percentile,
minimum-latency or historical synthetic/legacy claims. The rejected12.273s,
15.505s and10.070s closures remain retained. Final observer failures also remain:
an exact-text selector expired; a fixed-count loop ended before readiness and its
timing assignment failed; the first modal observer wrongly required an untruncated
location label. The successful full-state observations above follow those specific
observer corrections. Do not count failed observers as usable-screen measurements.

Evidence root: D:/freshvcf-build/evidence/research-rrr-buffer-trends-20261005-001.
`research-delivery.json` consolidates results and image identities;
`research-final-reader-proof.json`, `research-critical-proof.log` and
`research-modal-index-proof.log` retain complete response/source/guard proof;
`research-final-browser.json`, final grid/modal screenshots and body-free request
timing retain current UI evidence. The operational commands and serving flags are
in [the presentation handoff](PREPARED_PRESENTATION_HANDOFF.md).

RRR's existing prepared activation(VF_RRR_PREPARED=1) remains serving. Its retained
14-case/full8063-row ordering/page/CSV proof and observations are preserved;
the automated page2 speedup remains unproved, separate from human usability acceptance. The explicit human
“choose cardinal” amendment(controller turn01a10c8d-427f-7e11-9bdb-99e14705ada5)
approves only the retained occurrence ordinal after four canonical sort keys.
Full typed bags,counts,NULLs,scopes and first-four-key order remain strict; no
physical/virtual priority is invented. Original314/132 tied positions remain
retained. Earlier preparation failures rolled back and are preserved.
Buffer's implementation,23-case history-family proofs and observations remain
preserved; the current bounded controls and filtered result are recorded above.
These retained changes are not whole-page acceptance. No adjacent work is active.

Historical candidate2e74a36 was deployed and correctness-verified. The human
accepted its usability and authorized Buffer, then subsequently requested this
rollback to the prior version. Its automated page-transition benchmark discrepancy
remains retained and unaccepted as a speedup proof; the table below describes
the reverted candidate, not the current serving rollback. The human's current approximately2-second RRR
observation is retained as runtime evidence; it does not silently waive the
bounded page-transition criterion or imply a different dataset/scope/page size.

| RRR requirement | Bounded result |
|---|---|
| Exact data/count/filter/export |14 retained cases pass. Complete approved ordinal responses and CSV bytes are exact; full8063 occurrences partition into5000 plus3063 without loss/repetition. Broad/restricted/filter/empty cases retained. |
| Reader correction | Qualify narrow occurrence keys through live filters and permission/parent multiplicity before paging, then reconstruct only selected wide rows by source ordinal. Reader page2 diagnostic5.311→2.497s; SQL plan avoids whole rationed-source scan and wide pre-page spill. No source/recipe/receipt/schema/auth change. |
| Initial full usable grid/count | Corrected matched readiness9.367→3.733s,5000 of8063. First-after-deploy stricter12.033s observation remains retained and is not a pass; the normal serving correction is not a cold-start guarantee. |
| Supported SKU filter |21101151051000,11 rows/count,4.170s. Retained before22.581s is an upper bound from a failed one-row expectation, not an exact completion. |
| Page transition | **Unresolved**: retained before3.744s(API3.388s), corrected after6.204s(API4.355s). Earlier stricter after4.529s had API2.593s. No passing transition speedup is claimed. |
| Operation/proof |31 focused tests, backend build/startup admission and deployed candidate hash pass. Same source/admission;48 protected containers and all resource limits unchanged. Frontend unchanged. No schema checks needed for this read-only SQL change. Nginx restored byte-exact. |

The first continuation observer incorrectly required the dismissing “Loading Grid
Data” toast to disappear, whereas the retained before included that nonblocking
toast after grid/count readiness. One explicit observer correction used matching
populated grid, headings and page/count conditions; screenshots show no blocking
modal. Both original observations and corrected results are preserved. The
corrected initial grid improved, but the corrected transition still failed.

**Consolidated remaining blocker:** broad `RRRData`, page2/5000/filter{}, returns
3063 rows with an approximately7.2MB JSON response. The latest captured request
cost4.355s and screen was observed usable6.204s after click. Earlier identical
serving request cost2.593s; a focused two-request deployed diagnostic returned
exact broad grid/count in3.429/1.521s, with body transfer only0.009s. These traces
and the human's2-second observation show variability, but do not establish its
cause or prove a persistent intrinsic regression. No unmeasured index, resource,
gateway or grid redesign was introduced. The human has explicitly accepted current RRR usability and directed moving on;
this closes its delivery exit without relabeling the failed automated observation.
No further RRR optimization or sampling is authorized. The controller’s later
page2 observer failed on accessibility diff/footer formatting; it is not a
slow-page measurement. Data and ordering need no correction.

Evidence: `rrr-continuation-delivery.json`, full `rrr-continuation-proof.log`,
`rrr-continuation-tests.log`, browser JSON/grid/page2/filter screenshots, deployed
phase diagnostic and body-free request trace under the existing evidence root.
The candidate/deployed reader SHA256 is
`76776daeeb97324e45af8c7087e637c443c471548652a731af29453ce1b8e09b`.
Earlier ordering, receipt and failed performance proofs remain unchanged.

**Completed rollback retained:** RRR reader/test are restored exactly to08f58e4
(Git reader blobc237a1f9ce745b0acb340c825a456a18ea0cc845). Backend
`freshvcf-preview-mta:rrr-rollback-08f58e4-20261005-001` is serving on3005;
configuration identity`sha256:abe3866ebbf9e0c59bb40f7a438e04c83502f0693e0270387fc897df2e0cbe70`.
All31 focused tests, build/startup admission and runtime readyz pass with the
unchanged admission5c90ae58…3e7.48 protected containers, frontend identity,
ports/restart/resource caps are unchanged. Source facts, schema, memberships,
flags, permissions and calculations are unchanged; no new report benchmark or
reload ran. `rrr-rollback-receipt.json` and its logs consolidate the rollback.
Research remains accepted. The new human instruction resumes Buffer only.
Its retained work and the reverted2e74a36 evidence are preserved; this rollback
remains the fixed RRR serving version throughout Buffer delivery.

**Current Planning result:** the bounded April7 prepared-presentation delivery is
closed by the final six-destination matrix below, including the user's current
confirmation of all Excel downloads. Earlier partial/unproved/active statements
in the checkpoint history describe evidence at that time; they do not reopen
completed ordering/performance/export checks. Broader migration acceptance and
the explicitly deferred historical modal baseline are not claimed complete.

### Completed bounded acceptance continuation — 5 October 2026

Direct user reply `call_3680e1b171264b7490c914d82254602f` authorizes one bounded
continuation for the six remaining broad Expedite ordering differences and only
missing matched legacy/3005 usable-screen comparisons. This supersedes the prior
stop/no-new-benchmark boundary for those checks. Preserve strict comparisons,
all data, source SQL, engine/state/auth boundaries and existing resource limits.
First establish whether differing order violates explicit canonical ORDER BY or
is an unresolved tie/unspecified sequence; never invent a tie-break to fit a capture.
Then run only missing matched journeys with restoration, reuse passing surfaces,
and record precise evidence or the semantic decision needed. The historical modal
baseline gate stays deferred/unaccepted. MIGRATION.md remains the sole tracker.

Ordering disposition approved by direct reply
`call_038051c3721a4d7f8a5a28f8ddf66e93`: the six exact April7 query families may
compare full typed duplicate-preserving bags only inside equal explicit ORDER BY
keys, or across the complete result for the two critical queries without ORDER BY.
No serving response/query changes. Evidence-only `planning_order_contract.py`
binds run/source/date/family; three tests reject value/type/NULL/multiplicity,
explicit-order and boundary changes. `acceptance-continuation/order-acceptance.json`
passes all six broad cases under that exception and all six leaf cases strictly.
This resolves the six named sequence blockers, not every other report's order.

The continuation's first Windows launch lacked SeDebugPrivilege and changed no
limits. The authorized elevated launch succeeded; its heartbeat expiry restored
SQL/API/PostgreSQL budgets with zero errors. Browser runtime was reset during the
continuation; prior files are retained, not rerun. Temporary nginx request logging
was restored byte-exact (`acceptance-continuation/restoration.json`). A separately
identified resumed resource window continues only the missing observations.

The resumed window is now RESTORED with zero errors. The bounded continuation
records these single click-to-usable observations (seconds, automation overhead
included), reusing named retained matching journeys rather than resampling them:

| Journey | Legacy | Modern3005 | Qualification |
| --- | ---: | ---: | --- |
| GIT parent entry/grid | 6.799 | 6.048 | 1627 rows, configured5000 page |
| GIT child chart | 4.362 | 2.873 | Genuine empty shipment charts |
| Expedite parent chart | 13.064 | 3.629 | Approved own-label correction |
| Expedite child chart | 4.265 | 2.984 | Approved own-label correction |
| Excess grid | 26.242 | 3.058 | 5000 of9871; corrected legacy observer |
| Fulfillment grid | >55.100, observed ready by89.611 | 5.058 | 5000 of12720; legacy exact completion time unknown |
| Parent dispatch grid | 31.328 | 14.122 | 1030 rows; full nested response retained |
| Parent availability grid | 21.476 | 9.264 | 1443 rows; modern still materially slow |

GIT child's corrected1627-row grid takes2.796s; invalid legacy combined SQL means
there is no valid equivalent legacy populated-grid timing. The first legacy
Excess observer failed only its comma-formatted total check; retain it separately,
not as first-usable timing. Legacy Fulfillment stayed loading at55.1s and the same
request later populated; no retry or falsely precise time. Evidence and source
pointers: `acceptance-continuation/consolidated.json`, raw browser snapshots,
screenshots and both restored resource receipts. Existing passing charts/exports
remain reused. No performance code change was made in this continuation.

This closes the six named chart-order discrepancies under the explicit exception
and supplies the missing bounded observations above. It does not confer general
independent ordered-wire acceptance on other consumers (notably Parent's97097
nested transit rows, whose retained proof is a bag comparison), positive shipment
support, or the deferred historical modal baseline. Full goal remains unproved;
next audit must reconcile those exact remaining consumer contracts without
repeating this completed measurement pass.

Independent Parent SQL audit (same retained owned READ_ONLY databases, no engine
or persistent write): `parent-independent-sql/broad.sql` is the pinned deployed
query with only database/table and already-resolved scope bindings. Source owner
files and sealed manifest are verified. The complete1030 dispatch and1443
availability grid rows match ordered modern values after preserving JSON decimal
scale in the canonical string conversion. Both branches' row bags are exact.
The97097 dispatch nested rows match every field/value/duplicate, but their sequence
differs; availability nested rows are identically empty. This replaces the earlier
Python-only evidence gap for the broad case, not restricted/filtered SQL coverage.
Evidence: `parent-independent-sql/{raw-sql.json.gz,comparison.json,main-grid-comparison.json}`.
Canonical nested SQL has no ORDER BY; chart exception does not transfer. A separate
narrow nested-array order decision is pending direct human reply. No application
code, data or resource limits were changed for this read-only proof.

That decision is now approved by direct reply
`call_rXDWYB4DZf82Ch7YyyoH5EEa`. The separate evidence-only
`compare_parent_transit` comparator binds exact run/source/date/route/direction and
array name. All97097 broad nested rows pass with zero missing/extra occurrences;
original sequences and capture hashes are retained in
`parent-independent-sql/approved-transit-comparison.json`. Four focused comparator
tests pass, including rejection of numeric/string changes, NULL versus omitted
fields, whitespace changes, duplicate loss and transfer to any other boundary.
This closes the named broad Parent nested-order gate with an explicit exception.
The populated restricted case is now independently captured against the same
canonical SQL and owned READ_ONLY sources. Its resolved permissions `[4]`/`[25]`
match the serving fixture actor policy and retained modern capture. All78 dispatch
and161 availability rows match strictly in order, including decimal string scale;
availability transit remains identically empty. All97097 nested dispatch rows
pass the separately approved exception with zero missing/extra occurrences.
Both original sequences and hashes remain in
`parent-independent-sql-restricted/{raw-sql.json.gz,approved-transit-comparison.json,main-grid-comparison.json}`.
This proves these broad and populated restricted cases, not untested filtered SQL
variants or other consumers. The overall goal remains unproved.
No serving code, query, UI order, dataset or authentication changed.

### Delivered report-defect correction amendment — 5 October 2026

Direct human instruction verified in controller thread
01a1037c-5d96-7700-87a8-89a575f6c9f8,turn01a10b0a-e95f-7981-a326-8a42eb9c1c3b,
authorizes only: GIT child combined SQL207/8120 field/grain correction; Expedite
parent unpaged SQL156 separator correction (same-branch proven Norm owner only if
SQL209 encountered); and child receiving-chart own joined-location labels.
This supersedes the prior repair prohibition for those exact report contracts.
Active exit: establish retained combined-grid ownership/grains once, implement
all unblocked corrections using prepared ingredients, prove complete affected
values/NULLs/duplicates/order and scoped/empty cases, deploy3005 and verify actual
affected UI/full-data consumers, then commit/push coherent delivery. Label these
intentional corrected contracts separately from legacy parity. Any unresolved
cross-grain or order choice must be stated, not invented. No new benchmark,
unrelated retest, engine/state/auth change, source reload or resource increase.
The existing six-destination objective remains; this is not a replacement goal.

Delivered backend: `freshvcf-preview-mta:planning-report-corrections-20261005-001`.
Frontend remains `planning-grid-latency-20261005-003`. Startup admission and readyz
pass with the same run/date/admission digest; all22 other containers are unchanged.
Backend ports, restart policy and4GiB/2CPU limits are unchanged. No schema change.

GIT child now returns separate location/transporter objects: all1627 aggregate
location occurrences survive the genuinely empty shipment source. A populated
parent-location leaf returns67 exact rows; paging, duplicates, values and empty
scopes pass. Nonempty shipment sources remain rejected. Shipment quantity/order/
transporter fields belong to GoodsInTransitTransporterMaster, not the aggregate
GoodsInTransitMaster. No aggregate SKU supplies grouped shipment details. This
closes the retained empty-shipment fixture, not general positive-shipment support.

Parent unpaged reads preserve the valid paged selection and explicit branch/RN
order without a page predicate. Complete reference proof: broad1030 dispatch/
1443 availability, leaf78/161, empty0/0; the independent97097 dispatch transit
rows and zero availability transit rows are retained. The original reference's
SQL156 behavior remains default; correction is explicit opt-in. SQL209 was not
encountered or repaired. Browser and export use paged requests; the unpaged
consumer is proved through actual authenticated HTTP with pagination omitted.

Child receiving labels use their own verified joined row. Pinned DLL-input
comparison changes only102 broad/6 leaf labels and preserves every other field.
Critical-row reversal cannot change receiving labels; each retained receiving
code has one own label. Canonical receiving order is retained. Frontend stable
total-count sorting has a19/19 tie at the broad tenth-row cutoff; the retained
modern/reference top10 match exactly, without a general ordering waiver.
Pre/Post transformation indexes by state and emits fixed colour bands, so UNION
position cannot swap the values. Independent full SQL sequence acceptance remains.

Validation:34 focused tests pass, database checks show no migration drift/plan.
Eight authenticated broad/restricted3005 API responses match complete direct-reader
expected responses, including order. Independent source proofs above establish
changed semantics; gateway/direct-reader equality alone is not legacy parity.
Browser verifies1627 GIT rows, zero transporter rows,103 Child receiving table
rows and1030 Parent dispatch rows. Existing performance/export proofs are reused;
no new benchmark. Evidence: `planning-prepared-20261005-001/report-corrections/`
contains full responses, source/read proofs, ordering inspection, build/admission/
deployment receipts and screenshots. Historical legacy failures remain retained.
Whole-goal delivery remains partial: independent ordered-wire disposition and
matched usable-screen performance gaps below remain; positive shipments are
outside this fixture's proof. No engine/state/auth change or replay occurred.

Retained-evidence completion audit after deployment (no runtime queries or new
benchmark): `report-corrections/formatted-order-audit.json` applies the approved
own-label correction to both retained source datasets, then compares complete
formatted arrays without sorting. All8 restricted arrays and all4 Pre/Post
arrays match in order. Thus SQL Pre/Post UNION position is not a remaining
formatted-wire blocker. Six broad arrays still fail ordered equality: Parent
critical first differs at index0, receiving20, nil-stock15 and chronic12; Child
critical0 and receiving20 (zero-based). Existing exact bag proofs remain distinct
from ordered acceptance. No new tie-break or order waiver was introduced.
The retained prepared capture SHA256 is
`ab2ed01fadbcd0201e1d56f4eeb8fa5cca9c5cc82811850cff1e2fba194c54fe`.
These six arrays and the matrix's matched-performance gaps are the consolidated
remaining acceptance dependencies; not a reason to repeat passing exports or
change source calculations. The bounded plan requires stopping after this pass;
an exact ordering disposition and authority for any further matched measurements
are needed before those remaining acceptance claims can be made.

### Completed focused performance investigation — 5 October 2026

Direct human authorization in this thread extends the exhausted measurement
allowance for one focused investigation and final measurement of Planning Excess,
Fulfillment and the selected-row Daily Data Graph modal. Reuse the deployed
prepared data, accepted chart/export proofs and retained reference evidence.
Trace request/query/serialization/transfer/frontend rendering before changing a
measured bottleneck; preserve full5000-row pages, values, nested rows, scopes,
ordering, engines and permissions. The exit is a corrected observable final
usable-screen measurement with request attribution and restored resource limits,
or a precise evidenced blocker. This amendment supersedes only the prior repeat
measurement restriction for these three paths. SQL defects, ambiguous labels and
independent ordered-wire parity remain unaccepted and outside this amendment.

The authorized pass is complete. Retained backend profiles measure count readers
at0.934s Excess/0.664s Fulfillment and selected modal read at0.215s; no new SQL
or index bottleneck justifies a speculative change. Final authenticated3005
observations at1280x720 under the existing matched-resource caps:

| Path | Click to usable screen, automation upper bound | Correlated request times |
| --- | --- | --- |
| Excess normal grid |3.058s;5000 rows,total9871 |count1.601s,grid2.073s,columns2.266s |
| Fulfillment normal grid |5.058s;5000 rows,total12720 |count1.465s,grid2.993s,columns2.570s |
| Fulfillment selected modal |1.322s;SKU21125076009000/P064,eight series,14-day slider |DailyDataGraph0.597s |

These are single observable modern measurements, not percentiles or matched
legacy improvements. Retained legacy destination timings cover chart entry,
not these grid toggles, and cannot be substituted. No code change was justified
by this trace; the existing deployed correction remains. Request timings include
gateway work; the residual includes rendering and automation observation and is
not a pure frontend CPU measurement. Existing complete-response proofs are reused.
The first Excess observer incorrectly required `SKU Code` rather than the actual
`SKU code`, timed out and reset the browser tool. Its requests succeeded after a
normal token refresh; the failed observation is retained, not reported as latency.
One corrected full-snapshot observation avoids both casing and AX-diff pitfalls.
Both resource windows restored with zero errors; temporary body-free nginx timing
configuration was restored byte-for-byte. No image/data/auth changes occurred.
Evidence: `planning-prepared-20261005-001/performance-extension/consolidated.json`,
request log, raw browser observations/screenshots, restoration receipts and
`profile-focused-extension.json` in the parent evidence directory.

### Six-destination Planning implementation checkpoint history

Direct human instruction verified in controller thread01a1037c-5d96-7700-87a8-89a575f6c9f8,
turn01a108ed-b51d-7832-8ac3-401e3b308a87, selects Planning as the next objective.
Execution contract: [Planning plan](PLANNING_PRESENTATION_RESEARCH_PLAN.md),
committed8f1bd27. Daily Data Graph implementation is delivered at01b75fa; its
72ms historical completed-modal baseline gap is **deferred/unaccepted**, not passed.
No further modal edit or benchmark belongs to this Planning goal.

Active step: connect and deploy the prepared Planning backend and the minimum
existing frontend contract wiring on3005, including landing counts and valid
grids/charts/subtabs/details/exports. Human priority correction relayed by the
controller on5 October supersedes further modern-before testing and sequencing
that would hold connection behind remaining independent wire/order proofs.
Preserve existing baseline evidence; no further pre-connection modern timing,
failure captures or retries. Inspect connected usable screens first, then the
already bounded final comparison against retained legacy baselines. Unmet exit: qualified exact sources,
prepared typed ingredients and SQL reads, existing frontend wiring, complete-value
and bounded matched browser proofs, deployment/restoration and six-area handoff.
Boundary: retainedApril7 data and existing preparation guards; no new facts,
engine/state/auth/action changes, copies/restores, framework/cache or3004cutover.
The new Planning goal was created successfully with no numeric budget.

Connected deployment checkpoint (5 October): images
`freshvcf-preview-mta:planning-connected-20261005-001` and
`freshvcf-preview-frontend:planning-connected-20261005-001` are now serving3005.
Backend startup admission and `/readyz` pass with admission digest
`5c90ae58f6478f7b1805f534f95fbe0de241a5280c4422ec70f28467221bf3e7`;
the selected April7 fixture and existing BTR generation remain unchanged.
Frontend production build passed with inherited lint warnings. All21 protected
containers retained their identities/configured limits; the two replaced
containers retained their ports, limits and restart policy. Browser landing
counts show GIT1627/1627, Expedite1030/1030, Excess9871 and Fulfillment12720.
The minimal child Expedite chart error state exposes existing Grid View/Go Back
and preserves the chart failure across grid toggles; no ambiguous labels are
repaired. UI detector found no findings in the two changed files. Evidence:
`planning-prepared-20261005-001/{build-connected.txt,admission-connected.txt,deploy-connected-receipt.json}`.
This is connection/readiness, not six-destination functional/performance closure.
Active next step: inspect connected destinations and their supported grids/details,
then retain the bounded final comparison and precise unavailable dependencies.

Priority amendment: direct human feedback in controller turn
`01a10998-32f1-73a3-96af-053ae78f2a58` confirms Excess and Fulfillment graphs and
Excel downloads working on3005. Freeze those passing surfaces; no further graph
or export proofs. Prioritize measured connected-grid latency, in order:
Expedite From Parent / `createAvailabilityAtParent` (the existing label is
“Create Availability At Parent”), Excess normal grid, Fulfillment normal grid.
Use the deployed prepared relations, one attributable trace and focused proof/
connected correction check per changed grid. Preserve configured5000-row paging,
complete values/nested fields, live scopes/filters and existing contract order.
The observed late column-config request rendered previous-grid headings before
the new definitions arrived; its bounded frontend correction is building.
No additional baseline campaign. Child GIT has1627 aggregate location occurrences
but genuinely empty transporter/shipment data. Its displayed default charts are
shipment-based; Grid View requests the inherited invalid combined207/8120
consumer and fails explicitly. This contract dependency is not an empty dataset
and cannot be silently repaired. Continue the three independent grid corrections.

Further direct human additions relayed by the controller retain the same goal:
fix the initial Planning landing latency and Fulfillment grid row-icon Daily Data
Graph latency, without reopening accepted overview graphs/exports or DBM/BTR
modal work. Active shared/parent correction: the connected landing reload took
24.6s (automation upper bound). Its one backend trace found seven repeated
producer-attribute/permission expansions (about3.1s combined of8.6s profiled
overview work). Reuse that exact request-local expansion across ten totals;
retain each consumer's admission and count grain. Parent Expedite's configured
5000-row request retains1030 dispatch rows,1443 availability rows and97097 nested
transit rows (8.97MB JSON). Trace found0.67s JIT compilation in the main page query
and1.07s sorting the unchanged nested transit output. Disable only that query's
JIT with transactional restoration; compress only the Planning grid endpoint's
unchanged JSON. No row/field removal, scope change or new persisted population.
Excess/Fulfillment grid corrections and the selected-row modal remain required
after the shared/parent exit; bounded read-only modal caller diagnosis may proceed
independently. Resource-final-002 restored all limits with zero restoration errors.

Shared/parent correction checkpoint: latency001 images are deployed and ready;
all21 protected resources are unchanged. Generated additive migration0036 adds
`fresh_excess_run_date (run_id, ReportDate) INCLUDE (SKUCode, WhCode)` and was
applied through the exact guarded fixture allowlist. Django check, model-state
check, migration plan, physical index validity and source guard checks pass.
The traced landing custom-count query now uses the index:338ms versus3863ms,
removing the historical921652-row scan. Complete ten-total reference checks
pass for broad, leaf and empty scopes, retaining string types and multiplicity.
One connected landing reload reached all visible totals in3.691s versus the
retained24.641s observation (automation upper bounds, normal restored limits).
Parent availability grid displayed1443rows with correct headings at4.921s after
Grid View, retaining5000-page configuration; loader toast dismissal was observed
separately and is not a clean timing. Complete parent response proof preserved
every field/order and97097 nested transit rows; JIT setting restoration passes.
Evidence: `excess-index-{migration,proof}.txt`, `overview-index-proof.txt`,
`landing-latency-after.{json,png}`, `parent-grid-latency-after.{json,png}` and
`parent-correction-proof.txt` under the Planning evidence directory.
This closes the bounded shared/parent correction checkpoint, not matched legacy
performance acceptance. Active next: diagnose and correct normal Excess grid,
then Fulfillment grid and its selected-row modal. Passing graphs/exports stay frozen.

Excess grid correction is deployed in backend latency002. The measured prepared
page query spent about3s in parallel JIT compilation; query-local JIT disable
retains all5000 captured row positions/fields and restores the caller setting.
Complete response proof passes in0.904s versus4.53s in the profiled prior read;
seven focused grid/filter tests pass. Startup admission and21 protected-resource
checks pass. Its connected browser exit is deferred pending reauthentication:
the surviving3005 tab is now at login after interruption. No browser timing is
claimed. Continue independent Fulfillment diagnosis while that check is pending.
Fulfillment's measured page SQL spends625ms of696ms in JIT; extending the same
query-local correction preserves the complete5000-row page and nested order
details against the retained HTTP response (0.822s direct read, caller JIT restored).
The subsequent deployed correction also reuses existing request identity, RunDate
and ready-only shared loading in the Fulfillment row-modal caller, preserving
selected sc/wc keys and the original row object. Its browser exit remains pending.
The Planning caller now uses shared `loadDailyData` with explicit sc/wc aliases;
the modal receives request identity/status/RunDate. Both targeted frontend suites
pass (7tests), including unchanged close/new-selection behavior and original-row
identity. The initial test invocation passed both files but was stopped during
unrelated whole-frontend coverage collection; the same files then completed with
coverage disabled. Backend grid/filter tests also pass (7tests).
Candidate latency003 initially failed the redundant-default-type lint rule; the
annotation was removed without behavior change and the production rebuild passed.
Both latency003 images are now serving3005. Startup admission preserves the
selected run/digest/BTR generation and all21 protected resources are unchanged.
Deployed broad-actor counts and complete5000-row responses equal the retained
HTTP responses, including nested order details. One gateway observation measured
Excess grid1.141s (prior5.671s), Fulfillment grid1.324s (prior3.446s); count requests
were2.353s/1.052s. These serial API observations do not prove concurrent browser
completion. Evidence: `build-latency-003-repair.txt`, `deploy-latency-receipt.json`,
`latency003-api-summary.json`. Subsequent browser results and resolved login
are recorded below; no complete performance acceptance is claimed.

Resolved login blocker (5 October): the user approved the replacement CAPTCHA;
login succeeded as the existing broad fixture reader. Corrected Excess and
Fulfillment grids visibly render5000 rows with totals9871/12720 and correct
headings. Their final timing observations are invalid: Excess used an incorrect
comma-formatted pager selector; Fulfillment's observer timed out despite reporting
the matching12720 element visible. Retain functional screenshots/text only, no
speed claim or favorable resampling. `excess-final-browser.*` and
`fulfillment-final-browser.*` retain those results.

The selected Fulfillment row21125076009000/P064 shows real order9414276 but its
modal returned HTTP400. Diagnosis found existing Planning `parseFloatAllNumericStrings`
converts sc to a number; the new caller omitted the previous `.toString()` conversion.
An exact string-key gateway request succeeds with complete graph data and RunDate
(`fulfillment-modal-api.json`). The smallest caller correction restores only that
conversion while retaining the original row object and shared ready-only loader.
Its frontend build, deployment and attributable modal recheck completed as
recorded below (`build-modal-caller-repair.txt`). Auth/permissions/source unchanged.

Final caller deployment checkpoint: frontend image
`sha256:725f04d6d8b9117188bea286fdb28d33b4730c2371d311ad357a4d337b01637c`
passed production build and frontend-only deployment; readyz and21 protected
resource checks pass. Authenticated selected-row modal recheck succeeds for
21125076009000/P064, displaying the real eight-series chart, current Norm135700,
location Ghilot Satellite Plant and working14→30day horizon. Gateway logs show
DailyDataGraph200; the response carries April7 RunDate. Evidence:
`fulfillment-modal-final.txt/.png`, `build-modal-caller-repair.txt`.
The8.192s automation upper bound establishes functionality, not minimum latency
or matched performance. Original row identity/race/ready-only tests remain valid.
The CAPTCHA/login dependency is resolved; do not request it again for this session.

### Final bounded Planning closure — 5 October 2026

The authorized six-destination prepared-presentation delivery is complete for the
retained April7 fixture, with the exact approved exceptions and limitations below.
The user directly confirms: **“all excel downloads have been confirmed by me,
dont explore”**. This closes actual-download acceptance for all six destinations;
no further export capture, inspection or test is authorized or needed. Earlier
synthetic confirmations are not being substituted for this current confirmation.

This reconciliation uses existing evidence only. Source/grain qualification,
one-time typed preparation, prepared SQL readers, existing UI connection, full
current-reference comparisons, bounded matched observations, deployment and
restoration are delivered. No new native-oracle matrix, benchmark, source
acquisition, public-VM comparison or serving mutation is opened. The current
matrix supersedes historical checkpoint statements about open deployment,
ordering, performance or export gates. Historical Daily Data Graph baseline
acceptance remains explicitly deferred/unaccepted.

Evidence root: `D:/freshvcf-build/evidence/planning-prepared-20261005-001`.

| Destination | Delivered preparation/read and functional proof | Bounded UI performance and accepted disposition |
| --- | --- | --- |
| GIT From Parent | Sealed source/display occurrences; complete1627-row grid, scoped count/page proof and genuinely empty selected shipment details (`git-reader-proof.txt`, `git-storage-proof.txt`); Excel user-confirmed | Entry/grid6.048s vs legacy6.799s; selected empty details inspected |
| GIT To Child | Corrected location/transporter grains;1627 broad/67 leaf location rows, count/page proof, zero transporter rows (`report-corrections/git-child-proof.txt`); Excel user-confirmed | Empty shipment chart2.873s vs4.362s; corrected populated grid2.796s. Legacy combined207/8120 has no comparable valid populated-grid timing; correction explicitly approved |
| Expedite From Parent | Prepared charts/counts/custom and1030 dispatch/1443 availability grids; broad and restricted native SQL main rows strict;97097 nested rows exact under separate order approval (`parent-independent-sql`, `parent-independent-sql-restricted`); Excel user-confirmed | Chart3.629s vs13.064s; dispatch14.122s vs31.328s; availability9.264s vs21.476s; both subtabs inspected |
| Expedite To Child | Complete1030 dispatch/2746 availability reference rows, restricted400/1404, supported filters/page/count/custom and pinned empty April request input (`expedite-child-{reader,filter,export}-proof.txt`); Excel user-confirmed | Chart2.984s vs4.265s; own-label103-row table, grid toggle and return navigation inspected |
| Excess | Separate normal/chart/custom grains; complete9871 normal rows, populated restricted, meaningful filter/page and full chart/custom reference responses (`grid-reader-proof-final.txt`, `chart-reader-proof.txt`, `custom-reader-proof.txt`); graphs/Excel user-confirmed |5000-row grid3.058s vs legacy26.242s; accepted chart/export surfaces frozen |
| Fulfillment | Separate summary/detail/chart/custom grains; complete12720 summary rows and real nested orders, restricted647 plus filters/page (`grid-reader-proof-final.txt`); saved workbook12720 data rows; graphs/Excel user-confirmed |5000-row grid5.058s vs legacy loading through55.100s, observed ready by89.611s. Selected real order9414276, eight-series modal1.322s and14→30day horizon proved; exact legacy grid completion unavailable |

The fixed consumer/grain map is PLANNING_CONSUMER_MATRIX.md. The plan's complete
legacy/current-reference method is covered by retained full-value source/current
consumer comparisons, including broad/restricted, meaningful filter/page and
affected NULL/duplicate/order cases. Additional native SQL/DLL comparisons cover
the named source/chart/Parent boundaries. This is not a claim of independent
legacy HTTP comparison for every endpoint/filter; that enlarged matrix is not
an exit in the authorized fixed verification boundary.

Approved dispositions, with no transfer beyond their exact scope:
- GIT child207/8120 separate-grain correction, Parent unpaged156 separator and
  child receiving own-location labels: explicit report-correction amendment.
- Six April7 chart sequences: `call_038051c3721a4d7f8a5a28f8ddf66e93`; all values,
  types, NULLs and duplicate counts strict, explicit order keys preserved.
- Parent `expediteDispatchestransit`: `call_rXDWYB4DZf82Ch7YyyoH5EEa`; only this
  run/source/date/route/array; broad and restricted97097 rows, zero missing/extra.
Original sequences remain retained. No serving sort or calculation change.

Precise limitations/dependencies retained in the handoff: positive shipment
behavior is unproved because this fixture's real shipment input is empty;
legacy-invalid Norm/filter paths retain explicit denial rather than an invented
repair; later daily publication/refresh/retention integration and action/request
workflows remain separate work. None authorizes adding facts or expanding this
finite retained-fixture batch. Parent grids remain materially slow despite the
measured improvement. Single automation timings are upper bounds, not percentiles
or a minimum-latency guarantee. The historical modal baseline stays unaccepted.

Final builds/admission/preparation/storage proofs are retained; documentation
reconciliation needs no new application checks. Backend
`freshvcf-preview-mta:planning-report-corrections-20261005-001`, frontend
`freshvcf-preview-frontend:planning-grid-latency-20261005-003` are the delivered
images. `report-corrections/deploy-receipt.json` records readyz/admission and22
protected containers unchanged. All resource windows are RESTORED with zero
errors; temporary nginx instrumentation is restored byte-exact. Operational
preparation costs, commands and rollback are in PREPARED_PRESENTATION_HANDOFF.md.

Qualification checkpoint: the fixed [consumer/grain matrix](PLANNING_CONSUMER_MATRIX.md)
covers all six destinations and their existing supported reads/exports. Read-only
retained SQL comparison proves complete derived BPR master bag97,097 and GIT
master bag2,567 equal to actual retained tables, with duplicate multiplicity.
April OpenExpediteRequests exists and is genuinely empty; its independent
acquisition is retained, not admitted through the June17 exception. Evidence:
`D:/freshvcf-build/evidence/planning-prepared-20261005-001/derived-source-comparison.json`
and `source-schema.json`. No engine or database mutation occurred.
Next active step: implement the coherent typed preparation/read batch using this
matrix, binding new derived outputs separately to sealed inputs. PostgreSQL,
wire/order, frontend and performance exits remain unproved. Invalid combined
GIT child and unpaged Expedite parent contracts retain their explicit dependencies.

Preparation implementation now includes `planning_source_sql.py`: bounded,
fixture-bound BPR/GIT derivation SELECTs with explicit native target conversions
and source occurrence references. Read-only execution on the actual PostgreSQL
fixture matches every retained SQL field and duplicate occurrence for both
masters (97,097/2,567), recorded in `source-pg-comparison.json` and compressed
`planning-source-pg.json.gz` under the same evidence directory. Five focused
conversion/length/fixture-boundary tests pass. These SELECTs are preparation
ingredients, not request-time readers or completed prepared-table delivery.
No schema migration, serving code deployment or source mutation occurred at
this checkpoint. The coherent prepared storage/read batch remains active.

Typed source-storage checkpoint: migration0027 adds only Planning BPR/GIT master
rows and their separate immutable receipt. `prepare_planning_sources` loaded
97,097/2,567 rows in14.535s using the qualified queries. `verify_planning_sources.py`
proves exact complete PostgreSQL readback against each derivation, including
source ordinals/multiplicity, stable repeat verification and15 guarded mutation
attempts (insert without build, insert after seal, update/delete/truncate on all
three relations). Check and migration-state check pass; no pending migrations.
Evidence: `prepared-source-proof-final.txt` in the Planning evidence directory.

The initial ordinary migrate created empty DDL before fixture migration-history
recording rejected it. Recovery verified no rows and exact owned guards, reversed
only the empty unrecorded0027 objects, then applied the real migration atomically
through existing `migrate_btr_fixture --planning-sources`. No fake migration or
source reset; fixture admission/freeze digest unchanged. Recovery script retained
externally. Owned proof containers were serial,4GiB/2CPU, no ports/restart, removed
on exit. Serving application code is still unchanged; prepared consumer joins,
SQL readers, April-history admission and frontend/performance proof remain active.

Prepared source reader now checks fixture/day, source/recipe receipt and exact
immutable guards before exposing run-bound typed SQL relations. No broad source
reconstruction occurs in this boundary. Nine focused tests pass, including
missing/changed receipt, wrong run/day/kind and guard drift; actual PostgreSQL
admission/readback passes in `prepared-source-reader-proof.txt`.
The separate Excess/Fulfillment normal-grid preparation queries now resolve
stable dimension matches, raw display ingredients, normalized keys and all
filter/source ordinals once. Complete fact-and-display bag comparison against
existing selectors passes for9,871 current-day Excess and12,720 Fulfillment
summary occurrences (`grid-preparation-reference.txt`). These queries are not
called by HTTP and are not yet persisted occurrence tables. Next: persist these
qualified grains alongside the remaining GIT/Expedite/chart/custom ingredients,
then wire SQL consumers. Ordering/wire/browser acceptance remains unproved.

Normal-grid implementation: migration0028 has persisted and sealed9,871 Excess
and12,720 Fulfillment occurrences. Complete SQL EXCEPT ALL readback, repeat
checksum verification and15 insert/update/delete/truncate guard checks pass;
the fixture source digest is unchanged. The fixture grid/count API now calls
the prepared reader in the checkout, with live permission bags, canonical
filters, SQL pagination and selected-pair Fulfillment details. It is not deployed.
Complete ordered Python-reference comparisons pass for both full grids,
page2, populated restricted scopes224/647, empty scopes, product/location,
numeric, hierarchy, child and coverage filters. A custom-only activation mismatch
was corrected to preserve the existing ignored-filter contract; evidence retains
the failed proof.25 existing/admission tests and3 filter tests pass. The final
readback after removal of a redundant slow date predicate, activated custom-filter
case and Django migration checks passed:25 complete ordered grid/count cases,
system check clean, no model drift and no pending migrations. Evidence is under the same Planning
directory (`grid-reader-proof*.txt`). This closes no whole-page/browser gate;
chart/custom/GIT/Expedite preparation, April request-history admission, deployment
and all six end-to-end journeys remain outstanding under the same active goal.

Active next item: prepare Excess/Fulfillment chart membership at the separate
description-before-aggregation grain. Required proof is exact complete chart
datasets and response ordering against the retained selectors, including scoped
totals and attribute duplicate expansion after aggregation. The normal-grid
occurrences cannot supply this grain because their other INNER dimensions would
change eligibility. Keep source facts unchanged and filters ignored as deployed.

Chart implementation checkpoint: migration0029 adds the separate typed chart
membership/display grains and immutable receipt. Preparation loaded65,694
members and6,068 displays in29.58s with unchanged fixture source digest.
All16 complete ordered chart datasets (eight broad/eight populated restricted)
match the retained independent selectors, first for preparation and then through
the SQL aggregate reader. Counts/sums remain live and permission weighted;
display attribute expansion follows aggregation. Existing response formatters
are reused; fixture graph endpoints are connected in the checkout only.
19 focused tests pass; Django check/model state/migration plan are clean.
Full source readback of all12 membership/display datasets and15 mutation-denial
checks passed; repeat verification took1.10s without writes. Evidence: `chart-preparation-proof.txt`, `chart-load.txt`,
`chart-reader-proof.txt`, `chart-storage-proof.txt` in the Planning directory.
No serving deployment or browser acceptance yet. Custom grids and all
GIT/Expedite consumers remain required; the six-destination goal stays active.

Active item: custom Excess/Fulfillment occurrence preparation and SQL readers.
The retained NMS image has97,097 rows, so an empty-source shortcut is invalid.
Resolve NMS/parent-description/standard matches once, preserve independent fact
and source ordinals, then scope/order/page before selected display expansion.
Fulfillment's conflicting-NMS ordering denial remains mandatory. Required proof:
complete scoped ordered custom responses, NULL omission, paging and that denial.

Custom-grid checkpoint: additive migration0030 (after0029, reversible guard SQL)
and repeatable preparation loaded9,871 Excess/12,720 Fulfillment occurrences in
12.07s. All source-reference bags and complete storage readback match;15 mutation
attempts are denied and repeat verification is unchanged. Ten complete ordered
responses pass against existing consumers: full exports, page2, populated restricted,
empty and past-end cases. The retained population has no unmatched NMS and no
conflicting custom ordering keys, so this data does not exercise the ambiguity
denial branch. Ten focused admission/read tests and Django check/model/migration
checks pass. Fixture custom endpoints are wired in the checkout, not deployed.
Evidence: `custom-{preparation,reader,storage}-proof.txt`, `custom-load.txt` in
the Planning evidence directory. Active next item is the remaining GIT/Expedite
preparation/read batch; all six browser/performance/deployment exits remain open.

GIT shipment-only boundary now separates qualified empty transporter consumers
from positive aggregate GIT. Canonical transporter INSERT requires InTransitData;
the admitted April source is empty. All four child chart SQL datasets and custom
SQL begin from transporter rows, so these branches may return their existing empty
envelopes after source and scope admission. Actual fixture read confirms the four
sections and zero custom rows (`git-empty-shipment-proof.txt`). Positive parent
grid/location counts remain unavailable pending preparation, not changed to zero.
Three terminal admission tests pass after correcting their stale run mocks to
carry DAILY_CHAIN kind. No native ordinary-publication behavior or serving deploy
changed. Full independent wire/browser proof remains outstanding.

Active item: positive GIT location preparation/read. Preserve count's LEFT pair
join and grid's INNER pair eligibility in one explicit occurrence relation with
an eligibility flag. Bind exact derived master/source ordinals, description and
filter-owner matches; scoped counts and parent grid paging remain live.
Empty admitted transit proves the transporter LEFT join's NULL occurrence and
empty details only. Required proof includes independent complete occurrence bags,
scoped count/grid values and canonical integer penetration sort; no repaired
combined child SQL or invented tie-order acceptance.

GIT implementation checkpoint: migration0031 adds a sealed location occurrence
relation and receipt after0030. Independent source-join bag comparison proves
1,627 count occurrences, all grid eligible in this retained dataset. Preparation
took0.47s. Full SQL readback and10 mutation-denial checks pass; repeat verification
preserves source/recipe/digest. Positive parent grid and parent/child location
counts now use prepared references, live direction-specific scopes/filters and
SQL paging in the checkout. All1,627 parent rows, page2, empty scope, empty transit
details and inherited child207/8120 denial pass internal checks. Seven admission
tests and Django model/migration checks pass. Evidence: `git-preparation-proof.txt`,
`git-storage-proof.txt`, `git-reader-proof.txt`, `git-load.txt` in Planning evidence.
This is not independent legacy wire/order parity; that proof and scoped filtered
wire cases remain required. No deployment or browser/performance acceptance yet.
Expedite preparation/read, overview, complete wire comparisons and delivery remain
active within the unchanged six-destination objective.

Active item: Expedite's four grid occurrence grains. Parent dispatch and child
dispatch use LEFT source matches; parent availability also requires the exact
derived parent BPR master; child availability uses INNER matches with LEFT parent
description. Prepare source/filter ordinals and display hierarchy once, keeping
request/transit overlays separate. Required proof is complete occurrence bags
against the existing selectors, followed by scoped wire/filter/page proof.

Expedite grid storage checkpoint: migration0032 after0031 adds one explicitly
direction/branch-keyed occurrence relation and separate immutable receipt.
Independent source-bag proof passes parent dispatch1,030/availability1,443 and
child dispatch1,030/availability2,746. The loader persisted6,249 references in
2.09s. Complete SQL readback for every branch,10 mutation-denial checks and stable
repeat verification pass, with unchanged source digest. Four admission tests,
Django check/model-state/migration-plan checks pass. Evidence:
`expedite-preparation-proof.txt`, `expedite-grid-{load,storage-proof}.txt` in the
Planning evidence directory. These are prepared inputs, not completed readers:
live filters/scopes, response serialization, April request-history admission,
Expedite charts/custom/counts, overview and all delivery gates remain open.

Expedite reader contract correction: pinned `ExpediteFromParent` SQL confirms
nonempty NMS drives the parent nested transit results independently of empty
shipments. Dispatch LEFT joins its filtered/scoped CTE through remarks;
availability INNER joins it, both before grid paging. The reference reader now
supports explicit remark/Pick inputs, preserves GROUP BY before NULL substitution
and string-valued output, and still denies nonempty NMS when those inputs are
missing. Eight focused parent tests pass, including duplicate collapse, distinct
NULL/space groups, remark-dependent Pick joins and past-end paging. This is
reference implementation only, not SQL/wire parity or serving acceptance.
The retained full Pick source is now qualified below; PickPostRow alone is
insufficient for ParentStockForRationing.

Parent Expedite prepared read: migration0033 after0032 adds typed NMS/remark
base occurrences, grid/Pick matches and a separate immutable receipt, with
reversible build/seal SQL. The actual frozen8063-row Pick staging source passes
full-column checksum verification (`4a5583e805d564dd57f03117f43e7ba7f671e54f0f436b371cab2bca011bc229`).
Preparation persisted97100 bases and5 matches in9.87s; full EXCEPT ALL readback,
15 mutation-denial checks and repeat verification in1.78s pass. Django checks,
model-state and migration plan are clean; source admission/guards are unchanged.
Evidence: `expedite-transit-{schema-check,migrate,load,storage-proof}.txt` in the
Planning evidence directory. No imported source or prior migration was changed.

The fixture parent route now selects the prepared SQL reader. Main grids retain
scoped/filter-weighted rows, NULL omission, decimal string scales, ambiguity
denial and paging; nested results use the full eligible CTE before paging. Six
complete source-reference comparisons pass (full1030/1443, page2, leaf78/161,
empty, past-end and SKU filter), and six independent nested-source-join bag
comparisons pass. Canonical nested dispatch returns97097 rows even with empty
scope; availability transit is0. Preserve that inherited output; do not silently
scope/page it. Nested SQL has no ORDER BY: bag proof is explicitly not independent
legacy wire/order acceptance. Evidence: `expedite-parent-reader-proof-corrected.txt`
and `expedite-transit-reader-proof-final.txt`; initial failed probe transcripts
are retained. Twenty-three focused tests pass, including route selection and
admission denial. Seven additional complete filter comparisons pass for Stock,
Tags (empty result), location type, ignored ForChildren, hierarchy and inactive/
active custom attributes (`expedite-parent-filter-proof.txt`). Together these are
13 source-reference response cases, not independent legacy API acceptance.
Active item remains the Expedite reader batch: independent legacy wire proof,
April request-history admission/child reads and remaining charts/custom/counts.
Overview, before/final browser comparisons, deployment and restoration remain
required. Serving has not been rebuilt or restarted; engines, accepted F1/F2 and
authentication permissions remain unchanged.

Child Expedite request-source admission now uses a separately pinned April
qualification, `baseline/planning-april-empty-requests-v1.json` (SHA256
`0cec4bea850da03b9e57d59fe114a15d68fb60254637988451b609995757a33c`).
Read-only requalification verifies the owned BPR clone is READ_ONLY, its backup
owner matches the sealed dataset, all nine source columns match and the table
is empty. It also reconciles the earlier acquisition bytes. The imported roster
and June17 exception remain unchanged. Missing/changed bytes, fixture source,
run, day or manifest deny admission. Evidence: `april-request-admission-proof.txt`.

The child fixture route uses prepared grid occurrences with ParentWhCode scope,
live ForChildren multiplicity, numeric fields, NULLs, ETA and empty admitted
request/transit overlays. It does not load the parent BPR master or NMS. Existing
Norm-filter denial remains. Six complete grid cases and seven filter cases pass
against the source reference (full1030 dispatch/2746 availability, leaf400/1404);
23 focused tests pass. Evidence: `expedite-child-reader-proof.txt` and
`expedite-child-filter-proof.txt`. Unpaged export data and positive ForChildren
(484/1516 rows) also pass (`expedite-child-export-proof.txt`), giving15 child
source-reference cases. All six shared-parent regression cases pass unchanged
(`expedite-parent-child-shared-regression.txt`). This is not independent legacy
wire or frontend acceptance; no serving rebuild/restart has occurred.

Expedite count reader now reuses the prepared child occurrence grain with exact
INNER dimension eligibility and critical PipelineInventoryColor restriction,
using WhCode scope for parent and ParentWhCode for child. It does not use parent
master multiplicity or mistake child grid availability2746 for canonical count1443.
The fixture count route is wired; live supported filter joins remain multiplicity-
preserving. Norm-filter qualification remains explicitly unavailable. Fourteen
source-reference cases pass (six broad/leaf/empty and eight SKU/Stock/ForChildren/
custom cases across both directions), plus15 focused unit tests. Evidence:
`expedite-count-proof.txt`, `expedite-count-filter-proof.txt`. No new storage or
source mutation was needed. This proves the internal count read, not independent
legacy filtered wire acceptance. Next active item is overview's exact ten-count
grain mapping; remaining Expedite chart/custom and delivery exits remain required.

Prepared overview is now wired for the fixture: GIT review uses its INNER pair
eligibility, Expedite uses dispatch count grains, Excess/Fulfillment reuse exact
normal review counts, and custom totals read scoped typed facts without metadata
joins. Empty transporter total is backed by the retained empty shipment source.
All ten string-valued totals match the existing source reference for broad,
restricted and empty scopes (`overview-reader-proof.txt`). Broad GIT parent/child
1627/1627, Expedite1030/1030/custom1030, Excess9871/9871 and Fulfillment12720/12720
are verified. This removes the positive-GIT terminal-only dependency in the
checkout; it is not deployed or independent legacy wire/performance acceptance.
Active next item is the remaining Expedite chart/custom read batch, followed by
consolidated independent wire, frontend, deployment/restoration and handoff gates.

Custom Expedite prepared read is now implemented and wired for the fixture.
Additive migration0034 after0033 stores exact LEFT NMS/BPR/parent-description
references and a separate immutable receipt; it does not reuse normal-grid
eligibility. Preparation persisted1030 occurrences in0.78s. SQL applies live
parent-location scope, checks conflicting native sort keys, then pages/serializes
the selected rows with native aliases, numeric values and NULL omission.
Five complete source-reference comparisons pass: full1030, page2=50, leaf400,
empty and past-end. Full EXCEPT ALL readback,10 mutation-denial checks and
repeat verification0.12s pass;16 focused tests and Django model/migration checks
pass. Evidence: `expedite-custom-{schema-check,migrate,reader-proof,storage-proof}.txt`
in the Planning evidence directory. Source admission/guards remain unchanged.
These checks do not establish independent legacy wire or browser performance.
Active next item is Expedite chart preparation/read, followed by the consolidated
delivery gates. Serving has not been rebuilt or restarted.

Expedite chart membership qualification now passes all six exact source-join
bags: parent critical1030, receiving4722, nil-stock2746, chronic2473; child
critical20 and receiving4722. Parent pre/post uses2416 source/target Pick pairs
with explicit child-location multiplicities representing4186080 joined rows.
The canonical child match is location-only, not SKU/location. Complete independent
Python source-bag comparisons pass (`expedite-chart-members-complete-proof.txt`).
Additive migration0035 now stores15713 chart memberships and2416 pre/post
matches under immutable source/recipe/Pick-bound receipts. Preparation took7.82s;
seven complete EXCEPT ALL readbacks,15 mutation-denial checks, repeat verification
and Django model/migration checks pass (`expedite-chart-storage-proof.txt`).
Live scoped SQL aggregates now match complete existing source-reader datasets
for broad, populated restricted and empty scopes, including pre/post totals.
The initially selected restricted case was empty; its replacement proves parent
critical2/receiving8 and child receiving8. Broad reads took0.59s parent/0.49s
child in this functional proof, not a matched browser benchmark. Eleven focused
admission/chart tests pass. Fixture graph routing now selects these prepared
reads; production calculation/publication paths remain unchanged.

Independent retained read-only SQL proves all16 broad/restricted chart bags
equal in every value, NULL and multiplicity. Four actual deployed-DLL formatter
comparisons are exact on their identical ordered datasets. Reversing only broad
critical rows changes all103 receiving labels for both directions, reproducing
the known flaw on April7. The existing parent-only own-location label exception
transfers to this same transformation: all differences are receiving labels;
quantities, other fields and state remain identical. Child ambiguity denial is
preserved. Broad SQL sequences differ, and pre/post UNION order differs; this
is recorded, not accepted through a new implicit tie-order exception. Ordered
wire/browser acceptance remains open. Evidence: `expedite-chart-reader-proof-002.txt`,
`expedite-chart-reader-restricted-proof.txt`, `expedite-chart-canonical/comparison.json`
and `expedite-chart-canonical/formatter-comparison.json`. Serving remains unchanged.
The integrated Expedite backend checkpoint passes32 focused tests, including
fixture routing without full context reconstruction and preserved child-label
denial (`expedite-backend-unit.txt`). Preparation/read wiring is complete for
this batch; full ordered-wire and six-destination delivery acceptance are not.
Active next item is necessary API/frontend contract connection, affected build/
admission checks and deployment to3005, followed by connected-screen inspection
and the bounded final comparison. Keep chart-order and inherited child/unpaged
SQL dependencies explicit; they do not block connecting valid consumers.
The preserved baseline observations are `browser-before-trials.json` in the
Planning evidence directory. No more modern-before captures are authorized.

Checkpoint cadence: retain existing commits, accumulate the remaining chart and
backend integration work, and commit/push at the coherent backend milestone after
focused proof. Individual reader proofs/tracker updates do not trigger commits.
Later checkpoints are integrated frontend/deployment and final validated delivery.


### Daily Data Graph correction delivered; baseline gate remains unmet

Fixture history now reads selected-pair producer attributes under the existing
admission/receipt/freeze contract. Scope ID validation, hierarchy expansion,
NULL denial, duplicate eligibility and ordinary/command paths are unchanged.
24 focused tests pass; independent review has no findings. Both selected full
responses and the restricted response are byte-exact after deployment.

Final authorized BTR pair: **2.169s modern /11.888s legacy** fully settled.
Modern chart-ready was1.843s; legacy valid chart-ready was11.888s. Same retained
April7 pair21101153051000/P015_1004, broad scope,14days,1280x720;
SQL/PG3GiB/2CPU, APIs4GiB/2CPU. Both horizon controls changed15 and restored14.
The retained **2.097s baseline gate remains unmet by72ms**. Its earlier readiness
criterion remains qualified; the favorable incomplete1.008s trace is not a
replacement baseline. One pair is not a latency distribution.

Modern gateway recorded graph401, normal token renewal200, retried graph200.
The2.169s includes renewal, without subtraction or resampling. No unrelated
requests appear in the bounded gateway window; host-wide idleness is not proved.
HTTP completion1.483766s leaves0.685234s to completed observation, including
chart/modal transition and observer overhead, not isolated React work.
Actual serving profiling found2.092s SQL of2.384s backend, with selected attribute
reads0.028s. Profiler overhead included; initial instrumentation miss retained.
Profiler removed, normal two-worker Gunicorn restored. Backend scope-20261005-001
serves with unchanged frontend003 full-ready opening and no early strip.
All resource caps restored with errors[]; temporary viewport reset.
No engines, accepted F1/F2, auth grants, source data or adjacent pages changed.

Consolidated evidence: `D:/freshvcf-build/evidence/daily-graph-modal-20261004-001/`
`scope-validation.json`, `scope-final-{legacy,modern}.json/.png`,
`scope-final-interactions.json`, `scope-final-gateway.txt`,
`scope-serving-summary.json`, `backend/scope-deployed.json.gz`,
`resource-scope-final-001/budget-result.json`.
Stop at this precise unmet gate; no further sampling or adjacent implementation
under this amendment. Operational details are in the presentation handoff.

### Earlier replacement comparison (before selected-scope correction)

The user-authorized replacement comparison is complete, with the corrected
observer and matching SQL/PG3GiB/2CPU, API4GiB/2CPU caps. Same pair
21101153051000/P015_1004, April7 fixture, broad scope,14days,1280x720.
Modern completed modal: **2.788s**; legacy: **10.443s**; retained modern baseline:
**2.097s**. Both eight-series charts, settled transitions, selected pair, populated
legends and enabled controls were observed. Both horizon controls changed to15
and restored14. Modern wins this legacy observation but **fails the baseline gate**.
Modern HTTP completed at1.895840s, followed by0.892160s to completed-modal
observation. These bounds include browser-tool overhead, not direct React timing.
Unrelated DBM graph requests completed on3005 during the comparison window;
quiet application load is therefore not proved. No token/date retry appears for
the measured modern BTR opening. This is one bounded observation, not a latency
distribution. The earlier baseline uses an earlier chart readiness criterion;
it was not weakened or replaced by the favorable1.008s incomplete-transition trace.

No application change, deploy or speculative correction was made. All comparison
limits restored, errors[]. Evidence: `replacement-validation.json`,
`replacement-{legacy,modern003}.json/.png`, `replacement-interactions.json`,
`replacement-gateway.txt`, `resource-replacement-001/budget-result.json` under
`D:/freshvcf-build/evidence/daily-graph-modal-20261004-001`.
The full ready-only modal remains deployed. The authorized comparison is finished;
overall performance acceptance remains open at the2.097s completed BTR gate.

### Earlier Daily Data Graph implementation and retained observations

The bounded [Daily Data Graph contract](DAILY_DATA_GRAPH_MODAL_PLAN.md) and
user-authorized responsive addendum are implemented and deployed on3005.
User amendment5October removes the early loading strip in deployed frontend003.
Both entry points now remain closed during fetch and first appeared with the
eight-series graph and details in the functional browser checks. They reject
stale completions, reuse response
RunDate, and retain chart/source semantics. Fixture history resolves validated
metadata once per request:58 to15 SQL calls. Both selected responses and the
restricted response remain byte-for-byte identical after deployment.

Proof:21 backend tests,10 frontend tests, TypeScript and production build pass.
Both DBM/BTR layouts pass CSS1280x720,1680x971 and1713x971; bounded body scrolling
keeps the close button reachable. All five resource windows restored without
errors;21 protected containers unchanged. Evidence and operational details:
[handoff](PREPARED_PRESENTATION_HANDOFF.md),
`D:/freshvcf-build/evidence/daily-graph-modal-20261004-001/validation.json`.

Timings below are retained from frontend002, before the user-requested removal
of early loading. Frontend003 follow-up observations and their acceptance limitation are below.

| Bounded observation | Modern before | Modern002 | Matched legacy | Former loading |
|---|---:|---:|---:|---:|
| DBM row graph |2.360s|1.227s|9.820s|0.308s|
| BTR row graph |2.097s|3.542s|6.159s|1.152s|

**Unmet exit: completed matched BTR comparison remains unproved.**
The historical incomplete comparison below is superseded by the completed
replacement observation above; its raw evidence remains retained.
The authorized5October follow-up used one deployed003 diagnostic and one final
matched opening pair, with no code change or speculative optimization. Diagnostic:
2.379s to observed chart,2.106s to HTTP completion, no token/date retry. A separate
native profile preserved the exact response and15 queries:0.364s SQL of2.365s
including profiler/first-request initialization. Reader checksum work was
substantial; this does not attribute the serving browser request.
Final modern003 had the selected pair,14-day horizon and eight-series chart at
1.008s (HTTP0.919s), below2.097s retained baseline. This is a chart observation,
not a claim that the modal transition and all interaction work finished then.
The final legacy observer stopped at5.671s while **No data to display** remained:
its predicate only excluded **No Data Available**. Legacy later rendered, but its
exact completion was missed and modern began before that completion was proved.
Therefore the final pair cannot close the required completed comparison.
No further sample is authorized. Preserve the build; a separately authorized
comparison must require populated chart legends, absence of either empty overlay,
and a completed interactive modal. Do not infer another code bottleneck.
The corrected read-only observer is retained as `corrected-modal-observer.cjs`
in the evidence directory. Ten offline cases pass, including rejection of the
actual premature legacy stop, stale pair, missing legends, transition and disabled
controls. No live opening or application change was used for this correction.
Evidence: `D:/freshvcf-build/evidence/daily-graph-modal-20261004-001/followup-validation.json`,
raw traces and screenshots. The subsequent modern horizon interaction passed
and restored14. `validation.json` includes the follow-up evidence.
The browser interruption before the diagnostic terminated its budget controller:
its exact named Windows jobs were absent and PostgreSQL identity/limits were
explicitly restored from the saved receipt, errors[]. The final window restored
normally, errors[]. See `resource-followup-001/budget-recovery-result.json` and
`resource-final-003/budget-result.json`. No graph sample was consumed by that
interruption; no serving services or databases were replaced.
F1/F2, engines, data, permissions and completed Guided remain unchanged. The
Guided review automation remains paused; no adjacent page work has started.

### Complete: bounded Guided Insights prepared-presentation delivery

The bounded whole-page contract covers all five visible tabs and the Chronic
grid on the retained April7 fixture. It preserves the existing frontend,
permissions, source values/types/NULLs/multiplicity/order, F1/F2 and accepted
BPR/BTR. Hidden Custom Screens, main DBM commands, daily production integration,
other pages and Stages3–5 remain excluded. This bounded delivery does not close
the broader Stage2 page ledger or establish independent legacy ordering parity.

The initial three paired walks had four failed consumers. Human correction
froze passing DBM and Chronic charts, authorized shared typed Availability
preparation and separate Chronic-grid/Excess corrections, then one final
three-pair trial of only those four consumers. All corrected trials complete.

| Consumer | Legacy median seconds | Modern median seconds | Evidence |
|---|---:|---:|---|
| Availability Trend | 16.541 | 3.494 | Final corrected three pairs; PASS |
| Chronic charts | 4.970 | 1.427 | Original passing three pairs; frozen |
| Chronic grid | 3.957 | 2.923 | Final corrected three pairs; PASS |
| Availability Ageing | 14.663 | 4.077 | Final corrected three pairs; PASS |
| DBM four panels | 16.583 | 3.222 | Original passing three pairs; frozen |
| Excess two panels | 3.533 | 2.137 | Final corrected three pairs; PASS |

Final pairs alternate legacy/modern, modern/legacy, legacy/modern at horizon9,
age1, equivalent broad scopes, DBs3GiB/2CPU and APIs4GiB/2CPU. Pair1 enters the
known Guided route from the landing page; pairs2–3 use tab transitions. All24
observed screens complete, and all24 legacy/modern windows contain successful
gating HTTP responses. No passing view was rebenchmarked. One earlier heading click
did not navigate from the landing page; its46.16s harness failure is retained
separately, not represented as a report response or discarded successful sample.
The original failed36-observation walk, including its censored Ageing wait and
overlapping early user traffic, remains retained. No favorable report resampling.
Window003 restored original PostgreSQL1GiB/1CPU/swap2GiB and Windows job limits
without errors. Only MTA and frontend container identities changed;21 other
retained serving containers are unchanged.

Daily DBM preparation0021 seals97,097 occurrences (28.925s;52,379,648 bytes).
Chronic charts retain their efficient typed SQL. Chronic grid0022 seals3,340
occurrences (8.191s;1,384,448 bytes), preserving its LEFT-NMS grain separately
from chart INNER-description eligibility. Shared Availability0023–0025 seals
8,483,003 history occurrences plus97,299 snapshot references; separate Excess
contains920,774 importer-owned occurrences. The full build took1700.176s at
1GiB/1CPU. Before the added covering index, their relation sizes were
1,940,742,144 /43,376,640 /213,090,304 bytes. Index0026 adds840,966,144 bytes.
Source ordinals preserve filter owners and snapshot eligibility; no integer
business-key dictionary or per-user/horizon cache was introduced. Scope,
arbitrary supported filters, horizon, minimum age and aggregation remain live.

The original request-built history joins and first prepared heap-scan candidate
preserved output but failed latency. The measured Availability plan scanned the
full1.294GB heap for roughly849k qualifying rows. The covering run/date index
carries the fields required for broad permission joins, aggregation and ordering.
Before-index Trend/Age diagnostics55.759/36.597s fell to6.459/1.286s at1CPU;
the browser results above, rather than those diagnostics, establish the exit.
Two uncommitted loader attempts were stopped for NULL-join eligibility and
repeated per-row seal checks. Explicit corrective migrations preserve ordinary
SQL NULL exclusion and move invariant seal validation to a statement guard.

All15 original integrated broad/restricted responses matched completely. After
the corrections, all8 affected decorated endpoint cases again match every
field/type/omission/occurrence/order. Prepared PostgreSQL differentials cover
duplicates, NULL exclusion, snapshot eligibility, permission/parent weights,
grouped raw-owner filters and nondefault dates/age. History prepared2/2 and
fallback5/5 pass; daily family proofs remain retained. Full streamed repeated
readback reproduces both history digests; all7 history mutation probes reject
without changed rows. Django/schema/migration-enabled checks and builds pass.
The wider historical suite's two unrelated Expedite failures remain unclaimed.

The bounded browser inspection covers all panels/full chart tables, Chronic
expansion/local filtering3340→76→3340, age/horizon refresh and a restricted
one-series Depot actor. Affected restricted endpoint reads pass on the final
image. The deployed final reader also renders age2/horizon8 after refresh.
Existing Chronic group ordering and DBM pie ordering differ from legacy; the
correction preserves the prior modern order exactly. This is an inherited
source-disposition item, not an independent legacy-order parity claim or waiver.

Guided-only synchronous AG Grid XLSX download is deployed; unrelated shared
callers retain their original path. User confirms both DBM and Chronic grid
downloads. DBM location workbook80,368 bytes has all129×25 cells exact; Chronic
location-chart workbook65,323 bytes has all91×26 cells exact. Grid download is
user-confirmed but its separate workbook was not located for cell validation.
In-app download-event capture remains unavailable. Four focused frontend tests
pass; TypeScript retains only the same three pre-existing useBTR errors.

Corrected MTA image`7b31f6da2c336301e26729ed3599434d051f965d1effa31dbbd3fc4a2229626d`
and frontend`893c1672179651413144cf1ac3a95d5414313ec3c8339cbb3c68204fde53e7ac`
serve3005. Readiness confirms unchanged admission
`5c90ae58f6478f7b1805f534f95fbe0de241a5280c4422ec70f28467221bf3e7`,
selected run`bfd75b4b-a9df-4a08-82d3-852e3324b623` and BTR generation
`e5bdac30-bbd9-45d8-a93d-84a645fad73c`. Rollback, preparation costs and daily
producer/refresh/retry/retention debt are in the existing operational handoff.
No scheduler, calculation replay, permission change or3004 cutover occurred.

Evidence roots: `D:/freshvcf-build/evidence/guided-presentation-20261004-001`
(original/final trials, response comparisons, exports, restoration and deployment;
consolidated`guided-final-validation.json`)
and`D:/freshvcf-build/evidence/guided-history-prepared-20261004`
(build/repeat digests, migrations, indexes, diagnostics and guards).

### Complete: singular BPR UI-performance delivery

The bounded 4 October BPR exit passes from starting checkpoint `a4c64eb`.
The same retained April 7 dataset, effective authenticated scopes, empty filters,
29 configured columns, column widths and 5,000-row page were compared on legacy
3002 and modern 3005. Modern used 127.0.0.1 to isolate browser cookies, with the
same serving port and application. Exactly three paired completed-screen trials
ran in legacy/modern, modern/legacy, legacy/modern order:

| Pair | Legacy seconds | Modern seconds |
|---|---:|---:|
| 1 | 15.322 | 4.958 |
| 2 | 9.068 | 5.232 |
| 3 | 7.893 | 4.961 |
| Median | 9.068 | 4.961 |

Modern's median is 45.29% lower. All four gating responses (grid, count,
configuration, layout) completed successfully before the recorded screen exit;
each screen displayed 5,000/97,097. Pair 1 legacy includes three initial 401s and
its ordinary token-refresh retries; those costs and responses are retained.
PageDown changed rendered rows in pair 1 on both stacks; later repeated PageDown
kept the same position on both. Final Ctrl-End settled at row 4,999 on both.
No extra favorable load samples were taken. This is the agreed bounded browser
comparison, not universal latency, p95 or load-test acceptance.

One immutable typed relation prepares the six native candidate joins once.
It preserves raw filter owners, original ordinals, nullable matched-standard
presence and numeric pens. Live scope/filter/raw ordering precedes key-bag paging;
final selected keys expand every occurrence before remark/trend joins. Count and
analytics retain their distinct grains. The retained fixture has 97,097 unique
candidate keys, while differential tests also prove duplicates and missing joins.
Query-local JIT-off removes measured 3,254 ms compilation from a 3,379 ms prepared
query and restores the prior setting on success/failure. Native broad read fell
from 14.10 s to 1.41 s; this diagnostic excludes the full browser/gateway path.
The fixture now serves its retained 29-column AdminBPR configuration instead of
the earlier 19-column static projection, matching every canonical ordered value
and type. No frontend code, normal admission, permissions or export reader changed.

Migrations 0019/0020, complete typed readback/repeat verification and mutation-guard
rejections pass. Added storage: 65,232,896 bytes; initial command: 75.44 s.
Exact ordered 5,000-row and six-row restricted wire/count/analytics comparisons,
11 focused PostgreSQL tests, Django checks/migration plan, source baseline and
independent focused review pass. Only MTA was recreated; 22 other container
identities remain unchanged. The resource window (databases 3 GiB/2 CPU, APIs
4 GiB/2 CPU) is RESTORED without errors; PostgreSQL is back to 1 GiB/1 CPU.
These are existing shared database services, not independently isolated load rigs.

Evidence: `D:/freshvcf-build/evidence/bpr-ui-performance-20261004-001/`
`consolidated-bpr-result.json`, `prepared-validation.json`, `final-reader-proof.json`,
`ui-config-comparison.json` and `resource-window-final/budget-result.json`.
Serving image: `freshvcf-preview-mta:bpr-prepared-20261004-001`, immutable identity
`sha256:a8733a685bb53c9449dcafb2d2453a0b7b0171214de9655fdab5d4bb45c152fa`.
Run, fixture admission and BTR generation are unchanged. See
[operational handoff](PREPARED_PRESENTATION_HANDOFF.md) for preparation and rollback.
Stop here: no adjacent report optimization or normal daily publication integration
is opened. Daily preparation/refresh remains explicit later producer work; this
exit does not accept all remaining BPR workflows or the broader F3 programme.

### Holistic prepared presentation batch authorized

The human accepts the BTR snapshot/typed reader at `806a239` as the development
baseline and now authorizes the [holistic reporting plan](PREPARED_PRESENTATION_ROLLOUT_PLAN.md):
complete reporting contracts across existing read-only MTA consumers, one coherent
reporting implementation, one frontend integration batch, then module inspection
and attributable fixes. This supersedes the BPR-only and four-screen proposals.
Included: BPR, DBM, RRR, BTR/Buffer Trends, Guided/Research and existing Planning
reads, related histories and supported exports. Use available retained producers;
record exact missing inputs instead of dropping contracts or inventing data.

Phase1 complete: the portfolio matrix in the existing plan covers every included
implemented endpoint/tab, field/type contract, source grain, live semantics and
serving choice; retained receipt counts distinguish wiring defects from absent
BPRMaster/GIT-master dependencies. Frontend request owners/workloads are mapped.
Phase2 complete: froze affected before-results, corrected selective history/Research
and ancillary wiring, and removed evidenced repeated broad scans/joins using
existing typed inputs. No new table/preparation is currently justified. A bounded
Guided history EXPLAIN identifies the BPR history sequential scan as 30.8s of a
31.8s query (8.48m retained rows; nine-day request). The one run/image/date covering
index and its normal migration preserve source rows, scopes and aggregates.
Required
proof is complete affected output equivalence (or attributable prior unavailable
path plus independent source-contract proof), scoped/range cases and focused tests.
Guided index correction proved: migration0018 applied through the existing atomic
fixture metadata-guard command; no pending migrations/model drift, index valid,
875732992 added bytes, fixture binding/freeze unchanged. One post-change plan uses
an index-only BPR scan, zero heap fetches,176.7ms per worker versus30826.3ms before;
complete query14277.0ms, with residual sorting/joins (not a UI latency acceptance).
Twelve complete retained-data Research/historical/Guided/Excess comparisons pass,
including broad/restricted scopes and nine-/three-day windows; PostgreSQL
VALUES differentials also pass. No further history optimization is opened.
Seven full-population Guided lookup comparisons pass, every field/occurrence/order;
9871 current-date Excess rows match the old full-history reader;1030 populated
custom Expedite rows match the canonical query contract over retained inputs.
Phase3 complete: one frontend integration batch, limited to evidenced duplicate
Guided/Buffer Trends work and independent Research/Planning count-grid sequencing.
Required exit: preserved request bodies/error behavior, focused frontend checks/build,
then one coherent deployment and bounded module API/browser inspection.
TypeScript, four request-pair tests and production backend/frontend builds pass.
Phase4 complete for the bounded implementation/inspection batch: changed3005
backend/frontend deployed;23 expected authenticated/security gateway statuses
plus two Planning graph200 responses and full bodies retained. Admission and
selected BTR generation are unchanged;21 protected container identities remain
unchanged. BPR50/97097, RRR5000/8063, DBM5000/11158, BTR5000/97299,
Research5000/97097 with selected history, Guided trend/Chronic charts, Buffer
Trends30-day chart and Planning Excess5000/9871 loaded in the browser. This is
bounded module inspection, not exhaustive interaction or matched latency acceptance.
Desktop BPR visibility was additionally verified at1280x720; the default narrow
browser viewport does not make this inherited desktop layout usable.
Residuals: broad Guided responses remain15–34s in single observations; Research
calendar opens the system month rather than the publication month. No further
history optimization, workflow, daily-ingestion integration or whole-F3 acceptance
is implied. Operational details/limits: [batch handoff](PREPARED_PRESENTATION_HANDOFF.md).
Planning overview/GIT remain unavailable:2567 positive-GIT rows and no retained
GoodsInTransitMaster; BPRMaster is also absent for dependent Expedite consumers.
Evidence: `D:/freshvcf-build/evidence/prepared-portfolio-20261004-001`.
The authorized batch is delivered with the above residuals. Further source,
latency or calendar corrections must use this same tracker and exact contracts;
no adjacent migration/workflow phase is started. MIGRATION.md is the only tracker.
Required exit: available included paths implemented and connected on3005, complete
affected value proofs, bounded module UI inspection, committed/pushed delivery,
rollback and explicit coverage/dependencies. The accepted BTR baseline is retained.
Real daily ingestion/engine replay/scheduler/automatic activation, new workflow
porting, MTO and3004 cutover remain outside this authorization. Broader whole-page
acceptance remains paused; this entry resumes only the described presentation batch.

### BTR typed reader — delivered and verified

Human-authorized follow-up to the delivered snapshot trial: remove SQL JSON
packaging and per-row decoding from the prepared grid reader only. The selected
April7 generation, data, frontend, permissions, two-pass paging and response
semantics remain fixed. Counts/exports, engines, schema/resources and other
services are excluded. This supersedes the trial stop only for this correction.
Complete: frozen both-branch5000 and restricted seven-day20 responses match every
row/field after the change. Seven affected tests, Django check and backend build
pass. The one On-Hand5000 EXPLAIN took773.097ms, with no final wide sort.
Backend-only deployment preserves frontend container/image, generation and
admission `5c90ae58…`; rollback restores `8b218cd3cc5a…` with the same version2
snapshot. Final browser-triggered On-Hand/page1/Show All/90-day observation:
complete backend HTTP200 response, `displayPrepared=true`,5000 tech/0 eco rows,
17564034 bytes; response captured5.467s after click and rendered grid observed
by7.815s, followed by responsive scrolling. These include tool/capture overhead;
they are not a controlled speedup or p95 claim. The earlier5.132s/6.967s grid-only
observations remain qualified, not substituted for this complete proof.
The instrumentation gap is closed: the original packet observer lost large
response fragments. A temporary64MiB capture ring within the unchanged4GiB
container limit reconstructed the chunked response. Small readiness responses
validated the observer first. Failed capture retries remain evidence, not
benchmark samples. No diagnostic process, grant or service remains running.
Implementation checkpoint `91562a4` is pushed. The bounded correction is complete;
stop here without further optimization, benchmark expansion or adjacent work.
Evidence: `D:/freshvcf-build/evidence/btr-typed-reader-20261004-001`.

### Latest direction: BTR ready snapshot trial — delivered for human review

The user authorized the fresh
[BTR ready snapshot trial](BTR_READY_SNAPSHOT_TRIAL_PLAN.md). It supersedes earlier
BTR plan/addendum execution instructions for this intervention. The prior deployed
reporting/frontend work was preserved in a checkpoint, its status reconciled from
retained evidence, and `codex/btr-ready-snapshot-trial` created for this implementation.
The new plan is a scope contract, not a second status tracker.

Delivered objective: complete typed BTR presentation rows prepared ONCE from the
existing April7 heavy fixture, connected to the existing API/frontend for direct reads.
Live permissions, filters, paging and exact display semantics remain required.
Full daily ingestion/calculation/scheduling/automatic activation are DEFERRED;
the builder simulates only the retained day's presentation preparation. No engine
replay, new facts/date, database copies, integer keys or renewed benchmark campaign.
The bounded implementation/verification/deployment exit is complete. The trial
remains on3005 for human review; no speedup or whole-application acceptance is
claimed. Stop here. Daily refresh and any further optimization need a new direction.

Preserved reporting/frontend implementation commit: `97b9b07655ec9cba88c787a44f8beae1097485e3`.
Plan/tracker checkpoint: `d9c600e`. Active branch: `codex/btr-ready-snapshot-trial`,
created from that commit with a clean worktree. No prior code, dataset or evidence
was reset/deleted. This branch carries the snapshot implementation and handoff;
proof is limited to the new plan. Prior default grid source uniqueness
qualification and accepted invalid-filter guards were reused without weakening.

Snapshot implementation is on the trial branch: BtrPresentationRow and migration
0016 define typed display/filter cells, source ordinals and cumulative daily
summaries, reusing the existing generation immutability guards. The bounded builder
and prepared reader are implemented. Seven focused display/summary tests pass.
PostgreSQL Django check, migration drift/plan and actual migrations0016/0017 pass in
the existing fixture database; admission and source guards are unchanged. The single
heavy build is READY and selected: `e5bdac30-bbd9-45d8-a93d-84a645fad73c`,
194598 rows (97299 per branch),1213.73 seconds. First/later full5000-row comparisons
pass for both branches. The first request took67.92s: scope discovery scanned the
wide new table. Migration0017 adds two narrow covering scope indexes; serial VACUUM
completed after default parallel maintenance hit the existing64MiB shared-memory
cap. EXPLAIN now shows index-only scope scans. No data rebuild or resource increase.
Final added storage is461586432 bytes (440.2MiB). All16 focused proof observations
pass: complete first/later5000 rows per branch, shorter range5000, restricted/empty,
filters and retained errors, counts and100-row bounded export. Immutable-row and
truncate guards pass. Prepared reads use only the new typed presentation relation;
count/raw/export retain the pinned version1 path. Existing JS mapper equivalence
and unchanged frontend build/tests were reused. Seven affected local tests pass.

Current backend image: `8b218cd3cc5adfb94b6b70772d622f0eadf0756ba5db3041916bbd8e25fe71b2`.
Frontend stays `f88d22416ab5b5b50a30479c1684449eb020dd29d8feb1bdd7399c2d02df0e91`.
Admission: `5c90ae58f6478f7b1805f534f95fbe0de241a5280c4422ec70f28467221bf3e7`.
Only the authorized preview pair was recreated. Protected containers/allocations,
source/run identity, grants and F1/F2 are unchanged. Legacy3002/5153 were listening
and needed no relaunch. Broad/restricted gateway reads pass; forged scope cannot
expand access and the normal preview actor retains403.

All three UI views visibly show5000 rows per branch,97299 counts and7-Apr-2026.
One observation each,90-day/broad/1280x720: Pipeline14.53s to observed usable state.
On-Hand/Both exact timings remain UNPROVED after browser-tool wait failures; later
observations confirm completed grids without repeating the actions. Retained before
screenshots lack precise timings/request counts, so no speedup or p95 claim is made.
Observed API request counts were4/2/1 (one grid each), with16.65MB/16.65MB/33.31MB grid
bodies and proxy temporary-file buffering. Visible delay remains; no further
optimization/benchmark tranche was opened. This is dataset/presentation readiness,
not latency acceptance or general daily orchestration.

Evidence: `D:/freshvcf-build/evidence/btr-ready-snapshot-20261004-001` (`proof-result.json`,
`deploy-verified.json`, `gateway-smoke/result.json`, `browser-observations.json`).
[Operational handoff](BTR_REPORTING_HANDOFF.md#current-ready-snapshot-trial--4-october-2026)
contains the repeatable builder, migrations, selected images and exact rollback.
The source snapshot is unchanged; rollback selects the preserved prior image and
generation without deleting data or reversing migrations. Delivery branch:
`codex/btr-ready-snapshot-trial`; implementation and handoff form one coherent
trial checkpoint. Remain stopped for human review.
The goal service reported no active goal; a matching goal was created without a budget.

Historical override before this snapshot trial: STOP benchmark-copy/recovery/repopulation and copy-readback
work. Preserve partial artifacts without deletion. Advance the same BTR task using
existing legacy SQL and existing Fresh PostgreSQL databases, with authorized
temporary reversible resource matching on BOTH (including serving PostgreSQL),
then restore original settings. This supersedes copy prerequisites and the earlier
fixed-serving-allocation restriction for the benchmark window only. No data reset,
reload, replay or infrastructure expansion. Future replication or replacement
infrastructure decisions require prior explicit human approval. Immediate exit:
verify existing legacy availability and deliver comparable heavy-data BTR timings,
reusing retained identities/correctness proof without full table rescanning.

### Preserved BTR reporting/frontend checkpoint — deployed trial, performance unproved

HISTORICAL INSTRUCTION (superseded by the ready-snapshot trial): frontend implementation was the active
intervention. The c4 runner stopped at completed pair22 and temporary limits were
restored, as evidenced below. Remaining benchmark/cold/load campaigns are DEFERRED
and no longer prerequisites. Partial performance evidence is not acceptance.
Complete the frontend addendum, focused verification and deployment to3005 with
rollback. This supersedes the older benchmark-first sequencing.

Controller frontend assessment (4 October): the existing BTR plan now contains an
[addendum](BTR_DAILY_REPORTING_PLAN.md#addendum-remove-btr-frontend-work-from-the-report-journey-4-october-2026)
covering full-row conversion/Availability calculation, grid remounts and repeated
configuration/layout work. This records the requested inspection and proposed
bounded intervention. The retained backend-only benchmark is the before evidence;
no whole-journey performance acceptance is claimed.

The human explicitly authorizes the [BTR daily reporting slice](BTR_DAILY_REPORTING_PLAN.md)
following the5d7ef83 benchmark handoff. Implement/test additive typed BTR reporting
tables and a daily publication-bound builder using EXISTING textual product/location
keys; integer dimension keys are excluded and deferred for later review. Cover both
branches, exact grid/count/export contracts, live scopes, atomic generation selection,
daily retry/rollback and full-heavy-dataset performance against legacy and accepted
Fresh. Use existing databases/services only; no copying programme. Bounded3005
trial/migrations and reversible resource matching are authorized. Commit/push one
proved result or restore the accepted reader and report the exact failed gate, then
stop. Prior query-only tranche is dispositioned below; broader Stage2–5 stays paused.

Correctness/lifecycle gate passed for the bounded trial: heavy fixture grids/counts,
first/later and restricted/empty/filter/horizon cases, both restricted5082-row exports,
118 normal read comparisons (including14 retained error responses), normal exports,
and30 adversarial tie cases through the accepted-reader fallback. Private-build
visibility, failed-build rollback/retry/idempotency, immutable PostgreSQL guards,
exact-generation admission and accepted-selection rollback passed. No engine work.

Migrations0013–0015 are applied in existing fixture and normal databases. Fixture
metadata migration guards were restored atomically; admission/source freeze stayed
unchanged. Full April7 generation3242710a-7478-4668-b9ed-b7af543e4f84 has389196
references (97299 per branch/grid-or-export), built in74.5s, adding110MiB. Normal
generationbb0b0859-431d-426b-a71b-9629692c8357 has4960 references.

3005 now runs the correctness-verified **UNACCEPTED TRIAL**, using explicit generation
selection and non-overlapping MTA restart. Startup and browser request logs show
the reporting reader. Both browser branches render April7 data; user reports little
visible speedup. Preliminary offline12.0→1.9s counts and16.0→9.2s grids are diagnostic,
not acceptance. The superseding active exit is the finite frontend proof below.
Human explicitly permits this correct opt-in trial to remain for inspection if only
performance is unproved; no whole-page or performance acceptance is implied.

First3GiB matched resource window failed legacy SQL pool memory before valid samples;
all resource settings restored, failed bodies retained. A4GiB common database window
uses SQL2560MiB buffer cap plus1536MiB non-buffer headroom, within observed host headroom.
That window's30 measured c1 paired grid/count journeys passed complete response
comparison: legacy median14.04s/p9521.30s versus reporting Fresh10.45s/19.95s;
throughput0.0647 versus0.0874 journeys/s. These are native API observations only,
with shared-host variability retained. The c4 series stopped at18 measured batches;
accepted Fresh
at the same4GiB budget remains unproved and is explicitly deferred under the
human's benchmark scope limit. Do not launch another accepted-Fresh matrix.
Evidence: `D:/freshvcf-build/evidence/btr-reporting-20261004-001`.

Frontend implementation is active under the superseding direct human instruction.
The benchmark runner stopped after pair22:18 measured c4 batches/72 journeys per
stack, all responses valid. Resource helper reported RESTORED with no errors;
actual PostgreSQL1GiB/1CPU and SQL original memory settings were independently
checked. Full c4 protocol was truncated by human direction, not passed. Cold,
three-burst, extra baseline and attribution campaigns are DEFERRED, not prerequisites.

The active exit is the narrow BTR frontend correction: maintain mounted same-view
grids under a truthful overlay, reject stale responses, stabilize column/layout
work, reuse actor/publication-bound config and supply display-ready values through
an explicit BTR-only opt-in response. Default raw APIs/exports retain their contract.
Availability and conversion move to the serving path with focused equivalence to
the existing JS mapper; request-specific preparation is not claimed as eliminated
system-wide. No new schema/cache/framework or benchmark campaign.

Required proof: focused affected tests/build, one representative before/after
On-Hand/Pipeline/Both browser capture at existing5000-row size, affected
paging/filter/layout/error/race/export smoke checks, safe existing3005 deployment
and rollback handoff, commit/push. Reuse prior backend correctness/migration proofs.
No whole-journey performance acceptance is claimed from partial native API timings.

Preserved implementation checkpoint: the reporting layer and BTR display opt-in
are deployed on3005. Seven focused frontend tests, TypeScript check and production
build pass (`frontend-tests-final.log`, `frontend-typecheck.log`,
`display-build-003.log`); five presenter/route tests and complete5000-row comparisons
per branch at90/7 days pass. The first fixture harness failure was Windows UTF-8
decoding; its correction did not modify source data. Impeccable reports no findings.

`display-deploy-result.json` proves identical admission
6da166e120fce96e567a7007caed410943864071004f4a6b5b302218b652a40b and only MTA/frontend
replacement. Current MTA image a7c58a5097357be81b44a710fdc6c9588b50a810facc99029e1365887a8c91f2;
frontend f88d22416ab5b5b50a30479c1684449eb020dd29d8feb1bdd7399c2d02df0e91.
Exact previous image pair is retained in `compose.display-rollback.json`.

Authenticated On-Hand/Pipeline/Both display5000 rows and97299 counts; vertical and
horizontal split render. Page2 changes rows, Depot filter resets page1/count86243,
local SKU filter/clear and Save/Reset Layout pass. CSV completed HTTP200:86243 rows,
108 columns,21112927 downloaded bytes, SHA256
867fe5f5503721ffb5ce03080efdd95047af74be0b8dcecf37eeb9f2b30c8513
(`display-csv-receipt.json`). This is bounded export smoke, not a new value-parity
suite. Prepared gateway reads preserve broad/restricted scope, ignore forged grants,
and deny the normal-preview actor (`display-gateway-smoke/result.json`). Legacy
3002/5153 remained listening. Race/error behavior is covered by focused tests.

Before/after screenshots are retained for each view. Exact click-to-usable timings
and request-count attribution were not captured; no browser speed improvement or
whole-page acceptance is claimed. This old intervention is checkpointed, superseded
by the new ready-snapshot contract above; do not reopen its deferred campaigns.

### Prior BTR query/access-path tranche — consolidated blocker at5d7ef83

That bounded intervention stopped at its authorized consolidated-blocker exit. No
safe query/index improvement was established. Accepted source7b40ba6 and MTA image
761719e96c0f95ccdb5f0ad79f7e96125b172ab79fafac72e3a3790615bc952a remained serving
at that checkpoint; the reporting trial above is the current serving status.
Performance parity and broader Stage2 acceptance are **not achieved**.

The latest human override was followed: copy/recovery/full-copy verification was
stopped, only the owned scan cancelled, and both owned copy containers stopped.
Partial data and evidence remain inert; no recovery or deletion occurred. Existing
legacy SQL and existing Fresh PostgreSQL supplied the actual comparison. Future
replication/replacement infrastructure requires prior explicit human approval.

The existing legacy launch issue was resolved;3002/5153 became available and both
native APIs returned200 from the same HTTP client in the existing gateway. The
benchmark temporarily enforced3GiB/2CPU per database and4GiB/2CPU per application.
SQL's own resource view reported cpu_rate200 and3072MiB throughout the measured
boundary snapshots. No active SQL request was observed at those boundaries.
Shared host load, Windows-versus-Linux memory accounting, storage and cache
conditions are retained qualifications; no disk cache was flushed.

Five warmups followed by30 alternating measured paired grid/count journeys per
engine completed at concurrency1, using both branches/all90days/page1/5000 and
the same broad scope. Request timing includes full response transfer; compression
and evidence processing occur afterward. Full responses were retained and checked.

| Existing reader | Median paired journey | p95 | Journeys/second | Errors |
|---|---:|---:|---:|---:|
| Canonical legacy |12.728s|19.228s|0.07072|0/30|
| Fresh accepted reader |13.976s|22.020s|0.06788|0/30|

Fresh is9.81% slower at median,14.52% slower at p95 and4.01% lower in throughput.
This measured scope fails the no-worse performance gate. It is a baseline result,
not a query optimization or a full API/browser performance certification.
All120 measured responses passed their full contracts: Fresh strictly; legacy grid
Category alias order only under the exact human-approved April7 multiset exception,
including duplicate multiplicity. Original strings remain retained; types, other
values and row positions are strict. Counts remain97299 in both branches.

The first concurrency4 warmup was interrupted by a resource-observer prelogin
timeout. SQL Server logged insufficient memory in its default pool at06:51:11;
its3GiB job ceiling was reached. Response evidence was not saved before that
observer failure, so concurrency4 is UNPROVED. The recorder is corrected to save
responses first; the failed attempt is not reclassified as a passing measurement.
SQL's configured max-server-memory remained its original unrestricted setting;
future c4 testing must account for internal buffer/non-buffer headroom within the
same total ceiling. No speculative capacity increase or infrastructure replacement
was performed. Application-cold/browser performance remains unproved as well.

Bounded query experiments remain rejected:
- Key-prefix paging matched eight complete heavy responses and104 strict normal
  cases (14 retained declared flaws), but changed values/tied selection in10/30
  actual-reader adversarial cases, including D90=11 becoming10. A semijoin variant
  also failed ordering. Neither can be deployed.
- Normalized materialization regressed counts from approximately3.52/4.96s to
  9.48/10.17s and timed out the grid at55s.
- Duplicate-multiplicity count aggregation preserved97299 counts but regressed
  approximately1.12/1.88s to3.42/3.44s.
These diagnostics do not certify all possible query designs; they establish that
none of the bounded candidates is a correct demonstrated improvement.

Restoration passed: exact accepted image/runtime, admission, selected catalogue,
protected state, original PostgreSQL1GiB/1CPU (2GiB memory+swap), and grant digest
92579e9b054da03d9e170b91ca3037d35c6d7a8ae757179a9a28a6b7658d264a.
SQL/API temporary job limits were cleared with no restoration errors, and SQL
requests drained. No calculation, replay, serving dataset write, grant/index/schema
change, new image or reporting projection was deployed. Prior accepted browser,
export/security/overlap/restart/rollback proofs remain applicable to the unchanged
image; no new candidate acceptance is claimed. Fourteen focused restored-reader
checks and six scoped comparator tests pass; the unrelated prior suite failures
remain as recorded below.

Consolidated evidence:
`D:/freshvcf-build/evidence/3005-btr-performance-20261004-001/matched-consolidated-result.json`.
It binds `existing-matched-001/observations.jsonl`, `summary-c1.json`, full bodies
and comparisons, `existing-budget-001/budget-result.json`, SQL memory evidence,
`matched-final-runtime.json`, grants and rejected candidate receipts. Earlier
`validation.json` is historical and its copy prerequisites are superseded.

Next decision: review the prepared BTR daily reporting-layer assessment as a
separately authorized storage/read-model intervention. Reuse existing databases,
full response contracts, normal-publication proof and the measured baseline.
Do not implement it, resume copy work, or open broader Stage2–5 under this exit.
Operational details: [dataset handoff](STAGE2_DATASET_HANDOFF.md).

### Report contention correction — PASS for bounded overlap; stopped for review

4 October 2026: the human in the successor control chat authorizes the bounded
[report contention correction](REPORT_CONTENTION_CORRECTION_PLAN.md) following
accepted login/profile checkpoint `fe8ad13`. Active exit: eliminate the retained
60-second 504s for the four existing grid/count pairs plus ChronicUnavailabilityLoc
under the same full fixture and resource limits, preserving complete responses,
scopes and login/profile independence. Diagnose query/request/queue work, apply
only measured non-semantic corrections, verify repeated overlap and browser
behavior, deploy on isolated3005, commit/push and stop for review. This narrowly
supersedes the report-tuning pause below; general Stage2 and Stages3–5 stay paused.
The contract fixes the permitted boundary, required proof and blocker conditions;
it is not a second status tracker.

Execution starts from the unchanged `fe8ad13` runtime. Capture individual/pair
and eight-/nine-request timing, isolated native profiling, DB activity and drain
before choosing a correction. Successful retained responses remain the oracle;
timeouts are failures, never expected response bodies. No engine, import,
permission, capacity or broader page work is opened.

The bounded baseline reproduced six 60-second failures in the nine-request burst;
the eight-request burst succeeded (maximum33.91s). Native attribution identified
Chronic Location's repeated lookup scans as dominant:55.14s initially, and105.31s
in the retained full-bag differential run. Its insertion-ordered lookup correction
reduces that reconstruction to0.56s, preserving all3340 joined rows and five full
response cases (broad, restricted, SKU/location filters, empty). The broad response
matches the retained successful native response byte-for-byte; the candidate full
request took6.24s. The normal June17 response also matches exactly (empty terminal
population); adversarial tests cover duplicate/NULL/missing joins and order.

Only the MTA image is changed. Dataset/policy/catalogue hashes, admission, resource
limits, worker count, gateway/frontend, grants and accepted state remain fixed.
No SQL/index/schema or calculation change is included. Evidence:
`D:/freshvcf-build/evidence/3005-report-contention-20261004-001`.
The original drain monitor included its own CPU overhead; its nine-burst drain
timeout is retained as an observer failure. A corrected Gunicorn-only CPU plus DB
activity check confirmed quiescence before candidate proof/deployment. Do not use
the original aggregate-CPU drain times as precise worker completion times.

Final bounded acceptance: three consecutive nine-request bursts returned all27
complete expected responses, maximum50.565/53.155/54.376s under the unchanged60s
gateway limit, without restart/cache clearing between bursts. The eight-request
burst also passed (45.424s). All six measured candidate phases match the retained
successful native baseline in complete JSON types, values, fields and ordering.
Fresh login overlapped each burst (0.865/1.022/1.228s);94 profile reads succeeded,
maximum2.046s. Worker/DB quiescence was observed between bursts. Sampled candidate
MTA/gateway maxima were502.98/125.24MiB with no OOM, within unchanged4GiB/1GiB.
The finite samples are not formal matched-legacy median/p95 acceptance.

Browser RRR/BPR/BTR/DBM rendered5000/50/5000/5000 rows from8063/97097/97299/11158
totals; local SKU filters worked and both BTR inventory branches rendered.
Address navigation away from pending BTR reached Profile Details; work drained
and returning BTR loaded successfully. The SPA profile-link attempt during BTR
loading stayed on BTR; this observation remains, and immediate SQL cancellation
is not claimed. Restricted/forged/unauthenticated/normal-actor/action-denial proofs
pass, and serving grants retain SHA92579e9b054da03d9e170b91ca3037d35c6d7a8ae757179a9a28a6b7658d264a.
23 focused tests pass. Normal Chronic's terminal empty response is byte-identical;
populated/duplicate coverage is supplied by fixture and adversarial proofs.
There is no affected backend Chronic download route.

Unchanged BTR paired reads varied19.16s before to44.89–46.87s afterward. Image
source comparison proves only insights.py changed; the SQL text and response
hashes match. Follow-up observed37096 PostgreSQL block reads,10.58MB temporary
files,26.32 CPU-seconds and9.24 throttle-seconds at the fixed1CPU/1GiB allocation,
with no lock waits or other active database. Exact EXPLAIN/BUFFERS plans are
retained. The earlier baseline lacks matching PG counters, so a specific host/
cache cause is unproven. This remaining SQL/I/O performance limitation is explicit;
the bounded timeout fix does not certify broader low-latency acceptance.

MTA image761719e96c0f95ccdb5f0ad79f7e96125b172ab79fafac72e3a3790615bc952a
is deployed. Restart, exact rollback to66ddf0722c4f87cbbfa9291067b991f85d51acfbd0cb604661591788463263c2,
candidate reapplication and coordinated normal-restoration input checks pass.
Gateway/frontend, fixture admission and accepted/protected state remain unchanged.
Consolidated receipt:`3005-report-contention-20261004-001/validation.json` under
the evidence root above. Operational commands are in the dataset handoff.
The delivery commit is identified by the external `delivery.json` receipt, avoiding
a self-referential commit hash. General Stage2 performance and Stages3–5 remain open.

### Login/profile catalogue delivery — PASS; stopped for review

4 October 2026: direct human authorization in command-centre turn
`01a10375-b2b4-7993-aad5-35e850573d9d` opens only the dependency correction in
[the implementation contract](LOGIN_REPORT_WORKER_DECOUPLING_PLAN.md), from
`612a629`. Consume the same validated catalogue locally in the configured 3005
user-service; preserve live identity grants, scope enforcement, response values,
fixture/publication selection, resource limits and protected services. No report
tuning, F1/F2 changes or general Stage 2–5 work. Required exit: exact catalogue
and identity comparisons, fail-closed selection/startup and isolated revocation
proof, real login/profile under the retained report contention, coordinated
restoration, committed/pushed deployed result or precise consolidated blocker.
The preceding stabilization stop remains in force outside this boundary.

Deployed and verified on 4 October 2026. The configured user-service reads the
same checksum-bound catalogue locally, with the existing fixture policy or normal
publication/hierarchy binding. Its MTA permission branch makes no catalogue HTTP
request. Missing, corrupt, mixed or wrong selection fails startup/returns 503;
local assembly failures cannot become an empty-permission success. Effective
grants remain live identity-database queries; other deployments retain HTTP mode.

The profile Loading defect was a stale module-level redirect flag surviving SPA
login. A new protected verification clears that transition flag, always fetches
profile, and sends missing/failed profile responses through the existing login
redirect. Successful local login also resets the flag. No permission or route
rule was changed.

- 26 focused backend tests pass, including actual login/profile assembly without
  MTA HTTP and grant addition/revocation in an isolated identity test database.
  Five frontend regression tests pass; both production images built successfully.
- Complete normal and fixture catalogue payloads equal the unchanged native MTA
  view, including ordering and types. Network-disabled ASGI startup accepts both
  valid configurations and rejects missing/wrong selections. Broad/restricted
  login and profile preserve all response content; only the pre-existing
  `list(set(...))` URL/feature arrays are compared as unordered sets. No values
  are excluded; catalogue and hierarchy array order is compared exactly.
- Unloaded login/profile: broad 0.931/0.437s; restricted 1.161/0.403s. During eight
  full grid/count requests plus Chronic, fresh login returned 200 in 2.495s with
  all nine report requests still outstanding. All 72 profile requests returned
  200; maximum 2.427s, 70 completed while reports were pending. Earlier 30s login
  timeout and 51.47s profile evidence remain retained. These are bounded diagnostic
  observations, not matched legacy report-performance acceptance.
- Real browser login during contention returned 200, Profile Details rendered,
  all four populated pages were reached, and SPA navigation back to profile
  completed. Restricted four-page reads, forged scopes, unauthenticated and
  normal-versus-fixture denials, and disabled Apply/Sleep all pass.
- Sampled gateway/MTA memory peaks: 119.95/719.02 MiB; no new OOM events. CPU over
  the measured phase, including the probes/browser activity: 45.049/157.149s.
  Existing limits/timeouts/restart policies are unchanged. MTA was not restarted;
  image, admission, full fixture, accepted F1/F2 and serving grants are unchanged.

Evidence: `D:/freshvcf-build/evidence/3005-login-decoupling-20261004-001/validation.json`,
with retained bodies, browser screenshots, resource samples and test logs. Initial
test setup/coverage-run failures remain recorded alongside the corrected passes.
Gateway image `sha256:9de37195b08a33a6916fa9c10e8ecd0dc5b4d847bd8f0c96c1892caa61c1188b`;
frontend `sha256:c7f4fc70f70df8a3a59b557a6d815fc0f473d856c799877c9515cc0f01facf4e`.
Recreated startup/readiness and `tools/stage2_identity_catalogue.py check` passed.
The handoff records coordinated normal restoration and exact-image rollback;
normal restoration was not executed, so the April 7 fixture remains available.

Residual limitation: the retained contention burst produced 60s 504s for BPR
grid, BTR grid, DBM grid/count and Chronic. The following aborted-read diagnostic
also received a BTR 504. The login/profile dependency exit is complete; report
latency, general Stage 2–5 and other workflows remain paused, not accepted.

### Earlier 3005 stabilization checkpoint — memory fixed, identity blocker superseded above

4 October2026: human authorization in review chat
`01a100e2-7943-7102-9760-62d9e492ecd9`, turn
`01a1033b-54a0-7692-9984-d480048bd840`, supersedes the pending serving-approval
blocker for the isolated3005 gateway/user-service, MTA and frontend only. The
gateway exited137/OOMKilled at1GiB on3 October19:16:41UTC; frontend liveness200
did not establish login/API availability. Preserve this incident and diagnose
actual forwarding/request memory lifetime before choosing the smallest correction.
Active exit: reliable real login/profile during bounded repeated and overlapping
RRR/BPR/BTR/DBM navigation, full retained responses/scopes and resource/timing
proof, verified deployment, rollback identities, one committed/pushed handoff.
Keep limits/restart policy fixed; no reload, engine/F1/F2/auth/permission change,
other-page implementation or broader Stage2/Stages3–5 continuation. Earlier
four-page availability is historical, not a claim that the failed gateway is healthy.

Result: the bounded gateway correction and RRR/DBM frontend candidate are deployed.
Stop for command-centre review; do not resume general Stage2 or Stages3–5. Evidence
root: `D:/freshvcf-build/evidence/3005-stabilization-20261004-001`;
`stabilization-validation.json` consolidates resources, timings, protected state
and exact running identities. This is **not full stabilization acceptance**.

- Original BTR33.7MB forwarding raised an isolated gateway process from128MiB
  to377MiB peak through body/text/JSON/serialization allocations. Actual old
  gateway cgroup peak reached695MiB during two full four-page rounds.
- Large MTA grid/export and observed Chronic reads now use an async byte iterator;
  no duplicate report object graph, explicit close on EOF/error/disconnect,
  bounded connect/read waits, and count-request cleanup within the existing
  public60-second limit. Commands, authentication, scope injection and MTO remain
  unchanged. The measured final gateway peak is134MiB across stress samples;
  no gateway/MTA OOM. Largest sampled MTA usage is742MiB under the unchanged4GiB.
-16 focused gateway tests pass, including ASGI first-chunk/disconnect, timeout,
  downloads and existing identity tests. All16 complete grid/count responses at
  full page sizes match the original gateway after UTF-8 JSON decoding. No new
  RRR tie-break is introduced. The complete1,524,093-byte RRR CSV and headers
  match the native response. Four restricted grids/counts, forged scope,
  Apply/Sleep403, normal-preview403 and unauthenticated denials pass.
- Real browser login and all four populated pages pass. Observed page times are
  RRR13.82s, BPR9.12s, BTR On Hand9.00s and DBM navigation4.52s. Navigation away
  during pending reads and return to populated RRR were exercised. `/profile`
  itself remained Loading despite observed API200; that UI is not certified.
- Full paired API medians (two diagnostic observations each), before→final:
  RRR7.31→10.36s, BPR7.47→11.78s, BTR both15.99→22.49s, DBM4.18→5.42s.
  There is **no demonstrated API latency improvement** or matched legacy parity.
  Eight supported overlapping grid/count requests returned200 within39.88s;
  adding Chronic produced60-second report504s in retained stress attempts.

Consolidated blocker: `ResponseUser.response()` and `ResponseProfile.response()`
call `ALL_PERMISSIONS.get_combined_permissions()`, which synchronously retrieves
MTA `GetAllPermmision` through the same two sync workers as large reports. The
final dependency probe's profile requests returned200 but took up to51.47s
(65-second observer, unchanged60-second gateway). Real login during that burst
exceeded the existing30-second probe timeout. Earlier10-second profile observer
failures are retained and are not misreported as public HTTP failures. Gateway
memory is healthy; report-worker contention still delays identity responses.
Correcting catalogue delivery/freshness or worker isolation changes the present
dependency boundary and is not inferred here. No permission snapshot/cache,
new source, extra workers, memory increase or timeout extension was introduced.

Current gateway image: `sha256:ccf8da228c02c7ebd25eb91c5dae52447fed13ae58f20fd17bf931ea768bee36`.
Current frontend: `sha256:89118af27cb171259f14d570f35cfcdc35e21ebcd20d2a784716c76ec60fe401`.
MTA remains `sha256:66ddf0722c4f87cbbfa9291067b991f85d51acfbd0cb604661591788463263c2`.
Readiness now distinguishes frontend-only `/healthz` from `/readyz` checks of
the identity database and admitted MTA; neither certifies whole-page behavior.
Protected services/publications match the retained checkpoint. Normal restoration
uses `tools/stage2_stabilization_restore.py` (check-only passed), preserving
window010 and checking the explicitly updated protected-service identities.
Gateway/frontend rollback commands and limitations are in the dataset handoff.

The existing four-page latency history below is retained context for this result.

Direct human follow-up authorizes inspecting contracts and data-fetch architecture
and reducing latency on the existing RRR/BPR/BTR/DBM fixture paths. Profile the
current full page-size requests, reuse earlier selective-read work, and correct
measured redundant work at the relational/request boundary. Preserve responses,
scope/filter semantics, duplicate bags/order, immutable dataset, admission and
the4GiB/two-worker/60-second limits. No engines/F1/F2/authentication/permission
changes, other-page work or dataset reload. Required proof: complete affected
response comparisons, focused regression checks, authenticated concurrent API
and browser timings, and preserved fixture/normal restoration. Retain window008
as the rollback checkpoint; record measured improvements and remaining limits.

Measured follow-up within this same item: the retained RRR and DBM frontend hooks
serialize count then grid on filter application (RRR browser12.76s versus concurrent
gateway6.7s). BPR and BTR already start both requests concurrently and remain unchanged.
Prepare only concurrent existing count/grid reads in the RRR and DBM hooks,
retaining endpoints, payloads, page sizes, error cleanup and UI configuration.
Prove concurrency and rejection handling with deferred-request tests. The
protected frontend service is not replaced by the MTA-only fixture window;
any frontend runtime replacement must respect the separate serving approval.

Backend checkpoint: window010 repeats the populated four-page browser/filter,
restricted-scope and denial proofs with the same frozen dataset. Fixture reads
now use bounded BPR SQL, pair-filtered DBM inputs, narrower BTR metadata/late daily
column fetching, inline RRR CTEs and a transaction-local measured count plan.
The index roster retains the prior seven and adds nine measured access paths;
raw keys and stored facts are unchanged. Full first-page response comparisons
pass; RRR preserves full row bags and declared sort-key groups, with physical
permutations inside undeclared exact ties (no invented tie-break).

Three concurrent gateway observations give median complete grid/count wall times
RRR6.70s, BPR7.83s, BTR16.75s and DBM4.21s. Existing-frontend browser observations
are12.76s,16.84s,16.76s and3.20s respectively. These are diagnostic observations,
not the required matched legacy performance protocol. BTR remains slow; minimum
latency and production-scale normal-run performance are not accepted. Evidence:
`latency-001/response-comparison.json` and `fixture-window-010` below the dataset
evidence root. Window009's unsuccessful timing trial restored normal serving;
window010 retains fixture serving and its exact normal restoration command.

Normalization finding: the original synthetic-run RRR serving SQL also used
`lower(rtrim(...))`; relational state was keyed by run/image/source ordinal,
without dedicated canonical SKU/location lookup columns. F1/F2 correctness proof
did not certify a scalable consumer lookup design. The present expression indexes
are an isolated compatibility correction, not a schema-wide canonical-key
migration or evidence that normal production access paths are now optimized.

Client candidate `freshvcf-preview-frontend:latency-20261003` built successfully;
four deferred-request Jest tests passed. Its RRR/DBM changes are now deployed in
the above stabilization frontend. The prior frontend rollback image is
`sha256:a37599db5558f52af99753ece785a0254aedc64a832906b3f99533d6983f366a`.
The final focused backend run passed16 of17 tests (one opt-in PostgreSQL case
skipped there and separately passed against PostgreSQL). A unit-route run inside
the serving fixture environment failed because its mocked actor was denied;
the clean local test environment passed. Preserve both receipts. The above
stabilization disposition supersedes the former pending deployment approval;
neither this checkpoint nor fixture availability closes Stage2.

### Four-page visible-data delivery — PASS; fixture serving on3005

The direct human instruction in this chat authorized closing only the current
3005 availability blocker. Window008 completed that bounded exit on3 October2026.
Full page implementation remains paused. This is visible dataset availability,
not whole-page, Stage2, F3, engine parity or matched performance acceptance.

Reused the sealed April7 VM dataset, existing typed consumer schema, mapping,
loader, fixture admission, page contracts and all unaffected proofs. No source
extraction, reload, engine/replay/F1/F2 mutation or permission change occurred.
The BTR execution plan showed repeated full scans/sorts of97k-row relations.
Seven exact normalized join-expression indexes were added only to the owned
fixture database; the fixture-only `enable_nestloop=off` override was removed.
SQL predicates, parameters, bags, values and ordering are unchanged. Full sampled
tech/eco responses and counts equal the retained slow result. The index tool
validates manifest/database, exact index definitions and frozen identity.

| Page | Browser population | Local SKU filter | Restricted API count |
|---|---|---|---|
| RRR |5000 of8063 |11 rows for21101151051000 |809 |
| BPR |50 of97097 |1 row for23102164028000 |5076 |
| BTR |5000 of97299; both inventory views |Retained21101050051000 rows |5082 in each branch |
| DBM |5000 of11158 |13 rows for21101149051000 |1036 |

Real broad-account browser login, navigation and filters passed. All four
restricted count/grid APIs returned200; forged scope did not expand any count.
Concurrent authenticated BTR requests at the actual5000-row page size returned
200: both grids35.965s and count42.903s, below the unchanged60-second gateway.
Peak MTA memory was2.20GiB with zero OOM events. Seven focused BTR tests passed;
Django check, migration drift check and migration
plan passed (no model migrations). Independent bounded review found no blockers.
No claim replaces the retained broader suite's two pre-existing Expedite failures.

403 attribution: normal `fresh.preview@vectorflow.local` is intentionally absent
from fixture policy and returns `fixture_actor_scope_denied`; dedicated broad/
restricted actors pass. The frontend's existing forbidden-page navbar can repeat
GetAllReports after a403, masking that cause. Window007 lacks actor identity, so
its human session cannot be retrospectively attributed. Window008 proves the
supported fixture accounts work, normal/unauthenticated access remains denied,
and Apply/Sleep remain disabled. No authentication/permission bypass was added.

Current service: isolated April7 fixture on3005, dedicated read/layout actors
are enabled. Use `stage2.broad@vectorflow.local` (or the restricted actor); retrieve
its existing password from the local fixture secret file identified in the
handoff. Ordinary preview accounts are not fixture accounts. Protected services,
accepted publication and existing grants passed the window's unchanged checks.
F1/F2 engines/state, other pages and Stages3–5 remain outside this delivery.

Current consolidated proof:
`D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002/visible-availability-validation.json`.
Window008 retains browser text/screenshots, scope/security and concurrent gateway
receipts, runtime resource evidence and `serving-handoff.json`. Windows001–007
and the former blocked consolidated receipt remain preserved. To restore normal
June17 and disable the fixture actors:
`D:/freshvcf-build/venv/Scripts/python.exe tools/stage2_fixture_window.py restore --attempt 008`.

### Bounded Stage 2 dataset preparation — consolidated consumer blocker

The human supplied VM-extracted backups at `E:/vflow_backup_dump` in the review
chat on 3 October 2026. Active work now verifies/freezes/restores the available
Importer/BPR/BTR originals in **new** owned resources and prepares their staging
and mapping independently. The human subsequently confirmed DBM copying complete;
its stable original was hash-pinned and restored separately after preserving an
interrupted capture. All four API sources share 7 April 2026 LastBatchRun dates.
Interface/IntermediateDB/Vendor/Distributor are conditional source dependencies,
not automatic readiness gates; any required missing input must name an actual
Stage 2 consumer. None may be borrowed from synthetic sources. Exit remains
dataset readiness or a consolidated evidenced blocker. Required proof includes
hashes, usable restores, source dates/identity/coverage, bounded capacity, typed
bulk readback and actual consumer mappings. No engine, accepted-state, permission,
serving or page changes under the initial scope. The existing app goal is active.

**Bounded authorization amendment (3 October 2026):** verified human instruction
in command-centre chat `01a100e2-7943-7102-9760-62d9e492ecd9`, turn
`01a100e3-6258-7bf1-a9d0-f191636ed24f`, authorizes its relayed grant: dedicated
local fixture actors through existing account/auth mechanisms, new actor-owned
MTA read/navigation and layout grants using the original 9-product/60-location
catalogue; preserve source IDs, NULL/empty semantics and existing accounts/grants.
No VM passwords/sessions or invented memberships. Catalogue collisions require
isolated fixture configuration/storage. Implement only explicit fixture admission
and representative real authenticated API reads/scope denial. If needed, switch
only MTA on3005 temporarily after recording image/config/database/publication and
exact restoration; restore June17/catalogue/actions-disabled on every exit and
prove protected resources unchanged. Preserve gateway/frontend/auth/MTO services.
Fixture accounts must have no normal-publication access and be disabled outside
the test window; credentials remain outside Git/logs. Keep4GiB/2CPU/two workers/180s/
restart=no. Engine changes/execution, F1/F2 mutation, business actions, page-by-page
work, performance campaigns and Stages3–5 remain excluded. Active exit remains
dataset readiness or a precise additional blocker; no new queue.

**Bounded preparation stopped at a consolidated blocker; dataset readiness is
withheld.** All303 source tables /91,645,123 rows are preserved. The73-table
Stage2 union /56,500,041 rows passed full staging readback;60 consumer images
/52,760,538 rows and six projections /965,475 rows passed full typed source/target
comparison. Manifest `afe42593ca2abdf5e2395433ac70834723f4eac1dfa5a2982192c7688906b836`
is sealed. Database `test_freshvcf_stage2_vm_20261003_002`, fixture run
`bfd75b4b-a9df-4a08-82d3-852e3324b623`, remains explicitly non-production.
A zero-insert retry passed;396 relations are immutable. Three fixture-owned
pair-history indexes preserve the same frozen identity.

Window004 proves native DBM counts11158 broad /1036 restricted, populated grids,
forged-scope non-expansion, a populated history drill-down, Apply/Sleep403 and
normal-preview-actor403. Research/historical-availability/BPR/remarks/Planning
Expedite remain explicitly503. Existing accounts/grants are unchanged. Both
fixture actors are disabled, real login denial is proved, and normal June17
image/configuration/admission plus all protected services are restored.

**Blocking contract:** existing `RRRDataCount` over this native population
returns gateway504 after60seconds (windows003 and004). RRR grid, BTR and
fulfillment checks following it were not executed; do not claim their acceptance.
Further RRR presentation-query diagnosis/correction is a separate authorized
boundary, not page implementation or an engine change. Other declared native
ancillary/history adapter gaps and39 static UI metadata differences remain in
the handoff. No timeout increase, API assertion waiver or performance campaign.

Earlier windows are retained:001 exposed the fixture DBM quadratic join;
subject-bag partitioning now uses the unchanged selector and passes exact
bag/NULL/missing/accepted/predicate equivalence.002 exposed pair-history scans;
owned indexes resolved that check (window003 history200 in4seconds). All four
windows restored normal service.37 focused tests pass; the broader19-test HTTP
suite retains exactly two pre-existing Expedite failures. No engine execution,
F1/F2 mutation, replay, frontend implementation or Stages3-5 work occurred.

Consolidated receipt: `D:/freshvcf-build/evidence/stage2-vm-dataset-20261003-002/dataset-validation.json`
(`BLOCKED_CONSUMER_READINESS`). Manifest, mappings, repeatable loaders and exact
operation/restoration steps are in [the operational handoff](STAGE2_DATASET_HANDOFF.md).
The requested stop-at-readiness-or-blocker boundary is reached; no adjacent work
is active. Page implementation remains paused.

The following describes the preserved, superseded first candidate:

On 3 October the human corrected source authority to `F:/VFlow_Source_Backup`
in review chat `01a0f7c6-1050-7741-b80a-a7f10ca0d04d`. No original populated
SQL backup set was found in the bounded preserved-source inventory/MTA archives;
its reconstruction runbook says databases were not copied. The local Demo
runbook explicitly identifies its 1,240-row population as synthetic reconstruction.
Matching database names did not establish original-data lineage.

Before the correction, eight checksum-verified local Demo backups were restored
to owned read-only `VFTEST_Fresh_S2_20261003_001_*` clones. 523 tables / 280,651
rows passed full typed staging readback in owned PostgreSQL database
`test_freshvcf_stage2_dataset_20261003_001`; 102 consumer images and six projection
families were copied and fully read back. The consumer transaction finished before
the stop took effect. All are preserved as quarantined evidence, **not dataset
readiness**. Fixture partition `f9db3dfc-efc3-488d-af2f-a88e8b2c68ee` is
`LEGACY_UI_FIXTURE/FIXTURE_BLOCKED`, with no engine success, parity receipt,
checkpoint, command or production manifest. No fixture admission/serving change
was implemented. All three loader entry points now fail before source/database
work pending reconciliation; no environment override is provided.

Additional observed limits of that rejected candidate: native `LOCAL_ALL`
hierarchy matches zero unchanged modern permission memberships; Suggestions,
SuggestionsLog and RationingHistory are empty; BTR BPR has one date; source
OrderIdentity is absent. Do not transfer these findings to the missing original
data. No engines, accepted F1/F2 rows, authentication permissions, serving services
or page implementation were changed. Scope ends at this consolidated blocker.

Handoff: [Stage 2 dataset handoff](STAGE2_DATASET_HANDOFF.md). Evidence:
`D:/freshvcf-build/evidence/stage2-shared-dataset-20261003-001/`, especially
`source-reconciliation.json`, `dataset-manifest.json`, `mapping.json` and
`staging-validation.json`. Resumption requires the original populated source set
and API/engine suffix reconciliation, or an explicit human change of source scope;
use separately owned replacement resources and retain this candidate.

| Boundary | Current assessment |
|---|---|
| F0 Foundation | Complete for the registered foundation scope. |
| F1 Current-day MTA | Complete for selected registered contracts; not universal customer/branch coverage. |
| F2 Temporal MTA | Complete for selected registered 12-day scope with declared Norm0 occurrence-text flaw: 360 strict passes and 12 narrowly qualified report contracts. Norm0 text is not parity. Day 12 peak 3.10 GiB; terminal relational/readback proof passed. No further F2 recovery queue. |
| F3 recovery Stage 1: connection/admission boundary | Accepted at pushed `52f2ff5` (implementation `26158a6`). Retain accepted inventory and admission proof. |
| F3 recovery Stage 2: connected reporting journeys | **Incomplete; paused at `2d0cfde`.** Implemented and verified portions below are not whole-page acceptance. |
| Stage 3: operational reports/logistics | Not opened under the Stage 2 authorization. Reassess after Stage 2. |
| Stage 4: workflows/master data | Not opened, except the completed bounded DBM action validation amendment. Reuse that proof later. |
| Stage 5: combined runtime/MTO/final acceptance | Not opened. Final application acceptance and any 3004 cutover remain outstanding. |

## Stage 2 page ledger

These are the remaining obligations, not parallel work queues. Guided was the active page at the stop. On an explicitly authorized continuation, finish or give an evidenced disposition for one whole page before independent next work. A recorded blocker permits independent progress; it does **not** make that page complete or remove its required exits. An untested feasible check is not an external blocker.

| Page / journey | Implemented or verified at checkpoint | Remaining acceptance / disposition |
|---|---|---|
| RRR | SQL/read/export proofs retained; layout save/reset/reload/restart and full saved-layout CSV proved. | Real leaf actor, residual controls and matched performance. Inherited screen has no wired history entry: retain exact source disposition. Partial, not accepted. |
| DBM current / daily history | June 17 current Suggestions = 0; positive Apply/Sleep, own-next-day effects and restoration proved in owned trials; Product/Location controls repaired and proved. | Downloaded XLSX, remaining positive controls/scopes, real actor coverage and matched performance. Reuse consumed trial receipts; never reset trials. Partial, not accepted. |
| BTR | Both branches, selective reads/CSV, authenticated gateway/restart, browser views/paging/Depo/horizon/history/layout save/reset and both toolbar files proved. Delayed tab-return restore passes. | Inherited fresh-reload hook fails; disposition required. Residual controls, leaf actor and matched performance remain. Partial, not accepted. |
| Buffer Trends | 134 exact graph responses and 30 declared failures; gateway/restart and type/horizon/summary/Depo/reset/reload controls proved. | Inherited doubled Total / stale Percentage behavior needs exact disposition; residual controls, leaf actor and matched performance remain. Partial, not accepted. |
| Planning categories | Overview proof retained; user explicitly verified exports working and directed deferral. Normal To Child grid rendered 7 dispatch rows, filter/selection and selected-run controls proved. | Custom NMS identity provenance/disposition; canonical child SQL and filtered-count wire proof; residual controls, leaf actor and matched performance. Empty request input does not prove request workflows. User-directed deferred, not accepted. |
| BPR | Read batch deployed at `88c434d`: filtering/count/grid/CSV/analytics/history/configuration; authenticated graph/filter/layout/paging proof retained. | Independent 52-case grid/count/analytics/export and CSV-cell comparisons; actual browser CSV receipt; leaf actor; matched performance; deferred drag/resize/split/multiselect/filter/historical/concurrency controls; inherited Reset Layout ordering disposition. Partial, not accepted. |
| Guided | Read batch deployed at `2d0cfde`; 578 independent consumer comparisons; approved 12-day/770-row history published; all 11 authenticated routes returned 200. Availability Trend rendered six location types; legend hide/restore proved. | Five-tab controls, horizons/ageing, chart/table/legends, Chronic grid/filter/layout/paging/downloads, DBM panels/link, Excess dual horizons; gateway value/wire comparisons; real leaf actor; persisted-layout/restart interactions; configured query-count and unaffected-route overhead diagnostic; matched API/browser performance. Inherited ageing/stale Excess horizon remains source-mapped, not waived. Partial, paused. |
| Research Insights | Existing native history/BPR evidence may be reused. Not opened in the Guided batch. | Whole-page selection→summary/calendar/ageing, graph/grid/date/horizon/filter/config/layout/export contract and proof, scope/restart/performance. Not accepted or covered by Guided. |

All required gaps remain in the Stage 2 denominator. Stage 2 closes only when required exits are proved or the human explicitly approves a narrow scope disposition. SQL/provider recovery makes formerly blocked comparisons feasible again; the old 18456/823 outage is not a continuing excuse to omit them.

## Serving checkpoint and approved inputs

The following identity is the recorded safe-stop state, not a perpetual health claim:

- Preview: `localhost:3005`; no 3004 cutover. Only MTA was recreated at the checkpoint.
- MTA image: `sha256:526ebe525ca7ea1b4c90e7fd475d3dc1eec6166a40161983477a117f7b302da8`.
- Container: `a7a583ea16a86197fe507013927db9df859b13574f25257b129b4fc5a922e9e8`.
- Selected run: `ac1612c8-0e49-4155-83c3-f59f41422293`; business date: `2026-06-17`.
- Output digest: `bd1c522f3df299d2fc3841aed7f66d48e4307e6967450b2d8a5463dc7867d33d`.
- Startup admission: `34a99fa5de6f70c2e7384283d083f6011558ac92c5927e627f4fd322d97044a7`.
- Normal current Suggestions = 0; normal actions disabled. Limit 4 GiB / 2 CPU, two workers, 180-second timeout, restart=no; MTA has no separate host port.
- Build/gateway/SQL comparison jobs ended and owned exclusive leases exited. Retain `test_freshvcf_guided_history_20261003_002`; no cleanup/reset is implied.

Approved supplements are exact, bounded exceptions. Missing input otherwise means unavailable, not empty:

| Input / exception | Allowed scope |
|---|---|
| Retained hierarchy | Exact approved 200-SKU/20-location catalogue, hierarchy and scopes; versioned read-time SL1–3/LL1–3 supplement bound to approved run/date/digest/catalogue. No F2 modification or invented hierarchy. |
| Empty transit and initial BPR remarks | Exact June 17 terminal supplement only, bound to complete retained shipment ledger and audit/input identities. No positive logistics or other-date transfer. |
| DBM positive trials | Separately owned retained pre-action scenarios, genuine run/date/actions and own predecessors. Apply/Sleep and restoration evidence is retained; no standing trial mode or permission reassignment. Any future authorized trial must stop action access and prove normal admission/date/Suggestions0/actions-disabled/gateway restoration on success, failure or interruption. |
| Empty initial OpenExpediteRequests | Human approval `call_zbzXQ93n4Qfs9tOGAixne3Lc`, selected June 17 preview only. No historical-empty claim or request writes. |
| Excess preview history | Human approval `call_bEZzSUkIR32TJ5lhNiuxhyFI`; empty pre-June 6 opening ONLY for this preview; June 6–17 own-output projections, 770 typed rows. Not proof of empty legacy history or a general rolling publication lifecycle. |

Excess input: `D:/freshvcf-build/inputs/excess-history-input-v1.json`, SHA256 `f7a03468227d2b5ef97fc28fec951ec8f373852ed906c9754d50269b75b84154`. Atomic publication/retry preserved accepted run metadata and existing projections. No engine replay or copying calculated legacy output into modern state occurred. General next-day publication/retention lifecycle remains a later architectural obligation, not an extra recovery platform to build during the paused page batch.

## Next bounded task — preparation, not execution authorization

The four-page dataset availability exit is accepted as recorded above; broader page implementation remains paused. Before a separately authorized whole-page continuation:

1. Reuse the retained page inventory and above residual ledger. Identify only missing page inputs/scenarios; do not repeat a full discovery programme.
2. Prefer the existing approved catalogue/population and retained history/trials. Define a finite fixture manifest covering required positive, empty, NULL, scoped and historical UI branches. Record exact missing facts and ownership before any loading.
3. Map the same logical consumer inputs to legacy MSSQL and modern PostgreSQL using their actual contracts. Confirm dataset/date/scope and restore boundaries. Do not assume identical physical schemas, overwrite accepted serving state, reset consumed trials, or create fake accepted calculation runs.
4. Separate claims: common consumer fixtures can prove API/UI contract compatibility. They cannot establish independent engine calculation parity. Calculated-state acceptance still requires each engine's own inputs, predecessor and outputs. Preserve F1/F2 proof untouched.
5. Deliver one complete page package with one consolidated affected QA pass, then record its result here. Retry only failed or changed behavior. No per-click delivery cycle, generic fixture/history framework or unbounded replay programme.

A small UI fixture does not satisfy whole-population performance or permission coverage. The separately stopped legacy date-alignment replay is not an instruction to resume it; retain its partial evidence and establish oracle availability before any new comparisons. SKU 6061's prior screenshot discrepancy was pagination/filter coverage, not proof that the catalogue identity was missing.

## Acceptance and engineering boundaries

- Preserve canonical NULLs, duplicate multiplicity/order, types, envelopes, filters, permissions and calculation semantics. No legacy repairs, guessed defaults, hidden fields, count-only parity or unsupported exclusions. Use `docs/LEGACY_EXCEPTIONS.md` for attributable, narrowly scoped flaws.
- Preserve accepted F1/F2 rows, frozen inputs/actions/SQL/comparisons/receipts. Reuse accepted evidence unless a relevant change invalidates it. Exact earlier approvals do not transfer to different runs, populations or workflows automatically.
- Existing frontend/auth/MTO business contracts remain the target. Retain explicitly approved fixes; no further redesign or permission changes implied. Actor-owned layout writes are distinct from immutable publication and business actions.
- Keep read queries tied to the actual page contract; scope/filter/count/order/page at the relational boundary where semantics permit. Preserve startup admission, run/digest/projection/config binding and full command integrity. No blanket cache, framework or speculative schema. Any schema change needs Django check, migration check/plan and migration-enabled PostgreSQL proof.
- Measure the configured request path when diagnosing repeated verification work. Consolidate demonstrably redundant reads without dropping integrity. The Guided diagnostic covers Excess and one unaffected route; it does not authorize a general admission redesign.
- Performance compares equivalent independently retained legacy/Fresh input/date/population, scope/hierarchy, request/filter/page/columns/export/output and resources. Protocol: 5 warmups, 30 interleaved warm samples, 5 application-cold repetitions, concurrency 1/4; retain raw failures, median, p95 and throughput. Fresh median/p95 no worse, throughput at least equal, errors no worse. Require affected API and browser journey proof. Missing comparable provider or inconclusive evidence stays UNPROVED. No arbitrary threshold, reduced population, shared cache flush or calculation replay just for benchmarks.
- Protect 3002/3003/3004, other tasks, live databases and shared infrastructure. `F:/vflow_integrated` is read-only reuse; `F:/new_vflow` excluded. No serving reset/repopulation, new public port, resource increase, shared Docker/WSL restart/prune or borrowed test database. SQL replay uses verified unique owned `VFTEST_Fresh_*` databases and the exclusive oracle lease; never bypass a verified owner.
- Stage 2 excludes BOR/supplier families, positive logistics, MDM, remarks, expediting/due-date writes and other Stage 3/4 workflows. DBM's exact amendment is the exception, not authority to open those workflows. MTO regression/final deployment and 3004 cutover remain later gates with explicit coordination.

## Evidence and supporting contracts

Read the relevant pointer, not the whole historical tracker. Evidence is external; this file keeps conclusions and open exits.

| Evidence / document | Purpose and limits |
|---|---|
| `D:/freshvcf-build/evidence/f2-runtime-memory-full-011/execution.json`, `terminal-readback.json`; `f2-runtime-memory-sql-full-011/replay.json` | Retained F2 terminal execution, relational readback and independent oracle evidence; qualifications remain. |
| `D:/freshvcf-build/evidence/f3-stage1-admission-002/receipt.json` | Accepted Stage 1 admission. |
| `D:/freshvcf-build/evidence/f3-stage2-guided-batch-001` | Guided checkpoint evidence described below. |
| [Archived tracker](archive/MIGRATION_2026-10-03_2d0cfde.md) | Earlier per-page receipt paths, exact approval context and preserved failures. Historical only. |
| [Page delivery contract](audit-2026-10-01/PAGE_DELIVERY_CONTRACT.md) and [interaction inventory](audit-2026-10-01/PAGE_INTERACTION_INVENTORY.csv) | Whole-page delivery method and static route/API/background candidates; inventory is not dynamic interaction proof or another queue. |
| [BPR contract](audit-2026-10-01/BPR_PAGE_CONTRACT.md), [Guided contract](audit-2026-10-01/GUIDED_PAGE_CONTRACT.md) | Specific source/request/producer contracts; current status comes from this file. |
| [Recovery plan](audit-2026-10-01/RECOVERY_PLAN.md), [earlier Stage 2 plan](audit-2026-10-01/STAGE_2_COMPLETION_PLAN.md), [audit](audit-2026-10-01/AUDIT.md) | Supporting scope/dependency references. Old sequencing, authorization and status statements are historical. Stages 3–5 require reassessment after Stage 2. |

Guided evidence: `filtered-scoped-comparison.json` has 468 independent cases; `excess-trend-comparison.json` has 110; these are **578 consumer comparisons, not UI interactions**. `excess-history-comparison-001/receipt.json` covers 12 own-output/770-row comparisons. `history-publication.json` and `history-postgres-tests-003.txt` prove atomic/readback/idempotent retry and six transaction/producer tests. Earlier failed attempts remain preserved.

`unit-suite-final.txt`: 270 tests, 268 passed; two pre-existing Expedite fixture failures (503 vs 200) remain: `test_expedite_chart_native_scope_and_source_flaw_unavailable` and `test_expedite_count_direction_and_unavailable_detail_contract`. Do not report the suite green. Baseline verification retained 376 pinned resources unchanged.

`build.txt` and startup admission establish the deployed checkpoint. `guided-gateway.json` records authenticated HTTP 200 twice for all 11 Guided routes plus BPR count, with complete bodies; it is not independent value comparison. Observed modern-only Excess 2.80–3.06s and BPR count 0.82–0.87s are not matched performance acceptance. `browser-handoff.png` proves only the bounded browser observations in the page ledger.

## How this tracker is maintained

Update current rows in place at a logical page exit or meaningful blocker change. Keep the active page, remaining exit, permitted boundary and required proof explicit before mutation. Record a concise result and evidence pointer; keep commands, test transcripts and incident chronology outside this tracker. Commit/push coherent checkpoints, not every probe. Never mark the overall goal complete while required exits remain. Do not resume the paused executor merely to acknowledge this baseline.
