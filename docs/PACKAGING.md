# ScanWitMe — Windows Packaging Guide

This guide details how to build and package **ScanWitMe** into a standalone Windows executable.

## Prerequisites

- Windows 10 / 11 64-bit
- Python 3.11 or 3.12 64-bit
- Installed virtual environment (`.venv`) with all dependencies

## Packaging Methods

### 1. PyInstaller (Standard One-Folder Build)

Building a one-folder distribution is recommended for desktop applications with heavy native libraries (PySide6 Qt C++ binaries and PaddleOCR ONNX/Paddle runtimes):

```powershell
.\.venv\Scripts\pyinstaller.exe `
    --name ScanWitMe `
    --windowed `
    --noconfirm `
    --clean `
    --add-data "src/scanwitme;scanwitme" `
    --paths "src" `
    src/scanwitme/__main__.py
```

### 2. Standalone One-File Build

To generate a single `.exe` file:

```powershell
.\.venv\Scripts\pyinstaller.exe `
    --name ScanWitMe `
    --windowed `
    --onefile `
    --noconfirm `
    --clean `
    --add-data "src/scanwitme;scanwitme" `
    --paths "src" `
    src/scanwitme/__main__.py
```

The resulting binary will be placed in the `dist/` directory:
```
dist/
└── ScanWitMe/
    ├── ScanWitMe.exe
    └── ... (Qt and Python runtime DLLs)
```

## Running the Packaged Executable

1. Launch `dist/ScanWitMe/ScanWitMe.exe` or `dist/ScanWitMe.exe`.
2. The application minimizes to the Windows system tray and starts listening for `Ctrl+Shift+S`.
3. Configure your API key or preferences via the Settings dialog (`⚙ Pengaturan`).
