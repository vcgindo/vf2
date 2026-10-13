# VectorFLOW 3005 production handoff plan

Version 1.0 | 13 October 2026 | Implementation guideline

Prepare an independently deployable VectorFLOW application from the 3005 code and application baseline. Preserve its calculations, existing frontend, MTO integration and optimized presentation paths. Add the missing native ingestion, daily execution, report publication and operating capabilities. Demonstrate the result with small functional datasets, without carrying the heavy migrated testing population into the handoff.

The delivery sequence is: establish the baseline, generate native data, demonstrate that data in the UI, package the working application, then verify installation and recovery. The main functional UI acceptance occurs in Step 3. UI checks begin in Step 1 and continue at every relevant change.

## Authority and document ownership

This plan defines the implementation scope and acceptance criteria. [TRACKER.md](TRACKER.md) is the sole progress, blocker, decision and evidence tracker for this five-step handoff. The user's instruction to create a separate tracker supersedes the earlier requirement to use `docs/MIGRATION.md` for this effort only.

Do not import old stage names, completion labels, pending queues or approval requests. Earlier plans and trackers are historical context, not prerequisites or execution instructions. Existing code and useful artifacts may be inspected or reused, but each adopted item must have a clear purpose and boundary in the new tracker. Reused evidence must match the code, inputs and behavior it is being used to support. Its availability is not a reason to create another discovery programme.

This is a fresh plan, not a reset of existing business contracts or permission to change calculations. Preserve typed values, NULL behavior, duplicates, source order, scope rules and known business limitations. A proposed business amendment needs its exact terms and user decision recorded in the new tracker before implementation. Do not treat a previous approval as transferable without establishing its scope.

Creation of these planning artifacts did not itself start implementation or change a serving stack. Subsequent implementation releases and their exact boundaries are recorded in the tracker. Routine work within a released boundary can proceed without repeated permission questions; genuinely new business decisions and protected serving operations remain separate.

## Branch and working boundary

- Preserve the original 3005 checkout, its dirty work, deployed assets, databases and retained data.
- During Step 1, pin the actual 3005 source and deployment identities. Create a separate worktree and a new branch from that pinned 3005 commit. Proposed name: `codex/3005-production-handoff`. Record the actual name and path once created.
- Distinguish deployed source, accepted later source changes and unfinished experiments. A branch from the current HEAD does not by itself reproduce the deployed application. Import only deliberately selected changes.
- Treat the previous production-handoff branch as a source of candidate patches. Do not merge it wholesale or delete baseline, parity or test assets from the development repository.
- Exclude validation and legacy execution assets from the production export. Retain native PostgreSQL queries, migrations and necessary application integrity checks.
- Use one owned, bounded validation environment when execution is released. Record exact databases, services, storage and access boundaries before using it. Reuse resources only after confirming ownership and suitability. No heavy dataset restoration, shared infrastructure reset, additional public port or production cutover is implied.
- Keep 3005 and other existing serving addresses protected. A required startup or deployment must respect the applicable explicit authorization. No automatic 3004 cutover.

## Small functional data policy

Use a compact population chosen for business coverage, not a large copied customer or testing database. Prefer suitable retained input artifacts when they reduce work; otherwise define transparent synthetic external facts. Freeze each case's inputs and expected checks before execution. Keep the optional demonstration data outside the default production installation.

The minimum case set must cover:

1. A positive core flow with a supplier, parent and child relationship, stock shortage and surplus, and enough SKUs to exercise the required report branches.
2. Enabled MDM and NMS changes, including applicable supplier and control changes, with their actual approval and next-day effects.
3. Genuine calculated recommendations for Apply and Sleep, with separately identifiable cases and own persisted successors.
4. Required order allocation, receipt, transit, request and remark behavior, including a positive case where the feature requires one.
5. Empty results, denied scopes and relevant NULL, duplicate and ordering boundaries.
6. Historical and trend behavior plus the populated retained MTO journeys selected in the Step 1 coverage boundary.

