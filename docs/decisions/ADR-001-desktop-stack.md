# ADR-001: Desktop Application Framework Selection

## Status
Accepted

## Context
ScanWitMe requires a Windows-native desktop application capable of:
1. Low-latency, multi-monitor, High-DPI screen capture.
2. Transparent fullscreen rubber-band region selection.
3. A frameless, draggable, always-on-top floating translation overlay card.
4. System tray integration and background worker execution with responsive UI rendering.

Options considered:
1. **PySide6 (Qt for Python)**: Native C++ bindings, mature High-DPI support, robust signals/slots threading model, rich widget library, system tray support.
2. **Tkinter**: Built-in, but poor High-DPI rendering on Windows, lacks modern frameless transparency controls and cross-platform native tray features.
3. **Electron / Tauri**: High memory overhead, extra bridge complexity between Python OCR engine and web renderer.

## Decision
We select **PySide6** (Qt 6) as the primary desktop UI framework.

## Consequences
- **Positive**:
  - Full control over screen coordinate systems, DPI scaling, and multi-monitor setups.
  - Native always-on-top flags (`Qt.WindowStaysOnTopHint`), frameless transparent windows (`Qt.FramelessWindowHint`).
  - Thread-safe background execution with `QThreadPool` / `QRunnable` / `Signal`.
- **Negative / Mitigations**:
  - Requires large binary dependency packages (~120MB). Addressed by standard virtual environment management and packaging tools (e.g. PyInstaller or Nuitka).
