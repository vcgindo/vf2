"""Focused Section9 A5 native producer-boundary proof.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend
presentation and behavior. No frontend redesign, substitute screens, refactoring
or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal
import unittest
from unittest.mock import patch

from mta.application.native_output_contracts import (
    BTR_CURRENT, CurrentGenerations, columns, control_fields, validate_cell,
    validate_rows,validate_dbm_writer,native_assignments,producing_native,
)
from mta.application.r1_norm_updates import apply_norm_updates
from mta.domain.btr_finalization import BPR_SOURCE_FIELDS, DAYS, _import_bpr, _update_br_age
from mta.domain.dbm_postrules import generate_reports
from mta.domain.dbm_suspension_history import CONTRIBUTORS, gather_suspension_history


TODAY = "2026-06-06"


class NativeValueContractTests(unittest.TestCase):
    def test_primitive_nullable_images_remain_valid_but_native_writers_reject_required_null(self):
        from mta.domain.dbm_ingestion import import_daily_observations
        raw=[dict(SKUCode='S',WhCode='W',Stock=1,Consumption=None,GIT=0,Receipts=0,ReportDate=TODAY)]
        args=(TODAY,[],raw,[dict(SKUCode='S',WhCode='W')],[],[],[])
        before=deepcopy(raw)
        self.assertIsNone(import_daily_observations(*args)[0]['Consumption'])
        with self.assertRaisesRegex(ValueError,'Consumption'),native_assignments():
            import_daily_observations(*args)
        with native_assignments():
            valid=import_daily_observations(TODAY,[],[dict(raw[0],Consumption=0)],args[3],[],[],[])
        self.assertEqual(valid[0]['Consumption'],0)
        self.assertEqual(raw,before)
        state=dict(LastBatchRunTbl=[{'LastRunDate':TODAY+'T00:00:00'}],DBMMaster=[],Suggestions=[],
            SuggestionsLog=[],SpikeReport=[],SuspendSpikeTbl=[dict(SKUCode='S',WhCode='W',WaitStartDate=TODAY,WaitTillDate=None)])
        self.assertIsNone(generate_reports(TODAY,state)['SpikeReport'][0]['SuspendTillDate'])
        with self.assertRaisesRegex(ValueError,'SuspendTillDate'),native_assignments():generate_reports(TODAY,state)
        valid=deepcopy(state);valid['SuspendSpikeTbl'][0]['WaitTillDate']='2026-06-07'
        with native_assignments():self.assertEqual(generate_reports(TODAY,valid)['SpikeReport'][0]['SuspendTillDate'],'2026-06-07')

    def test_native_scope_resets_after_error_and_nested_non_native_call(self):
        self.assertFalse(producing_native())
        with self.assertRaisesRegex(ValueError,'stop'),native_assignments():
            self.assertTrue(producing_native())
            with native_assignments(False):self.assertFalse(producing_native())
            self.assertTrue(producing_native())
            raise ValueError('stop')
        self.assertFalse(producing_native())
    def test_semantic_writer_roster_does_not_rescan_deepcopied_unchanged_tables(self):
        state=dict(Suggestions=[],DBMMaster=[{'sentinel':'unchanged'}],DailyConsumption=[{'history':'retained'}])
        with patch('mta.application.native_output_contracts.validate_rows') as validate:
            validate_dbm_writer(deepcopy(state),'rule1')
            validate.assert_called_once_with([], 'DBM/Suggestions',stage='dbm/rule1')
            validate.reset_mock()
            validate_dbm_writer(deepcopy(state),'daily-cleanup')
            validate.assert_not_called()
        with self.assertRaisesRegex(ValueError,'Undeclared native DBM writer'):
            validate_dbm_writer(state,'invented-stage')

    def test_full_partial_empty_rosters_and_native_scalar_boundaries(self):
        full = dict(SKUCode="S", WhCode="W", Type=1, NewNorm=2)
        rows = [full]
        self.assertIs(validate_rows(rows, "DBM/Suggestions", stage="full"), rows)
        validate_rows([dict(SKUCode="S", Type=1)], "DBM/Suggestions",
                      fields=("SKUCode", "Type"), stage="partial")
        validate_rows([], "DBM/Suggestions", stage="empty")
        self.assertEqual(control_fields("NormChangeLogTbl"),
                         ("SKUCode", "WHCode", "OldNorm", "NewNorm",
                          "NormChangeDate", "NormChangeReason"))
        for row in (dict(full, extra=1), {k: v for k, v in full.items() if k != "NewNorm"}):
            with self.assertRaisesRegex(ValueError, "field roster differs"):
                validate_rows([row], "DBM/Suggestions", stage="roster")
        with self.assertRaisesRegex(ValueError, "Undeclared native producer fields"):
            validate_rows([{}], "DBM/Suggestions", fields=("missing",), stage="partial")

        schema = columns("DBM/Suggestions")
        validate_cell("", schema["SKUCode"])
        validate_cell("😀" * 25, schema["SKUCode"])
        for value in (None, "😀" * 26):
            with self.assertRaises(ValueError):
                validate_cell(value, schema["SKUCode"])
        for value in (-2**31, 2**31 - 1):
            validate_cell(value, schema["Type"])
        for value in (True, 1.5, 2**31, -2**31 - 1):
            with self.assertRaises(ValueError):
                validate_cell(value, schema["Type"])

        decimal_column = columns("BTR/ChronicUnavalabilityData")["PhysicalInventoryPen"]
        for value in (Decimal("99999999.99"), Decimal("-99999999.99"), None):
            validate_cell(value, decimal_column)
        for value in (Decimal("1.234"), Decimal("100000000.00"), float("nan")):
            with self.assertRaises(ValueError):
                validate_cell(value, decimal_column)

    def test_dispatch_generation_is_complete_and_retained_identity_is_not_scanned(self):
        self.assertIn("BufferTrendDispatch", BTR_CURRENT)
        initial = {name: [] for name in BTR_CURRENT}
        generations = CurrentGenerations(BTR_CURRENT, "BTR", initial)
        with patch("mta.application.native_output_contracts.validate_rows") as validate:
            generations.validate(dict(initial), "unchanged")
            validate.assert_not_called()
            current = dict(initial)
            current["BufferTrendDispatch"] = []
            generations.validate(current, "dispatch")
            validate.assert_called_once_with(
                current["BufferTrendDispatch"], "BTR/BufferTrendDispatch", stage="dispatch")
            generations.validate(current, "reused")
            self.assertEqual(validate.call_count, 1)

        row = dict(SKUCode="S", WhCode="W", D90="Black", BRAge=None,
                   BRAgeRedCount=None, BRAgeBlackCount=None,
                   **{field: "Black" for field in DAYS if field != "D90"})
        opening = {"BufferTrendDispatch": [row], "ExpediteDispatches": []}
        before = deepcopy(opening)
        result = _update_br_age(opening, {"ExpediteDispatches": []},
                                "BufferTrendDispatch", 0, True, _owned=True)
        self.assertIsNot(result["BufferTrendDispatch"], opening["BufferTrendDispatch"])
        self.assertEqual(opening, before)
        self.assertEqual(result["BufferTrendDispatch"][0]["BRAge"], 90)


class NewHistoryRowContractTests(unittest.TestCase):
    def setUp(self):
        context=native_assignments();context.__enter__()
        self.addCleanup(context.__exit__,None,None,None)
    def test_postrule_validates_only_new_log_and_spike_rows(self):
        prior_log = dict(SKUCode="OLD", WhCode="W", Type=1, OldNorm=1,
                         NewNorm=2, SuggestionDate="2026-06-05")
        prior_spike = dict(SKUCode="OLD", WhCode="W", SuspendFromDate="2026-06-05",
                           SuspendTillDate="2026-06-07")
        state = dict(LastBatchRunTbl=[{"LastRunDate": TODAY + "T00:00:00"}],
                     DBMMaster=[dict(SKUCode="S", WhCode="W", Norm=1)],
                     Suggestions=[dict(SKUCode="S", WhCode="W", Type=1, NewNorm=2)],
                     SuggestionsLog=[prior_log], SuspendSpikeTbl=[dict(
                         SKUCode="S", WhCode="W", WaitStartDate=TODAY,
                         WaitTillDate="2026-06-08")], SpikeReport=[prior_spike])
        calls = []
        real = validate_rows

        def capture(rows, table, **kwargs):
            materialized = list(rows)
            calls.append((table, deepcopy(materialized)))
            return real(materialized, table, **kwargs)

        with patch("mta.application.native_output_contracts.validate_rows", side_effect=capture):
            result = generate_reports(TODAY, state)
        self.assertEqual([name for name, _ in calls], ["DBM/SuggestionsLog", "DBM/SpikeReport"])
        self.assertEqual([len(rows) for _, rows in calls], [1, 1])
        self.assertNotIn(prior_log, calls[0][1])
        self.assertNotIn(prior_spike, calls[1][1])
        self.assertEqual(len(result["SuggestionsLog"]), 2)
        self.assertEqual(len(result["SpikeReport"]), 2)

    def test_norm_and_suspension_writers_reject_invalid_new_rows_before_history_append(self):
        controls = dict(
            dbm_master=[dict(SKUCode="S", WhCode="W", Norm=1, MinNorm=0)],
            suggestions=[dict(SKUCode="S", WhCode="W", Type=1, NewNorm=2**31)],
            phase_out=[], acceptance=[], accepted=[dict(SKUCode="S", WhCode="W")],
            reason_codes=[dict(Id=1)], log=[], triggers=[], phase_in=[], seasonality=[],
            forced=[], upload_log=[], importer_master=[], raw_master=[])
        with self.assertRaisesRegex(ValueError, "controls/accepted-log"):
            apply_norm_updates(controls, TODAY)

        member = dict(SKUCode="S", WhCode="W", RedEnabled=2, GreenEnabled=True)
        suspension = dict(LastBatchRunTbl=[{"LastRunDate": TODAY + "T00:00:00"}],
                          SuspendStockType=[member],
                          SuspendConsumptionType=[dict(member, RedEnabled=True)],
                          SuspendHistory=[])
        for table, _, _ in CONTRIBUTORS:
            suspension[table] = []
        with self.assertRaisesRegex(ValueError, "suspension-history"):
            gather_suspension_history(TODAY, suspension)

    def test_bpr_writer_validates_only_incoming_history_rows(self):
        retained = dict(SKUCode=None)
        prior = dict(BPR=[retained], LocationAttributeData=[], SiteDescriptionTbl=[],
                     SkuAttributeData=[], SKUDescriptionTbl=[], SkuLocAttributeData=[])
        incoming = {field: None for field in BPR_SOURCE_FIELDS}
        incoming.update(SKUCode=None, WhCode="W")
        facts = dict(vf_RationedReqReport=[incoming], LocationAttributeData=[],
                     SiteDescriptionTbl=[], SkuAttributeData=[], SKUDescriptionTbl=[],
                     SkuLocAttributeData=[], CWH_List=[], DistributorList=[], DBMMaster=[])
        with self.assertRaisesRegex(ValueError, "btr/import-bpr"):
            _import_bpr(date(2026, 6, 6), prior, facts)


if __name__ == "__main__":
    unittest.main()