Keep populations small. Choose history depth from the rule being tested; do not shorten a required horizon simply to call the data shallow. Declare any rounding rule explicitly. Synthetic facts must reconcile stock, shipments, receipts and consumption. Every calculated report, suggestion, accepted Norm and successor state must come from the application. Do not seed calculated outputs to make a screen look populated.

A small-case pass establishes functional behavior in that case. It does not establish production-volume throughput, capacity or large-history latency. Those claims remain unproved unless separately scoped and measured. No heavy-data campaign is part of this plan.

## Step 1 Establish a reproducible application baseline

**Improvement:** a precise, recoverable starting point and an explicit list of behavior to preserve. This step changes no business behavior.

**Entry:** implementation released; access to the 3005 checkout and deployment metadata established. If services are stopped, record that state and obtain any necessary startup authorization rather than asserting current health.

**Work:**

- Record source commit, dirty-file boundaries, image identities, effective configuration, mounts, schema identity, selected data owner and prepared generations. Record secret references only, never secret values.
- Reconcile those identities to source and configuration. Separate the existing heavy reporting population from the code needed to create and read reporting data.
- Map each required journey from publication and refresh through tables/indexes, reader, API, gateway, frontend transformation and usable display. Mark fixture-specific dispatch and unconnected native paths explicitly.
- Establish the finite required scope for BPR, RRR, DBM, BTR, Guided, Research, Buffer Trends, Planning, agreed BOR/BOROA, MDM and retained MTO journeys. Do not silently remove a required family because it is difficult or unavailable.
- Define the small-case roster and expected outputs or invariants. Identify candidate backend additions and distinguish plumbing, missing producer logic and business amendments.
- Create the isolated branch/worktree and pin the baseline. Preserve all unrelated dirty files.

**Tests and UI checkpoint:** reproduce a bounded set of existing login, navigation, report, scope, filter and download journeys when the serving environment is available. Reuse applicable retained observations without claiming them as fresh runs. Record actual loading behavior and reader dispatch. Baseline UI failures are explicit gaps, not behavior to reproduce as successful acceptance.

**G1 exit criteria:**

- G1.1 Source, deployment, database and worktree identities are recorded and reproducible; unresolved source differences are identified.
- G1.2 Required journeys and their prepared-reader paths are mapped, with a clear disposition for each baseline gap.
- G1.3 The compact test roster, branch boundaries and intended transfer units are defined.
- G1.4 A bounded UI baseline is recorded with its date, population and limitations; protected resources are unchanged except for separately authorized actions.

**Deliverable:** pinned baseline, journey map and test roster referenced from the tracker. No second status document.

## Step 2 Complete native ingestion and daily execution

**Improvement:** the application can accept supplied masters and external facts, calculate a day and continue from its own persisted state without legacy execution or fixture approval machinery.

**Entry:** G1 satisfied, or a specific independent subtask released against an evidenced blocker. Select only the necessary additions from previous work.

**Work:**

- Integrate typed initialization, opening and daily input contracts, including the documented CSV/JSON or other supported operator feed boundary. State who supplies deployment data and how invalid or incomplete input is rejected.
- Integrate native MDM capture, applicable NMS/control behavior, supplier inputs, ordered actions, own-predecessor loading and frozen retry around the existing `execute_day` boundary.
- Complete required BPR, RRR, DBM and BTR producers and the agreed allocation, buyer-report, history, shipment, request and remark sources. Preserve same-run ownership and transactional persistence.
- Keep business amendments separate from dependency removal. Resolve exact missing contracts through the tracker; do not invent defaults, order identities or formulas.
- Keep calculation identity independent of unrelated presentation edits where a bounded correction is needed. Avoid repeated full-state reconstruction on ordinary reads; measure an observed bottleneck before changing its implementation.
- Use real additive schema migrations and retain development validation outside the exported runtime.

