# Step4 combined execution and resource proposal — 27 October 2026

**One human decision is required for the entire package; neither execution nor the resource delta is approved.** Bounded scoped-runtime Step3 has now been independently accepted. This packet completes the retained design proposal with exact intended owners, source/input mappings, run counts and a bounded DISK request. It supersedes only that design document's unresolved planning details; the original submission and receipts remain preserved.

Objective: qualify matched Full vs UptoBPR→PostBPR vs UptoDBM→PostDBM, with identical raw facts/configuration and **no manual actions**. Each arm computes its own persisted predecessors. Do not compare the differing already-accepted Step3 action histories as equivalence. Retain the Step3 action/failure/browser proof at unchanged dependencies; no new action, fault or browser campaign is included.

The sole execution-status/decision authority is `F:/freshvcf/docs/handoff-3005/TRACKER.md`. Current production source is ba326432; this planning assignment changed documentation only. Machine-readable exact proposal: adjacent JSON, SHA256 `0978682518a9ba3e1e1e8cadfce6d06ad2b5621df1f513ed4b7651a76d16e3b2`.

## Exact owners, resources and isolation

| Arm | Proposed unique database | Opening / source identity |
| --- | --- | --- |
| Full | `vftest_fresh_runtime_step4_full_20261027` | `owned-step4-full-conserving-initial-facts-v1` / `owned-step4-full-conserving-20261027` |
| BPR split | `vftest_fresh_runtime_step4_bpr_20261027` | `owned-step4-bpr-conserving-initial-facts-v1` / `owned-step4-bpr-conserving-20261027` |
| DBM split | `vftest_fresh_runtime_step4_dbm_20261027` | `owned-step4-dbm-conserving-initial-facts-v1` / `owned-step4-dbm-conserving-20261027` |

These names were absent in the single bounded read-only inspection; that does not reserve them. Any collision at the future pre-creation check refuses rather than resets/renames silently. New namespace/container metadata must name owner chat `01a17c63-cae8-7730-b340-01900cd1dd6c` and this approved proposal. Do not transfer ownership of the existing PG or any accepted source.

Reuse existing PG `407fda1021836b322c9db248f9f91fab8ffc73c8351b6b0fb7ae2081b9b6a110`, its current exclusive volume `vectorflow-uptodbm-private-pg-20261025`, and exact existing `vftest_g2n_20261024_{owner,installer,runtime}` roles plus the existing namespace-registrar/operational-acceptor authority. No new global role, grant expansion, PG restart or PG16 serving transition. New database-local CONNECT/schema/migration grants are only the already-qualified fresh-namespace profile. Reuse the finite Step3 `create-database.py` template0 pattern for named new databases; do not invoke broad `release.provision.provision`, which would create MTO/global roles. Existing scripts are references, not executable approval: their old owner/name/approval pins cannot simply be reused.

New evidence root: `D:/freshvcf-build/evidence/scoped-runtime-step4-20261027`, observed absent. Each arm has `{root}/{arm}/pick-output`; one new-root RW mount `/evidence`, retained fixture-v2 mounted RO at `/retained/fixtures-v2`. Runtime reports use the existing captured `pick_output_root/{own_run}/runtime-reports`. Old evidence, both relocated folders and archive have no writable worker mount. The JSON names every producing container; all are sequential, restart=no, no host port. One4GiB/2CPU worker; PG384MiB/0.5CPU. No auth/frontend/server, new image, build or service switch is needed. Existing servingMTA/auth/frontend/MTO and protected3002/3003/3004/3005 remain untouched.

## Current-image applicability, not a new runtime claim

Pin image `sha256:4e66836122213a23fa8d52981cda1d8bc274b3412c775fa01e79cd4230e30708`, source `ba32643250c1c3b916cd400fd801ae88b57122c6`, native manifest `9f15707cf3ee46cc0878c1fce714e291b688d391aa79cd65d879d208391fac5c`. Existing complete native package/recipes/schema proof is reused. The JSON pins13 inspected source files as canonical Git blobs.

