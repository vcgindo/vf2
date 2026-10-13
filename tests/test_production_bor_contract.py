from copy import deepcopy
import unittest

from mta.application.production_bor_contract import (
    COLOUR_FIELDS, INPUT_FIELDS, OUTPUT_FIELDS, POLICY, produce,
)
from mta.presentation.bor_contract import FIELDS as BOR_FIELDS


def supplier(**changes):
    row = dict(
        SKUCode="SKU-1", WHCode="TOP", SupplierCode="SUP",
        OriginalReq=17, DispatchReq=17,
        ReqTopOfRed=7, ReqTopOfYellow=5, ReqTopOfGreen=3, ReqTopOfBlue=2,
        **{f"SKULocAtt{i:02}": None for i in range(1, 16)},
        CumulativeTOR=7, CumulativeTOY=12, CumulativeTOG=15, CumulativeTOB=17,
    )
    row.update(changes)
    return row


def colour(name="Black", **changes):
    row = dict(SKUCode="SKU-1", WHCode="TOP", DispatchColor=name)
    row.update(changes)
    return row


class ProductionBorContractTests(unittest.TestCase):
    def test_black_moves_red_only_and_rebuilds_all_cumulatives(self):
        rows = [supplier()]
        colours = [colour()]
        before = deepcopy((rows, colours))

        result = produce(supplier_dispatch_rows=rows, dispatch_colours=colours, policy=POLICY)

        self.assertEqual(tuple(result[0]), OUTPUT_FIELDS)
        self.assertEqual(OUTPUT_FIELDS, tuple(BOR_FIELDS["SupplierDispatchReq"]))
        self.assertEqual(len(result[0]), 30)
        self.assertEqual(
            tuple(result[0][field] for field in (
                "ReqTopOfBlack", "ReqTopOfRed", "ReqTopOfYellow",
                "ReqTopOfGreen", "ReqTopOfBlue")),
            (7, 0, 5, 3, 2),
        )
        self.assertEqual(
            tuple(result[0][field] for field in (
                "CumulativeTOBlack", "CumulativeTOR", "CumulativeTOY",
                "CumulativeTOG", "CumulativeTOB")),
            (7, 7, 12, 15, 17),
        )
        self.assertEqual(result[0]["DispatchReq"], 17)
        self.assertEqual(sum(result[0][field] for field in (
            "ReqTopOfBlack", "ReqTopOfRed", "ReqTopOfYellow",
            "ReqTopOfGreen", "ReqTopOfBlue")), result[0]["DispatchReq"])
        self.assertEqual((rows, colours), before)

    def test_every_nonblack_colour_retains_red_and_zeroes_black(self):
        for name in ("Red", "Yellow", "Green", "Blue", "White"):
            with self.subTest(name=name):
                result = produce(
                    supplier_dispatch_rows=[supplier()],
                    dispatch_colours=[colour(name)], policy=POLICY,
                )[0]
                self.assertEqual(
                    tuple(result[field] for field in (
                        "ReqTopOfBlack", "ReqTopOfRed", "CumulativeTOBlack",
                        "CumulativeTOR", "CumulativeTOY", "CumulativeTOG",
                        "CumulativeTOB", "DispatchReq")),
                    (0, 7, 0, 7, 12, 15, 17, 17),
                )

    def test_preserves_row_order_multiplicity_and_all_nonband_values(self):
        first = supplier(SupplierCode="A", SKULocAtt04="first")
        second = supplier(SupplierCode="B", SKULocAtt04="second")
        extra = colour("Green", SKUCode="SKU-2", WHCode="CHILD")
        result = produce(
            supplier_dispatch_rows=[first, second],
            dispatch_colours=[extra, colour("Black")], policy=POLICY,
        )
        self.assertEqual([row["SupplierCode"] for row in result], ["A", "B"])
        self.assertEqual([row["SKULocAtt04"] for row in result], ["first", "second"])
        self.assertEqual([row["ReqTopOfBlack"] for row in result], [7, 7])

    def test_requires_explicit_policy_and_complete_typed_sources(self):
        with self.assertRaisesRegex(ValueError, "policy"):
            produce(supplier_dispatch_rows=[supplier()], dispatch_colours=[colour()], policy="legacy")
        with self.assertRaisesRegex(ValueError, "28-field"):
            produce(supplier_dispatch_rows=[dict(supplier(), unexpected=1)],
                    dispatch_colours=[colour()], policy=POLICY)
        with self.assertRaisesRegex(ValueError, "SQL int"):
            produce(supplier_dispatch_rows=[supplier(ReqTopOfRed="1.5")],
                    dispatch_colours=[colour()], policy=POLICY)
        self.assertEqual(tuple(colour()), COLOUR_FIELDS)
        self.assertEqual(tuple(supplier()), INPUT_FIELDS)

    def test_denies_missing_ambiguous_and_unknown_colour(self):
        with self.assertRaisesRegex(ValueError, "Missing or ambiguous"):
            produce(supplier_dispatch_rows=[supplier()], dispatch_colours=[], policy=POLICY)
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            produce(supplier_dispatch_rows=[supplier()],
                    dispatch_colours=[colour(), colour()], policy=POLICY)
        with self.assertRaisesRegex(ValueError, "Canonical"):
            produce(supplier_dispatch_rows=[supplier()],
                    dispatch_colours=[colour("Purple")], policy=POLICY)

    def test_sql_ascii_key_and_colour_semantics(self):
        result = produce(
            supplier_dispatch_rows=[supplier(SKUCode="sku-1 ", WHCode="top  ", OriginalReq="17")],
            dispatch_colours=[colour("black ")], policy=POLICY,
        )[0]
        self.assertEqual((result["ReqTopOfBlack"], result["ReqTopOfRed"]), (7, 0))
        self.assertIs(type(result["OriginalReq"]), int)


if __name__ == "__main__":
    unittest.main()
