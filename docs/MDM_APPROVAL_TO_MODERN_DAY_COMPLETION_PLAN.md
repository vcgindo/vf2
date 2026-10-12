# MDM approval to modern-day completion — finite implementation proposal

Prepared 10 October 2026. **M1–M4 implementation released by the direct human
instruction relayed through controller01a1037c-5d96-7700-87a8-89a575f6c9f8.**
S1–S5 package preparation is separately approved in
`MDM_APPROVAL_DAY_SOURCE_DECISION.md`. New calculations and serving changes remain
held for their exact frozen release. `MIGRATION.md` records current progress.

`docs/MIGRATION.md` remains the sole status tracker. This document is the scope and exit contract, not another work queue. Approval of implementation must be explicit. A later frozen execution request must separately identify and authorize actual business-day calls and any serving-selection change.

## 1. Outcome and stopping boundary

Close one gap: real authenticated MDM approval -> exact frozen typed input -> the existing modern `execute_day` -> atomic queue/history/task consumption -> own persisted successor -> coherent MDM/read-side presentation.

Cover eight business families: SKU1, Location2, SKU–Location3, SOB4, MOQ5, Stop/Phase6–9, Seasonality10–12 and Force13. Masters7–9 and10–12 are variants, not additional families. Each applicable variant gets a named source/transition/result witness. A menu, successful approval, installed owner, empty queue or successful day alone is insufficient.

Deliver ONE reusable integration change, one bounded complete-flow correctness exercise, numbered verified commands and one cohesive commit/push/handoff; then STOP. No MTO implementation, broad report completion, full-population temporal run, capacity programme or general production-readiness claim.

The result must distinguish: (a) request approved; (b) request captured; (c) canonical input consumed; (d) business consequence persisted; (e) native task completion or legitimately pending lifecycle. Do not force every approval to say Completed if canonical SQL leaves it pending or defers a later date. A pending branch needs exact reason, evidence and later completion obligation; it cannot be reported as fully closed.

## 2. Fixed baseline and evidence reuse

Baseline delivery commit: `c55a1156b1e511de1357ba2913685962e200c306`.

Working3005 image: `sha256:b3bc7ea3994db6967a590fb3d5d7b265d680d7bce205f9395643e7efd3582016`; schema0106; fixture run `bfd75b4b-a9df-4a08-82d3-852e3324b623`, April7; source `eccbec8cf5f61f87f80bdf65715dee350e616041e7957f27daead42bab4b975d`.

Reuse `MDM_3005_DEPLOYMENT_HANDOFF.md`, `MDM_3005_OPERATOR_STEPS.md`, the existing MDM family/capture plans, Cohort5 admission and Cohort6 two-date proofs at their exact identities. Preserve all existing tasks, grants, scopes, downloads, failed attempts and consumer-fixture owner receipts. Existing ten reviewed tasks remain historical UI evidence, not new daily-source requests.

Important observed seam: `target_fixture.py` explicitly grants consumer admission only. The April fixture is not a modern DAILY_CHAIN predecessor or consumed MDM generation. Nine reviewed detail rows remain DB Update Pending. **Never relabel the fixture, fabricate a consumed capture, borrow its calculated closing as a new modern predecessor, or make its approvals silently migrate to another source.**

New acceptance requests belong to a separately owned, properly admitted daily source. No implicit transfer of Force flag overrides, historical clocks, hierarchy supplements or old source-specific qualifications. Declare any required transfer once in the frozen approval request.

## 3. Tight implementation boundary

Use existing services and owners:

| Seam | Existing owner / permitted boundary | Required result |
|---|---|---|
| Daily source and initial install | `mta/mdm/daily_source.py`, `daily_source_install.py`, existing family source modules | Truthful registered opening/configuration and exact source ownership; no fixture-to-daily bypass. |
| Family composition and input capture | `daily_input.py`, `supplier_capture.py`, `force_capture.py`, `season_capture.py`, `stop_pipo_capture.py`, `phase_controls_capture.py` and their existing revision helpers | Approved occurrences frozen once with source, task, revision, order, configuration and predecessor identity. |
| Combined owner binding | `integration_source.py` | All installed families share the same accepted modern source/predecessor; no latest fallback or mixed closing. |
| Day execution and successful consumption | `runtime/temporal.py`, `runtime/services.py`, existing `finalize_consumption` and family finalizers | One `execute_day` calculation; successful typed output and capture/queue/task/history changes committed coherently. |
| Canonical business effects | Existing ingestion, shared controls, order/supplier/DBM chain | Preserve source SQL, formulas, flags, NULLs, duplicates, date rules, priority and native ordering. Change only evidenced integration defects, not algorithms. |
| Supported command forwarding | Existing `run_daily` and required install/capture/accept/check commands | Exact source/profile/configuration forwarding; no second executor, scheduler or registry framework. |
| Presentation after consumption | Existing MDM publication/current/task/history helpers, prepare/accept/select guards | One coherent run/date/source generation; native status/date filters retained. No fixture projection fallback for operational sources. |
| Typed schema, only if necessary | Exact MDM runtime models and a forward migration | State/history/occurrences relational; bounded metadata only in JSON. No destructive migration or state blob. |

