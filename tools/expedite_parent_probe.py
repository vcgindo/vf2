"""Read-only persisted parent reader probe; no route or whole trace load."""
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.conf import settings
from mta.presentation.admission import admit
from mta.presentation.context import scope
from mta.presentation.expedite_parent import parent_rows
from mta.presentation.expedite_read import expedite_context

settings.DATABASES['default']['OPTIONS']['options'] += ' -c default_transaction_read_only=on -c statement_timeout=45000'
admission = admit()
with patch('mta.runtime.services.read_outputs', side_effect=AssertionError('whole publication forbidden')):
    context = expedite_context()
    result = dict(run=str(context.run.pk), output_digest=context.run.output_digest,
                  admission=admission, observations={})
    for case in json.loads(Path(sys.argv[1]).read_text()):
        products, locations = scope(case['payload'], attributes=context.importer)
        for label, paging in (('full', (1, 5000)), ('page1', (1, 3)), ('page2', (2, 3))):
            result['observations'][case['id']+'/'+label] = parent_rows(
                context.rows, context.importer, context.standards, context.masters,
                nms=context.nms, products=products, locations=locations, paging=paging)
print(json.dumps(result))
