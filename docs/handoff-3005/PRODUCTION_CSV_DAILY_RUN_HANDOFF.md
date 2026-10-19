# CSV daily operation — verified delivery boundaries

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**

19 October 2026. The sole current status/approval authority remains `F:/freshvcf/docs/handoff-3005/TRACKER.md`. This is a proof index, not another queue. Backend execution and recovery passed; original authenticated UI acceptance is awaiting its separately requested MTA-only connection window. This feature is not yet declared fully closed.

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

The affected parser/native-contract/archive/export/Compose/packaging/producer suite passed78 tests. Real migration and PostgreSQL/native proofs are separate from those tests. Full outputs and row-level diagnostics stay outside Git; no secrets, dumps, calculated fixtures or external test operators were shipped in the image.

## Remaining acceptance and limits

The requested original-UI window is at `D:/freshvcf-build/evidence/production-csv-20261019/ui-window-decision.json`: maximum30minutes, MTA-only temporary connection at existing8080, no auth/frontend/MTO replacement or permission change, no new calculation/workflow, exact original-service restoration. Its independent finite restoration guard is prepared and identity-validated but has not started without actual approval. Both published report generations can be observed read-only using a separate temporary candidate selection file; the authoritative daily selection remains19October, and current database owners are not rolled back.

After that accepted window, record actual scoped BPR/RRR/Planning/DBM/date/download observations and exact restoration before closing this delivery. The existing current instance and protected3005 remain unchanged so far. No public deployment/cutover, customer-format/API connector, automatic scheduler installation, production-volume performance, alternate-v2 full-engine trial or sealed-instance upgrade is claimed. V2 master/supplier CSV mapping and native decode are verified separately from the active-NMS two-date engine case. Existing inherited application/parity limitations remain applicable.
