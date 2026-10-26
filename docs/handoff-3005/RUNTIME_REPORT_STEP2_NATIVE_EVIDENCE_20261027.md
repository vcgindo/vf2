# Step2 runtime-report recovery and authenticated delivery evidence

The sole status authority is `F:/freshvcf/docs/handoff-3005/TRACKER.md`.
This records the fixed bounded proof submitted for independent controller review.
It does not release general Step3, a serving switch or general G2 acceptance.

## Pinned implementation and fixture

- Target: `52f2227366ee8c71dd4233d26ba1c23c3f3dd1a6`; image `sha256:8f025e44b66d2ffc156cc38f0e7f300f67f14deb503a1de5bc780d24d65fd079`.
- Writer-disabled compatible reader: `59f6d7aaa255a639068f054617c0fc9e3a9fdbb4`; image `sha256:d3ea89d175acb2e92cb2f7d5b181027e8fa6a41ceafdcd0b14331e163b97c076`.
- Database: `vftest_fresh_runtime_step2_integrated_retry_20261027`, OID **712333**.
- Initialization: `8307cf3f-a2cd-4a64-9f93-0696e5e8f957`.
- Own Full23/24 predecessors precede UptoDBM25/PostDBM run `eb4a58fe-3ddd-469b-ab08-7fb5d2112e45`.
- Final output digest: `c046df7858205617e48bf09caf3b0f2f6e24aaf651bbceff69b9d29c28c54625`.
- Direct human approval: `call_779ed866c15f48fd835466a08b47fd86/0`; proposal SHA256 `7f22209bdcdac0d0b455e4fd6586fa3bffdd996b9aa2d5333099b5bcc9295ca2`.

Evidence root: `D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/runtime-step2-20261026`.
The adjacent `RUNTIME_REPORT_STEP2_CHECKPOINT_20261027.json` pins the exact evidence files, byte sizes, SHA256 hashes, releases and complete report digests.
The index contains 74 artifacts; SHA256 `d3f21b499e1e298f443d9f4cb8d66476cb44d17649f1db581fb126d31442f043`.
Paths below are relative to that evidence root.

## Fixed proof matrix

| Boundary | Evidence and exact qualification |
| --- | --- |
| Scoped master ownership | Accepted DBM ancestry, pending final owner and producer/source roots are checked again at master acceptance. Intake reuse=true and actual producer reused=false remain distinct. The native configuration cut is41/312 to 41/402 from 90 actual writer statements, including empty VFSettings contributing zero, with no extra master increment. `integrated-retry/final-readiness-proof.json` proves fresh-process readiness and committed ancestry. |
| Scoped recovery | Phase/action/scope and copied-authority denials; competing continuation exclusion; pre-final file failure; real worker exits before first new registration and after five report/master writes; rollback and exact-worker fencing; postcommit acknowledgement loss and exact original-receipt retry. Prefix, prior files, counts and all five epochs are preserved. See continuation/filefault/concurrency, beforeinsert/beforecommit recovery and `integrated-retry/scope25-native-result.json`. Failures before injection are not counted as disconnect proof. |
| Typed sources and files | All eight scoped reports compare complete typed occurrence multisets and applicable ORDER BY groups against independent SELECT transcription over actual persisted sources. Complete headers/cells, file catalogue ownership and CSV/ZIP member bytes pass. Phase placements retain PRE/BPR/DBM owners; terminal placements bind to sealed DAY_FINAL. `integrated-retry/independent-report-proof.json`. |
| Permission transition | On approved original Full DB583444, packaged 0231-to-0232 adds only consumer EXECUTE on existing SECURITY INVOKER `runtime_report_publication_source`. Bodies, old ACLs and writer authority remain unchanged. Packaged rehearsal, late-fault rollback, commit, repeat/readback and accepted/failed-run preservation pass. `consumer-upgrade-*-proof.json`. Applied 0229/0230/0231 were not edited. |
| Fresh and compatible consumer | Fresh 0232 role/schema checks pass. An actual restricted runtime session consumes all five scoped receipts and eight files after supported code admission. ReceiptUPDATE, stageDELETE and writer-helperEXECUTE deny; the compatible reader rejects new publication and continuation entry. `integrated-retry/schema-role-check-proof.json` and `bridge-readback-proof.json`. |
| Native selection | Initially declared existing BOR output policy and actual own-predecessor ExcessProjection preparation satisfy complete DailyUiPublication/Planning summary. Existing native selection is used; no alternate selector, fakeREADY, old-run exception or retroactive input repair. `integrated-retry/download-selection-proof.json`. |
| Restricted native HTTP | Existing GetAllReports/DownloadReports return all eight descriptors/names/dates/bytes under the runtime role. Missing identity/entitlement, empty/foreign grants, foreign/stale owners and invalid selector deny. `integrated-retry/api-download-proof.json`. |
| Authenticated delivery | Real password login, cookie JWT, persisted admin scope expansion and HTTP gateway forwarding return exact eight-file bytes/headers. Forged client identity/grants are overwritten; missing/invalid authentication and unsupported POST deny. Actual image, native release, DB/OID, runtime role, source, run, selection and admission are verified before HTTP. `integrated-retry/auth-gateway-proof/proof.json`. Permission/foreign-owner negatives above belong to native-layer proof, not a fabricated non-admin login. |
| Retained Full proof | Unchanged Full publication/atomic master-report rollback/lostACK/typed eight-report proof remains source dd6e3477, run 4d0eddeb-5bb4-4252-91c8-1c09ce3a7839, under `master-retry/`. Source 52f22273 changes only scoped configuration-image validation. This reuse does not assert a new source 52f22273 Full replay or matched Full/split campaign. Step1 remains closed. |
| Preservation/resources | All pre-existing database run/phase/report fingerprints, including earlier failed scoped trials, remain unchanged. Build archives were verified against every decompressed and original file hash. PG 384 MiB / 0.5 CPU; worker 4 GiB / 2 CPU, one worker/build; private auth proof 512 MiB / 0.5 CPU. No public ports. Final accounted bytes including 512 MiB reserve: 4501908691, below 4.25 GiB; growth 648748819, below 656 MiB. Temporary proof containers removed; serving auth/MTA/frontend identities and 8080 unchanged. `integrated-retry-final-preservation.json`. |

