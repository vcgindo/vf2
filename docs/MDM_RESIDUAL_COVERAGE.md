# Residual MDM coverage: source reconciliation

> Retained family-source contract from25b4fad. Historical proof and approval statements below apply to that original delivery. Current3005 integration proof and limits are in [MDM_3005_CODE_DELIVERY.md](MDM_3005_CODE_DELIVERY.md); no fixture approval or runtime acceptance transfers implicitly.

9 October 2026. Baseline `71ce853d6e8532eb4407173e347a7e998c91b6cb`, branch `codex/nms-sob-moq`. Supporting evidence for the sole status tracker, `docs/MIGRATION.md`; this document is not a new execution queue.

**Disposition:** destination MOQ behavior is already implemented through master 5 and its format setting. Master 14 has no independently reachable operation in the selected canonical route. The ten fixed retail entries are configured but have no reachable canonical business-data operation in the retained source. No concrete missing port was found; no alias, retail reader or implementation proposal is warranted by this reconciliation.

## Authority and limits

The approved scope is exits A–C of `docs/MDM_RESIDUAL_COVERAGE_PLAN.md`, with human approval verified in controller turn `01a11dbd-ca0d-7e90-bb1d-f2933059ca91`. Approval supersedes that plan's pending wording only for source reconciliation. It does not authorize implementation or runtime work.

Canonical SQL below is under `F:/VFlow_Local/local-runtime/mta-engine/Scripts/DBCreation/`. Retained DLL-matched extractions and user-service source are under `D:/freshvcf-build/evidence/nms-sob-moq-20261008-001/` (abbreviated **E**). The deployed DLL is `F:/VFlow_Local/local-runtime/mta-latest/VectorFlowAPIs.dll`.

| Source | SHA256 |
|---|---|
| Deployed DLL | `0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346` |
| E/MDMProcessor.deployed.cs | `f46e2fc1db36007ee29ea2de4574eca2017ceea268db55eea6b62fa9b16779c8` |
| E/TaskStatusProcessor.deployed.cs | `37d67850dcf255961643435b9079df858929a51876b5c6bad12d1e9761c6bc76` |
| MasterMapper_2.0.sql | `f6c3c800e643fd01101397c864bfc21eddf2f7fbb374287068d39aef83ceb967` |
| UI_MDMConfig_2.0.sql | `ffda9ff6f3395746303432eb24ef2f4aa63aa1cc7ba0a403d11fea8a3c6131dc` |
| Retained/current master_validation/urls.py | `147598f0eb5204a5eccaf09307c99aced848d2684f51136da1860f9b50936a4e` |
| Retained/current master_validation/db_config/db_mappings.py | `a20bd9ee860468f96229bdc9f661b0c564cc9089ae7e2eaa1abf6a704eea3aaa` |

The latter two retained files are in `E/user-source-001/`; their current counterparts are in `user-service/`. The retained compressed MasterMapper/UI_MDMConfig database snapshots cover only SOB/MOQ. Their absence of retail rows is not proof of a complete live roster. This conclusion concerns the pinned SQL, deployed standard dispatcher, and retained retail routing source; no live configuration or service was queried.

## A — Destination MOQ route and ownership

`MDMProcessor.GetMasterUIConfiguration` (line 193 onward) joins mapper and UI rows by MasterId and filters mapper action flags. Mapper row 14 (`MasterMapper_2.0.sql:83`) has action flags 1/1/1 but no corresponding UI row, so the inner join cannot select it. UI rows 127–130 describe master 5: `sc=SKUCode`, `wc=WhCode`, `spc=SupplierCode`, `mq=MOQ`. The seed's destination-field visibility does not create a new ID; retained configuration governs visibility.

The unchanged frontend sends the selected configuration ID (`frontend/src/VectorFlow/Pages/MTA/MDM/ViewModify/useViewModify.ts:563`). Its configuration selection at lines 265–293 rejects a query-string ID absent from the response. `frontend/src/helpers/MDMConstants.ts:72` maps MOQ to 5, with no 14 alias.

`MDMProcessor.GetData` case 5 (line 600 onward) uses `NMSMOQInputDataFormat`: `WithDestLoc` selects `MOQDataRaw2`; the other format selects `MOQDataRaw1`. `GetDataCount` case 5 uses the same selector. `ADDModifyMaster` case 5 (line 2141) dispatches add/modify to `AddModifyMOQMaster`, remove to `RemoveMOQMaster`. `TaskStatusProcessor.UpdateApprovedData` case 5 (line 2562) selects `NMSMOQWithDestination` for the destination format. None requires a standalone 14 route.

