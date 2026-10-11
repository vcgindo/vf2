# BPR I1 index trial — rejected and rolled back

11 October 2026. Finite I1 delivery only; BPR default remains 5,000.

The exact approved `fresh_bpr_page_order` candidate was built once concurrently,
verified valid/ready, measured, then removed concurrently. PostgreSQL did not use
it in any of the nine actual after-plans. The scoped page selector retained its
permission hash joins, parallel scan and sort. The default-page SQL median missed
the 20% target. No index is retained and no performance improvement is attributed
to this candidate. Do not expand this result into a query rewrite or I2/I3 trial.

## Measurements

Three observations before and after per case, without warmups, cache flushing,
restart, planner forcing or resource changes. The initial admission EXPLAIN is
sample zero of each before set, not an extra sample. The actual unchanged `_build`
query preserves permission multiplicities, live remark handling, raw page order,
projected final order and duplicate reconstruction; JIT is locally off as in the
reader. All pages request 5,000 rows; later means page two. The selective request
uses the retained SKU21101050051000 filter with the broad actor's existing scope.

| Case | SQL median before → after (ms) | API median before → after (s) | Candidate used |
|---|---:|---:|---|
| Default first page, 5,000 rows | 842.362 → 692.748 | 1.7763 → 1.5880 | 0/3 |
| Retained SKU filter, 100 rows | 189.816 → 134.286 | 0.8869 → 0.8069 | 0/3 |
| Page two, 5,000 rows | 1153.863 → 782.436 | 2.2942 → 1.8192 | 0/3 |

These are small, sequential, cache-sensitive observations. Apparent improvements
without index use are not attributable wins. API timings cover the real MTA HTTP
endpoint inside its serving container using the retained trusted-gateway actor
contract, including reader/serialization/response transfer. They exclude public
3005 gateway, browser and grid time; no end-to-end UI or legacy parity claim.
The failed SQL/plan gate makes further gateway/browser measurements unnecessary.

## Correctness and containment

All nine before/after complete API JSON bodies matched exactly, including list
order, values, NULLs and duplicates. Broad count97,097, restricted count5,076 and
its first5,000 typed rows, and denied count0/empty rows matched. The denied check
is empty-scope reader denial, not a new unauthenticated gateway/security test.
Existing authentication proofs are unchanged and reused.

Runtime: freshvcf-preview-mta-1, image
`sha256:f94d47c65a0f68bc3a4614e4821d68c35c42a15b28d42c477c4ab0e57949862e`,
database test_freshvcf_stage2_vm_20261003_002, fixture
bfd75b4b-a9df-4a08-82d3-852e3324b623. Live reader SHA256
c2657bf310ce1c1ce44be7575ee5a93766f5130310308484c059b303092bcca3 matched.

Before build: 113.6GiB available; MTA178.9MiB/4GiB and PG228MiB/1GiB.
Query timeout60s, lock timeout3s, concurrent build/drop timeout120s; existing
maintenance/work memory unchanged (recorded in binding.json). Build took3.995s,
size14,884,864 bytes. Candidate absence was checked before creation. Before
rollback its exact DDL/validity/size matched the owned build receipt. After drop,
the original full BPR index catalogue matched exactly and candidate was absent.
Fixture binding confirms source, selection and seals unchanged. No failures were
hidden; no query, row, account, service, image or unrelated index was changed.

No migration or model change is retained because this index failed acceptance.
The final runtime and repository both remain at their original no-candidate
schema state; changed-migration checks and fresh-schema creation are therefore
not applicable. Paused MDM work and unrelated dirty files remain untouched.

Evidence: D:/freshvcf-build/evidence/bpr-i1-index-20261011-001 contains scripts,
actual SQL/payloads, all18 plans, complete compressed response bodies, scope
comparisons, build/rollback receipts and a SHA256 manifest. No full-publication
rescan, new business date or serving restart occurred. I1 is closed as rejected;
I2/I3 and all adjacent work remain outside this delivery.
