# UI performance measurement — stopped by human, incomplete

On 10 October 2026 the human instruction relayed by the controller stopped tranche A immediately. No more samples, browser calibration or tuning will be performed in this tranche. This is an incomplete, qualified observation set, not UI parity, a completed benchmark, or proof that tuning failed. MTO configuration-only verification is separately authorized to proceed without the former A-completion dependency.

Evidence: [raw samples](D:/freshvcf-build/evidence/ui-performance-parity-20261010-001/samples.json), [partial CSV](D:/freshvcf-build/evidence/ui-performance-parity-20261010-001/partial-timings.csv), [runtime identities](D:/freshvcf-build/evidence/ui-performance-parity-20261010-001/runtime-identities.json), [browser versions](D:/freshvcf-build/evidence/ui-performance-parity-20261010-001/browser-versions.json). Recorded errors and superseded observer attempts remain retained. No service, source code, data, grants or business-day execution changed.

Edge155 and Chrome154 were explicitly approved as a qualification. Actual resource equivalence, layout/visible columns and complete per-row output matching were not established. Timings include browser-tool/DOM observation overhead and cannot be called pure browser latency, native paint time, p95 or controlled parity. BPR defaults differed: legacy5000 versus modern50 rows. Buffer Trends snapshots could expose prior chart content before a fresh result; its incomplete samples do not establish usable completion. The browser connection later failed and was reconnected by the user; no measurements resumed after the stop instruction.

| Branch | Legacy observations (s) | Modern observations (s) | Legacy median | Modern median | Disposition |
|---|---|---|---|---|---|
| planning-overview | 11.463;6.755;4.642 | 3.127;2.783;3.089 | 6.755 | 3.089 | UNMATCHED |
| planning-fulfillment-primary | 12.979;10.967;10.494 | 6.781;6.797 | 10.967 | Unavailable | UNMATCHED |
| planning-fulfillment-grid | Unavailable | Unavailable | Unavailable | Unavailable | UNMATCHED |
| planning-fulfillment-custom | Unavailable | Unavailable | Unavailable | Unavailable | UNMATCHED |
| bpr-main | 14.796;10.073;9.394 | 5.579;8.781 | Unavailable | Unavailable | UNMATCHED |
| bpr-daily | 3.661;3.895;4.059 | 2.531;1.514;1.429 | 3.895 | 1.514 | UNMATCHED |
| rrr-main | 13.584;15.902;21.514 | 16.42;13.28;12.598 | 15.902 | 13.28 | UNMATCHED |
| btr-tech | 13.52;9.187;9.277 | 1.508;1.499;1.517 | 9.277 | 1.508 | UNMATCHED |
| btr-eco | 9.935;11.772;8.506 | 1.473;0.709;1.385 | 9.935 | 1.385 | UNMATCHED |
| btr-daily | 3.581;3.616;3.349 | 3.126;2.06;2.026 | 3.581 | 2.06 | UNMATCHED |
| dbm-main | 11.133;11.539;14.467 | 11.369;13.668;13.863 | 11.539 | 13.668 | UNMATCHED |
| dbm-daily | 4.378;3.249 | 3.063;1.784;1.874 | Unavailable | 1.874 | UNMATCHED |
| buffer-trends-onhand | 0.874;14.91;17.797 | 9.627;1.455 | Unavailable | Unavailable | UNMATCHED |
| buffer-trends-pipeline | 0.444;16.615;22.766 | 11.002;18.348 | Unavailable | Unavailable | UNMATCHED |

Only complete ordinary three-sample sets receive descriptive medians above. BPR mixed-boundary observations and Buffer Trends retain raw numbers but no accepted median. Fulfillment grid remains content-only; the loading indicator was not reliably excluded. The single permitted DBM modal observer recheck failed again, so its legacy median is unavailable. Legacy BTR pipeline initial observation failed in the observer; later branch observations are separate. A modern fulfillment invalid navigation and its retained recheck are not silently substituted into an ordinary sample series.

Among ordinary qualified observations, DBM main was slower on modern (13.668s median versus11.539s), while RRR was faster (13.280s versus15.902s). These do not isolate a bottleneck or establish comparative performance parity. No optimisation was attempted in this release.

Unfinished roster at stop: remaining fulfillment custom/product/detail proof; excess, GIT and expedite branches; Buffer Trends completion; Guided and Research branches; BOR/BOR-OA; RRR colour; supplier/allocation and other explicit report dispositions. These are NOT TESTED in this truncated tranche, not passed or inferred unavailable. Prior populated correctness receipts are not substituted for current timings. Existing source and functional qualifications continue to apply.

MTO status and its blocked business journey are recorded in [the bounded handoff](MTO_SAME_PRODUCT_INTEGRATION_HANDOFF.md). The stopped measurement does not block that separately requested verification.
