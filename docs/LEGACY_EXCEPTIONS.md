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
