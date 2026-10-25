"""Typed live remark owners and immutable per-run capture rows."""
from django.db import models

from mta.runtime.models import CalculationRun


class RemarkOwner(models.Model):
    family = models.CharField(max_length=32, primary_key=True)
    provenance_digest = models.CharField(max_length=64)
    provenance_receipt = models.JSONField()
    next_ordinal = models.PositiveBigIntegerField(default=0)
    initialized_at = models.DateTimeField(auto_now_add=True)


class RemarkCapture(models.Model):
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    family = models.CharField(max_length=32)
    provenance_digest = models.CharField(max_length=64)
    watermark = models.PositiveBigIntegerField()
    cutoff = models.DateTimeField(null=True)
    row_count = models.PositiveBigIntegerField()
    rows_digest = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['run', 'family'], name='remark_capture_family')]


class _LiveRemark(models.Model):
    owner = models.ForeignKey(RemarkOwner, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    actor_id = models.CharField(max_length=256)
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    Remark = models.TextField(null=True)
    RemarkDate = models.DateTimeField()

    class Meta:
        abstract = True


class BprLiveRemark(_LiveRemark):
    Username = models.CharField(max_length=100, null=True)
    # Internal append ownership only; the database stamps the full transaction
    # identity. Empty identifies older rows with no recorded transaction owner.
    append_transaction = models.CharField(max_length=20, default='', editable=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['owner', 'ordinal'], name='bpr_live_remark_ord')]


class BorLiveRemarkDaily(_LiveRemark):
    Username = models.CharField(max_length=100, null=True)
    SupplierCode = models.CharField(max_length=50)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['owner', 'ordinal'], name='bor_live_remark_ord_daily')]


class BorOaLiveRemarkDaily(_LiveRemark):
    Username = models.CharField(max_length=50, null=True)
    SupplierCode = models.CharField(max_length=50)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['owner', 'ordinal'], name='boroa_live_remark_ord_daily')]


class _CapturedRemark(models.Model):
    capture = models.ForeignKey(RemarkCapture, on_delete=models.PROTECT)
    ordinal = models.PositiveBigIntegerField()
    source_ordinal = models.PositiveBigIntegerField()
    SKUCode = models.CharField(max_length=50)
    WhCode = models.CharField(max_length=50)
    Remark = models.TextField(null=True)
    RemarkDate = models.DateTimeField()

    class Meta:
        abstract = True


class BprCapturedRemark(_CapturedRemark):
    Username = models.CharField(max_length=100, null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['capture', 'ordinal'], name='bpr_captured_remark_ord')]


class BorCapturedRemark(_CapturedRemark):
    Username = models.CharField(max_length=100, null=True)
    SupplierCode = models.CharField(max_length=50)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['capture', 'ordinal'], name='bor_captured_remark_ord')]


class BorOaCapturedRemark(_CapturedRemark):
    Username = models.CharField(max_length=50, null=True)
    SupplierCode = models.CharField(max_length=50)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['capture', 'ordinal'], name='boroa_captured_remark_ord')]
