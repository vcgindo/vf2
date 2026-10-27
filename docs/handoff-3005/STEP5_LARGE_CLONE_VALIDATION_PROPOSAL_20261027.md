# Step5: fresh Git clone to three-date large-data validation

**PROPOSAL ONLY — 27 October 2026. No execution release.** The sole status authority is `F:/freshvcf/docs/handoff-3005/TRACKER.md`. This document defines one proposed cycle, not another queue. Step4 and the independently accepted permanent localhost:8080 promotion stay closed and preserved. Step6 will document commands actually exercised successfully in this cycle.

The human asked for the retained approximately 97,000-row dataset and a couple of additional dates. The subsequent direct answer to `call_6e13cf4d7ae64644a0c43776030791c6` is **“Three total dates — add two.”** Therefore the proposal is opening **7 April 2026**, retained daily facts **8 April**, new external facts **9–10 April**, and **exactly three Full daily executions**. Preparing this document does not authorize generating those facts, cloning, building, creating resources, loading data or running a day.

## 1. Frozen source and evidence boundary

Clone `git@github.com:yurtse/freshvcf.git`, branch `codex/bounded-ui-recovery`, then detach at **`022e9ef2b5e33e8f762ab52fc01f75acd33e613d`**. That accepted documentation checkpoint has no non-document difference from application baseline **`ba32643250c1c3b916cd400fd801ae88b57122c6`**. Frontend/auth corrective source is **`c63161ed35955add4ffdddf07042e131d484ca15`**. Build all four application targets from this same clone. Newly built image/native identities must identify this exact checkout; do not substitute the old deployed image ID or relabel an existing sealed database.

The companion `STEP5_LARGE_DATA_PINS_20261027.json` (SHA256 **`8d5f1f2a752eee829b7fdd8ba36f2d686b21221a21a4b1dc7dc51ab8470fc16d`**) records physical file hashes, ordered headers/counts, source files and historical receipts. All 167 opening CSVs were independently rehashed and read through `csv.reader`; every manifest hash, ordered header and row count matches. These are read-only inventory results, not fresh-install acceptance.

| Population / artifact | Verified meaning |
| --- | --- |
| `D:/freshvcf-build/evidence/large-data-day1-benchmark-20261019/csv/MasterDataRaw.csv` | 97,464 raw master rows; SHA256 `3bb8e675520480c234d5daadcc31144f65759b6ffac7a5e88e93a18b608455ad` |
| Same directory, `MasterData.csv` | 97,097 normalized master rows; SHA256 `bea437f82fba74677a2dad51a77fa3d77daf25bc7f8feda9e78f71f80b91881b` |
| `I:/VectorFLOW-benchmark-20261020/fresh-start/opening/` | Actual cold-start input: 167 explicit populations, 1,692,306 CSV rows, 129,445,303 CSV bytes; zero daily history; 2,189 SKUs / 235 locations in retained qualification |
| `opening/opening-manifest.json` | `vectorflow-initialization-csv-v1`; SHA256 `889e2021cca5d0665718a7bf827673c7995d47443489c05c50aefd6d9ec61489` |
| `opening-original.json` | 438,689,733 bytes; SHA256 `27b3893b0f8a0f0db0197439c760677e9dc6dca07ad00f26fc4297781dd57a70`; provenance original required by normal onboarding |
| Configuration / recipe | `214a1c4326975ddbf9ea67a2535fa4130d3ec3a5958320ab68b80624b1f795fc` / `b76147260e3f58cd2fbe16a370bfe7d562f3160843595a2e9bfb853ae4fe176d` |
| `fresh-start/2026-04-08/DailyDataRaw.csv` | 97,097 rows / distinct pairs, all ReportDate 8 April; SHA256 `5714e18c51c4a65bb636bedc8437b4003d870e2c7da11eb97b72660184afce20` |
| Previous clone `D:/vf5/git-clean-build-20261018/source` | Actual HEAD `78775f4989737b9612f2dc0c350971338457af07`; retained image/source/locked-dependency receipt exists. Its two-date starter is small, not this large pack |
| Small starter | 200-SKU / 20-location catalogue, 12 active pairs, 16 daily rows/date, 18–19 October. Its two-date own-predecessor receipt is applicable only to that boundary |

