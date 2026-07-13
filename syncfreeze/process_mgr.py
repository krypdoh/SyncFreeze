import subprocess
import psutil

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008


def is_service_running(exe_name):
    """Check if any process matching ``exe_name`` is running."""
    target = exe_name.lower()
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == target:
                return True
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return False


def stop_service(exe_name):
    """Terminate all processes matching ``exe_name``.

    Returns the full executable path of one of the terminated processes (so it
    can be restarted later), or None if nothing was running.
    """
    target = exe_name.lower()
    exe_path = None
    for proc in psutil.process_iter(["name", "exe"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == target:
                if exe_path is None and proc.info.get("exe"):
                    exe_path = proc.info["exe"]
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    proc.kill()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return exe_path


def start_service(exe_path):
    """Start a service executable as a detached process."""
    subprocess.Popen(
        [exe_path],
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
        close_fds=True,
    )
