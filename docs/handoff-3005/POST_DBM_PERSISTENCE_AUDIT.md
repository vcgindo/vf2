# Post-DBM persistence contract audit — 22 October 2026

The large rerun is **paused by the user**. This is a bounded architecture audit
and correction, not a new implementation queue or release to execute another
large day. `TRACKER.md` remains the only status authority. The uncommitted
admission/retry work was saved externally and withdrawn from the working tree.
No serving process, loaded database, frozen input, prior attempt or receipt is
changed by this audit.

The production path through DBM is frozen at `c82231b9`. Full normalized source
and AST equality is recorded for147 whole files, including planning/domain/temporal,
master/initialization code, daily entry/recovery and the shared input validators.
The additional MDM edit is only `daily_current._closing_projection`, called
after DBM during publication or subsequent persisted verification. Every other
function in that module remains AST-identical. Changes below affect only
post-DBM source processing/readback.
An import of a post-DBM module does not authorize changing a shared scalar rule;
its existing arithmetic and comparison functions remain unchanged.

## Why the pre-trial proof missed the failure

Two dimensions were not matched to the actual April8 workload:

1. `load_image` changed its return contract on20 October: at10000 rows it returns
   a list; above10000 it returns immutable `RecordRows`. The force readback
   validator still required a list. Other spool tests did not cover that reader.
2. The retained small native starter fixture has `daily_publication=True`, but
   does **not** enable `operational_sources`, `operational_input_sources` or
   `operational_force_sources`. April8 enables all three. That native test did
   not execute the force-source writer, regardless of its successful day result.

The stage named `persistence_full_output_readback` audits the main typed snapshot
images. In `finish_run`, it occurs **before** operational calculation sources,
processed-input sources, force sources, Pick facts, route facts, daily sources,
native audit sealing and final master-revision acceptance. Its success was not
proof of the complete transaction. The latest large attempt failed in force
readback after that stage, before an operational commit. This was an audit
coverage error, not evidence that the previously accepted UI tests were false.

## Change history and applicability of earlier large-data tests

| Finding | Introducing history | Classification and actual reachability |
|---|---|---|
| `load_image` returns `RecordRows` above10000 | `25f8a2ae`,20-Oct01:14IST; writable-spool/read-only modes refined by `0cfcf615`,20-Oct01:19IST | New reader-contract change. This is the cause of incompatibility with older list-only readers. |
| Force list-only validation | `5eac7e1d`,8-Oct23:57IST | Older guard became incompatible with the new reader. Actual failed April8 path; corrected in `c82231b9`. |
| Transit processor and raw decoder list-only checks | `d972e540`,6-Oct10:11IST | Older consumers became incompatible with current typed reloads. April8 has97097 current standard-attribute rows and an explicit shipment source: even empty raw shipments do not avoid the standards check. |
| BOR/RRR predecessor-history list-only checks | `5eac7e1d`,8-Oct23:57IST | Latent successor regression when a persisted history exceeds10000. Applies to actual typed history reads, not just hypothetical generators. |
| Supplier/report `_project` list-only check | `7890415c`,14-Oct02:35IST | Latent large-opening consumer mismatch. Current saved supplier opening is only97 SOB/1496 MOQ rows, so do not call it an already observed April8 failure. |
| BOR full-population joins | `5eac7e1d`,8-Oct | Pre-existing scale risk, not introduced by the BTR split. The required producer runs inside daily source publication. |
| Norm RRR repeated joins | `144ea39f`,7-Oct12:39IST | Pre-existing report-producer cost; not an upstream DBM rule change. |
| Same-day Order/Norm RRR source assembly | `7890415c`,14-Oct | Native source path has its own scans; qualify separately from earlier prepared presentation SQL. |
| BTR/report separation and COPY | `63db37c3`,21-Oct23:53IST | Did not introduce the10000-row reader switch. It separates derived report generation and retains required atomic sources; do not blame every discovered gap on this commit. |
| Master/input-capture/live-capability list checks | Master `837ef17f`,13-Oct; input/capability `5eac7e1d`,8-Oct; location projection `68f24130`,14-Oct | A rejected spool probe alone is not a defect. These APIs receive private producer lists, not `load_image` results, on this path. Their checks are retained unchanged. |
| Persisted current-master verification → shared projection | Typed reader switch `25f8a2ae` exposes the older master/list boundary during later verification | Actual persisted closing can contain spools. The post-DBM `_closing_projection` adapter materializes only selected master inputs; shared installation validators and unrelated histories stay unchanged. |

