# Cohort5 qualified operational admission

Delivered scope: A1–A4 of COHORT5_GENERAL_OPERATIONAL_ADMISSION_PLAN.md under
the direct approval of supported-synthetic-operational-v1. MIGRATION.md is the
sole status tracker. This is reusable admission implementation with focused
fixture proof, not acceptance of a new business-day run or full legacy parity.

## What changed

`accept_daily_operational` verifies exact registered input and finalization bytes,
typed MDM installation/capture/consumption, own predecessor/actions, native
completion, explicit operational openings, O1–O9 effects/files/backup receipts,
all eighteen prepared layers, native remark/request captures and access. It then
creates OperationalAcceptance and matching DailyUiActivation in one transaction.
The receipt binds code, input/profile/revision/output, source/configuration,
operation/repair lineage, predecessor receipt/output, actions, publication seal,
access and BTR generation. Exact retries reverify and reuse; any changed identity
denies. No calculation or parity row is rewritten.

`check_daily_selection` emits a coherent explicit tuple only after verification.
Startup revalidates native owners; requests compare bound identities. The blank
operational-policy default still requires independent parity. The old two-owner
Cohort3 policy is separate and cannot be mixed with this mode. Missing populations
remain unavailable; no source omission or arbitrary input registration was added.

## Proof and its limits

- 23 admission tests pass in admission-a004.log. They cover atomic receipt/access,
  rollback, append-only/deferred SQL guards, wrong/partial owners, exact retry,
  predecessor receipt/output, repair graphs, source/profile/opening drift,
  explicit-policy conflicts, native flag/date qualification, all-layer verifier
  dispatch, failed-candidate prior-selection preservation and startup/request denial.
- 11 affected tests pass in affected-regression.log: six existing strict access
  activation cases and five typed MDM capture/installation/consumption cases.
- An exclusively owned empty PostgreSQL database migrated through0097, then
  0098–0100 using real migrations. Django check, drift and final migration plan
  pass. Final database proof records zero run/acceptance/activation rows after
  fixture rollback. No execute_day or legacy engine was invoked.
- Persistence fixtures mock the full expensive native candidate verifier while
  exercising real PostgreSQL guards and transactions. Protocol tests exercise
  dispatch/failure propagation with injected validators; frozen-input and native
  flag tests exercise the actual comparators against declared fixtures. These are
  not a substitute for a future real-owner end-to-end acceptance. Existing
  Cohort1–4 producer/consumer evidence is reused, not rerun or extended.
- admission-a001.log retains an initial retry-test expectation failure; the test
  had held an obsolete mocked snapshot. The corrected fixture and all subsequent
  logs remain indexed. Earlier strict failures and baseline test-double failures
  remain unchanged. No full-suite PASS is claimed.

Proof root: D:/freshvcf-build/evidence/cohort5-20261009-001. The JSON evidence index
pins logs, harness, sanitized resource descriptor and exact source overlay. Proof
used the immutable Cohort4 image
sha256:0a8ca22f471386ec6ce8dd3e59cd3fb5b1f5e56cfc525e32a6f30e3a2adb5dff with read-only
Cohort5 source mounts, four GiB/two CPUs, restart=no and no host ports. The old
Cohort4 image alone does not contain this code. A future deployment must package
this delivered revision; no serving image or service was replaced. The private
compose contains credentials, is excluded from the index/Git and must not be shared.

A separate no-profile child PowerShell audit attempt could not resolve Get-FileHash;
its failed log is retained. The exact numbered blocks passed in the working
PowerShell session (operator-audit.log); this was a shell-tool availability issue.

## Privilege boundary

Migration0100 requires the dedicated `fresh_operational_acceptor` role to insert
receipts. packaging/cohort5/offline-issuer.sql defines its database privileges;
it creates no login, credential or membership grant. An ordinary nonmember
session cannot assume it, and a custom GUC without a receipt cannot activate.
Receipt/activation must commit together. Already activated owners cannot be
retroactively labelled operationally accepted.

This is an offline trusted-verifier boundary, not protection from a database
owner/superuser who can alter schema or grants. Serving credentials must be
nonowners/nonsuperusers and not members of the issuer role. Deployment-specific
credential separation remains a prerequisite for later serving release; existing
serving credentials and permissions were not changed. Only the owned proof DB
received the new migrations/role table grants; no role membership was granted.

## Supported and held domain

| Boundary | Disposition |
|---|---|
| Registered synthetic artifact/current installer, inactive NMS, generic finalization, exact O1–O9 and 18 core layers | Implemented reusable verification; focused fixture proof only |
| Native IsBatchFileExecuted=0 | Preserved; explicitly qualified inactive critical skips, never full-batch PASS |
| Independent parity | Unchanged strict default; no synthetic parity PASS |
| Remarks/requests, openings/history/logs | Actual typed captures and explicit provenance required; no inferred empties |
| Four export ordering, Pick tied allocation, eleven restore CHECK casts | Prior exact bounded qualifications retained; no extension |
| Order-fulfillment custom / combined GIT child | Two existing 503 contracts remain blocked; original FAILED receipts preserved |
| BOR/BOROA and history expansion | Excluded; no new positive coverage claim |
| Arbitrary real input, active NMS, populated SOB/MOQ approvals/upload producers, client/sanitation, alert transport, new Sleep scenarios | Unsupported and held |
| New real day, full temporal continuation, benchmark, whole application/MTO acceptance, serving/cutover | UNPROVED and held |

## Smallest subsequent correctness proposal — not released

A later proposal should freeze one complete input/configuration package for exactly
two consecutive owned dates from the currently registered artifact: first an
explicit root, then its own successor/actions. Before requesting execution, pin
artifact/finalization bytes, complete native source/capture/opening populations,
MDM/config/tool/access digests, operation requests, retained Apply/Sleep policy
and unique run/attempt revisions. Do not silently change the registered artifact
or omit missing populations. If it cannot meet this approved policy, report the
exact input blocker and request that disposition rather than running.

Propose one bounded worker per date, four GiB/two CPUs, a separately approved
owned database/resource, no ports or serving selection. Exits: actual execute_day,
typed readback and consumption; complete O1–O9; eighteen layers; atomic operational
receipt/access; strict-default denial; exact retry without recalculation; own
successor receipt/action/source linkage and coherent selection-check output.
Stop after a failed first-date gate; do not run the successor. This describes the
smallest future acceptance shape only: no input package or calculation budget is
released by Cohort5, and none of these dates was executed here.
