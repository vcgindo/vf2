"""Bounded commitments for typed operational storage, not business payloads."""
import uuid

from django.db import models
from django.db.models.functions import Length
from django.db.models.lookups import LessThanOrEqual


class OperationalStateCut(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    initialization = models.ForeignKey('fresh_mta.ProductionInitialization', on_delete=models.PROTECT)
    family = models.CharField(max_length=48)
    position = models.PositiveBigIntegerField()
    run = models.ForeignKey('fresh_mta.CalculationRun', null=True, on_delete=models.PROTECT)
    parent = models.ForeignKey('self', null=True, on_delete=models.PROTECT)
    input_digest = models.CharField(max_length=64)
    settings_digest = models.CharField(max_length=64)
    # Canonical JSON text, containing only fixed context and delta commitments.
    # SQL verifies its hash and seal context. Payload cells live in typed tables.
    root_body = models.TextField(default='')
    root_digest = models.CharField(max_length=64, default='')

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(family__in=(
                'rationing_history', 'closing/dbm/DailyConsumption',
                'closing/dbm/OrderData', 'closing/dbm/OrderDataSummary',
                'closing/dbm/SuggestionsLog', 'closing/dbm/DiscardedSuggestions',
                'closing/dbm/SpikeReport', 'closing/dbm/SuspendHistory',
                'closing/bpr/DailyConsumption','closing/orders/SpikeOrderClosureHistory')),
                                   name='state_cut_qualified_family'),
            models.CheckConstraint(condition=(models.Q(position=0, parent__isnull=True) |
                models.Q(position__gt=0, parent__isnull=False, run__isnull=False)),
                name='state_cut_parent_shape'),
            models.UniqueConstraint(fields=('initialization', 'family', 'position'),
                                    name='state_cut_position'),
            models.UniqueConstraint(fields=('initialization', 'family', 'run'),
                                    condition=models.Q(run__isnull=False), name='state_cut_run'),
            models.CheckConstraint(condition=LessThanOrEqual(Length('root_body'), models.Value(32768)),
                                   name='state_cut_root_bound'),
        ]
