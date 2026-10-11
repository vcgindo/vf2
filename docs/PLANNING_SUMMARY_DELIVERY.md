# Planning summary delivery evidence

11 October 2026. Status is maintained only in `docs/MIGRATION.md`.
Contract: `PLANNING_SUMMARY_PREPARATION_AND_REUSE_PLAN.md`.
External evidence: `D:/freshvcf-build/evidence/planning-summary-20261011-001`.

## Exact metric map

Contributions preserve the native occurrence bag before live permission weights.
Raw authorization equality remains case/space sensitive; NULL keys cannot match.
Only daily GIT custom uses the existing normalized equality.

| Metric | Native grain and eligibility | Product / location owner |
|---|---|---|
| GIT parent | Admitted GIT rows with `grid_eligible`, joined to the exact rationed/standard master ordinals | Master SKUCode / WhCode |
| GIT child | Same occurrence join | Master SKUCode / ParentWhCode |
| GIT custom | Fixture: existing empty transit contract. Daily: transporter × transit join using native normalized SKU/location equality | Transporter SKUCode / WhCode |
| Expedite parent | Child dispatch occurrences with all six required ordinals and native red/black pipeline colour | Expedite SKUCode / WhCode |
| Expedite child | Same occurrence join | Expedite SKUCode / ParentWhCode |
| Expedite custom | RationedQty > 0 and native red/black pipeline colour | Expedite SKUCode / ParentWhCode |
| Excess review | Admitted grid occurrences joined to their exact fact ordinal | Excess SKUCode / WhCode |
| Excess custom | Selected business-date facts | Excess SKUCode / WhCode |
| Fulfillment review | Admitted grid occurrences joined to their exact fact ordinal | Fulfillment SKUCode / WhCode |
| Fulfillment custom | All selected-run summary fact occurrences | Fulfillment SKUCode / WhCode |

No DISTINCT is introduced. Scope multiplicities multiply occurrence counts.
Bigint permission-product overflow and the five native int32 count limits remain
errors. Responses retain the four original category objects and ten string counts.

## Generation and read contract

Three additive typed models hold attempts, receipts and contributions. Migrations
0114/0115 descend from the actual serving 0112 branch; paused MDM migrations are
not applied. Summary rows are run-owned and immutable after sealing. A failed
transaction leaves a FAILED attempt and no partial receipt/contribution rows.
Same-source preparation reuses the completed receipt.

Identity binds run, business date, source, reporting generation, upstream Planning
projection receipts, recipe, current actor, permissions and resolved scope weights.
Daily identity also binds the base publication seal and transit image metadata.
Unsupported filters, unavailable sources and mismatches remain explicit failures.
The prepared endpoint never calls the underlying detailed count readers.

The frontend validates current identity before using its TanStack Query entry.
It retains only a successful response, clones data for consumers, detects account
changes during a read and guards late responses. Counts and date come from the
same summary. The original overview remains named for explicit feature rollback.

## Completed preparation proof

Selected fixture: `bfd75b4b-a9df-4a08-82d3-852e3324b623`, 7 April 2026.
Source: `4cbef69cbe8d75d64e5e9cdfc5b023d31770c318214c01c1d29912b6509a3f73`.
Original receipt: `cc5efc9b-fa7e-4906-b6cd-9048032b0c18`.
Original recipe: `afe1dbce5fa4b3472c1484f2a9a3936937d2aa3d430b020f84e14394b123a470`.
Corrected receipt: `5dca1e36-82b8-42b3-9a66-744505ed78cd`.
Corrected recipe: `189dd5148e1c9b4e13eb33a285ae666823925d4bead69e583d670745bf01ba9d`.
Rows digest: `8ec4a1a67aeffdf9cf8b745d6a3dfac18a4f707510420562bd723ea53df556f6`.

50,061 contribution rows; 19,398,656 bytes measured table storage; preparation
10.985 seconds. All ten fields exactly match original selectors for broad,
restricted, denied and overlapping assigned scopes (`fixture-proof.json`).
Injected interruption rolled back all generation rows; retry reused the receipt.
Native PostgreSQL boundary cases prove NULL denial, raw/normalized equality,
duplicate weights, parent ownership, sealed mutation rejection and overflow
(`boundary-proof.json`). Eight Python contract tests and four frontend reuse
tests pass. A ninth Python test proves the call-local binding optimization retains
wrong-run/source rejection, immutable guards and the default reader path.
The four existing Planning page tests also pass with the summary-date
header in their response mock. Their pre-existing async/network console warnings
remain in the retained log; this is not a claim that every page dependency was
integrated by that unit harness.