**Tests and UI checkpoint:** verify exact typed input/output readback, relevant calculations, duplicate/NULL/order cases, complete rollback of business rows on failure, frozen retry and an own successor. A failed-attempt record may remain by design. Demonstrate meaningful action and MDM effects in persisted state. Run affected existing UI regression checks as shared modules change. Native data need not be represented as fully usable in the UI before Step 3 connects its readers.

**G2 exit criteria:**

- G2.1 A clean native initialization and supplied daily feed pass, with invalid-input and ownership denials.
- G2.2 Required calculations and output sources pass complete-value checks in the declared small cases; no fabricated calculated state is used.
- G2.3 Own successor, relevant action/MDM effects, failure rollback and frozen retry pass without recalculating accepted days.
- G2.4 Schema checks and focused regression proofs pass; all unsupported domains or new business decisions are visible.

**Deliverable:** coherent native runtime/input/producer changes and evidence, committed at the logical step exit. API/UI readiness remains a separate G3 obligation.

## Step 3 Connect native reporting to a usable UI

**Improvement:** freshly calculated data reaches the existing frontend through the intended prepared reporting layer. This is the main functional application acceptance step.

**Entry:** G2 outputs and source ownership are established. Reuse the existing frontend, gateway and MTO integration.

**Work:**

- Prepare all required report layers and summaries from the same native run. Select a complete coherent generation atomically; leave the previous usable selection intact if preparation fails.
- Connect native endpoints to the prepared readers used for the relevant optimized paths. Remove fixture-only gating from the production path through explicit native admission; do not merely disable fixtures and accept a slower fallback.
- Preserve filters, permission multiplicities, counts, ordering, paging, wire types, columns, exports and history. Scope/filter/page at the relational boundary where the contract permits.
- Integrate real login and scopes, actor-owned layouts, permitted remarks and actions. Show the action's effect after an own successor and subsequent publication.
- Verify populated retained MTO journeys within the frozen scope, including required gateway/WebSocket and download behavior. Preserve MTO rules and avoid a redesign.

**Tests and UI checkpoint:** walk the required journeys using the small dataset: login; populated and empty grids; broad/restricted/denied scopes; filters; pagination; layout where supported; charts/horizons/history; downloads; MDM approvals; Apply/Sleep; successor display. Compare API values and downloaded cells with the intended persisted outputs. Observe request counts, payload size, reader dispatch and click-to-usable-screen behavior. Set finite small-case performance acceptance before modifying the reader; use matched inputs and resources, not old heavy-data timings as thresholds.

**G3 exit criteria:**

- G3.1 Every required publication layer and summary uses the correct run/date/generation, with incomplete or mixed publication denied.
- G3.2 Every required journey has passed UI/API/export checks or an explicit user-approved scope disposition. A blank grid does not prove a required positive flow.
- G3.3 Actual requests use the intended prepared paths. Bounded small-case screen measurements show no unexplained regression against the agreed baseline or acceptance target.
- G3.4 UI actions and required MDM operations are reflected in their own successor and newly published screens; relevant MTO journeys pass.

**Deliverable:** a usable demonstrated application. Do not move to packaging with required screens broken, wrongly scoped, missing required data or silently bypassing optimized readers. READY receipts alone cannot close G3.

## Step 4 Package the working application for deployment

**Improvement:** the Step 3 application can be installed and operated without this workstation or the development checkout.

**Entry:** G3 satisfied. Package the demonstrated implementation rather than replacing its integration design.

**Work:**

- Produce a versioned source/runtime bundle and reproducible service configuration for the agreed deployment target. Pin required dependency and image identities.
- Include frontend, authentication gateway, MTA, MTO, PostgreSQL and required background/realtime services. Declare supported OS/runtime versions, addresses, origins and WebSocket configuration.
- Exclude SQL Server, BAT/DLL execution, oracle/comparison runners, validation fixtures, heavy test data and hardcoded local-drive paths from the production bundle. Keep necessary native PostgreSQL SQL and migrations.
- Provide external secret configuration, least-privilege roles, durable storage, permissions and operator commands for initialize, day, span, status, publication, restart and recovery.
- Provide migration, backup, restore, upgrade and rollback procedures, plus useful readiness/failure diagnostics. Do not add a new scheduling platform unless the agreed operation requires one.
- Supply small demonstration inputs separately and optionally. The default install must not restore a test/customer database or reset credentials.

