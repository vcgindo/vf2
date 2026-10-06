"""Add an explicit production branch, preserving all fixture predicates/seals."""
from django.db import migrations
from mta.runtime.daily_prepared_schema import FORWARD, REVERSE

class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0053_daily_input_publication')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