Django check and makemigrations check pass. Actual forward plan contains only
0114/0115. Both migrations were executed against a fresh owned PostgreSQL schema
with their historical CalculationRun FK model, and their guards verified. This
is proof of these migrations, not a replay of every historical migration.
The initial temporary-alias failure and corrected proof are retained separately.

## Daily integration limit

`prepare_daily_ui` calls the new reporting-generation coordinator, which prepares
the existing publication and then the separately sealed Planning summary. It does
not change the old publication's required-layer roster, recipe or seal, or select
a new serving owner. Unit sequencing and failure propagation pass.

The accepted June 6/7 owners belonged to `fresh_complete` in the former owned
`freshvcf-complete001` facility. Neither that container nor its volume is currently
available. Historical receipts are retained, but **actual accepted-daily runtime
preparation is unproved**. The coordinator mock is not runtime acceptance. No
restore, new calculation, source substitution or serving switch was performed.

## API baseline and remaining measurement

Three private serving HTTP observations per actor, without warmup or retries:
broad 3.5291 / 3.3094 / 4.8326 seconds; restricted 2.7841 / 4.0226 / 5.1350 seconds.
Complete bodies are retained compressed. These boundaries exclude browser and
public gateway overhead. Baseline SQL decomposition was not captured, so it must
not be inferred from whole-request timing.

| Actor | Corrected after samples (seconds) | Before median | After median | Reduction |
|---|---|---:|---:|---:|
| Broad | 2.2550 / 1.4553 / 1.1703 | 3.5291 | 1.4553 | 58.76% |
| Restricted | 1.1154 / 1.3656 / 1.3192 | 4.0226 | 1.3192 | 67.21% |

All six complete response bodies equal their original baseline bodies byte for
byte; source/run/date bindings match. No warmup, flush or favorable retry was
used. Fixed service resource ceilings were retained; this is an observed local
summary comparison, not a controlled legacy capacity benchmark.

The first deployed attempt is retained separately: broad median2.7852s failed
the50% target; restricted1.9696s passed. Its profile found six repeated fixture
bindings in one summary call. The correction passes that call's validated binding
to its four direct dependencies while retaining their receipt/recipe/guard checks
and the original path for other callers. No cross-request cache was introduced.
The new recipe appends an identical generation in15.775s; the original receipt,
rows and failure remain. Each generation has50,061 rows, so retained storage now
includes both generations.

Separate SQL diagnostics (not extra API timing samples) fell from84 to56 queries.
Measured SQL execution sums were0.3201s broad and0.1337s restricted; aggregate
EXPLAIN execution was104.997ms and32.151ms. The entire authenticated HTTP request
also includes existing admission, scope materialization and serialization.
Original profiling and all first/corrected samples are retained.

The first browser observation exposed a stripped custom date header: cards
remained blank. Its screenshot and error are retained. The frontend correction
uses the business date already carried in the validated identity response and
passes it to the category selector, removing that selector's independent date
read. The corrected build is deployed and both finite browser journeys pass.

## Browser acceptance and qualified outcome

| Actor | GIT parent/child | Expedite parent/child | Excess | Fulfillment | Date |
|---|---:|---:|---:|---:|---|
| Broad | 1627 / 1627 | 1030 / 1030 | 9871 | 12720 | 07 Apr 2026 |
| Restricted | 203 / 0 | 78 / 0 | 360 | 1063 | 07 Apr 2026 |

Each account entered Planning, entered GIT From Parent and returned. The grid
loaded and all four cards/date matched before and after. For each journey,
frontend access logs prove exactly one GetPlanningDataCount request (entry),
two successful ReportReadIdentity requests (entry and return), and **zero repeat
summary-count requests on return**. Current access/generation validation remains.
`browser-proof.json`, both DOMs/screenshots and original access logs retain proof.

Cards/date were first observed ready within7.148s broad and5.287s restricted from
navigation. Restricted return was observed ready in3.292s. Broad cards appeared
within0.686s, but the date awaited identity validation; the next observation was
10.330s after the click. These are observation bounds including tool/sampling
overhead, not precise browser render timings. Server identity reads on return
took1.401s broad and2.262s restricted. No before-browser timing was collected;
do not claim a measured browser speedup or instantaneous return.

