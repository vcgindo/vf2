# from django.db import connection, transaction
from datetime import datetime as dt, timedelta
from ist.models import ISTStatus, ISTStatusHistory
from django.forms.models import model_to_dict
from django.db.models import Q
from django.db import models, transaction
from apps.settings import DAYS_BEFORE_HISTORICAL_TRANSFER
from asyncio.log import logger

def move_old_ist_statuses_to_history():
    try:
        with transaction.atomic():
            # Set threshold date to 30 days ago
            threshold_date = dt.now() - timedelta(days=DAYS_BEFORE_HISTORICAL_TRANSFER)

            # List of statuses that are allowed to be moved to history
            statuses_to_be_moved = ['EXPIRY', 'GRN', 'PAUSE', 'REJECT', 'FORCED CLOSURE', 'TERMINATED', 'OVERLOOKED', 'EXPIRED']

            # Construct the query
            combined_query = Q(updated_at__lt=threshold_date, status__in=statuses_to_be_moved)

            # Fetch entries from the last 30 days and older entries with specific statuses
            ist_instances = ISTStatus.objects.filter(combined_query)

            if ist_instances.exists():
                # Create ISTStatusHistory instances using bulk_create
                ist_history_instances = [ISTStatusHistory(**model_to_dict(ist_instance, exclude=['id'])) for ist_instance in ist_instances]
                ISTStatusHistory.objects.bulk_create(ist_history_instances)

                # Delete the entries from IST_STATUS if the query_set is not empty
                ist_instances.delete()

    except Exception as e:
        # Handle exceptions or log the error
        logger.info("Error while moving IST statuses to history")