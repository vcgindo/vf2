from importlib import import_module
from django.db import migrations


prior=import_module('mta.runtime.migrations.0195_scope_pick_revision_ownership')
assert prior.NEW.count('OR C.id IS NULL')==1
NEW=prior.NEW.replace('OR C.id IS NULL','OR C.run_id IS NULL')


class Migration(migrations.Migration):

    dependencies = [
        ('fresh_mta', '0195_scope_pick_revision_ownership'),
    ]

    operations = [
        migrations.RunSQL(prior.transition(prior.NEW,NEW),
            "DO $pre$ BEGIN IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopepickfiles) THEN "
            "RAISE EXCEPTION 'Accepted Pick files require a compatible forward release'; END IF; END $pre$;\n"
            +prior.transition(NEW,prior.NEW)),
    ]
