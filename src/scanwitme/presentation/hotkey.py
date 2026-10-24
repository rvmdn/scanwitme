"""Thread-safe global hotkey listener for Windows using pynput."""

from __future__ import annotations

import logging

from pynput import keyboard
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("scanwitme.hotkey")


class GlobalHotkeyManager(QObject):
    """Listens for global hotkeys in a background thread and emits Qt signals."""

    hotkey_triggered = Signal()
    registration_failed = Signal(str)

    def __init__(self, hotkey_str: str = "<ctrl>+<shift>+s", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._hotkey_str = hotkey_str
        self._listener: keyboard.GlobalHotKeys | None = None
        self._is_running = False

    @property
    def hotkey_str(self) -> str:
        return self._hotkey_str

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> bool:
        """Start global hotkey listener thread."""
        if self._is_running:
            return True

        try:
            hotkey_mapping = {self._hotkey_str: self._on_hotkey_pressed}
            self._listener = keyboard.GlobalHotKeys(hotkey_mapping)
            self._listener.daemon = True
            self._listener.start()
            self._is_running = True
            logger.info("Global hotkey registered: %s", self._hotkey_str)
            return True
        except Exception as exc:
            logger.warning("Failed to register global hotkey '%s': %s", self._hotkey_str, exc)
            self._is_running = False
            self.registration_failed.emit(str(exc))
            return False

    def stop(self) -> None:
        """Stop global hotkey listener thread."""
        if self._listener:
            try:
                self._listener.stop()
            except Exception as exc:
                logger.debug("Error while stopping hotkey listener: %s", exc)
            self._listener = None
        self._is_running = False

    def update_hotkey(self, new_hotkey_str: str) -> bool:
        """Update and restart the listener with a new hotkey."""
        self.stop()
        self._hotkey_str = new_hotkey_str
        return self.start()

    def _on_hotkey_pressed(self) -> None:
        """Callback invoked from pynput thread."""
        logger.debug("Global hotkey '%s' pressed", self._hotkey_str)
        # Emitting a Qt signal from another thread is thread-safe and queued into Qt event loop
        self.hotkey_triggered.emit()
