# Production execution and offline 21-day validation — implementation plan

Prepared 7 October 2026 for human review before executor handoff.

Status: human approved for executor handoff on 7 October 2026, including the
human-operated full execution and deferred terminal presentation publication.
This supersedes the earlier fixed-90-day proposal; no duration override is required.

This is an implementation contract, not another status tracker. Record active
work, evidence, blockers and closure only in `docs/MIGRATION.md`.

## Objective and release boundary

Deliver three connected capabilities: (1) a production-oriented application
execution/publication boundary; (2) a permanent, reproducible synthetic business
scenario for the retained 1,240 SKU–location pairs over 21 execution days; and
(3) unattended PowerShell orchestration that runs modern and legacy, validates
their outputs automatically and writes reviewable artifacts.

The previous scoped smoke/publication goal is closed and pushed as `9f69467`,
following Planning/RRR checkpoint `144ea39`. Use that closure and its accepted
receipts as the baseline; do not replay accepted runs to certify this new package.
Before implementation, verify the current checkout against those commits and
identify unrelated changes. Treat this as a NEW bounded package, not continuation
of the completed smoke goal or permission to reopen the history campaign.

This phase implements and verifies the package with a fresh small trial. It
does not launch the full 1,240-pair/21-day run, automatically select that run in
3006, integrate MTO, cut over 3004, or claim whole-stack production acceptance.
The delivered runbook will provide the subsequent full-run command.

The human operates the full-run commands after package delivery. Scripts generate
logs, receipts, comparisons and summaries automatically; no manual evidence
construction is required. One unattended command runs 21 sequential days, not
one 21-day calculation transaction. Persist and validate each day's canonical
state, actions, histories and report/source outputs. Defer only expensive prepared
presentation projections and UI activation until the accepted terminal day, after
proving they are not inputs to successor calculations. Normal production still
executes and publishes one day end to end. Deliver a separate terminal publication
command that prepares, validates, seals and selects the qualified final run on
owned3006, preserving3005 and denying partial selection.

Protect 3005 as the big-data demo and preserve 3002/3003/3004, accepted F2 runs,
the two accepted smoke seals and failed history attempt evidence. Do not alter
excluded checkouts, reset/copy databases, delete volumes, restart shared Docker
or WSL, add ports/resources, redesign the frontend or change engine rules.
Calculation workers stay at 4 GiB/2 CPU, one day per fresh bounded worker.

## Approved RLT amendment and shared horizon

The controlling catalogue contract is `baseline/synthetic-rlt-4-7-v1.json`.
Its complete catalogue is
`D:/freshvcf-build/synthetic/rlt-4-7-v1/catalogue.json`, SHA256
`2ecf4e079807e00d0f809abedde1303640910ca82faeb5b8e56671b22d5de0ff`.
The artifact contains catalogue rows only; it is NOT a runnable temporal input.

| Retained RLT | Amended RLT | Pair count | Execution days per pair |
|---|---|---|---|
| 1 | 4 | 312 | 21 |
| 2 | 5 | 299 | 21 |
| 3 | 6 | 296 | 21 |
| 4 | 7 | 333 | 21 |

The deterministic shift preserves the retained randomized cohorts, identities,
other master values, NULLs and occurrence order; do not reseed RLT assignments.
Maximum population RLT is 7, and the simulation horizon is `3 * 7 = 21 days`.
ALL 1,240 pairs share the same 21 execution dates. RLT 4/5/6 pairs do not stop
after 12/15/18 days. Full daily pair coverage is therefore 26,040 pair-date facts,
separate from opening/history rows, duplicate source occurrences and parent-only
dependencies. Source-specific NULL exclusions can affect report outputs; they
must not remove a pair from the simulation input population.

Keep per-pair canonical RLT windows and the existing half-up transit formula.
The new RLTs imply base GIT durations of 2 days for RLT4, 3 for RLT5/6 and 4 for
RLT7. Regenerate and reconcile the new scenario's dated dispatch/receipt facts;
never attach the unchanged old 12-day shipment ledger to amended RLTs. Do not
modify old catalogue/input hashes, historical receipts or serving3005.

## Existing code to reuse

Qualify these owners once, then implement their exact missing differences:

