# ScanWitMe PC

**ScanWitMe** is a Windows desktop application for readers of manga, manhwa, and manhua who need instant translation of foreign-language text displayed on their PC screen.

## Features (v1.0)

- **In-App Direct Free Translation**: Translates recognized dialogue directly inside the floating tool into Indonesian with zero setup and no API key required.
- **Sniper Frame Mode**: Floating viewfinder frame that stays over your comic/manga, ready to scan repeatedly with one click or `Enter`.
- **Auto Language Detection**: Automatically recognizes Mandarin (Hanzi), Korean (Hangul), Japanese (Kana), and English scripts.
- **Global Hotkey & Fast Selection**: Press `Ctrl+Shift+S` anywhere in Windows to trigger rectangular selection.
- **Local OCR via PaddleOCR**: Runs 100% locally on your machine with high accuracy for Asian scripts.
- **Floating Translation Overlay**: Frameless, movable, always-on-top card displaying both original and translated text with 1-click copy buttons.
- **Multi-Provider & Web Fallbacks**: Quick buttons for Google Search, Google Translate Web, and Google Lens. Also supports Google Cloud Translation v2 with private API keys.
- **Smart Caching**: Persistent SQLite cache prevents redundant translation requests for repeated dialogue.
- **Privacy & Security**: Zero transmission of raw screenshots to external servers; screenshots are processed locally on device.

## Requirements

- Windows 10 / 11 (64-bit)
- Python 3.11+ (or portable launcher)

## Installation & Setup

1. **Clone repository and setup virtual environment**:
   ```powershell
   git clone <repo_url>
   cd scanwitme
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**:
   ```powershell
   pip install -e ".[dev]"
   ```

3. **Configure Environment**:
   Copy `.env.example` to `.env`:
   ```powershell
   copy .env.example .env
   ```
   Add your `GOOGLE_TRANSLATE_API_KEY` to `.env` if using the Cloud API.

4. **Run the Application**:
   - **Opsi 1 (1-Click Launcher)**: Cukup klik ganda [`ScanWitMe-Launcher.bat`](ScanWitMe-Launcher.bat) atau [`ScanWitMe.vbs`](ScanWitMe.vbs) (mode senyap tanpa CMD popup).
   - **Opsi 2 (Versi Portable Standalone)**: Buka folder [`dist/ScanWitMe/`](dist/ScanWitMe/) dan jalankan `ScanWitMe.exe` langsung (tidak memerlukan instalasi Python/Git).
   - **Opsi 3 (Terminal Python)**:
     ```powershell
     python -m scanwitme
     ```

## Development & Testing

Run unit and integration tests:
```powershell
pytest
```

Run linter:
```powershell
ruff check .
```

Run formatter:
```powershell
ruff format .
```
