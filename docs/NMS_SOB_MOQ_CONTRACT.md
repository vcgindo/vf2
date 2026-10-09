# SOB / MOQ bounded source contract

> Retained family-source contract from25b4fad. Historical proof and approval statements below apply to that original delivery. Current3005 integration proof and limits are in [MDM_3005_CODE_DELIVERY.md](MDM_3005_CODE_DELIVERY.md); no fixture approval or runtime acceptance transfers implicitly.

Authority: deployed DLL SHA256
`0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346`.
The hash was checked before decompiling the two relevant processor types.
Evidence directory: `D:/freshvcf-build/evidence/nms-sob-moq-20261008-001`.
This is a contract map, not a status tracker. See MIGRATION.md for status.

| Boundary | Source / owner | Contract |
|---|---|---|
| Eligibility/configuration | Read-only retained Importer MasterMapper/UI_MDMConfig, master4/5; source-receipt.json | Both enable Add/Modify/Remove. MOQ destination visibility is configured, not a fabricated default. |
| Current SOB | Deployed MDMProcessor.GetData case4 | Raw SOB, product/location scope, left descriptions and approved queue join (multiplicity preserved), descending SKU/location/supplier ROW_NUMBER. |
| Current MOQ | GetData case5 | Raw1/Raw2 chosen by setting; SKU scope; left SKU description; descending SKU ROW_NUMBER. Do not substitute effective MOQ. |
| Supplier read scope | DLL GenericFunction.getAuthQueryForReports | Expand selected parent IDs to distinct matching child IDs, then join normalized hierarchy triples; preserve duplicate permission/attribute occurrences and exclude NULL join components. GenericFunction.deployed.cs SHA256 652e5d80da8d3555c9782756f7143fbe467447cece2336776396c2f670f5044c. |
| Approver assignment | DLL MDMProcessor.GetSKUWHIds plus existing user-service api_gateway.utils.getAllUserDetails | Exact leaf hierarchy IDs intersect the approver's stored grants. Root read permission alone does not assign a supplier task. The gateway keeps only active approvers sharing stored grants with the requester. |
| Drafts | DraftProcessor; retained DraftSOBMaster/DraftMOQMaster schema | Text business columns, row ordinal, error/warning; existing owner checks and shared mixed-draft limitations. |
| SOB submit | AddModifySOBMaster IL67005–68688; RemoveSOBMaster IL71214–72146 | Trim/lower scope checks for add/modify, exact native existence checks, SKU/location/supplier grain; modification conflict is SKU/location based. Requested SOB is float53. Add/modify queue marker1; removal has its own native marker. |
| MOQ submit | AddModifyMOQMaster IL42258–44053; RemoveMOQMaster IL74691–75864 | Format-specific eligibility; MOQ int32; requested location nullable. With-destination modify eligibility checks SKU/location (without supplier). Do not silently strengthen this. |
| Decisions | TaskStatusProcessor.PostMasterAfterApproved, UpdateApprovedData | Row status3 approves/status4 rejects; requested Approved/Reverted retained; absent-key INSERT SELECT preserves duplicate occurrences. SOB update uses NULLIF(value,'') (numeric zero treated as empty). No effective allocation recalculation at approval. |
| Raw input consumption | NMSImportData.sql:500–568 | Delete matching raw rows for Approved=1, then insert ActionType=1/Approved=1 rows; SOB triple grain, MOQ selected-format grain. Reverted is not an extra eligibility predicate. Description refresh uses Intermediate LocationMaster with the canonical undefined name. |
| Archive/clear | NMSArchiveInputData.sql:53–74; NMSClearInputTables.sql:29–39 | Archive all SOB rows and only configured MOQ format; clear approved rows from all three queues. Captured revision only in the modern atomic publication boundary. |
| Task completion | NMSTaskStatusUpdate.sql:157–208,349–397,466–483 | Approved history drives pending→updated transitions; task/history prune and native raw-table references must be preserved. Capture tasks with the same revision. |

Application raw masters, submitted requests/history, approved queues, and immutable
run captures are separate typed owners. Existing reports are not an editable
bootstrap source. No JSON business payload storage is authorised.

Captured revision ownership: supplier queues have an internal monotonic revision,
excluded from native/current/feed/archive business columns. Every native scalar
UPDATE advances it, including unchanged NULL/zero fallback. Publication archives
the frozen values and clears only an unchanged captured revision; a later scalar
revision remains pending. Keys/flags cannot change under that revision token.
Supplier task decisions have a separate typed generation. If a decision arrives
after capture, all captured transitions for that task are deferred together;
its current history/status is processed by the next capture. This does not claim
per-decision partial completion inside one concurrently edited native task.
Per-source advisory locking serializes approval against capture/publication.
Autocommit approval retains native statement commits; it is not wrapped in a new
whole-request transaction. The daily capture lock precedes its repeatable-read
snapshot, and is released before calculation so later approvals remain possible.

Qualification traps retained for explicit tests:

- Recovered C# differs from the deployed DLL in supplier-grain SOB checks and
  MOQ current-table selection. Only DLL-derived evidence governs.
- MOQ modify history selects MOQDataRaw1 even when WithDestLoc is selected.
  MOQ remove history also uses Raw1. A requested WhCode column can therefore
  fail natively. Native failures cannot be repaired implicitly.
- MOQ getValuesForAddModifyMOQMaster preserves the requested action marker;
  NMSImportData inserts only marker1. Do not normalize marker2 into marker1.
- WithoutDestLoc pending-add history handling in NMSTaskStatusUpdate references
  MOQDataRaw2. Do not substitute Raw1 as an apparent correction.
- Native SQL UPDATE with competing unequal duplicate matches is incomparable;
  do not select an invented winner.

Finite fixture roster: retained SKU/location identities with explicit external
supplier settings/requests; SOB add/modify/remove, fractional float and zero,
identical duplicates, NULL raw values, approved/rejected/partial rows; MOQ
WithDestLoc and WithoutDestLoc, zero/int32 boundary, both matching and unrelated
destinations; scope denial; capture followed by later approval; failed
publication then same-capture retry; current/task/history downloads and restart.
No calculated Norms or temporal run is an input fixture.

Browser facility: the retained Playwright1.55 image contains Chromium1187.
An owned restart=no,4GiB/twoCPU container successfully rendered a data URL with
network=none and no port mapping. The real journey will use a private owned test
network; this probe establishes availability only, not application acceptance.