The destination grain is SKUCode/WhCode/SupplierCode with Int32 MOQ. The current reader projects requested aliases through the native conversion helper, applies SKU scope, left-joins description and uses SKU descending row numbering. It does not establish an extra location authorization or duplicate tie-break. Native NULLs, duplicate occurrences and queue semantics remain those documented in `docs/NMS_SOB_MOQ_CONTRACT.md`. Its existing producer mapping covers `NMSImportData.sql:500–568`, `NMSArchiveInputData.sql:53–74`, `NMSClearInputTables.sql:29–39` and the selected `NMSTaskStatusUpdate.sql` sections; no producer or comparison was rerun here.

Modern route: `mta/presentation/urls.py` → `mdm_views.py` → `mta/mdm/families.py` master 5 → `moq.py`/`supplier.py`. `supplier.py` selects `MdmMoqRaw2` for `WithDestLoc`; `supplier_tasks.py:35–43` selects the matching grain and queue, with submission/approval in that same module. `supplier_capture.py` owns the frozen queue/feed handoff. Typed owners in `mta/runtime/mdm_supplier_models.py` include `MdmMoqRequested`, `MdmMoqHistory`, `MdmMoqWithDestinationApproved`, `MdmMoqRaw2` and `MdmMoqWithDestinationArchive`. Raw/current owners remain distinct from calculated effective MOQ. Existing source coverage is sufficient; this is not renewed runtime acceptance.

## B — Shared retail reachability proof

All ten fixed retail mapper rows have NULL VF/draft/history/temp table mappings and action flags 0/0/0. `GetMasterUIConfiguration` therefore excludes them for add, modify, remove and the unfiltered action-list mode. An unrecognized nonempty screen type does not provide an alternate valid read-only query. Their UI rows contain display metadata and some enabled field flags, but **every TableField and DataType is NULL**. Field flags alone do not make a reader reachable.

The selected standard `GetData` and `GetDataCount` switches cover 1,2,3,4,5,6,10,13; selected write/task branches likewise contain no 14 or fixed retail ID. This alone would be insufficient because the frontend has a separate retail path:

- `frontend/src/VectorFlow/Services/MTA/MDM/api.ts:19,33,130,142,154` targets `/api/validate-master/` count/data/modify/add/remove URLs. `useViewModify.ts:578–622` selects retail count/data and all-data requests for IDs greater than 14.
- `user-service/apps/urls.py:65` includes that namespace, but `master_validation/urls.py:13–18` comments out all those business routes and the retail configuration route. The retained URLconf is byte-identical. Only basic validation and upload-progress routes remain active.
- `master_validation/db_config/db_mappings.py` contains nominal retail model mappings, but imports absent `models.prefinal_models` and `models.final_models`. `migrations/0002_delete_discountperiodmastermodel_and_more.py` records removal of former validation models. Dormant utilities and configuration views do not supply an active route.
- The active generic basic-validation view has an authenticated retail branch calling `RetailMaster` without importing/binding that name; the retained source has the same defect. The separate class file is not evidence of a successful business operation. Upload progress is not a business-data read/write family. These native limitations are preserved, not repaired.

No selected reachable retail reader identifies a producer to trace further. Consequently table types, row NULL behavior, duplicate preservation, ordering, data authorization and download behavior cannot be inferred from the display metadata or dormant model names. They are unavailable contracts here, not empty datasets or successful coverage.

## Fixed disposition matrix

`M` and `U` are line references in the canonical mapper and UI SQL files above. Alias ranges below are inclusive; exact labels/spelling remain in U. **R classification** means “configured but no reachable canonical business-data operation,” supported by the common chain above. Dormant targets are source hints only, not verified producers or modern equivalents.