`docs/MIGRATION.md` records populated April7 presentation checks, including
BPR50/97097, RRR5000/8063, DBM5000/11158, BTR5000/97299, Research5000/97097,
Guided/Planning and full nested97097-row comparisons. Those prove the named
query/serialization/grid paths over the retained fixture. The same record
explicitly denies daily capture/root/seal admission for its fixture consumer
receipt and excludes native daily-ingestion integration from the presentation
batch. These tests remain valid in their stated scope. They cannot certify a
later return-type change or the new day's pre-clear force/history publication.
Full blame excerpts and pinned before-change implementations are retained in
the external audit evidence, rather than inferred from commit titles alone.

## Closed handshake inventory

This is the finite call path from DBM exit through `finish_run`, operational
readback and separate report preparation. Branches are explicit. The full field
catalogue is external evidence, not a replacement schema or source of defaults.

| ID | Producer → consumer | Contractual values, identity and proof boundary |
|---|---|---|
| H01 | DBM terminal generation → BTR | Current typed DBM/control tables; retained occurrence order, duplicates and NULLs. BTR category/age/history and dispatch-efficiency effects remain daily business work. No algorithm change. |
| H02 | BTR → closing assembly | Category-bearing `SKULocStandardAttributes` is the final BTR generation, including its DBM copy. Closing sections retain their complete table roster. Immutable histories may be `RecordRows`; mutable script flags/settings remain their owned lists. |
| H03 | Calculation → temporal finalizer | Exact eight `_CompletedBoundaries`; one closing-state row, capability envelope list, `Lineage` and policy-bound cohort metadata. Missing/duplicate capability populations are not empty defaults. |
| H04 | Complete Pick state → run files | Actual run-owned path, four named files, CP1252/CRLF sqlcmd format, explicit integer/decimal precision. File existence is not database commit or serving acceptance. |
| H05 | Captured profile → `finish_run` | Same immutable profile/input/configuration identity; three capture policies, complete-day mode, publication flag and horizons must match the run. Profile reads happen before the outer write transaction; exhaustive input audit remains inside it. |
| H06 | Capture preparation → commit admission | Source/run locks, RUNNING owner, predecessor/source/certification/base-revision identities and exact five-epoch capture cut. No stale input, scope replacement or metadata repair. |
| H07 | Input images/references → audit | Full ordered typed image rows and authenticated physical capture/reference ancestry. Canonical digest, row count and contiguous ordinals; counts alone never certify values. |
| H08 | Frozen occurrences → native consumption | Original source PK/revision/ordinal/task IDs; exact supplier/force/season/stop/phase queues, archives, pruning and task transitions. Mutation only under the day's transaction. CONSUMED is idempotent; missing input is not silently skipped. |
| H09 | Consumption → completion flags | Actual NMS mode and completed native writers authorize flags. `ScriptExecutedFlag` and importer settings are controlled mutable generations; no retrospective success markers without their writers. |
| H10 | Closing → current master projections | Exact business-field roster/types, source/owner partition, one-based occurrence ordinals, retained PKs, NULLs and duplicates. Private producer-list API remains unchanged. Batch500 full-value verification; sealed projection receipt. |
| H11 | Closing/report-source facts → typed image writer | `(run_id,image,ordinal)` ownership, zero-based row order, full fields and original wire kinds. Scalar-only image rows; no state JSON blob. Every named image resolves to its pinned table/binding. |
| H12 | Python scalar → SQL → wire scalar | `str/int/float/bool/NULL`, Decimal/date serialization, native SQL ranges/scale/width and NULL constraints. Conversion never invents data; canonical full readback catches coercion/type/value drift. All-NULL fields reconstruct NULLs even when their metadata wire kind defaults to `str`. |
| H13 | Typed writer → transport/readback | COPY at>=500; otherwise bounded executemany. Reads in500-row chunks. At<=10000 return list; above10000 use real disk spool or certified lazy read-only `RecordRows`. Conversion, SQL, readback or commit error rolls back the entire transaction. |
| H14 | Nested export rows → typed export cells | Explicit `values` arrays, row/cell ordinals, variable lengths and typed NULL/string/int/float/bool cells. Empty rows remain rows; orphan/extra cells are rejected. Nested export records use a lazy reader, not the flat spool. |
| H15 | Snapshot images → initial output audit | Exhaustive typed snapshot and export checks. This stage does not include writers H16–H29, which run later. It must not be described as complete persistence acceptance by itself. |
| H16 | Complete calculation capabilities → operational bands/advance sources | Exactly one required capability with explicit list-valued live producer rows; code fields, nullable parent, SQL integer quantities and stock-only allocation provenance. Immutable typed relational rows and separate receipt digest. This producer API is intentionally not changed to an arbitrary iterable. |
| H17 | Processed pre-BPR inputs → input source | All four native tables and exact field roster/typed cells; explicit [] allowed, absent/None forbidden. Producer snapshots remain lists. The stored `_rows` reader already accepts `RecordRows` and verifies the full source digest. No upstream capture change. |
| H18 | Pre-clear force inputs → force source | Exactly ForceNormChange/DBMMaster/MasterDataRaw; case-insensitive required fields without duplicate-case columns; requested Norm/approval/requester values and NULLs preserved. Typed image/table/run/policy/input ownership plus full aggregate digest. Reader accepts the closed list/`RecordRows` protocol. |
| H19 | Produced Pick bands → Pick facts | Exact3 code+5 band fields; nonempty codes<=50, canonical signed integer strings, no rounding/defaults. Duplicates/order retained under zero-based ordinal; native readback reconstructs the same strings. |
| H20 | Produced routes + own orders → route facts | Exactly one original-route capability, one unambiguous OrderKey mapping, same SKU, source/destination/due-date values, duplicates and order. No reconstructed allocations or foreign order source. |
| H21 | Current sources + pre-refresh supplier opening → BOROA | Full selected fields, nullable arithmetic, SQL ceiling/scale, bag multiplicity and ambiguous UPDATE denials. Index candidate bags retain existing ASCII case/trailing-space/NULL semantics; custom comparators/unqualified text use the original scan. |
| H22 | Same-day produced allocations/requirements → RRR | Order before Norm, native UNION/DISTINCT and all join multiplicity, signed/nullable quantities, pack-size division and blue adjustment unchanged. Ordered index buckets replace scans only in this post-DBM producer. |
| H23 | Own persisted histories → next history generation | Own completed predecessor and exact day/horizon; strict `ReportDate > today-horizon`, exclude current date, then append current occurrences. Native columns/NULLs/duplicates/order survive actual>10000-row SQL `RecordRows` reads. Expanded BOR text policy remains explicit approved NULL availability. |
| H24 | Optional supplier/colour/request/remark facts → daily-source receipt | Opening SOB keeps numeric wire spelling and float projection; MOQ typed readback; exact colour/sequence roster; request/remark identities were frozen earlier. Missing source stays unavailable, not invented empty. Bounded images metadata<=64KiB. |
| H25 | Optional explicit logistics → transit source publication | Full12 raw shipment fields, dated provenance, current standards and rationed report, explicit transporter directory, SuperDelayFactor. Preserve negative-quantity diagnostics, NULL exclusions, dates and duplicate joins. The standards/report reloads can be spools. Only the post-DBM validation call adapts owned external rows to the unchanged upstream validator's list API. |
| H26 | Native audit frozen occurrences → FINAL audit | Original source PKs/ordinals and aware timestamps, declared timezone and retention cutoff. Only FNC OldNorm may change through its actual writer. Immutable FINAL rows, exact pruning and SEALED receipt; no arbitrary history reseeding. |
| H27 | Producer preparation → master-preparation metadata | Contract/configuration digest/reuse boolean match the sealed capture, actual master/configuration cut, qualified producer call metadata. Bounded metadata only; no epoch reset. |
| H28 | Required receipts → operational root | Version3 roster is ClosingState/Lineage/PublicationContext/ReportSourceFacts. Main manifest, source receipts, input/root digests and SUCCEEDED/completed_at are saved together. Auxiliary operational sources additionally have their own immutable source/value checks; do not assume an early snapshot audit covers them. |
| H29 | Successful output → accepted master revision + COMMIT | Static roots bind the same run/source/output/input/production digests and exact fields. Revision acceptance occurs inside the same outer transaction after header UPDATE. A driver COMMIT success is required; a pre-commit log line is insufficient. |
| H30 | Committed operational state → next opening | `read_outputs(include_reports=False)` reconstructs own closing independently of derived report readiness. Commands replay in global event order with before/after digests; without commands the complete closing digest must match exactly. No prior run borrowed to populate a screen. |
| H31 | Operational sources → derived report generation | Separate advisory lock/transaction, source+recipe digest, INCOMPLETE→READY only after full image/export/consumer readbacks. Failure rolls back derived rows and preserves operational root/next-day eligibility. Resume must not call calculation. |
| H32 | Operational/report results → attempt/observer handoff | Attempt status reflects the committed run; report failure may leave COMMITTED with INCOMPLETE reports. Worker termination, no jobs/clients/transactions and preservation are independently checked. The prior observer's exit-time `/proc` race is a separate orchestration defect, not the force-source failure. |

