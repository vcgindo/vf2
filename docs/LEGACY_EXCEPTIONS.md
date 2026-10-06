# Legacy behavior and explicit exceptions

## LEG-BOR-APRIL-SUPPLIER-TIES — unresolved ordering, no exception yet

Exact April7 fixture bfd75b4b-a9df-4a08-82d3-852e3324b623, native digest
4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73:
deployed DLL0222eb96 getBORSelectQuery/GetBORData orders DispatchColorSequence,
DispatchPen DESC, SKUCode, WHCode; export reverses only the last two keys.
Neither adds SupplierCode. Independent complete1196-row comparison preserves all
values/types/NULLs/duplicates but strict sequences differ first at grid index343
for SKU729939070711/locationP064/color-sequence1/penetration100: suppliers102117
and101679 exchange positions. Export first difference is index387 for that pair.
Original arrays and strict failures remain in bor-family-20261006-001/
comparison-consumers-002.json, oracle-consumers-002.json and modern-consumers-002.json.
The raw selector is pinned in select.il.txt; native-csv-001.json preserves the
actual deployed CsvHelper output. No ordering assertion is waived. A requested
April-only tied-group comparison decision remains pending; an existing Expedite
exception does not transfer to BOR. No algorithm/query/tie-break change.

## LEG-BOR-UNESCAPED-LITERAL — unsafe native input remains NOT_PARITY

Deployed BOR remark append/history concatenate quoted values without escaping
(BPRProcessor IL96894–97156, DLL0222eb96). The modern parameterized paths deny
apostrophe-containing input with503/unavailable rather than execute arbitrary SQL.
This is explicitly NOT_PARITY: a benign unescaped value such as O'Brien normally
reaches the native swallowed-provider-error result, while other crafted strings
can parse differently. No universal native outcome is claimed and no injection
behavior is reproduced. Typed PostgreSQL test_bor_sources records denied input,
no append and preserved source/history state. This does not excuse differences in
ordinary remarks, actor ownership, NULL handling or timestamp multiplicity.

## LEG-BOR-PRODUCER-CONSUMER-BLACK — unresolved, no exception approved

6 October 2026 BOR qualification: pinned deployed DLL0222eb96…346,
`BORProcessor.getBORSelectQuery` IL17196–17261, requires SupplierDispatchReq
ReqTopOfBlack and CumulativeTOBlack. The canonical GenSupplierWiseReq.sql
SHA256 `fae0668e77fb3e149f62301f4e5e3cda1c1b546180a66f8262ca899644f16a9b`
(identical preserved counterpart) inserts no Black columns; modern
`calculate_bor` emits only red/yellow/green/blue bands. No inferred zeros,
cross-band derivation, column omission or engine change is authorized.

Affected contracts: complete BOR grid/count/export and typed calculated
publication. The original April7 backup SupplierDispatchReq contains1196 rows
with both Black columns. Those rows and its SOB97/MOQ1496/remarks27 populations
are outside the selected fixture's loaded input union; read-only PostgreSQL
qualification confirms no source tables/receipts. Selected run is
`bfd75b4b-a9df-4a08-82d3-852e3324b623`; no other run's results may fill this gap.
Producer-time SKULocAtt01–15 (SLSAttr aliases) also remain distinct from the
current E.c1–15 consumer join (SKULocAttr aliases). No snapshot substitution.
This records a source-version conflict, not accepted parity or a legacy repair.
Evidence and file hashes: `D:/freshvcf-build/evidence/bor-family-20261006-001/source-qualification.json`.

Bounded retained-source follow-up: the exact existing READ_ONLY April7 clone
contains1196 complete BOR rows; each Black field has398 positive and798 zero
values, noNULLs, sum965049. Both have schema default0 and no computed definition.
No retained SQL module references the fields/table; no per-row calculation run/date
exists. These are usable retained snapshot presentation facts after an explicitly
bounded consumer-source extension, not evidence for the missing modern formula.
Do not label the entire UI source unavailable because the producer mapping is
missing; do not claim fresh computation or explain individual zero values without
evidence. Receipt: `D:/freshvcf-build/evidence/bor-family-20261006-001/retained-rows/receipt.json`.

Additional direct failure evidence: retained
`F:/VFlow_Local/local-config/ErrorLog/2392026_Logs.txt`610–611, dated23September2026,
records Get BOR Data Count failing with Invalid column name for ReqTopOfBlack
and CumulativeTOBlack. RunCoreBPR.bat64 invokes GenSupplierWiseReq and pinned
BPR_DBCreation.sql1488–1517 defines no Black fields. Supplied downstream BTR
attribute updates and rationing-history reads do not supply their producer.
This confirms a prior API/schema mismatch; it does not invalidate the April
positive stored values, justify zero-fill, or identify the prevailing producer.
Exact source hashes/excerpts: `D:/freshvcf-build/evidence/bor-family-20261006-001/producer-version-anchors.json`.

Do not repair legacy algorithms or add invented ordering to make tests pass.
These known risks remain visible; neither is permission for blanket exclusions.

| Source | Issue and impact | Fresh-build treatment |
|---|---|---|
| BPR/Ration_Scripts/CalculateDD.sql | Unordered multi-row identity insertion can assign different OrderKey priorities, affecting allocation | Preserve raw evidence; no invented sort or expected allocation. Compare only where source semantics are defined; unresolved branch remains unaccepted. |
| DBM/Norm 0-1-2 Reports/Norm0Data.sql and related occurrence aggregates | STRING_AGG without declared order can change presentation text | Identify exact affected fields. Numeric/state parity stays strict; no auto-approved normalization or concealment. |
| DBM selected profile | Existing modern code has explicit unsupported guards for conditional rule/auto-acceptance profiles | Classify against actual canonical settings. Presence of a guard is not implementation or parity. |

Each reproduced flaw must add source hash, input hash, observed outcomes and
the narrow affected contract. Independent implemented contracts may continue.

## Planning overview empty-permission quotation — NOT_PARITY

The pinned deployed SCIH `GetQuadrantDetailsQuery` quotes permission ID lists
before calling GenericFunction. For an empty list it passes `''`; the helper's
empty-expansion fallback quotes this again, yielding a literal apostrophe in
the final SQL string_split/INT permission comparison. Source hashes:
SCIH `f709a448c1bb6f6af6583975a13a88cf3cb009caee516bc2fe867af21eb624e5`;
GenericFunction `6850a0bf2eadb4a38a2998e96ef70a264a2bc529d0de5c433c066d76c1933420`.
The exact conversion expression reproduced SQL245 in the owned Fresh SQL
connection, recorded with both denied requests in
`D:/freshvcf-build/evidence/f3-planning-overview-003/receipt.json`
(SHA256 `14f588968bd1cdbf44cdcb862381bda0a7f89d39369b168d97b1a87ff60f94ae`).
This is source analysis plus SQL-expression reproduction, not a claim that the
entire deployed HTTP request was run. Modern empty memberships return zero
counts under the existing denial semantics; those20 guard values are explicitly
NOT_PARITY. All40 positive-scope overview values remain exact comparisons.
Do not repair the helper, manufacture a passing legacy empty response, widen
permissions or carry this qualification into a valid positive scope.

## LEG-NORM0-OCCURRENCE-ORDER — reproduced on the retained full estate