**Tests and UI checkpoint:** install from the exported package in the owned target environment, apply real migrations, ingest the compact inputs and run the application without checkout mounts or legacy infrastructure. Repeat affected Step 3 UI journeys through the packaged gateway. Check restart persistence and actual service routing. Inspect the package for excluded assets and unresolved local defaults.

**G4 exit criteria:**

- G4.1 The complete service assembly installs from the versioned bundle using external configuration and secrets.
- G4.2 Roles, migrations, volumes and required service connections work on the declared deployment platform.
- G4.3 Packaged UI journeys retain G3 behavior and prepared-reader dispatch after startup/restart.
- G4.4 The operator/runbook, backup/restore and upgrade/rollback procedures are concrete and ready for the final rehearsal; package exclusions pass.

**Deliverable:** reproducible package, configuration templates and operator runbook. Source assembly or a Windows-only script test cannot certify a Linux target.

## Step 5 Verify the release and hand over

**Improvement:** demonstrate one coherent installed system and its recovery procedure, then provide an explicit operational handoff.

**Entry:** G4 package pinned. Reuse prior passing evidence; rerun only installation-dependent, changed or previously unresolved boundaries.

**Work and tests:** execute the small continuous path from external input through initialization, daily calculation, persistence, preparation, publication and UI/export. Exercise the required action and own successor. Demonstrate interrupted-run handling, frozen retry, missing generated-file recovery where supported, service restart and an actual backup/restore to owned resources. Verify restored values, identities and usable reports. Check the applicable upgrade/rollback path and record the exact target configuration.

**Final UI checkpoint:** repeat the representative end-to-end journeys on the packaged installation and restored system. Confirm correct values, date/generation, scopes, actions, exports and prepared-reader paths. Step 5 confirms the Step 3 application; it is not the first time the UI is tested.

**G5 exit criteria:**

- G5.1 Fresh install and the complete small-data input-to-successor-to-UI flow pass from the pinned release.
- G5.2 Failure/retry/restart and actual backup/restore preserve accepted state and restore usable application behavior.
- G5.3 The operator can follow the delivered instructions; all required defects are closed or explicitly dispositioned by the user.
- G5.4 The release record states the tested scope, platform, resource configuration, known limitations and unproved production-volume capacity. Cutover steps and rollback are explicit; execution remains separately coordinated.

**Deliverable:** versioned handoff package, operating instructions and release evidence. Use the claim “deployment handoff verified for the declared functional scope” when justified. Do not turn small-data success into a universal production-capacity claim.

## Progress and verification discipline

Before each implementation batch, read the tracker and identify the active step, unmet criterion, permitted boundary and required proof. The primary implementer owns integration and the result. Use a helper only where independent work or review has a concrete benefit.

Complete one step before advancing. An evidenced blocker can permit explicitly recorded independent work, but does not make the blocked step complete. Required acceptance cannot be dropped by relabeling it deferred. A scope reduction or changed business contract requires the user's decision.

At a logical exit, record the exact source/package identity, test inputs, commands/results, UI evidence and remaining limits. Commit coherent implementation changes without sweeping in unrelated files. Run focused affected tests and the applicable repository checks; schema changes require Django check, migration drift/plan checks and real PostgreSQL migration verification. Broaden verification only for a relevant change, failure or unresolved concern.

Keep one consolidated evidence record per meaningful result. Do not create a new approval loop, tracker or extensive receipt framework for each script or click. The plan changes only when scope or acceptance changes; the tracker changes as work progresses.
