import logging
from apps.settings import LOG_FOLDER
from datetime import datetime
import os

def get_logger(name):
    logger = logging.getLogger(name)
    log_file_path = os.path.join(
        LOG_FOLDER, f'{datetime.now().strftime("%Y-%m-%d")}.log')
    if not os.path.exists(log_file_path):
        with open(log_file_path, 'w') as file:
            pass 
    fh = logging.FileHandler(log_file_path)
    fh.setLevel(logging.DEBUG)

    # create console handler with a higher log level
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    return logger