import os
import subprocess
import sys

# --- Configuration ---
REQUIREMENTS_FILE = 'requirements.txt'
WHEELS_FOLDER = 'local_wheels'

def check_pip():
    """Checks if pip is installed and available."""
    try:
        subprocess.run([sys.executable, '-m', 'pip', '--version'], check=True, capture_output=True)
        print("✅ pip is available.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: pip is not installed or not found in your PATH.")
        print("Please install Python and pip before running this script.")
        return False

def create_wheels_folder():
    """Creates the folder to store the wheel files if it doesn't exist."""
    if not os.path.exists(WHEELS_FOLDER):
        print(f"📂 Creating directory: '{WHEELS_FOLDER}'")
        os.makedirs(WHEELS_FOLDER)
    else:
        print(f"📂 Directory '{WHEELS_FOLDER}' already exists.")

def check_requirements_file():
    """Checks if the requirements.txt file exists in the current directory."""
    if not os.path.isfile(REQUIREMENTS_FILE):
        print(f"❌ Error: '{REQUIREMENTS_FILE}' not found in the current directory.")
        print("Please create a requirements.txt file with your project's dependencies.")
        return False
    print(f"📄 Found '{REQUIREMENTS_FILE}'.")
    return True

def download_wheels():
    """
    Downloads all wheel files specified in the requirements.txt file
    into the designated wheels folder.
    """
    print("\n🚀 Starting wheel download process...")
    
    # The command to download all packages from requirements.txt as wheels
    command = [
        sys.executable,
        '-m',
        'pip',
        'download',
        '-r',
        REQUIREMENTS_FILE,
        '-d',
        WHEELS_FOLDER
    ]

    try:
        # We use subprocess.run to execute the command
        print(f"⚙️  Running command: {' '.join(command)}")
        process = subprocess.run(
            command,
            check=True,        # This will raise an exception if the command fails
            capture_output=True, # Captures stdout and stderr
            text=True          # Decodes stdout/stderr as text
        )
        print("\n--- pip output ---")
        print(process.stdout)
        print("------------------")
        print(f"\n✅ Success! All wheel files have been downloaded to the '{WHEELS_FOLDER}' folder.")

    except subprocess.CalledProcessError as e:
        # This block runs if the pip command returns a non-zero exit code (an error)
        print("\n❌ An error occurred during the download process.")
        print("--- pip error output ---")
        print(e.stderr)
        print("------------------------")
    except FileNotFoundError:
        print("❌ Error: Could not execute the pip command. Make sure Python and pip are correctly installed.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def main():
    """Main function to run the script."""
    print("--- Python Wheels Downloader ---")
    
    if not check_pip():
        return
        
    if not check_requirements_file():
        return

    create_wheels_folder()
    download_wheels()

    print("\n💡 To install these packages later without an internet connection, use the following command:")
    print(f"   pip install --no-index --find-links={WHEELS_FOLDER} -r {REQUIREMENTS_FILE}")
    print("--------------------------------")


if __name__ == "__main__":
    main()
