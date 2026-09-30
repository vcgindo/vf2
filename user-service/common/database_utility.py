import subprocess
import os 
import datetime
from datetime import date
from apps.settings import DB_HOST, DB_PORT, DB_USER, DB_NAME, DB_PASSWORD, DB_BACKUP_FOLDER
from common.logger import get_logger


logger = get_logger(__name__)


def delete_old_db_backups():
    for i in os.listdir(DB_BACKUP_FOLDER):
        backup_file_modification_timestamp = os.path.getmtime(os.path.join(DB_BACKUP_FOLDER,i))
        backup_file_modification_date = datetime.datetime.fromtimestamp(backup_file_modification_timestamp).date()

        if (datetime.date.today() - backup_file_modification_date).days > 30: 
            os.remove(os.path.join(DB_BACKUP_FOLDER,i))

def backup_database():
    os.environ['PGPASSWORD'] = DB_PASSWORD

    output_file = '{}/retail_local_db_{}.sql'.format(DB_BACKUP_FOLDER, date.today().strftime("%d%m%Y"))  

    pg_dump_cmd = [
        'pg_dump',
        '-U', DB_USER,
        '-h', DB_HOST,
        '-p', DB_PORT,
        '-d', DB_NAME,
        '-F', 'c',  
        '>', output_file
    ]

    try:
        subprocess.run(' '.join(pg_dump_cmd), shell=True, check=True)
        delete_old_db_backups()
    except subprocess.CalledProcessError as e:
        logger.info(f"Backup failed. Error: {e}")