The first fresh full-estate run stopped at Norm0's report on June6, before
publishing day0. `f2-auto-sizeable-001/execution.json` is retained as FAILED,
not parity. Input SHA256 is
`0f3084b7a6fb60b84edbd7c4dc01fef3c4b40f1a7c389ec82f88b9ad22519546`.
Canonical `Norm0Data.sql` SHA256 is
`c47103cd5d309c8d692766fcef798ab138694627d944dee7c3d25619c9ed9766`.
Its inner and outer STRING_AGG have no ordering clause. The retained canonical
reproducer already shows differently ordered sixteen-fragment text for
SKU5405 at LDC002/LP001 on this exact input. Receipt SHA256:
`88534f720b108e7cf33d0fcd4e1310f9c3270b7e76a534ecbe0f2b5a57a83fc5`.

Under the user's canonical record-and-move-on rule, continue the independent
calculation/state chain using the existing explicit report-limitation mechanism.
`baseline/norm0-occurrence-limitation.json` scopes this only to Norm0/horizon30
rows independently proved ambiguous from the canonical daily state. No source
SQL, facts, Norm, allocation, count, sum, key, duplicate or other report field
changes. The modern ambiguous text stays unavailable, not invented or copied.
The affected text is **LEGACY_FLAW / NOT_PARITY**, including its truncated and
quoted export forms. Preserve every raw legacy value and compare all remaining
fields. A completed trial with this limitation must say
**COMPLETE_WITH_LEGACY_FLAWS**, never unconditional parity PASS.

This disposition does not authorize conflicting-parent-Norm resolution, changes
to Rule12 occurrence text, broader report omissions or hidden UI substitutions.
F3 must expose the limitation in the delivered report/readback.

## LEG-EXPEDITE-UNORDERED-LABEL — F3 consumer only

**Approved presentation amendment,3 October2026:** direct human response to
`call_7ZtUGdijA5CSTdAfXbs6XTwM`: "Approve both presentation exceptions".
Parent chart receiving labels now use each receiving location's persisted
LogisticsLocation. The child chart retains its existing transformation. This
supersedes the parent denial treatment below only; it is an intentional
presentation difference, not exact legacy parity. Calculated values, quantities,
permissions, persisted state and F2 remain unchanged.

April7 retained-fixture qualification (5 October2026): on run
`bfd75b4b-a9df-4a08-82d3-852e3324b623`, complete canonical broad/restricted chart
bags match the prepared datasets. Actual deployed-DLL calls reproduce the same
flaw: reversing only unordered critical rows changes all103 broad receiving
labels in both directions. The approved parent amendment changes only those
receiving labels to their own joined location labels (103 broad,6 restricted);
all other formatter fields remain exact. Evidence:
`D:/freshvcf-build/evidence/planning-prepared-20261005-001/expedite-chart-canonical/formatter-comparison.json`.
This demonstrates transfer of the existing parent-only presentation amendment;
it grants no child-label repair or SQL tie-order exception. Child ambiguity is
still unavailable, and SQL sequence differences remain an acceptance gap.

The same approval permits custom Expedite paging by persisted producer SKUCode,
WhCode and ParentWhCode, retaining native missing/NULL display fields and duplicate
bags. Native NMS identities are not filled. Conflicting values for the same
producer key remain unavailable rather than gaining an invented tie-break.
This ordering supersedes the custom undefined-NMS-order denial only and is also
an intentional presentation difference, not exact legacy ordering parity.

The pinned deployed DLL `0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346`
implements ExpediteProcessor receiving-location `LogisticsLocation` using the
last critical-chart model, not the receiving row. Its critical SQL has no ORDER
BY. Decompiled source SHA256:
`e78148cc38d5a802e014e6085111e79a40c2a6b462563e2bd412677505e654b4`.

Reproduced using the retained June17 report populations in
`D:/freshvcf-build/evidence/f3-expedite-charts-comparison-001/receipt.json`, SHA256
`e5aff4654c4878180a0984176e45dc28f99a30ec78794f8a9261b3f300c4750b`.
The original parent method input SHA is
`f44f5c06cbfd9641a05262dd5e17223cbc90bef5fdc58a0b8387a94023d722e3`;
reversing only its unordered critical rows preserves the exact query bag but
changes all five receiving labels from `PLCS21` to `PL001` in the actual DLL.
Both original/reordered inputs and DLL responses are retained. The pure method
was invoked under the recorded .NET10 CLR, not the legacy HTTP host.

Treatment: do not carry over the old demo's label repair or select a fabricated
last row. The application rejects an ambiguous chart response explicitly with
HTTP503 and this flaw ID. A deterministic scoped input may use the unchanged
source transformation; an empty critical population preserves the source's
NULL label. The ambiguous label/response is **NOT_PARITY**, not a waived match.
All14×69 post-report values, eight query bags and the pure DLL transformations
on explicit ordered datasets were compared independently. This does not alter
F2's calculations or its sole Norm0 qualification. Continue independent F3 work.

## Layout preference edge cases — F3 presentation only

Pinned DLL CommonsProcessor SHA256
`6a79e4cd927c3a4bee0f72c9dab6f327bfcfcf9ef7dda21f1c906e8762be767b`
and GenericFunction SHA256
`6850a0bf2eadb4a38a2998e96ef70a264a2bc529d0de5c433c066d76c1933420`
govern. Selected sequential layout operations are compared in
`D:/freshvcf-build/evidence/f3-ui-state-comparison-001/receipt.json`.

- **LEG-LAYOUT-UNESCAPED-LITERAL:** SaveState concatenates unescaped strings
  into SQL. The retained test `user's layout` reproduces a syntax error in the
  exact selected batch shape, using session-temp tables only. GenericFunction
  swallows SQL errors and returns empty text; Commons reports200. Modern rejects
  this branch explicitly as503/NOT_PARITY before changing rows; it does not
  invent a successful escaped-literal repair or reproduce an injection hole.
- **LEG-LAYOUT-UNORDERED-DUPLICATE:** the source table permits duplicates and
  GetState has no ORDER BY. Conflicting states have no defined selected value.
  Modern retains duplicate-capable storage but rejects conflicting values as
  503/NOT_PARITY, never choosing first/latest as a business rule. This is a
  source-backed ambiguity guard, not a claim of reproduced deployed divergence.
- Empty stored state differs from an absent row: GetSingleresponse returnsNULL
  for an existing empty/NULL scalar, but empty text for no row. The unchanged
  DBM frontend dereferences `.length` without a NULL check. Preserve the response
  distinction; do not silently normalize it to hide that frontend edge case.

These are not F2 calculation exceptions or blanket exclusions. The proven
layout contract is the selected sequential ASCII frontend payload; concurrent,
case/collation variants and malformed-input equivalence are not certified by it.

## LEG-RRR-FILTER-INVALID-SQL — selected report filter branches

Authority: canonical DLL `0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346`,
RRRProcessor `d59a23788cb992f0413fb39fe43744043acea57804432d4eda8e09a1ac8dda82`,
CommonsProcessor `6a79e4cd927c3a4bee0f72c9dab6f327bfcfcf9ef7dda21f1c906e8762be767b`.
Actual deployed `filterQueryForReports` was invoked, then its generated WHERE/
join text executed against the selected RRR query and accepted terminal facts.
Evidence: `D:/freshvcf-build/evidence/f3-rrr-filters-comparison-001/receipt.json`,
SHA256 `1cb7ff7fbd5952320d4a4e47242e722c0db5f11939dae5450bd319f08a9527b8`.

