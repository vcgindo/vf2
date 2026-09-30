import os
import sys
import subprocess
from pathlib import Path

# --- Configuration ---
VENV_DIR = "venv"
WHEELS_DIR = "local_wheels"
REQUIREMENTS_FILE = "requirements.txt"
MANAGE_PY_FILE = "manage.py"
BUILD_EXE = "build_exe.py"
# ---------------------

def run_command(command, error_message, capture_output=True):
    """Runs a command, streaming or capturing output, and exits if it fails."""
    try:
        print(f"--- Running command: {' '.join(command)} ---")
        if capture_output:
            process = subprocess.run(
                command, check=True, capture_output=True, text=True, encoding='utf-8'
            )
        else:
            process = subprocess.run(command, check=True)
        
        print("--- Command successful ---\n")
        return process

    except subprocess.CalledProcessError as e:
        print(f"!!! ERROR: {error_message} !!!")
        if capture_output and e.stdout:
            print(f"--- STDOUT ---\n{e.stdout}")
        if capture_output and e.stderr:
            print(f"--- STDERR ---\n{e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"!!! ERROR: Command '{command[0]}' not found. Is Python/venv installed and in your PATH? !!!")
        sys.exit(1)

def perform_pre_flight_checks(requirements_path, wheels_path):
    """Checks if required files and directories exist before starting."""
    print("--- Performing pre-flight checks... ---")
    if not requirements_path.is_file():
        print(f"!!! ERROR: '{REQUIREMENTS_FILE}' not found. This file is required.")
        sys.exit(1)
        
    if not wheels_path.is_dir():
        print(f"!!! ERROR: '{WHEELS_DIR}' directory not found. This script requires local wheel files.")
        sys.exit(1)
    print("--- Checks passed ---\n")

def create_virtual_environment(venv_path):
    """Creates the virtual environment if it doesn't already exist."""
    if not venv_path.is_dir():
        print(f"--- Step 1: Creating virtual environment in '{VENV_DIR}'... ---")
        create_venv_command = [sys.executable, "-m", "venv", VENV_DIR]
        run_command(create_venv_command, "Failed to create virtual environment.")
    else:
        print(f"--- Step 1: Virtual environment '{VENV_DIR}' already exists. Skipping creation. ---\n")

def get_venv_executables(venv_path):
    """Determines the correct paths for the venv's python and pip executables."""
    if sys.platform == "win32":
        venv_python = venv_path / "Scripts" / "python.exe"
    else:
        venv_python = venv_path / "bin" / "python"
    
    pip_command_base = [str(venv_python), "-m", "pip"]
    return venv_python, pip_command_base

def upgrade_pip(pip_command_base):
    """Upgrades pip within the virtual environment."""
    print("--- Upgrading pip... ---")
    upgrade_pip_command = pip_command_base + ["install", "--upgrade", "pip"]
    run_command(upgrade_pip_command, "Failed to upgrade pip.")

def install_build_dependencies(pip_command_base, wheels_path):
    """Installs essential build packages like setuptools and wheel."""
    print(f"--- Step 2: Installing build dependencies (setuptools, wheel) from '{WHEELS_DIR}'... ---")
    install_build_deps_command = pip_command_base + [
        "install",
        "--no-index",
        f"--find-links={wheels_path}",
        "setuptools",
        "wheel",
    ]
    run_command(install_build_deps_command, "Failed to install setuptools and wheel.", capture_output=False)

def install_requirements_from_wheels(pip_command_base, wheels_path, requirements_path):
    """Installs all packages listed in the requirements file from the local wheels."""
    print(f"--- Step 3: Installing all packages from '{WHEELS_DIR}'... ---")
    install_reqs_command = pip_command_base + [
        "install",
        "--no-index",
        f"--find-links={wheels_path}",
        "-r",
        str(requirements_path),
    ]
    run_command(install_reqs_command, f"Failed to install packages from '{WHEELS_DIR}'.", capture_output=False)
    print(f"--- Successfully installed all packages. ---")

def run_django_migrations(venv_python, manage_py_path):
    """Runs the 'migrate' command using the project's manage.py."""
    if not manage_py_path.is_file():
        print(f"--- Step 4: WARNING: '{MANAGE_PY_FILE}' not found. Skipping migration command. ---")
    else:
        print(f"--- Step 4: Running Django migrations... ---")
        migrate_command = [str(venv_python), str(manage_py_path), "migrate"]
        run_command(migrate_command, "Failed to run Django migrations.", capture_output=False)

def print_completion_message():
    """Prints final instructions on how to activate the virtual environment."""
    print("\n✅ Setup complete!")
    if sys.platform == "win32":
        print(f"To activate the virtual environment, run: .\\{VENV_DIR}\\Scripts\\activate")
    else:
        print(f"To activate the virtual environment, run: source {VENV_DIR}/bin/activate")

def run_build_exe(venv_python, build_exe_path):
    """Runs the build_exe.py script using the virtual environment's Python."""
    if not build_exe_path.is_file():
        print(f"--- WARNING: '{BUILD_EXE}' not found. Skipping EXE build step. ---")
        return
    
    print(f"--- Running '{BUILD_EXE}' to build the executable... ---")
    build_exe_command = [str(venv_python), str(build_exe_path)]
    run_command(build_exe_command, f"Failed to run '{BUILD_EXE}'.", capture_output=False)

def main():
    """Main function to orchestrate the setup process."""
    current_dir = Path.cwd()
    venv_path = current_dir / VENV_DIR
    wheels_path = current_dir / WHEELS_DIR
    requirements_path = current_dir / REQUIREMENTS_FILE
    manage_py_path = current_dir / MANAGE_PY_FILE
    build_exe_path = current_dir / BUILD_EXE

    # Run setup steps sequentially
    perform_pre_flight_checks(requirements_path, wheels_path)
    create_virtual_environment(venv_path)
    venv_python, pip_command_base = get_venv_executables(venv_path)
    # upgrade_pip(pip_command_base)
    install_build_dependencies(pip_command_base, wheels_path)
    install_requirements_from_wheels(pip_command_base, wheels_path, requirements_path)
    run_django_migrations(venv_python, manage_py_path)
    run_build_exe(venv_python, build_exe_path)
    print_completion_message()

if __name__ == "__main__":
    main()

