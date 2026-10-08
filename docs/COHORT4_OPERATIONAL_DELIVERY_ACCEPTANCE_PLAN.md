# Cohort 4 — operational delivery and qualified acceptance

Prepared 9 October 2026. D1–D4 approved by the direct human reply in controller
turn01a11d57-4b23-7691-9433-e058daed41f3, verified before implementation.
Only the bounded packaging goal is released; no business run or deployment.
MIGRATION.md remains the sole status tracker; this document is the finite contract.

## Next logical cohort and fixed delivery checklist

Current Git and MIGRATION confirm Cohorts1–3 closed. P1–P5 are the five exits
inside Cohort3; they are not five completed cohorts. Cohort4 is the next unmet
delivery boundary. Do not invent a Cohort5/6 or skip the operational package.

Complete only these four deliverables, in order:
1. One command contract mapping input/predecessor/actions -> run_daily ->
   cohort2_operational -> prepare_daily_ui -> activation/selection -> readers.
   Each step must name its inputs, outputs, failure stop and exact supported domain.
2. One reproducible runtime package with pinned dependencies and private config
   template, preserving strict defaults and current services.
3. One executable operator runbook covering normal execution, zero-calculation
   checks, failed-attempt handling and existing repair/restore procedures.
4. One evidence-backed readiness matrix, cohesive commit/push and stop.

Targeted code review confirms run_daily requires a frozen artifact SHA, exact MDM
binding, own predecessor, revision and explicit remark horizon. It calls execute_day
once and leaves publication unselected. check_daily_selection still requires
independent parity PASS/PASS_WITH_LEGACY_FLAWS. Cohort3's qualified policy therefore
does not already provide a general production CLI selection contract. D1 must name
this exact gap; do not silently change that check or hard-code further run owners.
If a general admission change is required, present its exact policy decision before
dependent implementation. Packaging cannot remove the active-NMS/approval/input gaps.

No new calculation or acceptance sweep is part of this plan. Only missing packaging
or command integration is implemented; reuse completed business/report proofs.
Any proposed run of daily external inputs is a subsequent, separately approved
correctness acceptance step after its required input and admission gates are closed.

## Reviewed predecessor

Cohort 3 commit 44c350b0fc201f832393ca02664e3b17b07143fd equals upstream.
Controller independently verified all96 evidence hashes and proof image
sha256:17f7568f65fcbbb78c3ecfd694b8ac4b340f0a78c417d2e9d7691e11f221bc2d.
Both accepted dates have18 prepared layers, authenticated readers, four Pick
downloads, restart/readmission and denial/prior-valid-state evidence.
Goal complete; executor stopped. This is qualified closure, not full readiness.

Two original consumer receipts remain FAILED with the human-approved503 blocks:
order-fulfillment custom ambiguous canonical ranking and invalid combined GIT
child SQL. Preserve those failures; no legacy repair. Two pre-existing history
test-double errors remain disclosed, not a passing whole-repository suite.

## Objective and acceptance claim

Deliver one reproducible operational package and executable operator procedure
for the supported generic daily path, with exact readiness gates and qualifications.
Use existing services/commands and accepted Cohort1–3 receipts. No discovery campaign,
new scheduler/framework, UI/report work or producer expansion.

Cohort4 completion may establish **qualified operational packaging readiness**.
It cannot establish unrestricted migrated-stack production readiness while the
explicit gaps below remain. It does not release real-system connection, temporal
runs or cutover. An arbitrary daily input must never inherit the two-owner policy.

## Finite dependency-ordered delivery map

| Item | Concrete gap and source | Smallest work after approval | Required exit |
|---|---|---|---|
| D1 — Freeze supported domain and command contract | Cohort3 admission is pinned to two UUID/date/digest tuples; native flag0 and parity_summary{} remain. Current runbook audits receipts rather than executing a general production day. Existing run_daily, prepare_daily_ui, activate_daily_ui, check_daily_selection and cohort2_operational are the command owners. | Map ONLY these existing command boundaries into one input-to-calculation-to-operations-to-preparation-to-admission procedure. Identify exact required external input/config/action/predecessor/file/credential owners and fail gates from existing plans and code. Separate reusable generic commands from two-owner acceptance tooling. | One fixed command/exit matrix, with each step executable, qualified or BLOCKED for a named reason. No inferred sanitation, empty queues, hierarchy or admission defaults. No second tracker or broad inventory. |
| D2 — Reproducible package | Cohort3 proof image combines runtime/auth dependencies; handoff explicitly excludes production packaging. | Pin code/image/dependency/tool/config identities and minimal private deployment configuration template using existing packaging. Secrets remain external. Include existing command help/preflight and exact schema requirements. Change code only for an evidenced missing packaging/forwarding dependency; preserve strict admission defaults. | Clean owned build/import/Django/schema verification where affected; package source equals delivered code. No live service or ports. If a clean build cannot reproduce, retain failure and fix only that dependency. No image matrix or dependency modernization. |
| D3 — Operator procedure and recovery | Prior cohorts prove owned operations, files, backups, reader admission and recovery separately. No single operator procedure clearly distinguishes new-day execution from zero-calculation retrieval/repair and failed/prior-publication truth. | Compose one numbered runbook using existing commands and accepted evidence: inputs/preflight; explicit day invocation boundary; operations; preparation; check/admission; reader verification; failure stop; explicit retry/repair; backup/restore ownership; restart. Document actual return/status handling and exact supported arguments. | Audit the command chain and no-calculation check path in owned facilities. Reuse passing runtime/restore/HTTP receipts; do not rerun calculations, backup/restore campaigns, consumer sweeps or fabricate generic success from retained-owner audits. General execution remains BLOCKED wherever admission/input gates are unresolved. |
| D4 — Qualified final handoff | Cohort names could be mistaken for whole-product acceptance. C1–C6 and additional gaps need one honest disposition. | Reconcile existing assessment and MIGRATION into complete/qualified/missing implementation/missing proof/decision/deferred rows, citing existing evidence. Consolidate exact release/input decisions once. Produce package identities, actual commands and limits; one cohesive substantive commit/push. | Every readiness claim has evidence; all remaining gaps below retain a named completion requirement. Verify upstream, close bounded goal and STOP. No automatic next gap implementation or real daily run. |