| Branch | Source-generated invalid reference | Observed SQLSTATE |
|---|---|---|
| Availability category | b.category absent from the joined pair table | 42S22 |
| PIPO/seasonality | tags absent from the selected joined tables | 42S22 |
| Availability numeric | a.availability absent from the selected Pick report | 42S22 |
| Coverage | coverage absent from the selected query | 42S22 |
| Color count | redCount absent; no required history-count join | 42S22 |
| Color age | btd.D90/Age absent; no required history/age join | 42S22 |
| Unknown operator | generated empty predicate () | 42000 |
| Unknown hierarchy p9 | generated sl9 absent | 42S22 |

Modern explicitly guards these branches with503 and this flaw ID. It does not
invent joins/default values, reinterpret categories or repair the malformed SQL.
These eight cases are **NOT_PARITY**; successful guarded rejection is not a
matching legacy HTTP error envelope. They are F3 consumer exceptions, not new
F2 calculation waivers. Continue independent valid filters. The44 valid retained
requests compare all row values/types/duplicate occurrences, counts and declared
order. This certificate does not cover arbitrary malformed/Unicode/collation
variants or a different report's aliases/populations.

## LEG-DBM-FILTER-INVALID-SQL — selected current-suggestions filters

Authority: pinned DLL SHA256
`0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346`;
DBMProcessor SHA256 `7339a2e04aab1b2c4108bb182721dfb057ab65267fcee027c88480e6c449aea5`.
Actual Commons.filterQuery overload e/i/f, six-group gate and ParentWhCode
replacement were invoked. Exact SQL reads independent retained pre-action legacy
state with the identical approved hierarchy supplement, not modern outputs.
Evidence: `D:/freshvcf-build/evidence/f3-dbm-filters-comparison-001/receipt.json`,
SHA256 `a9e9cc25d37316918f6322e88b9b78135f1315c8deabd2a30ac4d20abb7ef0e6`.

| Selected branch | Canonical defect |
|---|---|
| Stock/GIT/VirtualNorm/PIC/OHIC | Missing selected Suggestions/DBMMaster columns |
| Category/tags/availability/coverage | Missing category/tags/availability/coverage columns |
| Colour count/age | Missing btd/history/age joins |
| Unknown operator | Empty invalid predicate |
| Unknown p9 hierarchy | Generated sl9 absent |

13 frozen requests yield26 count/grid contracts LEGACY_FLAW_NOT_PARITY with
attributable42S22/42000 receipts. Modern503 guards are not legacy HTTP-error parity
or calculation waivers. Never invent missing fields/joins/defaults. Other82
contracts compare full typed populations/multiplicity. Custom-only filters,
including invalid operators, are ignored by the actual standard-group call gate;
preserve it, do not repair it. No arbitrary malformed/Unicode/collation certification.

## LEG-BTR-FILTER-INVALID-SQL — deployed count/grid filter distinction

Authority: same pinned canonical DLL; BORProcessor source SHA256
`80ceb4916ca4cd8567384a4598858cef55f8574007662b025aee237f20ab9298`.
Actual DLL Commons `filterQueryForReports` uses BTR aliases E/E/E/sa/la/sla.
Generated text was executed in the exact GetBTRDataCount/GetBTRDataAsync queries
on retained June17 facts and the identical run-bound hierarchy supplement.
Evidence: `D:/freshvcf-build/evidence/f3-btr-filters-comparison-001/receipt.json`,
SHA256 `fae017590847e047805d65883979b31e96fbdd2f9bdeb03b89f1f2f54e1a79b9`.

| Selected branch | Count | Grid | Observed reason |
|---|---|---|---|
| Stock/GIT/PIC/OHIC | PASS | NOT_PARITY | Grid E joins only five requirement fields; missing Stock/GIT/DispatchColor/PhysicalInventoryColor,42S22 |
| Availability | NOT_PARITY | NOT_PARITY | E.Availability absent,42S22 |
| Coverage | NOT_PARITY | NOT_PARITY | coverage absent,42S22 |
| Unknown operator | NOT_PARITY | NOT_PARITY | generated empty predicate,42000 |
| Unknown p9 hierarchy | NOT_PARITY | NOT_PARITY | sl9 absent,42S22 |
| Black/red colour count with hasvalue | NOT_PARITY | NOT_PARITY | OR inserted inside repeated-column operator yields invalid SQL,42000 |

These are14 count/grid contracts across nine requests, not14 calculation flaws.
Modern guards them with503/flaw ID and does not invent grid fields, repair SQL,
waive valid count comparisons or claim matching legacy HTTP error envelopes.
Unlike RRR, BTR category/tags and valid age/colour-count filters have actual
source joins and pass. The104 successful contracts preserve values, types,
multiplicity, key paging/rejoin, declared order and horizon labels. Certification
is limited to the frozen59 requests, not arbitrary malformed/collation variants.

## RRR export header-order qualification

Pinned BORProcessor.BuildHeaderQuery and StreamCsvFromQueryAsync, source SHA256
80ceb4916ca4cd8567384a4598858cef55f8574007662b025aee237f20ab9298, select visible
RationRequirementReport headers then stable-sort by Col_Position. The canonical
configuration has both SKULocAttr9 and SKULocAttr10 at position99 and the default
header query has no tie order. Export comparison001 matches the observed retained
sequence exactly. Universal ordering for this tied pair is not certified; no
new tie-break is introduced and neither column/comparison is dropped. Saved
layout array positions remain distinct and are compared separately. This is a
presentation ordering limitation, not a calculation waiver or a reason to block
independent F3 work. Valid empty saved layouts emit blank records as deployed;
no fallback to all columns is invented.

## RRR inherited history entry — unresolved source capability

The Stage2 requested RRR DailyDataGraph browser entry is absent from the pinned
inherited screen. At reuse revision66a77735d3f3f9a9becf4c87a08ae7827900cf84,
`RationedRequirementReport/useRRR.ts` calls `getColumnDefinationsMTA` with no graph
customization; its `grapCellRenderer` is empty. `index.tsx` has no history handler
or modal. `CellRenderersMapping` contains only five colour mappings. The older
`mapRRRColorBandWiseFieldsToColDefs` graph helper is not called by this screen.
Current files normalize byte-identically to that pinned source; hashes and actual
37-column3005 UI evidence are in `f3-stage2-rrr-001/rrr-inherited-source.json`.
This affects the requested RRR history-entry acceptance only. It does not waive
DailyDataGraph API comparisons or history in screens that wire the control.
No frontend repair or invented entry is authorized, and no full RRR parity is
claimed. The unresolved requirement remains in docs/MIGRATION.md.

## Description lookups — empty permission ID conversion failure

Pinned DLL0222eb96, GuidedInsightsProcessor.GetSKUDescription/GetWHDescription
and GenericFunction.GetAuthenticationCTEs use BufferTrend attributes/descriptions
and Importer permission records. When the relevant permission ID array is empty,
the caller supplies a quoted empty string and the generic fallback quotes it
again. STRING_SPLIT then supplies a quote to the integer permission-ID predicate;
SQL Server raises245 and the processor returns HTTP500/status500/data:null.
Fresh preserves this exact source failure for empty product IDs on SKUDesc and
empty location IDs on WHDesc. It does not invent a successful empty list.
This differs from valid permissions with native NULL hierarchy, which return
HTTP200/data:null. No calculation, permission assignment or scope rule changes.

Evidence: `D:/freshvcf-build/evidence/f3-stage2-descriptions-002/receipt.json`,
SHA256 `e928b9bc220251a33a10b538df6f1a9f4a099c95d588d06257f73be44cf94899`.
All14 retained requests compare complete ordered typed envelopes and HTTP status
against independent deployed SQL. Source SHA d2f578a2 and IL SHA ccd47dc8 are
pinned in that receipt. The earlier descriptions001 table-alias binding failure
is preserved as verifier diagnostics, not a legacy defect or acceptance result.

