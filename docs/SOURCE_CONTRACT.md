# Canonical execution contract

This map governs sequencing, not status. Status is only in MIGRATION.md.
Paths below are relative to the pinned `mta-engine` root.

| Business capability | Canonical producer / execution boundary | Required downstream behavior |
|---|---|---|
| Raw input and validation | VectorFLOWv4.bat → ImportAllRawData.bat → ValidateAndProcessInputData; ImportMasterDataComponents resets SKULocStandardAttributes | Explicit raw vs processed inputs, rejection behavior, daily scratch reset, retained catalogue |
| Controls and master state | VectorFLOWv4.bat Norm changes / parent validation, then task status | Accepted/forced Norm, phase and seasonal changes precede BPR; DBM opening is distinct from refreshed supplier state |
| Current-day requirements | RunCoreBPR.bat: ImportData → StockCalculation → GenerateAddionalMasterData → ImportSpikeOrders → CalculateDD → CalculateRoute → CalculateReq → ConsolidateReq → UpdateBPPAndColorForOrder → ReqInColorBand | Typed stock, order route/remainder, CNR, requirements, colors/bands and allocation |
| Rationing and dispatch | RunCoreBPR.bat: NormRationing.bat → CollectDataForPSORationing → PSORationing → GenerateRationReqReport → GenerateBifurcationOfRationedReq → GenerateLogisticPickList / PickListReports | Full normal/PSO/advance and formed/remaining Pick populations; no count-only claim |
| Planning/report producers | RunCoreBPR.bat: UpdateBPR, exception reports, GenSupplierWiseReq, ProdOrderSuggestions, Planning.bat | Preserve BOR opening vs refresh, RRR, Fulfilment, Expedite, GIT and Excess contracts |
| DBM and recommendations | RunCoreDBM.bat: daily/exclusion/order imports → ExtendedOCP → ordered suspension scripts → rules 1–6 → conditional 7/10/11 → conditional12 → DiscardSuggestions → GenerateReports | Precedence, thresholds, row multiplicity, state histories and true next-day effects |
| DBM outputs/workflow | OrderSummary, Norm1 advisory, phase recommendations, conditional AutoNormAcceptance, norm-change and suspension history, Norm0/1/2 reports, cleanup | Apply/Sleep/control state, report outputs and retained temporal state; API actions use deployed clock semantics |
| BTR, final state and delivery | RunCoreBufferTrend.bat → site PostBTR → runtime reports → generic/site final processing | Computed BTR/history/insights and persisted own-state closing; consistent API/UI publication |

The top-level engine also has site hooks before/after importer, BPR, DBM, BTR
and final processing. Selected site is GulfOil. Its external file adapter is
customer-specific; common standard-input acceptance and adapter acceptance are
separate obligations, not permission to remove either from the selected path.

## Activation boundaries

- MTO-only BPR OrderAllocation.sql runs when VFSettings.IsMTOEnvironment=1.
  The selected MTA profile is 0; do not fabricate that screen's combined population.
- Rules7/10/11 use DBMSettingsTbl.NormZeroOneRuleActive; retained effective setting
  is 0. Site-specific rule SQL overrides generic SQL only where present.
- Rule12 uses DelistingofNormRuleActive; retained effective setting is 1.
- AutoDBMActive defaults to 0 in StdSettingsPre.bat. Trial auto-Apply/Sleep is an
  explicit workflow driver; it must not silently enable a different batch profile.
- DistributorSystemActive and VendorSystemActive default to0; GulfOil settings
  do not override these flags in the inspected source. DB-held mutable values
  must not be inferred from file defaults where a DB query governs behavior.
- RuntimeReports uses Active=1 and RunPlacement to select downloadable reports.
  Configuration/consumer inventory remains part of F3; generic placeholders cannot
  certify missing routes.
- NormZeroOneRuleActive is also consulted by raw order import. Imports from UI
  vs files are gated by FNCFromUI and PI_PO_FromUI. Record boundary-specific facts,
  never assume a file is selected merely because it exists.

## Comparison rules

The calculation roster includes the20 current-day checkpoints and eight major
daily boundaries (controls; BPR/BlueZone; DBM imported; final suspensions;
final suggestions; post-rule reports; BTR/insights; full closing state).
Use full typed bags including duplicates. Preserve nondeterministic legacy
outcomes as qualified/unaccepted contracts, not repaired oracle values.

State ownership: daily external facts are separate from engine-owned carry.
Daily scratch must be reinitialized by the actual selected producer; Category
accumulation cannot be assumed cross-day carry. Previous state comes from the
same engine's persisted preceding run, never a paired oracle's output.
