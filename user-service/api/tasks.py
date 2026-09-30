from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import UserAuditInfo
from asyncio.log import logger


@shared_task(queue='db_cleanup_queue')
def clear_old_audit_logs():
    logger.info("Task started!") 
    cutoff_date = timezone.now() - timedelta(days=90)
    deleted_count, _ = UserAuditInfo.objects.filter(log_in__lt=cutoff_date).delete()
    logger.info(f"{deleted_count} old audit log(s) deleted.")