Large pack provenance is `stage2-vm-dataset-20261003-002`, source manifest `afe42593ca2abdf5e2395433ac70834723f4eac1dfa5a2982192c7688906b836`. Preserve its catalogue, hierarchy, exact typed NULLs, Unicode, codes, duplicate ordinals and source order. Opening current masters, 10,256 outstanding orders and existing suspension/control state are declared operational opening state, not newly generated recommendations. Do not replace them with warm history or future calculated outputs. The older 97,299-row warm BTR snapshot is a different population.

Historical Full49, `49efa557-a31f-4ea8-9089-b510f2856d30`, committed output `ee1f58bb9e2161b6bca5ebf5bdbb0993ae75a060e5e9312d2181b750782949ad`, has full relational readback and exact closing/next-opening digest `160435d0b62d7777bb94e40c09185cd3389308d230adb52dc4eddde4f12deb46`. Its original human-stop receipt explicitly says report generation INCOMPLETE; later report qualification does not rewrite that failure. Neither that run nor its database is a fresh-clone dependency or seed. A whole-output equality claim across releases requires exact matching input/configuration/algorithm contracts; count equality and excluded identity fields cannot substitute for it.

## 2. Exact proposed input preparation

After execution approval, create one new **unbound** input directory `D:/vf-step5-large-20261027/input`, refusing an existing destination. Whitelist-copy only `opening/`, `opening-original.json`, `binding-template.json`, `consumer-opening.json`, `permissions.json` and `2026-04-08/` from the retained cold pack. Verify all companion pins before and after copying. Do not copy any `binding.json`, `binding-final*.json`, other `binding-*.json`, old `compose.csv.json`, initialization receipt, run archive, database dump or accepted output. The template remains unchanged; the normal launcher writes fresh installation IDs and access configuration itself.

The current binding is intake **`fresh-production-day-input-v5`**, with 11 CSVs/date. Do not substitute the generic v2 fourteen-file roster. Every date has a complete `batch.json`, every feed explicitly PRESENT, and READY written last. New files follow the current published ordered type/NULL/width grammar; retain `\N` as NULL, never a guessed zero. New batches receive unique identities and a sealed producer manifest with input hashes, algorithm version, row ordinals and conservation checks.

The following is the proposed **external fixture-producer contract**, requiring approval with this plan; no files have been generated:

| Feed | 9–10 April rule |
| --- | --- |
| `DailyDataRaw.csv` | Same 97,097 ordered pair identities. Maintain a separate external stock ledger, never read engine output. The retained `tools/large_data_benchmark.py` already writes closing Stock into the day8 CSV. For known day8 Stock, initialize external closing8 = supplied Stock8; never apply day8 C/R again. For date d, external opening_d = external closing_(d−1), Receipts_d = 0, Consumption_d = min(retained nonnegative Consumption8, external opening_d), external closing_d = external opening_d − Consumption_d, and supplied Stock_d = external closing_d. Record all cells and prove nonnegative conservation before sealing. All 18,788 known-stock rows have non-NULL C/R. For 78,309 NULL-stock rows retain Stock NULL and retained Consumption; set the non-NULL Receipts cells to zero to assert no new arrivals. Preserve every NULL flag and mark stock conservation unavailable, leaving the existing native missing-input policy in control. Do not invent stock for them. |
| GIT / PSO fields | Retain day8 GIT snapshot (2,567 positive, remainder zero) and zero PSO. No new transit movement or arrival is asserted; new receipts are zero. These aggregate legacy daily cells do not certify populated shipment-detail parity. |
| `MasterDataRawNonNMS.csv` | Exact unchanged 7,661-row raw attribute snapshot, byte-identical; no calculated Norm copied back as external input. Existing active-NMS ownership stays authoritative. |
| `NoNormMasterRaw.csv`, `AcceptedNorms.csv` | Header-only, as retained. No fabricated approval, new force request, action or Norm. |
| `OrderData.csv` | Header-only: explicitly no new order events on these two dates. Existing `import_orders` retains earlier dates and replaces only the current ImportDate, so this does not delete prior order history. Do not re-date/replay the retained 333 events. |
| `OrderFeed.csv` | Header-only PRESENT, deliberately an empty external snapshot rather than MISSING. Existing `reconcile_order_feed` empty-feed branch retains prior orders whose pairs remain in the master, and closes only excluded-master pairs. It does not mean “close every order.” Prior order state comes from the new installation's own predecessor. Do not repeat the 12,671-row day8 snapshot as fabricated amendments. |
| `AdditionalDataStockForReqCalc.csv` | Header-only PRESENT: no new stock override assertion; do not repeat the 216 day8 exceptions. Existing native stock/NULL policy owns the resulting behavior. |
| Distributor/vendor transactions, `InTransitRaw.csv`, `Transporters.csv` | Header-only, retaining the existing empty contract; no receipt, dispatch, transporter or fabricated parent movement. |

