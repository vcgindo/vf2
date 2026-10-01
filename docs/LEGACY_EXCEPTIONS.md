# Legacy behavior and explicit exceptions

Do not repair legacy algorithms or add invented ordering to make tests pass.
These known risks remain visible; neither is permission for blanket exclusions.

| Source | Issue and impact | Fresh-build treatment |
|---|---|---|
| BPR/Ration_Scripts/CalculateDD.sql | Unordered multi-row identity insertion can assign different OrderKey priorities, affecting allocation | Preserve raw evidence; no invented sort or expected allocation. Compare only where source semantics are defined; unresolved branch remains unaccepted. |
| DBM/Norm 0-1-2 Reports/Norm0Data.sql and related occurrence aggregates | STRING_AGG without declared order can change presentation text | Identify exact affected fields. Numeric/state parity stays strict; no auto-approved normalization or concealment. |
| DBM selected profile | Existing modern code has explicit unsupported guards for conditional rule/auto-acceptance profiles | Classify against actual canonical settings. Presence of a guard is not implementation or parity. |

Each reproduced flaw must add source hash, input hash, observed outcomes and
the narrow affected contract. Independent implemented contracts may continue.

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
