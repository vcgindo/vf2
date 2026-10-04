"""Exact compatibility checks for the opt-in BTR display presenter."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import re
import subprocess
import unittest
from unittest.mock import patch

os.environ.setdefault("VF_SECRET_KEY", "unit-only")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vectorflow.settings")
import django

django.setup()
from django.test import Client

from mta.presentation.btr_display import display_horizon, prepare_display


ROOT = Path(__file__).resolve().parents[1]
MAPPER = ROOT / "frontend/src/helpers/utils.ts"
IDENTITY = {"HTTP_X_VECTORFLOW_IDENTITY": '{"id":"btr-display-test"}'}


def node_mapper(cases):
    """Execute the retained TypeScript mapper body as JavaScript in Node."""
    source = MAPPER.read_text(encoding="utf-8")
    start = source.index("export const mapBTRRowData =")
    end = source.index("export const mapBTRRowDataToColDefs", start)
    mapper = source[start:end]
    mapper, replacements = re.subn(
        r"export const mapBTRRowData = \(rows: Array<any>, horizon: number\): Array<any> =>",
        "const mapBTRRowData = (rows, horizon) =>",
        mapper,
        count=1,
    )
    if replacements != 1 or "{} as any" not in mapper:
        raise AssertionError("retained mapBTRRowData source no longer matches the bounded transpiler")
    mapper = mapper.replace("{} as any", "{}", 1)
    script = """
const fs = require('fs');
%s
const cases = JSON.parse(fs.readFileSync(0, 'utf8'));
const output = cases.map(({rows, horizon}) => {
  const mapped = mapBTRRowData(rows, horizon);
  const descriptors = [];
  mapped.forEach((row, rowIndex) => Object.keys(row).forEach(field => {
    const value = row[field];
    if (typeof value === 'number' && !Number.isFinite(value)) {
      descriptors.push(['tech', rowIndex, field,
        Number.isNaN(value) ? 'NaN' : value > 0 ? 'Infinity' : '-Infinity']);
      row[field] = null;
    }
  }));
  return {rows: mapped, descriptors};
});
process.stdout.write(JSON.stringify(output));
""" % mapper
    completed = subprocess.run(
        ["node", "-e", script], input=json.dumps(cases), text=True,
        capture_output=True, check=True, encoding="utf-8",
    )
    return json.loads(completed.stdout)


class BtrDisplayTests(unittest.TestCase):
    @staticmethod
    def rows():
        first = {
            "SKUCode": "001", "SKUDescription": "123 product\u00a0", "Whcode": "002",
            "WhCode": "003", "LocationName": "004 location", "pc": "005", "pn": "006 parent",
            "Source": "12tech", "Category": "7BR", "Tags": None, "Availability": "stale",
            "D90": "99.9tail", "D89": "100tail", "D88": "", "D87": None,
            "D86": "Infinity", "D85": "-Infinity", "D84": "NaN", "D83": "0x10",
            "D82": "1e21", "D81": "1e-7", "D80": "-1e21",
            "D79": "  +12.5e1junk", "D78": ".5", "D77": "1e",
            "D76": "\ufeff-0", "D75": "  .", "CD90": "3Green",
        }
        second = {"SKUCode": None, "WhCode": "W", **{f"D{i}": "" for i in range(1, 91)}}
        third = {"SKUCode": "round", "WhCode": "W", "D90": "1", "D89": "100", "D88": "100"}
        return [first, second, third]

    def test_every_horizon_matches_actual_retained_javascript_mapper(self):
        cases = [{"rows": deepcopy(self.rows()), "horizon": horizon} for horizon in range(1, 91)]
        expected = node_mapper(cases)
        actual = []
        for case in cases:
            result = prepare_display({"tech": case["rows"], "labels": []}, case["horizon"])
            actual.append({"rows": result["tech"], "descriptors": result["displayNonFinite"]})
        self.assertEqual(actual, expected)

    def test_marker_descriptors_and_missing_fields_are_sparse(self):
        result = prepare_display({"eco": [{"SKUCode": "S", "WhCode": "W", "D90": "Infinity"}]}, 1)
        self.assertTrue(result["displayPrepared"])
        self.assertEqual(result["eco"][0]["D90"], None)
        self.assertEqual(result["displayNonFinite"], [["eco", 0, "D90", "Infinity"]])
        self.assertEqual(result["eco"][0]["Availability"], 0.0)
        self.assertNotIn("D89", result["eco"][0])

    def test_opt_in_validation_is_strict(self):
        self.assertIsNone(display_horizon({}))
        self.assertIsNone(display_horizon({"displayPrepared": False, "displayHorizon": 0}))
        for value in (1, 90):
            self.assertEqual(display_horizon({"displayPrepared": True, "displayHorizon": value}), value)
        for value in (None, True, 0, 91, 1.0, "90"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                display_horizon({"displayPrepared": True, "displayHorizon": value})

    def test_route_preserves_raw_default_and_count_then_prepares_opt_in_grid(self):
        client = Client()
        raw = {"tech": [{"SKUCode": "001", "WhCode": "W", "D90": "1"}], "labels": [{"D90": "date"}]}
        payload = {"name": "tech", "paginationParameter": {"pageNumber": 1, "recordsPerPage": 50}}

        with patch("mta.presentation.views.selected_run", return_value="run"), \
             patch("mta.presentation.btr_sql.read_btr", side_effect=lambda *a, **k: deepcopy(raw)) as read:
            response = client.post("/api/mta/GetBTRData", payload, content_type="application/json", **IDENTITY)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["data"], raw)
            read.assert_called_once_with("run", payload, paging=(1, 50), count=False)

        prepared = {**payload, "displayPrepared": True, "displayHorizon": 1}
        with patch("mta.presentation.views.selected_run", return_value="run"), \
             patch("mta.presentation.btr_sql.read_btr", return_value=deepcopy(raw)):
            data = client.post("/api/mta/GetBTRData", prepared, content_type="application/json", **IDENTITY).json()["data"]
        self.assertTrue(data["displayPrepared"])
        self.assertEqual(data["tech"][0]["Availability"], 100.0)
        self.assertEqual(data["tech"][0]["D90"], 1.0)

        count_payload = {**payload, "displayPrepared": True, "displayHorizon": "ignored-for-count"}
        counts = {"TechCount": "7", "EcoCount": "8"}
        with patch("mta.presentation.views.selected_run", return_value="run"), \
             patch("mta.presentation.btr_sql.read_btr", return_value=counts) as read:
            response = client.post("/api/mta/GetBTRDataCount", count_payload,
                                   content_type="application/json", **IDENTITY)
            self.assertEqual(response.json()["data"], counts)
            read.assert_called_once_with("run", count_payload, paging=(1, 50), count=True)

    def test_invalid_opt_in_horizon_fails_before_reader(self):
        client = Client()
        payload = {"displayPrepared": True, "displayHorizon": 0,
                   "paginationParameter": {"pageNumber": 1, "recordsPerPage": 50}}
        with patch("mta.presentation.views.selected_run") as selected, \
             patch("mta.presentation.btr_sql.read_btr") as read:
            response = client.post("/api/mta/GetBTRData", payload,
                                   content_type="application/json", **IDENTITY)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "displayHorizon_must_be_an_integer_from_1_to_90")
        selected.assert_not_called()
        read.assert_not_called()


if __name__ == "__main__":
    unittest.main()
