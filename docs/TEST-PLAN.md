# ScanWitMe Test Plan

This document describes the testing strategy, test layers, test execution commands, and coverage targets for **ScanWitMe**.

## 1. Testing Philosophy

- **Speed & Isolation**: Unit tests run 100% in memory without network calls or GPU/OCR model downloads.
- **Predictable Mocks**: Translation API calls are mocked using deterministic HTTP responses via pytest fixtures.
- **DPI and UI Safety**: UI component tests utilize `pytest-qt` to simulate user actions, signals, and widget states cleanly without blocking the event loop or relying on sleep timers.
- **Legally Usable Fixtures**: OCR integration tests use programmatically generated synthetic images containing Korean and Chinese text glyphs to prevent copyright infringement.

## 2. Test Suites

### Unit Tests (`tests/unit/`)
- `test_domain_models.py`:
  - `CaptureResult`, `OCRBlock`, `TranslationResult`, `ScanSession` validation.
  - Sorting and reading order calculations on OCR blocks.
- `test_cache_service.py`:
  - Text normalization (casing, trailing whitespace, line endings).
  - Deterministic SHA-256 key computation.
  - In-memory SQLite cache hit/miss behavior and expiration.
- `test_scan_controller.py`:
  - State machine transitions: `idle -> capturing -> recognizing -> translating -> completed`.
  - Cancellation handling at each phase.
  - Rejection of overlapping capture triggers.
  - Stale asynchronous result rejection via monotonically increasing session counters.
- `test_translation_v2_provider.py`:
  - Request body construction and query parameter validation.
  - Bounded retry backoff on HTTP 429/503.
  - Normalization of Google Cloud errors: 401/403 -> `AuthenticationError`, 429 -> `QuotaExceededError`.
- `test_web_launcher.py`:
  - Safe URL parameter encoding (`urllib.parse.quote_plus`).
  - Validation of source/target language codes.

### Integration Tests (`tests/integration/`)
- `test_sqlite_cache_repository.py`:
  - Thread safety and persistent disk reads/writes.
  - Cache table creation, vacuum, and clear operations.
- `test_cloud_translation_live.py`:
  - Opt-in test with real `GOOGLE_TRANSLATE_API_KEY` (skipped by default if env var is missing).

### UI Tests (`tests/ui/`)
- `test_region_selector.py`:
  - Escape key cancels selection and emits `cancelled` signal.
  - Dragging creates valid selection geometry.
  - Inverted drag coordinates (e.g. bottom-right to top-left) are normalized to positive width/height.
- `test_floating_overlay.py`:
  - Text rendering and source/target display.
  - Copy button interaction and system clipboard updating.
  - Dragging repositioning without window frame borders.

## 3. Test Execution Commands

```powershell
# Run all unit tests
pytest -m "unit"

# Run all tests except live external APIs
pytest -m "not live_api"

# Run UI tests with Qt fixture
pytest tests/ui/

# Run with verbose output and failure tracebacks
pytest -vv --tb=short
```
