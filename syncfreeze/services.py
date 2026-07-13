"""Registry of supported file-sync services.

Each service is identified by a stable ``id`` and the name of its main
executable. None of these clients expose a reliable, documented command-line
"pause" interface, so SyncFreeze pauses a service by terminating its process
and restarts it later (the same technique originally used for Dropbox). The
full path of the running executable is captured at stop time so it can be
restarted; ``default_paths`` provides best-effort fallbacks used only when the
process was not running (and therefore no path could be captured).
"""
import os


class Service:
    """Describes a supported file-sync application."""

    def __init__(self, id, name, exe, default_paths=None):
        self.id = id
        self.name = name
        self.exe = exe
        self.default_paths = default_paths or []

    def __repr__(self):
        return f"Service(id={self.id!r}, name={self.name!r}, exe={self.exe!r})"


def _p(*parts):
    """Join an environment-variable-rooted path, or None if the root is unset."""
    root = os.environ.get(parts[0])
    if not root:
        return None
    return os.path.join(root, *parts[1:])


# Ordered list of supported services (registry).
SERVICES = [
    Service(
        "onedrive",
        "Microsoft OneDrive",
        "OneDrive.exe",
        [
            _p("LOCALAPPDATA", "Microsoft", "OneDrive", "OneDrive.exe"),
            _p("PROGRAMFILES", "Microsoft OneDrive", "OneDrive.exe"),
            _p("PROGRAMFILES(X86)", "Microsoft OneDrive", "OneDrive.exe"),
        ],
    ),
    Service(
        "googledrive",
        "Google Drive",
        "GoogleDriveFS.exe",
        [
            _p("PROGRAMFILES", "Google", "Drive File Stream", "GoogleDriveFS.exe"),
        ],
    ),
    Service(
        "dropbox",
        "Dropbox",
        "Dropbox.exe",
        [
            _p("PROGRAMFILES(X86)", "Dropbox", "Client", "Dropbox.exe"),
            _p("PROGRAMFILES", "Dropbox", "Client", "Dropbox.exe"),
            _p("LOCALAPPDATA", "Dropbox", "Client", "Dropbox.exe"),
        ],
    ),
    Service(
        "icloud",
        "Apple iCloud Drive",
        "iCloudDrive.exe",
        [
            _p("PROGRAMFILES", "Common Files", "Apple", "Internet Services", "iCloudDrive.exe"),
            _p("PROGRAMFILES(X86)", "Common Files", "Apple", "Internet Services", "iCloudDrive.exe"),
        ],
    ),
    Service(
        "box",
        "Box",
        "Box.exe",
        [
            _p("PROGRAMFILES", "Box", "Box", "Box.exe"),
            _p("PROGRAMFILES(X86)", "Box", "Box", "Box.exe"),
        ],
    ),
    Service(
        "mega",
        "MEGA",
        "MEGAsync.exe",
        [
            _p("PROGRAMFILES", "MEGAsync", "MEGAsync.exe"),
            _p("PROGRAMFILES(X86)", "MEGAsync", "MEGAsync.exe"),
        ],
    ),
    Service(
        "idrive",
        "IDrive",
        "idwutil_64.exe",
        [
            _p("PROGRAMFILES(X86)", "IDriveWindows", "id_bg", "idwutil_64.exe"),
        ],
    ),
    Service(
        "pcloud",
        "pCloud",
        "pCloud.exe",
        [
            _p("PROGRAMFILES(X86)", "pCloud Drive", "pCloud.exe"),
            _p("PROGRAMFILES", "pCloud Drive", "pCloud.exe"),
        ],
    ),
    Service(
        "sync",
        "Sync.com",
        "sync-taskbar.exe",
        [
            _p("LOCALAPPDATA", "Sync", "sync-taskbar.exe"),
        ],
    ),
]

# Lookup helpers ----------------------------------------------------------------
SERVICES_BY_ID = {s.id: s for s in SERVICES}


def get_service(service_id):
    """Return the Service with the given id, or None."""
    return SERVICES_BY_ID.get(service_id)


def find_service_path(service):
    """Best-effort lookup of a service executable path from default locations."""
    for path in service.default_paths:
        if path and os.path.isfile(path):
            return path
    return None