| ID/name | Canonical rows and display aliases | Producer/owner and actual modern comparison | Classification / smallest change |
|---|---|---|---|
| 14 MOQWithDestination | M83; no U14. U127–130 belongs to 5: sc/wc/spc/mq | Native destination raw/approved queues; modern master 5 supplier route and typed owners described in A | Destination behavior covered through 5; standalone 14 unreachable. None. |
| 15 Contact(R) | M89; U253–256 (4): wc/cnm/cph/cem | No reachable producer. Dormant ContactDetail mapping; no installed modern 15 family | R; none |
| 16 Deployment(R) | M95; U265–298 (34): spsdt/irbf/swa1–20/sc/wc/wcp/nm/nmin/nmx/rlt/mvd/nhd/psz/rsna/rsnsa | No reachable producer. Dormant SkuLocDeploymentMaster. Modern 3 uses `skuloc.py:80` and MdmSkuLocCurrent/attributes; not this projection | R; none; do not alias to 3 |
| 17 DiscountPeriod(R) | M101; U306–307 (2): lp/TMDTFPS | No reachable producer. Dormant DiscountPeriodMasterModel, deleted validation model; no installed modern 17 | R; none |
| 18 ISTYield(R) | M107; U316–325 (10): mrosn/irosn/ph1–3/rnpmrc/deoss/cgmrp/ccp/scp | No reachable producer. Dormant ISTYieldMasterModel, deleted validation model; no installed modern 18 | R; none |
| 20 LocationCapacity(R) | M113; U334–339 (6): wc/ph1–3/cp/cs | No reachable producer. Dormant LocationCapacityMasterModel, deleted validation model; no installed modern 20 | R; none |
| 21 Location(R) | M119; U348–375 (28): wa1–15/wc/wn/wr/ws/wcty/wlg/gstn/wt/wst/ms/ss/pg/psg | No reachable producer. Dormant LocationMasterModels. Modern 2 uses `location.py:60`, MdmLocationAttributes/Description; not this projection | R; none; do not alias to 2 |
| 23 LocationPriority(R) | M125; U384–386 (3): ph1/wc/pr | No reachable producer. Dormant LocationPriorityMasterModel; no installed modern 23 | R; none |
| 24 PivotalSize(R) | M131; U395–409 (15): wc/ph1–3/pvt1–10/mpsad | No reachable producer. Dormant PivotalSizeMasterModels; no installed modern 24 | R; none |
| 26 Seasonality(R) | M137; U416–431 (16): wc/ph1–3/Jan–Dec | No reachable producer. Dormant SeasonatilyMaster monthly projection. Modern 10 uses `season.py`/`season_current.py`, MdmSeasonCurrent; 11/12 are date-range ADD workflows | R; none; no equivalence to 10–12 |
| 27 SKU(R) | M143; U440–483 (44): ph2/ph3/prc/cs1–2/uom/pf1/dcl/dtp/pf2/ph4/ph5/pf3/sc/sn/gc/sl/rplc/brc/vt/ph1/clrc/clrn/lp/sa1–20 | No reachable producer. Dormant SKUMasterModels. Modern 1 uses `sku.py:70`, MdmSkuAttributes/Description; not this projection | R; none; do not alias to 1 |

For every R row, TableField/DataType are NULL; thus display aliases do not assert physical columns or types. Examples of preserved metadata differences include retail SKU `rplc=replenishment_catery`, retail Location's region/state/city fields, and retail Seasonality's calendar-month columns. Similar names do not establish contract equivalence.

## C — Coverage and review disposition

**Planned workflow ports:** masters 1–13 are present in `mta/mdm/families.py`; the existing source-port delivery record remains intact, including combined masters 7–9 at the baseline commit. This bounded review finds no additional destination-MOQ workflow gap. It does not re-audit or revalidate every previously delivered workflow.

**Wider configured roster:** every fixed residual row is now classified. The ten retail entries are not functional reader coverage in either the retained native route or modern dispatch. Their presence in SQL metadata must not be presented as a completed wider retail application. Conversely, inactive native entries do not prove missing migration ports.

**Unverified:** live configuration, deployed retail service behavior, runtime routing, browser usability, integrations and the previously unverified recent source ports remain unverified. Migrations/source bindings retain their prior unapplied or unavailable qualifications. Prior fixtures, accepted receipts and failures are untouched; no earlier acceptance is transferred.

No reachable missing operation or unresolved source contradiction was found, so there is no missing-port implementation proposal. Activating dormant retail functionality would require a separate product/source decision, not automatic continuation of this migration review. Source reconciliation exits A, B and C are complete. Changes are limited to this document and `docs/MIGRATION.md`; no code, frontend, service, database or fixture changed. No tests or runtime checks were run. Stop for human review; no implementation commit, activation, merge or deployment is authorized by this artifact.