A file outside this list may be changed only for a demonstrated direct dependency of one row. Record the failed exit, exact dependency and smallest remedy before mutation. Reading one directly called helper is permitted; traversing unrelated families, producers or whole repository inventories is not.

Forbidden: reader rewrite, generalized onboarding framework, new recovery modes, wholesale reference-branch merge, frontend redesign, grant/account changes, broad source extraction, legacy repairs or hardcoded new run-owner exemptions. A narrowly registered input adapter may use a frozen artifact identity; acceptance policy must still verify actual typed receipts and lineage.

## 4. Fixed family consequence matrix — settle once before code changes

Use retained canonical SQL/BAT/DLL-matched source references already collected in family deliveries. Fill exact table/column/flag/transition references in one supporting matrix, without re-auditing entire workflows.

| Family / variant | Positive request witness | Consumption and result required |
|---|---|---|
| SKU1 | One supported modification on a retained identity | Exact approved field reaches composed raw master and applicable final importer/master state; queue/history and native task transition exact. No new SKU identity campaign. |
| Location2 | One supported modification on a retained identity | Same for producer-owned location field and applicable final state; current data and consumer scope remain coherent. No hierarchy/grant expansion. |
| SKU–Location3 | One supported pair modification | Exact pair values/exclusions and downstream master/current state. Add/remove contracts reuse passed proofs unless this seam changes them; do not invent broad lifecycle cases. |
| SOB4 | Valid retained supplier shares with native total/rule constraints | Exact configured supplier feed, approved occurrence handling, resulting supplier closing/source rows and history/task consequence. Count/totals alone do not pass. |
| MOQ5 | One supported selected destination format | Exact MOQ feed/configuration and resulting supplier state. Choose one native format in freeze; reuse unchanged proof for the other format, do not change formats mid-lineage. |
| Stop6 | One canonically eligible Stop/PIPO change | Correct working stop input and persisted control/phase consequence, occurrence/archive and task status. Eligibility must come from own modern opening/closing. |
| Phase7–9 | One Phase Out, one PIPO mapping and one Target Norm request on nonconflicting retained pairs | Exact phase input/current/map/history/Norm consequence and native completion rule per variant. Known Target Norm limitation must not become invented completion. |
| Seasonality10–12 | One eligible status request and one each absolute/delta request with declared dates | Exact queue/current/status capture, native date-window effect and computed result/history. Status request already applied at approval must not be reapplied by daily consumption. Preserve native status/label/draft qualifications. |
| Force13 | One canonically eligible forced-Norm request | Exact Force input, flags and computed Norm/control/history consequence; no bypass of master-match/eligibility conditions or direct Norm update by UI. |

Use disjoint pairs for conflicting controls; combine requests only when source order and compatibility are proved. Derived Norms, phase/control histories, recommendations and accepted closings are computed by modern owners. Never seed them to make an expected result happen.

Every row must name: actor/scope, request and approved queue, effective time, captured ordinal/revision, working input, exact output columns, consumer projection, task transition and reused/new proof. If a necessary outcome takes more dates than the proposed exercise, state it before execution. Do not shorten dates/durations, silently omit a variant, or add days later.

## 5. Four delivery stages and strict exits

### M1 — Freeze the known seam and authority request

Before substantive implementation record in MIGRATION: M1, its unmet exit, permitted files and proof. Produce one `MDM_APPROVAL_DAY_SOURCE_EXIT_MAP.json` containing only the matrix above plus the exact initial-owner bootstrap sequence.

