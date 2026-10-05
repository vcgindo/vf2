"""Persist exact per-occurrence Research availability band counts."""
import django.db.models.deletion
from django.db import migrations, models

from mta.presentation import research_availability_preparation


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0039_research_availability_cover')]

    operations = [
        migrations.CreateModel(
            name='ResearchAvailabilityBandProjection',
            fields=[
                ('run', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,
                                             primary_key=True, serialize=False,
                                             to='fresh_mta.calculationrun')),
                ('status', models.CharField(default='READY', max_length=16)),
                ('source_digest', models.CharField(max_length=64)),
                ('membership_digest', models.CharField(max_length=64)),
                ('recipe_digest', models.CharField(max_length=64)),
                ('row_count', models.PositiveBigIntegerField()),
                ('rows_digest', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'constraints': [models.CheckConstraint(
                condition=models.Q(('status', 'READY')),
                name='research_availability_band_ready')]},
        ),
        migrations.CreateModel(
            name='ResearchAvailabilityBand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name='ID')),
                ('ordinal', models.PositiveBigIntegerField()),
                ('history_ordinal', models.BigIntegerField()),
                ('sku_code', models.TextField()),
                ('location_code', models.TextField()),
                ('black_01_30', models.PositiveSmallIntegerField()),
                ('recognized_01_30', models.PositiveSmallIntegerField()),
                ('black_31_60', models.PositiveSmallIntegerField()),
                ('recognized_31_60', models.PositiveSmallIntegerField()),
                ('black_61_90', models.PositiveSmallIntegerField()),
                ('recognized_61_90', models.PositiveSmallIntegerField()),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                                          to='fresh_mta.calculationrun')),
            ],
            options={
                'constraints': [models.UniqueConstraint(
                    fields=('run', 'ordinal'), name='research_availability_band_ord')],
                'indexes': [models.Index(fields=['run','sku_code','location_code'],
                                         name='research_avail_band_scope')],
            },
        ),
        migrations.RunSQL(
            research_availability_preparation.FORWARD,
            research_availability_preparation.REVERSE,
        ),
    ]
