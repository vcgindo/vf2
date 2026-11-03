"""Preserve the existing invoker read permission for the reference predicate."""
from importlib import import_module

from django.db import migrations


reference = import_module('mta.runtime.migrations.0255_postbtr_rationing_reference')
original_acl = import_module('mta.runtime.migrations.0232_runtime_report_consumer_read')
signature = 'mta.runtime_report_publication_source(mta.fresh_mta_runtimereportpublication)'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0256_preserve_rationing_source_order')]
    # Fresh registration owns this grant for an unregistered database. In a
    # populated upgrade, use the original ACL owner and recorded consumer.
    # Both earlier schema versions require this same read permission.
    operations = [migrations.RunSQL(reference.placement.exact(signature, reference.SOURCE) + original_acl.SQL,
                                    migrations.RunSQL.noop)]
