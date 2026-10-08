# Cohort4 command and ownership contract

Cohort5 adds a separately approved operational admission path; see
[COHORT5_OPERATOR_RUNBOOK.md](COHORT5_OPERATOR_RUNBOOK.md). This Cohort4 document
retains its historical strict-path evidence. Do not use its separate activation
step for the new atomic operational receipt/access path. New runs and serving
changes remain held.

This maps the existing command owners; it is not a second status tracker or a
release to execute a new day. `MIGRATION.md` owns status. Cohort4 packages the
commands without changing their semantics. The general daily chain remains
blocked at the input/admission gates described below.

| Step | Existing command / owner | Explicit inputs | Output and failure stop | Supported domain |
|---|---|---|---|---|
| 1. Opening and MDM binding | `install_daily_input_source INPUT --sha256 SHA` | Registered synthetic artifact bytes/SHA; `daily_source_install.install` owns registration | MdmSource ID/digest/receipt; stop on identity or ownership failure | Existing registered synthetic opening only. No arbitrary production MDM installer is claimed. Installation mutates owners and is not executed by this cohort. |
| 2. Predecessor and actions | `temporal.command_state`, persisted RunCommand; existing authenticated Apply/Sleep workflow | Own preceding CalculationRun, ordered action payload/digest/before/after chain and explicit timestamps/policy | Validated predecessor closing state; stop on changed chain/date or unapproved actor/action | `run_daily` has no action-generation CLI. Never invent recommendations, copy another engine's actions or use proof scripts to manufacture actions. Existing real workflow evidence remains distinct from unexercised Sleep in the two-date trial. |
| 3. Calculate one day | `run_daily INPUT --sha256 SHA --day-index INDEX --revision REV --mdm-source ID --mdm-source-digest DIGEST --bpr-remark-horizon DAYS [--predecessor UUID] [--exceptions FILE] --evidence-mode production` | Frozen `case` with days/static_day/profile/opening; exact MDM binding; day0 has opening, successors require preceding date; explicit approved exception file only | JSON run/status/date/input/output digests, publication unselected; error stops chain. Calls execute_day once | Existing command contract only; no new input/day run authorized. Do not use a different revision/date/input to hide failure. |
| 4. Operational boundary | `cohort2_operational materialize --request REQUEST` | Existing typed configuration, committed run/output, unique request key/owned root, own operational predecessor; declared initial openings only on first attempt | Attempt/status/run/root. Stop unless SUCCEEDED and native verification passes | `cohort2-integrated-materialization-v1` exact roster; explicit ZIP path/hash; approved C1–C6 inputs/limitations. No general deployment configuration is inferred. |
| 5. Read-only operational check | `cohort2_operational check --attempt UUID` | Exact completed attempt, original files/backup/evaluation receipts and mounted paths | SUCCEEDED JSON after verify_attempt; any mismatch stops | Zero calculation; no materialization or restore campaign. Reused completed Cohort2 evidence remains authoritative. |
| 6. Prepare | `prepare_daily_ui --run-id UUID --output-digest DIGEST` | Same committed run, exact source/input/action/configuration identity, required report sources | READY seal and layers, else nonzero and unselected | Explicit 18-layer core-without-bor-v1 domain; no inferred remark/request/hierarchy population. Cohort3's supplements cover only its two pins. |
| 7. Bind access | `activate_daily_ui --run-id UUID --output-digest DIGEST --publication-seal SEAL` | Unselected accepted owner, unchanged READY seal, explicit catalogue/hierarchy hashes | Append-only activation digest, selected=false; failure preserves original | Strict independent parity by default. Exact two-owner qualified policy is not a new general policy. |
| 8. Check selection | `check_daily_selection --run-id UUID --output-digest DIGEST` | Independently accepted DAILY_CHAIN with parity PASS/PASS_WITH_LEGACY_FLAWS plus native and full prepared readback | Emits run/digest/BTR generation together; never edits files/services | **BLOCKED for arbitrary qualified daily runs.** It deliberately rejects both flag0/parity{} Cohort3 owners. Do not bypass it or add owners to the two-owner policy. |
| 9. Select and read | Existing owned configuration plus `admission.AdmittedApplication`; existing gateway | One coherent checked tuple, catalogue/access seals and real authenticated scopes | Startup admission and per-request identity; failure must preserve prior serving tuple | No serving activation in Cohort4. Cohort3 in-process selection proves only its exact two owners. |

## Operational request and file owners

The request requires `run_id`, `configuration_id`, `request_key`, `owned_root`,
`expected_output_digest`. Optional fields are exactly `predecessor_id`,
`retry_of_id`, `interrupted_attempt_id`, `repair_of_id`, `repair_file_ids`,
`openings`, `abort_opening`. Recovery fields are forbidden in materialize;
recover requires explicit retry or repair lineage. Repair cannot supply new
openings. A successor consumes its own operational predecessor, not fresh openings.

`operational_runner.validate_configuration` requires the exact roster and a ZIP
tool with absolute path and SHA256. Existing PHYSICAL_TABLES/LOG_BINDINGS/
NORM_REPORTS/ALERT_SEEDS and configuration receipts enumerate the supported file
and intent domain. Arbitrary output names, recipients, credentials, sanitation
inputs or backup roots are not admitted by this package. Secrets and resource
ownership belong to the private deployment configuration, outside Git.

## Finite release decisions remaining

A later real-input acceptance proposal must supply the frozen input/config/tool
identities, MDM owner, first opening or exact predecessor/actions, enabled workflow
domain, supported sources/files, exclusive resources, day count and acceptance
exits. General consumption additionally needs an explicit completion/admission
policy: retain independent parity or separately approve and implement a verified
general operational policy. Neither decision is needed to finish packaging, and
neither is inferred here. Native flag0, all prior qualifications and the two
approved503 route blocks remain truthful. No broader policy code changes occur.