Nine backend contract tests and ten affected frontend tests pass. The selector's
old independent-date mock failure is preserved; its corrected test supplies the
summary date. The final production build passed with existing lint warnings.
No extra API timing, baseline campaign, source population or business day was run
during finalization.

This is a **qualified selected-fixture delivery**, not full S1–S4 acceptance or
production daily completion. The accepted-daily runtime exit remains UNPROVED
for the facility absence stated above. No other source or serving approval is
implied. Finite delivery stops after the cohesive commit/push.

## Packaging boundary

This is an incremental overlay over backend image
`sha256:f94d47c65a0f68bc3a4614e4821d68c35c42a15b28d42c477c4ab0e57949862e`
and frontend image
`sha256:f2bb743897014823f755eafd8453ef592b67e85469cf02531cd46226ef69c3e8`.
The serving foundation contains pre-existing Guided work outside this task's
commit boundary, including migration 0112. The task is not a certification of
a standalone clean-HEAD reconstruction of that separate delivery. Backend
models/views overlay uses actual serving source plus only the Planning changes.
Other files are explicitly enumerated in the external overlay. Whole-checkout
Docker builds and `git add -A` are excluded.

The private worker environment is external evidence only and must never be
copied into Git, public receipts or command output. Source and build manifests
must not contain credentials.

## Deployed overlay and rollback

Backend: `freshvcf-preview-mta:planning-summary-candidate-20261011-004`, image
`sha256:9681fd04d68f73705fcaae88f44af791c37f3b29eb1b163afe0847fe71393269`.
Frontend: `freshvcf-preview-frontend:planning-summary-20261011-002`, image
`sha256:dd3cc3884907920bebc2f054a97098ccaa9c9965d70bfa0686fd2466e02faf04`.
Frontend asset-manifest SHA256:
`90c8a802f2b22452abb2ad01b8c1d652751a512c5619a4aeeaefef5f2003c9a4`.
Admission digest remains
`5c90ae58f6478f7b1805f534f95fbe0de241a5280c4422ec70f28467221bf3e7`.

Backend overlay files: Planning summary module/models/schema; migrations0114/0115;
prepare/migrate Planning commands; daily_publication and prepare_daily_ui;
four direct Planning admission modules; the two narrow models/views integrations.
Frontend implementation files: Planning service api/index, usePlanning and page
index, and its SelectCategory component. Existing nginx/auth/MTO configuration
and other frontend modules are inherited unchanged. `delivery-manifest.json`
enumerates every backend file hash and the safe runtime identities/mounts/limits.
`candidate-source-hashes.json` and `final-source-hashes.json` retain build inputs.

Only the two task-owned containers were recreated. Protected runtime identities,
mounts and ceilings were verified unchanged. The backend's only environment
addition is VF_PLANNING_SUMMARY=1. BPR's5000 setting and selected fixture remain.
The original-directory baseline rebuilt to the exact live asset manifest before
the Planning edits were built. Separate-directory build differences, the baseline
test-harness failure, initial API target failure and browser date failure remain.

Rollback preflight PASS (`rollback-preflight.json`): original images, environment
apart from explicitly disabling the new feature, mounts and resource limits match.
Rollback was **not executed** after successful delivery. Additive generations and
failure evidence are retained. To perform an ordered rollback:

1. Run `D:/freshvcf-build/venv/Scripts/python.exe D:/freshvcf-build/evidence/planning-summary-20261011-001/deploy.py rollback`.
2. Wait for the MTA log to report publication admission and listening; this
   deployment observed roughly three to four minutes for retained startup checks.
3. Confirm `/readyz` returns ready=true and reload the browser. The original
   frontend/count path is restored; do not reverse migrations or delete receipts.

For a future authorized preparation on this foundation, the commands are
`manage.py migrate_planning_summary --plan`, `manage.py migrate_planning_summary`,
then `manage.py prepare_planning_summary --run-id <selected-run-id>` and its
`--verify-only` variant. Fixture execution was verified in this delivery.
`manage.py prepare_daily_ui --run-id <accepted-run-id> --output-digest <digest>`
includes the new step, but actual daily execution of it remains UNPROVED. These
are command contracts, not authority to restore sources or run new business days.
