"""Run-owned typed copies of the eight native upload logs."""
from django.db import models
from mta.runtime.mdm_models import MdmSkuUploadLog, MdmLocationUploadLog
from mta.runtime.mdm_skuloc_models import (MdmSkuLocAddUploadLog,
    MdmSkuLocModifyUploadLog, MdmSkuLocRemoveUploadLog)
from mta.runtime.mdm_supplier_models import MdmSobUploadLog, MdmMoqUploadLog
from mta.runtime.mdm_force_models import MdmForceUploadLog


class NativeUploadAudit(models.Model):
    run = models.OneToOneField('fresh_mta.CalculationRun', primary_key=True, on_delete=models.PROTECT)
    source = models.ForeignKey('fresh_mta.MdmSource', on_delete=models.PROTECT)
    initialization = models.ForeignKey('fresh_mta.ProductionInitialization', on_delete=models.PROTECT)
    predecessor = models.ForeignKey('self', null=True, on_delete=models.PROTECT, related_name='successors')
    origin = models.ForeignKey('self', null=True, on_delete=models.PROTECT, related_name='retries')
    business_date = models.DateField()
    configuration_digest = models.CharField(max_length=64)
    horizon = models.PositiveIntegerField()
    timezone = models.CharField(max_length=128)
    client_folder = models.TextField(null=True)
    status = models.CharField(max_length=8, default='FROZEN')
    frozen_digest = models.CharField(max_length=64)
    terminal_digest = models.CharField(max_length=64, default='')

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(status__in=('FROZEN','SEALED')),
            name='native_audit_status')]


class AuditOccurrence(models.Model):
    capture = models.ForeignKey(NativeUploadAudit, on_delete=models.PROTECT)
    stage = models.CharField(max_length=6)
    source_pk = models.PositiveBigIntegerField()
    ordinal = models.PositiveBigIntegerField()
    retained = models.BooleanField(null=True)

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(fields=('capture','stage','source_pk'), name='%(class)s_pk'),
            models.UniqueConstraint(fields=('capture','stage','ordinal'), name='%(class)s_ord'),
            models.CheckConstraint(condition=(models.Q(stage='FROZEN', retained__isnull=True)
                | models.Q(stage='FINAL', retained__isnull=False)), name='%(class)s_stage')]


def native_fields(source):
    """Copy every producer field with its exact PostgreSQL type/nullability."""
    def attach(cls):
        for field in source._meta.fields:
            if field.name not in ('id','source'):
                cls.add_to_class(field.name, field.clone())
        return cls
    return attach


@native_fields(MdmSkuLocAddUploadLog)
class NativeAuditAdd(AuditOccurrence):
    pass


@native_fields(MdmSkuLocModifyUploadLog)
class NativeAuditModify(AuditOccurrence):
    pass


@native_fields(MdmSkuLocRemoveUploadLog)
class NativeAuditRemove(AuditOccurrence):
    pass


@native_fields(MdmLocationUploadLog)
class NativeAuditLocation(AuditOccurrence):
    pass


@native_fields(MdmSkuUploadLog)
class NativeAuditSku(AuditOccurrence):
    pass


@native_fields(MdmSobUploadLog)
class NativeAuditSob(AuditOccurrence):
    pass


@native_fields(MdmMoqUploadLog)
class NativeAuditMoq(AuditOccurrence):
    pass


@native_fields(MdmForceUploadLog)
class NativeAuditForce(AuditOccurrence):
    pass


BINDINGS = (
    ('UIUploadLogNMSNewItem', MdmSkuLocAddUploadLog, NativeAuditAdd),
    ('UIUploadLogNMSModifyItem', MdmSkuLocModifyUploadLog, NativeAuditModify),
    ('UIUploadLogNMSRemoveItem', MdmSkuLocRemoveUploadLog, NativeAuditRemove),
    ('UIUploadLogNMSLocations', MdmLocationUploadLog, NativeAuditLocation),
    ('UIUploadLogNMSSKUs', MdmSkuUploadLog, NativeAuditSku),
    ('UIUploadLogNMSSOB', MdmSobUploadLog, NativeAuditSob),
    ('UIUploadLogNMSMOQ', MdmMoqUploadLog, NativeAuditMoq),
    ('UIUploadLogFNC', MdmForceUploadLog, NativeAuditForce),
)
