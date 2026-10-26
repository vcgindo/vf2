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

## Native report configuration component

`mta/application/runtime_report_configuration.py` validates the native 16-field
RuntimeReports roster and separate four-field DownloadableUIReportSettings,
preserving NULLs, spelling, string widths, scalar types and supplied rows. It
separates definition identity from LastGeneratedFileName state. The shared plan
selects Active rows by native CI/space-padded placement matching and Id order;
both split stage sequences equal Full without replaying an earlier placement.

Eight focused tests pass. They use the exact retained eight-row configuration
capture, with its SHA checked, plus explicit local witnesses for otherwise empty
placements. Tests cover all five scopes, independent UI download settings,
source/reference tampering, duplicate keys/IDs/names, invalid native types/NULLs,
UTF-16 widths, missing-versus-explicit-empty tables and last-file identity.
The existing empty TEST validator rejects the new production configuration.

This is a pure configuration/placement component. No runtime entry accepts it
yet; initialization and TEST guards are unchanged. It does not execute SQL,
authorize an empty production roster, qualify any files/templates/destinations,
adopt the benchmark configuration or issue a READY result. Production binding,
enabled report execution and native/UI qualification remain required.

## Retained RuntimeReports data projections

All eight captured SQL queries now have finite pure data projections and an
explicit logical source dispatch contract in `runtime_report_projection`.
Query SHA256 selects the implementation; a deployment Id remains execution
order rather than business identity. Wrong BaseDB, missing/extra logical source
tables and unknown queries are denied. BTR attributes are not substituted with
similarly named BPR or Importer attributes. Date-dependent queries use the
specified LastBatchRunTbl scalar population; no host/run-date fallback exists.

The three BOR bandwise variants produce 31 cells, the two efficiency reports
24, Spike 12, allocation history 34 and Total Requirement 107. Complete local
expected tuples and duplicate/NULL/filter/date witnesses pass. The efficiency
Pick join supplies the four unqualified TOR columns. Allocation-history
AdvAllocDone comes from the requirement join; its latest remark is selected
per pair before matching supplier. Distinguishable latest-date ties deny
explicitly; no artificial native tie-break is introduced.

Metadata lookups are grouped once. Latest remark bags are prepared once per
pair and projected outcomes cached per pair/supplier for one query lifetime;
a 101-remark/60-output witness proves one preparation and one resolution without
deduplicating output. The unordered Total Requirement projection yields rows
incrementally from RecordRows; the 10,001-row witness confirms consuming one
output does not enumerate all fact rows. This is an operation-count/lifetime
proof, not a scale or latency benchmark.

All 38 focused configuration/projection tests pass (0.086 seconds locally).
Independent bounded static review compared all eight full captured SQL queries
and relevant canonical DDL with the implementations and found no actionable
projection mismatch. The review and tests are limited to pure typed sources.
Persisted wire conversion, accepted phase-source binding, enabled placement
execution, native query equivalence, SQLCMD headers/types/encoding, physical
files, setup/upgrade and UI remain unqualified. Current serving code and
accepted state were not changed or replayed.

## Persisted source decoder and Total Requirement correction

The subsequent real-source audit found an error missed by the pure fixtures and
static review at 057e38f5: the three unqualified ReqTopOfRed/Yellow/Green columns
belong to SupplierDispatchReq B. They are absent from vf_RationedReqReport A.
The projection now reads B and preserves NULL for a missing left-join supplier.
The fixture no longer invents A columns; a native-schema regression check binds
both source rosters. This was an undeployed modern projection defect, not a
legacy exception or accepted-run change. The earlier review is superseded for
this specific mapping.

runtime_report_sources.image_rows now decodes requested fields from the existing
checksum/ordinal-verified relational reader using declared physical SQL types.
It preserves duplicate ordinals, exact decimals, dates, literal \N text and NULLs;
unknown/missing columns, wrong tables and damaged images fail even for empty
populations. It retains RecordRows iteration rather than copying a large image.
The caller still owns accepted-phase authentication and source selection.

All 47 focused configuration/projection/decoder tests pass. Read-only native
proof runtime-report-source-proof-01.json compares all typed cells for 71 actual
images / 351 rows with direct PostgreSQL reads. Spike's complete 2 x 12 cells
also match. runtime-report-empty-source-proof-01.json checks four actual empty
images and rejects an unknown field. runtime-report-total-proof-02.json compares
the corrected complete 8 x 107 typed occurrence bag with the captured SELECT
translated only for PostgreSQL syntax over the same persisted sources: one
matched supplier and seven NULL supplier-band rows. Complete typed bag digest:
f312cff293ce13b81d05feb642b6122425b70b71bfb85864909b79e597dbf17d.