## BTR export — missing pair-attribute join

Pinned BORProcessor.BuildSqlForExportBTR (source80ceb491, DLL0222eb96) omits
SkuLocAttributeData/sla, although Commons can generate predicates on sla.c1–c15.
The retained pair-custom and three raw-NULL pair-attribute requests therefore
raise SQL4104. Fresh returns503 with LEG-BTR-EXPORT-MISSING-SLA; it does not add
the missing join or claim matching legacy HTTP error handling. This qualification
applies to export only; the canonical grid/count pair-attribute join remains valid.

Export also retains five previously identified invalid-filter cases: missing
availability/coverage/sl9 columns (SQL207), unknown operator and malformed
black/red multi-column operator (SQL102). All nine failures are individually
retained in `f3-stage2-btr-export-004/receipt.json`, SHA256
`248811e2146fc79fc3efdc4b3f4f367cb53659308131f4bc184a24eb5e48dab0`.
The other54 cases match full ordered typed rows, actual deployed header SQL and
CsvHelper bytes. Valid Stock/GIT/PIC/OHIC export filters are supported because
export consumes terminal requirements; their grid-specific five-column failure
does not transfer to export. No calculation or F2 exception is introduced.

## Buffer Trends graph — deployed filter failures and call gate

SCIHProcessor.GetBufferGraphData (sourcef709a448, DLL0222eb96) uses colour history
A with SKU/location/pair attributes. It does not join btd or b. Consequently
colour-age predicates reference missing btd.D90; category references b.category.
Stock/GIT/PIC/OHIC/tags/availability/coverage are absent. The retained invalid
sl9, unknown operator and malformed black/red hasvalue requests also fail.
Independent SQL Server reports207/4104/102 for the exact affected identifiers.
Fresh returns503 LEG-BUFFER-TRENDS-FILTER-INVALID-SQL and does not repair the
query or claim matching legacy HTTP error behavior.

The six-group call gate excludes customAttributeFilter. Custom-only requests
therefore canonically do not apply that filter; a present standard group, even
empty, causes Commons to include it. The valid black/red count expression has
an unparenthesized OR whose precedence is preserved, including combined SKU
filters. These behaviors are not silently normalized.

Evidence: `f3-stage2-buffer-trends-001/receipt.json`, SHA256
`f26ab20f3f15dc51e7b46e650453f452bfc5db62a8bee94a06d5a53388861265`:
134 full ordered responses match,30 source failures are qualified, with exact
failure audit retained separately. The scope is this graph consumer only; no
calculation exception, filter repair or whole-journey acceptance follows.

## Buffer Trends inherited frontend — doubled Total and stale Percentage plot

`frontend/src/VectorFlow/Pages/MTA/InsightsAndTrends/BufferTrends/useBufferTrends.tsx`
contains two reproduced presentation defects. `getGraphDataWithTotal` only
shallow-copies its argument and rewrites nested data. `handleApplyFilter` calls
it twice on that same response; the second reduction includes the already-added
total. Show All therefore plots Total2480 for1240 colour observations, and the
percentage Total is approximately200. The six colour values and summary are
unmodified canonical API outputs.

Separately, mode switching sets `currentPageTab` to `Percentage`, while the
graphData effect checks `percentage`. Submitting a different horizon in that
mode updates summary/availability but retains the prior plotted dates/data.
Observed: one-day selector and99.35% summary with the old30-day graph; toggling
Absolute then shows only17-Jun-2026.

Receipt `f3-stage2-buffer-trends-serving-001/receipt.json`, SHA256
`b169380bfa441f5299cbfe84e550801d20f2dd1b5af68c9dc60ae0cb42becc95`, includes
screenshots and source hashes. The hook, page and both chart components match
the pinned reuse revision66a77735 after line-ending normalization. These are
inherited frontend flaws, not evidence of a Django calculation/report mismatch.
At that historical checkpoint they were unresolved acceptance blockers. The
human-authorized Research/RRR/Buffer presentation batch subsequently corrected
the hook: copy the nested response, add Total once, and match `Percentage` in the
new-response effect. Existing request-race tests pass. On5-Oct-2026 the retained
April7 fixture's Eco/SKU21101151051000 chart shows Total100 in Percentage rather
than200; submitting1day in that mode plots only07-Apr-2026 with12 Black summary,
then Absolute shows12 Total. Screenshots/AX states are in
`research-rrr-buffer-trends-20261005-001/buffer-one-day-*-final.*`.
This closes these two frontend defect dispositions for that fixture; it does not
waive the remaining filtered performance or absent expanded-view coverage.
Backend responses do not compensate by changing counts, percentages, date ranges
or legacy comparison assertions. Historical receipts remain unchanged.

## Planning Excess — source-invalid filters and independent custom population

PlanningProcessor bf716c4f uses Commons filterQuery(sa,la,sla) for normal Excess
grid/count. Category targets missing description-table column b.category;
availability/coverage and colour-count fields do not exist in the selected
joins; colour-age targets missing btd.D90. Invalid sl9/operator and malformed
black/red hasvalue SQL also fail. Receipt f3-stage2-excess-005 binds28 failures
to exact207/4104/102/156 identifiers/codes, independently checked in
failure-audit.json. Fresh returns503 LEG-EXCESS-FILTER-INVALID-SQL; this is an
explicit unavailable contract, not matching legacy HTTP errors or repaired SQL.
Other filters, including tags and normal numeric inventory fields, are valid.

ExcessInventoryProcessor5eb90eb1 does not read graph request filters.
GetCustomGridData does not read filters or type and uses case-sensitive category
dispatch. Its NMSAllItems inner join sees zero native rows in the accepted June17
independent legacy/modern states. Custom therefore returns an empty list while
the normal Excess report has85 rows. Do not substitute normal rows, populate
NMSAllItems or project new hierarchy into that table to conceal this difference.
Terminal empty custom parity does not certify populated custom behavior.
No business/calculation exception or authorization to change these rules follows.

## Planning Fulfilment — missing custom identity and undefined row numbering

Pinned PlanningProcessor bf716c4f, GetCustomGridData orderFulfillment branch,
LEFT joins OrderFulfillmentData B to native NMSAllItems A and orders ROW_NUMBER
only by A.SKUCode,A.WhCode. Selected June17 has1222 summary rows and zero native
NMS rows in both independently retained engines. The SQL therefore emits distinct
Norm/Stock/RationedQty payloads without sc/wc and assigns RN from identical
NULL/NULL keys. Neither a hidden report-identity tie-break nor normal-grid rows
may replace that source contract. Paged membership/ordered RN parity cannot be
claimed; empty scope and bounds selecting no rows remain verifiable empty results.

Fresh's custom adapter preserves native LEFT joins and NULL omission and returns
503 LEG-FULFILLMENT-CUSTOM-UNORDERED-NMS when different payloads share those source
sort keys. This is an explicit unavailable contract, not a claim that legacy
returns the same HTTP error. Existing inherited validateCustomRows also refuses
rows without sc/wc. Do not invent NMS identities, change the frontend guard,
populate calculated metadata or weaken comparison assertions. Populated custom
behavior requires independently admitted native input and its own proof.

