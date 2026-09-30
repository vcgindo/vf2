import subprocess
import os
import ctypes
import sys
from pathlib import Path
from dotenv import load_dotenv

from logger_config import setup_logger
setup_logger()

import logging
logger = logging.getLogger(__name__)

# Get the current working directory
current_dir = os.getcwd()
env_path = os.path.join(current_dir, ".env")
load_dotenv(dotenv_path=env_path)

port_number = os.getenv('PORT_NUMBER') or 9002
asgi_path = os.environ.get('ASGI_PATH')

# Define the paths for the virtual environment Python and manage.py
venv_python = os.path.join(current_dir, "venv", "Scripts", "python.exe")
manage_py = os.path.join(current_dir, "manage.py")

logger.debug("Using virtual environment Python executable")
logger.debug("Using manage.py script")

logs_dir = os.path.join(current_dir, "logs")
os.makedirs(logs_dir, exist_ok=True)

server_log = os.path.join(logs_dir, "server.log")
worker_log = os.path.join(logs_dir, "celery_worker.log")
beat_log = os.path.join(logs_dir, "celery_beat.log")

# Verify the paths
if not os.path.isfile(venv_python):

    ctypes.windll.user32.MessageBoxW(0, f"Error: Python executable not found at {venv_python}", "Error", 0x10)
    sys.exit(1)

if not os.path.isfile(manage_py):
    ctypes.windll.user32.MessageBoxW(0, f"Error: manage.py not found in {current_dir}", "Error", 0x10)
    sys.exit(1)

def start_process(command, log_file=None):
    if log_file:
        log = open(log_file, "a", buffering=1)  # line-buffered logging
        stdout_target = log
        stderr_target = log
    else:
        stdout_target = subprocess.DEVNULL
        stderr_target = subprocess.DEVNULL

    return subprocess.Popen(
        command,
        cwd=current_dir,
        stdout=stdout_target,
        stderr=stderr_target,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

try:
    # --- Start Django server ---
    server_proc = start_process(
        [str(venv_python), "-m", "uvicorn", asgi_path, "--host", "0.0.0.0", "--port", str(port_number)]
    )

    # --- Start Celery worker ---
    worker_proc = start_process(
        [str(venv_python), "-m", "celery", "-A", "apps", "worker", "-l", "info", "-Q", "db_cleanup_queue", "--pool=solo"],
        worker_log
    )

    # --- Start Celery beat ---
    beat_proc = start_process(
        [str(venv_python), "-m", "celery", "-A", "apps", "beat", "-l", "info"],
        beat_log
    )

    ctypes.windll.user32.MessageBoxW(
        0,
        f"Server + Celery started successfully on port {port_number}",
        "Success",
        0x40
    )

except Exception as e:
    ctypes.windll.user32.MessageBoxW(0, f"Error: {e}", "Error", 0x10)
    sys.exit(1)
        