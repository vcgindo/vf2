# Step 1 application baseline

Recorded 13 October 2026. This is evidence and source disposition, not a second tracker. The live tracker decides closure and later releases.

## Source and recovery identities

The new branch is `codex/3005-production-handoff`, at managed worktree `C:/Users/thapa/.codex/worktrees/handoff-3005/freshvcf`, starting from `ff43036d77dad9198d972c48d4d954fc8b138986`. This is the existing 3005 lineage, including accepted daily/MDM source commit `587757de00f6c38d4dc9bb991d0bd32bf3c2c1af` and the normal serving resource configuration. It is not the rejected handoff branch and is not an exact source match to the serving images.

The deployed Planning source checkpoint is `0dcd43b473df4ee2f18933c8f108620490240a7d`, with retained overlays. Of 804 deployed MTA code/configuration files, 778 match that checkpoint and 756 match the new branch base. All 48 differences from the branch have per-file hashes and dispositions in `source-dispositions.json`: 24 accepted later files, 3 overlapping accepted/deployed changes, and 21 deployed runtime files retained for deliberate integration. No dirty source or donor patch has been copied into application files in S1.

The exact 804-file deployed source archive is `deployed-mta-source.tar.gz`, SHA256 `b0da6767cca9045934f55c030662ffc5e68273d40b2ea27dd973d0b4be0af3f5`. Every archive member was read back and matched to its live container SHA256. It contains only the explicit mta/vectorflow code/configuration roster plus manage.py/requirements.txt; no environment file, database or fixture population. The archive is an external recovery input, not runtime code added to the branch. It prevents silent loss of deployed Guided, Planning, cache and prepared-reader changes.

Before rebuilding any affected path, reconcile that file's deployed archive member with the accepted branch version and preserve the relevant behavior. Mixed model/migration files must retain both accepted ownership/schema changes and deployed reporting prerequisites. Never blindly overlay all 804 files on the branch: that would regress the accepted daily/MDM changes. Unfinished checkout changes remain excluded unless a later released item deliberately selects them.

**Reproduction limit:** the operating reference can be identified and its captured MTA source recovered. A clean source build of the complete six-service stack from this branch has not been demonstrated. The branch does not yet contain all deployed overlays; frontend/auth/MTO source-to-image equivalence has not been proved afresh. Existing immutable local images and retained frontend build directory are operating references, not a portable release. These gaps are explicit inputs to S2/S3 integration and S4 packaging, never claims of production readiness.

Evidence root: `D:/freshvcf-build/evidence/handoff3005-s1-20261013-001`. `runtime-before.json` records all six image IDs, effective safe configuration, environment digests, ports, limits, mounts and start times. `compose-reference-hashes.json` pins effective Compose file references without importing secrets. `source-checkout.json` preserves the original dirty-file boundary. `mta-source-reconciliation.json` and `historical-source-reconciliation.json` retain the exact comparisons.

## Serving identity

