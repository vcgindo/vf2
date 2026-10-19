# CSV daily operation — verified delivery boundaries

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

19 October 2026. The sole current status/approval authority remains `F:/freshvcf/docs/handoff-3005/TRACKER.md`. This is a proof index, not another queue. The cohesive CSV intake and daily operation delivery is complete for the verified fresh-install boundary: two native days, existing report preparation, authenticated original UI, five downloads per date, failure/resume protections and exact original-service restoration passed.

## Delivered operation

`release/run_daily.ps1 -BusinessDate YYYY-MM-DD` is the operator/scheduler entry point. It calls the repository's `process_daily_csv` coordinator: complete batch → immutable originals → CSV/native validation → own persisted predecessor → ordinary native calculation → existing full report/Planning/guided preparation → input archive → native admission/selection → MTA-only restart → actual process acknowledgement. No new report producer, scheduler daemon, serving API, frontend behavior or MTO change was introduced.

Three optional host-path settings configure incoming batches, the reviewed onboarding binding and private host operation receipts. Initial masters/opening remain a separate explicit native initialization, not an installation or daily side effect. [The operator instructions](../../release/CSV_DAILY_RUN.md) give the file/column/null contract, example conversion, invocation, diagnostics and safe resume. The sample converter stays outside production images.

One additive migration, `0143_daily_feed_attempt`, stores bounded operational metadata. The worker uses the existing trusted installer CLI authority already required by manual native daily execution. The serving role gains no attempt/calculation INSERT privileges. Normal Compose startup still has six services, no automatic daily work and no CPU/memory ceilings. The explicit `daily` profile has no listener and cannot activate provisioning. Fresh installation/registration is verified; upgrading an existing sealed namespace is not silently authorized or claimed.

## Actual fresh-target proof

Evidence root: `D:/freshvcf-build/evidence/production-csv-20261019`. Native runtime build source: `132364658a1cb1d60071a068bf4a94b5bbc339d1`, on `codex/3006-logistics-integration`. Later changes are operator Compose dependency correction, documentation and tests; the runtime Python and host wrapper match that tested implementation, recorded in `final-runtime-source-match.json`.

The fresh private target is `vectorflow-csv-20261019`, with no published ports. Normal provisioning, complete real migrations, Django checks/no pending migrations, finite metadata grants, current-source registration and one native initialization passed. Database `vectorflow_mta`, OID16402; namespace `e75c5dcf-c028-421b-b6cc-840cc04e74a3`; initialization `30572302-6da7-429a-8312-f59ebc20fc3f`. Full opening/current-master verification completed in its required rollback-only transaction before the first day.

| Business date | Native run | Verified result |
|---|---|---|
| 18 October 2026 | `223e1bae-4443-4c82-afa5-99b9f28e904f` | SUCCEEDED; full typed input/output readback; all20layers/own summary/guided aggregates; five download files; actual MTA serving acknowledgement. Output `7cae9892dc8b031d71934eccfe0a49d2a950162278a43f4a35253776481a5fb7`. |
| 19 October 2026 | `ffec6a92-89a1-4186-a110-2f7a1710448c` | Same complete proof; predecessor is the exact new18October run/output. Output `37f733edc2582b22f07c76465ebee5a1cfa347b75519460a18015a913a99e2fc`. |

`proof/backend-final-proof.json` indexes complete typed input/output artifacts, layer seals, summary digests and each download's bytes/hash. It establishes exactly two successful native headers and no failed native header. Four Pick downloads are header-only for these raw facts; byte correctness is verified, but a positive Pick allocation is not claimed. Native warnings for empty PhaseOut/StopPhaseOut/PhaseInNorms populations (`-141/-146/-142`) are retained exactly, including inherited day-two history. They were not removed or converted into passing business assertions.

The actual normal host wrapper completed both dates. The changed root Compose daily dependency is separately configuration-tested: the daily service does not pull in installation/provisioning. No Docker build, initialization or calculation occurs inside the daily wrapper.

## Failure and replay protection

