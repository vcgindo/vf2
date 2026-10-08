# Cohort4 qualified operational packaging

D1–D4 deliver the existing daily-command contract, pinned CLI package, private
configuration template and executable numbered operator audit. Status belongs
only to `MIGRATION.md`. Start with `COHORT4_OPERATOR_RUNBOOK.md` steps1–5 and stop.
This delivery does not establish unrestricted production readiness or release a
new business date, benchmark, serving activation or cutover.

## Package and proof

| Identity | Retained value |
|---|---|
| Local tag | `freshvcf-cohort4:operational-004` |
| Immutable image | `sha256:0a8ca22f471386ec6ce8dd3e59cd3fb5b1f5e56cfc525e32a6f30e3a2adb5dff` |
| Application commit | `44c350b0fc201f832393ca02664e3b17b07143fd` |
| Source audit | 848 files; newline-normalized source where declared, two Cohort3 JSON manifests byte-exact; source manifest SHA256 `97669e2c54dfe26644566b046e550d30ace775932102e8e25c359bab17cee3e7` |
| Image archive | `D:/freshvcf-build/evidence/cohort4-20261009-001/runtime-image.tar`; SHA256 `a5ab31f60a88631a0267579d66183f1884fd243965a68f3074dc595509bab4d5` |
| Base/tool donor | Exact Cohort3 closure-003 and Cohort2 final001 images in `packaging/cohort4/runtime-lock.json` |
| Required schema | Through0097; current owned database has no pending migrations; reuse Cohort3 actual upgrade/fresh-database proof |
| Configuration | `packaging/cohort4/compose.template.yaml`, `private.env.example`; actual credentials remain external |
| Evidence | `COHORT4_EVIDENCE_INDEX.json`; root `D:/freshvcf-build/evidence/cohort4-20261009-001` |

The package retains Django5.2.4, DRF3.14.0, simplejwt5.2.2, psycopg3.3.6,
psycopg2-binary2.9.10, pycryptodome3.23.0 and requests2.32.3. Both PostgreSQL
tools report16.15. The immutable bases pin the remaining environment; no
dependency upgrade or online installation occurred. Rebuilding requires those
local images and the retained Git commit; bit-for-bit BuildKit metadata identity
across rebuilds is not claimed. The exported image provides the exact artifact.

The only runtime packaging correction copies libldap2.5, liblber2.5 and libsasl2
from the pinned Cohort2 image: pg_dump originally could not start without them.
Application code, calculations, schemas, inputs, actions and admission are
unchanged. The entrypoint is `python -m django`, with no serving process or port.

All11 command checks passed their expected outcomes: Django check, migration
drift/plan, six command-help checks, June7 operational readback and expected
strict-selection rejection. Actual imports and pg_dump/pg_restore startup passed.
No new backup/restore or consumer campaign ran. The audit template has a read-only
filesystem/mounts,4GiB/twoCPU limits, restart=no, actions off and blank selection
and qualified-policy settings. All transient audit containers exited.

Failed builds/audits remain indexed: a001 incorrectly requested gunicorn metadata
for a CLI image; a002 exposed the missing pg_dump libraries; a003 exposed a Git
LF/Windows CRLF PowerShell source-audit mismatch. a004 fixed only those packaging
issues. A private-config harness initially omitted the explicit default DB port;
it failed before creating any container and was corrected to the existing5432
setting. None of these failures is calculation or parity evidence.

## Readiness and remaining release gates

The following is a disposition matrix, not another work queue. No row releases
additional work. Existing proofs are reused without rerunning their campaigns.

