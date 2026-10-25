"""Immutable phase read references, separate from whole-scope readiness."""
import uuid
from django.db import models


class ScopeReadReference(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    # Null identifies the original generation cut. Later DBM actions advance
    # this reference without changing the accepted report generation's cut.
    action_command=models.ForeignKey('fresh_mta.RunCommand',null=True,blank=True,
        on_delete=models.PROTECT,related_name='scope_read_references')
    previous_reference=models.ForeignKey('self',null=True,blank=True,
        on_delete=models.PROTECT,related_name='next_references')
    report_generation=models.ForeignKey('fresh_mta.ScopeReportGeneration',on_delete=models.PROTECT)
    git_generation=models.ForeignKey('fresh_mta.ScopeGitGeneration',on_delete=models.PROTECT)
    expedite_parent_generation=models.ForeignKey('fresh_mta.ScopeExpediteParentGeneration',on_delete=models.PROTECT)
    pick_files=models.ForeignKey('fresh_mta.ScopePickFiles',on_delete=models.PROTECT)
    recipe_digest=models.CharField(max_length=64)
    runtime_reports_digest=models.CharField(max_length=64)
    metadata=models.JSONField()  # finite dependency identities only, never report rows
    digest=models.CharField(max_length=64,unique=True)
    created_at=models.DateTimeField(auto_now_add=True)
