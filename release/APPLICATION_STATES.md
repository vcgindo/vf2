# Installed application and business-data states

This defines the release's application boundary. Acceptance progress belongs only in the handoff TRACKER.md.

An installation is not a business population. An initialized population is not a calculated publication. Configuration and normal authorization must work before either exists; operational readers and commands retain their own prerequisites.

| State | Admission and response boundary |
| --- | --- |
| Installed, no trial chosen | Validate the pinned exported source, applied migrations, expected owned schema/runtime identity and finite setup grants. No initialization, source, run or namespace registration is created to expose configuration. Return release configuration and an explicit not-initialized state; data-dependent requests report a prerequisite rather than a successful empty business result. |
| Initialized, no publication | Validate the real initialization/source and existing immutable namespace/capability. Supported current-master readers can use that source. Operational reports still require a selected calculated publication. |
| Publication configured | Existing startup binding, source/capability/namespace/seal/receipt validation and per-request admission remain mandatory. Published wire bodies, scopes and business behavior retain their existing contracts. |
| Invalid or inconsistent | Reject. A partial selection, missing configured selection file, tampered source/receipt, existing runs without a selected publication or incomplete installation cannot be represented as the empty state. |

## Installation and identity

Defer the existing input-bound one-time `register_mta` operation until an operator chooses the optional initialization artifact. Do not replace an existing registration. Before that boundary, the installer supplies only schema USAGE and SELECT on the migration record and the initialization/source/run identity relations needed to distinguish empty from inconsistent state. No master/workflow/calculation mutation is granted by setup admission. Registration later establishes its existing complete runtime capability using the chosen artifact and unchanged registration rules.

Installed-source verification uses the committed export manifest inside the pinned image; it is not a new database registry or operator bypass. All API configuration requests still pass the existing authenticated gateway and endpoint identity/role checks. The existing permission catalogue path reports upstream failures distinctly; an installation without a population has no invented product/location IDs or memberships. Ordinary requester/reviewer permissions are explicitly assigned from existing function definitions. Metadata access does not authorize a data-dependent write.

Application/setup availability and business-data readiness are separate observations. Existing health/status surfaces must expose that distinction without converting a missing publication's data-readiness failure to operational readiness. Normal serving restart does not provision, register, initialize or execute a day.

## Existing screen/request inventory

Route authority is `frontend/src/app-routes.tsx` and existing authorized navigation; MTA HTTP authority is `mta/presentation/urls.py`. Alias routes share the existing page; an inventory entry grants no permission or unsupported capability. The baseline inventory contains 87 distinct literal profile/landing/MTA/MTO/admin routes, including existing aliases, and the finite MTA route roster. Validation evidence retains their exact names rather than creating a second route registry.

| Existing screen family | Definition/setup requests | Population or publication boundary |
| --- | --- | --- |
| Login, landing, profile, permissions, Manage Users | Existing auth/RSA/CAPTCHA/profile/roles/application/functions and permission-catalogue APIs | Authentication and assigned functions; no fabricated population scope. Account/configuration writes are installation metadata, separately recorded. |
| Vector Admin roles, URLs, environment, permissions, report/MDM UI configuration | Existing administrator functions and retained configuration owners | Existing administrator policy and actual supported writes; no new blanket privilege or fabricated business settings. |
| MTA MDM control panel: view/modify, add, remove | `GetMasterUIConfiguration`; existing configuration modules for SKU, Location, SKU Location, SOB, MOQ, Stop PIPO, Add PO, Add PIPO, Target Norm, Seasonality Status/Absolute/Percentage and Force Norm Change | Preserve each family's operation flags. MOQ destination applicability depends on initialized supplier settings; expose that unresolved dependency explicitly, without choosing a setting. Current masters require initialization. Draft/upload/submit/review commands retain server prerequisites. |
| MTA saved drafts, task status, pending review, modification history | Existing family definitions and task/history field definitions | No task, history, pending count or action target is invented before a source exists. Actual source-bound reads and workflow permissions remain authoritative. |
| Planning, BPR, open expediting, logistics/transit | `GetEnvironmentConfiguration`, `GetAllReports`, `GetUIConfig`, saved-layout metadata; location/description filters are population-dependent | Planning counts/graphs/grids, BPR, transit and requests require their actual population/publication. No fake zero metrics, date, shipment or target. |
| RRR, colour/order allocation, BOR/BOROA, supplier allocation/dispatch, elephant orders | Existing report UI definitions and pinned BOR/BOROA configuration | Retain existing report controls and supported-source requirements. Showing a definition does not enable an unsupported reader or business action. |
| Guided/Research Insights, BTR/Buffer Trends, DBM | Retained environment/report/column/chart definitions | Calculated charts, histories, suggestions, date and Apply/Sleep require a valid selected publication; show setup explanations instead of invented results. |
| MTO MDM control/add, drafts/tasks/review/history | Existing MTO metadata and master-validation API contracts | Empty application visibility does not initialize MTO masters, generate scheduler inputs or run the scheduler. |
| MTO production planning/scheduling, enquiry, full-kit, rescheduling, due-date, dynamic release | Existing page configuration, UI columns and gateway/MTO connections | Uninitialized operational panels explain missing data; no scheduler/result or operational zero-value claim. |
| MTO procurement planning/material requirement/coverage, simulative full-kit | Existing procurement metadata and page definitions | Preserve direct-port MTO contracts and unavailable-input requirements. |
| MTO POOGI/manufacturing intelligence: delivery/OTIF/OT-IF/lead time, future load, congestion, forward execution, improvement areas | Existing page definitions and aliases, configured report services | Empty/setup handling only; no new algorithm, dataset, scheduling or execution acceptance. |

## UI and proof boundary

Authorized menus and static definitions remain navigable in both setup states. Grids/charts show their existing fields with a clear prerequisite explanation, no fabricated business payload, date or metrics. Dependent controls are unavailable in the UI and independently rejected by the server. A configuration/permission error must remain distinguishable from legitimate absence of business data.

The optional retained external initialization pack is a separate operator procedure: choose and verify its exact artifact/profile/recipe/configuration identities, transfer it, inspect, register once if absent, initialize and verify the intended master/initial facts with zero calculation runs. No daily sequence or publication is generated by this procedure. Operational execution/action/successor, failure/retry and full backup/restore belong to Stage Five.
