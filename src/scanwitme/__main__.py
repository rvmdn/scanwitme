"""Entry point for running ScanWitMe PC application."""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from scanwitme.app import ScanWitMeApp
from scanwitme.infrastructure.logging import setup_logging


def main() -> None:
    # High-DPI scaling is enabled by default in Qt 6
    # Setup sanitized logging
    log_level = os.environ.get("SCANWITME_LOG_LEVEL", "INFO")
    api_key = os.environ.get("GOOGLE_TRANSLATE_API_KEY")
    logger = setup_logging(level=log_level, api_key=api_key)
    logger.info("Starting ScanWitMe PC application...")

    q_app = QApplication(sys.argv)
    q_app.setApplicationName("ScanWitMe")
    q_app.setOrganizationName("ScanWitMe")
    q_app.setQuitOnLastWindowClosed(False)  # Keep running in system tray

    app = ScanWitMeApp(q_app)
    app.start()

    sys.exit(q_app.exec())


if __name__ == "__main__":
    main()
