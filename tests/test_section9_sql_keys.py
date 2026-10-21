"""Focused Section9 A4 SQL identifier-key proof.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend
presentation and behavior. No frontend redesign, substitute screens, refactoring
or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date
from pathlib import Path
import unittest

from mta.domain.btr_finalization import (
    BPR_SOURCE_FIELDS, _categories, _count_graph, _import_bpr, _latest_norms, _pivot,
    _snapshot, _unique_source, _generate_trends,
)
from mta.domain.dbm_ingestion import calculate_extended_ocp, import_daily_observations
from mta.domain.dbm_rules import stockout_type_a
from mta.domain.dbm_suspension_history import CONTRIBUTORS, gather_suspension_history
from mta.domain.dbm_postrules import discard_suggestions, generate_reports
from mta.domain.dbm_norm1_advisory import norm1_advisory
from mta.domain.dbm_norm_change_history import norm_change_history
from mta.domain.dbm_norm012 import data_stage, detail_stage
from mta.domain.ordinal_lookup import OrdinalLookup
from mta.domain.sql_identity_keys import group_key, join_key


TODAY = date(2026, 6, 6)


class QualifiedSqlKeyTests(unittest.TestCase):
    def test_join_group_null_domain_and_original_spelling(self):
        left = join_key("Sku ", "wh")
        self.assertEqual(left, join_key("sKU", "WH  "))
        self.assertEqual(tuple(left), ("Sku ", "wh"))
        self.assertNotEqual(left, join_key("SKU\t", "WH"))
        self.assertNotEqual(join_key("0", "WH"), join_key("00", "WH"))
        self.assertNotEqual(join_key(None, "WH"), join_key(None, "wh"))
        self.assertEqual(group_key(None, "WH "), group_key(None, "wh"))
        with self.assertRaisesRegex(ValueError, "UNQUALIFIED_SCALAR_DOMAIN"):
            join_key("café", "WH")

    def test_ordinal_index_preserves_duplicates_null_denial_mutation_and_lifetime(self):
        for size in (32, 64, 128):
            rows = [dict(SKUCode=f"S{i}", WhCode="W", ordinal=i) for i in range(size)]
            rows.extend((dict(SKUCode="Target ", WhCode="w", ordinal=size),
                         dict(SKUCode="target", WhCode="W ", ordinal=size + 1),
                         dict(SKUCode=None, WhCode="W", ordinal=size + 2)))
            with OrdinalLookup(rows) as lookup:
                folder = Path(lookup.directory.name)
                matches = list(lookup.matching(rows, ("TARGET", "W")))
                self.assertEqual([row["ordinal"] for row in matches], [size, size + 1])
                self.assertEqual(lookup.candidate_rows, 2)
                self.assertEqual(list(lookup.matching(rows, (None, "W"))), [])
                self.assertEqual(lookup.db.execute("SELECT COUNT(*) FROM candidate").fetchone()[0], size + 2)
                rows[size] = dict(SKUCode="changed", WhCode="W", ordinal=size)
                with self.assertRaisesRegex(ValueError, "reordered or mutated"):
                    list(lookup.matching(rows, ("TARGET", "W")))
            self.assertFalse(folder.exists())

        for field, replacement in (("SKUCode", "tARGET"), ("WhCode", "W ")):
            rows = [dict(SKUCode="Target", WhCode="W", ordinal=0),
                    dict(SKUCode="target ", WhCode="w ", ordinal=1)]
            with OrdinalLookup(rows) as lookup:
                self.assertEqual([row["ordinal"] for row in lookup.matching(rows, ("TARGET", "w"))], [0, 1])
                rows[0][field] = replacement
                with self.assertRaisesRegex(ValueError, "reordered or mutated"):
                    list(lookup.matching(rows, ("target", "W")))


class DbmQualifiedJoinTests(unittest.TestCase):
    def test_postrules_and_norm1_advisory_qualified_joins(self):
        base = dict(LastBatchRunTbl=[{"LastRunDate": "2026-06-06T00:00:00"}],
                    DBMMaster=[dict(SKUCode="Sku ", WhCode="Loc", Norm=3, MinNorm=2),
                               dict(SKUCode="Sku ", WhCode="Loc", Norm=3, MinNorm=2),
                               dict(SKUCode=None, WhCode="Loc", Norm=3, MinNorm=2)],
                    Suggestions=[dict(SKUCode="sKU", WhCode="lOC ", Type=1, NewNorm=4),
                                 dict(SKUCode=None, WhCode="Loc", Type=1, NewNorm=3)],
                    DiscardedSuggestions=[], SuggestionsLog=[], SuspendSpikeTbl=[], SpikeReport=[])
        before = deepcopy(base)
        reported = generate_reports(TODAY, base)
        self.assertEqual(len(reported["SuggestionsLog"]), 2)
        self.assertEqual((reported["SuggestionsLog"][0]["SKUCode"],
                          reported["SuggestionsLog"][0]["WhCode"]), ("Sku ", "Loc"))
        self.assertEqual(reported["Suggestions"][-1]["SKUCode"], None)
        discard = deepcopy(base)
        discard["Suggestions"][0]["NewNorm"] = 1
        discarded = discard_suggestions(TODAY, discard)
        self.assertEqual(len(discarded["DiscardedSuggestions"]), 1)
        self.assertEqual(discarded["Suggestions"], [base["Suggestions"][1]])
        self.assertEqual(base, before)

        advisory = dict(LastBatchRunTbl=base["LastBatchRunTbl"],
                        DBMMaster=[dict(SKUCode="Sku ", WhCode="Loc", Norm=1, RLT=1),
                                   dict(SKUCode=None, WhCode="Loc", Norm=1, RLT=1)],
                        DailyConsumption=[
                            dict(SKUCode="SKU", WhCode="loc ", ReportDate="2026-06-04", Consumption=1),
                            dict(SKUCode="SKU", WhCode="loc ", ReportDate="2026-06-04", Consumption=1),
                            dict(SKUCode="sKu", WhCode="LOC", ReportDate="2026-06-05", Consumption=1),
                            dict(SKUCode="sku", WhCode="loc", ReportDate="2026-06-06", Consumption=1),
                            dict(SKUCode=None, WhCode="Loc", ReportDate="2026-06-06", Consumption=9)],
                        PhaseInTbl=[], PhaseOutTbl=[], IntermediateTables=[])
        result = norm1_advisory(TODAY, advisory)["Norm1IncreaseSuggestions"]
        self.assertEqual(len(result), 1)
        self.assertEqual((result[0]["SKUCode"], result[0]["WhCode"]), ("Sku ", "Loc"))
        self.assertEqual(result[0]["SaleInAllBuckets"], 4)
        excluded = deepcopy(advisory)
        excluded["PhaseInTbl"] = [dict(SKUCode="SKU")]
        self.assertEqual(norm1_advisory(TODAY, excluded)["Norm1IncreaseSuggestions"], [])

    def test_norm_change_and_norm012_adjacent_qualified_joins(self):
        history_state = dict(LastBatchRunTbl=[{"LastRunDate": "2026-06-06T00:00:00"}],
            NormChangeLogTbl=[dict(SKUCode="Sku ", WHCode="Loc", OldNorm=1, NewNorm=2,
                                   NormChangeDate="2026-06-06", NormChangeReason=1),
                              dict(SKUCode=None, WHCode=None, OldNorm=1, NewNorm=2,
                                   NormChangeDate="2026-06-06", NormChangeReason=None)],
            SKUDescriptionTbl=[dict(SKUCode="sKU", SKUDescription="Item")],
            SiteDescriptionTbl=[dict(WHCode="lOC ", WHDescription="Site")],
            ReasonCodes=[dict(Id=1, Reason="Increase")])
        history = norm_change_history(TODAY, history_state, 30)["ReportRows"]
        self.assertEqual(history[0]["values"][:4], ["Sku ", "Item", "Loc", "Site"])
        self.assertEqual(history[1]["values"][:4], [None, None, None, None])

        attrs = {f"c{i}": None for i in range(1, 16)}
        report_state = dict(
            LastBatchRunTbl=history_state["LastBatchRunTbl"],
            DBMMaster=[dict(SKUCode="Sku ", WhCode="Loc", Norm=0, ParentWhCode="Parent"),
                       dict(SKUCode="sKU", WhCode="PARENT ", Norm=7, ParentWhCode=None),
                       dict(SKUCode=None, WhCode=None, Norm=0, ParentWhCode=None)],
            DailyConsumption=[dict(SKUCode="SKU", WhCode="lOC ", ReportDate="2026-06-05", Consumption=2),
                              dict(SKUCode=None, WhCode=None, ReportDate="2026-06-05", Consumption=9)],
            SKUDescriptionTbl=[dict(SKUCode="sku", SKUDescription="Item"),
                               dict(SKUCode=None, SKUDescription="Null")],
            SiteDescriptionTbl=[dict(WHCode="LOC ", WHDescription="Site")],
            SkuAttributeData=[dict(SKUCode="sKU", **attrs)],
            SkuLocAttributeData=[dict(SKUCode="SKU", LocCode="loc ", **attrs)],
            LocationAttributeData=[dict(WHCode="lOc", **attrs)],
            Norm0Norm1Norm2Report=[], Norm0_1_2ReportDetails=[], IntermediateTables=[])
        data = data_stage(TODAY, report_state, 0, 30)
        self.assertEqual(len(data["Norm0Norm1Norm2Report"]), 1)
        self.assertEqual((data["Norm0Norm1Norm2Report"][0]["SKUCode"],
                          data["Norm0Norm1Norm2Report"][0]["WHCode"]), ("Sku ", "Loc"))
        details = detail_stage(data)["Norm0_1_2ReportDetails"]
        self.assertEqual(len(details), 1)
        self.assertEqual((details[0]["WhName"], details[0]["ParentNorm"]), ("Site", 7))

    def test_observation_exclusions_bluezones_duplicates_and_spelling(self):
        raw = [
            dict(SKUCode="Sku", WhCode="Main ", ReportDate=TODAY, Stock=1, Consumption=2, GIT=3, Receipts=4),
            dict(SKUCode="S2", WhCode="blocked", ReportDate=TODAY, Stock=1, Consumption=2, GIT=3, Receipts=4),
            dict(SKUCode="S3", WhCode="vendor", ReportDate=TODAY, Stock=1, Consumption=2, GIT=3, Receipts=4),
            dict(SKUCode=None, WhCode="Main", ReportDate=TODAY, Stock=1, Consumption=2, GIT=3, Receipts=4),
        ]
        masters = [dict(SKUCode="sKU ", WhCode="MAIN"), dict(SKUCode="S2", WhCode="BLOCKED "),
                   dict(SKUCode="S3", WhCode="VENDOR "),
                   dict(SKUCode=None, WhCode="Main")]
        bpr = [dict(SKUCode="SKU", WhCode="main", ReportDate=TODAY, BlueZone=7)]
        before = deepcopy((raw, masters, bpr))
        actual = import_daily_observations(
            TODAY, [], raw, masters, bpr,
            [dict(WhCode="BLOCKED ", ReportDate=TODAY, TransactedItemCount=0)],
            [dict(WhCode="VENDOR ", ReportDate=TODAY, TransactedItemCount=0)],
        )
        self.assertEqual(actual, [dict(SKUCode="Sku", WhCode="Main ", Stock=1, Consumption=2,
                                       GIT=3, Receipts=4, BlueZone=7, ReportDate=TODAY)])
        self.assertEqual((raw, masters, bpr), before)
        with self.assertRaisesRegex(ValueError, "conflicting BPR BlueZone"):
            import_daily_observations(TODAY, [], raw, masters, bpr + [
                dict(SKUCode="sku ", WhCode="MAIN ", ReportDate=TODAY, BlueZone=8)], [], [])

    def test_extended_ocp_and_nonempty_suspension_rule_history(self):
        attrs = [dict(SKUCode="Sku", WhCode="Loc ", ExtendedOCP=0),
                 dict(SKUCode=None, WhCode="Loc", ExtendedOCP=9)]
        masters = [dict(SKUCode="sKU ", WhCode="LOC", OCP=2, RLT=1)]
        daily = [dict(SKUCode="SKU", WhCode="loc", ReportDate=day, Stock=0)
                 for day in ("2026-06-04", "2026-06-05", "2026-06-06")]
        self.assertEqual([row["ExtendedOCP"] for row in
                          calculate_extended_ocp(TODAY, attrs, masters, daily)], [4, 9])

        member = dict(SKUCode="Sku", WhCode="Loc ", RedEnabled=False, GreenEnabled=True)
        state = dict(LastBatchRunTbl=[{"LastRunDate": "2026-06-06T00:00:00"}],
                     SuspendStockType=[member],
                     SuspendConsumptionType=[dict(member, SKUCode="sKU ", WhCode="LOC")],
                     SuspendHistory=[])
        for table, _, _ in CONTRIBUTORS:
            state[table] = []
        state["SuspendWhitesTbl"] = [dict(SKUCode="SKU", WhCode="loc", IsRedEnabled=False)]
        history = gather_suspension_history(TODAY, state)["SuspendHistory"]
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["SKUCode"], "Sku")
        self.assertEqual(history[0]["RedReasonStockType"], 64)

        rules = dict(LastBatchRunTbl=[{"LastRunDate": "2026-06-06T00:00:00"}],
                     SuspendStockType=[dict(SKUCode="sKU ", WhCode="LOC", RedEnabled=True)],
                     DBMMaster=[dict(SKUCode="Sku", WhCode="Loc ", Norm=3)],
                     DailyConsumption=[dict(SKUCode="SKU", WhCode="loc", ReportDate=TODAY, Stock=0)],
                     Suggestions=[], IntermediateTables=[])
        suggestion = stockout_type_a(TODAY, rules)["Suggestions"]
        self.assertEqual(suggestion, [dict(SKUCode="SKU", WhCode="loc", Type=1, NewNorm=4)])


class BtrQualifiedJoinTests(unittest.TestCase):
    def test_mixed_null_pivot_keys_are_grouped_then_excluded_before_joined_sort(self):
        row=dict(SKUCode='S',WHCode='W',ParentWhCode='P',ReportDate='2026-06-06',Norm=5,VirtualNorm=5,
            **{name:'Black' for name in ('TechColor','EcoColor','DispatchColor','PhysicalInventoryColor')},
            **{name:100 for name in ('TechPen','EcoPen','DispatchPen','PhysicalInventoryPen')})
        original={'BPR':[row], 'LocationAttributeData':[]}
        expected=_generate_trends(TODAY,original,{'DBMMaster':[]})
        for field in ('SKUCode','WHCode'):
            source={'BPR':[dict(row,**{field:None}),row], 'LocationAttributeData':[]}
            before=deepcopy(source)
            self.assertEqual(_generate_trends(TODAY,source,{'DBMMaster':[]}),
                {**expected,'BPR':source['BPR']})
            self.assertEqual(source,before)

    @staticmethod
    def _fields(names, **values):
        return {name: values.get(name) for name in names}

    def test_attribute_master_parent_norm_location_sync(self):
        report = self._fields(BPR_SOURCE_FIELDS, SKUCode="Sku", WhCode="Child ",
                              ParentWhCode="Parent", Norm=5, VirtualNorm=6,
                              TechPen=1, EcoPen=2, DispatchPen=3, PhysicalInventoryPen=4,
                              TechColor="Green", EcoColor="Green", DispatchColor="Green",
                              PhysicalInventoryColor="Green", Stock=1, GIT=0)
        location_fields = ("WHCode", "LocationType", "LogisticsLocation", "LL1", "LL2", "LL3", "LL4", "LL5") + tuple(f"c{i}" for i in range(1, 16))
        sku_fields = ("SKUCode", "ElephantOrderCapping", "Weight", "Volume", "SL1", "SL2", "SL3", "SL4", "SL5") + tuple(f"c{i}" for i in range(1, 16))
        sku_loc_fields = ("SKUCode", "LocCode", "PackSize", "SpikeThreshold", "PSOThreshold", "FGRMFlag", "StockPercentForRationing", "NormPercentReservation", "NonNMS") + tuple(f"c{i}" for i in range(1, 16))
        prior = dict(BPR=[], LocationAttributeData=[], SiteDescriptionTbl=[],
                     SkuAttributeData=[], SKUDescriptionTbl=[], SkuLocAttributeData=[])
        facts = dict(vf_RationedReqReport=[report],
                     LocationAttributeData=[self._fields(location_fields, WHCode="CHILD", LocationType="x"),
                                            self._fields(location_fields, WHCode="parent ", LocationType="x")],
                     SiteDescriptionTbl=[dict(WHCode="child", WHDescription="child")],
                     SkuAttributeData=[self._fields(sku_fields, SKUCode="SKU ")],
                     SKUDescriptionTbl=[dict(SKUCode="sku", SKUDescription="item")],
                     SkuLocAttributeData=[self._fields(sku_loc_fields, SKUCode="SKU", LocCode="CHILD")],
                     CWH_List=[], DistributorList=[dict(WhCode="child")],
                     DBMMaster=[dict(SKUCode="SKU ", WhCode="CHILD", ParentWhCode="PARENT ")])
        before = deepcopy((prior, facts))
        result = _import_bpr(TODAY, prior, facts)
        self.assertEqual(result["BPR"][0]["SKUCode"], "Sku")
        self.assertEqual(result["LocationAttributeData"][0]["WhType"], "dist")
        self.assertTrue(result["LocationAttributeData"][0]["IsChild"])
        self.assertTrue(result["LocationAttributeData"][1]["IsParent"])
        self.assertEqual(len(result["SkuAttributeData"]), 1)
        self.assertEqual(len(result["SkuLocAttributeData"]), 1)
        self.assertEqual((prior, facts), before)

        norms = _latest_norms(result["BPR"], [dict(SKUCode="sku ", WhCode="child", Norm=8,
                                                   ParentWhCode="Parent ")])
        self.assertEqual(norms[next(iter(norms))], (8, 6, "Parent "))
        with self.assertRaisesRegex(ValueError, "latest BTR norm"):
            _latest_norms(result["BPR"] + [dict(result["BPR"][0], SKUCode="sKU ", WHCode="CHILD",
                                                Norm=9)], [])
        with self.assertRaisesRegex(ValueError, "latest BPR parent"):
            _import_bpr(TODAY, prior, {**facts, "vf_RationedReqReport": [
                report, dict(report, ParentWhCode="parent ")]})

    def test_trend_pivot_snapshot_category_joins_and_ambiguity(self):
        bpr = [dict(SKUCode="Sku", WHCode="Loc ", ReportDate="2026-06-06", TechColor="Red"),
               dict(SKUCode="Sku", WHCode="Loc ", ReportDate="2026-06-06", TechColor="Black")]
        pivot = _pivot(bpr, TODAY, "TechColor")
        self.assertEqual(len(pivot), 1)
        self.assertEqual(next(iter(pivot.values()))["D90"], "Red")
        with self.assertRaisesRegex(ValueError, "pivot identity spelling"):
            _pivot(bpr + [dict(bpr[0], SKUCode="sKU ", WHCode="LOC")], TODAY, "TechColor")
        graph = _count_graph({"BPR": [dict(ReportDate="2026-06-06", ParentWhCode=None,
                    WHCode="Loc", TechColor="Red", EcoColor="Red", DispatchColor="Red",
                    PhysicalInventoryColor="Red")] * 2})["BufferTrendGraph"]
        self.assertEqual(len(graph), 1)
        self.assertIsNone(graph[0]["SrcWhCode"])

        def trend(sku, loc, **extra):
            return dict(SKUCode=sku, WhCode=loc, ParentWhCode="P", WhType="dist",
                        ParentWhType="cwh", Norm=3, Age=2,
                        **{f"D{i}": "Black" if i == 90 else None for i in range(1, 91)},
                        **{colour + "Count": 0 for colour in ("White", "Blue", "Green", "Yellow", "Red", "Black")},
                        **extra)
        tech = trend("Sku", "Loc ")
        state = {"BufferTrendReport": [tech], "BufferTrendReportEcon": [trend("SKU ", "loc")],
                 "BufferTrendDispatch": [trend("sku", "LOC ")],
                 "BufferTrendPhysicalInv": [trend("sKu", "lOc")],
                 "BPPTrendTech": [], "BPPTrendEcon": [], "BPPTrendDispatch": [],
                 "BPPTrendPhysicalInv": []}
        snapshot = _snapshot(state)["BTRSnapshotForUI"]
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot[0]["SKUCode"], "Sku")
        self.assertEqual(snapshot[0]["TodayColorPhysicalInv"], "Black")

        category_state = {"BTRSnapshotForUI": [dict(snapshot[0], TodayColorDispatch="Black",
                          AgeDispatch=2, TodayColorPhysicalInv="Black", AgePhysicalInv=2)],
                          "BufferTrendPhysicalInv": [dict(SKUCode="sku", WhCode="LOC ", BRAge=2)]}
        facts = {"SKULocStandardAttributes": [dict(SKUCode="Sku ", WhCode="Loc", Category=None)],
                 "MasterData": [dict(SKUCode="SKU", WhCode="loc ", RLT=1)],
                 "DailyConsumption": [], "GoodsInTransitTransporterMaster": [], "Suggestions": []}
        selected = {"up": set(), "down": set()}
        categorized = _categories(TODAY, category_state, facts, selected)["SKULocStandardAttributes"]
        self.assertEqual(categorized[0]["Category"], "1|2|3")
        self.assertEqual((categorized[0]["SKUCode"], categorized[0]["WhCode"]), ("Sku ", "Loc"))
        with self.assertRaisesRegex(ValueError, "SOURCE_ORDER_AMBIGUITY"):
            _unique_source([dict(SKUCode="A", WhCode="W", RLT=1),
                            dict(SKUCode="a ", WhCode="w ", RLT=2)],
                           lambda row: join_key(row["SKUCode"], row["WhCode"]), ("RLT",), "master")


if __name__ == "__main__":
    unittest.main()
