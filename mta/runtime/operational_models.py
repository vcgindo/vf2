"""Run-owned operational effects; these rows never authorize publication."""
import uuid
from django.db import models
from mta.runtime.models import CalculationRun


class OperationalConfiguration(models.Model):
    digest = models.CharField(max_length=64, primary_key=True)
    policy = models.CharField(max_length=80)
    source_digest = models.CharField(max_length=64)
    # Bounded tool/path/format and provenance metadata only, never table rows.
    bindings = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)


class OperationalSetting(models.Model):
    configuration = models.ForeignKey(OperationalConfiguration, on_delete=models.PROTECT)
    ordinal = models.PositiveIntegerField()
    name = models.TextField()
    value = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['configuration','ordinal'], name='op_setting_ordinal')]


class OperationalInputTable(models.Model):
    configuration = models.ForeignKey(OperationalConfiguration, on_delete=models.PROTECT)
    ordinal = models.PositiveIntegerField()
    database_name = models.TextField(null=True)
    table_name = models.TextField(null=True)
    condition = models.TextField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['configuration','ordinal'], name='op_input_table_ordinal')]


class OperationalAlertSetting(models.Model):
    configuration = models.ForeignKey(OperationalConfiguration, on_delete=models.PROTECT)
    ordinal = models.PositiveIntegerField()
    name = models.TextField(null=True)
    active = models.BooleanField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['configuration','ordinal'], name='op_alert_setting_ordinal')]


class OperationalAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    configuration = models.ForeignKey(OperationalConfiguration, on_delete=models.PROTECT)
    retry_of = models.ForeignKey('self', null=True, related_name='retries', on_delete=models.PROTECT)
    repair_of = models.ForeignKey('self', null=True, related_name='repairs', on_delete=models.PROTECT)
    predecessor = models.ForeignKey('self', null=True, related_name='successors', on_delete=models.PROTECT)
    request_key = models.CharField(max_length=120, unique=True)
    business_date = models.DateField()
    run_output_digest = models.CharField(max_length=64)
    action_digest = models.CharField(max_length=64)
    source_digest = models.CharField(max_length=64)
    # Snapshot clock is frozen for recovery, distinct from the business date.
    clock = models.DateTimeField()
    root = models.TextField(unique=True)
    status = models.CharField(max_length=16, default='PENDING')
    failure = models.TextField(default='')
    lease_key = models.BigIntegerField(null=True)
    lease_owner = models.UUIDField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(status__in=[
            'PENDING','RUNNING','FAILED','SUCCEEDED']),name='op_attempt_status')]


class OperationalOperation(models.Model):
    attempt = models.ForeignKey(OperationalAttempt, related_name='operations', on_delete=models.PROTECT)
    ordinal = models.PositiveIntegerField()
    group = models.CharField(max_length=2)
    name = models.CharField(max_length=120)
    stage = models.CharField(max_length=80)
    source_digest = models.CharField(max_length=64)
    status = models.CharField(max_length=16, default='PENDING')
    reason = models.TextField(default='')
    started_at = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['attempt','ordinal'],name='op_operation_ordinal'),
            models.UniqueConstraint(fields=['attempt','name'],name='op_operation_name'),
            models.CheckConstraint(condition=models.Q(status__in=[
                'PENDING','RUNNING','FAILED','SUCCEEDED','DISABLED','UNAVAILABLE']),name='op_operation_status')]


class OperationalFile(models.Model):
    operation = models.ForeignKey(OperationalOperation, related_name='files', on_delete=models.PROTECT)
    relative_path = models.TextField()
    role = models.CharField(max_length=24)
    sha256 = models.CharField(max_length=64)
    size_bytes = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['operation','relative_path'],name='op_file_path')]


class OperationalArchiveMember(models.Model):
    archive = models.ForeignKey(OperationalFile, related_name='members', on_delete=models.PROTECT)
    ordinal = models.PositiveIntegerField()
    name = models.TextField()
    sha256 = models.CharField(max_length=64)
    size_bytes = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['archive','ordinal'],name='op_member_ordinal')]


class OperationalRepairTarget(models.Model):
    attempt = models.ForeignKey(OperationalAttempt,related_name='repair_targets',on_delete=models.PROTECT)
    ordinal = models.PositiveIntegerField()
    original_file = models.ForeignKey(OperationalFile,related_name='repair_targets',on_delete=models.PROTECT)
    replacement_file = models.OneToOneField(OperationalFile,null=True,related_name='replacement_target',on_delete=models.PROTECT)
    equivalence = models.CharField(max_length=24,default='')

    class Meta:
        constraints=[
            models.UniqueConstraint(fields=['attempt','ordinal'],name='op_repair_target_ordinal'),
            models.UniqueConstraint(fields=['attempt','original_file'],name='op_repair_target_file'),
        ]


class OperationalAlertIntent(models.Model):
    """An evaluated local intent; never an email transmission or queue."""
    run = models.ForeignKey(CalculationRun, on_delete=models.PROTECT)
    configuration = models.ForeignKey(OperationalConfiguration, on_delete=models.PROTECT)
    identity = models.CharField(max_length=64, unique=True)
    alert_name = models.TextField()
    branch = models.CharField(max_length=120)
    stage = models.CharField(max_length=80)
    business_date = models.DateField()
    source_digest = models.CharField(max_length=64)
    recipients = models.TextField()
    subject = models.TextField(null=True)
    body = models.TextField(null=True)
    disposition = models.CharField(max_length=24)
    reason = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(disposition__in=[
            'LOCAL_READY','DISABLED','PREDICATE_FALSE','RECIPIENT_SUPPRESSED',
            'ATTACHMENT_UNAVAILABLE']),name='op_intent_disposition')]


class OperationalIntentAttachment(models.Model):
    intent = models.ForeignKey(OperationalAlertIntent, related_name='attachments', on_delete=models.PROTECT)
    ordinal = models.PositiveIntegerField()
    relative_path = models.TextField()
    sha256 = models.CharField(max_length=64)
    size_bytes = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['intent','ordinal'],name='op_intent_attachment_ord')]


class OperationalIntentEvaluation(models.Model):
    operation = models.ForeignKey(OperationalOperation, on_delete=models.PROTECT)
    intent = models.ForeignKey(OperationalAlertIntent, on_delete=models.PROTECT)
    evaluated_digest = models.CharField(max_length=64)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['operation','intent'],name='op_intent_evaluation')]


class OperationalBackup(models.Model):
    operation = models.ForeignKey(OperationalOperation, related_name='backups', on_delete=models.PROTECT)
    database_name = models.TextField()
    database_system = models.CharField(max_length=16)
    method = models.CharField(max_length=40)
    snapshot_identity = models.TextField()
    tool_sha256 = models.CharField(max_length=64)
    file = models.OneToOneField(OperationalFile, on_delete=models.PROTECT)
    base_backup = models.ForeignKey('self', null=True, on_delete=models.PROTECT)
    logical_digest = models.CharField(max_length=64)
    restore_target = models.TextField(default='')
    restore_status = models.CharField(max_length=16, default='UNPROVED')
    restored_digest = models.CharField(max_length=64, default='')
    qualification = models.CharField(max_length=80, default='')
    qualification_sha256 = models.CharField(max_length=64, default='')

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(restore_status__in=[
            'UNPROVED','RUNNING','FAILED','VERIFIED','QUALIFIED']),name='op_restore_status')]