- `mta/runtime/temporal.py`: `execute_day`, `record_command`, `command_state`.
- `mta/runtime/services.py`: `finish_run` and typed output readback.
- `mta/runtime/management/commands/run_temporal.py`: input binding and continuation.
- `tools/temporal_worker.py`: single-day execution, predecessor verification and
  resource-lifetime discipline. It contains historical F2-specific pins; do not
  blindly reuse those special cases as new-scenario authority.
- `parity/replay_temporal.py`: independent legacy replay, retained capture and
  `compare_day`; `parity/legacy_isolation.py`: exclusive Fresh SQL ownership.
- `parity/temporal_ledger.py`, `temporal_policy.py`, `temporal_contract.py`,
  `output_archive.py`: reconciliation, action policy and full comparisons.
- Existing prepare/activate/check daily UI management commands and source-specific
  Planning/RRR serving extensions.

Do not run extraction/import tools to re-import the engine, replace the oracle,
create a second daily boundary, or build a generic job/registry framework.

## Step 1 — Production-oriented application boundary

### Work the agent must do

1. Map the supported call path from approved input capture through `execute_day`,
   typed closing state/actions/history, source production, report preparation,
   sealing, explicit activation and readers. Identify concrete gaps relevant to
   this package. Do not begin a whole-repository cleanup or production audit.
2. Keep business state and approval consumption in the application. The script
   supplies bound inputs and invokes supported commands; it must not insert
   calculated rows, mutate completed runs, change suggestions/Norms directly,
   fabricate parity status or reconstruct report data from traces.
3. Separate application configuration from trial orchestration. Bind the owned
   instance/database, immutable input/source/configuration identities and report
   roster explicitly. Avoid ambient serving flags changing calculation profiles,
   as happened in the interrupted history trial.
4. Retain consistent MDM SKU/Location/SKU–Location capture at the canonical import
   boundary, durable revision/digest binding, exact consumed-approval handling,
   frozen retry capture and independent future approvals. No broad new MDM work.
5. Preserve idempotence, transaction/rollback ownership, authenticated actors,
   timestamps and action eligibility. Use existing run and attempt identities;
   add narrow fields/relations only when existing owners demonstrably cannot fit.
6. Calculation SUCCEEDED, parity accepted, publication READY and serving selected
   remain different states. Prepare without selection; select only a complete,
   genuinely admitted run. A failed preparation must not replace the serving run.
7. Make synthetic-only exceptions explicit and disabled outside their approved
   boundary. The two-account 3006 CAPTCHA exemption stays fixture-only; normal
   password, scope and authentication checks remain. RRR colour-band execution
   under MTO=0 is a recorded synthetic producer-gate exception, not canonical
   gating parity. Legacy comparison must apply the same scoped gate exception
   explicitly while leaving the pinned SQL formulas/source unchanged.
8. Preserve the finite approved synthetic report disposition: BOR/BOROA and
   Guided Excess rolling history are deferred, not passed. Retain genuine
   current-day computed data; unavailable endpoints must not claim empty success
   or fall back to unrelated history. Preserve documented GIT/order limitations.
   Do not introduce additional exclusions without evidence and human disposition.
9. Provide supported commands with clear exit codes and durable logs. Do not
   add scheduling, automatic UI activation, or a new background platform.

### Required proof

Focused tests cover changed input capture/retry, transaction rollback, duplicate
submission/idempotence, predecessor/source mismatch, incomplete publication,
selection denial and exception-off/default protection. Reuse passing smoke proof.
Run affected Django checks, migration checks/plans, real owned PostgreSQL migration
and fresh-schema verification where schema changed, and affected builds. Verify
deployed code/image identity and unchanged protected services for any deployment.

Exit: the supported application commands can execute, persist, prepare and safely
admit a new owned run without relying on agent actions or legacy outputs.
This is production-oriented code readiness for these boundaries, not a blanket
security, performance, deployment or whole-application production certification.

## Step 2 — Permanent synthetic business scenario

### Deliverables

Create `docs/SYNTHETIC_TEMPORAL_BUSINESS_CONTRACT.md`, a versioned scenario
specification and deterministic generator/validator under existing tool ownership.
Store the small specification and source pins in Git. Generated bulk data and
evidence belong under `D:/freshvcf-build`, registered by manifest/hash.

### Work the agent must do

1. Reuse the exact registered 200-SKU/20-location catalogue, names, hierarchy,
   scopes, parent relationships and 1,240 business pairs. Pin catalogue hashes,
   pair occurrence/order and parent dependencies. Do not regenerate identities,
   silently enforce uniqueness or mistake pair count for SKU count.