Observed source supports the intended fresh route:

- `release.register_mta.register` requires a new owned namespace, truthful current native identity and complete real migrations; use its fresh certification at0238, not an old certificate or consumed transition.
- `report_definition_registration.register` requires actual owner, installation/source/certificate, exact typed seed/definitions and guards. `runtime_report_registered_request.request` reads that actual registration and attaches it outside the scope request before input capture.
- `runtime_report_request.request` explicitly supports Full/UptoBPR/UptoDBM and recomputes compatibility against `require_current()` and the phase recipe. A genuinely fresh request must equal that result. The two-run retained compatibility fallback is **not** authority for any Step4 run and must not be entered to cure a refusal.
- `run_production_report_placement --scope Full|UptoBPR|UptoDBM --report-registration-digest ...` supports all target entries; `continue_production_report_placement` owns the split tails. Full uses existing execute_day/completion with zero scope attempts. Split uses existing claims/phase acceptance/finalization. The TEST-name guard permits the proposed VFTEST_Fresh prefix; it does not confer human authority.
- Generic terminal admission resolves selected complete daily publication/summary/source/recipe/configuration; no new UUID eligibility entry is needed.

This is a source applicability assessment, **not runtime qualification on new owners**. The exact fresh registration/capture/preflight checks remain first in any approved operation. A refusal stops with the original evidence, before speculative business execution; no waiver, identity spoof, schema edit or rebuild is authorized.

## Exact facts, configuration and path changes

Retained fixture-v2 manifest SHA256 `2319d241704f56db0e14b79a572a58f7fd6d894338c28f0aba3ab4d5b926cad9`. Reuse original catalogue, raw opening22 history, declared external ledger and the same raw day files, not calculated answers:

| Date | Original day-file SHA256 |
| --- | --- |
| 23 October | `cdc75639779d275ea9ed9e3bc8e5e35e69776ada31d35849ad9a55efbff25f11` |
| 24 October | `6b60cabac12c41439edffcdb23efbf9dfe5f3655024ba6b3b286c5177dd8e05b` |
| 25 October | `6ceaa5d767e73fc2f84e73b1733b124094e2276fe864efe7c3d020871ec28a78` |
| 26 October | `3e44fde251f7679cdd936e16d7cbd93d45be5c004574557cd81db6fce073590e` |

All three initializers derive from **one** retained BPR operator template SHA7b24a76b…a76cd1. Only `/opening/identity`, `/recipe/source_identity` and `/recipe/version` change to the exact arm values in JSON. The DBM template differs from that template only in those three identity cells; none of its calculated results is used. The proposed canonical serialization and complete planned initializer hashes are pinned in JSON; no initializer files or sources have been created. All masters/configuration/opening business values and row order remain exact. Configuration digest remains `e68126aa6602169be3996303249ec9dcb73b985b69eca4a8eb9aed1a9c6ec106`; new source/recipe/certificate digests legitimately differ and must be derived, never copied from Step3.

Reuse exact eight-report roster bytes SHA`1f036745abadf0224d9778a8fabf3cc93ad632d106a61127973f08b2baa9af55`, definition digest`0fc450d4d99bddc964790800ffc1eca0c43a2e72b0c1090838c55fed2826726a`, initial filename seed digest`4afa2e17e1f84e4212d5578fe306036e4a65a00847c85d9cebb13f72988a1f3f`, and disabled independent RRR. The placement configuration JSON remains byte-identical (digestf8d5fe6f…). Seed LastGeneratedFileName values are retained, including the historical TotalReqReport_20260407 seed; do not replace them with the new date before execution.

The report reference derives from the pinned BPR reference: replace only initial anchor UUID/source evidence with newly returned own initialization/source; keep empty catalogue/null output; replace hook/disposition authority with this proposal's SHA and actual later human approval. Same no-op five hooks, site and enabled five-file/four-table InputData policy. Exact transformations are in JSON. No old registration/capture/certificate/authority is adopted. This package's approval would explicitly authorize that new TEST disposition; it does not infer production defaults.

