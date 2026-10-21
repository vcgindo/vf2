# Single large-data April8 attempt: calculation passed, persistence OOM

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

## Actual outcome

The one approved97,097-SKU/location-pair April8 saved-input attempt is stopped and incomplete. Loaded masters/opening and accepted CSV inputs were reused; no master reload, history import, CSV reparse/restage, legacy rerun or extra date occurred. The complete calculation, including R1, order allocation, Pick, supplier, DBM and BTR, returned successfully. Pick generated6,488allocations. Four Pick files were generated. Atomic persistence did not complete: Docker reports the worker OOMKilled, exit137/PID0, at15:54:18.778972UTC21October2026. No automatic retry or seventh continuation is released.

| Observed stage | Seconds |
|---|---:|
| Compatible release append |6.143|
| Saved input reconstruction |318.797|
| Entry preparation |56.043|
| Controls |177.884|
| Native order allocation |7.077|
| Pick |3.354|
| Remaining BPR |14.342|
| DBM |450.573|
| BTR |509.288|
| Full daily calculation, including nested stages/finalization |1664.141|
| Pick files |1.075|
| Worker lifetime through OOM |3283.600|

Nested timings overlap and must not be summed. Calculation throughput is approximately58.35SKU/location pairs/second for this specific case; it excludes earlier initialization/CSV intake and does not measure a successfully published day. Peak recorded process RSS was15,179,501,568bytes (14.14GiB); the last sampled worker memory reached14.49GiB of the15.46GiB Docker host. Paging and Docker observation timeouts occurred. These observations do not justify a general capacity promise or an unqualified speedup comparison against the historical/split-phase legacy run.

## Exact identities and preserved boundary

Tested code/image source commit: `f1345857160c2105bcb21f03cb9e203755edc631`, branch `codex/3006-logistics-integration`. Image: `sha256:27989e026c65a0748d5869cf1eee295d63d25893e8837d3c91304f2a1a39343f`; native manifest: `30229bc19a8af615776c7146c1b8d5f1bd5ee9ef5ec197e668f998bfeca96bfb`; source export: `38b6b8d4b0be11b6dd0498a61ea137ec4d60c135b98f3f95eddc9ba1be22652b`. All766packaged application files, report source, imports and non-root identity passed. This documentation outcome does not imply a new image build.

Worker `972de1478f8271f3bdff6cba3daaf819458b097d2dc1d87913cb101c7d28db41`; run `15c38728-9782-4d72-b731-2573fb8ba9b5`; public attempt `f24b08e7-db3c-4ac2-a99f-3976314fa8eb`. The earlier external launcher KeyError was corrected before any business attempt or compatible append; original script/logs and failed launch were retained, then the SAME worker/image/configuration continued under the original fixed window. No second business attempt was made.

A real resource/observation failure stopped acceptance. Docker recovered without shared restart; the separately approved recovery restart was skipped as unnecessary. Independent terminal read-only checks prove all386typed output tables have zero rows for the new run, no checkpoints/commands/publications/successors, and no owned jobs/clients/open transactions. The existing initialization, certification, namespace, capability, migration graph, role/membership catalogue and all six original service identities/images/running/start states are unchanged. All five previous failed full owner records and all six earlier attempt files match their before hashes. Only the prior human-stopped leaf was canonically disposed as HumanInterruption during the approved admission.

The new process-interrupted header remains truthfully RUNNING/CALCULATE/CAPTURED with no committed output; no arbitrary SQL FAILED/SUCCEEDED rewrite was performed. Process OOM and database lifecycle status are separate facts. The input reference remains readable within the fixed six-wrapper limit; no seventh path was enabled.

## Evidence and next boundary

Evidence root: `D:/freshvcf-build/evidence/daily-contract-audit-20261021/section10-admission-proposal/`. Read `actual-terminal-worker.json`, `large-operation2-measurement.json`, `performance-summary.json`, `terminal-preservation.json`, `terminal-new-owner-full-typed.jsonl`, `terminal-full-owner-records.jsonl`, `terminal-rollback-prefix-proof.json`, `resource-failure-handoff.json`, `large-operation2.log` and resource samples. Small lifecycle proof and source/package receipts remain separately bound in `lifecycle-readiness.json`, `terminal-sixth6-postgres.log`, `source-remote-receipt.json`, `candidate-release.json` and the approved decision/release/window files.

The bounded attempt is concluded as incomplete. Calculation success is tangible; persisted results, full large-data typed readback, report preparation/admission/selection and usable UI are NOT claimed. The unresolved blocker is memory use during the persistence path after a high-memory calculation; the exact retaining/copying cause is not established by this run. Any further production diagnosis/correction must be scoped from that boundary, preserving the loaded opening, original inputs and accepted calculation semantics. No automatic build, timeout/resource increase, new namespace, reference-depth extension, replay or daily retry follows from this handoff.
