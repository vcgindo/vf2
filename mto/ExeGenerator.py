import subprocess
import os
import ctypes
import sys
from dotenv import load_dotenv
from pathlib import Path

# Get the current working directory
current_dir = os.getcwd()

env_path = os.path.join(current_dir, ".env")
load_dotenv(dotenv_path=env_path)
asgi_path = os.getenv('ASGI_PATH')

port_number = os.getenv("PORT_NUMBER") or 8000
# Define the paths for the virtual environment Python and manage.py
venv_python = os.path.join(current_dir, "venv", "Scripts", "python.exe")
manage_py = os.path.join(current_dir, "manage.py")

# Verify the paths
if not os.path.isfile(venv_python):

    ctypes.windll.user32.MessageBoxW(0, f"Error: Python executable not found at {venv_python}", "Error", 0x10)
    sys.exit(1)

if not os.path.isfile(manage_py):
    ctypes.windll.user32.MessageBoxW(0, f"Error: manage.py not found in {current_dir}", "Error", 0x10)
    sys.exit(1)
# Start the server if paths are valid
try:
    # Start the Django server
    subprocess.Popen(
         [
                str(venv_python), "-m", "uvicorn", asgi_path,
                "--host", "0.0.0.0",
                "--port", str(port_number)
            ],
        cwd=current_dir,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    ctypes.windll.user32.MessageBoxW(0, f"Server started successfully on 0.0.0.0:{port_number}", "Success", 0x40)
except Exception as e:
    ctypes.windll.user32.MessageBoxW(0, f"Error: {str(e)}", "Error", 0x10)
    sys.exit(1)
