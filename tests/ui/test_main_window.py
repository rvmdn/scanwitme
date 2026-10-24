"""UI tests for MainWindow and SettingsDialog."""

from pathlib import Path

import pytest
from pytestqt.qtbot import QtBot

from scanwitme.infrastructure.settings.json_settings import JsonSettingsRepository
from scanwitme.presentation.main_window import MainWindow
from scanwitme.presentation.settings_dialog import SettingsDialog


@pytest.mark.ui
def test_main_window_elements_and_signals(qtbot: QtBot, tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    repo = JsonSettingsRepository(file_path=settings_file)

    window = MainWindow(settings_repo=repo)
    qtbot.addWidget(window)
    window.show()

    assert window.isVisible()
    assert window._scan_btn.text() == "⚡ Scan Layar (Ctrl+Shift+S)"

    # Test scan button signal
    with qtbot.waitSignal(window.scan_requested, timeout=1000):
        window._scan_btn.click()

    # Test frame toggle button signal
    with qtbot.waitSignal(window.toggle_frame_requested, timeout=1000):
        window._frame_btn.click()

    # Test auto scan toggle button signal
    with qtbot.waitSignal(window.auto_scan_toggled, timeout=1000) as blocker:
        window._auto_btn.click()
    assert blocker.args == [True]
    assert "ON" in window._auto_btn.text()

    # Test source language change
    zh_idx = window._src_combo.findData("zh-CN")
    with qtbot.waitSignal(window.source_language_changed, timeout=1000) as blocker:
        window._src_combo.setCurrentIndex(zh_idx)
    assert blocker.args == ["zh-CN"]
    assert repo.get("default_source_language") == "zh-CN"

    # Test provider change
    prov_idx = window._prov_combo.findData("cloud_v2")
    with qtbot.waitSignal(window.provider_changed, timeout=1000) as blocker:
        window._prov_combo.setCurrentIndex(prov_idx)
    assert blocker.args == ["cloud_v2"]
    assert repo.get("default_translation_provider") == "cloud_v2"


@pytest.mark.ui
def test_settings_dialog_save(qtbot: QtBot, tmp_path: Path) -> None:
    settings_file = tmp_path / "settings.json"
    repo = JsonSettingsRepository(file_path=settings_file)

    dialog = SettingsDialog(settings_repo=repo)
    qtbot.addWidget(dialog)

    dialog._api_key_edit.setText("AIzaSyTestKey123456789")
    dialog._hotkey_edit.setText("<ctrl>+<alt>+x")

    with qtbot.waitSignal(dialog.settings_saved, timeout=1000):
        dialog._save_btn.click()

    assert repo.get("google_translate_api_key") == "AIzaSyTestKey123456789"
    assert repo.get("hotkey") == "<ctrl>+<alt>+x"