## Bounded correction and proof requirements

The final correction addresses reachable reader mismatches in force/transit,
typed predecessor histories, supplier projections and post-commit current-master
verification. It does not broadly relax all list validators. Shared live-producer/
master/input validators remain frozen. Post-DBM source recipe identity explicitly
includes the new lookup helper and underlying Norm RRR source, so a later change
to either cannot silently retain the same producer recipe digest.
BOR/RRR candidate lookup changes are restricted to the source producers called
after DBM; they preserve matching occurrence order and legacy ambiguity errors.
No formula, catalogue, SQL, scalar assignment, action policy or schema changes.

The actual large snapshot shows explicit source policy flags,90-day complete-day
retention,90-day BOR/RRR histories,97097-pair population and10256 opening orders.
The source catalogue contains384 typed business tables; the two export tables
bring the post-stop typed-output check to386. The current-master phase already
passed at1602.155s on the failed large attempt. Its cost remains visible; this
audit does not invent a whole-phase SQL/client split or optimize it speculatively.

Evidence requirements are separate:

- Source freeze and exact changed-function/caller boundary.
- Reproduced old failures, including the empty-shipment/large-standards case.
- Native value tests for NULLs, signed/zero quantities, dates/cutoffs, field and
  ownership denials, duplicates, case/trailing spaces and ambiguous joins.
