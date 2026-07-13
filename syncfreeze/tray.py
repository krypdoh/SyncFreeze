import pystray
from pystray import MenuItem, Menu

from syncfreeze.icon import load_app_icon, load_paused_icon


class SyncFreezeTray:
    """System tray icon for SyncFreeze."""

    def __init__(self, app):
        """
        Args:
            app: The main App instance (provides timer_mgr, config, pause/resume methods).
        """
        self.app = app
        self._icon = None

    def start(self):
        """Create and run the tray icon (blocking)."""
        self._icon = pystray.Icon(
            "SyncFreeze",
            icon=self._get_current_icon(),
            title="SyncFreeze - File Sync Pause Utility",
            menu=self._build_menu(),
        )
        self._icon.run(setup=self._on_setup)

    def stop(self):
        """Stop the tray icon."""
        if self._icon:
            self._icon.stop()

    def update(self):
        """Refresh icon and menu state."""
        if self._icon:
            self._icon.icon = self._get_current_icon()
            self._icon.update_menu()

    def notify(self, message, title="SyncFreeze"):
        """Show a balloon notification."""
        if self._icon and self.app.config.get("notifications_enabled", True):
            self._icon.notify(message, title)

    def _on_setup(self, icon):
        """Called after tray icon is visible. Start background services."""
        icon.visible = True
        self.app.on_tray_ready()

    def _get_current_icon(self):
        """Return the tray icon, with a blue glow when paused."""
        if self.app.timer_mgr.is_paused:
            return load_paused_icon(size=64)
        return load_app_icon(size=64)

    def _build_menu(self):
        """Build the context menu."""
        return Menu(
            MenuItem("Status...", self._on_status, default=True),
            Menu.SEPARATOR,
            MenuItem("Pause 1 minute", lambda: self._on_pause(1)),
            MenuItem("Pause 5 minutes", lambda: self._on_pause(5)),
            MenuItem("Pause 10 minutes", lambda: self._on_pause(10)),
            MenuItem("Pause 30 minutes", lambda: self._on_pause(30)),
            MenuItem("Pause 1 hour", lambda: self._on_pause(60)),
            MenuItem("Pause indefinitely", lambda: self._on_pause(0)),
            Menu.SEPARATOR,
            MenuItem("Resume", self._on_resume),
            Menu.SEPARATOR,
            MenuItem("Settings...", self._on_settings),
            MenuItem(
                "Notifications",
                self._on_toggle_notifications,
                checked=lambda item: self.app.config.get("notifications_enabled", True),
            ),
            Menu.SEPARATOR,
            MenuItem("About...", self._on_about),
            MenuItem("Exit", self._on_exit),
        )

    def _on_pause(self, minutes):
        """Handle pause menu item click."""
        self.app.do_pause(minutes)

    def _on_resume(self, icon=None, item=None):
        """Handle resume menu item click."""
        self.app.do_resume()

    def _on_status(self, icon=None, item=None):
        """Handle status/double-click."""
        self.app.show_status_dialog()

    def _on_settings(self, icon=None, item=None):
        """Show the settings dialog."""
        self.app.show_settings_dialog()

    def _on_toggle_notifications(self, icon, item):
        """Toggle notification setting."""
        self.app.config["notifications_enabled"] = not self.app.config.get("notifications_enabled", True)
        from syncfreeze.config import save_config
        save_config(self.app.config)

    def _on_about(self, icon=None, item=None):
        """Show about dialog."""
        self.app.show_about_dialog()

    def _on_exit(self, icon=None, item=None):
        """Exit the application."""
        self.app.shutdown()
