"""Correct the typed NEW-record branch without replacing applied0056 behavior."""
from django.db import migrations
from mta.runtime.publication_schema import FORWARD, INITIAL_FORWARD


def definition(sql):
    return ('CREATE OR REPLACE FUNCTION mta.guard_daily_source_insert()' +
        sql.split('CREATE FUNCTION mta.guard_daily_source_insert()',1)[1].split('$$;',1)[0]+'$$;')


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0056_daily_publication_seals')]
    operations = [migrations.RunSQL(definition(FORWARD), definition(INITIAL_FORWARD))]
