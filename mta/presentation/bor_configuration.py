"""Pinned BuyerOrderReport subset of already admitted immutable UI metadata."""
import hashlib,json
from pathlib import Path
from decimal import Decimal
from django.db import connection
from mta.presentation.context import PublicationUnavailable
from mta.presentation.rrr import sql_key

CONFIG=Path(__file__).resolve().parents[1]/'config/bor_snapshot_config.json'
CONFIG_SHA256='149e82fec14b483f46c45ac43c44e31006a1ba8c1a42a5cccbbf49871b6bef09'
# Git stores the same retained configuration with LF line endings. The legacy
# fixture pin above identifies its CRLF capture; native publication pins Git bytes.
NATIVE_CONFIG_SHA256='ea1043b8424f042c87b05151b213cde19fd4ac9caabc8b9a76348367a01c32d4'


def configuration():
    from mta.presentation import native_publication
    native = native_publication.enabled()
    raw=CONFIG.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=(NATIVE_CONFIG_SHA256 if native else CONFIG_SHA256):
        raise PublicationUnavailable('BOR_configuration_changed')
    value=json.loads(raw)
    if native:
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


def wire_rows(rows,value):
    # Deployed reader dictionary is OrdinalIgnoreCase, not SQL trimming semantics.
    types={r['ColCode'].casefold():r['DataType'] for r in value['types']}
    result=[]
    for row in rows:
        mapped={}
        for name,v in row.items():
            if str(types.get(name.casefold(),'')).casefold()=='number':
                mapped[name]=(int(v) if v==v.to_integral_value() else float(v)) if isinstance(v,Decimal) else v
            else: mapped[name]='' if v is None else str(v)
        result.append(mapped)
    return result
