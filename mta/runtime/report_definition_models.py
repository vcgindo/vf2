"""Typed immutable definition/initial-seed owners for future report captures.

The separate database registration guards and admitted command are required
before these draft tables can be used. There is no automatic default registry.
"""
from django.db import models
from mta.runtime.ingestion_models import bounded


class ReportDefinitionRegistration(models.Model):
    id = models.CharField(max_length=64, primary_key=True)
    initialization = models.ForeignKey('fresh_mta.ProductionInitialization', on_delete=models.PROTECT)
    certificate = models.ForeignKey('fresh_mta.InitializationCertification', on_delete=models.PROTECT)
    schema = models.CharField(max_length=64)
    source_digest = models.CharField(max_length=64)
    certificate_digest = models.CharField(max_length=64)
    configuration_digest = models.CharField(max_length=64)
    definition_digest = models.CharField(max_length=64)
    seed_digest = models.CharField(max_length=64)
    policy_digest = models.CharField(max_length=64)
    reference_digest = models.CharField(max_length=64)
    # Only bounded hook/disposition/initial catalogue authority metadata.
    # Report definitions and settings are in the typed relations below.
    policy = models.JSONField()
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [bounded('policy', 'report_definition_policy_bound')]


class RegisteredRuntimeReport(models.Model):
    registration = models.ForeignKey(ReportDefinitionRegistration, on_delete=models.PROTECT,
                                     related_name='report_rows')
    ordinal = models.PositiveIntegerField()
    Id = models.IntegerField()
    ReportName = models.CharField(max_length=50)
    Query = models.TextField()
    BaseDB = models.CharField(max_length=50)
    HeaderList = models.TextField(null=True)
    FileName = models.CharField(max_length=500)
    DestFolder = models.CharField(max_length=500)
    Extension = models.CharField(max_length=10)
    Delimeter = models.CharField(max_length=10, null=True)
    TemplateName = models.CharField(max_length=50, null=True)
    TemplateLoc = models.CharField(max_length=500, null=True)
    Placement = models.CharField(max_length=50)
    Compression = models.BooleanField()
    DeleteOldFile = models.BooleanField()
    Active = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('registration', 'ordinal'), name='report_definition_ordinal'),
            models.UniqueConstraint(fields=('registration', 'Id'), name='report_definition_native_id'),
        ]


class RegisteredRuntimeReportSeed(models.Model):
    definition = models.OneToOneField(RegisteredRuntimeReport, primary_key=True,
                                     on_delete=models.PROTECT, related_name='initial_seed')
    LastGeneratedFileName = models.CharField(max_length=500, null=True)


class RegisteredDownloadableUiSetting(models.Model):
    registration = models.ForeignKey(ReportDefinitionRegistration, on_delete=models.PROTECT,
                                     related_name='ui_rows')
    ordinal = models.PositiveIntegerField()
    ReportName = models.CharField(max_length=100)
    Active = models.BooleanField(null=True)
    GenerationScope = models.CharField(max_length=50, null=True)
    DestFolder = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('registration', 'ordinal'), name='report_ui_setting_ordinal'),
            models.UniqueConstraint(fields=('registration', 'ReportName'), name='report_ui_setting_native_name'),
        ]
