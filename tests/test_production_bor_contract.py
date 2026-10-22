from copy import deepcopy
from decimal import Decimal
import unittest
from unittest.mock import patch

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
        for name in ("Red", "Yellow", "Green", "Blue", "White", "Grey"):
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

    def test_all_seven_real_producer_bands_have_independent_complete_outputs(self):
        from mta.domain.colours import colour as calculate_colour
        cases = ((100, 0, 0, 'BLACK'), (100, 20, 0, 'RED'),
                 (100, 50, 0, 'YELLOW'), (100, 80, 0, 'GREEN'),
                 (100, 110, 20, 'BLUE'), (100, 130, 20, 'WHITE'),
                 (0, 0, 0, 'GREY'))
        for norm, stock, blue, band in cases:
            with self.subTest(band=band):
                actual = calculate_colour(Decimal(norm), Decimal(stock), Decimal(blue))
                self.assertEqual(actual.band, band)
                source, colours = [supplier()], [colour(actual.band)]
                before = deepcopy((source, colours))
                expected = dict(source[0], ReqTopOfBlack=7 if band == 'BLACK' else 0,
                    ReqTopOfRed=0 if band == 'BLACK' else 7, CumulativeTOBlack=7 if band == 'BLACK' else 0)
                expected = {name: expected[name] for name in OUTPUT_FIELDS}
                self.assertEqual(produce(supplier_dispatch_rows=source,
                    dispatch_colours=colours, policy=POLICY), [expected])
                self.assertEqual((source, colours), before)

    def test_extra_grey_node_and_empty_supplier_population_are_valid(self):
        colours = [colour('gReY ', SKUCode='EXTRA', WHCode='CHILD'), colour()]
        self.assertEqual(produce(supplier_dispatch_rows=[], dispatch_colours=colours, policy=POLICY), [])
        self.assertEqual(produce(supplier_dispatch_rows=[supplier(), supplier(SupplierCode='OTHER')],
            dispatch_colours=colours, policy=POLICY)[1]['SupplierCode'], 'OTHER')

    def test_full_validation_precedes_duplicate_detection_and_context_is_actionable(self):
        with self.assertRaisesRegex(ValueError, "Canonical.*colour ordinal=3.*Purple"):
            produce(supplier_dispatch_rows=[supplier()],
                dispatch_colours=[colour(), colour(), colour('Purple')], policy=POLICY)
        with self.assertRaisesRegex(ValueError, "text.*colour ordinal=1.*None"):
            produce(supplier_dispatch_rows=[], dispatch_colours=[colour(None)], policy=POLICY)
        with self.assertRaisesRegex(ValueError, "Ambiguous.*colour ordinal=2"):
            produce(supplier_dispatch_rows=[], dispatch_colours=[colour(),
                colour('Grey', SKUCode='sku-1 ', WHCode='top ')], policy=POLICY)
        with self.assertRaisesRegex(ValueError, "Missing.*supplier ordinal=1.*SKU-1"):
            produce(supplier_dispatch_rows=[supplier()], dispatch_colours=[], policy=POLICY)

    def test_unqualified_keys_keep_original_comparison_denial_and_overflow_fails(self):
        with self.assertRaisesRegex(ValueError, 'UNQUALIFIED_SCALAR_DOMAIN'):
            produce(supplier_dispatch_rows=[supplier()],
                dispatch_colours=[colour(SKUCode='é')], policy=POLICY)
        for changes in ({'ReqTopOfRed': 2147483648},
                        {'ReqTopOfRed': 2147483647, 'ReqTopOfYellow': 1}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'overflows'):
                produce(supplier_dispatch_rows=[supplier(**changes)], dispatch_colours=[colour()], policy=POLICY)

    def test_lookup_candidate_work_grows_linearly_and_handles_full_workload_shape(self):
        from mta.application import production_bor_contract as module
        original = module._same_pair
        for count in (256, 512, 1024, 97097):
            colours = [colour('GREY' if i % 7 == 0 else 'Black', SKUCode=f'SKU-{i}') for i in range(count)]
            sources = [supplier(SKUCode=f'SKU-{i}') for i in range(count if count < 97097 else 1)]
            with self.subTest(count=count), patch.object(module, '_same_pair', wraps=original) as same:
                result = produce(supplier_dispatch_rows=sources, dispatch_colours=colours, policy=POLICY)
                self.assertEqual(same.call_count, len(sources))
                self.assertEqual(len(result), len(sources))
                self.assertEqual(result[0]['ReqTopOfBlack'], 0)

    def test_real_expanded_report_projection_accepts_producer_grey(self):
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
        import django
        django.setup()
        from mta.presentation.production_reports import current
        from mta.application import production_output_policy as policy
        from mta.domain.colours import colour as calculate_colour
        capabilities = [dict(capability=name, rows=[]) for name in (
            'r1_requirement_band', 'r1_advance_stock_allocation', 'r1_allocated_orders')]
        cases = ((100,0,0,'BLACK'),(100,20,0,'RED'),(100,50,0,'YELLOW'),
                 (100,80,0,'GREEN'),(100,110,20,'BLUE'),(100,130,20,'WHITE'),(0,0,0,'GREY'))
        rows = []
        for index,(norm,stock,blue,band) in enumerate(cases):
            produced = calculate_colour(Decimal(norm),Decimal(stock),Decimal(blue)).band
            self.assertEqual(produced,band)
            rows.append(dict(sku_code=f'SKU-{index}',location_code='TOP',colours={'dispatch':{'band':produced}}))
        capabilities.append(dict(capability='r1_requirement', rows=rows))
        output = dict(CalculationOutputs=capabilities,
            ClosingState=[dict(bpr={'BPRMaster': []}, complete={'SupplierDispatchReq': [supplier(SKUCode=f'SKU-{i}') for i in range(7)]})],
            BPRFinal=[dict(vf_RationedReqReport=[], BPR_Table=[])])
        opening = dict(supplier=dict(SOBData=[], MOQData=[]),
            production_report_schema=policy.SOURCE_SCHEMA,
            production_report_policy={'output_contract': policy.contract()})
        before = deepcopy((output, opening))
        result = current(output, opening)
        self.assertEqual(tuple(result['SupplierDispatchReq'][0]), OUTPUT_FIELDS)
        self.assertEqual([(row['ReqTopOfBlack'],row['ReqTopOfRed']) for row in result['SupplierDispatchReq']],
                         [(7,0)]+[(0,7)]*6)
        self.assertEqual((output, opening), before)


if __name__ == "__main__":
    unittest.main()
