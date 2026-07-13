import threading
import time


class TimerManager:
    """Manages the Dropbox pause/resume timer."""

    def __init__(self, on_expire_callback):
        """
        Args:
            on_expire_callback: Called (with no args) when the timer expires.
                                Should resume Dropbox.
        """
        self._lock = threading.Lock()
        self._timer = None
        self._paused = False
        self._indefinite = False
        self._expire_time = None  # time.time() when timer will fire
        self._on_expire = on_expire_callback

    def pause(self, minutes):
        """
        Pause Dropbox for the given number of minutes.
        If minutes == 0, pause indefinitely (no timer).
        """
        with self._lock:
            self._cancel_timer_internal()
            self._paused = True

            if minutes == 0:
                self._indefinite = True
                self._expire_time = None
            else:
                self._indefinite = False
                seconds = minutes * 60
                self._expire_time = time.time() + seconds
                self._timer = threading.Timer(seconds, self._timer_expired)
                self._timer.daemon = True
                self._timer.start()

    def resume(self):
        """Cancel any active timer and mark as resumed."""
        with self._lock:
            self._cancel_timer_internal()
            self._paused = False
            self._indefinite = False
            self._expire_time = None

    def get_state(self):
        """
        Returns a dict with:
            - "status": "running" | "paused"
            - "indefinite": bool
            - "remaining": float seconds remaining, or None
        """
        with self._lock:
            if not self._paused:
                return {"status": "running", "indefinite": False, "remaining": None}

            if self._indefinite:
                return {"status": "paused", "indefinite": True, "remaining": None}

            remaining = None
            if self._expire_time:
                remaining = max(0, self._expire_time - time.time())
            return {"status": "paused", "indefinite": False, "remaining": remaining}

    @property
    def is_paused(self):
        with self._lock:
            return self._paused

    def _cancel_timer_internal(self):
        """Cancel the timer (must hold lock)."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _timer_expired(self):
        """Called when the timer fires."""
        with self._lock:
            self._paused = False
            self._indefinite = False
            self._expire_time = None
            self._timer = None
        # Callback outside the lock to avoid deadlock
        self._on_expire()
