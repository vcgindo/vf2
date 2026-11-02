# Central execution settings: Part 1 qualification

Part 1 centralizes the supported execution controls without changing their
business meaning. Existing values are adopted exactly; new operations capture
an immutable settings version. Only the already-supported `AutoDBMActive`
integer `0`/`1` transition can be scheduled for an eligible future business date.
Other selectors remain fixed. **Part 2 is on hold.**

## Completed checks

| Area | Result |
|---|---|
| Populated upgrade | The normal upgrade adopted the actual values of an accepted 97,097-pair Day1/Day2 installation. The original selected Day2 remained readable. No initialization or accepted-day replay was required. |
| Accepted data | Complete ordered binary readbacks of 927 original tables, covering 4,916,136,577 bytes, matched before and after upgrade and the installation's own Day3. Original initialization, certificate, producers, run IDs and report receipts remained unchanged. The new settings revision is separately identified. |
| Own Day3 | Independent old-code and settings-enabled restores used the same retained Apr10 facts and their own identical accepted Apr9 closing. Both normal Full commands reached PUBLISHED/FINISHED, all 20 reports READY, run/output-bound readiness and acknowledgement. |
| Complete outputs | All 180 operational images, 12 derived images, 10 deferred exports, five consumer row tables and all 194,194 typed BTR display rows matched. Comparisons preserved types, NULLs, order and duplicates. Only individually authenticated new-run/settings provenance differed. |
| Future values | A separate old-code fixture configured with AutoDBM enabled matched the centralized future-date revision through its own successive Full days. Initial adoption did not replace supplied values with sample defaults. |
| Scoped and recovery paths | UptoBPR/PostBPR and UptoDBM/PostDBM retained their frozen revision. Mid-operation edits were refused. Failed-capture retry used the recorded version. A late BTR failure resumed reporting with all other 19 READY receipts unchanged and no calculation or intake replay. |
| Management and permissions | Invalid types, locked controls, missing rows, foreign exports and stale revisions were refused atomically. Repeated apply identified the already-applied revision. Concurrent capture/edit and rollback checks passed. Serving-role SELECT succeeded and all eight tested write operations were denied. |
| Schema and deployment | Actual PostgreSQL checks reported no Django issues, model drift or pending migrations. Only additive migrations 0247/0248 are introduced. Physical backup/restore and normal post-apply startup-failure resume passed. Real PowerShell 5.1 and 7 operator paths passed. |
| Consumer behavior | Existing case matching, numeric conversions, COUNT predicates, duplicate occurrences, NULLs and absent/cleared sources were retained. Native first/successor and case-variant fixtures passed against independent old code. |
| API and exports | Private authenticated HTTP and WSGI page/count/filter/empty-scope/identity-denial cases and complete BTR exports matched. These requests did not select current management settings or mutate saved state. |

The final affected checks ran 156 tests: 155 passed and one was skipped. Separate
actual PostgreSQL, host-command and full-workload checks support the results
above. Eight unrelated `test_native_publication` failures were independently
reproduced on the starting code; this is not a whole-repository green claim.

## Settings cost and observed delivery times

For the actual large installation, the catalogue contained 151 cells occupying
33,661 serialized bytes. Twenty resolutions made exactly twenty batched values
queries. Query plus finite compatibility projection took a median 3.283 ms,
95th percentile 4.109 ms and maximum 13.829 ms, below the 100 ms investigation
threshold. There are no settings queries in SKU/location loops. The original
whole-input integrity checks remain separate and intact.

| Normal Apr10 Full command | Observed operator time |
|---|---:|
| Starting code | 1h 16m 07.269s |
| Central settings | 1h 16m 32.130s |

Both isolated runs used the same daily worker 9 GiB/2 CPU and PostgreSQL
1 GiB/1 CPU/no-swap limits. These are qualification limits, not deployment
defaults. Build, upgrade, backup and extra readbacks are outside these clocks.
Cache/background conditions were recorded. Stage and overall clocks are
observations from one pair; they do not prove reporting performance equivalence
or a cause for timing differences. At the user's direction, reporting timing
investigation and repeat benchmarking were excluded from Part 1 closure.

## Release and limits

The full-workload runtime checkpoint is
`1cae18ed87f1432f2eb55e483692d70ded68aa26`. Subsequent qualification documentation
and a fail-closed regression test do not change its packaged runtime bytes.
All trials used owned isolated resources without application port exposure;
the existing user application was not upgraded or changed.

This qualifies the supported Part 1 settings arrangement. It does not unlock
missing legacy workflows, certify every customer configuration, or establish
new frontend/gateway/browser acceptance. No reporting optimization, resource
increase or Part 2 implementation is included. Runtime evidence and preserved
failed trials remain outside the shareable source.

See [execution settings](EXECUTION_SETTINGS.md) for commands and ownership, and
[the upgrade guide](../release/UPGRADE.md) for normal deployment.
