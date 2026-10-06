"""Pure port of canonical Importer ``NMSCreateSnapshot.sql``.

Source SHA256: f306ea8dc185611197d55d5deb7dd8bf5d1ab5523a581577bc0b8f1ec63a47ab.
The function models only the script's NMSActive gate, MasterData introduction-
date UPDATE, and truncate/rebuild of NMSAllItems.  Input occurrence order and
join multiplicity are retained; no source row is selected or deduplicated.
"""
from copy import deepcopy
from itertools import product


MASTER_FIELDS = (
    "SKUCode", "WhCode", "Norm", "MinNorm", "RLT", "RCP", "GCP", "OCP",
    "MinOrderCount", "ParentWhCode", "SKUIntroDate",
)
SKU_FIELDS = (
    "SKUCode", "ElephantOrderCapping", "Weight", "Volume",
    *("SL%d" % i for i in range(1, 6)), *("c%d" % i for i in range(1, 16)),
)
LOCATION_FIELDS = (
    "WHCode", "LocationType", "LogisticsLocation",
    *("LL%d" % i for i in range(1, 6)), *("c%d" % i for i in range(1, 16)),
)
SKULOC_FIELDS = (
    "SKUCode", "LocCode", "PackSize", "SpikeThreshold", "PSOThreshold",
    "FGRMFlag", "StockPercentForRationing", "NormPercentReservation",
    "NonNMS", *("c%d" % i for i in range(1, 16)),
)
NMS_FIELDS = (
    "SKUCode", "WhCode", "Norm", "MinNorm", "RLT", "RCP", "GCP", "OCP",
    "ParentWhCode", "SKUIntroDate", "SKUDescription", "WHDescription",
    "ParentDescription", "PackSize", "SpikeThreshold", "DefaultSpikeThreshold",
    "PSOThreshold", "DefaultPSOThreshold", "FGRMFlag",
    "StockPercentForRationing", "NormPercentReservation", "MinOrderCount",
    "DBMActive", "ElephantOrderCapping", "Weight", "Volume",
    *("SL%d" % i for i in range(1, 6)), "LocationType", "LogisticsLocation",
    *("LL%d" % i for i in range(1, 6)),
    *("SKUAtt%02d" % i for i in range(1, 16)),
    *("LocAtt%02d" % i for i in range(1, 16)),
    *("SKULocAtt%02d" % i for i in range(1, 16)),
)


class NmsSnapshotAmbiguity(ValueError):
    """Native UPDATE has multiple unequal qualifying source values."""


def _key(*values):
    if any(value is None for value in values):
        return None
    # Canonical databases use SQL_Latin1_General_CP1_CI_AS.  The retained
    # connector cases exercise its ASCII case/trailing-space behavior only.
    return tuple(value.rstrip(" ").upper() if isinstance(value, str) else value
                 for value in values)


def _index(rows, *fields):
    result = {}
    for row in rows:
        key = _key(*(row[field] for field in fields))
        if key is not None:
            result.setdefault(key, []).append(row)
    return result


def _require(rows, fields, table):
    missing = [(ordinal, sorted(set(fields) - set(row)))
               for ordinal, row in enumerate(rows) if not set(fields) <= set(row)]
    if missing:
        raise ValueError("NMSCreateSnapshot incomplete %s fields: %r" % (table, missing))


def _updated_master(master_data, dbm_master):
    dbm = _index(dbm_master, "SKUCode", "WhCode")
    result = deepcopy(list(master_data))
    for row in result:
        current = row["SKUIntroDate"]
        if current is None:
            continue  # SQL NULL <> value is UNKNOWN.
        candidates = {source["SKUIntroDate"] for source in dbm.get(
            _key(row["SKUCode"], row["WhCode"]), ())
            if source["SKUIntroDate"] is not None and source["SKUIntroDate"] != current}
        if len(candidates) > 1:
            raise NmsSnapshotAmbiguity(
                "NMSCreateSnapshot MasterData SKUIntroDate update has no source winner")
        if candidates:
            row["SKUIntroDate"] = candidates.pop()
    return result