## Finite producer and proof roster

There are **12 logical day runs and14 producing command invocations**, one bounded fresh worker per invocation:

1. Each of3 owners computes Full23, Full24 and Full25 from its own persisted predecessor:9 invocations. Same `run_production_day` mechanism as retained predecessor proofs. No cross-arm copy of calculated opening/history. Prepare only the necessary new Full25 operational/native reporting for inherited consumers.
2. Full arm executes registered Full26:1 invocation; no scope attempt or fabricated early acceptance.
3. BPR arm executes registered UptoBPR26, stops at accepted BPR, then fresh-process PostBPR26:2 invocations.
4. DBM arm executes registered UptoDBM26, stops at accepted DBM, then fresh-process PostDBM26:2 invocations.

Additionally:14 non-producing input/preflight inspections;3 initializations/typed report registrations;6 new daily preparation coordinators (Full25 and terminal26 in each arm), plus2 early-stop read preparations;3 exact non-producing terminal retry calls. JSON pins command/container names. No manual actions/remarks, invalid27 trial, day27 calculation, accepted-run replay, extra producer retry or rebuild. A failure preserves its prefix/attempt and stops; additional producing attempts are not automatic.

Required phase proof: split PRE_BPR/BPR/DBM/DAY_FINAL accepted chain with exact original prefix and final owner; BPR's DBM is produced by its tail, DBM's BPR remains its own accepted parent. Target Full has zero scoped attempts and one atomic finalization. Each target owns five placement receipts (PostImporter, PostBPR, PostDBM, PostBTR, Final), even when a placement has zero enabled report rows. Correct post-hook/pre-final timing and typed source lineage remain mandatory. No Full terminal substitution for early snapshots.

## Complete comparison and allowed identity map

Freeze the comparison manifest before producing26, using existing persisted codecs/registries: complete operational closing state, pending queues, accepted masters/norm/suspension/cooling, DBM/BPR/Pick/rationing/allocation, BTR/history/trends/availability/excess, actions/effects, consumer projections, every applicable report and prospective27 opening. Preserve every native scalar, date, NULL/empty distinction, duplicate occurrence, ordinal and canonical order. Compare the full semantic predecessors before26 and all three complete terminal results; independently verify each closing-to-next-opening reconstruction. There is no total/count-only acceptance.

Compare applicable typed runtime rows/header/filename/MIME/CSV and ZIP members for Id2/3/4/5/6/7/8/10 and Pick/InputData/fixed outputs at exact placement cuts. Native7Zip container identity is not required. Preserve explicitly disabled/absent branches as unqualified; missing required output fails. Native response/count/filter/export and relevant Research/Guided/Planning/BTR projections bind their own selected owners/configuration/date. Reuse Step3 browser proof because no presentation/security dependency changes; no new browser window is proposed.

JSON's allowed bijection is limited to: new database/OIDs; source/initialization/certificate/registration/run/capture/claim/attempt/phase/publication/generation identities and their actual foreign keys; command/worker/audit-wall-clock envelope; owned physical root/run paths. Compare their graph/ownership separately. If an owner ID participates in a custody digest, recompute against the verified own graph rather than falsely requiring identical cross-arm hashes. Business dates/timestamps, SKU/location/parent/supplier keys, values, types, NULLs, multiplicities and ordinals are not normalized. Source-derived archive identity/outer-path names may use only the declared owner map; actual business member headers/cells/order stay exact. A new unlisted difference stops, rather than expanding the ignore list.

Retain full external typed comparisons and first divergence. Three matching engines alone do not establish canonical truth; reuse the independent legacy BAT/SQL/DLL and source-family expected-value proofs. Stage-specific R1 action effects and R2 failures/R3 browser reuse remain as in the original design, not a fresh action campaign. Zero unexplained semantic mismatches is the exit.

