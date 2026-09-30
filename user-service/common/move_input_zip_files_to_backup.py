import os 
import datetime 
import shutil
from apps.settings import LOCAL_PATH, DAILY_ZIPS_BACKUP_FOLDER, DAYS_BEFORE_ZIP_FILE_TRANSFER_TO_BACKUP, DAYS_BEFORE_ZIP_FILE_DELETE_FROM_BACKUP


# Moving old files (timespan = DAYS_BEFORE_ZIP_FILE_TRANSFER_TO_BACKUP) from ftp local folder to backup folder
def backup_old_input_files(days_before_zip_file_transfer_to_backup = DAYS_BEFORE_ZIP_FILE_TRANSFER_TO_BACKUP, source_folder = LOCAL_PATH, backup_folder = DAILY_ZIPS_BACKUP_FOLDER):
    for i in os.listdir(source_folder):
        backup_file_modification_timestamp = os.path.getmtime(os.path.join(source_folder, i))
        backup_file_modification_date = datetime.datetime.fromtimestamp(backup_file_modification_timestamp).date()

        if (datetime.date.today() - backup_file_modification_date).days > days_before_zip_file_transfer_to_backup:
            shutil.move(os.path.join(source_folder,i), os.path.join(backup_folder,i))

# deleteing old files (timespan = DAYS_BEFORE_ZIP_FILE_DELETE_FROM_BACKUP) from backup folder
def delete_old_input_files(days_before_zip_file_delete_from_backup = DAYS_BEFORE_ZIP_FILE_DELETE_FROM_BACKUP, source_folder = DAILY_ZIPS_BACKUP_FOLDER):
    for i in os.listdir(source_folder):
        backup_file_modification_timestamp = os.path.getmtime(os.path.join(source_folder, i))
        backup_file_modification_date = datetime.datetime.fromtimestamp(backup_file_modification_timestamp).date()

        if (datetime.date.today() - backup_file_modification_date).days > days_before_zip_file_delete_from_backup:
            os.remove(os.path.join(source_folder,i))