2. Preserve retained input bytes. Create a separately versioned 21-day artifact
   with declared lineage; neither relabel nor extend the frozen 12-day artifact
   in place. Qualify existing generator logic once, retaining compatible behavior.
3. Use the approved versioned catalogue `baseline/synthetic-rlt-4-7-v1.json`
   and its pinned external catalogue. Its mapping shifts retained RLT cohorts
   1->4, 2->5, 3->6 and 4->7 without reseeding or changing other master fields.
   The full 1,240-pair population has maximum RLT 7 days, so the shared simulation
   horizon is `3 * max(population.RLT) = 21 days`. EVERY pair executes all 21
   consecutive dates, including RLT 4/5/6 pairs; never assign per-pair horizons
   of 12/15/18 days. Freeze opening/first/last dates, units, seed/calendar and
   source order. Preserve the existing 3-times-maximum validation rather than
   introducing a fixed-90-day override or changing old receipts. Canonical
   per-pair calculation windows remain governed by that pair's RLT. A short
   acceptance trial is an explicit prefix of the validated full artifact; it
   does not redefine the full population's horizon.
4. Describe a coherent replenishment business case using retained attributes:
   base demand, declared weekly pattern, bounded seasonality, intermittent demand,
   quiet days and named demand shocks. State exact formulas, coefficients,
   deterministic cohort assignment and seed behavior. Do not use an implicit
   random default or silently resample until reports look favorable.
5. Define supply as external facts: root supplier availability, dispatch rules,
   parent/child flows, lot/quantity rules and receipt timing. Keep it independent
   of either engine's outputs. If a rule requires live computed orders, identify
   that feedback boundary and obtain a separate contract decision; do not use
   modern output to generate both engines' future inputs.
6. Maintain an inventory/shipment ledger at every pair/day. Receipts occur on
   the declared receipt date; quantities stay in GIT only across the declared
   dispatch-to-receipt interval. Preserve `max(1, (RLT + 1) // 2)` half-up transit
   rounding in the approved base scenario. Do not add delays that violate that
   contract; any separate delay scenario needs explicit versioned authorization.
7. Reconcile stock and GIT using exact event boundaries:
   closing stock = opening stock + receipts - realized consumption;
   closing GIT = opening GIT + dispatches - transit receipts.
   Parent outbound and child inbound quantities must reconcile, with explicit
   external source/sink ownership. Do not invent unledgered stock top-ups.
8. Distinguish requested demand, realized consumption and unserved demand where
   applicable. If stock is insufficient, declare the supported business treatment
   rather than clipping quantities silently. Generate only the input fields
   actually consumed by canonical ingestion, preserving NULLs and omissions.
9. Pin the approved shipment metadata conventions and deterministic transporter
   mapping; never merge shipment facts with the aggregate GIT report population.
10. Declare historical opening coverage separately from future facts. Reuse a
    qualified retained opening where compatible; if new warm-up facts are needed,
    specify their generation/source/date coverage. Do not seed computed Norms,
    recommendations, suspension/cooling state or Excess history as external facts.
11. Version the action policy explicitly. Reuse the retained real Apply/Sleep
    policy where compatible, using each engine's own suggestions. If the longer
    run requires a different business decision policy, present that exact change
    for approval rather than inventing one.
12. Produce a compact business preview: cohort definitions, daily totals, demand
    and receipts, stock/GIT trajectories and expected event coverage. These are
    input characteristics, not promised calculated report outcomes. Present all
    substantive unresolved assumptions together before freezing the scenario.
    Use named numeric parameters rather than vague instructions such as
    "realistic" or "random". Plan approval authorizes implementation of this
    package; it does not silently approve an unspecified demand distribution,
    new action policy or transit-delay exception. Freeze any material choices
    through one consolidated scenario decision, without serial approval loops.
13. Freeze the approved specification, seed, generator/version, catalogue,
    opening, daily facts, shipment ledger, controls/actions and hashes. Record
    the complete roster/counts and parent dependencies. Never repeat short facts
    to reach 21 days. A second generation from the same specification must match.
    The RLT assignments are already frozen by the approved catalogue mapping;
    do not draw them again.

### Required proof

