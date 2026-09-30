import os 
import datetime 
from apps.settings import LOG_FOLDER, LOG_RETENTION_DAYS


def delete_old_logs():
    for i in os.listdir(LOG_FOLDER):
        if os.path.isfile(os.path.join(LOG_FOLDER, i )) and i != '.keep':
            backup_file_modification_timestamp = os.path.getmtime(os.path.join(LOG_FOLDER,i))
            backup_file_modification_date = datetime.datetime.fromtimestamp(backup_file_modification_timestamp).date()

            if (datetime.date.today() - backup_file_modification_date).days > LOG_RETENTION_DAYS: 
                os.remove(os.path.join(LOG_FOLDER,i))

