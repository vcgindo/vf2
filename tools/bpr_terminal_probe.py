"""Read only actual PostgreSQL consumer images; no whole trace or replay."""
import json
import os
from pathlib import Path
import sys
from decimal import Decimal
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.db import connection
from mta.presentation.bpr_read import bpr_context
from mta.presentation.bpr import ReadModel
from mta.presentation.views import scoped


def typed(value):
    kind = ('null' if value is None else 'bool' if isinstance(value, bool) else
            'decimal' if isinstance(value, Decimal) else 'int' if isinstance(value, int) else
            'float' if isinstance(value, float) else 'str')
    return dict(type=kind, value=str(value) if kind in ('decimal', 'float') else value)

cases = json.loads(Path(sys.argv[1]).read_text())['cases']
with connection.cursor() as cursor:
    cursor.execute('SET default_transaction_read_only=on')
    cursor.execute("SET statement_timeout='15s'")
with patch('mta.presentation.context.read_outputs', side_effect=AssertionError('whole-publication read')):
    context = bpr_context()
model = ReadModel(context.output, context.ancillary)
attrs = context.output['ClosingState'][0]['importer']
observations = []
for case in cases:
    payload = case['payload']
    count = scoped(model.count_rows(), payload, 'WHCode', attributes=attrs, preserve_join_multiplicity=True)
    candidates = scoped(model.candidates(), payload, 'WHCode', attributes=attrs, preserve_join_multiplicity=True)
    page, size = payload['paginationParameter']['pageNumber'], payload['paginationParameter']['recordsPerPage']
    rows = model.page(candidates, page, size)
    values = []
    for row in rows:
        assert row['intransit'] is None
        values.append({key:typed(value) for key,value in row.items()})
    observations.append(dict(id=case['id'], count=len(count), rows=values))
print(json.dumps(dict(run_id=str(context.run.pk), output_digest=context.run.output_digest,
    production_digest=context.run.production_digest, ancillary=context.ancillary, observations=observations)))