| Component | Pinned identity / observation |
|---|---|
| Frontend | planning-simple-20261011-002; image `384dbbe639b7e8c407920d8ccbef6f693d4ded6f9e4dc31b8033d61c323701dd` |
| MTA | planning-simple-20261011-002; image `cb08fa3abe1f1fb93160cbf2d6bffd72dd6e207e1f4c961dee959fd087f71160` |
| Gateway/auth | image `1c226612541b36f135a352e2d626cee778ca479c55b5f302447ff5f7eca7e8e0` |
| MTO | image `bc5a6fb828bc9e0123a837763c9d3cbf6f4f8e8fbd1e91f10c73a0e1c373ab5f` |
| Redis | image `858f009f9709ce576febc734aa78b8f6d624b82571f9ddb6bda4377c833b3499` |
| PostgreSQL | 16.15; image `721873c34ceb9f8d8fc265984940dc982404c105f19ad51be9fdc5970a6080ea` |
| MTA database | `test_freshvcf_stage2_vm_20261003_002` on `freshvcf-test-postgres-1`; auth/MTO database is separately `freshvcf` |
| Selected run | `bfd75b4b-a9df-4a08-82d3-852e3324b623`, 7 April 2026, kind LEGACY_UI_FIXTURE, status FIXTURE_BLOCKED, no native output digest |
| Fixture owner | stage2-vm-dataset-20261003-002; serving descriptor SHA256 `a6b28597dc5ec7d5e013521f548da0f90512d64834d3c8e869225033fc2a3f3d` |
| BTR generation | `e5bdac30-bbd9-45d8-a93d-84a645fad73c`, READY, eligible, same fixture run; 194598 rows according to its receipt |
| Prepared receipts | BPR 97097, RRR 8063, Guided availability 8483003, Guided excess 920774; receipt metadata only, no source-table count/scan |
| Publication | No DailyUiPublication row for the selected fixture run. Native daily publication is not selected. |
| Serving flags | BPR, RRR, Guided, history, Research availability and Planning summary preparation enabled. BTR generation explicitly selected. |
| Schema | Applied mta migration metadata includes 0114/0115 Planning and 0110/0112 Guided prerequisites. The new branch also has later accepted merge/MDM migrations; no serving migration was run. |
| Resources | Existing MTA 3 CPU / 4 GiB and PG 2 CPU / 2 GiB; no changes by S1. |

This establishes that 3005 is a healthy fixture-backed presentation application. It does not establish that ingestion, native producers, own successors and every report work together in a new deployment. Prepared relational tables/projections exist; do not assume that every endpoint uses a PostgreSQL materialized view or a native prepared reader.

## Bounded browser baseline

On 13 October, /login and /readyz returned 200; readiness reported identity database, MTA and MTA catalogue ready. The retained broad account logged in successfully after one rejected CAPTCHA and an explicitly approved replacement. No credentials were changed or recorded.

Planning rendered 7 April 2026 and counts: transit parent/child 1627/1627, expedite 1030/1030, excess 9871, fulfillment 12720. Selecting SKU 23103123007000 left the overview counts unchanged. This is an observed limitation requiring contract/dispatch checking in S3, not a diagnosed calculation defect. The filtered Order Fulfillment grid did apply that SKU and showed 21 rows; the first row was CDC2, virtual norm 7896, norm 6950, stock 400, GIT 0, rationed quantity 4500.

Ordinary Excel Export produced an 8092-byte workbook with 21 data rows, all containing the selected SKU, and matching the observed first-row values. The browser download event timed out, but the newly timestamped Downloads file was located and its XML inspected; both outcomes are retained. Export hash `abadf513d80333714bcfceb3bc6e111d4e4b9b778d3cbec6e6b5b03800ea407e`. This is a bounded report download, not migration of the heavy population.

Fresh evidence: login-success.png, planning-baseline.png, planning-filter-counts.png, planning-filter-grid.png/.txt, planning-one-sku-export.xlsx and ui-export-check.json. No precise click-to-usable latency is claimed: loading states were observed, but these manual tool observations are not a controlled timing trial. No Apply/Sleep, remarks, layout save, MDM approval or engine execution occurred.

Retained scope evidence is limited to `D:/freshvcf-build/evidence/planning-screen-20261011-001/simple-proof.json` and its broad/restricted screenshots and response samples. Its source digest equals current prepared source `4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73`; final image tags match. It supports historical Planning broad/restricted/denied/overlap scope observations, not fresh restricted login, all-report correctness or current performance. The earlier 50% performance target was not met and is not inherited as a pass.

No heavy data was copied/restored or rescanned. No services, schema, calculations, selected generation or business rows were intentionally changed. Login/session writes and normal report requests are the authorized browser effects. Protection comparison is scoped to captured container/configuration/mount identities and selected metadata; this is not a whole-database byte comparison.

Final protection check: `protection-check.json` passes all captured identities, images, start times, environment digests, mounts, memory/swap/CPU settings and ports for all six containers. Unrelated original-checkout Git status is unchanged. `selected-metadata-after.txt` preserves the same selected run and BTR receipt. `schema-metadata-digests.txt` pins sorted migration/column/index/constraint metadata; no schema or data migration ran.
