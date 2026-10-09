# Eight-group MDM integration contract

> Retained family-source contract from25b4fad. Historical proof and approval statements below apply to that original delivery. Current3005 integration proof and limits are in [MDM_3005_CODE_DELIVERY.md](MDM_3005_CODE_DELIVERY.md); no fixture approval or runtime acceptance transfers implicitly.

9 October 2026. Source-only implementation under MDM_INTEGRATION_IMPLEMENTATION_PLAN.md. MIGRATION.md is the sole status tracker.

## Pinned boundaries

MDM base: `71ce853d6e8532eb4407173e347a7e998c91b6cb`. Read-only production reference: `a6bdf1296239bc68c976a806e15551ee25935be5`. Human mandate: controller turn `01a11f39-0692-7493-bc2d-9e3e5dd49d25`. Existing DLL/SQL mappings and native limitations remain in the family contracts; residual coverage stays closed.

## Exit I: finite integration map

| Group | Existing owner / route / capture | Prerequisite and concrete integration disposition | Source-review exit |
|---|---|---|---|
| SKU1 | Root receipt, SKU attributes/description/use; sku/tasks/task_reads; daily_input base sets | Explicit installed root; retain exact receipt and base configuration. Combined identity must include root family1 | Root unchanged; actual base receipt checked |
| Location2 | MdmFamilySource, attributes/description/use; location; daily_input base sets | Same source and complete base1–3; retain family receipt equality | Base owner2 verified, no inferred population |
| SKU–Location3 | Pair/current/approval owners; skuloc; daily_input composition | Same source, exclusion owner and frozen action membership | Base owner3 verified; exclusion/NULL/duplicate policy unchanged |
| SOB4 | Supplier configuration/raw/queue/archive; supplier_tasks/reads; supplier_capture | Existing installer requires both4/5 and all three explicit raw bags | Combined roster keeps4/5 together; one supplier capture/finalizer |
| MOQ5 | Same shared supplier owner, format selects destination/raw2 or raw1 | Exact format/configuration receipt; no standalone14 alias | Existing destination route unchanged |
| Phase6–9 | Separate StopPIPO owner6; shared Phase owner7–9; bound from accepted own closing | Optional6, complete7–9; existing binders need same-source CONSUMED selected run, no pending capture | Integration binds already installed owners; no synthesized opening or master9 native task repair |
| Seasonality10–12 | Shared owner/current/queue/eligibility; season_current/tasks/reads/capture | Complete10–12; existing installation is fixture-specific, generic onboarding absent | Verify existing owner; no transfer of fixture scope; opening anchor checked before other working-copy overlays |
| Force13 | Force owner/queue/log; force/tasks/reads/capture | Optional13; existing installation is fixture-specific, generic onboarding absent | Verify existing owner; frozen lineage and exact trial override remain scoped |

Shared dispatch/drafts, typed capture tables, queue revisions and atomic finalizers already cover these families. The original roster whitelist rejected Seasonality with SOB/MOQ or Force. The separate immutable integration receipt binds an explicitly selected existing source, its exact installed family receipts, current adapter and relevant configuration, without changing the source digest or reinterpreting old receipts. It is a companion ownership seal, not a new source installer or publication acceptance.

Capture previously overlaid Force before checking Seasonality's whole-opening digest. Both anchors now validate against the same unmodified predecessor/opening before their disjoint working tables are replaced. Existing calculation/validation order stays intact.

The reference's `mta/mdm/owned_namespace.py` is a standalone catalogue/ACL guard; its `daily_source_install.py` change authorizes the existing registered bootstrap in an independently provisioned namespace. Port only those seams. The exact registered artifact restriction remains.

The reference's `operational_admission.verify_input_domain` requires the base registered ten-pair artifact, inactive NMS, its exact operational profile, empty approval queues/upload log and operational configuration/attempt/acceptance models. `operational_mdm._verify_installed_owners` reconstructs the original base opening. `qualified_consumption` is separately pinned to named runs. Neither explicitly admits an eight-group publication. Importing selected_run's alternate branches alone would be an unsupported gate extension; retain the existing accepted selected-run policy.

## Migration and shared-file boundary

Both graphs share `0081_complete_nms_approval_queues`. This branch then owns `0082_nms_sob_moq_owners` through `0100_nms_phase_controls_owners`; the reference instead owns `0082_operational_effect_ownership` through `0101_operational_bound_files`. Numbers are not identities. Preserve both histories. Add only a uniquely named MDM integration metadata migration after this branch's0100. No operational model or migration is copied.

A future authorized merge must retain both named branches, reconcile shared `models.py`, input table/storage registration, temporal/services handoff and presentation admission, and add a merge migration depending on both actual leaves after source conflict resolution. That bridge cannot truthfully be created here while the operational graph is absent. No claim of applied migrations or mergeability.

## Exit II: implemented seams and prerequisites

`mta/mdm/integration_source.py` admits base1–3 plus optional6 and13, optional complete4/5, complete7–9 and complete10–12. Unknown IDs, partial shared groups, an extra family1 row, missing base owners and mismatched owner receipts fail. Root schema, DLL, registered artifact identity, base configuration and all existing family validators still apply. Force/Season family artifact identity must match the root; their fixture-specific checks were not generalized.

`MdmSourceIntegration` stores one bounded immutable metadata receipt per source. Its SHA covers the original source digest, exact installed family receipt digests, applicable configuration files, a separate integration adapter identity and accepted anchor run/output/capture revision. It contains no business-state rows. Migration `0101_mdm_source_integration` adds only this owner and its INSERT size/type and UPDATE/DELETE/TRUNCATE guards. Binding checks the anchor's frozen source identity; the root MdmSource and family receipts are never rewritten. The baseline71ce853 adapter is explicitly pinned as `118b06f3fbee192ef2f5ca161f6ff1849b4b1f57ac4651896ce92117a227bdaf`; existing historical roster rules remain in the unsealed path. Broader combinations require the new integration seal, not an old adapter assertion.