All DailyDataRaw ReportDate cells become the explicit new business date. No historical CustomerExpectedDate, SKUIntroDate, order/event date or configuration date is shifted. No additional facts are generated from calculated allocations, DBM outputs, accepted Norms, suspension history or run rows. External ledger closing and engine operational closing have distinct ownership and must never be substituted for one another.

The repository's `csv-sample` / `tools.create_daily_csv_example` supports the fixed small starter only. There is **no supported general command to generate these two new large external batches**. Do not pass large data through that helper or mount historical external benchmark builders into production. Execution approval must include implementing/reviewing one small fixture-only producer outside application images, implementing precisely the table above, with a no-overwrite destination, manifest and pre-seal validation. A producer rejection stops before initialization/day execution; a semantic ambiguity requires a revised decision rather than a guessed default. This is an honest preparation prerequisite, not a missing runtime import command.

Max retained RLT is 60 days; three times that is 180 days. The explicitly chosen three-date cycle is a fresh-install, short successor-chain and large-report rehearsal. It cannot certify 180-day temporal/history coverage. Preserve the retained 90-day BOR/RRR report policies and approved BOROA nullable supplier-text qualification (`APPROVED_NULL_AVAILABILITY_NOT_LEGACY_PARITY`); do not invent history or advertise those limitations as parity. No new transit-time rule is needed because no new shipment facts are proposed.

## 3. Proposed footprint and admission gates

One new project **`vf_step5_large_20261027`**, one private bridge network and its own PostgreSQL/Redis/application/secret/receipt volumes. Internal database names may use the repository defaults because the entire PostgreSQL container is new and exclusive. No connection to an existing test/live database, old opening or old image. No published PG/Redis/API port. Proposed sole new mapping **127.0.0.1:8091**, requiring explicit human exception approval; observed free on 27 October is not an execution-time reservation. Use `restart: no` throughout.

All new clone/input/operations/evidence storage is under `D:/vf-step5-large-20261027/`; only this project may be stopped on failure. Preserve accepted 8080 and its four exact components, six business databases, Full49, Step3/4 pins, all old failed attempts and all other services. No cleanup/prune/shared restart, old database copy, port switch or permanent cutover. No MTO scheduler, new MTO facts or MTO algorithm validation; retain the transferred MTO integration boundary.

Proposed finite test profile, explicitly separate from production sizing: initializer **provision** and daily worker 8 GiB / 2 CPUs, serving MTA 4 GiB / 2 CPUs, PostgreSQL 2 GiB / 1 CPU, auth and MTO each 1 GiB / 1 CPU, Redis and frontend each 128 MiB / 0.5 CPU; installer helpers retain the versioned resource-test limits. Set memswap equal to memory. The existing resource overlay gives provision only 512 MiB and daily 4 GiB: using it unchanged would be incorrect for this proposal. Use it with a final deployment-only override for provision/daily below. No memory increase or semantic edit after a failure.

