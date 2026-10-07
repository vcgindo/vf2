# Modern DBM 33.733-second diagnostic

**Incomplete: stopped at the first isolated-setup failure; zero engine samples
executed.** Docker refused the probe network because all predefined address
pools are fully subnetted. No network repair, retry, accepted-run write or
serving change followed. This is not a fine-grained profiling result.

The latest direct human amendment `01a1176f-0cc3-7b00-8a47-1367d41057db`
authorized one offline June6 day per engine, sequentially, with instrumentation
only inside DBM. It superseded the earlier native-opening prerequisite: the
normal day flow would supply that opening without a reconstruction programme.

## Measured attribution available

| Boundary | Exclusive wall | Worker CPU | Calls | Meaning |
|---|---:|---:|---:|---|
| Modern `calculation/dbm` | 33.732720 s | 33.729016 s | 51 | Time advancing `chain.selected_stages`, excluding separately timed nested spans |
| Individual DBM stages/functions/primitives | unavailable | unavailable | unavailable | The retained wrapper did not record these |
| Profiler overhead within that bucket | unmeasured | unmeasured | — | No uninstrumented paired sample; do not assume zero |
| Legacy `calculation/dbm` reference | 18.770936 s | 0.171875 s client only | 64 | Aggregate client elapsed around selected DBM SQL script execution |

All **33.732720 seconds remain unallocated below the modern bucket**. The near
wall/CPU equality indicates worker CPU activity; it does not distinguish Python
loops from in-process SQLite, copying or other native work. Do not add the legacy
row to the modern total, infer SQL server CPU from client CPU, or claim a matched
speed ratio. No finer retained legacy timings are available in these samples.

## Boundary already established from retained evidence

The retained `timing_probe.py` wraps `mta.temporal.chain.selected_stages`:
each `next()` runs inside the DBM span. Fifty yielded stages plus termination
explain51 calls. Child spans are subtracted when separately wrapped; there are
no function-level timings. Caller work between yields is outside the bucket.

- `mta/domain/dbm_selected_chain.py:selected_stages` dispatches ingestion,
  suspension1–26, rules1–6/12, postrules, order summary, norm advisory, report/
  history writers, enabled norm0/1/2 reports and cleanup.
- `mta/domain/dbm_connected.py:connected_stages` owns the initial connected
  sequence; its first snapshot is after `ingest_dbm`.
- `mta/evidence.py:snapshot` returns the working state in production mode.
  Domain-local copying and ordinal-index work remain within the DBM boundary.
- Upstream assembly/BPR, between-yield report copies, subsequent BTR and final
  PostgreSQL persistence are outside this measured bucket; none was investigated.
- The legacy timing wrapper places `DailyDataImportExport` scripts in its import
  bucket. Modern DBM includes its own ingestion. Database resources and embedded
  capture also differ. These labels do not prove comparable work or a speed ratio.

No measured evidence ranks DBM hotspots yet. For example,
`mta/domain/dbm_ingestion.py:calculate_extended_ocp` scans masters/daily rows per
attribute, but that code-level scaling risk is not a measured dominant cost.
No optimization or time-saving estimate is proposed before attribution exists.

## Failure, resources and next prerequisite

Evidence owner: `D:/freshvcf-build/diagnostics/dbm-33733-001`.
`postgres-setup.log` preserves the failure; `setup-failure.json` records resources
and verifies the protected-service snapshot is unchanged. The reserved
`freshvcf-dbm33733-001-pgdata` volume exists; no probe PostgreSQL container or probe
network exists. The volume and private compose are retained, not deleted/reset.
No SQL namespace was provisioned and neither engine was invoked.

The attempted standard setup preserved the prior worker4GiB/twoCPU and
PostgreSQL1GiB/oneCPU limits, with no host ports. It would have used the immutable
refinement image `sha256:3791d148878aae8780200cb91fcee9e90920f9afb6f63f974d07a3569330c48f`.

A usable permitted Docker network is required before resuming setup. Reusing the
existing approved probe network is a possible bounded remedy, but was **not
executed** after the stop-on-first-failure instruction. Do not restart/prune
Docker, change shared address pools or retry calculation to address this failure.
After a human continuation decision, the intended work remains one sample per
engine, minimal external DBM timers/profiler and one compact hotspot report.

## Preserved identities

- Baseline evidence: `D:/freshvcf-build/refinement/integrated-001/timing_probe.py`,
  `modern-timing.json`, `legacy-timing.json`, `legacy-timing-worker.json`.
  Their pins and the initial missing-opening observation are in `evidence.json`.
- Original modern timing run: `f6842ba8-f3f3-4012-8be0-e43aea0aa48a`.
- Frozen1240-pair June6 input SHA256:
  `ee707e71eb134f8ade084bef95d4ff915d8ba94a50776e0c1621e5a3bd0b0f56`.
- Refinement `99d4854`/`b884ff7` and readiness `b89c790` remain unchanged.
  No optimization, parity rerun, publication or temporal continuation occurred.
  Full-run/publication holds remain in force.
