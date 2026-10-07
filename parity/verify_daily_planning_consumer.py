"""Independent Planning consumer proof for the accepted 7 June 3006 run.

``export`` runs read-only against the owned PostgreSQL stack and emits the
complete typed source bags plus modern reader responses.  ``compare`` binds
those bags to connection-local SQL Server tables and executes only extracted
deployed consumer SELECTs.  It never invokes a calculation or writes either
database.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
from uuid import UUID
import inspect
import gzip
import hashlib
import subprocess
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


RUN = "17f0eb84-7b6d-40e9-a288-9441a4d7a860"
OUTPUT = "e9777b060d27a77584fcc20734e5f1daba7fab38f8e1eaf99bec907cc278233f"
SCOPES = {
    "broad": ([71001], [72001]),
    "restricted": ([71003], [72003]),
}


def wire(value):
    if isinstance(value, (date, datetime, Decimal, UUID)):
        return str(value)
    raise TypeError(type(value).__name__)


def export():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "vectorflow.settings")
    import django
    django.setup()
    from django.db import connection
    from mta.presentation.daily_planning.dispatch import read
    from mta.presentation.daily_planning_extension import require
    from mta.presentation.selective import image_rows
    from mta.runtime.models import (
        CalculationRun, ExcessInventoryRow, FulfillmentSummaryRow,
        FulfillmentDetailRow, PlanningGitMasterRow,
    )

    run = CalculationRun.objects.get(pk=RUN)
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_database()")
        if cursor.fetchone()[0] != "daily_3006":
            raise ValueError("Planning proof requires owned daily_3006")
    if run.output_digest != OUTPUT or run.status != "SUCCEEDED":
        raise ValueError("Accepted June 7 run identity differs")
    for route in ("overview", "grid", "graph", "custom"):
        require(run, route)

    observations = {}
    for actor, (products, locations) in SCOPES.items():
        base = dict(product_permissions=products, location_permissions=locations,
                    filters={}, paginationParameter=dict(pageNumber=1, recordsPerPage=50))
        result = {"overview": read(run, base, "overview")}
        for category, family in (("excessInventory", "excess"),
                                 ("orderFulfillment", "fulfillment")):
            payload = dict(base, category=category, type="review")
            family_result = {
                "count": read(run, payload, "grid", count=True),
                "grid": read(run, payload, "grid"),
                "graph": read(run, payload, "graph"),
            }
            try:
                family_result["custom"] = read(run, dict(payload, type="custom"), "custom")
            except Exception as exc:
                family_result["custom"] = {"error": type(exc).__name__, "detail": str(exc)}
            result[family] = family_result
        parent = dict(base, category="git", type="parent")
        child = dict(base, category="git", type="child")
        git = {
            "parent_count": read(run, parent, "grid", count=True),
            "parent_grid": read(run, parent, "grid"),
            "child_count": read(run, child, "grid", count=True),
            "child_graph": read(run, child, "graph"),
            "custom": read(run, dict(child, type="custom"), "custom"),
        }
        try:
            read(run, child, "grid")
        except Exception as exc:
            git["child_grid"] = {"error": type(exc).__name__, "detail": str(exc)}
        else:
            raise AssertionError("Canonical invalid child GIT grid unexpectedly succeeded")
        result["git"] = git
        observations[actor] = result

    paths = (
        "closing/importer/SkuAttributeData", "closing/importer/LocationAttributeData",
        "closing/importer/SkuLocAttributeData", "closing/importer/SKUDescriptionTbl",
        "closing/importer/SiteDescriptionTbl", "closing/dbm/SKULocStandardAttributes",
        "closing/consumer_context/NMSAllItems", "sources/bpr/InTransitData",
        "sources/planning/GoodsInTransitTransporterMaster",
        "closing/dbm/LastBatchRunTbl", "reports/bpr/vf_RationedReqReport",
    )
    sources = {path: image_rows(run, path) for path in paths}
    sources.update(
        excess=list(ExcessInventoryRow.objects.filter(run=run).order_by("ordinal").values()),
        fulfillment=list(FulfillmentSummaryRow.objects.filter(run=run).order_by("ordinal").values()),
        fulfillment_details=list(FulfillmentDetailRow.objects.filter(run=run).order_by("ordinal").values()),
        git_master=list(PlanningGitMasterRow.objects.filter(run=run)
                        .order_by("rationed_ordinal", "standard_ordinal").values()),
        manifest_images=sorted(run.production_manifest.get("images", {})),
    )
    value = dict(kind="daily-planning-consumer-export-v1", run=RUN,
                 output_digest=OUTPUT, observations=observations, sources=sources)
    print("PLANNING_EXPORT=" + json.dumps(value, default=wire, separators=(",", ":")))


def _runtime(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    values = [json.loads(line.split("=", 1)[1]) for line in lines
              if line.startswith("PLANNING_EXPORT=")]
    if len(values) != 1 or values[0].get("run") != RUN or values[0].get("output_digest") != OUTPUT:
        raise ValueError("Exact single accepted Planning runtime export required")
    return values[0]


def _plain(rows):
    remove = {"id", "run_id", "ordinal", "sku_key", "location_key", "parent_key",
              "rationed_ordinal", "standard_ordinal", "source_ordinal"}
    return [{key: value for key, value in row.items() if key not in remove} for row in rows]


def _json_scalar(cursor):
    row = cursor.fetchone()
    return [] if not row or row[0] in (None, "") else json.loads(row[0])


def _xlsx(path):
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with ZipFile(path) as archive:
        shared = []
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        for item in root.findall("a:si", ns):
            shared.append("".join(node.text or "" for node in item.iter("{" + ns["a"] + "}t")))
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        rows = []
        for row in sheet.findall(".//a:sheetData/a:row", ns):
            values = []
            for cell in row.findall("a:c", ns):
                node = cell.find("a:v", ns)
                value = None if node is None else node.text
                if cell.get("t") == "s" and value is not None:
                    value = shared[int(value)]
                values.append(value)
            rows.append(values)
    return rows


def compare(runtime_path, evidence, xlsx):
    from mta.serialization import storage
    from parity.legacy_isolation import exclusive_replay, connection
    from parity.output_archive import file_sha
    from parity.temporal import differences
    from parity.verify_rrr_consumer import (auth_ctes, supplement_temp_hierarchy,
                                            temp_rows, PERMISSION_SHA)
    from parity.planning_overview_queries import queries as overview_queries
    from parity.verify_excess_readmodel import (selected_queries as excess_queries,
                                                expected_response as excess_response,
                                                SECTIONS as EXCESS_SECTIONS)
    from parity.verify_fulfillment_consumer import selected_queries as fulfillment_queries
    from parity.verify_fulfillment_charts import (selected_queries as fulfillment_charts,
                                                   SECTIONS as FULFILLMENT_SECTIONS)
    from parity.git_queries import queries as git_queries, PLAN, PLAN_SHA, CHART, CHART_SHA

    evidence.mkdir(parents=True, exist_ok=False)
    receipt = dict(status="FAILED", run=RUN, output_digest=OUTPUT,
                   persistent_database_writes=False, engine_replays=0,
                   expedite_repeated=False)
    try:
        runtime = _runtime(runtime_path)
        runtime_file = evidence / "runtime-export.json.gz"
        with gzip.open(runtime_file, "wt", encoding="utf-8") as stream:
            json.dump(runtime, stream, ensure_ascii=False)
        catalogue_path = Path("D:/freshvcf-build/inputs/permission-input-v1.json")
        if file_sha(catalogue_path) != PERMISSION_SHA:
            raise ValueError("Permission catalogue differs")
        catalogue = json.loads(catalogue_path.read_text())
        sources = runtime["sources"]
        importer = {
            name: sources["closing/importer/" + name]
            for name in ("SkuAttributeData", "LocationAttributeData", "SkuLocAttributeData",
                         "SKUDescriptionTbl", "SiteDescriptionTbl")
        }
        result, sql_evidence, dll_jobs = [], {}, []
        os.environ["VFTEST_PROFILE"] = "fresh"
        with exclusive_replay(), connection("VFTEST_BPR") as db:
            for name, table, rows in (
                ("#Sku", "VFTEST_Importer.dbo.SkuAttributeData", importer["SkuAttributeData"]),
                ("#Loc", "VFTEST_Importer.dbo.LocationAttributeData", importer["LocationAttributeData"]),
                ("#Pair", "VFTEST_Importer.dbo.SkuLocAttributeData", importer["SkuLocAttributeData"]),
                ("#SkuDesc", "VFTEST_Importer.dbo.SKUDescriptionTbl", importer["SKUDescriptionTbl"]),
                ("#LocDesc", "VFTEST_Importer.dbo.SiteDescriptionTbl", importer["SiteDescriptionTbl"]),
                ("#Standard", "VFTEST_Importer.dbo.SKULocStandardAttributes", sources["closing/dbm/SKULocStandardAttributes"]),
                ("#Nms", "VFTEST_Importer.dbo.NMSAllItems", sources["closing/consumer_context/NMSAllItems"]),
                ("#Transit", "VFTEST_Importer.dbo.InTransitData", sources["sources/bpr/InTransitData"]),
                ("#Transporter", "dbo.GoodsInTransitTransporterMaster", sources["sources/planning/GoodsInTransitTransporterMaster"]),
                ("#Git", "dbo.GoodsInTransitMaster", _plain(sources["git_master"])),
                ("#Rationed", "dbo.vf_RationedReqReport", sources["reports/bpr/vf_RationedReqReport"]),
                ("#Excess", "dbo.ExcessInventoryDetails", _plain(sources["excess"])),
                ("#Summary", "dbo.OrderFulfillmentData", _plain(sources["fulfillment"])),
                ("#Fulfillment", "dbo.OrderFulfillmentData", _plain(sources["fulfillment"])),
                ("#Details", "dbo.OrderFulfillmentDataDetails", _plain(sources["fulfillment_details"])),
                ("#LastDate", "dbo.LastBatchRunTbl", sources["closing/dbm/LastBatchRunTbl"]),
            ):
                temp_rows(db, name, table, rows)
            supplement_temp_hierarchy(db, catalogue)
            dynamic = db.execute("SELECT Col_Code FROM ui_ReportConfigurations WHERE reportname='adminbpr' AND Visible=1 AND (Col_Code LIKE 'SKUAttr%' OR Col_Code LIKE 'LocAttr%' OR Col_Code LIKE 'SKULocAttr%')").fetchall()
            if dynamic:
                raise ValueError("Selected dynamic attributes require explicit mapping: " + str(dynamic))
            excess_grid, excess_count, excess_charts, excess_config = excess_queries()
            _, fulfill_grid, fulfill_count, fulfill_config = fulfillment_queries()
            fulfill_charts = fulfillment_charts()
            for actor, (products, locations) in SCOPES.items():
                payload = dict(product_permissions=products, location_permissions=locations)
                auth = auth_ctes(db, catalogue, payload)
                modern = runtime["observations"][actor]

                selected = overview_queries(auth)
                indices = (0, 1, 2, 6, 7, 8, 9)
                values = {index: db.execute(selected[index]).fetchone()[0] for index in indices}
                native_overview = [
                    dict(category="git/wip", parentCount=str(values[0]), childCount=str(values[1]), custom=str(values[2])),
                    dict(category="excessInventory", reviewCount=str(values[6]), custom=str(values[7])),
                    dict(category="orderFulfillment", reviewCount=str(values[8]), custom=str(values[9])),
                ]
                modern_overview = [row for row in modern["overview"] if row["category"] != "expedite"]
                result.append(dict(actor=actor, route="overview-without-expedite",
                                   differences=differences(native_overview, modern_overview, "/overview")))
                sql_evidence[actor + "/overview"] = [selected[index] for index in indices]

                native_excess_grid = _json_scalar(db.execute(auth + excess_grid))
                native_excess_count = int(db.execute(auth + excess_count).fetchone()[0])
                excess_tables, excess_columns = {}, {}
                for spec, query in zip((row[0] for row in EXCESS_SECTIONS), excess_charts):
                    cursor = db.execute(auth + query)
                    names = [column[0] for column in cursor.description]
                    excess_tables[spec] = [dict(zip(names, row)) for row in cursor.fetchall()]
                    excess_columns[spec] = names
                native_excess_graph = excess_response(excess_tables)
                excess_dataset = []
                for spec, rows in excess_tables.items():
                    names = excess_columns[spec]
                    excess_dataset.append(dict(columns=[dict(name=name, type="int32" if name == "counts" else "string") for name in names], rows=rows))
                excess_dataset_path = evidence / (actor + "-excess-chart-input.json")
                excess_dataset_path.write_text(json.dumps(dict(tables=excess_dataset), default=wire), encoding="utf-8")
                dll_jobs.append((actor, "ExcessInventoryProcessor", "parent", "excess",
                                 excess_dataset_path, modern["excess"]["graph"]))
                result.extend((
                    dict(actor=actor, route="excess-count", differences=differences(native_excess_count, modern["excess"]["count"], "/excess/count")),
                    dict(actor=actor, route="excess-grid", differences=differences(native_excess_grid, modern["excess"]["grid"]["data"], "/excess/grid")),
                ))
                if modern["excess"]["custom"].get("data") != []:
                    raise ValueError("Exact empty Excess/NMS custom join no longer empty")
                result.append(dict(actor=actor, route="excess-custom",
                    differences=[], qualification="canonical INNER NMS join; exact accepted NMS and Excess populations are empty"))

                native_fulfill_grid = _json_scalar(db.execute(auth + fulfill_grid))
                native_fulfill_count = int(db.execute(auth + fulfill_count).fetchone()[0])
                tables, query_rows = [], {}
                for section, query in zip(FULFILLMENT_SECTIONS, fulfill_charts):
                    cursor = db.execute(auth + query)
                    names = [column[0] for column in cursor.description]
                    rows = storage([dict(zip(names, row)) for row in cursor.fetchall()])
                    query_rows[section] = rows
                    tables.append(dict(columns=[dict(name=n, type="int32" if n == "counts" else "string") for n in names], rows=rows))
                dataset_path = evidence / (actor + "-fulfillment-chart-input.json")
                dataset_path.write_text(json.dumps(dict(tables=tables), default=wire), encoding="utf-8")
                dll_jobs.append((actor, "QuadrantProcessor", "parent", "fulfillment",
                                 dataset_path, modern["fulfillment"]["graph"]))
                result.extend((
                    dict(actor=actor, route="fulfillment-count", differences=differences(native_fulfill_count, modern["fulfillment"]["count"], "/fulfillment/count")),
                    dict(actor=actor, route="fulfillment-grid", differences=differences(native_fulfill_grid, modern["fulfillment"]["grid"]["data"], "/fulfillment/grid")),
                ))
                sql_evidence[actor + "/fulfillment"] = dict(grid=auth + fulfill_grid, count=auth + fulfill_count,
                    charts=[auth + query for query in fulfill_charts])

                git = git_queries(auth, payload)
                native_parent_count = int(db.execute(git["parent-location-count"]).fetchone()[0])
                native_child_location = int(db.execute(git["child-location-count"]).fetchone()[0])
                native_child_transporter = int(db.execute(git["child-transporter-count"]).fetchone()[0])
                native_parent_grid = _json_scalar(db.execute(git["parent-location-grid"]))
                native_custom = _json_scalar(db.execute(git["child-custom"]))
                result.extend((
                    dict(actor=actor, route="git-parent-count", differences=differences([dict(locationwise=native_parent_count)], modern["git"]["parent_count"], "/git/parent-count")),
                    dict(actor=actor, route="git-parent-grid", differences=differences(native_parent_grid, modern["git"]["parent_grid"]["data"], "/git/parent-grid")),
                    dict(actor=actor, route="git-child-count", differences=differences([dict(locationwise=native_child_location, transporterwise=native_child_transporter)], modern["git"]["child_count"], "/git/child-count")),
                    dict(actor=actor, route="git-custom", differences=differences(native_custom, modern["git"]["custom"]["data"], "/git/custom")),
                ))
                try:
                    db.execute(git["child-transporter-grid"]).fetchall()
                except Exception as exc:
                    if "207" not in str(exc):
                        raise
                    native_error = "207"
                else:
                    raise AssertionError("Pinned invalid GIT child grid unexpectedly executed")
                child = modern["git"]["child_grid"]
                result.append(dict(actor=actor, route="git-child-grid-source-flaw",
                    differences=[] if native_error in child["detail"] else [dict(native=native_error, modern=child)]))
                git_tables = []
                for number in range(4):
                    cursor = db.execute(git["chart-" + str(number)])
                    columns = []
                    for column in cursor.description:
                        kind = ("int32" if column[1] is int else
                                "decimal" if column[1] is Decimal else "string")
                        columns.append(dict(name=column[0], type=kind))
                    names = [column["name"] for column in columns]
                    rows = [dict(zip(names, row)) for row in cursor.fetchall()]
                    git_tables.append(dict(columns=columns, rows=rows))
                git_dataset_path = evidence / (actor + "-git-chart-input.json")
                git_dataset_path.write_text(json.dumps(dict(tables=git_tables), default=wire), encoding="utf-8")
                dll_jobs.append((actor, "ExpediteProcessor", "git", "git",
                                 git_dataset_path, modern["git"]["child_graph"]))
                sql_evidence[actor + "/git"] = {key: git[key] for key in
                    ("parent-location-count", "parent-location-grid", "child-location-count",
                     "child-transporter-count", "child-transporter-grid", "child-custom",
                     "chart-0", "chart-1", "chart-2", "chart-3")}
                db.execute("DROP TABLE #ProductPermissions; DROP TABLE #LocationPermissions")

        harness = ROOT / "parity/invoke_legacy_quadrant.ps1"
        for actor, processor, direction, family, dataset_path, modern_graph in dll_jobs:
            output = evidence / (actor + "-" + family + "-chart-dll.json")
            log = evidence / (actor + "-" + family + "-chart-dll.log")
            completed = subprocess.run(["pwsh", "-NoProfile", "-File", str(harness),
                "-InputPath", str(dataset_path), "-OutputPath", str(output),
                "-Processor", processor, "-Direction", direction],
                capture_output=True, text=True)
            log.write_text(completed.stdout + completed.stderr, encoding="utf-8")
            if completed.returncode:
                raise RuntimeError("Pinned chart DLL failed: " + actor + "/" + family)
            native = json.loads(output.read_text(encoding="utf-8-sig"))["response"]
            result.append(dict(actor=actor, route=family + "-graph",
                               differences=differences(native, modern_graph, "/" + family + "/graph")))

        xlsx_rows = _xlsx(xlsx)
        headers = xlsx_rows[0]
        modern_grid = runtime["observations"]["broad"]["fulfillment"]["grid"]
        configured = {row["header"]: row for row in modern_grid["uiConfig"]}
        # The unchanged frontend export labels the native Location Code column
        # WHCODE and omits the empty Tags column; every exported header must
        # still resolve to one configured native field.
        config = []
        for header in headers:
            item = configured.get("Location Code" if header == "WHCODE" else header)
            if item is None:
                raise ValueError("Browser XLSX header is not a selected native grid field: " + str(header))
            config.append(item)
        def cell(value):
            if value is None:
                return ""
            text = str(value)
            try:
                number = Decimal(text)
            except Exception:
                return text
            return str(number.normalize())
        expected_xlsx = [[cell(row.get(item["colCode"]))
                          for item in config] for row in modern_grid["data"]]
        actual_xlsx = [[cell(value) for value in row] for row in xlsx_rows[1:]]
        result.append(dict(actor="broad", route="fulfillment-browser-xlsx-23-fields",
                           differences=differences(expected_xlsx, actual_xlsx, "/xlsx")))

        failures = [item for item in result if item["differences"]]
        queries_path = evidence / "canonical-queries.json.gz"
        with gzip.open(queries_path, "wt", encoding="utf-8") as stream:
            json.dump(sql_evidence, stream)
        receipt.update(status="PASS" if not failures else "FAIL", comparisons=result,
            comparison_count=len(result), failures=failures,
            runtime_export_sha256=file_sha(runtime_file), runtime_log_sha256=file_sha(runtime_path),
            canonical_sources={str(PLAN): PLAN_SHA, str(CHART): CHART_SHA},
            canonical_queries_sha256=file_sha(queries_path),
            browser_xlsx=dict(path=str(xlsx), sha256=file_sha(xlsx), rows=len(actual_xlsx), fields=len(headers)),
            residual_source_flaws=[
                "Pinned GIT combined child/transporter grid fails SQL 207 and remains denied.",
                "Broad fulfillment custom has unequal rows sharing the native SKU/location ROW_NUMBER keys and remains NOT_PARITY; restricted custom is not promoted by this proof.",
                "Expedite is excluded because its complete independent SQL/DLL proof is already retained.",
            ], qualification="Accepted June 7 typed source bags; scoped overview (excluding Expedite), Excess/Fulfillment grid-count-chart, GIT parent/count/custom and canonical child-grid failure. Not whole-page/browser performance acceptance.")
        if failures:
            raise AssertionError(str(len(failures)) + " Planning consumer comparisons differ")
    except Exception as exc:
        receipt["error"] = dict(type=type(exc).__name__, message=str(exc))
        raise
    finally:
        with (evidence / "receipt.json").open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2, default=wire)
    print(receipt["status"], receipt["comparison_count"], evidence)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("export")
    launch = sub.add_parser("export-stack")
    launch.add_argument("--label", required=True)
    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("--runtime", type=Path, required=True)
    compare_parser.add_argument("--evidence", type=Path, required=True)
    compare_parser.add_argument("--xlsx", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "export":
        export()
    elif args.command == "export-stack":
        from tools.daily_stack_check import invoke
        prefix = ("from datetime import date,datetime\nfrom decimal import Decimal\n"
                  "from uuid import UUID\nimport json,os\n"
                  f"RUN={RUN!r}\nOUTPUT={OUTPUT!r}\nSCOPES={SCOPES!r}\n")
        code = prefix + inspect.getsource(wire) + inspect.getsource(export) + "\nexport()\n"
        raise SystemExit(invoke(["-c", code], args.label))
    else:
        compare(args.runtime, args.evidence, args.xlsx)


if __name__ == "__main__":
    main()
