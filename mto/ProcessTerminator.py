import psutil
import os

def kill_uvicorn_in_current_directory():
    current_dir = os.path.abspath(os.getcwd())

    for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline', 'cwd']):
        try:
            name = proc.info['name']
            cmdline = proc.info['cmdline']
            cwd = proc.info.get('cwd')

            if (
                name.lower() == 'python.exe'
                and cmdline
                and '-m' in cmdline
                and 'uvicorn' in cmdline
                and cwd
                and os.path.abspath(cwd) == current_dir
            ):
                print(f"Found Uvicorn master PID {proc.pid} in {cwd}: {' '.join(cmdline)}")

                # Kill child processes first
                for child in proc.children(recursive=True):
                    print(f"  Killing child PID {child.pid}")
                    child.kill()

                # Kill the master process
                proc.kill()
                print(f"Uvicorn master PID {proc.pid} killed.")
                return
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

if __name__ == "__main__":
    kill_uvicorn_in_current_directory()
