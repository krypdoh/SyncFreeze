import tkinter as tk
from tkinter import simpledialog, messagebox
import threading

from syncfreeze.services import SERVICES
from syncfreeze.config import get_enabled_service_ids, set_enabled_services


class _TkThread:
    """Singleton that owns a persistent hidden Tk root in a dedicated thread.

    All Tkinter widgets must be created on this thread. Use call_soon() to
    dispatch callables to it from any other thread.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._ready = threading.Event()
        self._root = None
        t = threading.Thread(target=self._run, daemon=True, name="TkThread")
        t.start()
        self._ready.wait()

    def _run(self):
        self._root = tk.Tk()
        self._root.withdraw()  # hidden; dialogs use Toplevel
        self._ready.set()
        self._root.mainloop()

    def call_soon(self, fn):
        """Schedule fn() to run on the Tk thread (thread-safe)."""
        self._root.after(0, fn)

    @property
    def root(self):
        return self._root


class StatusDialog:
    """Tkinter dialog showing SyncFreeze status with live countdown."""

    def __init__(self, app):
        self.app = app
        self._window = None
        self._update_job = None

    def show(self):
        """Show the status dialog (thread-safe)."""
        _TkThread.get().call_soon(self._show_on_tk_thread)

    def _show_on_tk_thread(self):
        """Must only be called from the Tk thread."""
        if self._window is not None:
            try:
                self._window.lift()
                self._window.focus_force()
                return
            except tk.TclError:
                self._window = None

        self._create_window()

    def _create_window(self):
        """Create the status window as a Toplevel on the shared Tk root."""
        root = _TkThread.get().root
        self._window = tk.Toplevel(root)
        self._window.title("SyncFreeze Status")
        self._window.resizable(False, False)
        self._window.attributes("-topmost", True)

        # Try to set icon
        try:
            from syncfreeze.icon import icon_file_path
            self._window.iconbitmap(icon_file_path())
        except Exception:
            pass

        # Main frame
        frame = tk.Frame(self._window, padx=20, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Status label
        tk.Label(frame, text="Sync Status:", font=("Segoe UI", 10)).pack(anchor=tk.W)
        self._status_label = tk.Label(frame, text="", font=("Segoe UI", 14, "bold"))
        self._status_label.pack(anchor=tk.W, pady=(2, 10))

        # Timer label
        self._timer_frame = tk.Frame(frame)
        self._timer_frame.pack(anchor=tk.W, fill=tk.X)
        tk.Label(self._timer_frame, text="Time remaining:", font=("Segoe UI", 10)).pack(anchor=tk.W)
        self._timer_label = tk.Label(self._timer_frame, text="", font=("Segoe UI", 12))
        self._timer_label.pack(anchor=tk.W, pady=(2, 10))

        # Enabled services and their process state
        tk.Label(frame, text="Services:", font=("Segoe UI", 10)).pack(anchor=tk.W)
        self._services_frame = tk.Frame(frame)
        self._services_frame.pack(anchor=tk.W, fill=tk.X, pady=(2, 0))
        self._service_rows = []  # list of (name_label, state_label)
        self._services_empty_label = None

        # Buttons
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self._pause_btn = tk.Button(
            btn_frame, text="Pause...", width=10, command=self._on_pause
        )
        self._pause_btn.pack(side=tk.LEFT, padx=(0, 5))

        self._resume_btn = tk.Button(
            btn_frame, text="Resume", width=10, command=self._on_resume
        )
        self._resume_btn.pack(side=tk.LEFT, padx=(0, 5))

        tk.Button(btn_frame, text="Close", width=10, command=self._on_close).pack(side=tk.RIGHT)

        # Initial update and start refresh loop
        self._update_display()

        # Center window on screen
        self._window.update_idletasks()
        w = self._window.winfo_width()
        h = self._window.winfo_height()
        x = (self._window.winfo_screenwidth() // 2) - (w // 2)
        y = (self._window.winfo_screenheight() // 2) - (h // 2)
        self._window.geometry(f"+{x}+{y}")

        self._window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _update_display(self):
        """Update the status display."""
        if self._window is None:
            return

        try:
            state = self.app.timer_mgr.get_state()

            if state["status"] == "running":
                self._status_label.config(text="Running", fg="#228B22")
                self._timer_label.config(text="—")
                self._pause_btn.config(state=tk.NORMAL)
                self._resume_btn.config(state=tk.DISABLED)
            else:
                self._status_label.config(text="Paused", fg="#CC0000")
                self._pause_btn.config(state=tk.DISABLED)
                self._resume_btn.config(state=tk.NORMAL)

                if state["indefinite"]:
                    self._timer_label.config(text="Indefinitely")
                elif state["remaining"] is not None:
                    remaining = state["remaining"]
                    mins = int(remaining // 60)
                    secs = int(remaining % 60)
                    self._timer_label.config(text=f"{mins:02d}:{secs:02d}")
                else:
                    self._timer_label.config(text="—")

            self._update_services()

            # Schedule next update
            self._update_job = self._window.after(1000, self._update_display)
        except tk.TclError:
            # Window was destroyed
            self._window = None

    def _update_services(self):
        """Refresh the list of enabled services and their running/stopped state."""
        services = self.app._service_status()

        if not services:
            if self._service_rows:
                for child in self._services_frame.winfo_children():
                    child.destroy()
                self._service_rows = []
            if self._services_empty_label is None:
                self._services_empty_label = tk.Label(
                    self._services_frame,
                    text="(none selected)",
                    font=("Segoe UI", 10),
                    fg="#666666",
                )
                self._services_empty_label.pack(anchor=tk.W)
            return

        if self._services_empty_label is not None:
            self._services_empty_label.destroy()
            self._services_empty_label = None

        names = [name for name, _ in services]
        current_names = [lbl.cget("text").rstrip(":") for lbl, _ in self._service_rows]
        if names != current_names:
            for child in self._services_frame.winfo_children():
                child.destroy()
            self._service_rows = []
            for name, _ in services:
                row = tk.Frame(self._services_frame)
                row.pack(anchor=tk.W, fill=tk.X)
                name_lbl = tk.Label(
                    row, text=f"{name}:", font=("Segoe UI", 10), width=20, anchor=tk.W
                )
                name_lbl.pack(side=tk.LEFT)
                state_lbl = tk.Label(row, text="", font=("Segoe UI", 10, "bold"))
                state_lbl.pack(side=tk.LEFT)
                self._service_rows.append((name_lbl, state_lbl))

        for (_, state_lbl), (_, running) in zip(self._service_rows, services):
            state_lbl.config(
                text="Running" if running else "Stopped",
                fg="#228B22" if running else "#CC0000",
            )

    def _on_pause(self):
        """Prompt user for minutes and pause."""
        minutes = simpledialog.askfloat(
            "Pause Sync",
            "Enter number of minutes to pause\n(0 = indefinitely):",
            minvalue=0,
            parent=self._window,
        )
        if minutes is not None:
            self.app.do_pause(minutes)
            self._update_display()

    def _on_resume(self):
        """Resume Dropbox."""
        self.app.do_resume()
        self._update_display()

    def _on_close(self):
        """Close the dialog."""
        if self._update_job:
            self._window.after_cancel(self._update_job)
        self._window.destroy()
        self._window = None


def show_about():
    """Show the About dialog (thread-safe)."""
    _TkThread.get().call_soon(_show_about_on_tk_thread)


def _show_about_on_tk_thread():
    root = _TkThread.get().root
    messagebox.showinfo(
        "About SyncFreeze",
        "SyncFreeze v1.0.0\n\n"
        "File Sync Pause Utility\n\n"
        "Temporarily pause file syncing\n"
        "for a specified duration.\n\n"
        "\u00a9 2026",
        parent=root,
    )


class SettingsDialog:
    """Dialog to choose which sync services SyncFreeze controls."""

    def __init__(self, app):
        self.app = app
        self._window = None
        self._vars = {}

    def show(self):
        """Show the settings dialog (thread-safe)."""
        _TkThread.get().call_soon(self._show_on_tk_thread)

    def _show_on_tk_thread(self):
        if self._window is not None:
            try:
                self._window.lift()
                self._window.focus_force()
                return
            except tk.TclError:
                self._window = None
        self._create_window()

    def _create_window(self):
        root = _TkThread.get().root
        self._window = tk.Toplevel(root)
        self._window.title("SyncFreeze Settings")
        self._window.resizable(False, False)
        self._window.attributes("-topmost", True)

        # Try to set icon
        try:
            from syncfreeze.icon import icon_file_path
            self._window.iconbitmap(icon_file_path())
        except Exception:
            pass

        frame = tk.Frame(self._window, padx=20, pady=15)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            frame,
            text="Sync services to pause/resume:",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.W, pady=(0, 8))

        enabled = set(get_enabled_service_ids(self.app.config))
        self._vars = {}
        for svc in SERVICES:
            var = tk.BooleanVar(value=svc.id in enabled)
            self._vars[svc.id] = var
            tk.Checkbutton(
                frame,
                text=f"{svc.name}  ({svc.exe})",
                variable=var,
                anchor=tk.W,
                font=("Segoe UI", 9),
            ).pack(anchor=tk.W)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=(12, 0))
        tk.Button(btn_frame, text="Save", width=10, command=self._on_save).pack(side=tk.RIGHT, padx=(5, 0))
        tk.Button(btn_frame, text="Cancel", width=10, command=self._on_close).pack(side=tk.RIGHT)

        self._window.update_idletasks()
        w = self._window.winfo_width()
        h = self._window.winfo_height()
        x = (self._window.winfo_screenwidth() // 2) - (w // 2)
        y = (self._window.winfo_screenheight() // 2) - (h // 2)
        self._window.geometry(f"+{x}+{y}")
        self._window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_save(self):
        selected = [sid for sid, var in self._vars.items() if var.get()]
        set_enabled_services(self.app.config, selected)
        self._on_close()

    def _on_close(self):
        if self._window is not None:
            self._window.destroy()
            self._window = None