Validate all 1,240 pairs and all 21 days, plus required opening history; quantity
conservation, no undeclared identities, date coverage, shipment identity uniqueness,
GIT duration, event ordering, types/NULLs and declared occurrences. Include tests
rejecting tampered hashes, broken balances, missed/duplicate days, wrong receipts
and altered catalogue. Keep existing frozen-artifact validation passing.
Explicitly assert RLT min4/max7, the declared 312/299/296/333 distribution, all
26,040 required pair-date memberships and one shared end date for all cohorts.
Test rejection of a per-pair `3 * RLT` truncation and any fixed-90-day override.

Exit: a reviewed and frozen business contract and immutable complete input package
exist. Its input validation PASS does not certify calculation parity or UI coverage.

## Step 3 — Unattended execution, parity and evidence

### Proposed deliverables

- `tools/Invoke-TemporalValidation.ps1`: finite modern/legacy orchestration.
- `tools/Test-TemporalValidationPreflight.ps1`: read-only ownership/config checks.
- `tools/Get-TemporalValidationSummary.ps1`: compact status from durable receipts.
- `tools/Publish-TemporalValidationTerminal.ps1`: explicit admitted terminal
  preparation/publication/selection for the human-operated full run.
- `docs/OFFLINE_TEMPORAL_VALIDATION_RUNBOOK.md`: verified commands, recovery and
  evidence interpretation, including the later full 21-day command.

These filenames describe proposed additions, not commands already available.
Reuse Python comparison and worker owners; PowerShell orchestrates rather than
reimplementing business rules or writing a second comparison engine.

### Work the agent must do

1. Expose explicit scenario manifest, execution ID, date range/through day,
   engine mode, evidence root and resume parameters. Keep secrets outside Git
   and command output. Validate paths and owned database/resource identity.
2. Preflight the source/input/config hashes, catalogue/pair population, all-day
   ledger, Python/SQL/PostgreSQL dependencies, exclusive legacy lease, normal
   resource limits and adequate measured storage. A running SQL process alone
   is not a healthy oracle. Refuse borrowed/shared/live databases or changed pins.
3. Allocate a new owned modern timeline and unique `VFTEST_Fresh_*` legacy
   namespace. Provision only demonstrably new owned resources. Never reset
   accepted namespaces or serving databases. Keep accepted smoke state intact.
4. Provide combined, modern-only, legacy-only and compare-retained modes with
   matched input/attempt identities. Default combined mode computes each day in
   modern, computes the same day independently in legacy, validates and compares
   both, then permits the next day. Stop the combined run at the first failure.
   Separate engine runs never imply parity until matching captures are compared.
5. Each engine uses its own opening and durable predecessor. Execute one modern
   day through `execute_day`; execute canonical legacy stage order in the owned
   oracle. Apply real workflow actions using each engine's own results. No copying
   closing states or action selections between engines to force convergence.
6. Preserve the complete comparison roster: eight day boundaries, calculation
   outputs, master/control effects, emitted reports and action/post-action state;
   the retained automatic-action path currently produces 31 comparisons. Preserve
   full values, NULLs, types, duplicate multiplicity and native ordering contracts.
   Count-only success, hidden differing fields and invented tie-breaks are forbidden.
7. Include daily producer/source acceptance for the qualified roster. Link
   core calculation comparisons, RRR gate-exception formula proof, source checksum,
   terminal recipe/readiness checks and consumer checks separately. A core PASS
   cannot stand in for an unverified report reader. Preserve every daily source
   or history needed by terminal readers. Defer expensive prepared presentation
   projections after proving they are not successor calculation inputs. Do not
   launch 21 browser
   sessions or a new performance matrix; terminal usable UI verification is finite.
8. Keep calculation status, parity status, report preparation and later serving
   selection distinct. Do not mark parity or READY by script fiat. Do not change
   selected 3006 on every day. Preparation may remain unselected; later terminal
   selection uses the existing complete-roster guards explicitly.
9. Write immutable per-attempt logs/captures/receipts and atomic summary updates.
   Record dates, run IDs, own predecessor IDs, source/image/config/input hashes,
   output/readback checksums, comparison results, exception scope and resource
   failures. Large complete captures stay compressed; JSON summaries are metadata.
10. Write a final JSON summary and readable Markdown report even on failure:
    requested/accepted day ranges, pair/SKU/location counts, first failed stage,
    exact differences and capture paths, elapsed execution, exceptions/deferred
    reports, publication disposition and next safe command. Use meaningful
    nonzero exits for input/config failure, engine failure and parity divergence.