Admission before each expensive operation must reserve the incoming worker's full 8 GiB plus 2 GiB for this project's other active services, keep host available RAM ≥2 GiB, combined Docker working memory ≤12 GiB and at least 2 GiB below Docker's allocation, and prove no interference with protected services. During daily work the launcher stops only its MTA. If these conditions cannot hold, do not start. The observed Docker allocation was 15.46 GiB, host available about 9.79 GiB and existing Docker RSS about 5 GiB: **current inspection does not prove fit and likely blocks admission**. Do not stop another owner's jobs or resize Docker to make it fit. A resource decision or naturally available capacity is required before execution.

Proposed incremental disk ceiling **32 GiB**, including clone/input 1 GiB, images/build cache 6 GiB, new database including WAL 20 GiB, compressed evidence 0.5 GiB and 4.5 GiB unspent preservation reserve. WAL is included, not a second allowance. These are proposed ceilings, not measured three-day requirements. Require ≥52 GiB free on the actual backing D: filesystem before entry and ≥20 GiB remaining throughout; preserve ≥20 GiB on C: and I: and ≥10 GiB on F:. Observed D: free 58.9 GiB is a planning snapshot only. Attribute incremental build cache, named volumes, container layers/logs, input/receipts and evidence without double counting. Standard Compose volumes have no automatic 20 GiB quota: a bounded observer must enforce stop thresholds. The prior permanent8080 100 MiB allowance is closed and cannot fund this cycle.

Maximum elapsed envelope **16 hours from first build**, including build ≤2h, initialization ≤2h, each of three daily operations ≤3h including publication, and remaining 3h for readback/browser/final preservation. These are stop ceilings, not an ETA or performance claim. Historical large initialization took about35min; Full49 saved-day time about67.5min plus10.1min full readback and14.1min next-opening proof, with an8GiB profile. Its incomplete report attempt establishes no completed report time. Observe current behavior; do not assume a speedup.

## 4. Concrete proposed command sequence

These commands are **not executed**. Run sequentially, from the new source directory, checking `$LASTEXITCODE` after every native command and stopping at the first error. Requires Git/authorized repository access, PowerShell5.1 or7, Linux/amd64 Docker Desktop, Compose≥2.24.4 and network access to the pinned base images/dependency registries. Host Python is only a fixture/evidence preparation tool; installation and daily operation must use the clone's normal commands.

```powershell
git clone --no-checkout --single-branch --branch codex/bounded-ui-recovery `
  git@github.com:yurtse/freshvcf.git D:/vf-step5-large-20261027/source
Set-Location D:/vf-step5-large-20261027/source
git checkout --detach 022e9ef2b5e33e8f762ab52fc01f75acd33e613d
git rev-parse HEAD
git status --porcelain
Copy-Item -LiteralPath .env.example -Destination .env
```

Refuse an existing root/project/volume set; never overwrite it. Do not clone dirty `F:/freshvcf`. Set only the following deployment values in the new ignored `.env`, preserving all other template values and keeping the new admin password private/prompted:

```dotenv
VF_PROJECT=vf_step5_large_20261027
VF_IMAGE_PREFIX=vf_step5_large_20261027
VF_RELEASE=source
VF_BIND_ADDRESS=127.0.0.1
VF_HTTP_PORT=8091
VF_CSV_INPUT_DIR=D:/vf-step5-large-20261027/input
VF_DAILY_STATE_DIR=D:/vf-step5-large-20261027/operations
COMPOSE_PATH_SEPARATOR=;
COMPOSE_FILE=compose.yaml;release/compose.resource-test.yaml;D:/vf-step5-large-20261027/deployment.yaml
```

Prepare this deployment-only final override after approval, outside source export:

```yaml
services:
  provision:
    mem_limit: 8g
    memswap_limit: 8g
    cpus: "2"
  daily:
    mem_limit: 8g
    memswap_limit: 8g
    cpus: "2"
  auth:
    environment:
      VF_AUTH_SITE_CACHE_URL: redis://redis:6379/1
      VF_AUTH_SITE_KEY_NAMESPACE: vf_step5_large_20261027
