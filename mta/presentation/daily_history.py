"""Deployed DailyDataGraph wire shape over the retained pure projection.

SQL Server's nested scalar FOR JSON PATH emits NULL for an empty rowset in
the deployed outer SELECT ... INCLUDE_NULL_VALUES. Keep that distinction;
the reused projection's Python lists are not the API contract.
"""
from mta.presentation.dbm import daily_graph as _rows

POPULATIONS=('StockData','NormData','MasterData','MonitoringData','NormChangeHistoryData','SuggestionHistoryData')


def daily_graph(state,sku,location):
    return [{**root,**{name:root[name] if root[name] else None for name in POPULATIONS}}
            for root in _rows(state,sku,location)]