Normal Fulfilment Commons filters also retain source failures: category refers
to unbound b.category (SQL4104); availability and colour-count fields are missing;
colour age refers to absent btd.D90; invalid sl9/operator and malformed black/red
hasvalue SQL fail. Fresh exposes LEG-FULFILLMENT-FILTER-INVALID-SQL, not repaired
results. Coverage is valid on this report and uses the exact stored labels
(`Gap < 33%`, `33% <= Gap <= 67%`, `Gap > 67%`), never ordinal codes inferred
from the UI. Canonical QuadrantProcessor9f084f35 ignores graph request filters.
Planning's empty-permission literal is quoted twice by GenericFunction's fallback,
causing SQL245 varchar-to-int conversion. The existing modern empty-scope denial
is retained as SCOPE_DENIAL_NOT_PARITY, with the exact source failure recorded;
it is not evidence that the legacy returned an empty grid successfully.
No calculation, action-policy or broader presentation repair is authorized here.

## Fulfilment browser — inherited zero rendering and tied graph order

Actual3005 order details for6584/DP020819 show the retained order
B3F-positive-pick-remaining-6584-DP020819, pending65, due2026-06-16 and Over Due.
The exact independently compared API detail has numeric price0. Inherited
`frontend/src/VectorFlow/Pages/MTA/SupplyChainIntelligenceHub/BPR/BPRViewTable.tsx`
line102 uses a truthiness test on each value, falling back to literal NULL at141.
Thus zero is rendered NULL. The API must preserve numeric0; no frontend repair
or reporting-accuracy waiver is inferred. Source hash/screenshot are bound in
f3-stage2-fulfillment-serving-001/receipt.json.

The product coverage chart's200-row workbook has every canonical typed cell and
source count-descending order, but its first different relative position from
the independent SQL capture is index24 within count9 groups. Quadrant SQL orders
only counts descending; no group tie-break is defined. Preserve the failed strict
order verifier/complete actual and expected arrays, then separately record exact
serving-response→workbook order, full canonical bags and count order. Relative
order for those ties remains unproved/NOT_PARITY; do not claim exact independent
ordered workbooks, invent a tie-break or silently exclude values.

## GIT child transporter — SQL failure concealed by empty response

Pinned deployed PlanningProcessor `bf716c4f84e43920b5f2ab302e3d3c78ec685f5d714471c53047d377537d3486`,
GetMonitorGITChildTransporter, selects ta.InTransitQty and correlates
ta.TransporterCode/ta.OrderNo against GoodsInTransitMaster, where those fields
are absent. Its grouped outer query also references an ungrouped SKUCode.
Selected June17 empty terminal inputs reproduce SQL207 and8120 in all four
retained permission cases; emptiness does not avoid SQL name/group binding.
The child's direct-ID permission CTE differs from generic hierarchical expansion
and is retained separately. No positive-shipment or other-day behavior is proved.

GenericFunction.ExecuteScalar catches SQL exceptions and returns null. Actual
canonical DLL invocation with a controlled207 confirms that behavior. The
child processor substitutes an empty list when that helper returns null and
continues toward its200 envelope. Its catch assigning500 does not establish
the disposition of an exception swallowed by the helper. Thus the SQL fault is
real even when the outward transporter grid looks empty. Preserve the inherited
wire behavior separately from its failed SQL contract; neither fix the source
nor count an empty UI as healthy-query/reporting parity.

Input/provenance,44 exact SQL observations, four empty chart schemas and actual
DLL method outputs are bound in
`D:/freshvcf-build/evidence/f3-stage2-git-terminal-wire-001/receipt.json`, SHA256
`7a8481ab22525ae8aefa7b275491343249db38e791128edf6791aaa89c0b0575`.
The initial proof expected[] instead of SQL NULL; its failed receipt and original
verifier remain immutable. Corrected expectations validate the pinned capture
without changing SQL or rerunning accepted calculations. DLL method invocation
under.NET10.0.11 is not a native hosted legacy HTTP/performance proof.

The77-case retained filter expansion is in `f3-stage2-git-filters-001`; the
review/private-route comparison is `f3-stage2-git-modern-001` (SHA256
`e41bf5f17be5fbb0e1782709e450be565425b08c9ea1af1f1ff5e55e308aed65`).
Fourteen filter cases fail the location queries; another14 fail only the child
transporter count because SKU hierarchy/custom fields or their alias are absent.
The selected modern adapter exposes these source failures as503/LEG-GIT and
keeps the combined child grid unavailable. This is an explicit blocker and
**NOT wire parity with the legacy helper's concealed error/empty response**.
Do not count these unavailable branches as accepted or infer permission to
repair legacy SQL. Valid independently proved parent/count/chart/custom branches
may continue. A zero count alone does not certify an invalid child query.

## Expedite parent — SQL failures become empty success in legacy

Pinned PlanningProcessor `bf716c4f84e43920b5f2ab302e3d3c78ec685f5d714471c53047d377537d3486`
has no separator before ORDER BY in unpaged parent queries (SQL156); the Norm
filter is unqualified in the availability branch (SQL209). The remaining invalid
filters and exact inputs are retained in f3-stage2-expedite-parent-filters-001.
Actual deployed GetDataSet in f3-stage2-expedite-envelope-002/dataset.json returns
a zero-table DataSet on both failure classes; parent source then returns empty
lists with status200. This helper probe does not claim hosted legacy HTTP proof.
Its first harness invocation failed argument binding; envelope-001 is preserved.

The new parent route keeps an explicit unavailable response for source-invalid
filters and unpaged requests. This is an intentional containment divergence,
NOT_PARITY and not an approved acceptance exception. Do not silently reproduce
empty-success to conceal failures or repair canonical SQL. Valid paged responses
remain independently comparable. A human disposition is required if these exits
cannot satisfy Stage2's unchanged working-feature and parity requirements.

## BTR inherited frontend — fresh reload misses saved column state

On3005, save a31-column BTRon-hand layout for Depo/June6–17 with SKUDescription
unpinned. The exact persisted row survives a fresh page reload, but that grid
still renders SKUDescription pinned left after the inherited2-second apply delay.
Pipeline→On-Hand subsequently fetches and applies the saved row, visibly unpinning
it. These are different entry paths; successful tab-return restoration does not
certify fresh-reload restoration.

`frontend/src/VectorFlow/Pages/MTA/InsightsAndTrends/BTR/useBTR.tsx` starts
initialColumnState as undefined at133. Saved-state effects at641–656 track mount
and currentTab only and require initialColumnState before calling
getUserColumnConfig; no dependency tracks its first asynchronous arrival.
The apply effects at568–600 wait2000ms after a saved state exists. Current Fresh
bytes equal `F:/VFlow_Local/vflow-frontend/src/VectorFlow/Pages/MTA/InsightsAndTrends/BTR/useBTR.tsx`,
SHA256 `ae2aaa8e048e9e9220f49e92f805b31b2c8ec99856a6a0943ab5ed658faa1833`.
Source, input, exact saved/readback state, screenshots and separate reload/tab
observations are bound in f3-stage2-btr-browser-recheck-001/receipt.json. The
original absent layout is restored through the existing authenticated endpoint;
no business publication or command changes. This is a reporting-control blocker,
not parity acceptance or approval to repair inherited frontend behavior.

## Approved initial child Expedite request history — 3 October 2026

