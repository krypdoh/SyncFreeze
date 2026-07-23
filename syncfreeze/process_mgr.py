import subprocess
import psutil

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008


def _as_list(exe_names):
    if isinstance(exe_names, str):
        return [exe_names]
    return list(exe_names)


def is_service_running(exe_names):
    """Check if any process matching any of ``exe_names`` is running."""
    targets = {name.lower() for name in _as_list(exe_names)}
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() in targets:
                return True
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
    return False


def stop_service(exe_names, path_exe=None):
    """Terminate all processes matching any of ``exe_names``.

    ``exe_names`` may be a single name or an ordered list (companions first so
    they cannot respawn the primary). Returns the full executable path of a
    terminated process matching ``path_exe`` (defaults to the last name, i.e.
    the primary), or None if that process was not running.
    """
    names = _as_list(exe_names)
    preferred = (path_exe or names[-1]).lower()
    exe_path = None

    # Kill in list order so a GUI/watchdog dies before the sync engine.
    for exe_name in names:
        target = exe_name.lower()
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == target:
                    if (
                        exe_path is None
                        and target == preferred
                        and proc.info.get("exe")
                    ):
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
