# SyncFreeze

**Temporarily pause file-sync services for a specified duration.**

SyncFreeze is a Windows system tray utility that lets you pause and resume popular
file-sync clients (Dropbox, OneDrive, Google Drive, and more) via the tray icon or
command line. You choose which services it controls in **Settings**. After the pause
duration expires, the selected services automatically restart.

## Supported Services

Select any combination of the following in the **Settings** screen:

| Service | Process |
|---------|---------|
| Microsoft OneDrive | `OneDrive.exe` |
| Google Drive | `GoogleDriveFS.exe` |
| Dropbox | `Dropbox.exe` |
| Apple iCloud Drive | `iCloudDrive.exe` |
| Box | `Box.exe` |
| MEGA | `MEGAsync.exe` |
| IDrive | `idwutil_64.exe` |
| pCloud | `pCloud.exe` |
| Sync.com | `sync-taskbar.exe` |

None of these clients expose a reliable command-line "pause" interface, so SyncFreeze
pauses a service by stopping its process and restarts it when the timer expires (or
when you resume). The exact executable path is captured when the process is stopped
so it can be relaunched reliably. Dropbox is enabled by default.

## Features

- **Multi-service support** — pause/resume several sync clients at once
- **Settings screen** — check off which services SyncFreeze controls
- **System tray icon** with right-click menu for quick pause/resume
- **Command-line interface** for scripting and quick access
- **Visual indicator** — green icon when running, red when paused
- **Balloon notifications** when pausing/resuming (can be disabled)
- **Status dialog** (double-click tray icon) with live countdown timer
- **Single instance** — CLI commands route to the running tray app via IPC
- **Auto-resume on exit** — if you close SyncFreeze while paused, it restarts the selected services

## Installation

### Requirements
- Python 3.10+
- Windows 10/11

### Setup
```bash
pip install -r requirements.txt
```

### Build standalone executables
```bash
pip install pyinstaller
build.bat
```
Two executables are produced in `dist\`:

| File | Purpose |
|------|---------|
| `SyncFreeze.exe` | CLI / launcher — prints output, exits immediately |
| `SyncFreeze_tray.exe` | Background tray process — spawned automatically by `SyncFreeze.exe` |

Both files must be kept in the same directory.

## Usage

### Command Line

```
SyncFreeze.exe -t 5        # Pause selected services for 5 minutes
SyncFreeze.exe -t .5       # Pause for 30 seconds
SyncFreeze.exe -t 0        # Pause indefinitely
SyncFreeze.exe -r          # Resume selected services (overrides any timer)
SyncFreeze.exe -s          # Show current status
SyncFreeze.exe             # Launch tray app (no action)
SyncFreeze.exe -v          # Show version
SyncFreeze.exe -h          # Show help
```

The CLI process exits immediately after sending its command. If no tray instance is running, `SyncFreeze_tray.exe` is spawned as a detached background process so your terminal prompt returns right away.

### System Tray

- **Right-click** — Context menu with preset durations and options
- **Double-click** — Status dialog with live countdown and Pause/Resume buttons

### Tray Menu Options

| Option | Action |
|--------|--------|
| Status... | Open status dialog (default action) |
| Pause 1 minute | Pause selected services for 1 minute |
| Pause 5 minutes | Pause selected services for 5 minutes |
| Pause 10 minutes | Pause selected services for 10 minutes |
| Pause 30 minutes | Pause selected services for 30 minutes |
| Pause 1 hour | Pause selected services for 1 hour |
| Pause indefinitely | Pause until manually resumed |
| Resume | Restart selected services immediately |
| Settings... | Choose which sync services to control |
| Notifications | Toggle balloon notifications on/off |
| About... | Version info |
| Exit | Resume selected services (if paused) and close |

## Settings

Open **Settings...** from the tray menu to choose which sync services SyncFreeze
pauses and resumes. Each supported service has a checkbox; enable the ones you use
and click **Save**. Your selection is stored in the config file and applied to every
subsequent pause/resume (from both the tray and the CLI).

> Coming soon: SyncFreeze will scan running processes and pre-select the sync
> services it detects, so manual selection becomes optional.

## Configuration

Settings are stored in `%APPDATA%\SyncFreeze\config.json`:

```json
{
  "notifications_enabled": true,
  "enabled_services": ["dropbox", "onedrive"],
  "service_paths": {
    "dropbox": "C:\\Program Files (x86)\\Dropbox\\Client\\Dropbox.exe",
    "onedrive": "C:\\Users\\you\\AppData\\Local\\Microsoft\\OneDrive\\OneDrive.exe"
  }
}
```

- `enabled_services` — service ids SyncFreeze will stop/start (managed via the
  **Settings** screen). Defaults to `["dropbox"]`.
- `service_paths` — cache of each service's executable path, captured automatically
  when a service is stopped so it can be restarted. Well-known install locations are
  used as a fallback if a path hasn't been captured yet.

Config files from earlier versions (which used a single `dropbox_path`) are migrated
automatically on first run.

## Running from Source

```bash
python -m syncfreeze.main
python -m syncfreeze.main -t 5
python -m syncfreeze.main -s
python -m syncfreeze.main -r
```

## Architecture

- **Two-process design**: `SyncFreeze.exe` is a short-lived CLI process; `SyncFreeze_tray.exe` is the long-running background tray process. This keeps the terminal prompt responsive and avoids shared-tempdir cleanup issues.
- **IPC**: Localhost TCP socket on port 49152 — subsequent CLI calls route to the running tray instance (no firewall prompt).
- **Single instance**: If a tray is already running, CLI commands are forwarded via IPC and the CLI exits immediately.
- **Timer**: Background thread with cancelable timer.
- **Tray**: pystray with Windows notification support.
- **Tkinter thread safety**: All dialogs run on a single dedicated Tk thread via a shared `Tk` root, preventing `Tcl_AsyncDelete` crashes on repeated opens.
- **Process management**: psutil for finding/killing sync processes, subprocess for restarting them.

## License

MIT
