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