```

The site-key configuration is necessary to transfer the accepted retained-session boundary. Current code supports it, but root Compose does not supply these optional values automatically. Without both, auth intentionally uses the old process-local boundary. The new private Redis database/namespace is deployment configuration, not shared permission-cache replacement or a source patch. The committed `release/nginx.template` already supplies Planning gzip, immutable static assets and no-store index; do not mount old window gateway helpers.

```powershell
docker compose build
docker compose run --rm install
docker compose up -d --no-build --wait
docker compose ps
.\vf.ps1 csv-init
.\vf.ps1 csv-day 2026-04-08
# Close the first-day state/report/browser proof before the next date.
.\vf.ps1 csv-day 2026-04-09
# Close the second-day own-predecessor/state/report proof before continuing.
.\vf.ps1 csv-day 2026-04-10
```

One clean build command covers four application targets, each once; common intermediate stages may be shared. PostgreSQL/Redis are their pinned official images. Record actual source export, native manifest, dependency locks and all resulting image identities. Use no old application image ZIP, hand-built context, external wheelhouse, workstation-only helper or existing database. Build cache reuse of content-addressed unchanged layers is allowed but does not replace source/lock/image verification. Do not promise bit-identical frontend bytes across a changed public WebSocket origin; prove same source and intended config origin.

One install initializes real new databases/migrations/least-privilege roles and a new administrator through normal prompts, without copying/resetting another account. One `csv-init` registers the new namespace and atomically initializes/certifies all13 MDM families, then normal master serving. Do not manually fill UUIDs/source hashes/certificates, weaken admission or run migrations against an existing sealed database. One `csv-day` per date uses the normal CSV freeze/validation/execute_day/full-report preparation/selection/restart/serving-verification path. All three must end PUBLISHED. No split UptoBPR/UptoDBM/continuation runs, manual action resubmission or duplicate calculations.

After terminal proof, one planned restart of **only this new project's MTA and auth** verifies selected-run persistence and retained session:

```powershell
docker compose restart mta auth
docker compose ps
```

Then remain in the real browser through normal access expiry and verify refresh followed by read/export. No CAPTCHA bypass, credential reset or external email. Ordinary scoped access can use the normal admin UI to create one explicitly owned read-only fixture user and grant one retained product/location scope; that is account metadata, never a new business identity. Test both permitted and outside-scope requests. Delete nothing afterward.

## 5. Required proof and finite acceptance

| Gate, in order | Required proof / pass-fail |
| --- | --- |
| Source/build | Exact detached commit, clean tracked source, four images identifying that commit, source/native/dependency inventories; actual build commands and exits. No external test artifact in runtime/build prerequisite list. |
| Blank install | Six expected services, unique private resources, only8091 published, real normal login/navigation; actual applied migrations and least-privilege identity. Blank readiness/unavailable reports reported truthfully, zero business runs before onboarding. |
| Initialization | Exact pinned167 input populations and typed opening certification, all13 native MDM families complete/readable, no daily run, fresh namespace/IDs, actual permissions catalogue. Independent full persisted reconstruction equals the supplied opening; counts alone fail. |
| Each date, before its successor | Frozen original CSV manifest/typed capture; all validation/rejection diagnostics preserved; exactly one own successful run/attempt, committed run/output, reports READY and selected serving identity PUBLISHED. Full typed persisted output readback equals committed digest. Exact next-opening reconstruction equals that run's operational closing, including histories/orders/controls/duplicate ordinals; for9/10 verify actual predecessor8/9 plus digest in the new chain. No old run as predecessor or output seed. |
| Report assembly and storage | Actual normal full report roster and prepared publication/MDM generations; inspect row/value sources and SQL/access paths from retained source and actual phase/SQL timing, serialization payload size and transfer. Every report must bind the selected new run/date. No missing-data→empty200 substitution. Empty DBM can be valid but cannot count as a positive Apply/Sleep scenario. |
| Browser per date | Authenticated BPR, RRR, BTR standalone and both combined orientations, Planning category/grid/graph, existing Guided reports and MDM. Direct-entry/reload first, visible readable rows/headers after spinner completion, navigation/filter/pagination/sort/count behavior and actual CSV download. For each applicable report perform one unfiltered, one positive retained catalogue filter and one legitimate zero-result filter; compare complete ordered typed values/counts to its own prepared source, not row counts only. Preserve authorized NULL/text formatting and rejected/unavailable distinctions. No Apply/Sleep/business action is submitted in this historical three-date cycle. |
| End-to-end timing | Per date one first visit per report; on terminal date add one repeat visit per report and one filter/page interaction. Measure click→usable grid (including frontend transformation/rendering), first/last network bytes, API/SQL/serialization and export completion, not just backend response. Proposed review targets: first usable≤30s, repeat≤10s, filter/page≤5s; exports≤120s with exact matching data/count/columns and confirmed file arrival. A blank/empty screen or tiny scroll strip fails even if HTTP200. These are prospective targets, not claimed measurements. Record browser/machine/resource conditions and actual values. |
| Comparison qualification | Compare identical new selections/data/filter/resource conditions across cold/repeat requests. Retain earlier exact-source functional proofs where applicable. No new legacy run, no warm-vs-cold speed ratio, no comparison of large data to the eight-row8080 selection as scale parity. A fair resource/data-matched legacy speed comparison is unavailable in this cycle and must be labelled unavailable. |
| Terminal restart/auth | Selected10April run/output unchanged after one owned restart; normal session refresh after15min then report read/export works; scoped identity permitted/denied behavior. Preserve native ownership and runtime read-only limits. |
| Preservation/closure | Three successful own-chain dates only; original8080 components/data and all protected resources unchanged; fresh package/images/input/new receipts/DB/volumes/private secrets retained in place, exact capacity accounting, failures retained, and one controller review. Step6 runbook contains actual successful commands and limits only. |

Maximum producing invocations: **one build command (four app targets), one blank install, one initialization, three Full daily calls, one two-service restart**. Maximum CSV export interactions: two each for BPR/RRR/BTR per date (unfiltered and positive-filter,18 total); one each for the remaining report families on the terminal date only. Zero-result checks are reads. Browser/report enumeration is the finite existing navigation roster from the clone, not a new report programme. Record exact requests/route inventory before execution; an unexpectedly unsupported route is a failure to resolve within scope, not permission to add features.

Independent complete typed readback/next-opening evidence uses read-only repository APIs against this new database and compressed external evidence. There is no generic all-purpose fresh-install management command named `verify_offline_terminal` for this pack: that command is bound to older registered offline scenarios. Likewise `verify_application_reads` has hardcoded graph identities and is a wiring observer, not a complete generic parity oracle. Do not call either as blanket acceptance. Before execution, prepare a small reviewed read-only observer binding actual new run IDs and native `read_daily`/opening reconstruction APIs (one complete readback plus one exact next-opening reconstruction per date; six checks total), with no writes or copied test registries. Run these checks sequentially through the owned daily-image service under its8GiB profile, with only this project's MTA stopped as needed; never overlap two8GiB processes. Its source and invocation must be in the evidence package; application imports/builds cannot depend on it. This is the second explicit proof-preparation prerequisite.

## 6. Stop, preserve and decision boundary

Stop at the first input/identity/ownership/schema/native failure, wrong predecessor, full-value mismatch, unavailable required report, unreadable browser view, missing/corrupt download, timeout, OOM, disk/RAM breach, observer staleness or protected-service change. Preserve the successful prefix, failing attempt, all original files and compressed diagnostics; stop only owned active work. Do not reset/delete volumes, erase an attempt, reinitialize/reseal, replay an accepted date, increase memory, extend clocks, repair a legacy flaw, hide incomparable columns or change calculations/SQL/frontend/MTO. A failed calculation is not automatically retried. A committed preparation/serving failure may be diagnosed, but even non-producing `-Resume` requires an explicitly recorded bounded recovery decision; it is not an extra producing allowance.

Before resource creation, controller review and the direct human execution decision must cover this exact source/data recipe, the two fixture-only preparation prerequisites, one8091 exception, concrete resource/storage/time limits and the fresh fit gate. Current release remains read-only inspection plus planning documents. If accepted, implement/review only the fixture producer, deployment configuration and read-only observer first; seal their hashes and actual commands before building. A needed application/business-contract change returns for a concrete revised proposal. No silent implementation, broader performance work or permanent cutover follows from this plan.
