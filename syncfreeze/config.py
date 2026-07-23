import json
import os

from syncfreeze.services import SERVICES, SERVICES_BY_ID, find_service_path

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", ""), "SyncFreeze")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS = {
    "notifications_enabled": True,
    # Which service ids SyncFreeze will stop/start. Defaults to Dropbox to
    # preserve the original behavior.
    "enabled_services": ["dropbox"],
    # Cache of last-known executable paths per service id (captured when a
    # service is stopped) so it can be restarted reliably.
    "service_paths": {},
}


def _ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def _migrate(data):
    """Upgrade older config layouts in place."""
    # v1 stored a single "dropbox_path" and always operated on Dropbox.
    if "dropbox_path" in data:
        legacy_path = data.pop("dropbox_path")
        data.setdefault("service_paths", {})
        if legacy_path and "dropbox" not in data["service_paths"]:
            data["service_paths"]["dropbox"] = legacy_path
        data.setdefault("enabled_services", ["dropbox"])
    return data


def load_config():
    _ensure_config_dir()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        data = _migrate(data)
        # Merge with defaults for any missing keys
        for key, val in DEFAULTS.items():
            if key not in data:
                data[key] = val.copy() if isinstance(val, (dict, list)) else val
        return data
    return {k: (v.copy() if isinstance(v, (dict, list)) else v) for k, v in DEFAULTS.items()}


def save_config(config):
    _ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_enabled_service_ids(config):
    """Return the list of enabled service ids (filtered to known services)."""
    return [sid for sid in config.get("enabled_services", []) if sid in SERVICES_BY_ID]


def get_enabled_services(config):
    """Return the enabled Service objects in registry order."""
    enabled = set(get_enabled_service_ids(config))
    return [s for s in SERVICES if s.id in enabled]


def set_enabled_services(config, service_ids):
    """Store the enabled service ids and persist."""
    config["enabled_services"] = [sid for sid in service_ids if sid in SERVICES_BY_ID]
    save_config(config)


def get_service_path(config, service):
    """Return a usable executable path for a service, or None.

    Prefers the cached path captured on stop, then falls back to well-known
    default install locations. If the cache points at a companion process
    (also_stop), prefer the primary start exe in the same directory.
    """
    cached = config.get("service_paths", {}).get(service.id)
    if cached and os.path.isfile(cached):
        if os.path.basename(cached).lower() != service.exe.lower():
            sibling = os.path.join(os.path.dirname(cached), service.exe)
            if os.path.isfile(sibling):
                return sibling
        return cached
    return find_service_path(service)


def remember_service_path(config, service_id, path):
    """Cache the executable path for a service and persist if it changed."""
    if not path:
        return
    paths = config.setdefault("service_paths", {})
    if paths.get(service_id) != path:
        paths[service_id] = path
        save_config(config)
