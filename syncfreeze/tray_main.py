"""Entry point for the SyncFreeze_tray executable.

This is spawned detached by SyncFreeze.exe when no running instance exists.
It owns the system tray icon and the IPC server for the lifetime of the session.
"""
import argparse
import sys

from syncfreeze.config import load_config
from syncfreeze.timer_mgr import TimerManager
from syncfreeze.ipc import IPCServer, IPC_PORT
from syncfreeze.tray import SyncFreezeTray
from syncfreeze.dialog import StatusDialog, show_about
from syncfreeze import __version__


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-t", "--time", type=float, dest="time", default=None)
    parser.add_argument("-r", "--resume", action="store_true")
    args, _ = parser.parse_known_args()

    # Running as the background tray process — no console needed.
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.kernel32.FreeConsole()

    from syncfreeze.main import App, _format_duration

    command = None
    if args.time is not None:
        command = {"action": "pause", "minutes": args.time}
    elif args.resume:
        command = {"action": "resume"}

    app = App()
    app.run(initial_command=command)


if __name__ == "__main__":
    main()