Direct user reply to `call_zbzXQ93n4Qfs9tOGAixne3Lc` approves an explicitly
empty initial OpenExpediteRequests input for the June17 preview run
ac1612c8-0e49-4155-83c3-f59f41422293, output digest
bd1c522f3df299d2fc3841aed7f66d48e4307e6967450b2d8a5463dc7867d33d.
This is new preview application input, not a claim that legacy history was empty.
The opt-in environment setting defaults off and the reader checks run/date/digest.
Canonical ExpediteFromChild (pinned PlanningProcessor bf716c4f) consequently
returns NULL remarks; empty InTransitData remains separately authorized by the
terminal supplement. No request writes, populated-history behavior, calculation,
F2 row or receipt changes are authorized by this input. Missing/unapproved inputs
remain unavailable. Canonical child complete SQL wire parity, including ETA
serialization, remains unproved while the SQL oracle is unavailable. Norm server
filter is explicitly unavailable pending its canonical ambiguous-SQL disposition;
this is not silently corrected or claimed as parity.

## BPR filter SQL defects — source-attributed, 3 October 2026

Affected contracts: GetBPRData, GetBPRDataCount, GetAnalyticsData(name=BPR),
GetExportDataAsync(reportName=BPR). Actual pinned DLL Commons invocation with
aliases vf/a/a/c/d/sla is retained in
`D:/freshvcf-build/evidence/f3-stage2-bpr-filters-001/dll-filters.json` for the
unchanged 52-case input roster SHA256
1393290641b5a0f0a5b8117f328a3c585f953bd6be8ae72927fe3429e24b3ee5.
BPR processor SHA256 68b9680373d7edf530fe5985f89d88d67b6fc4f7f1870112230cba9c7bb6b03b;
analytics SHA256 5aaa5d1d137789ca46a1d41608872c6b0074dcaabe9d914ad07412fbca200d6e.

Category emits b.category although BPR has no b alias; availability emits
a.availability although BPR_Table has no such column; coverage has no joined
owner. Colour age emits btd.D90 although no BPR branch joins btd. Colour counts
have no owner in grid/count/analytics but CAN resolve to the trend join in CSV
export. Invalid operator/hierarchy cases emit empty expressions or missing sl9.
The modern adapter explicitly denies those invalid cases. These denials are not
claimed as exact legacy error-envelope parity or as completed controls; no
presentation or business-rule repair is authorized here. SQL execution/error
comparison remains open while the independent oracle is unavailable.

The roster's historical label `missing-tags` does NOT describe BPR: its emitted
unqualified tags resolves to joined SKULocStandardAttributes.Tags, so that filter
is connected. NULL values and exact IN matching remain intact. No missing
population is defaulted to empty and no F2 data is changed.

## Guided Excess — approved preview opening history

Direct user reply to call_bEZzSUkIR32TJ5lhNiuxhyFI approves declaring no Excess
history before June6 for the selected June6–17 preview, then deriving reports
independently from each engine's own accepted daily outputs. This is a declared
preview input, not proof that the original legacy history was empty. It does not
authorize another run/date chain, calculation change or copied legacy output.

Affected contracts: GuidedInsightsProcessor.GetExcessInventorySku/Value, source
SHA256 d2f578a2beda0b67226b3c85ae65d3a39fe732496237ee41f7c0a9b067f29249;
CollectExcessInventoryDetails.sql producer SHA256
71bb48766d3af7a739b90c511124f9ad99072066283536fd28a9530f3640b8c4.
The input declaration and all12 accepted run/digest identities are pinned in
D:/freshvcf-build/evidence/f3-stage2-guided-batch-001/excess-history-input.json,
SHA256 f7a03468227d2b5ef97fc28fec951ec8f373852ed906c9754d50269b75b84154.
Its independent comparison covers770 rows/all producer fields. No synthetic
zero dates, unrelated shallow trials, F2 mutations or general history lifecycle
acceptance follow from this approval. Publication and browser proof remain separate.

## BTR VM category alias order — narrow human-approved presentation exception

4 October2026 full-data consumer comparison, pinned deployed DLL
`0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346`,
BORProcessor source `80ceb4916ca4cd8567384a4598858cef55f8574007662b025aee237f20ab9298`.
The April7 retained VM fixture, broad native scope, both branches, page1/5000 and
all90 days returns5000 aligned SKU/location positions per branch. Each branch has
93 Category string differences: for example canonical `DN|BR` versus Fresh
`BR|DN`. All other compared row fields and the labels/envelope match. Exact full
response equality therefore fails. Direct human reply to
`call_AGGtUEgL9nSvOJpm7AQWemMi` subsequently approves this Category-order exception
for the retained April7 fixture only: compare alias multisets with exact duplicate
multiplicity, retain/report original strings, and keep all other fields, types
and row ordering strict. This is qualified presentation equivalence, not exact
string equality, and does not transfer to normal publications or other reports.

Canonical `cteCatDes` uses `STRING_AGG(d.categoryalias,'|')` after STRING_SPLIT
and a CategoryColDescription join, with no WITHIN GROUP ordering clause. Fresh
`btr.category_alias_text` preserves the persisted category-code sequence. The
standalone canonical aggregate returns the latter ordering in the retained probe,
whereas the full canonical grid returns the former for affected groups. Its
default repeat and MAXDOP1 diagnostic matched each other; this does not prove
identical-request instability or authorize changing the application ordering rule.

Evidence: `D:/freshvcf-build/evidence/3005-btr-performance-20261004-001/`,
`legacy-full-grid-002.json.gz`, `legacy-grid-field-differences.json`, and
`category-order-source-proof.json`. The first direct request omitted the required
empty horizonFilter object and returned application status500 inside HTTP200;
that malformed probe is retained separately and is not an availability claim.
No response rewriting, output exclusion, legacy repair, fixture mutation or
F1/F2 change is authorized. `parity/btr_benchmark_contract.py` applies only the
approved evidence-comparison rule, pinned to this manifest/date/BTR route. The
retained full comparison passes with186 declared ordering qualifications and
zero other differences; original responses remain retained. Focused tests reject
duplicate loss, case/whitespace/type changes, reordered rows and scope transfer.


## 5 October 2026 — authorized retained Planning report corrections

Direct human instruction in controller turn01a10b0a-e95f-7981-a326-8a42eb9c1c3b
supersedes the repair prohibition only for these report defects. On April7 fixture
run bfd75b4b-a9df-4a08-82d3-852e3324b623, GIT child retains1627 aggregate location
occurrences and independently empty shipments. Shipment fields belong to
GoodsInTransitTransporterMaster; aggregate master rows cannot supply transporter,
order, quantity or grouped shipment SKU. Nonempty shipment inputs still fail
closed; this is not general positive-shipment acceptance. Parent unpaged SQL156
is corrected by retaining valid selection/order without pagination. Unrelated
SQL209/filter defects remain unchanged. Child receiving LogisticsLocation now
comes from its own joined row, not the last critical row. Pinned DLL dataset
proof changes only labels and proves critical-order independence.

Evidence: planning-prepared-20261005-001/report-corrections contains complete
broad/scoped/empty proofs and authenticated gateway captures. Historical failed
SQL and original DLL outputs are preserved. These are intentional corrected
contracts, not parity with concealed SQL failures or incorrect legacy labels.
The retained receiving top10 matches including its cutoff tie; independent full
SQL sequence acceptance remains unresolved. No calculation exception is implied.
See MIGRATION.md for current status.

## April7 Expedite chart ordering — approved bounded comparison exception

