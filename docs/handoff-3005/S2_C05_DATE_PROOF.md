# Native new-pair capture date

The native temporal caller now supplies the current business date to NMS composition. The legacy caller retains its previously sealed opening-date behavior.

The controller independently approved this correction after canonical attribution: VectorFLOWv4.bat93 calls SetRunDate before import96 and validation109; SetRunDate.bat6 sets Importer LastRunDate to RunDate; NMSImportData.sql44 uses that date for approved added-pair raw SKUIntroDate. ValidateAndProcessMaster.sql793/829/840 records current-date retirement, re-entry and final new-master introduction dates. Submission audit/history timestamps remain a separate contract.

`test_native_mdm_capture_date.py` runs the actual execute_day caller, request/date/retry branches and real compose implementation. Admission, persistence and transaction boundaries are explicit test doubles; execution stops after composition. It compares every raw column for an added pair and an existing pair, proves native July5 versus retained legacy July4, and preserves the existing pair's 2025 introduction date. A retry reuses the identical frozen snapshot/request, never selects a fresh queue, and rejects a failed-capture business-date mismatch before composition.

Two tests pass. No business calculation, initialization, database writes or accepted-day replay occurred. The first test-double setup failure and corrected passing log are retained. This component proof does not replace C05's pending real native addition and own-successor acceptance.

External receipt: `D:/freshvcf-build/evidence/handoff3005-s2-20261013-001/c05-native-date-component-proof.json`. It binds the pre-correction802eb8f temporal source, controller boundary, test/source hashes and logs. Earlier accepted C01–C04/shared-supply cases did not exercise native MDM pair addition; their receipts and seals remain unchanged. The authoritative tracker remains `F:/freshvcf/docs/handoff-3005/TRACKER.md`.