11. Resume only from a verified contiguous accepted prefix with matching pins.
    If modern succeeded but legacy/comparison failed, reuse the immutable modern
    capture where valid rather than recompute it. Preserve the failed attempt;
    create a new explicit attempt for a legitimate retry. Reject changed code,
    input, policy or predecessor identity instead of silently adopting it.
12. Handle process interruption honestly: reconcile committed rows and actual
    run state, mark only the interrupted owned attempt appropriately and preserve
    evidence. No blind timeout retry, process-wide/shared service kill, resource
    increase or database cleanup as a recovery strategy.

### Package acceptance trial

Use a fresh deterministic ten-pair subset from the SAME frozen 21-day scenario,
with explicit parent dependencies, over three consecutive execution days. This
is a new runner trial, not a replay of the accepted June6–7 smoke. Choose retained
identities to cover supported receipts/GIT/consumption and action boundaries;
report legitimately unexercised branches, never manufacture computed positivity.
The three-day trial is only an execution prefix of the full validated scenario.
Its length does not alter the 21-day full horizon, even if its selected pairs do
not include RLT7. Select representatives from all four RLT cohorts where feasible.
A newly dispatched RLT7 shipment takes four days to arrive; do not shorten transit
to force its receipt into this trial. Prove such ledger timing with focused input
validation and disclose what the three-day engine trial did not exercise.

Run both engines and automatic comparisons; verify durable next opening,
publication/readiness and representative terminal BPR/BTR/DBM/RRR reads. Exercise
one controlled orchestration failure and resume using a fake worker/owned small
trial where feasible; prove no duplicate accepted execution and changed-pin denial.
Run required affected tests/migrations/build checks once; repeat only after a real
fix or invalid observer. Preserve failures. A three-day pass is package acceptance,
not 21-day acceptance, scale-performance proof or all-workflow certification.

## Final handoff and stopping rules

One primary agent owns integration. Use one bounded independent review only
where execution truth, security or migration changes warrant it; do not create
serial planning/review teams. No numeric goal budget without direct human input.

Before handoff, commit and push the substantive integrated package; record exact
commit/image/input/scenario identities, checks and trial evidence. Deliver verified
PowerShell invocations for preflight, small trial, full 21 days, resume and summary.
Do not show placeholder arguments as runnable commands. Explain required private
configuration without exposing credentials. Include restoration of temporary
fixture exceptions and explicit terminal-publication instructions.

The agent must STOP after package acceptance and handoff. Full 21-day execution
is a subsequent offline action. Its eventual result is accepted only from complete
durable receipts and comparisons, followed by the agreed finite UI verification.
Unresolved business/input assumptions require one consolidated decision; don't
substitute a new source or expand into a history-reconstruction campaign.

## Approved executor handoff

Implement this plan as one new bounded goal, without an inferred numeric budget.
The completed smoke goal remains completed. Read this plan, the approved RLT
contract, current `AGENTS.md` and the relevant daily-publication guide; use
`docs/MIGRATION.md` as the sole status tracker. Establish the active item, unmet
exit, permitted mutation boundary and proof before changes. Qualify existing
owners once, then implement the three connected deliverables in a coherent pass.

Use the amended catalogue exactly: RLT4–7, fixed retained cohort mapping and
one 21-day horizon for EVERY one of the 1,240 pairs. Keep canonical calculations
and accepted artifacts unchanged. Settle substantive business input assumptions
together, freeze the scenario, and generate a complete ledger-conserving input
package. Deliver PowerShell scripts that execute modern and legacy independently,
run full automatic parity and write durable per-day/final evidence. Keep source,
action, input and predecessor guards; stop on the first actual failure.

Perform only the fresh ten-pair/three-day acceptance trial and focused changed
boundary checks. Preserve existing serving selection during execution; any
terminal trial UI verification must use an explicit owned admission/selection
step with recorded previous selection and restoration, without replacing the
big-data demo or accepted smoke records. No extra ports or shared restarts.

Commit and push the integrated delivery, provide the actual verified preflight,
trial, full21-day, resume and summary commands, identify remaining limitations
and then STOP. Do not launch the full1,240-pair21-day run, integrate MTO, claim
whole-stack production acceptance, or resume Guided Excess history reproduction.
