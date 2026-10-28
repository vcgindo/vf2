"""Disambiguate only generic JSON traversal aliases from PL/pgSQL records."""
from importlib import import_module
import re
from django.db import migrations

prior = import_module('mta.runtime.migrations.0239_production_generic_scope_read')
OLD = prior.BODY
ALIASES = {'Q': 'GenericRequestFields', 'T': 'GenericScopeFields', 'F': 'GenericReferenceFields'}
ADMISSION = re.sub(r'\b[QTF]\b', lambda match: ALIASES[match[0]], prior.ADMISSION)
assert OLD.count(prior.ADMISSION) == 1
BODY = OLD.replace(prior.ADMISSION, ADMISSION, 1)
replace_read = prior.prior.replace_read
SQL = replace_read(OLD, BODY)
REVERSE = prior.REVERSE.split('END $stop$;', 1)[0] + 'END $stop$;\n' + replace_read(BODY, OLD)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0241_scope_transit_settings_owners')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
