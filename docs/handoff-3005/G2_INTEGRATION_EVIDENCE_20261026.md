# Final G2 integration evidence

Status and sequencing live only in `F:/freshvcf/docs/handoff-3005/TRACKER.md`.
This appendix records bounded evidence, not general G2 acceptance.

## BPR history ownership

Fresh UptoBPR now uses the existing history producer before atomic BPR
acceptance whenever production report sources are configured. UptoDBM keeps
its required-history validation. An already accepted BPR returns before this
producer; no retained receipt or input is rewritten. Existing native release
compatibility fences execution across the code change.

The focused local suite passed 17 tests in `test_scope_bpr_histories`,
`test_production_scope` and `test_scope_runtime_reports` with Django initialized.
The first local invocation lacked Django settings and failed import; it did
not execute production code or access a database.

Four PostgreSQL tests passed in 21.334 seconds on the existing rollback-only
component database `VFTEST_Fresh_LifecycleG2_20261024`, inside the approved private
PostgreSQL copy. They cover exact typed histories at UptoDBM, fresh UptoBPR
release followed by a separate PostBPR DBM claim without recollection, and late
BPR failure/retry for both fresh scopes. The tests preserve accepted PRE and
prove no duplicate BPR acceptance. No new native run, database or schema was
created. PostgreSQL sequence gaps are not transactional and may advance.

Before and after row-multiset fingerprints match across 731 application/state
tables, 3,953 rows:
`9227b0287c339f6389f0810995c256d7ef99125267ef5100039ef47c50115dac`.
History assertions compare complete ordered values independently of this
whole-database preservation fingerprint.

Evidence root:
`D:/freshvcf-build/evidence/bounded-ui-recovery-20261023/g2/`.

| Artifact | SHA256 |
| --- | --- |
| `uptodbm-private-20261025/three-day-positive-test/final-g2-bpr-history-component-03.json` | `dc3583ad5f11455fe2e409042d380ac664c49c4ddb63e96cbf7116252ec36d50` |
| `final-g2-history-source-02/source-manifest.json` | `5b6d413905e1b68e059115e0b079fd769ca28c3365d22ff8fa17597d80cdfa58` |

Driver `qualify-final-g2-bpr-history-03.py` imports the immutable source snapshot
only in its own process within the existing MTA resource limit. Serving code,
images, gateway, frontend and MTO are unchanged. The two earlier driver failures
(missing Django secret setting; omitted baseline schema file) and both source
snapshots remain retained. Neither failure reached database work.

This is a component ownership/transaction proof. It does not qualify native
Full/split parity, a production report roster, successor execution or latency.

Retained evidence plus the existing PostgreSQL copy, including both new source
snapshots and failed drivers, totals 3,816,420,899 bytes against the approved
4,294,967,296-byte limit. Read-only accounting is retained in
`uptodbm-private-20261025/three-day-positive-test/final-g2-history-footprint.json`.
No evidence was deleted or compressed for this checkpoint.
