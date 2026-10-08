"""Pure operational projections for BPR exceptions and parent-Norm validation."""
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext

from mta.application.r1_importer_master import MASTER_COLUMNS


SOURCES = {
    "bpr_export": (
        "Scripts/BPR/GenerateBPRExceptionReport.sql",
        "c1e0a6b607a50a51226ed25f525f362f256eef34eb640b58ca33d6e0c7a2912d",
    ),
    "bpr_collect": (
        "Scripts/BPR/CollectDataForBPR.sql",
        "1236b702861dce1d9f2492f9c7d9a280bbef20245326ff49628dd6b09308a7c7",
    ),
    "bpr_penetration": (
        "Scripts/BPR/CalculatePenetrationAndColor.sql",
        "e4a62d592b660fe08d46c45eecaf7a061e60eba7c8d86d3adec239023de5e251",
    ),
    "parent_norm": (
        "Scripts/Importer/ValidationForParentNorm.sql",
        "014d3c5f3cccff32b266eb11210960ca3fe2241da4bdd62d807dfb860f92da52",
    ),
}

BPR_MASTER_FIELDS = ("SKUCode", "WHCode", "Norm", "ParentWhCode", "SKUIntroDate")
DAILY_CONSUMPTION_FIELDS = (
    "SKUCode", "WHCode", "Stock", "Consumption", "GIT", "Receipts", "PSO", "BlueZone",
    "ReportDate",
)
BPR_EXCEPTION_FIELDS = ("SKUCode", "WhCode", "Norm", "Stock", "GIT")
PHASE_OUT_FIELDS = (
    "SKUCode", "WHCode", "OldNorm", "NewNorm", "PhaseOutFinished", "PhaseOutStartDate",
    "LastProcessedDate", "PhaseInSKUCode",
)
NO_NORM_PARENT_FIELDS = ("SKUCode", "WhCode", "Norm", "ParentWhCode")

NATIVE_SCHEMAS = {
    "BPRExceptions": (
        ("SKUCode", "nvarchar(50)", False), ("WhCode", "nvarchar(50)", False),
        ("Norm", "int", True), ("Stock", "int", True), ("GIT", "int", True),
    ),
    "NoNormAtParentReport": (
        ("SKUCode", "nvarchar(50)", False), ("WhCode", "nvarchar(50)", False),
        ("Norm", "int", False), ("ParentWhCode", "nvarchar(50)", True),
    ),
}

MIN_PENETRATION = Decimal("-99999999.00")


def bpr_exception_resultsets(*, exceptions, sku_descriptions, site_descriptions, equal):
    """GenerateBPRExceptionReport.sql left joins and native typed result sets."""
    _rows('BPRExceptions', exceptions, BPR_EXCEPTION_FIELDS)
    _rows('SKUDescriptionTbl', sku_descriptions, ('SKUCode', 'SKUDescription'))
    _rows('SiteDescriptionTbl', site_descriptions, ('WHCode', 'WHDescription'))
    if not callable(equal):
        raise ValueError('Explicit SQL equality adapter required')
    header = ['SKU Code', 'SKU Description', 'Location Code', 'Location Description', 'Norm', 'Stock', 'GIT']
    rows = []
    for row in exceptions:
        skus = [item for item in sku_descriptions if row['SKUCode'] is not None
                and item['SKUCode'] is not None and equal(row['SKUCode'], item['SKUCode'])] or [None]
        sites = [item for item in site_descriptions if row['WhCode'] is not None
                 and item['WHCode'] is not None and equal(row['WhCode'], item['WHCode'])] or [None]
        for sku in skus:
            for site in sites:
                sku_text = None if sku is None else sku['SKUDescription']
                site_text = None if site is None else site['WHDescription']
                rows.append([row['SKUCode'], 'Not Defined' if sku_text is None else sku_text.replace(',', ''),
                    row['WhCode'], 'Not defined' if site_text is None else site_text.replace(',', ''),
                    row['Norm'], 0 if row['Stock'] is None else row['Stock'],
                    0 if row['GIT'] is None else row['GIT']])
    return [dict(fields=header, types=['varchar-literal'] * 7, rows=[header]),
            dict(fields=header, types=['nvarchar(50)', 'nvarchar-export', 'nvarchar(50)',
                                      'nvarchar-export', 'int', 'int', 'int'], rows=rows)]
ORDER_QUALIFICATION = {
    "BPRExceptions": "source INSERTs have no ORDER BY; daily/master join-bag order retained pending native qualification",
    "NoNormAtParentReport": "source INSERT/SELECT has no ORDER BY; processed MasterData self-join bag order retained pending native qualification",
}


def _rows(name, rows, fields):
    if not isinstance(rows, list):
        raise ValueError(f"{name} must be an explicit row list")
    expected = set(fields)
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected:
            raise ValueError(f"{name} fields differ from the typed source contract")


