from collections import Counter
from datetime import date
from decimal import Decimal
import json
import unittest

from mta.application.daily_nms_snapshot import (
    LOCATION_FIELDS, MASTER_FIELDS, NMS_FIELDS, SKU_FIELDS, SKULOC_FIELDS,
    NmsSnapshotAmbiguity, create_snapshot,
)


def bag(rows):
    return Counter(json.dumps(row, sort_keys=True, default=str) for row in rows)


def values(fields, **changes):
    row = dict.fromkeys(fields)
    row.update(changes)
    return row


class DailyNmsSnapshotTests(unittest.TestCase):
    def sources(self):
        master = values(MASTER_FIELDS, SKUCode="SKU", WhCode="LOC", Norm=4,
            MinNorm=1, RLT=2, RCP=3, GCP=4, OCP=None, MinOrderCount=5,
            ParentWhCode="PARENT", SKUIntroDate=date(2025, 1, 1))
        dbm = dict(master, SKUIntroDate=date(2026, 1, 1))
        pair = values(SKULOC_FIELDS, SKUCode="SKU", LocCode="LOC", PackSize=6,
            SpikeThreshold=Decimal("1.25"), PSOThreshold=None, FGRMFlag=None,
            StockPercentForRationing=90, NormPercentReservation=10, NonNMS=False,
            **{"c%d" % i: "pair-%d" % i for i in range(1, 16)})
        sku = values(SKU_FIELDS, SKUCode="SKU", ElephantOrderCapping=None,
            Weight=Decimal("2.500"), Volume=None,
            **{"SL%d" % i: "sl-%d" % i for i in range(1, 6)},
            **{"c%d" % i: "sku-%d" % i for i in range(1, 16)})
        location = values(LOCATION_FIELDS, WHCode="LOC", LocationType=None,
            LogisticsLocation="Y", **{"LL%d" % i: "ll-%d" % i for i in range(1, 6)},
            **{"c%d" % i: "loc-%d" % i for i in range(1, 16)})
        return dict(master_data=[master], dbm_master=[dbm],
            skuloc_attributes=[pair], sku_descriptions=[{
                "SKUCode": "SKU", "SKUDescription": "Product"}],
            site_descriptions=[{"WHCode": "LOC", "WHDescription": "Location"},
                               {"WHCode": "PARENT", "WHDescription": "Parent"}],
            exclusions=[], sku_attributes=[sku], location_attributes=[location])

    def test_inactive_returns_existing_bags_without_reading_unrelated_sources(self):
        master = [{"unvalidated": "master"}]
        prior = [{"unvalidated": "snapshot"}]
        result = create_snapshot(nms_active=False, master_data=master,
            dbm_master=None, skuloc_attributes=None, sku_descriptions=None,
            site_descriptions=None, exclusions=None, sku_attributes=None,
            location_attributes=None, nms_all_items=prior)
        self.assertEqual(result, {"MasterData": master, "NMSAllItems": prior})
        self.assertIsNot(result["MasterData"], master)
        with self.assertRaisesRegex(ValueError, "NMSActive"):
            create_snapshot(nms_active=1, master_data=[], dbm_master=[],
                skuloc_attributes=[], sku_descriptions=[], site_descriptions=[],
                exclusions=[], sku_attributes=[], location_attributes=[])

    def test_intro_date_null_comparison_and_ambiguous_update(self):
        source = self.sources()
        source["master_data"][0]["SKUIntroDate"] = None
        result = create_snapshot(nms_active=True, **source)
        self.assertIsNone(result["MasterData"][0]["SKUIntroDate"])
        self.assertIsNone(result["NMSAllItems"][0]["SKUIntroDate"])

        source = self.sources()
        source["dbm_master"].append(dict(source["dbm_master"][0],
                                         SKUIntroDate=date(2027, 1, 1)))
        with self.assertRaisesRegex(NmsSnapshotAmbiguity, "no source winner"):
            create_snapshot(nms_active=True, **source)

    def test_full_shape_join_multiplicity_exclusion_and_non_nms_filter(self):
        source = self.sources()
        source["sku_descriptions"].append(dict(source["sku_descriptions"][0]))
        source["exclusions"] = [{"SKUCode": "sku ", "WhCode": "loc"},
                                {"SKUCode": "SKU", "WhCode": "LOC"}]
        source["skuloc_attributes"].append(dict(source["skuloc_attributes"][0],
                                                 NonNMS=True, PackSize=999))
        result = create_snapshot(nms_active=True, **source)
        self.assertEqual(result["MasterData"][0]["SKUIntroDate"], date(2026, 1, 1))
        self.assertEqual(len(result["NMSAllItems"]), 4)
        self.assertTrue(all(tuple(row) == NMS_FIELDS for row in result["NMSAllItems"]))
        self.assertTrue(all(row["DBMActive"] is False and row["PackSize"] == 6
                            for row in result["NMSAllItems"]))
        self.assertEqual(len(bag(result["NMSAllItems"])), 1)
        self.assertEqual(len(NMS_FIELDS), 83)


if __name__ == "__main__":
    unittest.main()
