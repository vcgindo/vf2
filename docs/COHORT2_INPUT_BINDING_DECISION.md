# Cohort2 missing input bindings — one bounded decision

APPROVED: direct human reply call_5c8463bd82e544cf9b51d0e44efb0765,
“Approve all six bounded bindings”,8 October2026. This is a contract supplement,
not a status tracker. Concrete source/tool/resource pins still require proof. MIGRATION.md remains authoritative. It applies only to
the new Cohort2 owners reproducing the accepted10-pair June6–7 artifact
7e60ef1b3d73a36889b25a43995234ec5839a5bb646da5b782328189a1b2699d.
No new calculation/date, client fallback or change to accepted state is proposed.

## Proposed consolidated choices

1. **History openings and skipped RRR.** Declare initially empty BOR order-
   allocation history, RRR order-allocation history and current RRR_OrderAllocation
   in the new Cohort2 owner. June6 onward history uses only its own computed
   report rows and predecessor. Generic IsMTOEnvironment=0 still skips the RRR
   producer: retain the declared empty current RRR and execute its mandatory
   history append/retention exactly. Do not claim pre-June6 history coverage or
   populate RRR from the disabled MTO producer. Nonempty current RRR requires
   an explicit supplied owner, never an implicit empty default.

2. **Physical input files.** The generic BAT copies InputFolder verbatim but
   has no generic site filename/CSV parser. Declare these five owned reproduction
   files: MasterDataRaw.csv, DailyDataRaw.csv, SOBDataRaw.csv, MOQDataRaw1.csv and
   InTransitRaw.csv. Use unchanged retained raw facts:10 master/daily rows,
   3SOB and1MOQ1; shipment rows come from each exact day's shipment_input.
   Four input column rosters follow native Importer DDL physical order/types;
   transit follows the retained daily-transit-raw-v1 field order. Format is UTF-8
   without BOM, CRLF, RFC4180 quoting, one exact field-name header, ISO dates/
   timestamps, decimal scale preserved, and literal backslash-N for NULL.
   Empty text stays empty text; reject a text value equal to the NULL token.
   Verify full typed round-trip, including order and duplicates. This is an
   explicitly declared reproduction interface, not evidence of an absent native
   generic site import parser or its original file bytes.

3. **InputTableList.** Declare exactly four rows, in this order, for the newly
   owned SQL Importer fixture identity: MasterDataRaw, DailyDataRaw, SOBDataRaw,
   MOQDataRaw1; Condition=NULL in all rows. Bind DatabaseName to that verified
   exclusive fixture name and use the same name as the modern export label.
   Table-export content uses the canonical ExportInputTable.sql contract and its
   actual source-stage typed rows, not the physical-file serializer. Preserve
   native metadata/row ordering and comma replacement; no new ordering waiver.
   Archive membership is exactly five physical CSVs, four generated
   <ownedImporter>_<table>.CSV members and one date-marker text file. These names
   have no collisions. Prove duplicate/collision overwrite behavior separately.
   Omit inactive/empty non-NMS/no-Norm/MOQ2/exclusion/order/control/vendor/
   distributor physical files; retain those unchanged facts in typed source.
   Vehicle/config files are outside this intake archive. No other table or
   arbitrary WHERE condition is supported by this bounded binding.

4. **Eight upload logs.** Declare each of the eight named upload-log populations
   initially empty in the new Cohort2 owner, independently of approval queues.
   Bind UIUploadLogActionType to its six exact DDL seeds and the seven-day upload
   horizon to retained settings. Carry each owner's logs through exact retention;
   always generate its native header/archive even when empty. Positive focused
   fixtures cover all eight typed schemas, NULLs, duplicates and timestamps.
   This does not certify the missing populated application log producers or
   broaden the approved MDM workflow scope. Optional client-folder copies remain
   absent when the explicitly owned configured destination is absent.

5. **Generic archive clock.** Freeze each business date at00:00:00 Asia/Kolkata
   for these operational attempts and all retries. Bind year/month/day with
   four/two/two digits, hr=12, min=00, ampm=AM, so June6's marker is
   06_06_2026_12_00.txt and RunDateTime is2026-06-06 12:00AM. The marker text
   remains the exact native sentence. This clock is declared configuration,
   not inferred from modern engine timestamps or substituted with host time.

6. **Alerts and unavailable attachments.** Retain all14 exact seeded activation
   flags. Keep generic recipients/profile Not-Defined; record recipient-suppressed
   evaluations at their actual source stages. Positive isolated predicate fixtures
   use fixture@example.invalid as an explicit local-only recipient. No messages
   are sent. If DailyDataValidationError's positive branch is exercised, its
   commented-out CSV writer leaves the declared ZIP unavailable: record that
   outcome and fail the dependent operation rather than inventing an attachment
   or marking the intent ready. The approved empty sanitation configuration does
   not exercise that positive branch. Missing source populations remain errors.

## Source facts behind this decision

InputTableList and the eight upload logs have schemas but no seed rows. Generic
StdSettingsPre leaves date/time and recipient variables Not-Defined; there is no
generic site importer binding. OrderAllocBasedReports calls both histories even
when IsMTOEnvironment disables the current RRR producer. These are actual absent
inputs, not permission to repair legacy behavior. AGENTS.md says: “NEVER repair
legacy flaws, invent tie-breaks/defaults, hide incomparable fields, replace the
oracle, weaken assertions or report excluded behavior as parity.”

No decision is requested again for already-approved C3ZIP tooling, C4local-only
intents or C5owned backup/restore. Generic DBBkpCompress=1 uses native SQL database
compression only. Existing C6 failure qualification retains native unchecked
backup logging versus truthful modern failed attempts. The observed unmatched
Norm export redirect quote creates the intended filename in an owned CMD probe;
actual SQLCMD/ZIP proof must retain that behavior, not silently rewrite the BAT.
