"""Complete existing-fixture dimension-bag proof before occurrence persistence."""
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from django.db import connection
from mta.presentation import fixture
from mta.presentation.planning_grid_preparation import grid_occurrences, DIMENSIONS
from mta.presentation.selective import image_rows
from mta.presentation.excess_views import joined_rows as excess_rows
from mta.presentation.fulfillment_views import joined_rows as fulfillment_rows
from mta.runtime.models import ExcessInventoryRow, FulfillmentSummaryRow
from mta.serialization import storage


def main():
    run, source = fixture.binding()
    with connection.cursor() as c:
        c.execute('SET default_transaction_read_only=on')
        c.execute("SET statement_timeout='60s'")
    importer = {name: image_rows(run, 'closing/importer/' + name) for _, name in DIMENSIONS}
    output = {'ClosingState': [{'importer': importer}]}
    results = {}
    for family, model in [('excess', ExcessInventoryRow), ('fulfillment', FulfillmentSummaryRow)]:
        facts = model.objects.filter(run=run).order_by('ordinal')
        if family == 'excess':
            facts = facts.filter(ReportDate=run.business_date)
        fields = [f.name for f in model._meta.fields if f.name not in ('id', 'run', 'ordinal')]
        rows = storage(list(facts.values(*fields)))
        expected = excess_rows(output, rows, run.business_date) if family == 'excess' else fulfillment_rows(output, rows)
        query, params = grid_occurrences(run, family)
        with connection.cursor() as c:
            c.execute(query, params)
            names = [d[0] for d in c.description]
            actual = [dict(zip(names, row)) for row in c.fetchall()]
        aliases = {'sku_description': 'SKUName', 'location_description': 'WHName',
                   **{prefix + str(i): prefix + str(i) for prefix in ('sl', 'll') for i in range(1, 6)}}
        if family == 'excess':
            aliases['parent_description'] = 'ParentWHName'
        # Include fact identity/value bag, not just labels or counts. Fact ordinal
        # resolves the original source occurrence and remains outside wire output.
        originals = {row['ordinal']: row for row in facts.values('ordinal', *fields)}
        def packed(row):
            return json.dumps(storage(row), sort_keys=True, separators=(',', ':'))
        before = Counter(packed({**{f: row[f] for f in fields},
                                 **{name: row[alias] for name, alias in aliases.items()}}) for row in expected)
        after = Counter(packed({**{f: originals[row['fact_ordinal']][f] for f in fields},
                                **{name: row[name] for name in aliases}}) for row in actual)
        assert before == after, (family, sum((before-after).values()), sum((after-before).values()))
        results[family] = dict(facts=len(rows), occurrences=len(actual), exact_fact_display_bag=True)
    assert fixture.binding()[1] == source
    print(json.dumps(dict(status='PASS', families=results, source_digest=source)))


if __name__ == '__main__':
    main()