All proofs used the retained a2661554 run under runtime-role READ ONLY, and the
six-model fingerprint stayed f2f1d4b1852f238832402eff89c0a53bf5d9a424c1fa814a7750f483e43d9753.
Evidence is under the existing g2/uptodbm-private-20261025/three-day-positive-test
root. Earlier proof snapshots remain unchanged; snapshot02 pins the correction.
The bounded Total proof explicitly supplies the captured Importer attributes;
it does not establish generic Importer-to-BPR copy/hook lineage. These are typed
source/projection proofs, not SQL Server file/encoding, placement execution,
production enablement, setup/upgrade, Full/split or UI acceptance. No serving
code, accepted effect, frontend design or MTO contract changed.

## Runtime report successful file lifecycle

runtime_report_files reuses operational_io and the caller's existing verified
archive writer. The finite branch supports the retained CSV definitions with
explicit macro bindings into an owned root. It preserves the literal
Spiker_Order_Dump filename, current/previous output cleanup, optional previous
destination deletion, current replacement and the exact single CSV ZIP member.
It returns LastGeneratedFileName for the phase owner's transaction, without
changing the supplied configuration. Archive contents are independently read
back; a writer's success receipt cannot substitute different bytes. Invalid
paths/contracts fail before cleanup; archive failure does not replace the prior
download and cannot return a successful receipt. No phase READY claim is made.

Seven focused tests and nine existing operational-file tests pass. The ZIP test
writer verifies the protocol only; this is not new native 7-Zip qualification.
The supported previous-filename boundary is explicit: all eight retained rows
have nonempty previous names. Native NULL/blank FOR/F placeholder behavior for
fresh initialization remains unqualified and is denied, not guessed. Excel,
unknown queries and unsupported macro/path expressions remain denied. The
payload must already be formatter-qualified bytes; encoding is not implemented
or certified by this file lifecycle component.

runtime-report-native-file-audit-01.json (SHA256
501885d3f917aaa40428bfc2110dc48ebc2934add4cf06623ae66b99c4f25ea3)
records read-only reconciliation of the retained benchmark configuration and
all eight native output/download pairs. Each pair has identical full bytes;
all literal headers match exactly, and each compressed file has the expected
single member. Both canonical wrapper/script hashes match. These older files
are format/provenance evidence, not outputs of the current retained TEST run.
No SQL Server service was started, files rewritten or serving resources changed.

Phase-owned file publication, formatter data-byte qualification, fresh setup,
compatible upgrade and final native Full/split integration remain outstanding.

## Runtime serializer, streaming file write and fresh NULL filename

runtime_report_encoding binds the eight retained queries to their native SELECT
types and parses literal HeaderList expressions without executing SQL. It reuses
the existing scalar encoder and streams CP1252/CRLF lines, preserving NULL,
decimal scale, stored spaces and unescaped commas/quotes/newlines. Header and
data remain separate resultsets. Unsupported query/configuration/encoding/type
values deny; nvarchar(max) values above 256 characters remain unqualified rather
than receiving an invented display-truncation rule.

operational_io.write_chunks and runtime_report_files.publish now consume those
chunks incrementally. A late bad cell leaves unaccepted staging and cannot
replace the prior download or return a successful file receipt. Existing byte
payload callers retain their behavior. Focused encoder/file/operational tests
pass, including lazy row consumption and late failure. No phase owner or
production configuration is enabled by these utilities.

Read-only native scalar reuse proof runtime-report-scalar-reuse-01.json
(SHA256 6e42c470aabee864edc52b081cba3893a2648d75aca8f292b344b5ba39a3e5c0)
checks the retained SQLCMD probe bytes for spaces, NULL, integer, decimal, date,
datetime, bit, empty text and unescaped commas/newlines. This checks actual
retained output rather than treating general -W documentation as permission to
trim stored values. The source receipt is sqlcmd-format-a003/native-receipt.json,
SHA256 6d32b50ad9a61e30fad546d16cfb6604073081e5e1bcadb40bd48cdcccabeda2.

Full retained-file roundtrip01 (SHA256
b2aa0ff5752845686df242d664d8597acd94567bc3b7a2b706fc00d06f170c7b)
has five exact-byte successes: both efficiency reports, Spike, allocation history
and Total Requirement. Together these cover 3,130,270 rows. This is serialized
value reconstruction, not independent producer parity: text NULL versus SQL
NULL cannot be recovered from those bytes alone. Its three BOR variants FAIL
because the proof's simple delimiter parser cannot split SQL-quoted descriptions.
Roundtrip02 (SHA256
a4738ea4993b9ae1207b19ff8a1918f233a3bda3eba9bf4f1dcc69e09b1f0fa5)
corrects that lexical wrapper boundary but still FAILS on native embedded quotes.
Both failures remain intact. No encoder/output was changed to make the proof
pass. Complete typed-source/native comparison for those three files remains
unqualified; another guessed parser is not a substitute. This does not establish
that legacy output or the modern encoder is defective.

