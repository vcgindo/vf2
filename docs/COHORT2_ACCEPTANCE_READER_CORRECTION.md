# Cohort2 acceptance reader correction

The approved consolidated package requires stopping before June7 after a
June6 acceptance failure and reporting its first cause and smallest remedy.
June7 has not run. One of the two authorized calculation calls has been used.

June6 run `77731d95-03f4-4a82-8498-404f944df73b` is SUCCEEDED. Complete typed
daily readback and all three new source captures passed. The external acceptance
harness then raised `KeyError: CalculationOutputs`: it requested a validation
family from `services.read_outputs`, which deliberately returns production
relational state. This is a harness reader error, not a calculation mismatch.
No operational attempt or action was created before that failure.

Read-only diagnosis checked complete retained values against immutable checkpoint
digests and row counts. CalculationOutputs, DBMFinal, BPRFinal, BTRFinal, Reports
and every prior complete-state population match Cohort1 exactly. Only the two
approved empty complete-state populations were added. Both accepted Cohort1
owners and their actions remain unchanged.

Evidence directory:
`D:/freshvcf-build/evidence/cohort2-20261008-001/real-source-20261008-001`.
Preserve `day-000.json` and `day-000-a002.log` as failed acceptance evidence;
`day-000-diagnosis.json` records the successful read-only diagnosis. The earlier
`day-000-preflight-a001.json` / `day-000.log` retain a missing output-directory
setup failure before any calculation; creating that declared directory required
no engine/input change.

## Exact prepared correction

`run-day-reader-a002.py` changes only the external acceptance harness:

1. Read the five core validation families from retained calculated evidence,
   verifying each complete population against its checkpoint digest and count.
2. Resume the existing June6 owner without calculation; verify its input/output,
   typed-state and source-capture digests. Write a new linked acceptance receipt.
3. Complete the already specified actions, files, intents, restore and command
   proof. June7 still requires the new June6 acceptance receipt to pass.

Original runner SHA256:
`9653a74909629c85ace6c09b043a462feaec033c49528d713329f4c9eecab04e`.
Corrected runner SHA256:
`e712be3223aaa56fbafb8f1c5d16b4a09e320d0385d78f582f48de2ab79f0331`.
The transition is pinned in `reader-correction.json`; syntax validation passes.
The application image, calculation, inputs, configuration, policy, comparisons
and original frozen files remain unchanged. No extra calculation is requested.

Approved directly by the human via call_a7512ac1cb244e3f9bf31c8bed8e6c1f:
"Approve reader correction and bounded continuation." Permit this runner-only correction, resume zero-calculation
June6 acceptance, then use the one remaining authorized call for June7 only if
June6 passes. A new acceptance failure still stops continuation. Cohort2 closure
and its cohesive commit/push remain incomplete until all required exits pass.