The bootstrap question is finite: identify whether the existing installer permits a truthful registered root with base families, then attaches additional owners to that root's own persisted accepted closing/capture. Force/Seasonality/Stop/Phase modules have source-specific anchors; the existing April fixture cannot satisfy them. If the sequence is unsupported, name that direct seam and implement only the necessary source-owner binding. Do not create fake predecessor receipts to avoid a root day.

Prepare ONE consolidated decision covering exact root artifact/opening ownership, NMSActive/configuration and family flags, clocks/effective dates, target catalogue subset/scopes, and any required operation/admission-policy change. Prior inactive-NMS approval does not authorize active-NMS success. Under the user's synthetic-data authority, external facts and requests may be generated from the retained catalogue; pin every delta. Computed state and broadened grants remain outside that authority.

Exit: complete family matrix and bootstrap chain; exact missing authority named once; no code-by-investigation programme. Reuse the baseline maps, not another discovery report series.

### M2 — Implement one integrated approval/capture/consumption flow

Complete the source/install/command/capture/finalization/readback seams as a cohesive flow before running business days. Necessary evidenced in-scope fixes and failed/affected rechecks are autonomous under implementation release; do not ask routine per-field or per-fix permission.

Required guards: own accepted predecessor; immutable input/config/action/capture identities; atomic consumption with successful output; late approval retained for next capture; captured revision drift denied; no cross-source task update; no double consumption; failed run leaves original approvals/history and prior accepted publication intact.

Do not rename a disabled writer successful or permit stale/partial preparation. Maintain strict default admission and existing denied routes. If active-NMS admission genuinely needs a policy amendment, settle its exact required writers/flags/sources and denial cases in M1 before changing the guard.

Exit: integrated code and focused affected proofs pass, actual schema gates if needed pass, source package can be frozen. No component/probe commit or serving replacement to obtain evidence early.

### M3 — One frozen three-date correctness exercise, only after execution approval

**Proposed maximum: exactly THREE new `execute_day` calls total**, in one fresh owned modern lineage. This is a proposal, not current authorization. No legacy full-day call, warm-up, failing trial, replay of accepted days or hidden recalculation. Dates and commands must be exact in a later execution request.

1. **D0 bootstrap:** one root calculation with declared installed base owners and truthful opening/configuration; create the actual accepted closing/capture needed for combined family anchoring. All mandatory enabled writers must pass before proceeding.
2. Bind the remaining owners to this own accepted D0 using supported typed installation. Create the fixed approved requests through existing authenticated request/reviewer services. Use in-process gateway transport with real authentication/scopes by default; no duplicated full browser campaign. Existing3005 browser UI receipts remain reusable. Bind every resulting task to the new source; do not move existing fixture tasks.
3. **D1 consumption:** one day using D0 and frozen approved requests. Prove every named applicable family input/result/task/history/queue transition and source/date consistency. No direct insertion into approved queues as a substitute for workflow acceptance.
4. **D2 successor:** one day using D1 own closing/actions/configuration. Prove retained business effects, no repeat consumption, remaining legitimately scheduled control behavior and correct next input. No new requests to tune outputs after D1.
5. Retrieve/check completed identities without calculation; prove identical task/queue/history state and no duplicate effects. Prepare/admit the required existing layers and check coherent scoped consumption. Do not repeat backup/restore/consumer campaigns whose identity-valid receipts are unaffected.

Input limit proposed: at most20 retained SKU–location identities, plus only declared parent/supplier dependencies, from the same retained catalogue; no new business IDs. Pick the smallest subset satisfying the fixed matrix. Do not use the entire97097-pair fixture merely for more coverage. If existing registered artifacts cannot provide that exact catalogue/opening and external ledger, present the precise package decision before generation/installation.

Opening Norms/history must have explicitly approved provenance as initial inputs, not copied outputs from another engine/run. External stocks, receipts, consumption and transit are ledger-conserving. Freeze complete schema/types/NULLs/duplicates/ordinals, hashes, input dates, expected request opportunities, and canonical reference witnesses before D0. A positive witness missing from the package is a preflight blocker, not an excuse for post-run rerolls.

Do not alter current3005 fixture source/selection to run this test. Use fresh owned facilities and in-process/no-port configuration. Final3005 selection/deployment is a separate explicit gate: snapshot current selection and rollback, approve exact target/image/source/run and full required reader-layer roster, then change only the existing application service if needed. Without this gate, deliver code and integration proof and clearly say the visible3005 fixture is unchanged.