Fresh-setup NULL previous-filename handling is now evidenced, superseding the
earlier component restriction for NULL only. The read-only native Windows
runtime-report-null-lastname-probe-01.cmd proves that the canonical selector's
ISNULL(...,' ') field survives FOR/F as one space; previous filenames are
" .csv" and " .zip". The implementation preserves exactly those cleanup paths,
with both plain/ZIP tests. A non-NULL empty previous filename remains a separate
unsupported token-shift case. No SQL service or protected resources were used.

All phase/source/publication, setup integration, native Full/split and existing
latency/scale/G3 qualifications remain governed by the sole tracker.

## Existing receipt-recorder compatibility and placement owner decision

Controller/reviewer integration audit found that compressed runtime files returned
`csv`, while the existing recursive operational recorder skips only `source_csv`
for deliberately removed inputs. The runtime file adapter now uses that existing
transient-source convention. A direct adapter-to-recorder test creates actual
plain/ZIP files, reads complete archive members, and verifies that exactly the
two surviving output/download files reach record_file. The database writer is
patched at that boundary; this is recorder compatibility, not durable receipt
or transaction acceptance. No deployed failure or accepted receipt was changed.
The 17 affected runtime file/encoder/recorder tests pass.

The bounded ownership review confirms that OperationalAttempt.start_attempt and
verification require a SUCCEEDED Full run/output digest and its operational
lease; operational_effects.operation requires autocommit. Those owners cannot
be nested in atomic scoped acceptance. ScopePickFiles is a separate exact
four-file contract whose complete module source is part of its accepted recipe.
Neither owner will be silently widened for RuntimeReports.

The selected integration is a dedicated immutable placement publication receipt,
using the existing source/projection/encoding/file utilities and current scoped
claim/fence mechanisms. It must bind an accepted source generation, action cut,
captured report configuration, recipe, exclusive candidate directory and only
surviving files/member hashes. Registration will recheck that owner in a short
transaction. Failed candidates remain unreferenced; retry verifies a completed
receipt or uses a new candidate, without replaying accepted effects. Generated
LastGeneratedFileName belongs to the receipt, not the frozen definition.
This is an implementation decision; durable registration/recovery is not yet
implemented or verified.

Full currently calculates prepare_day -> BPR -> DBM -> BTR before finish_run.
It lacks the intermediate durable placement barriers required for enabled early
reports. Terminal backfilling would not satisfy the contract. Production Full
activation remains unavailable until the subsequent generic orchestration uses
the accepted phase owners and gates continuation on required report readiness.
This dependency does not authorize a parallel Full engine or new fixture campaign.

Source-lineage investigation located the literal canonical copies in
Scripts/BPR/01. ImportData.sql, SHA256
c248baeedda13d74a71a499c8b59b7ec46f05f11db00938de59a746bce94ce93:
SiteDescriptionTbl, SKUDescriptionTbl, SkuAttributeData, SkuLocAttributeData and
LocationAttributeData are copied from Importer. The modern BPR acceptance writes
four MDM master partitions through phase_copy_batches; pair attributes remain
represented in the immutable phase's Importer image. That explains why matching
field names alone cannot establish BPR ownership. PostBPRProcessing runs before
PostBPR RuntimeReports and may change those values; exact copy/hook lineage must
be bound before a generic logical source alias is accepted. No alias, historical
phase recipe, initialization guard or production report configuration was changed.


## Authenticated physical placement sources

runtime_report_phase_sources binds an accepted PRE_BPR/BPR/DBM phase to its
run, snapshot, captured input/profile/request, business date and producer action
revision. It reuses the existing accepted-phase authenticator and full typed
image checksum reader. Exact manifest nodes support dictionary keys and ordered
report-list indices; negative, boolean, floating and string indices deny.
Physical ancestor reuse requires the same image suffix and complete metadata in
an authenticated ancestor. Even an empty source must name its actual table.
This does not establish logical Importer-to-BPR copy/hook equivalence or enable
nonempty RuntimeReports.

The first actual read-only proof exposed missing traversal of ordered DBM report
lists. Its source snapshot and failure receipt remain retained. The corrected
proof runtime-report-phase-source-proof-02.json (SHA256 f8046d973481799f856b40ae86f7a9f3d520a44090320ca9804018b36bc96184) passes
45 images / 217 rows across PRE_BPR, BPR and DBM, 12 changed-owner denials and
three actual empty-source wrong-table denials. The six-model fingerprint remains
f2f1d4b1852f238832402eff89c0a53bf5d9a424c1fa814a7750f483e43d9753.
Fifteen affected local source tests pass. No existing codec/recipe/schema,
accepted phase, serving service, frontend or MTO change. Publication and logical
copy/hook contracts remain open within the active report integration item.


