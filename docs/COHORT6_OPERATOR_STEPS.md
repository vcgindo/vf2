# Cohort6 operator steps

**Current instruction: STOP. Approval B has not been granted. Do not execute the run command.**
The prerequisite delivery contains no business-day execution. MIGRATION.md is the only status tracker.

After the human explicitly approves request SHA256
`a34bb2b1c837009ff81128cd37be5ba1c4a6d79816379bb266f5267bddf3748b`, execute steps1–3 below once, in order.
Do not copy Markdown fence lines into PowerShell.

1. Open PowerShell and run this exact block. It checks the frozen request and private
   Compose file, then supplies the approved request identity. It does not calculate.

```powershell
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath 'F:\freshvcf'
$requestPath = 'D:\freshvcf-build\evidence\cohort6-prerequisites-20261009-001\request-freeze\COHORT6_FROZEN_EXECUTION_REQUEST.json'
$composePath = 'D:\freshvcf-build\evidence\cohort6-prerequisites-20261009-001\compose-execution.private.json'
if ((Get-FileHash -LiteralPath $requestPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne 'a34bb2b1c837009ff81128cd37be5ba1c4a6d79816379bb266f5267bddf3748b') { throw 'Frozen request differs. STOP.' }
if ((Get-FileHash -LiteralPath $composePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne '57e8d32fd27c03e6761e14e1dbd29676f2414f65dc1dc30657ed624c96f2840b') { throw 'Execution configuration differs. STOP.' }
$env:COHORT6_APPROVAL_B_REQUEST_SHA256 = 'a34bb2b1c837009ff81128cd37be5ba1c4a6d79816379bb266f5267bddf3748b'
```

2. In the same PowerShell session, execute this block once. Keep the terminal open
   until it exits. A nonzero exit means STOP; retain the output and do not rerun it.

```powershell
docker compose -f $composePath run --rm --no-deps worker
if ($LASTEXITCODE -ne 0) { throw 'Cohort6 stopped on a failure. Preserve receipts; do not retry.' }
```

3. Read the terminal receipt, report its result, and STOP. No service-selection,
   restart, cleanup, recovery, benchmark or third-date command follows.

```powershell
Get-Content -LiteralPath 'D:\freshvcf-build\evidence\cohort6-prerequisites-20261009-001\execution\two-date-001\terminal-receipts.json'
```

The packaged `packaging/cohort6/execute-approved.sh` performs the fixed sequence:

1. Verify approved request identity, create a new output directory and verify fixed input hashes.
2. Verify the existing MDM installation receipt. Never reinstall it.
3. Invoke June6 `run_daily` once with the frozen source/profile bindings.
4. Bind its hierarchy and authenticate actor2 through real password login/JWT;
   construct and execute only its eligible historical-policy actions.
5. Bind/register the shared configuration from June6's exact input digest;
   materialize/check O1–O9 using the approved day-one openings.
6. Prepare reports, issue final acceptance and check selection without applying it.
   Verify all three receipts before continuing.
7. Invoke June7 once using June6's exact run as predecessor.
8. Bind June7 hierarchy, authenticate and execute its own eligible actions.
9. Materialize/check operations using June6's attempt and the same configuration;
   prepare, accept and check June7 without activation.
10. Write the receipt hash index and stop.

Every command runs in the pinned image with `tools.cohort6_settings`, inside one
4GiB/two-CPU worker on the existing owned network, with no published port and
restart disabled. Each Python command exits before the next starts. The script
refuses an existing output directory and has no retry loop. A failed daily command
consumes its one invocation. Save every failure and earlier receipt.

Operational materialization includes its declared O8 backup/qualified restore.
No separate backup campaign or consumer/browser campaign is part of these steps.
The source database is `fresh_cohort6_20261009_001`; serving3002–3006 stay unchanged.
The dedicated restore role alone has CREATEDB. Application and reader roles do not.
Credential values remain in the private configuration; never paste them into chat.

Keep all qualifications in the frozen request, including native flag0, two blocked
503 routes, Pick tied-allocation/export-order limits and eleven CHECK-cast restore
qualification. This handoff does not claim unrestricted readiness or exact parity
for qualified behavior. The retained case has no Sleep target.
