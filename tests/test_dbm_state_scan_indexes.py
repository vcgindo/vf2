"""Focused Section10 D1/D2/D3/D5 ordered-scan proof.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date, timedelta
from unittest.mock import patch
import unittest

from mta.domain import dbm_ingestion, dbm_norm1_advisory, dbm_suspensions
from mta.domain.ordinal_lookup import OrderedIndex
from mta.row_sequences import RecordRows


TODAY = date(2026, 6, 6)


class CapturedIndex(OrderedIndex):
    instances = []
    force_enabled = True

    def __init__(self, *args, **kwargs):
        kwargs["enabled"] = self.force_enabled
        super().__init__(*args, **kwargs)
        self.instances.append(self)


class DbmStateScanIndexTests(unittest.TestCase):
    def setUp(self):
        CapturedIndex.instances = []
        CapturedIndex.force_enabled = True

    def equivalent(self, module, function, *args):
        before = deepcopy(args)
        with patch.object(module, "OrderedIndex", CapturedIndex):
            CapturedIndex.force_enabled = False
            expected = function(*deepcopy(args))
            CapturedIndex.instances = []
            CapturedIndex.force_enabled = True
            actual = function(*args)
        self.assertEqual(actual, expected)
        self.assertEqual(args, before)
        self.assertTrue(all(index._closed and index.owner is None
                            for index in CapturedIndex.instances))
        return actual, list(CapturedIndex.instances)

    def test_exclusions_sql_join_duplicates_nulls_file_rows_and_scaling(self):
        exclusions = [dict(SKUCode="Sku ", WhCode="Loc"),
                      dict(SKUCode=None, WhCode="Loc")]
        masters = [dict(SKUCode="sKU", WhCode="lOC "),
                   dict(SKUCode="SKU", WhCode="LOC"),
                   dict(SKUCode=None, WhCode="Loc")]
        for source in (masters, RecordRows.from_rows(masters)):
            actual, indexes = self.equivalent(
                dbm_ingestion, dbm_ingestion.import_exclusions, exclusions, source)
            self.assertEqual(actual, [
                dict(SKUCode="Sku ", WHCode="Loc", IsRedEnabled=False,
                     IsGreenEnabled=False),
                dict(SKUCode="Sku ", WHCode="Loc", IsRedEnabled=False,
                     IsGreenEnabled=False),
            ])
            self.assertEqual((indexes[0].builds, indexes[0].indexed_rows,
                              indexes[0].probes, indexes[0].candidate_rows),
                             (1, 3, 2, 2))
        self.assertEqual(dbm_ingestion.import_exclusions([{}], []), [])

        for size in (8, 16, 32):
            rows = [dict(SKUCode=f"S{i}", WhCode="W") for i in range(size)]
            with patch.object(dbm_ingestion, "OrderedIndex", CapturedIndex):
                CapturedIndex.instances = []
                dbm_ingestion.import_exclusions(rows, rows)
            index = CapturedIndex.instances[0]
            self.assertEqual((index.builds, index.indexed_rows, index.probes,
                              index.candidate_rows), (1, size, size, size))

    @staticmethod
    def introduction_state(size=2, *, streamed=False):
        masters = [dict(SKUCode=f"S{i}", WhCode="W", Norm=10, RLT=2,
                        SKUIntroDate="2026-06-01") for i in range(size)]
        suspended = [dict(SKUCode=f"S{i}", WhCode="W", IsRedEnabled=False,
                          IsGreenEnabled=True, ReplenishmentRatio=50)
                     for i in range(size)]
        if size == 2:
            suspended.insert(1, deepcopy(suspended[0]))
        daily = [dict(SKUCode=f"S{i}", WhCode="W", ReportDate="2026-06-06",
                      Stock=0, Receipts=3) for i in range(size)]
        if streamed:
            masters = RecordRows.from_rows(masters)
            daily = RecordRows.from_rows(daily)
        return dict(DBMMaster=masters, DailyConsumption=daily,
                    FirstReplenishmentPercentageTbl=[{"ReplenishmentPercentage": 50}],
                    SuspendNewSKUTbl=suspended)

    def test_introduction_duplicate_membership_multiplication_and_record_rows(self):
        for streamed in (False, True):
            state = self.introduction_state(streamed=streamed)
            result, indexes = self.equivalent(
                dbm_suspensions, dbm_suspensions.suspend_introductions,
                TODAY, state)
            members = result["SuspendNewSKUTbl"]
            self.assertEqual([row["IsRedEnabled"] for row in members],
                             [True, True, False])
            self.assertEqual(len(indexes), 3)
            self.assertEqual(sum(index.probes for index in indexes), 9)
            self.assertEqual(sum(index.candidate_rows for index in indexes), 11)

        for size in (8, 16, 32):
            with patch.object(dbm_suspensions, "OrderedIndex", CapturedIndex):
                CapturedIndex.instances = []
                dbm_suspensions.suspend_introductions(
                    TODAY, self.introduction_state(size))
            self.assertEqual(sum(index.builds for index in CapturedIndex.instances), 3)
            self.assertEqual(sum(index.indexed_rows for index in CapturedIndex.instances),
                             3 * size)
            self.assertEqual(sum(index.probes for index in CapturedIndex.instances),
                             3 * size)
            self.assertEqual(sum(index.candidate_rows for index in CapturedIndex.instances),
                             3 * size)

        conflict = self.introduction_state(1)
        conflict["DBMMaster"].append(deepcopy(conflict["DBMMaster"][0]))
        before = deepcopy(conflict)
        with self.assertRaisesRegex(ValueError, "duplicate introduction master"):
            dbm_suspensions.suspend_introductions(TODAY, conflict)
        self.assertEqual(conflict, before)

    @staticmethod
    def forced_state(size=3, *, streamed=False):
        masters = [dict(SKUCode=f"S{i}", WhCode="W", Norm=9, RCP=1)
                   for i in range(size)]
        suspended = [dict(SKUCode=f"S{i}", WhCode="W", IsRedEnabled=False,
                          IsGreenEnabled=False, WaitStartDate="2026-06-04",
                          WaitTillDate="2026-06-05", WaitForReceipts=False,
                          ReqReceipts=2) for i in range(size)]
        daily = [dict(SKUCode=f"s{i} ", WhCode="w ",
                      ReportDate=(TODAY - timedelta(days=offset)).isoformat(),
                      Receipts=1, Stock=10)
                 for i in range(size) for offset in (0, 1, 2)]
        if streamed:
            daily = RecordRows.from_rows(daily)
        return dict(LastBatchRunTbl=[{"LastRunDate": "2026-06-06T00:00:00"}],
                    DBMMaster=masters, ForcedNormChangeTbl=[],
                    SuspendNormsForceChangedTbl=suspended,
                    SuspendStockType=[dict(SKUCode=f"S{i}", WhCode="W",
                                           RedResumeDate=None, GreenResumeDate=None)
                                      for i in range(size)],
                    DailyConsumption=daily)

    def test_forced_history_equivalence_boundaries_and_scaling(self):
        for streamed in (False, True):
            result, indexes = self.equivalent(
                dbm_suspensions, dbm_suspensions.apply_forced_norm_stock,
                TODAY, self.forced_state(streamed=streamed))
            self.assertTrue(all(row["IsRedEnabled"]
                                for row in result["SuspendNormsForceChangedTbl"]))
            self.assertEqual(len(indexes), 1)
            self.assertEqual((indexes[0].indexed_rows, indexes[0].probes,
                              indexes[0].candidate_rows), (9, 6, 18))

        for size in (8, 16, 32):
            with patch.object(dbm_suspensions, "OrderedIndex", CapturedIndex):
                CapturedIndex.instances = []
                dbm_suspensions.apply_forced_norm_stock(TODAY, self.forced_state(size))
            index = CapturedIndex.instances[0]
            self.assertEqual((index.indexed_rows, index.probes, index.candidate_rows),
                             (3 * size, 2 * size, 6 * size))

    @staticmethod
    def accepted_state(size=3, *, streamed=False):
        masters = [dict(SKUCode=f"S{i}", WhCode="W", Norm=9, RLT=3, RCP=1)
                   for i in range(size)]
        suspended = [dict(SKUCode=f"S{i}", WhCode="W", DeltaNorm=2,
                          WaitStartDate="2026-06-03", WaitTillDate="2026-06-05",
                          WaitForReceipts=False, HasStockComeOutOfRed=False,
                          IsRedEnabled=False, IsGreenEnabled=False)
                     for i in range(size)]
        daily = [dict(SKUCode=f"s{i} ", WhCode="w ",
                      ReportDate=(TODAY - timedelta(days=offset)).isoformat(),
                      Receipts=2, Stock=10, BlueZone=1)
                 for i in range(size) for offset in (0, 1, 2, 3)]
        if streamed:
            daily = RecordRows.from_rows(daily)
        return dict(LastBatchRunTbl=[{"LastRunDate": "2026-06-06T00:00:00"}],
                    DBMMaster=masters, NormAcceptanceTbl=[],
                    SuspendAcceptedNormsStockType=suspended,
                    SuspendStockType=[dict(SKUCode=f"S{i}", WhCode="W",
                                           RedResumeDate=None, GreenResumeDate=None)
                                      for i in range(size)],
                    DailyConsumption=daily)

    def test_accepted_current_and_horizon_history_once_per_generation(self):
        for function in (dbm_suspensions.suspend_accepted_norm_stock,
                         dbm_suspensions.apply_accepted_norm_stock):
            for streamed in (False, True):
                with self.subTest(function=function.__name__, streamed=streamed):
                    result, indexes = self.equivalent(
                        dbm_suspensions, function, TODAY,
                        self.accepted_state(streamed=streamed))
                    self.assertTrue(all(row["IsRedEnabled"]
                                        for row in result["SuspendAcceptedNormsStockType"]))
                    self.assertEqual(len(indexes), 1)
                    self.assertEqual((indexes[0].builds, indexes[0].indexed_rows,
                                      indexes[0].probes, indexes[0].candidate_rows),
                                     (1, 12, 6, 24))

        for size in (8, 16, 32):
            with patch.object(dbm_suspensions, "OrderedIndex", CapturedIndex):
                CapturedIndex.instances = []
                dbm_suspensions.apply_accepted_norm_stock(
                    TODAY, self.accepted_state(size))
            index = CapturedIndex.instances[0]
            self.assertEqual((index.builds, index.indexed_rows, index.probes,
                              index.candidate_rows),
                             (1, 4 * size, 2 * size, 8 * size))

        conflict = self.accepted_state(1)
        conflict["DailyConsumption"].append(dict(
            conflict["DailyConsumption"][0], Stock=0))
        before = deepcopy(conflict)
        with self.assertRaisesRegex(ValueError, "conflicting same-day accepted-Norm"):
            dbm_suspensions.apply_accepted_norm_stock(TODAY, conflict)
        self.assertEqual(conflict, before)

    @staticmethod
    def advisory_state(size=3, *, streamed=False):
        masters = [dict(SKUCode=f"S{i}", WhCode="W", Norm=1, RLT=1)
                   for i in range(size)]
        daily = [dict(SKUCode=f"s{i} ", WhCode="w ",
                      ReportDate=(TODAY - timedelta(days=offset)).isoformat(),
                      Consumption=1)
                 for i in range(size) for offset in (0, 1, 2)]
        if streamed:
            daily = RecordRows.from_rows(daily)
        return dict(LastBatchRunTbl=[{"LastRunDate": "2026-06-06T00:00:00"}],
                    DBMMaster=masters, DailyConsumption=daily,
                    PhaseInTbl=[], PhaseOutTbl=[], IntermediateTables=[])

    def test_norm1_first_scan_error_order_file_rows_and_many_key_scaling(self):
        for streamed in (False, True):
            result, indexes = self.equivalent(
                dbm_norm1_advisory, dbm_norm1_advisory.norm1_advisory,
                TODAY, self.advisory_state(streamed=streamed))
            self.assertEqual(len(result["Norm1IncreaseSuggestions"]), 3)
            self.assertEqual((indexes[0].indexed_rows, indexes[0].probes,
                              indexes[0].candidate_rows), (9, 2, 6))

        invalid = self.advisory_state(2)
        invalid["DailyConsumption"].insert(
            1, dict(SKUCode="unrelated", WhCode="W",
                    ReportDate="invalid-date", Consumption=1))
        before = deepcopy(invalid)
        with self.assertRaises(ValueError):
            dbm_norm1_advisory.norm1_advisory(TODAY, invalid)
        self.assertEqual(invalid, before)

        no_eligible = self.advisory_state(2)
        for master in no_eligible["DBMMaster"]:
            master["Norm"] = 2
        no_eligible["DailyConsumption"][0]["ReportDate"] = "invalid-date"
        self.assertEqual(dbm_norm1_advisory.norm1_advisory(
            TODAY, no_eligible)["Norm1IncreaseSuggestions"], [])

        ordered_error = self.advisory_state(2)
        ordered_error["DailyConsumption"][0]["ReportDate"] = "invalid-date"
        del ordered_error["DBMMaster"][1]["Norm"]
        with self.assertRaisesRegex(ValueError, "Invalid isoformat"):
            dbm_norm1_advisory.norm1_advisory(TODAY, ordered_error)

        for size in (8, 16, 32):
            with patch.object(dbm_norm1_advisory, "OrderedIndex", CapturedIndex):
                CapturedIndex.instances = []
                dbm_norm1_advisory.norm1_advisory(TODAY, self.advisory_state(size))
            index = CapturedIndex.instances[0]
            self.assertEqual((index.indexed_rows, index.probes, index.candidate_rows),
                             (3 * size, size - 1, 3 * (size - 1)))


if __name__ == "__main__":
    unittest.main()
