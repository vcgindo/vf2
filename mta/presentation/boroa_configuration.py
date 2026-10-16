"""Pinned BuyerOrderReport subset of already admitted immutable UI metadata."""
import hashlib,json
from pathlib import Path
from decimal import Decimal
from django.db import connection
from mta.presentation.context import PublicationUnavailable
from mta.presentation.rrr import sql_key

CONFIG=Path(__file__).resolve().parents[1]/'config/boroa_snapshot_config.json'
from mta.presentation.boroa_contract import CONFIG_SHA256


def configuration():
    raw=CONFIG.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=CONFIG_SHA256:
        raise PublicationUnavailable('BOR_configuration_changed')
    value=json.loads(raw)
    from mta.presentation import native_publication
    if native_publication.enabled():
        # Native publication binds this pinned file in configuration_identity;
        # it does not depend on the historical fixture staging registry.
        native_publication.require_mode()
        return value
    with connection.cursor() as c:
        c.execute('SELECT source,table_name,values_sha256,row_count FROM stage2_owner.tables '
            'WHERE (source=%s AND table_name=%s) OR (source=%s AND table_name=%s)',
            ['Demo_BPR_1','ui_ReportConfigurations','Demo_Importer_1','ui_ReportColumnTypes'])
        if set(c.fetchall())!={(s['source'],s['table'],s['values_sha256'],s['row_count']) for s in value['sources']}:
            raise PublicationUnavailable('BOR_configuration_source_changed')
    return value


def ui_columns(value):
    result=[]
    for row in value['columns']:
        if not row['Visible']: continue
        matches=[t for t in value['types'] if sql_key(t['ReportName'],t['ColCode'])==sql_key(row['ReportName'],row['Col_Code'])] or [{}]
        for match in matches:
            result.append({k:v for k,v in {**{k:v for k,v in row.items() if k not in ('TagID','source_ordinal')},
                                          'DataType':match.get('DataType')}.items() if v is not None})
    return result
