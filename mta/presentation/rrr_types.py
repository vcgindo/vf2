"""B1-02/R: selected deployed RRRProcessor response serialization.

Authority: pinned deployed DLL, StreamResults iterator IL_015f..IL_01c3.
The selected Demo_Importer_1 type map was read on 2026-09-26 and matches
the 118 RationRequirementReport rows in UI_ReportColumnTypes_2.0.sql.
Number means preserve the SQL value, NOT coerce it to a numeric value.
In particular ECol is configured Number but contains a colour string.
"""
from decimal import Decimal


NUMBER_COLUMNS = frozenset("""
Norm VirtualNorm VirtualNodeNorm SpikeThreshold PSOThreshold Stock GIT
StockForRationing StockForReqCalc TPen SKULocAttr9 SKULocAttr10 EPen ECol
DispatchPen ParentNorm TPenParent TColParent EPenParent EColParent Req
AllocatedForVirtualNormReq AllocatedForNormReq AllocatedForSnPReq
AllocatedForDirectOrders RReq torb torr toy tog tob PS RCPs LPS LeftoverStock
ParentPacksize IsNormed DirectSpikeOverdue SpikeOverdueAtParent PSO
RelPSOAndCNR ResidualChildrenSnP SnPToNetOff SnPNettedOff ResidualSnP
EcoStockForNormReq NormReq BlueReq AvgSiblingsNorm AvgChildrenNorm
ParentStockForNormRationing ParentStockForSnPRationing ParentStockForRationing
StockPercentageForRationing NormPercentReservation ParentStockPercentageForRationing
ParentNormPercentageReservation
""".split())
_NUMBER_KEYS = {key.casefold() for key in NUMBER_COLUMNS}


def selected_rrr_response(row):
    """Serialize an already selected SQL-shaped row, including NULL fields.

DbDataReader returns DBNull for SQL NULL: the Number branch returns null,
the other branch calls DBNull.ToString() and therefore returns an empty
string. Do not infer types from names or repair inconsistent configuration.
"""
    result = {}
    for key, value in row.items():
        if key.casefold() in _NUMBER_KEYS:
            if isinstance(value, Decimal):
                value = int(value) if value == value.to_integral_value() else float(value)
            result[key] = value
        else:
            result[key] = '' if value is None else str(value)
    return result