def create_snapshot(*, nms_active, master_data, dbm_master, skuloc_attributes,
                    sku_descriptions, site_descriptions, exclusions,
                    sku_attributes, location_attributes, nms_all_items=()):
    """Return post-script MasterData and NMSAllItems occurrence bags.

    When NMS is inactive the SQL returns before touching either table, so the
    prior bags are copied without inspecting unrelated source tables.
    """
    if type(nms_active) is not bool:
        raise ValueError("NMSActive must be explicit")
    if not nms_active:
        return {"MasterData": deepcopy(list(master_data)),
                "NMSAllItems": deepcopy(list(nms_all_items))}

    for rows, fields, table in (
            (master_data, MASTER_FIELDS, "MasterData"),
            (dbm_master, MASTER_FIELDS, "DBMMaster"),
            (skuloc_attributes, SKULOC_FIELDS, "SkuLocAttributeData"),
            (sku_descriptions, ("SKUCode", "SKUDescription"), "SKUDescriptionTbl"),
            (site_descriptions, ("WHCode", "WHDescription"), "SiteDescriptionTbl"),
            (exclusions, ("SKUCode", "WhCode"), "Exclusions"),
            (sku_attributes, SKU_FIELDS, "SkuAttributeData"),
            (location_attributes, LOCATION_FIELDS, "LocationAttributeData")):
        _require(rows, fields, table)

    masters = _updated_master(master_data, dbm_master)
    pairs = _index([row for row in skuloc_attributes if row["NonNMS"] == 0],
                   "SKUCode", "LocCode")
    descriptions = _index(sku_descriptions, "SKUCode")
    sites = _index(site_descriptions, "WHCode")
    excluded = _index(exclusions, "SKUCode", "WhCode")
    sku = _index(sku_attributes, "SKUCode")
    location = _index(location_attributes, "WHCode")
    output = []
    for master in masters:
        pair_key = _key(master["SKUCode"], master["WhCode"])
        parent_key = _key(master["ParentWhCode"])
        sources = (pairs.get(pair_key, ()), descriptions.get(_key(master["SKUCode"]), ()),
                   sites.get(_key(master["WhCode"]), ()), sites.get(parent_key, ()),
                   excluded.get(pair_key, (None,)), sku.get(_key(master["SKUCode"]), ()),
                   location.get(_key(master["WhCode"]), ()))
        for pair, sku_description, site, parent, exclusion, sku_row, location_row in product(*sources):
            row = {name: master[name] for name in (
                "SKUCode", "WhCode", "Norm", "MinNorm", "RLT", "RCP", "GCP",
                "OCP", "ParentWhCode", "SKUIntroDate")}
            row.update(
                SKUDescription=sku_description["SKUDescription"],
                WHDescription=site["WHDescription"],
                ParentDescription=parent["WHDescription"],
                PackSize=pair["PackSize"], SpikeThreshold=pair["SpikeThreshold"],
                DefaultSpikeThreshold=None, PSOThreshold=pair["PSOThreshold"],
                DefaultPSOThreshold=None, FGRMFlag=pair["FGRMFlag"],
                StockPercentForRationing=pair["StockPercentForRationing"],
                NormPercentReservation=pair["NormPercentReservation"],
                MinOrderCount=master["MinOrderCount"], DBMActive=exclusion is None,
                ElephantOrderCapping=sku_row["ElephantOrderCapping"],
                Weight=sku_row["Weight"], Volume=sku_row["Volume"],
                LocationType=location_row["LocationType"],
                LogisticsLocation=location_row["LogisticsLocation"],
            )
            row.update({"SL%d" % i: sku_row["SL%d" % i] for i in range(1, 6)})
            row.update({"LL%d" % i: location_row["LL%d" % i] for i in range(1, 6)})
            row.update({"SKUAtt%02d" % i: sku_row["c%d" % i] for i in range(1, 16)})
            row.update({"LocAtt%02d" % i: location_row["c%d" % i] for i in range(1, 16)})
            row.update({"SKULocAtt%02d" % i: pair["c%d" % i] for i in range(1, 16)})
            if set(row) != set(NMS_FIELDS):
                raise AssertionError("NMSAllItems output field order changed")
            output.append({name: row[name] for name in NMS_FIELDS})
    return {"MasterData": masters, "NMSAllItems": output}
