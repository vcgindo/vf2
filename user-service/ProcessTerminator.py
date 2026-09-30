import psutil
import os

from logger_config import setup_logger
setup_logger()

import logging
logger = logging.getLogger(__name__)

def kill_uvicorn_and_celery_in_current_directory():
    current_dir = os.path.abspath(os.getcwd())

    for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline', 'cwd']):
        try:
            name = proc.info['name']
            cmdline = proc.info['cmdline']
            cwd = proc.info.get('cwd')

            if not (name and cmdline and cwd):
                continue

            cwd = os.path.abspath(cwd)

            # Match Uvicorn
            if (
                name.lower() == 'python.exe'
                and '-m' in cmdline
                and 'uvicorn' in cmdline
                and cwd == current_dir
            ):
                logger.info(f"Found Uvicorn PID {proc.pid}")
                for child in proc.children(recursive=True):
                    logger.info(f"  Killing child PID {child.pid}")
                    child.kill()
                proc.kill()
                logger.info(f"Uvicorn PID {proc.pid} killed.")

            # Match Celery Worker or Beat
            elif (
                name.lower() == 'python.exe'
                and '-m' in cmdline
                and 'celery' in cmdline
                and cwd == current_dir
            ):
                logger.info(f"Found Celery PID {proc.pid} ({' '.join(cmdline)})")
                for child in proc.children(recursive=True):
                    logger.info(f"  Killing child PID {child.pid}")
                    child.kill()
                proc.kill()
                logger.info(f"Celery PID {proc.pid} killed.")

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            logger.error(f"Process error: {e}")
            continue

if __name__ == "__main__":
    kill_uvicorn_and_celery_in_current_directory()