The explicit `bind_mdm_integration` command requires `--source`, `--source-digest`, `--run` and `--output-digest`. It does not install families. Before it can succeed:

1. The branch's migrations, including0101, must actually exist in the owned database; none was executed here.
2. The original source and all desired family owners must already be explicitly installed under their existing admission rules. StopPIPO/shared Phase binders require an accepted own closing; bind those before adding supplier owners if the latter would exceed the unsealed historical roster. Installation after a completed integration seal is rejected, rather than silently changing its coverage.
3. `VF_MTA_PUBLISHED_RUN`/digest and the existing publication configuration must select that source's actual accepted successful DAILY_CHAIN run with a CONSUMED capture. It must be the unique terminal consumed node in that source's persisted predecessor graph. Independent roots/forks fail closed; neither business dates, timestamps nor UUIDs select a winner. The binding also rejects an unresolved CAPTURED leaf. Superseded failed captures remain retained. Installed Force/Season/Stop/Phase owners must all point to that same run.
4. Complete Force+Season onboarding is not supplied by the current installers: both remain separately approved fixtures. The command requires each family's supplement/override metadata to match its original root and neither combines those approvals nor constructs missing owners. The retained Force and Season roots cannot be spliced to satisfy this condition. Their presence in the supported roster is conditional code support, not an executable general-production onboarding claim.

`daily_source.require_binding` checks an installed integration seal before using the historical roster whitelist. Family/draft routes reuse that binding. `source.source()` additionally checks the explicitly selected accepted run against the integrated source's current consumed generation and family owner runs. It does not select a latest fallback or allow computation-only publication.

The existing MDM endpoint wrapper holds the existing source advisory lock from admission through response assembly. This closes the concrete race where `finalize_consumption` could advance mutable owners after the selected-generation check but before the reader queried them. Gateway authentication/payload checks remain outermost; no generic endpoint decorator or frontend changes. The lock is session-scoped, not a request transaction, so native decision statement commits remain intact. Integration/Stop/Phase binders use the same advisory-before-source-row lock order. Supplier/Stop/Phase installation rejects an unresolved frozen capture leaf; retained failed ancestors with completed retries are not mistaken for pending captures.

`daily_input.select_capture` records the bounded integration identity and checks that each installed optional group produced exactly its existing capture key. `execute_day` checks the own consumed predecessor after the existing idempotent-replay branches, reuses frozen retry snapshots, and verifies the seal before family input replacement. The Force and Season `prepare_working_input` functions validate both anchors before either overlay; singleton entry points keep the same checks. Stop/Phase replacement and native importer/calculation ordering are unchanged. Typed business bags still use the existing input tables; integration metadata consists only of scalar hashes/maps. No new state payload or engine is introduced.

`finalize_consumption` rechecks the frozen integration identity before the existing atomic supplier/Force/Season/Stop/Phase finalizers. Existing revision guards, late-approval deferrals, native task/archive/clear distinctions and rollback remain. The master9 native completion limitation is unchanged. A changed roster/config/adapter cannot silently consume a prior sealed capture.

### Exact reference port

`mta/mdm/owned_namespace.py` and the `daily_source_install.py` installer change are copied from reference `a6bdf1296239bc68c976a806e15551ee25935be5`; no operational cohort is copied. The installer still requires the exact registered base artifact `7ee7d940da3bab89ffeeddff94b4f2a7d9abace4aacdd589d698df6de85c24fc`. `install_daily_input_source` remains that bounded bootstrap, not general ingestion. The root adapter now includes the namespace guard; registration must pin that root adapter and artifact. Combined seals have their own adapter hash and preserve that original registration.

Outside historical `daily_3006`/`test_freshvcf`, the reference guard requires the independently provisioned `fresh_control.owned_namespace` singleton, dedicated database owner, issuer/consumer, `fresh_operational_acceptor`, `fresh_namespace_registrar`, exact OIDs/memberships/grants and matching artifact/adapter. This patch creates no registry, roles or grants. Missing registration fails closed. Receipt verification also requires inner namespace artifact/adapter to equal the original root. The registry remains outside Django migrations as the reference policy requires.

Git blob comparison confirms the guard is exactly `7dd98922468c57294aa37d599f786546f163a2fb` and the installer exactly `5a33c96e2698c1b8c0f8e6c2293cf905c0eb5f2d`, matching the pinned reference. Existing reference-environment registrations and acceptance receipts are not automatically transferred to this different branch/code identity.

## Exit III: delivery qualifications

Source/Git review only. No tests, Django/import/compile commands, browser/native checks, fixture work, business dates, service changes or activation were performed. The new migration is hand-authored and unapplied. General Force/Season source onboarding and an applicable combined operational publication policy remain absent prerequisites. Existing accepted-run policy remains fail-closed. No frontend, migration, runtime or production acceptance follows from this integration. Final delivery label: **integrated source port, UNVERIFIED**. One cohesive commit includes the residual reconciliation and plan artifacts; no automatic merge, activation or next cohort follows.

The bounded independent source review identified lock-order consistency, date-based generation selection and supplier installation during a frozen capture; each received the targeted correction above. Parent review also checked frozen anchor identity, fixture-root scope, immutable metadata guards and the response/finalization race. The namespace/installer Git blobs match the pinned reference exactly. Git whitespace/diff review is packaging evidence only, not runtime proof. External onboarding/admission limits are explicit limitations, not an open research or implementation queue.