## One proposed DISK envelope, with explicit uncertainty

The bounded planning read measured retained Step3 BPR71,711,767 bytes and DBM71,171,095 bytes (about68.39/67.87MiB). Retained window8 accounting observed total5,804,651,475 bytes including512MiB global reserve and cumulative1,951,491,603, with minimum headroom78,551,533. Those totals are historical, not a current fit assertion. No new capacity sweep, database creation, settings change or cleanup was performed.

| Proposed allocation | MiB | Basis / limitation |
| --- | ---: | --- |
| Three new databases | 240 | Hard80 each, above measured retained sources; fresh Full26/schema storage remains unmeasured. |
| Incremental WAL peak | 64 | Conservative allowance; recycled/preallocated WAL is not silently discounted. |
| Evidence, original new files, complete comparisons | 64 | No screenshots/build copies; exact high-water/compression not yet measured. |
| Worker writable/scratch | 12 | One sequential worker; no image layers/build. |
| Unspent operation reserve | 20 | Retained before every creating/producing/preparing operation. |
| **Operation allowance** | **400** | Hard limit, not predicted exact growth. Actual charged growth may use at most380 while20 remains reserved. |

Request **one combined authorization** for this finite execution plus these two DISK ceiling deltas:

- Total including unchanged512MiB reserve:5,632→**5,968MiB** (6,257,901,568bytes), +336MiB.
- Cumulative growth:1,936→**2,272MiB** (2,382,364,672bytes), +336MiB.
- Step4 operation allowance:400MiB including20MiB reserve. The earlier window8 allowance is closed and not reused. No RAM/CPU/global-reserve increase, baseline reset or storage exclusion.

At the last retained measurement, reserving the full400MiB would leave33,819,693bytes under the proposed total cap and11,442,669 under cumulative cap; the latter governs. These are arithmetic projections, **not current available bytes or a capacity guarantee**. Estimated PG+WAL incremental peak is bounded304MiB, actual growth upper allocation380MiB plus20reserve. The exact missing measurements are the new current-image namespace/Full-vs-split storage high-water, transient WAL and complete-comparison/serialization peaks. The proposed allowance contains these uncertainties without authorizing speculative preliminary runs.

After a matching human approval, take one normal pre-operation inventory using the same original cumulative/global accounting, including all retained/moved roots/images/volumes. Record the new Step4 operation start measurement only for its own growth ledger; never reset existing baselines. Require both caps/reserves and every slice to fit before starting; check growth at each bounded transition. If80MiB per DB,64MiB WAL,64MiB evidence,12MiB writable, operation400MiB or either global/cumulative cap would be exceeded, stop before the next mutation. Preserve already created resources/failed attempts; do not delete them, compress away originals, expand a limit, replay or launch a new approval chain. Present the exact failed guard for a later human decision.

## Human decision and stop

Reviewable decision: **approve this exact finite14-producing-command Step4 comparison, three named new namespaces and stated336MiB DISK ceiling increases with400MiB operation allowance, or approve neither.** Authority must match the JSON SHA`0978682518a9ba3e1e1e8cadfce6d06ad2b5621df1f513ed4b7651a76d16e3b2`. No separate preliminary capacity approval is requested. This packet creates no approval file, executable controller, worker, source or resource.

On approval, only the stated new-owner initialization/schema-profile/registration, bounded producer/read-preparation/comparison/retry tasks and external orchestration of these existing commands would be released. No product fix or new native build follows from a refusal. All earlier accepted runs (especially Full49efa557 and both Step3 sources), failures, both moved directories, archive, images and original evidence remain immutable. If this proposal is not approved, remain stopped.

Final delivery would be exact source/input/config/owner-bound complete comparison and reuse packet, stopped workers, unchanged protected/serving resources, commit/push and independent Step4 judgment. No Step5 deployment, Step6 handoff, G3 continuity, latency/scale, production-roster regularisation or permanent cutover is included.
