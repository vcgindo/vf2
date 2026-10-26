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