def _text(value, *, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or len(value) > 50:
        raise ValueError("Native nvarchar(50) value required")


def _int(value, *, nullable=False):
    if value is None and nullable:
        return None
    if isinstance(value, bool):
        raise ValueError("Native SQL int value required")
    try:
        number = Decimal(str(value))
    except Exception:
        raise ValueError("Native SQL int value required") from None
    if not number.is_finite() or number != number.to_integral_value() or not -2147483648 <= number <= 2147483647:
        raise ValueError("Native SQL int value required")
    return int(number)


def _date(value, *, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
        raise ValueError("Native SQL date value required")


def _join(left, right, fields, equal):
    return all(left[a] is not None and right[b] is not None and equal(left[a], right[b])
               for a, b in fields)


def _validate_bpr_sources(masters, daily):
    for row in masters:
        _text(row["SKUCode"]); _text(row["WHCode"]); _int(row["Norm"])
        _text(row["ParentWhCode"], nullable=True); _date(row["SKUIntroDate"], nullable=True)
    for row in daily:
        _text(row["SKUCode"]); _text(row["WHCode"]); _int(row["Stock"], nullable=True)
        for field in ("Consumption", "GIT", "Receipts", "PSO", "BlueZone"):
            _int(row[field])
        _date(row["ReportDate"])


def bpr_exception_rows(*, bpr_master, daily_consumption, business_date, equal):
    """Reconstruct the first physical ``BPRExceptions`` image without replaying calculation.

    ``CollectDataForBPR`` joins DailyConsumption to BPRMaster and then joins that
    bag to BPRMaster again when creating PenetrationAndColor.  Both occurrence
    multipliers are retained.  The selected RunCoreBPR call records exceptions.
    """
    _rows("BPRMaster", bpr_master, BPR_MASTER_FIELDS)
    _rows("DailyConsumption", daily_consumption, DAILY_CONSUMPTION_FIELDS)
    _validate_bpr_sources(bpr_master, daily_consumption)
    if not callable(equal):
        raise ValueError("Explicit SQL equality adapter required")
    today = date.fromisoformat(business_date).isoformat()

    collected = []
    for daily in daily_consumption:
        if daily["ReportDate"] != today or daily["Stock"] is None:
            continue
        for master in bpr_master:
            if _join(daily, master, (("SKUCode", "SKUCode"), ("WHCode", "WHCode")), equal):
                # The first SELECT retains DailyConsumption identity spelling.
                collected.append(dict(SKUCode=deepcopy(daily["SKUCode"]),
                    WHCode=deepcopy(daily["WHCode"]), Stock=daily["Stock"], GIT=daily["GIT"]))

    result = []
    for daily in collected:
        for master in bpr_master:
            if not _join(master, daily, (("SKUCode", "SKUCode"), ("WHCode", "WHCode")), equal):
                continue
            norm, stock, git = (_int(master["Norm"]), _int(daily["Stock"]), _int(daily["GIT"]))
            if norm == 0:
                tech = eco = MIN_PENETRATION
            else:
                with localcontext() as context:
                    context.prec = 50
                    tech = (Decimal(100) * (norm - stock) / abs(norm)).quantize(
                        Decimal(".01"), rounding=ROUND_HALF_UP)
                    eco = (Decimal(100) * (norm - stock - git) / abs(norm)).quantize(
                        Decimal(".01"), rounding=ROUND_HALF_UP)
            if tech < MIN_PENETRATION or eco < MIN_PENETRATION:
                # The second SELECT takes identity and Norm from BPRMaster.
                result.append(dict(SKUCode=deepcopy(master["SKUCode"]),
                    WhCode=deepcopy(master["WHCode"]), Norm=norm, Stock=stock, GIT=git))
    return result


def _validate_master_data(rows):
    _rows("MasterData", rows, MASTER_COLUMNS)
    for row in rows:
        _text(row["SKUCode"]); _text(row["WhCode"]); _int(row["Norm"])
        for field in ("MinNorm", "RLT", "RCP", "GCP"):
            _int(row[field])
        _int(row["OCP"], nullable=True); _int(row["MinOrderCount"], nullable=True)
        _text(row["ParentWhCode"], nullable=True)
        _date(row["SKUIntroDate"], nullable=True)


def _validate_phase_out(rows):
    _rows("PhaseOutTbl", rows, PHASE_OUT_FIELDS)
    for row in rows:
        _text(row["SKUCode"]); _text(row["WHCode"])
        _int(row["OldNorm"], nullable=True); _int(row["NewNorm"], nullable=True)
        if type(row["PhaseOutFinished"]) not in (bool, int) or row["PhaseOutFinished"] not in (0, 1):
            raise ValueError("Native SQL bit value required")
        _date(row["PhaseOutStartDate"]); _date(row["LastProcessedDate"], nullable=True)
        _text(row["PhaseInSKUCode"], nullable=True)


def no_norm_at_parent_rows(*, master_data, phase_out, equal):
    """Project ``NoNormAtParentReport`` from processed importer ``MasterData``."""
    _validate_master_data(master_data)
    _validate_phase_out(phase_out)
    if not callable(equal):
        raise ValueError("Explicit SQL equality adapter required")

    result = []
    for child in master_data:
        if _int(child["Norm"]) <= 0:
            continue
        for parent in master_data:
            if (_int(parent["Norm"]) == 0
                    and _join(child, parent, (("SKUCode", "SKUCode"),
                                              ("ParentWhCode", "WhCode")), equal)):
                row = dict(SKUCode=deepcopy(child["SKUCode"]), WhCode=deepcopy(child["WhCode"]),
                           Norm=_int(child["Norm"]), ParentWhCode=deepcopy(child["ParentWhCode"]))
                if row["WhCode"] is None:
                    raise ValueError("NoNormAtParentReport.WhCode is NOT NULL")
                result.append(row)

    def phased(row, location_field):
        return any(_join(row, phase, (("SKUCode", "SKUCode"),
            (location_field, "WHCode")), equal) for phase in phase_out)

    return [row for row in result if not phased(row, "WhCode") and not phased(row, "ParentWhCode")]
