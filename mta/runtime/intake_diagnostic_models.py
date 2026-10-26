"""Immutable failure facts and diagnostic files, never successful day owners."""
import uuid
from django.db import models
from django.db.models import Q
from mta.runtime.sql_datetime import SqlDateTimeField
from mta.runtime.ingestion_models import bounded


class IntakeDiagnostic(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    initialization=models.ForeignKey('fresh_mta.ProductionInitialization',on_delete=models.PROTECT)
    run=models.ForeignKey('fresh_mta.CalculationRun',null=True,on_delete=models.PROTECT)
    scope_attempt=models.OneToOneField('fresh_mta.RunScopeAttempt',null=True,on_delete=models.PROTECT)
    feed_attempt=models.ForeignKey('fresh_mta.DailyFeedAttempt',null=True,on_delete=models.PROTECT)
    kind=models.CharField(max_length=8)
    stage=models.CharField(max_length=40)
    business_date=models.DateField()
    clock=SqlDateTimeField()
    input_digest=models.CharField(max_length=64)
    source_digest=models.CharField(max_length=64)
    configuration_digest=models.CharField(max_length=64)
    recipe_digest=models.CharField(max_length=64)
    # Bounded provenance only: paths, source identities, producer error text.
    # Rejections, abort reasons, settings and file observations are typed below.
    metadata=models.JSONField(default=dict)
    rejection_count=models.PositiveBigIntegerField(default=0)
    abort_count=models.PositiveBigIntegerField(default=0)
    observation_count=models.PositiveBigIntegerField(default=0)
    setting_count=models.PositiveBigIntegerField(default=0)
    digest=models.CharField(max_length=64)
    created_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints=[
            models.CheckConstraint(condition=(Q(kind='IMPORTER',run__isnull=False)
                |Q(kind='FULLKIT',run__isnull=True,scope_attempt__isnull=True,feed_attempt__isnull=True)),
                name='intake_diagnostic_kind_owner'),
            models.UniqueConstraint(fields=('run',),condition=Q(kind='IMPORTER',scope_attempt__isnull=True),
                name='intake_diagnostic_full_run'),
            bounded('metadata','intake_diagnostic_metadata_bound'),
        ]


class _Fact(models.Model):
    diagnostic=models.ForeignKey(IntakeDiagnostic,on_delete=models.PROTECT)
    ordinal=models.PositiveBigIntegerField()

    class Meta:
        abstract=True
        constraints=[models.UniqueConstraint(fields=('diagnostic','ordinal'),name='%(class)s_ordinal')]


class IntakeRejection(_Fact):
    SKUCode=models.CharField(max_length=50)
    WhCode=models.CharField(max_length=50)
    RejectionDate=SqlDateTimeField()
    ReasonCode=models.IntegerField()
    ReasonDescription=models.CharField(max_length=100,null=True)


class IntakeAbortReason(_Fact):
    FileId=models.IntegerField()
    RunDateTime=SqlDateTimeField()
    Reason=models.CharField(max_length=512)
    inherited=models.BooleanField()


class IntakeFileObservation(_Fact):
    # Preserve original native configuration, including stale pre-check cells.
    Id=models.IntegerField()
    Path=models.CharField(max_length=150)
    FileName=models.CharField(max_length=100)
    Type=models.CharField(max_length=20)
    initial_exists=models.BooleanField()
    initial_resolved_path=models.CharField(max_length=150,null=True)
    initial_resolved_name=models.CharField(max_length=100,null=True)
    Exists=models.BooleanField()
    ResolvedPath=models.CharField(max_length=150)
    ResolvedFileName=models.CharField(max_length=100)
    member=models.CharField(max_length=120,null=True)
    sha256=models.CharField(max_length=64,null=True)
    size_bytes=models.PositiveBigIntegerField(null=True)

    class Meta(_Fact.Meta):
        constraints=_Fact.Meta.constraints+[
            models.UniqueConstraint(fields=('diagnostic','Id'),name='intake_file_native_id'),
            models.CheckConstraint(condition=(Q(Exists=True,member__isnull=False,sha256__isnull=False,size_bytes__isnull=False)
                |Q(Exists=False,member__isnull=True,sha256__isnull=True,size_bytes__isnull=True)),
                name='intake_observation_presence'),
        ]


class IntakeFullkitSetting(_Fact):
    Parameter=models.CharField(max_length=50)
    initial_value=models.TextField()
    final_value=models.TextField()


class IntakeDiagnosticArchive(models.Model):
    """One original O7 ZIP and its sole native CSV member; no repair guessing."""
    diagnostic=models.OneToOneField(IntakeDiagnostic,primary_key=True,on_delete=models.PROTECT)
    root=models.TextField(unique=True)
    relative_path=models.CharField(max_length=150)
    sha256=models.CharField(max_length=64)
    size_bytes=models.PositiveBigIntegerField()
    member=models.CharField(max_length=100)
    member_sha256=models.CharField(max_length=64)
    member_size_bytes=models.PositiveBigIntegerField()
    recipe_digest=models.CharField(max_length=64)
    digest=models.CharField(max_length=64)
    created_at=models.DateTimeField(auto_now_add=True)


class DiagnosticPublication(models.Model):
    """Append-only source-local file replacement order, matching the UI selector.

    The publisher serializes on initialization. Readers select this explicit
    publication order, never infer a latest calculation or operational attempt.
    """
    initialization=models.ForeignKey('fresh_mta.ProductionInitialization',on_delete=models.PROTECT)
    selector=models.CharField(max_length=50)
    failure_archive=models.OneToOneField(IntakeDiagnosticArchive,null=True,on_delete=models.PROTECT)
    operational_file=models.OneToOneField('fresh_mta.OperationalFile',null=True,on_delete=models.PROTECT)
    digest=models.CharField(max_length=64)
    published_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints=[models.CheckConstraint(condition=(
            Q(failure_archive__isnull=False,operational_file__isnull=True)
            |Q(failure_archive__isnull=True,operational_file__isnull=False)),
            name='diagnostic_publication_one_owner')]
        indexes=[models.Index(fields=('initialization','selector','-id'),name='diagnostic_source_selector')]