- Malformed CSV produced durable original files and record/column diagnostics before any calculation header. Producer-level master duplicate, negative supplier SOB and daily-subset rejection tests preserve exact existing reason codes/continuation behavior; these are component tests, not extra full engine dates.
- A real competing PostgreSQL session could not acquire the initialization lock. The real live-date uniqueness constraint rejected a second attempt owner. Serving-role calculation/attempt INSERT remained denied.
- Identical completed input for both dates returned its existing receipt without another header or selecting the older date. Changed bytes for a consumed date were rejected before the engine. Terminal audit found no other open client transaction.
- An external test interrupted preparation after day-one COMMIT. Its linked SUCCEEDED run/output remained intact. Explicit resume reused it and completed preparation without calculation replay.
- A controlled private MTA startup failure left the same PREPARED/SERVE attempt intact. Explicit serving resume admitted that exact generation, then recorded PUBLISHED. No old-selection file was claimed to roll back mutable state.
- Existing input archives are validated before reuse. Identical archives are idempotent; corrupt/partial bytes fail closed and are not overwritten.

The affected parser/native-contract/archive/export/Compose/packaging/producer suite passed 78 tests. Real migration and PostgreSQL/native proofs are separate from those tests. Full outputs and row-level diagnostics stay outside Git; no secrets, dumps, calculated fixtures or external test operators were shipped in the image.

## Original authenticated UI acceptance and restoration

The human approved the exact maximum 30-minute MTA-only packet, SHA256 `594a8dccb78dae28184644a75587072979c514af7772207c79ced178b6c16ffe`. The actual decision is retained in `ui-window-approval.json`. The window ran from 04:17:19 to 04:27:19 UTC on 19 October, then restored the original service before its deadline. The independent finite restoration guard exited; no recurring monitor was created.

Existing normal logins were used without account, role or scope changes: MTAStarter for scoped reports, administrator for native downloads including admin-only InputData. Both 18 and 19 October rendered through the unchanged frontend and gateway: 12 BPR rows, 8 RRR rows, Planning charts and 4-row excess-inventory grids, and the correctly empty current DBM suggestions screen. All 24 BPR rows' identities, Norm, virtual Norm, stock, on-hand penetration, colour and GIT matched the retained native consumer values. For example, SKU 337/DP010290 changed from stock 6/GIT 5 on 18 October to stock 11/GIT 0 on 19 October. The existing consumer projection supplies virtual Norm and physical inventory penetration/colour; raw producer BPR_Table TechPen is not substituted for that projection.

All five original download controls were exercised for each date. The four Pick CSVs and InputData.zip were actually saved and SHA256-matched to their respective native files. Header-only Pick files remain an explicit data-coverage limit. The separate temporary observation selection served each already-published generation read-only; the authoritative 19 October selection and current database owners were preserved. No calculation or workflow was submitted during the window.

`ui/final-ui-proof.json` indexes the actual snapshots/screenshots, 24 row value checks, ten download proofs, persisted run/attempt audit and terminal receipts. Exactly two SUCCEEDED native runs and two linked PUBLISHED feed attempts remain, together with the original pre-engine REJECTED CSV attempt; zero RunCommands and zero other open client transactions were observed. Failed browser automation waits and two external verification expectation corrections are recorded separately; neither changed application code or business state.

Original MTA container `61e266300be8` was restored with its exact image, network, IP 172.25.0.4 and aliases, and became healthy/ready. Frontend, auth, MTO, original PostgreSQL and Redis container/image identities remained unchanged. Candidate `c1b7065f8d0e` was stopped and detached from the existing application network. Its private PostgreSQL `d5a8d500fa4b` was also stopped; both exited 0, PID 0, non-OOM, with no active owned container/job. Volumes, network, private inputs/secrets and evidence were retained. Protected 3005 and unrelated services were not touched.

## Limits

No public deployment/cutover, customer-specific CSV layout/API connector, automatic scheduler installation, production-volume performance, alternate-v2 full-engine trial or sealed-instance upgrade is claimed. The documented CSV contract and repository-owned command are delivered; Windows Task Scheduler/cron can invoke that same command, but no scheduler was installed. V2 master/supplier CSV mapping and native decode are verified separately from the active-NMS two-date engine case. Existing inherited application/parity limitations remain applicable. Existing installations were not upgraded or resealed by this validation; follow the documented fresh-install/onboarding boundary.
