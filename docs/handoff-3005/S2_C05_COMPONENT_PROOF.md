# C05 pre-execution component corrections

The native master3 audit/history path and phase task completion now pass 21 focused PostgreSQL tests, with no skips. This is component evidence only: C05 remains unfrozen, its business database is uncreated, and none of its thirteen MDM family acceptance rows is closed. The sole status authority is `F:/freshvcf/docs/handoff-3005/TRACKER.md`.

## Corrected behavior

- Stop PIPO task completion remains pending as in canonical NMSTaskStatusUpdate; queue consumption and calculated stop effects are unchanged. Add PO/PIPO completion and target-task pending behavior are covered separately.
- SKU/location history maps staging StockPercentForRat to StockPercentForRationing. Modify/Remove record the submission database date in historical SKUIntroDate; current introduction dates remain unchanged.
- Three typed source-owned audit tables retain native Add/Modify/Remove submission values and reviewer decision occurrences. Actor names, timestamps, NULL fields, duplicates and rejection-before-approval ordering are preserved within the small-request boundary.
- Explicit blank spr/npr values become 100/0 in the native request/audit projections. Missing or unreadable configuration fails before submission writes. During approval, the same failure occurs after business effects but before audit/task completion, matching native statement order.

Canonical statements come from the retained DLL-matched MDMProcessor.deployed.cs (SHA256 f46e2fc1db36007ee29ea2de4574eca2017ceea268db55eea6b62fa9b16779c8) and TaskStatusProcessor.deployed.cs (37d67850dcf255961643435b9079df858929a51876b5c6bad12d1e9761c6bc76), under `D:/freshvcf-build/evidence/nms-sob-moq-20261008-001`. History: Modify3929–3942, Remove3492–3505; submission audits: Add5414–5420, Modify3943–3947, Remove3506–3518; blank defaults3260–3276/5816–5828; approval1228–1239 and EntryInLogTable2752–2864.

## Verification and preserved failures

Fresh database `handoff3005_s2_c05_component_20261014_001` uses the existing bounded isolated PostgreSQL/worker and retained test principals. Real migrations through0129 were applied, with no fake migration, reset, flush or business initialization. The original component database remains at0119.

The first physical-schema check found inherited NOT NULL on Modify audit ParentWhCode. Already-applied0128 remains immutable; additive0129 makes that column nullable. The final check compares every audit column, type, nullability, length, precision and scale with the pinned canonical DDL. Both migrations are in the native implementation digest.

Earlier failures remain in evidence: the original rationing history TypeError, the physical-schema mismatch, a rollback test missing its frozen profile metadata, and an audit test attempting to update immutable configuration. Fixtures now supply complete profile identities and create the intended immutable configuration initially; no assertion was weakened.

Final `c05-audit-component-v5-proof.json` records all21 passing tests and equal complete business-row snapshots before/after rollback-only fixtures. Django check, makemigrations --check and diff whitespace checks pass. Independent review accepted the bounded correction. All six protected serving instances and both owned container identities/resources remain unchanged, with no host port mappings or OOM.

`S2_C05_COMPONENT_EVIDENCE.json` binds retained external logs, scripts and receipts. This proof does not establish own-successor workflow acceptance, full report values, audit export/retention, UI behavior or unrestricted batch parity. In particular, native approval batches over999 rows interleave business/audit statements per chunk; the current modern path handles the whole decision list. C05 uses small requests. That larger-batch deviation remains explicit and must be resolved or bounded before broader acceptance.