| Boundary | Disposition | Evidence and remaining requirement |
|---|---|---|
| Existing daily command chain and CLI packaging | **Complete within this cohort** | `COHORT4_COMMAND_CONTRACT.md`, package/source receipts,11 checks, executed numbered audit. Template is for retained read-only audits; new-day writable roots/bindings require a release. |
| Cohort1 own predecessor/actions and typed state | **Qualified** | Cohort1 closure evidence referenced in MIGRATION and Cohort2 two-date receipts; own persisted state and two actual Apply actions retained. No copied legacy state. |
| C1 active NMS; populated SOB/twoMOQ approval queues | **Missing implementation/proof outside supported domain** | Approved explicit empty queues only; inactive NMS retains native flag0. Implement and prove exact enabled workflows before expanding support. |
| C1 real sanitation/critical-file/upload-log inputs | **Missing deployment binding/proof** | Synthetic empty openings and C1/C6 declarations are not a real deployment workload. Supply exact owners/configuration, no inferred empties. |
| C2 client history/profile sources | **Qualified; expansion deferred** | Explicit empty initial history and opt-in FG/GulfOil sources; BOR/BOROA, separate RRR colour and GuidedExcess source/history boundaries retain their prior exclusions. No universal profile claim. |
| C3 operational files and ZIPs | **Qualified** | Cohort2 file/native/repair receipts: exact supported roster, four Pick CSV export-order exception and approved input/BOR ordering exceptions; mapped ZIP member/content repair qualification only. Arbitrary configured outputs need their own proof. |
| Pick calculation ties | **Qualified equivalence only where approved** | Existing bounded permissible canonical tied-row-order proof; distinct SKU differences are not exact parity. Untied behavior, formulas, capacity, NULLs and duplicates retain exact requirements. This is separate from CSV order. |
| C4 alerts | **Local disposition complete; external delivery unproved** | Fourteen local evaluations/date in Cohort2; no email sent. Later transport/recipient/attachment binding and delivery verification need explicit authorization. |
| C5 backups/restores | **Qualified owned logical restore** | Cohort2 full rows/sequences/schema proof, exact eleven CHECK-cast pairs, retained strict failures; SQL full/differential fixtures separately owned. No general deployment restore certification. |
| C6 completion/successor | **Qualified** | Native batch flag0 remains; enabled-writer successor check admits the accepted two-date domain only. No full-batch success claim. |
| General input and selection policy | **Decision plus implementation/proof required** | Registered synthetic MDM opening only. `check_daily_selection` strictly rejects parity{}; tested here. A later exact input/configuration release and general admission contract are required. Cohort3's two-owner policy cannot transfer. |
| Prepared/authenticated consumers | **Qualified two-owner acceptance** | Cohort3 indexed96-file proof:18 layers/date,81 HTTP observations/date, four Pick streams/date,32 full RRR comparisons, auth/scope/NULL/path/drift denials, restart and prior-valid preservation. Not a new arbitrary-run proof. |
| Order-fulfillment custom and combined GIT child grid | **Explicitly blocked by approved disposition** | Both original final consumer receipts remain FAILED with two503 responses: ambiguous legacy ranking and invalid legacy SQL207/8120. No positive acceptance or repair claimed. |
| Sleep in this two-date chain | **Missing proof for this scenario** | No designated target was suggested. Earlier separately owned real Apply/Sleep proof does not make this chain's Sleep exercised. Retain the limit until a separately approved finite exercise is required. |
| Whole application/direct-port MTO, deployment and cutover | **Deferred/unproved by this delivery** | Existing frontend/MTO unchanged. No serving3002–6 change; eventual3004 cutover still requires readiness and explicit coordination. |
| Independent full daily parity, scale/performance, arbitrary continuity | **Missing proof; held** | Small two-date correctness proofs do not establish full-day legacy parity or production capacity. Benchmark and stopped temporal run remain on hold. |
| Repository-wide tests | **Not claimed passing** | Cohort3's25 focused tests passed; two pre-existing history Cursor.fetchone test-double errors remain disclosed. No business code changed here; do not treat packaging checks as a full-suite pass. |

Only two consolidated release decisions remain relevant before proposing a new
daily run: (1) exact external input/configuration/MDM/predecessor/actions, enabled
domain, exclusive resources and finite acceptance scope; (2) independent parity
or a separately approved general operational admission contract. Neither is
implicitly granted by this delivery. Other expansion rows stay held, rather than
becoming an automatic discovery or implementation programme.

## Retained evidence references

`COHORT2_HANDOFF.md` identifies its128-file closure proof
`01278f44616e40abe73c74d6c896588769ee954df5efaa189ca1cdf273ad8ae0`.
`COHORT3_HANDOFF.md` and `COHORT3_EVIDENCE_INDEX.json` identify its96 files and
closure proof `3960b52efc5d6c842242140c98ed4a070b1a2d1a5301a758c884f7ad28095fbe`.
Those accepted owners, seals, original failures and qualifications are unchanged.
The packaging commit contains no new business engine or permission change.