Direct reply `call_038051c3721a4d7f8a5a28f8ddf66e93` approves only this retained
April7 fixture's six chart-query sequences. Parent/Child critical queries have
no ORDER BY, so their complete row bags may be compared. Parent/Child receiving
queries preserve ParentwiseCount DESC, MaxPipelineInv DESC; Parent nil-stock and
chronic preserve counts DESC. Reordering is allowed only within equal explicit
keys. Every field, scalar type, NULL and duplicate count remains strict. Retain
original arrays; this does not alter queries/UI, invent a tie-break, waive other
reports or transfer to another run/date/source. `parity/planning_order_contract.py`
enforces the run/source/date/family boundary. Tests reject changed values/types,
duplicate loss, explicit-order reversal and scope transfer. Retained evidence:
`planning-prepared-20261005-001/acceptance-continuation/order-acceptance.json`.
Six broad comparisons pass with the exception; six leaf comparisons remain strict.

## April7 Parent nested transit order — separately approved exception

Direct reply `call_rXDWYB4DZf82Ch7YyyoH5EEa` approves unordered comparison only for
`GetPlanningDataGrid`, Parent, `expediteDispatchestransit`, on run
`bfd75b4b-a9df-4a08-82d3-852e3324b623` and its pinned April7 source digest.
Canonical `cte_intransit` has no ORDER BY. Independent retained READ_ONLY SQL
and modern capture contain the same97097 complete string-valued rows, including
NULL omission and duplicate multiplicity, in different sequences. Both sequences
remain retained. No values, types, fields, duplication or other order is waived.
`compare_parent_transit` enforces the exact boundary separately from chart rules.
Evidence: `planning-prepared-20261005-001/parent-independent-sql/approved-transit-comparison.json`.
The populated restricted actor (`products=[4]`, `locations=[25]`) also passes with
97097 rows and zero missing/extra occurrences; its original sequences and hashes
are in `parent-independent-sql-restricted/approved-transit-comparison.json`.
Its78 dispatch/161 availability main rows remain strictly ordered comparisons.
This is a comparison exception, not a change to serving queries or UI ordering.


## LEG-BOROA-APRIL-RN-TIES - explicitly approved bounded comparison qualification

Direct human reply to call_O27BVOUnwvUYcWT8ic8bKy1P approved April BOR-OA tie
qualification. Source: pinned DLL getSelectQueryBORColorBandWise RN keys (IL109305),
run bfd75b4b-a9df-4a08-82d3-852e3324b623/date2026-04-07/native digest
4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73,
BORWithOrderAllocation captured digest141ac5aff9f44e1f0fb4a16215bd95f0a8b340fc67cfd8da01ceac3eec0a20a6.
All1199 business rows match;53 groups/512 rows tied,458 RN assignments differ.
Four cohorts cross100-row page boundaries100/200/400/600/700. Acceptance may compare
complete equal-key business-row bags without generatedRN and qualify within-tie
page membership; explicit ordering keys, all actual business fields/types/NULLs,
duplicate counts, source/filter/scope and non-tied page membership remain strict.
No runtime tie-break, oracle replacement or removal of failed strict comparisons.
Evidence:
D:/freshvcf-build/evidence/boroa-family-20261006-001/ordering-boundary.json and
comparison-consumers-001.json. No transfer to other dates/families or calculations.

## LEG-BOROA-COUNT-ATTRIBUTE-ALIAS - retained canonical failure

Pinned DLL BOROrderAllocationReportDataCount IL110379 aliases ColorSequence C,
IL110387 aliases SKU attributes s, while BOROA filter compilation uses c for SKU
custom attributes. SKU-custom predicates therefore reference missing colour-table
columns; product hierarchy uses unqualified sl fields and resolves normally. Preserve the source failure; do not redirect count's c to s.
Grid uses C=SkuAttributeData. Same April source/scope as above; no assertion waived.

## LEG-BOROA-UNESCAPED-LITERAL - unavailable unsafe legacy literal behavior

Pinned AddBOROARemark/GetBOROARemarkDetails concatenate raw quoted strings
(IL98740-99006). BOR-OA denies apostrophe-containing remark/key values with503;
this is NOT_PARITY, not an exact emulation of arbitrary SQL fragments. Omitted
nullable remarks and explicitNULL distinctions retain the native tested behavior.
No normal-BOR approval is transferred to this boundary and no unsafe SQL executes.


## LEG-MDM-DRAFT-OWNER-READ-APPEND - approved narrow ownership exception

Pinned DLL DraftProcessor.GetDraftCount IL21424–21504 and GetDraftDetails
IL23097–23299 accept only draft ID (plus pagination for details); their SQL has
no requester predicate. DraftController IL160059–160228 does not pass an actor.
AddMasterDraft supplied-ID append branch also has no owner predicate, while
ModifyMasterDraft/DeleteMasterDraft explicitly check DraftInstance.userId.
This conflicts with the new tranche's owned draft read/write acceptance.
Do not claim actor-denial parity. Exact source
snippets/strings are in mdm-sku-20261006-001/draft.il.txt and draft-strings.json.
Direct human reply to call_Mz37jsXw2plmDe3DDwJljyxJ item1 on6October2026:
"Approve narrow draft ownership checks". Enforce owner on read/count/provided-ID
append, retaining the native successful owner flow. This is an intentional
deviation limited to those three checks; no other legacy repair is authorized.

## LEG-MDM-SKU-MODIFY-MARKER - corrected qualification, no exception

The first qualification incorrectly equated task header Actiontype2 with the
staged row marker. Pinned InsertSKUMaster IL50354–50366 calls the getValues overload
whose IL56494–56515 emits literal Reverted0,ActionType1,Approved0 for BOTH add and
modify. Canonical
NMSImportData.sql (SHA256 c86d014b1f7ee921821f83936a53d1d4da566ba9b2558db9252853260c3c3801)
overlays ActionType1 and deletes ActionType0. Approved SKU modifications normally
reach this ActionType1 overlay and DO change master values at the daily boundary.
Do not use header Actiontype2 as the approved-input marker. Archive/clear consumes
approved staging;
NMSTaskStatusUpdate.sql (99836bcf74c618350924bf02e21dea30cbe4cc9d6022f859f5c1c6cfca10dbe8)
advances approved-history subtasks2/3 to4/5 and parent7 independently of successful
master application, including when NMSActive disables import. Full bounded
DLL/BAT/SQL qualification is mdm-sku-20261006-001/contract.md. Adapter verification
is confined to owned revision/input tests; no production/daily/demo run is released.

## LEG-MDM-TASK-ACTOR-GAPS - approved narrow task access exception

Pinned submission accepts supplied TaskId without owner validation; approval
PostMasterAfterApproved IL81868–82400 updates by taskId/SKU without checking acting
reviewer assignment; DeleteTaskProcessor IL90228–90354 accepts no actor and deletes
history/temp/header/subtasks. Download IL84101–86580 trusts supplied ApproverId;
TaskMasterHistory IL90655–91055 ignores caller scope. The draft ownership approval
does not cover these task endpoints. Evidence: mdm-sku-20261006-001/task-wire.md.
Approved narrow exception: requester-only task append/delete; assigned-row reviewer
and submitted-product scope for decisions; requester or selected acting reviewer
for downloads; current SKU scope for history. Deny other actors with403, preserving
successful authorized wire shapes, source calculation and status/failure behavior.
Direct human reply call_kh5dPo7oujWIY7JUspAONbrS item0 on6October2026:
"Approve narrow MDM task actor checks". This authorizes only the stated guards;
draft, ordering, transaction and calculation contracts remain separately governed.

## LEG-MDM-SKU-UNPAGED-ORDER - approved exact-family qualification

