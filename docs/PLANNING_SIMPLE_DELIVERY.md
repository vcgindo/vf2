# Planning single-response delivery

This design supersedes the reversed Planning cache/identity design in
70bc43f. The selective reversal is84ff87d; retained evidence and sealed
contribution tables are preserved. Status belongs only in MIGRATION.md.

The existing authenticated GetPlanningDataCount returns all ten original count
fields and businessDate in its response body. Each entry and quadrant return
requests it once. The screen renders that response directly, with no Planning
identity/date request, query cache, revision protocol or background validation.

The reader validates the current fixture source, existing dependency receipts,
BTR generation and immutable contribution guards. It reads the exact accepted
producer recipe189dd5148e1c9b4e13eb33a285ae666823925d4bead69e583d670745bf01ba9d
and applies current actor permissions through the existing scope resolver.
The latest human requirement adds summary population to the existing daily
reporting preparation command. It does not add another daily framework or any
engine input. The exact retained additive schema declarations are restored;
the already-applied PostgreSQL migration plan is empty.

After execute_day commits and the existing required report layers are sealed,
prepare_daily_ui prepares the summary with an atomic, idempotent write. A failed
summary propagates failure and leaves a retained failed attempt. Serving admission
also requires the matching summary; the base publication seal stays unchanged.
The daily identity includes the base publication seal, dependency receipts,
transit metadata, producer recipe, source and business date. Reads retain the
existing Planning actor/hierarchy admission before applying current scopes.

Operator sequence:

1. Complete the already-authorized daily execution and acceptance through the
   existing daily operator workflow. This delivery authorizes no new day calls.
2. Before selecting that reporting generation, in its owned configured runtime,
   execute `python manage.py prepare_daily_ui --run-id <accepted-run-id> --output-digest <accepted-output-digest>`.
3. Require command exit0 and READY for both the base publication and its
   planning_summary. On failure, retain the failure and leave the selection
   unchanged. Correct the diagnosed authorized prerequisite before retrying the
   same command; verified sealed rows are reused.
4. Use `VF_PLANNING_SUMMARY=1` for the single-response reader. Continue the existing explicit activation/selection procedure only after its
   other required gates and approvals pass. Preparation does not select a run.

Actual daily-runtime preparation remains UNPROVED: accepted June6/7 owners are
in fresh_complete on the former owned freshvcf-complete001 facility. Its container
and volume are absent on recheck. The smallest further proposal is an explicitly
authorized restore of that exact owned accepted source and zero-calculation
prepare_daily_ui proof; no restore or substitute source is part of this delivery.

Delivery proof comprises exact broad/restricted counts/date, empty/overlapping
scopes, rejection of changed source/recipe and unknown scopes, focused frontend
tests, and three complete entry/return observations per actor. The retained
broad before samples precede reversal; restricted before samples use the
restored foundation. That image difference must qualify any timing comparison.
Preserve all failed samples; do not substitute API timings for screen readiness.

Deploy only the 3005 backend/frontend overlay with recorded rollback. Preserve
selected source/admission, authentication, resources, BPR5000 and other services.
After proof, commit the narrow rebuild and push the normal reversal plus rebuild;
report the 50% median target honestly and stop.

External evidence: D:/freshvcf-build/evidence/planning-screen-20261011-001.

## Delivery observations

The final 3005 overlay uses backend/frontend tags planning-simple-20261011-002.
The backend is ready with admission digest
5c90ae58f6478f7b1805f534f95fbe0de241a5280c4422ec70f28467221bf3e7.
Protected container identities/resources/mounts and BPR5000 remain unchanged.
The first overlay and correction build/startup records remain in external
evidence; the correction handles every consecutive Go Back, not just the first.

Seven frontend tests and six daily coordinator/readiness unit tests pass. The
count formula AST matches the retained producer exactly. PostgreSQL schema and
guard checks pass with no pending migration. Exact broad/restricted ten-count
and date, denied/overlap scopes, changed source/recipe and unknown-scope checks
are in simple-proof.json. Current screenshots verify the six visible values
and date; custom metrics remain in the unchanged ten-field API contract.

Serving access logs prove one GetPlanningDataCount on each entry and each return
for all six measured journeys, with zero standalone identity/date requests.
All responses are200. No benchmark retry or favorable-sample substitution was
performed. The expired-session attempt is retained separately.

| Actor / journey | Before median | After median | Improvement |
| --- | ---: | ---: | ---: |
| Broad entry | 4.580s | 2.353s | 48.6% |
| Broad return | 2.619s | 3.793s | -44.9% |
| Restricted entry | 3.166s | 4.211s | -33.0% |
| Restricted return | 3.522s | 4.110s | -16.7% |

The50% full-screen target is NOT MET. These are bounded observed timings, not
controlled performance parity: broad before used the prior Planning image,
restricted before the restored baseline; first after navigation followed login
while broad before used reload. The external monotonic observer includes DOM
polling/tool overhead, and browser resource/render subdivision was unavailable.
No wider optimization or new measurement campaign is included. Actual daily
runtime acceptance also remains UNPROVED for the absent facility described above.

To roll back this task-owned3005 overlay, run
`D:/freshvcf-build/venv/Scripts/python.exe D:/freshvcf-build/evidence/planning-screen-20261011-001/deploy_simple.py rollback`.
This restores the recorded pre-Planning backend/frontend and flag0 without
reversing shared migrations or deleting retained receipts.
