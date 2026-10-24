# ScanWitMe — Developer & Agent Guide

Welcome to **ScanWitMe**, a Windows desktop application for manga, manhwa, and manhua readers that provides on-screen rectangular region capture, local OCR, and translation into Indonesian.

## Architecture Guidelines

ScanWitMe follows a strict layered architecture:

- **`scanwitme.domain`**: Pure Python data models, custom exception hierarchy, and abstract interfaces (`CaptureProvider`, `OCRProvider`, `TranslationProvider`, `SettingsRepository`, `CacheRepository`). No Qt or external API client dependencies here.
- **`scanwitme.application`**: Orchestrator layer (`ScanController`, `TranslationWorkflow`, `CacheService`). Manages scan state transitions (`idle`, `capturing`, `recognizing`, `translating`, `completed`, `error`, `cancelled`), deduplication, stale result rejection, and execution timing.
- **`scanwitme.infrastructure`**: Concrete adapters:
  - `capture`: `QtScreenCaptureProvider` (DPI-aware Windows screen capture).
  - `ocr`: `PaddleOCRProvider` (Local Korean and Chinese OCR models, deterministic block ordering).
  - `translation`: `CloudTranslationV2Provider` (Google Cloud Translation v2 REST API), `GoogleTranslateWebLauncher` (OS browser launcher).
  - `cache`: `SQLiteCacheRepository` (thread-safe, normalized text hashing, TTL support).
  - `settings`: `JsonSettingsRepository` (local config persistence with validation).
- **`scanwitme.presentation`**: PySide6 presentation layer:
  - `MainWindow`: Primary control window, hotkey configuration, provider selection.
  - `RegionSelector`: Transparent full-screen draggable rubber-band selection.
  - `FloatingOverlay`: Frameless, always-on-top, movable translation card with actions (copy, Google search, Google Translate launch, retry, dismiss).
  - `TrayManager`: Windows system tray icon and menu.
  - `workers`: `QRunnable` / `QThread` workers with Qt signals to keep all OCR and network operations off the main UI thread.

## Environment & Tooling

- **Python**: Python 3.11+ (verified on 3.12 64-bit on Windows).
- **Virtual Environment**: `.venv` in the repository root.
- **Package Manager / Build**: `pyproject.toml` (standard pip / setuptools).
- **Testing**: `pytest` with `pytest-qt` and `pytest-mock`.
- **Linting & Formatting**: `ruff check` and `ruff format`.

## Working Rules & Security Constraints

1. **Zero Secrets in Code or Logs**:
   - `GOOGLE_TRANSLATE_API_KEY` must only come from environment variables or settings file.
   - Never print API keys in logs, console, or UI error dialogs.
   - Never commit `.env` or any file containing credentials.
2. **Local OCR & Data Privacy**:
   - PaddleOCR runs 100% locally on the user's machine.
   - Screenshots are NEVER sent to the translation API or remote servers.
   - Only recognized text is sent to Google Cloud Translation.
3. **No Web Scraping**:
   - Google Translate website launcher strictly launches the default system browser with query parameters. Never scrape or emulate private API calls to translate.google.com.
4. **Synthetic Test Data**:
   - Never commit copyrighted manga/manhwa images. Use synthetic text images generated for testing.
5. **Thread Safety**:
   - Never perform screen capture processing, OCR inference, or HTTP requests on the Qt GUI thread. Always use workers with Qt signals.