Pinned current SKU query computes ROW_NUMBER(sc DESC) but its unpaged outer SELECT
neither uses RN nor orders results. SQL Server removes the unused window; native
unpaged order varies with scope/access path. Modern complete row bags match for
all2,189 broad and1,042 restricted records. Strict unpaged order failed at742 and
1,038 positions; every100-row page (including empty terminal pages) matched exactly.
Original failures schema-001/002/003 and native/modern complete bags remain under
mdm-sku-20261006-001. Human reply call_zXrNT7N0MmY734I0z7Oy3J46 item0:
"Approve SKU unpaged ordering qualification". Unpaged current read/download may
compare complete bags only for this SKU boundary. Exact page order and complete
field/type/NULL/multiplicity checks remain required. No other family/task/draft
ordering exception transfers and no invented sorting tie-break is added.

## LEG-MDM-SKU-HISTORY-WIRE - approved gateway shape adapter

Pinned GetSkuLocProcessor master1 (IL91417–91687) returns data as a direct
SKUCode array. Retained DataModificationHistory/useDataModificationHistory.ts
reads data.sku/data.loc; the retained gateway provides no response adapter.
Direct human approval call_d242e2987b96420fa241a55c123555df item0:
"Approve SKU history response adapter". Only the authenticated gateway's
successful GetSkuLoc master1 response wraps that array as {sku: rows, loc: []}.
The native service response, current hierarchy scope, DISTINCT SKU grain,
modify-task predicate and90-day through today's-midnight cutoff remain unchanged.
This does not authorize a same-day history repair or another family's adapter.

## LEG-MDM-MENU-ALIASES - approved conditional navigation aliases

Retained NavbarMenu/listMenu.tsx uses five /masters-interceptor routes, while
the existing MTA permissions authorize /mta/master-data-management routes.
NavbarMenu's exact URL checks therefore hide MDM despite those grants; direct
routes work. Human reply call_afa0d7ddadba48b791143b5fd0b6e2f0 item0:
"Approve conditional MDM menu aliases". Login/profile responses may add only
the matching control-panel, saved-drafts, task-pending, task-status and
data-modification-history interceptor alias when its exact MTA route is granted.
Stored grants, credentials, product/location scopes and MTO access stay unchanged.
The retained application selector still checks the underlying application route.

## LEG-MDM-UPLOAD-TRANSPORT - approved CSV and progress compatibility repairs

Retained read_uploaded_master_file sends CSV to openpyxl and raises BadZipFile.
GetUploadProgressView uses async get under synchronous DRF APIView dispatch,
which raises a coroutine/Response assertion; its cached model also retains stale
progress. The unchanged frontend offers these upload/polling paths. Human reply
call_04ea8b66063b4ea682ca0df8100ce7cb item0: "Approve CSV and progress fixes".
Use pandas.read_csv(dtype=str) only for CSV, retain Excel parsing and cell cleanup,
and make progress get synchronous with a fresh typed progress-row read per poll.
Validation rules, scopes, response fields and frontend behavior remain unchanged.

## LEG-MDM-MIXED-DRAFT-PROJECTION - unqualified native mixed-family read

Pinned DLL DraftProcessor.GetDraftDetails IL23138–23145 concatenates download
columns across all nonempty-grid family mappings into one SQL projection while
assigning a single unordered @MASTERID. GetDraftCount IL21457 assigns (rather than
appends) its dynamic SELECT for each mapped family without ORDER BY. A mixed-family
draft therefore has no qualified cross-family read/count contract in this port.
The three-family extension retains separate typed draft rows and exact single-
family reads; it does not invent a winning family or claim mixed-family parity.
Mixed-family count/projection requests are explicitly incomparable. This is a
recorded limitation, not approval to repair native mixed-family behavior.

## LEG-MDM-FAMILY-SCOPES - approved Location and SKU–Location actor checks

Human reply call_gIWwZjTVAlJCQTBBsDtsy1dH item0 on6October2026:
"Approve family-specific scope checks". Extend the earlier assigned-reviewer
decision checks and scoped history reads to the relevant Location scope for
master2 and both product/location scopes for master3. Other actors receive403
before mutation. Authorized response shapes and business effects stay unchanged.
This is the narrow repair of native omitted checks described in
LEG-MDM-TASK-ACTOR-GAPS; no calculation, ownership or ordering exception transfers.

## LEG-MDM-LOCATION-HISTORY-WIRE - approved master2 gateway adapter

Pinned GetSkuLocProcessor master2 (IL91417–91687) returns a direct WHCode array.
The unchanged DataModificationHistory screen requires data.sku/data.loc. Human
reply call_UzVFxn5XOksXp90eX1ChNLTT item0 on6October2026:
"Approve Location history adapter". At the authenticated gateway, wrap only a
successful master2 array as {sku: [], loc: rows}. The native MTA response, scope,
90-day window and today's-midnight cutoff remain unchanged. Master3 is unaffected.

## LEG-MDM-LOCATION-SKULOC-UNPAGED-ORDER - approved current-read qualification

Pinned master2/master3 GetData outer queries do not order unpaged results; their
unused ROW_NUMBER/RANK expressions do not define the wire sequence. Human reply
call_9QfAPeRqplgZiMfwKfKiZrJE item0 on6October2026:
"Approve these two unpaged ordering qualifications". Only Location and SKU–Location
unpaged current reads/downloads may compare complete row bags. Exact fields,
NULLs, duplicate multiplicity, counts and paged order/membership remain required.
Proof004 retains strict failures and complete native/modern rows: Location scopes
234/9/6 rows match as bags with231/8/6 changed positions; SKU–Location scopes
97,097/7,851/5,076 match with94,140/4,913/3,123 changed positions. All tested first
100-row pages match exactly. This does not claim every possible page was tested,
authorize a sort/tie-break, or transfer to task/draft/history responses.
Evidence: mdm-location-skuloc-20261006-001/{location,skuloc}/current-comparison-004.json.
Location's original capture with an added outer ORDER BY is explicitly disqualified;
only its exact v2 capture is used. Proof003 was stopped during costly unittest
large-list diff formatting (not OOM); proof004 retained strict assertions with
compact diagnostics. No runtime resource increase or business-rule change occurred.

## LEG-MDM-FAMILY-REVIEW-OLD - retained native review/download projection

Pinned DLL GetTaskDetails IL78840–78856 (Location) and download IL84595–84611
reuse A-qualified requested columns inside the correlated B-history subquery.
Location modify `old` therefore repeats requested values. SKU–Location download
IL84851–84983 has the same defect; its review IL79227–79369 correctly projects
separate A/B values, cast to VARCHAR(max) with NULL represented as empty text.
All these `new`/`old` properties are JSON text, not nested objects. Correlated
duplicate source rows yield comma-separated object fragments without brackets;
no uniqueness or repair is invented. The first browser trial exposed our object
serialization mismatch. The new-family projections now retain this native text
contract, action-specific RN direction and original flawed old-value semantics.
Focused PostgreSQL proof008 and native-review-json-text.json cover the correction.
This record does not authorize changing accepted SKU. The following explicit
approval supersedes preservation only for Location modify-review old values.

## LEG-MDM-LOCATION-REVIEW-OLD - approved review-only old-value correction

Human reply call_eIJMnXR1wG9XdpXTiFUBpX8n item0 on6October2026:
"Approve Location review old-value repair". The browser reproduced the native
defect above: requested values in both columns caused automatic rejection with
"No modifications made in this record" and disabled approval. Only master2
modify-review old JSON now projects matching history fields. Text shape, NULL
omission, duplicate subquery multiplicity, actor/location scope and approval
effects stay unchanged. Location downloads and SKU–Location downloads retain
their native A-qualified old projection. No other family or calculation repair
is authorized. Evidence: location-modify-native-old.png and focused proof009.
