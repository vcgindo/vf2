"""Bounded daily preparation metadata and explicit ingestion owners.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import django.db.models.deletion
from django.db import migrations, models
from django.db.models.functions import Cast, Length
from django.db.models.lookups import LessThanOrEqual


def bounded(field, name):
    return models.CheckConstraint(condition=LessThanOrEqual(
        Length(Cast(field, models.TextField())), models.Value(262144)), name=name)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0147_ingestion_owner_catalogue')]
    operations = [
        migrations.AddField(model_name='dailyfeedattempt', name='accepted_facts',
            field=models.JSONField(default=dict)),
        migrations.AddField(model_name='dailyfeedattempt', name='prepared_context',
            field=models.JSONField(default=dict)),
        migrations.AddField(model_name='dailyfeedattempt', name='certification',
            field=models.ForeignKey(blank=True, null=True, related_name='daily_feed_attempts',
                on_delete=django.db.models.deletion.PROTECT,
                to='fresh_mta.initializationcertification')),
        migrations.AddField(model_name='dailyfeedattempt', name='master_revision',
            field=models.ForeignKey(blank=True, null=True, related_name='daily_feed_attempts',
                on_delete=django.db.models.deletion.PROTECT,
                to='fresh_mta.masterinputrevision')),
        migrations.AddConstraint(model_name='dailyfeedattempt',
            constraint=bounded('accepted_facts', 'csv_accepted_facts_bound')),
        migrations.AddConstraint(model_name='dailyfeedattempt',
            constraint=bounded('prepared_context', 'csv_prepared_context_bound')),
    ]
