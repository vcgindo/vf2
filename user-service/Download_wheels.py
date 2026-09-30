import os
import subprocess
import sys
from pathlib import Path
from logger_config import setup_logger
setup_logger()

import logging
logger = logging.getLogger(__name__)

# --- Configuration ---
_REQUIREMENTS_FILE = 'requirements.txt'
_WHEELS_FOLDER = 'local_wheels'

def check_pip():
    """Checks if pip is installed and available."""
    try:
        subprocess.run([sys.executable, '-m', 'pip', '--version'], check=True, capture_output=True)
        logger.info(" pip is available.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error(" Error: pip is not installed or not found in your PATH.")
        logger.error("Please install Python and pip before running this script.")
        return False

def create_wheels_folder():
    """Creates the folder to store the wheel files if it doesn't exist."""
    if not os.path.exists(_WHEELS_FOLDER):
        logger.info(f" Creating directory: '{_WHEELS_FOLDER}'")
        os.makedirs(_WHEELS_FOLDER)
    else:
        logger.info(f"Directory '{_WHEELS_FOLDER}' already exists.")

def check_requirements_file():
    """Checks if the requirements.txt file exists in the current directory."""
    if not os.path.isfile(_REQUIREMENTS_FILE):
        logger.info(f"Error: '{_REQUIREMENTS_FILE}' not found in the current directory.")
        logger.info("Please create a requirements.txt file with your project's dependencies.")
        return False
    logger.info(f" Found '{_REQUIREMENTS_FILE}'.")
    return True

def download_wheels():
    """
    Downloads all wheel files specified in the requirements.txt file
    into the designated wheels folder.
    """
    logger.info("\n Starting wheel download process...")
    
    # The command to download all packages from requirements.txt as wheels
    command = [
        sys.executable,
        '-m',
        'pip',
        'download',
        '-r',
        _REQUIREMENTS_FILE,
        '-d',
        _WHEELS_FOLDER
    ]

    try:
        # We use subprocess.run to execute the command

        #fetching just command name instead of whole path
        command_name = Path(command[0]).name if command else "download wheels command"
        logger.info(f" Running command: {command_name} (arguments hidden for security)")
        process = subprocess.run(
            command,
            check=True,        # This will raise an exception if the command fails
            capture_output=True, # Captures stdout and stderr
            text=True          # Decodes stdout/stderr as text
        )
        logger.info("\n--- pip output ---")
        logger.info(process.stdout)
        logger.info("------------------")
        logger.info(f"\n Success! All wheel files have been downloaded to the '{_WHEELS_FOLDER}' folder.")

    except subprocess.CalledProcessError as e:
        # This block runs if the pip command returns a non-zero exit code (an error)
        logger.error("\n An error occurred during the download process.")
        logger.error("--- pip error output ---")
        logger.error(e.stderr)
        logger.error("------------------------")
    except FileNotFoundError:
        logger.error(" Error: Could not execute the pip command. Make sure Python and pip are correctly installed.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")

def main():
    """Main function to run the script."""
    logger.info("--- Python Wheels Downloader ---")
    
    if not check_pip():
        return
        
    if not check_requirements_file():
        return

    create_wheels_folder()
    download_wheels()

    logger.info("\n To install these packages later without an internet connection, use the following command:")
    logger.info(f"   pip install --no-index --find-links={_WHEELS_FOLDER} -r {_REQUIREMENTS_FILE}")
    logger.info("--------------------------------")


if __name__ == "__main__":
    main()