## Logical PostBPR copies and explicit hook disposition

runtime_report_bpr_sources now supplies the two qualified PostBPR query source
rosters (Spike and Total Requirement) from an authenticated BPR cut. Total reads
the late accepted vf_RationedReqReport image, consistent with the existing scoped
reader. SupplierDispatchReq retains its complete/BPR physical identity.

The four BPR master-copy identities are recomputed incrementally using the same
model fields and typed_field conversion as phase_copy_batches, then compared to
the full accepted partition roster: owner, model, fields, counts and storage
digests. No mutable current partition is read. Logical BPR attribute references
retain their Importer physical image and pinned canonical ImportData SQL identity.
SkuLocAttributeData uses an explicit reconstructed SELECT-star copy witness;
it does not claim a persisted BPR pair partition that the original producer did
not write. Its complete field roster, NULLs, duplicate ordinals and order survive.

There is no generic production site-hook executor. A new pure hook configuration
validator represents only an explicit provenance-backed declared no-op. The
source adapter requires it in the frozen scope request and matches the captured
profile/site. Existing TEST no-ops use the original UptoDBM disposition validator
and TEST database guard; they are not production defaults. Missing/active hooks,
wrong sites and changed capture identities deny. Existing entry factories still
do not admit the new production declaration field; generic admission and hook
applicability remain future integration work. This adapter does not adopt report
definitions or mark files/placements ready.

Actual read-only runtime-report-bpr-source-proof-01.json (SHA256 342dbda739c643e099c6defafe5ec8926a9506e14afb3aaf6f5d47774d054c16)
passes Spike 2x12 and Total 8x107 complete typed cells against their previously
pinned direct-PG query proofs. It rejects all four changed copy identities and
two changed hook-capture identities. The six-model fingerprint remains f2f1d4b1.
The original captured TEST no-op is the proof's only hook authority; the retained
nonempty query fixture is not installed into this run's empty RuntimeReports.
The 34 affected local tests pass. Independent source-boundary review found no
actionable defect, explicitly excluding production admission and publication.
No existing phase codec/recipe, schema, accepted data, frontend or MTO changes.


## Private ordered report candidates and filename-state separation

runtime_report_candidates connects the existing query projection, streaming
encoder and file lifecycle in an exclusive UUID directory. Every selected report
runs in native Id order. Only final surviving output/download files are retained
in its manifest; complete file hashes and ZIP member hashes are reread before
return. A reused candidate identity fails, partial failures retain an unaccepted
orphan, and verification of an existing complete candidate performs no replay.
The captured configuration and explicit LastGeneratedFileName state are separate:
missing/mismatched filename state denies, and before/after state is recorded
without changing the captured definition.

Cleanup becomes an ordered catalogue change. Old accepted directories are never
modified or copied wholesale. Unchanged visible files retain their earlier
candidate reference; logical deletion changes visibility only. Exact same-path
writes follow Id order. Different spellings of case-equivalent paths are denied
both within a candidate and against its prior catalogue; this avoids silently
changing Windows path semantics on Linux. The latter cross-candidate check was
an independent review finding and now has removal/write collision regressions.

Native Linux proof runtime-report-candidate-proof-02.json (SHA256 540aa6d62318dfd741d97c76ab26f81e4d3ce9e7669a7ab3d6288433e7b94e19)
uses the protected accepted BPR source adapter to create four private files for
Spike/Total, verifies full files/member content and explicit generated-name
state, rejects reuse, injects an archive failure after CSV creation, and retries
in a new directory. The failed CSV remains without a candidate manifest; the
original complete candidate still verifies. Captured TEST RuntimeReports and
the six-model fingerprint f2f1d4b1 remain unchanged. ZIP_DEFLATED follows the
existing scoped InputData protocol; native 7-Zip archive-byte identity is not
claimed. These evidence candidates do not install the retained nonempty query
configuration into the protected run.

Final source readback runtime-report-candidate-final-readback-01.json (SHA256
2e5b7dd157803cb1ca153810afd797845cf61a0cad65507b4f794201469bb7aa) verifies both native candidates on Windows and checks the added
cross-candidate case guard. The 26 affected local tests pass, covering late
failure, exact overwrite, old visibility, missing filename state and tampering.
An initial unit fixture incorrectly supplied text for native integer OrderKey
and PartId; only that fixture was corrected, with production encoding unchanged.

This completes private materialization/readback only. Durable database receipts,
worker fencing, atomic registration, captured configuration admission and retry
across the registration boundary remain required. No schema, accepted calculation,
frontend, MTO, serving selection or production readiness changed.
