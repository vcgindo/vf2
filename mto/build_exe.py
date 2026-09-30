import os
import shutil
import subprocess
import sys
from pathlib import Path
import winshell
from win32com.client import Dispatch
from dotenv import load_dotenv
# Change this to your script name
script_name = "ExeGenerator.py"  # This should remain as is

# Get the current directory
current_dir = Path(__file__).parent.resolve()

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Define the EXE name
exe_name = os.getenv("EXE_NAME") or "MTO_EXECUTABLE"  # Change this as needed example :   MTO_Backend_PORT_NUMBER
print("EXE NAME",exe_name)
# Define paths for the EXE and shortcut
exe_path = current_dir / f"{exe_name}.exe"
startup_folder = Path(winshell.startup())
shortcut_path = startup_folder / f"{exe_name}.lnk"

# Step 1: Remove existing EXE if it exists
if exe_path.exists():
    print(f"Removing existing {exe_name}.exe...")
    exe_path.unlink()

# Step 2: Remove existing shortcut if it exists
if shortcut_path.exists():
    print(f"Removing existing shortcut from Startup folder...")
    shortcut_path.unlink()

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
    print(f"Moving {exe_name}.exe to {current_dir}")
    shutil.move(str(dist_exe_path), str(exe_path))

# Step 6: Remove build and dist folders
shutil.rmtree(current_dir / "build", ignore_errors=True)
shutil.rmtree(current_dir / "dist", ignore_errors=True)

# Step 7: Create a new shortcut in the Windows Startup folder
shell = Dispatch("WScript.Shell")
shortcut = shell.CreateShortcut(str(shortcut_path))
shortcut.TargetPath = str(exe_path)
shortcut.WorkingDirectory = str(current_dir)
shortcut.Description = f"Shortcut for {exe_name}"
shortcut.IconLocation = str(current_dir / "Favicon_White.ico")  # Ensure the icon file exists
shortcut.Save()

print(f"Shortcut created in Startup folder: {shortcut_path}")


def run_exe(exe_path):
    if os.path.exists(exe_path):
        try:
            # Run the executable
            subprocess.Popen([exe_path], shell=True)
            print(f"Running: {exe_path}")
        except Exception as e:
            print(f"Error running {exe_path}: {e}")
    else:
        print(f"File not found: {exe_path}")
 
run_exe(exe_path)