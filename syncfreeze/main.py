import argparse
import sys
import os

from syncfreeze import __version__
from syncfreeze.config import (
    load_config,
    save_config,
    get_enabled_services,
    get_service_path,
    remember_service_path,
)
from syncfreeze.process_mgr import stop_service, start_service, is_service_running
from syncfreeze.timer_mgr import TimerManager
from syncfreeze.ipc import IPCServer, send_command, IPC_PORT
from syncfreeze.tray import SyncFreezeTray
from syncfreeze.dialog import StatusDialog, SettingsDialog, show_about


class App:
    """Main application controller."""

    def __init__(self):
        self.config = load_config()
        self.timer_mgr = TimerManager(on_expire_callback=self._on_timer_expire)
        self.tray = SyncFreezeTray(self)
        self.ipc_server = None
        self.status_dialog = StatusDialog(self)
        self.settings_dialog = SettingsDialog(self)

    def run(self, initial_command=None):
        """Start the tray application."""
        # Start IPC server
        try:
            self.ipc_server = IPCServer(handler=self._handle_ipc_command)
            self.ipc_server.start()
        except OSError:
            print(
                f"ERROR: Could not bind to port {IPC_PORT}. "
                "Another application may be using it. Exiting.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Store initial command to execute once tray is ready
        self._initial_command = initial_command

        # Run tray (blocking)
        self.tray.start()

    def on_tray_ready(self):
        """Called when tray icon is visible and ready."""
        # Execute initial command if any
        if self._initial_command:
            cmd = self._initial_command
            if cmd["action"] == "pause":
                self.do_pause(cmd["minutes"])
            elif cmd["action"] == "resume":
                self.do_resume()
            elif cmd["action"] == "status":
                state = self.timer_mgr.get_state()
                _print_status({
                    "services": self._service_status(),
                    "timer_state": state["status"],
                    "indefinite": state["indefinite"],
                    "remaining": state["remaining"],
                })

    def _stop_services(self):
        """Stop all enabled services, caching each captured executable path."""
        for svc in get_enabled_services(self.config):
            path = stop_service(svc.exe)
            remember_service_path(self.config, svc.id, path)

    def _start_services(self):
        """Restart all enabled services from their known executable paths."""
        for svc in get_enabled_services(self.config):
            path = get_service_path(self.config, svc)
            if path:
                start_service(path)

    def _service_status(self):
        """Return a list of (name, running) tuples for enabled services."""
        return [(svc.name, is_service_running(svc.exe)) for svc in get_enabled_services(self.config)]

    def _enabled_label(self):
        """Human-readable label for the enabled services."""
        names = [svc.name for svc in get_enabled_services(self.config)]
        if not names:
            return "sync"
        if len(names) <= 2:
            return " & ".join(names)
        return f"{len(names)} sync services"

    def do_pause(self, minutes):
        """Pause the enabled services for the specified minutes."""
        self._stop_services()
        self.timer_mgr.pause(minutes)
        self.tray.update()

        label = self._enabled_label()
        if minutes == 0:
            self.tray.notify(f"Pausing {label} indefinitely")
        else:
            self.tray.notify(f"Pausing {label} for {_format_duration(minutes)}")

    def do_resume(self):
        """Resume the enabled services."""
        self.timer_mgr.resume()
        self._start_services()
        self.tray.update()
        self.tray.notify(f"Resuming {self._enabled_label()}")

    def show_status_dialog(self):
        """Show the status dialog window."""
        self.status_dialog.show()

    def show_settings_dialog(self):
        """Show the settings dialog window."""
        self.settings_dialog.show()

    def show_about_dialog(self):
        """Show the about dialog."""
        show_about()

    def shutdown(self):
        """Clean shutdown: resume services if paused, then exit."""
        if self.timer_mgr.is_paused:
            self.timer_mgr.resume()
            self._start_services()

        if self.ipc_server:
            self.ipc_server.stop()
        self.tray.stop()

    def _on_timer_expire(self):
        """Called when the pause timer expires."""
        self._start_services()
        self.tray.update()
        self.tray.notify(f"Resuming {self._enabled_label()}")

    def _handle_ipc_command(self, command):
        """Handle an IPC command from a CLI invocation."""
        action = command.get("action")

        if action == "pause":
            minutes = command.get("minutes", 5)
            self.do_pause(minutes)
            label = self._enabled_label()
            if minutes == 0:
                return {"status": "ok", "message": f"{label} paused indefinitely"}
            return {"status": "ok", "message": f"{label} paused for {_format_duration(minutes)}"}

        elif action == "resume":
            self.do_resume()
            return {"status": "ok", "message": f"{self._enabled_label()} resumed"}

        elif action == "status":
            state = self.timer_mgr.get_state()
            return {
                "status": "ok",
                "services": self._service_status(),
                "timer_state": state["status"],
                "indefinite": state["indefinite"],
                "remaining": state["remaining"],
            }

        return {"status": "error", "message": f"Unknown action: {action}"}


def _format_duration(minutes):
    """Format minutes into a human-readable string."""
    if minutes >= 60:
        hours = minutes / 60
        if hours == int(hours):
            return f"{int(hours)} hour{'s' if hours != 1 else ''}"
        return f"{hours:.1f} hours"
    if minutes == int(minutes):
        return f"{int(minutes)} minute{'s' if minutes != 1 else ''}"
    # For fractional minutes, show seconds
    seconds = minutes * 60
    if seconds == int(seconds):
        return f"{int(seconds)} seconds"
    return f"{minutes} minutes"


def _spawn_tray_detached(extra_args=()):
    """Spawn SyncFreeze_tray.exe as a detached background process.

    Looks for SyncFreeze_tray.exe next to the current executable (installed/dist
    layout). Falls back to running tray_main.py via the current interpreter
    for development runs.
    """
    import subprocess
    DETACHED_PROCESS = 0x00000008
    CREATE_NEW_PROCESS_GROUP = 0x00000200

    exe_dir = os.path.dirname(sys.executable)
    tray_exe = os.path.join(exe_dir, "SyncFreeze_tray.exe")
    if os.path.isfile(tray_exe):
        cmd = [tray_exe] + list(extra_args)
    else:
        # Development fallback
        cmd = [sys.executable, "-m", "syncfreeze.tray_main"] + list(extra_args)

    subprocess.Popen(
        cmd,
        creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main():
    parser = argparse.ArgumentParser(
        prog="SyncFreeze",
        description="SyncFreeze - Temporarily pause file-sync services",
    )
    parser.add_argument(
        "-t", "--time",
        type=float,
        metavar="MINUTES",
        help="Pause selected services for MINUTES (0 = indefinitely, decimals OK)",
    )
    parser.add_argument(
        "-r", "--resume",
        action="store_true",
        help="Resume selected services (overrides any active pause timer)",
    )
    parser.add_argument(
        "-s", "--status",
        action="store_true",
        help="Show current status",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"SyncFreeze {__version__}",
    )

    args = parser.parse_args()

    # ── CLI mode ──────────────────────────────────────────────────────────
    command = None
    if args.time is not None:
        if args.time < 0:
            print("ERROR: Time must be >= 0", file=sys.stderr)
            sys.exit(1)
        command = {"action": "pause", "minutes": args.time}
    elif args.resume:
        command = {"action": "resume"}
    elif args.status:
        command = {"action": "status"}

    # Try to send to an existing running instance
    if command:
        try:
            response = send_command(command)
            if response.get("status") == "ok":
                if "message" in response:
                    print(response["message"])
                elif command["action"] == "status":
                    _print_status(response)
            else:
                print(f"Error: {response.get('message', 'Unknown error')}", file=sys.stderr)
            sys.exit(0)
        except (ConnectionRefusedError, OSError):
            if command["action"] == "status":
                print("SyncFreeze is not running.")
                sys.exit(0)
            # pause/resume with no running instance: fall through to spawn tray

    # No running instance — spawn SyncFreeze_tray.exe detached and exit immediately.
    extra = []
    if args.time is not None:
        extra += ["-t", str(args.time)]
    elif args.resume:
        extra += ["-r"]
    _spawn_tray_detached(extra)
    sys.exit(0)




def _print_status(response):
    """Print status response to console."""
    services = response.get("services", [])
    timer_state = response.get("timer_state", "unknown")
    indefinite = response.get("indefinite", False)
    remaining = response.get("remaining")

    if services:
        print("Sync services:")
        for name, running in services:
            print(f"  {name}: {'Running' if running else 'Stopped'}")
    else:
        print("Sync services:   (none selected)")
    print(f"SyncFreeze state: {timer_state.title()}")

    if timer_state == "paused":
        if indefinite:
            print("Duration:        Indefinitely")
        elif remaining is not None:
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            print(f"Remaining:       {mins:02d}:{secs:02d}")


if __name__ == "__main__":
    main()
