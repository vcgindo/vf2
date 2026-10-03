"""Read-only BPR batch on persisted rows; observations, not legacy parity."""
import json
import os
from pathlib import Path
import sys
import time
from decimal import Decimal
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.db import connection
from mta.presentation.bpr import ReadModel
from mta.presentation.bpr_read import bpr_context
from mta.presentation.bpr_filters import BprPredicate
from mta.presentation.context import PublicationUnavailable
from mta.presentation.views import scoped


def typed(value):
    kind = ('null' if value is None else 'bool' if isinstance(value,bool) else
            'decimal' if isinstance(value,Decimal) else 'int' if isinstance(value,int) else
            'float' if isinstance(value,float) else 'str')
    return dict(type=kind,value=str(value) if kind in ('decimal','float') else value)


with connection.cursor() as cursor:
    cursor.execute('SET default_transaction_read_only=on')
    cursor.execute("SET statement_timeout='15s'")
with patch('mta.presentation.context.read_outputs', side_effect=AssertionError('whole-publication read')):
    context = bpr_context()
model = ReadModel(context.output,context.ancillary)
attrs = context.output['ClosingState'][0]['importer']
observations = []
for case in json.loads(Path(sys.argv[1]).read_text())['cases']:
    result = dict(id=case['id'])
    payload = case['payload']
    for mode in ('count','grid','analytics','export'):
        started = time.monotonic()
        try:
            predicate = BprPredicate(payload,attrs['LocationAttributeData'],export=mode=='export')
            source = (model.count_rows() if mode=='count' else list(model.joined(final=True))
                      if mode=='export' else model.candidates())
            selected = predicate.select(scoped(source,payload,'WHCode',attributes=attrs,
                                               preserve_join_multiplicity=True))
            if mode == 'count': value = len(selected)
            elif mode == 'analytics': value = model.analytics(selected)
            else:
                paging = payload['paginationParameter']
                rows = (model.export(selected) if mode=='export' else
                        model.page(selected,paging['pageNumber'],paging['recordsPerPage']))
                assert all(row['intransit'] is None for row in rows)
                value = [{name:typed(value) for name,value in row.items()} for row in rows]
            result[mode] = dict(value=value, seconds=time.monotonic()-started)
        except PublicationUnavailable as exc:
            result[mode] = dict(unavailable=str(exc), seconds=time.monotonic()-started)
    observations.append(result)
print(json.dumps(dict(run_id=str(context.run.pk),output_digest=context.run.output_digest,
    observations=observations,qualification='Modern read-only observations; no independent SQL or browser parity')))
