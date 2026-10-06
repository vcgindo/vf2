from collections import Counter
from datetime import date, datetime
from decimal import Decimal
import json
import unittest

from mta.application.daily_transit import (
    TRANSIT_FIELDS, TRANSPORTER_FIELDS, transporter_master,
    validate_goods_in_transit,
)


def bag(rows):
    return Counter(json.dumps(row, sort_keys=True, default=str) for row in rows)


class DailyTransitTests(unittest.TestCase):
    def test_raw_join_trims_sql_spaces_but_preserves_tabs(self):
        result = validate_goods_in_transit(
            [self.raw(SKUCode='\tA\t'), self.raw(SKUCode=' A ')],
            [{'SKUCode': 'A', 'WhCode': 'L1', 'SLT': 2}],
            date(2026, 6, 6), datetime(2026, 6, 6))
        self.assertEqual([row['SKUCode'] for row in result['rows']], [' A '])

    def raw(self, **changes):
        row = dict(SKUCode=" A ", ToLocationCode=" L1 ", FromLocationCode="P1",
            CurrentLocationCode=None, LRCode="LR1", OrderNo="O1",
            CreationDate=date(2026, 6, 1), GateOutDate=date(2026, 6, 3),
            InTransitQty=5, TransporterCode="T1", Remark=None,
            ReportDate=date(2026, 6, 6))
        row.update(changes)
        return row

    def test_validation_deletes_only_all_three_null_and_keeps_negative_with_diagnostic(self):
        deleted = self.raw(SKUCode=None, ToLocationCode=None, FromLocationCode=None,
                           InTransitQty=-9)
        negative = self.raw(SKUCode="B", ToLocationCode="L2", FromLocationCode=None,
                            InTransitQty=-3, OrderNo="O2")
        partial_null = self.raw(SKUCode=None, ToLocationCode="L1", FromLocationCode="P1")
        standards = [
            {"SKUCode": "A", "WhCode": "L1", "SLT": 2},
            {"SKUCode": "A", "WhCode": "L1", "SLT": 3},
            {"SKUCode": "B", "WhCode": "L2", "SLT": None},
        ]
        stamp = datetime(2026, 6, 6, 2, 3, 4)
        result = validate_goods_in_transit(
            [deleted, self.raw(), partial_null, negative], standards,
            date(2026, 6, 6), stamp)
        self.assertEqual(len(result["rows"]), 3)  # duplicate join plus negative
        duplicate = [row for row in result["rows"] if row["OrderNo"] == "O1"]
        self.assertEqual(len(duplicate), 2)
        self.assertTrue(all(row["SKUCode"] == " A " and row["WhCode"] == " L1 "
                            for row in duplicate))  # source spelling is retained
        self.assertTrue(all(row["Ageing"] == 5 and row["TLT"] == 3
                            for row in duplicate))
        self.assertEqual({(row["SLT"], row["ETA"]) for row in duplicate}, {
            (2, date(2026, 6, 3)), (3, date(2026, 6, 4)),
        })
        kept_negative = next(row for row in result["rows"] if row["OrderNo"] == "O2")
        self.assertEqual(kept_negative["InTransitQty"], -3)
        self.assertIsNone(kept_negative["ETA"])
        self.assertEqual(result["diagnostics"], [{
            "SKUCode": "B", "WhCode": "L2", "RejectionDate": stamp,
            "ReasonCode": -166,
            "ReasonDescription": "negative Qty in GoodsInTransit Data file/table",
        }])

    def transit(self, sku, wh, parent, lr, order, tlt, slt):
        return dict(SKUCode=sku, WhCode=wh, ParentWhCode=parent,
            CurrentLocationCode=None, LRCode=lr, OrderNo=order,
            CreationDate=date(2026, 6, 1), GateOutDate=date(2026, 6, 2),
            InTransitQty=2, TransporterCode="T1", Ageing=5,
            ETA=date(2026, 6, 3), TLT=tlt, SLT=slt, Remark=None,
            ReportDate=date(2026, 6, 6))

    def test_transporter_join_multiplicity_and_lr_sku_precedence(self):
        transit = [
            self.transit("A", "P1", "ROOT", "LR-X", "PARENT", 1, 2),
            self.transit("A", "L1", "P1", "LR-X", "SUPER", 4, 2),
            self.transit("A", "L2", "P1", "LR-Y", "DELAY", 3, 2),
            self.transit("A", "L3", "P1", None, "ONTIME", 1, 2),
        ]
        directory = [
            {"TransporterCode": "T1", "TransporterName": "Carrier", "TransporterContact": None},
            {"TransporterCode": "T1", "TransporterName": "Carrier", "TransporterContact": None},
        ]
        reports = [{"SKUCode": row["SKUCode"], "WhCode": row["WhCode"],
                    "ParentWhCode": row["ParentWhCode"], "GIT": 1,
                    "PhysicalInventoryPen": Decimal("1.25"),
                    "PhysicalInventoryColor": "Black", "DispatchColor": "Red"}
                   for row in transit]
        standards = [{"SKUCode": "A", "WhCode": wh, "Price": Decimal("12.9")}
                     for wh in ("P1", "L1", "L2", "L3")]
        rows = transporter_master(transit, directory, reports, standards, Decimal("1.5"))
        self.assertEqual(len(rows), 8)  # duplicate directory row remains a duplicate join
        self.assertTrue(all(set(row) == set(TRANSPORTER_FIELDS) for row in rows))
        by_order = {}
        for row in rows:
            by_order.setdefault(row["OrderNo"], row)
        self.assertTrue(by_order["PARENT"]["IsParent"])
        self.assertEqual(by_order["PARENT"]["TruckStatus"], "SuperDelay")
        self.assertEqual(by_order["SUPER"]["TruckStatus"], "SuperDelay")
        self.assertEqual(by_order["DELAY"]["TruckStatus"], "Delay")
        self.assertIsNone(by_order["ONTIME"]["TruckStatus"])
        # Exact deployed statement order: the later delayed-SKU UPDATE
        # overwrites the prior super-delayed-SKU assignment.
        self.assertTrue(all(row["SKUStatus"] == "Delay" for row in rows))
        self.assertTrue(all(row["Price"] == 12 for row in rows))
        self.assertEqual(bag(rows), bag([row for row in rows]))

    def test_missing_and_ambiguous_scalar_facts_fail_without_defaults(self):
        with self.assertRaisesRegex(ValueError, 'native int range'):
            validate_goods_in_transit([self.raw(InTransitQty=2**31)], [],
                                      date(2026, 6, 6), datetime(2026, 6, 6))
        with self.assertRaisesRegex(ValueError, "complete fields"):
            validate_goods_in_transit([{"SKUCode": "A"}], [], date(2026, 6, 6),
                                      datetime(2026, 6, 6))
        with self.assertRaisesRegex(ValueError, "SuperDelayFactor"):
            transporter_master([], [], [], [], None)
        self.assertEqual(set(TRANSIT_FIELDS), {
            "SKUCode", "WhCode", "ParentWhCode", "CurrentLocationCode", "LRCode",
            "OrderNo", "CreationDate", "GateOutDate", "InTransitQty", "TransporterCode",
            "Ageing", "ETA", "TLT", "SLT", "Remark", "ReportDate",
        })


if __name__ == "__main__":
    unittest.main()
