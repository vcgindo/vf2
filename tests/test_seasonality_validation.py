import unittest

from mta.application.seasonality_validation import validate_seasonality_data


RUN_TIMESTAMP = "2026-10-09T10:11:12"


def season(
    sku,
    wh="W1",
    *,
    approved=1,
    start="2026-06-06",
    end="2026-06-16",
    target=5,
    delta=None,
    buildup=5,
):
    return {
        "SKUCode": sku,
        "WhCode": wh,
        "StartDate": start,
        "EndDate": end,
        "TargetNorm": target,
        "DeltaNormPercentage": delta,
        "BuildupDuration": buildup,
        "Approved": approved,
    }


def master(sku, wh="W1", *, norm=10, rlt=4):
    return {"SKUCode": sku, "WhCode": wh, "Norm": norm, "RLT": rlt}


class SeasonalityValidationTests(unittest.TestCase):
    def test_no_approved_row_returns_before_all_validation(self):
        rows = [season("DUP", approved=0), season("DUP", approved=0)]
        prior = [
            {
                "SKUCode": "OLD",
                "WhCode": "W1",
                "RejectionDate": "2026-10-08T00:00:00",
                "ReasonCode": 100,
                "ReasonDescription": "existing",
            }
        ]

        result = validate_seasonality_data(rows, [], prior, RUN_TIMESTAMP)

        self.assertEqual(result["outcome"], "EARLY_RETURN")
        self.assertEqual(result["seasonality"], rows)
        self.assertEqual(result["rejected_master"], prior)
        self.assertEqual(result["rejections_added"], 0)
        self.assertEqual(
            result["stages"],
            ("clear_all:before", "approved_gate", "early_return"),
        )
        self.assertTrue(all(not value for value in result["scratch"].values()))

    def test_any_approved_row_enables_unqualified_validation_and_stage_order(self):
        rows = [
            season("DUP", approved=1),
            season("DUP", approved=0),
            season("MISSING", approved=0),
            season("GOOD", approved=0),
        ]

        result = validate_seasonality_data(
            rows, [master("GOOD")], [], RUN_TIMESTAMP
        )

        self.assertEqual(result["outcome"], "VALIDATED")
        self.assertEqual([row["SKUCode"] for row in result["seasonality"]], ["GOOD"])
        self.assertEqual(
            [row["ReasonCode"] for row in result["rejected_master"]], [201, 202]
        )
        self.assertEqual(result["rejected_master"][0]["SKUCode"], "DUP")
        self.assertEqual(result["rejected_master"][1]["SKUCode"], "MISSING")
        self.assertLess(
            result["stages"].index("reject:201"),
            result["stages"].index("reject:202"),
        )
        self.assertEqual(result["stages"][-1], "clear_all:after")
        self.assertTrue(all(not value for value in result["scratch"].values()))

    def test_nulls_group_as_duplicates_but_do_not_join_for_deletion(self):
        rows = [
            season("APPROVED", approved=1),
            season(None, approved=0),
            season(None, approved=0),
        ]

        result = validate_seasonality_data(
            rows, [master("APPROVED")], [], RUN_TIMESTAMP
        )

        self.assertEqual(
            [row["ReasonCode"] for row in result["rejected_master"]],
            [201, 202, 202],
        )
        self.assertEqual(
            [row["SKUCode"] for row in result["seasonality"]],
            ["APPROVED", None, None],
        )
        self.assertEqual(result["rejections_added"], 3)

    def test_lower_norm_rejections_follow_204_205_206_sequence(self):
        rows = [
            season("NO_BUILDUP", buildup=None),
            season("TOO_LONG", end="2026-06-08", buildup=3),
            season("UNDER_RLT", end="2026-06-20", buildup=3),
            season("NO_END", end=None, buildup=None),
            season("NULL_COMPARE", target=None, delta=None, buildup=None),
        ]
        masters = [
            master("NO_BUILDUP", rlt=4),
            master("TOO_LONG", rlt=9),
            master("UNDER_RLT", rlt=4),
            master("NO_END", rlt=4),
            master("NULL_COMPARE", rlt=4),
        ]

        result = validate_seasonality_data(rows, masters, [], RUN_TIMESTAMP)

        self.assertEqual(
            [row["ReasonCode"] for row in result["rejected_master"]],
            [204, 205, 206],
        )
        self.assertEqual(
            [row["SKUCode"] for row in result["seasonality"]],
            ["NO_END", "NULL_COMPARE"],
        )
        self.assertEqual(
            result["rejected_master"][0]["ReasonDescription"],
            "Buildup duration is not provided. (Lower Norm during Season type)",
        )
        self.assertEqual(
            result["rejected_master"][1]["ReasonDescription"],
            "Buildup duration is larger than Season duration. Buildup Dur=3, "
            "Season Dur=2",
        )
        self.assertEqual(
            result["rejected_master"][2]["ReasonDescription"],
            "Buildup duration is smaller than RLT. RLT=4, Buildup Dur=3",
        )
        self.assertEqual(
            [
                stage
                for stage in result["stages"]
                if stage in ("reject:204", "reject:205", "reject:206")
            ],
            ["reject:204", "reject:205", "reject:206"],
        )


if __name__ == "__main__":
    unittest.main()