Failure rule: preserve earliest failed attempt/gate. An integration/file/preparation defect may be fixed and continued without calculation using the committed run. A failed calculation consumes a call; any extra call or revised input/semantic authority needs one explicit amendment. No autonomous fourth call. No accepting a failed variant under an unapproved waiver.

Exit: all matrix witnesses pass or exact human-approved native limitation is indexed; no required modern omission concealed. Actual call count and terminal ownership are recorded.

### M4 — Focused runtime proof and one handoff

Verify exact code/image/schema/source/configuration hashes, current/task/history readback, own terminal generation, all-eight availability and directly affected application seams. If serving change is authorized, use one finite browser check of changed consumption/completion displays; reuse all unchanged upload/review/download proofs. Confirm existing report selection/auth/MTO identities are preserved. Only a concrete attributable failure permits another affected check.

Produce `MDM_APPROVAL_DAY_HANDOFF.md`, one hash index and numbered commands for install/bind/approve/run/check/retrieve/failure handling. Include exact day/call counts, original failures, task statuses, source/domain qualifications and whether3005 serving was changed. Commit/push ONE cohesive change, verify upstream and complete the bounded goal; STOP.

## 6. Focused verification budget — acceptance criteria, not expanding test counts

Reuse existing `test_mdm_daily_input.py`, `test_nms_supplier_input.py`, `test_nms_supplier_contract.py`, `test_operational_force_capture.py`, relevant Seasonality tests and integration-preservation tests only where their seam changes. Add assertions only for missing combined-source behavior; do not mirror unchanged implementation.

Minimum affected proof:

- Complete typed approved-input reconstruction, NULL/duplicate/ordinal and exact parameter forwarding.
- One combined commit/rollback test for output plus capture/queue/task/history; retain approved requests on failure.
- One capture-cutoff case: late approval retained, captured revision conflict denied; no whole concurrency framework.
- Source/predecessor/config mismatch denial and once-only consumption/retrieval.
- Exact per-family canonical consequence matrix, with existing native receipts reused for unchanged arithmetic.
- Coherent current/task/history display and old fixture denial/default behavior intact.

For schema changes: actual Django check, `makemigrations --check`, migration plan, fresh-owned PostgreSQL migration and upgrade preservation of the exact changed tables/old columns. No fake migrations, whole-database hashing or untouched large-history rescan. Backup/rollback and write-exclusion evidence remain required. Source/build checks only for changed package components; no full regression by habit.

If a new field/formula/source conflict lacks a retained reference, inspect only that exact canonical method/SQL and its direct dependency. A second independent branch, new family, profiling exercise or producer campaign requires a scope decision. Stop verification when required exits pass.

## 7. Protected boundaries and explicit exclusions

Protect current3005 data/selection/grants/auth/frontend/MTO and optimized BPR/BTR/DBM/RRR/Buffer/Planning/Research/Guided readers.3006 is reference only. Preserve3002–4, stopped temporal-full-001, accepted calculations/inputs/seals and all failed evidence; unrelated dirty work and excluded checkouts remain untouched.

Use existing exclusively owned facilities,4GiB/twoCPU worker and existing DB limits; no new public port/resource increase/reset/prune/shared restart/borrowed namespace or restore over accepted data. New owned test databases must have verified absent names and ownership.

No scale/performance benchmark, new index campaign, full97097-pair or21-day run, old temporal continuation, production data connection, external alert/email, MTO modernisation, general logistics/BOR history work, client/GulfOil expansion, native flaw repair or UI redesign. Those are separate programme gaps.

## 8. Approval requested and monitoring contract

**Review now:** approve or amend this finite M1–M4 implementation boundary. This does not release actual days or changing3005 selection. No agent instruction or automatic monitor restart is issued by creating this artifact.

**After implementation release:** executor sets ONE goal without inferred numeric budget. MIGRATION records active M item, unmet exit, permitted files and proof before mutation. One consolidated frozen execution/serving decision remains necessary; independent code work continues while it is prepared. Do not reapprove already resolved authority.

**Monitor if released:** one compact changed-work snapshot; verify matrix completion, exact calls, source/target discipline and focused proof. Correct only evidenced scope drift, needless approval stops or omitted required flow. No healthy-work nudges or automatic next tranche. Pause at verified pushed handoff or terminal authority blocker.

Success is approval-to-modern-day completion in the declared domain. It is not unrestricted production readiness, whole-MTO acceptance or permission to release the next programme gap.