The approved execution uses ONE bounded goal without numericbudget. Before mutation
record active D item, unmet exit, boundary and proof in MIGRATION. Reuse passed
proofs and debug only an attributable failure. Do not create component commits.

## Known readiness gaps — retained, not silently absorbed into packaging

| Reference | Remaining gap / business consequence | Required closure beyond this package |
|---|---|---|
| C1 and additional admission gap | Inactive NMS only, native batch flag0; populated SOB/twoMOQ approval workflows and populated upload-log producers unqualified. Two-owner consumption policy cannot admit arbitrary daily runs. | Source-mapped enabled-workflow implementation/proof and an explicit supported general completion/admission contract. No blanket flag waiver or fake parity. |
| C1/configuration | Empty sanitation/critical-file opening is a declared synthetic limitation, not recovered deployment workload. Real missing-file resolver and deployment bindings unproved. | Exact deployment input/config owner and focused supported-case proof; no invented defaults. |
| C2/profile/history | Client FG-history and GulfOil calculated attributes remain opt-in, not universal generic requirements. BOR/BOROA, separate RRR colour and GuidedExcess history/source boundaries remain. | Keep exact exclusions; any proposed expansion requires its own finite source contract, not this cohort. |
| C3 | File/ZIP paths and ordering have accepted narrow qualifications; arbitrary configured outputs not automatically certified. | Operator config must enumerate enabled supported files and reject unsupported ones. Preserve exact CSV/ZIP exceptions. |
| C4 | Fourteen local alert dispositions are proved; actual external delivery is not. | Explicit transport/recipient configuration and separately approved delivery verification, if required by deployment. No email sent by Cohort4. |
| C5 | Owned SQL fixtures and PG logical restore proved with exact eleven CHECK-cast qualifications; no general environment restore certification. | Document exact supported methods/resources/qualification and deployment backup ownership. No new restore campaign. |
| C6 | Completion/successor and prior-publication truth qualified; native full-batch flag remains false for inactive NMS. | General acceptance must verify actual enabled critical operations and denied/failure states, not rename qualified consumption full completion. |
| Additional workflow proof | Sleep was not exercised in these two-date trials. | Reconcile existing valid real workflow proof once; if inadequate, retain exact missing proof and propose the smallest separate correctness exercise. No invented action. |
| Additional application scope | Two approved503 routes, whole application/direct-port MTO acceptance and deployment/cutover unproved. | Preserve route denials; named later application/release gates. No UI campaign or MTO changes here. |
| Additional scale/parity | Full independent legacy daily parity, production workload/capacity and arbitrary daily-input continuity are not established by small two-date proofs. | Separate bounded acceptance proposal where needed; no benchmark or million-capacity claim. |

## Approved execution boundary for Cohort4

Only packaging/config-template/runbook/integration-check changes plus focused
affected checks. ZERO new execute_day or legacy engine calls. Existing accepted
owners are read-only inputs; no trace backfill or copied calculated state.
Read-only retained audits may run once where required; no repeated passing sweeps.
Schema changes only for an evidenced required dependency, with actual migration
and fresh owned PG proof. No live database copies or resets.

Protect serving3002–6/selections, stopped temporal-full-001/artifacts, canonical
SQL/formulas/NULLduplicates/order/actions, all accepted proofs, GulfOil boundary,
excluded checkouts and unrelated dirty work. Normal4GiB/twoCPU/existing DBlimits;
no port, resource increase, sharedrestart/prune/reset/borrow/cutover.

If proving a general operator command needs a new business-day run or broader
admission policy, stop at ONE concrete proposal: exact inputs/configuration,
scenario/count, isolated owners, acceptance exits and limitations. Approval of
this packaging plan alone would not authorize that execution or policy waiver.

## Approval and stop

Verified direct human approval covers ONLY D1–D4 qualified operational packaging
above, not an unconditional production-ready declaration. At the verified cohesive
push or exact terminal blocker, stop and await further release.
