import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
import winshell
from win32com.client import Dispatch
from dotenv import load_dotenv

from logger_config import setup_logger
setup_logger()

import logging
logger = logging.getLogger(__name__)

# Change this to your script name
script_name = "ExeGenerator.py"  # This should remain as is

# Get the current directory
current_dir = Path(__file__).parent.resolve()

env_path = Path(__file__).parent  / ".env"
load_dotenv(dotenv_path=env_path)

exe_name = os.getenv("EXE_NAME") or "UserServiceExecutable"

#validation added for exe name if it does not contain any
if not re.match(r'^[a-zA-Z0-9_-]+$', exe_name) or len(exe_name) > 100:
    logger.error(f"Invalid EXE_NAME '{exe_name}', using default")
    exe_name = "UserServiceExecutable"

exe_name = Path(exe_name).name
if not exe_name:  # If name returns empty 
    exe_name = "UserServiceExecutable"

logger.info(f"Using EXE name: {exe_name}")

# Define paths for the EXE and shortcut
exe_path = current_dir / f"{exe_name}.exe"

# Get paths for user and system startup folders
user_startup_folder = Path(winshell.startup())  # Current user's startup
system_startup_folder = Path(os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs\Startup"))

# Function to remove existing shortcuts
def remove_existing_shortcuts(startup_folder):
    for shortcut in startup_folder.glob("*.lnk"):
        try:
            shell = Dispatch("WScript.Shell")
            shortcut_obj = shell.CreateShortcut(str(shortcut))
            if shortcut_obj.TargetPath == str(exe_path):  # Remove only shortcuts pointing to this EXE
                logger.info(f"Removing existing shortcut: {shortcut}")
                shortcut.unlink()
        except Exception as e:
            logger.error(f"Error removing {shortcut}: {e}")

# Step 1: Remove existing EXE if it exists
if exe_path.exists():
    logger.info(f"Removing existing {exe_name}.exe...")
    exe_path.unlink()

# Step 2: Remove existing shortcuts from both user and system startup folders
remove_existing_shortcuts(user_startup_folder)
remove_existing_shortcuts(system_startup_folder)

# Step 3: Define the PyInstaller command
subprocess.run([
    sys.executable, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--icon=Favicon_White.ico",
    f"--name={exe_name}",
    script_name
], check=True)

# Step 5: Move the generated EXE to the script's directory
dist_exe_path = current_dir / "dist" / f"{exe_name}.exe"

if dist_exe_path.exists():
    logger.info(f"Moving {exe_name}.exe to current directory")
    shutil.move(str(dist_exe_path), str(exe_path))

# Step 6: Remove build and dist folders
shutil.rmtree(current_dir / "build", ignore_errors=True)
shutil.rmtree(current_dir / "dist", ignore_errors=True)

# Step 7: Create a new shortcut in the Windows Startup folder
new_shortcut_path = user_startup_folder / f"{exe_name}.lnk"

shell = Dispatch("WScript.Shell")
shortcut = shell.CreateShortcut(str(new_shortcut_path))
shortcut.TargetPath = str(exe_path)
shortcut.WorkingDirectory = str(current_dir)
shortcut.Description = f"Shortcut for {exe_name}"
shortcut.IconLocation = str(current_dir / "Favicon_White.ico")  # Ensure the icon file exists
shortcut.Save()

logger.info(f"New shortcut created in Startup folder: {new_shortcut_path}")

def run_exe(exe_path):
    if os.path.exists(exe_path):
        try:
            # Run the executable
            subprocess.Popen([exe_path])
            logger.info(f"Running: {exe_path}")
        except Exception as e:
            logger.error(f"Error running {exe_path}: {e}")
    else:
        logger.error(f"File not found: {exe_path}")

run_exe(exe_path)