## Report populations

These counts identify the compared populations; acceptance uses all typed cells and file bytes, not counts alone. Complete typed and CSV/member SHA256 digests are in the checkpoint JSON.

| Id | Rows | Columns |
| --- | ---: | ---: |
| 2 | 12 | 24 |
| 3 | 12 | 24 |
| 4 | 4 | 31 |
| 5 | 0 | 31 |
| 6 | 0 | 31 |
| 7 | 2 | 12 |
| 8 | 12 | 34 |
| 10 | 8 | 107 |

## Preserved failures and corrections

Earlier scoped run d5db7a0d exposed intake-reuse/actual-producer and terminal-parent ownership errors. Source c1de53d3 corrected that handoff and the consumer ACL interface. Its new run b4382bea then exposed an omitted canonical empty `Importer/VFSettings` image before disconnect injection. Both accepted prefixes remain preserved. Source 52f22273 admits only the five installed configuration-domain table names, keeps exact zero/per-row/COPY accounting and rejects unknown tables. 21 focused checks pass; corrected native recovery is the replacement run above. No frozen request was forced onto changed code.

Readiness harness 01 nested an API-owned snapshot ; 02 retained a duplicate call due to line-ending replacement ; 03 passes after observer-only correction. Auth harness 01/02 stopped at the nested read-only mount destination ; 03 reached auth startup and exposed missing terminal run/digest environment pins ; 04 passes with pins from the validated complete selection and existing catalogue preflight. Original logs remain. These repairs changed no production authentication, schema, calculation or accepted state. The first local compatibility probe stopped on absent native pins; its misleading status is explicitly superseded by `integrated/config-correction-compatibility-boundary-02.json`, a labelled local component test, not native compatibility acceptance.

## Explicit limits

- Chennai/P041 and Silvasa/P001 populations are empty; nonempty applicability is unqualified.
- Source keys satisfy retained uppercase ASCII/collation constraints; ambiguous latest-remark ties are absent. No new tie-break or universal collation claim.
- Complete CSV/ZIP member bytes are verified; native 7Zip container identity is not claimed.
- Independent downloadable RRR remains explicitly disabled/unqualified. RuntimeReport Id3 RRR WH Efficiency is enabled and verified.
- Hooks, InputData, BOR presentation and optional-output dispositions apply only to the approved owned test. No production defaults are inferred.
- No final browser run, 8080 cutover, visual redesign, MTO change, general Step3, matched Full/split proof, latency/scale acceptance or G3 release.
