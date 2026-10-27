# Step3 action guard qualification — 27 October 2026

Evidence checkpoint only. The sole status authority is
`F:/freshvcf/docs/handoff-3005/TRACKER.md`.

Application checkpoint `36c33f66f825299a0b3796ba6d1496c13cc3d6c3`, packaged image
`sha256:730ca68dbd2c8870109d6f8d52379b8ee0c6491e1f5ef10ac063d38af0627e84`.
The accompanying JSON index pins all underlying evidence files by SHA256.

## Qualified boundary

Both existing Step3 BPR and DBM test databases passed:

- Actual packaged consumed 0237 → 0238 migration plan, injected rollback,
  committed transition, exact retry and runtime-role startup/read checks.
- Complete preservation of 1,130 typed tables in each database, original
  publication files, registration, accepted phases and selected read identity.
- Real runtime Apply, remark and Sleep writers with refreshed reads and forced
  deferred constraints, inside deliberately rolled-back outer transactions.
- Stale actor, stale action revision, altered PostBPR locator and failure after
  refreshed selection all rejected or rolled back as required.

The native action trials preserved the original positive browser targets.
PostgreSQL sequence allocations may advance during aborted transactions; these
gaps were recorded and no sequence was reset. These checks do not establish
committed action durability, authenticated gateway permissions, final browser
acceptance or latency acceptance.

## Remaining execution compatibility problem

Inspection-only PostBPR and PostDBM commands on the corrected image both refuse
`Captured placement request or implementation differs`. No continuation ran.
The original captures bind execution to `18b9da4d`; the corrected reader is
`36c33f66`. `runtime_report_request.validate_request` recomputes execution
compatibility from the actual current native release. This validation also
participates in claim, registered-request and downstream publication paths.

The consumed-schema and reader compatibility profiles deliberately do not grant
execution compatibility. Running the old image merely because its inspection
passes would not establish its authority on schema 0238: its old activation
describes schema 0237. Replacing strict execution validation with read-only
validation, changing frozen requests or spoofing native identity is unacceptable.

Recommended next boundary: a finite, run-bound execution compatibility profile
which independently verifies unchanged original producer dependencies, the
actual current release and admitted schema, immutable capture/registration,
accepted phase chain and current action revision. Retain original execution
digests in attempts and receipts. New captures retain strict current-build
validation. This requires a separately qualified source/build extension; it is
not implemented or authorized by the single-build storage approval.

## Resources and serving

Post-qualification accounting is 5,410,095,182 bytes including the 512 MiB
reserve, leaving 204,672,370 bytes under the approved 5.25 GiB cap. Every old
image, database and receipt remains. The original 8080 stack is serving;
no replacement window, new database, auth build, frontend/MTO change or
continuation occurred.