- Complete before/after component outputs **and errors** against pinned old
  source, with independent existing native-value assertions.
- Actual PostgreSQL10001-row force and history readbacks plus late SQL rollback.
- A real small native day with the three April8 capture policies enabled,
  actual persisted SQL rows exercised as spools, atomic commit/readback, report
  failure/rebuild without calculation, and exact own successor admission.
- Unchanged working metadata, prior attempts/archives/roles and protected services;
  explicit terminal result and cleanup of only the owned scratch resources.

Architecture recommendation, component qualification, integrated SQL proof and
large operational acceptance are different claims. The last remains pending.
The audit cannot prove that every future input is executable or promise there
are no unknown defects. It closes the enumerated current producer/consumer
contracts and states any unproved boundary before another large execution.

External evidence root:
`D:/freshvcf-build/evidence/daily-contract-audit-20261021/section11/post-dbm-persistence-audit-20261022`.
Key artifacts: `scope.json`, `baseline-representation-probes.json`,
`change-history-blame.json`, `upstream-freeze.json`,
`contract-field-catalogue.json`, `source-join-differential.json`, and the
`post-dbm2-*` integrated proof and `post-dbm4-*` read-only projection proof source
manifests, SQL logs, resource observations and terminal results. `post-dbm1`
retains the stopped Decimal-versus-wire test-fixture comparison; `post-dbm3`
retains the wrong-runner wiring failure. Neither is counted as a passing proof.
The final local suite's older mode-admission mock was brought up to the existing
production-manifest/receipt signature; no production guard was relaxed.

The old launcher's exit-time RSS race is separately reproduced and a bounded
correction is prepared in `observer-exit-race-correction.patch`/`observer_rss.py`.
Four component cases cover valid live RSS, terminal empty/failed proc reads,
and a still-live worker with unknown RSS that must fail closed. The original
failed launcher is unchanged. No new execution packet was assembled; future
runner integration and pins must include that tested helper before execution.
This is not an assertion of a successfully observed corrected large run.

This document records the contract/decision; actual proof status belongs only
in `TRACKER.md` and the terminal evidence, not in an unchecked completion label.

## Subsequent approved execution preparation

The user subsequently approved only the described preparation, explicitly
excluding further scope. The narrowly permitted pre-execution exception is
capture/admission plumbing for one child of the failed v4 attempt. Migration
0166 adds the nine-record prefix/admission functions and dispatch while keeping
the existing v3/v4 admission and lifecycle branches. No operational state table,
business column, calculation, DBM/BTR rule, input or action policy is changed.
The original nine records remain immutable; another retry is not admitted.

The exit-observation correction is integrated in the external prepared launcher.
The launcher consumes an already built, pinned image rather than rebuilding.
Both host and container entrypoints explicitly deny execution while the packet
records the large run as paused. The one-time schema transition is prepared
separately; it is not part of `execute_day` or an ordinary daily migration.

Focused evidence for this preparation is under the existing audit evidence
root's `retry-preparation` directory. It reuses the successful persistence
campaign and adds only the changed schema/admission/capture checks, observer
integration checks and actual-image read-only compatibility checks. Preparation
does not itself claim a corrected large-day result or authorize serving changes.
