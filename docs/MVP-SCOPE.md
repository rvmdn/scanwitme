# ScanWitMe MVP Scope Specification

## Objective

Build a Windows-first desktop floating screen translator enabling readers of manga, manhwa, and manhua to capture dialogue on screen, perform local OCR, and translate it into Indonesian instantly.

## In-Scope Features

1. **Desktop Presentation (PySide6)**:
   - Primary control window with scan trigger, language pair selectors, provider toggle, and hotkey configuration.
   - Transparent fullscreen region selector with drag-to-select box and `Escape` key cancellation.
   - Draggable, always-on-top floating translation overlay with source/target text presentation.
   - Windows System Tray integration with quick scan and minimize/restore actions.

2. **Screen Capture**:
   - High-DPI and multi-monitor aware capture using `QScreen.grabWindow()`.
   - Automatic hiding and restoring of ScanWitMe windows during capture to prevent recursive self-capture.

3. **Local OCR (PaddleOCR)**:
   - Lazy loading of models to ensure rapid application startup.
   - Explicit configuration for Korean (`korean`) and Chinese (`ch`) models.
   - Structured `OCRBlock` extraction with bounding boxes and reading order sorting.

4. **Translation Providers**:
   - **Provider A**: Official Google Cloud Translation Basic v2 API integration via HTTP client. Supports auto-detection, `ko`, `zh-CN`, and `id` target.
   - **Provider B**: Google Translate Web Launcher, opening the OS browser with prefilled text and query params.

5. **Actions & Caching**:
   - Single-click actions: Copy Source, Copy Translation, Google Search source text, Open in Google Translate.
   - Local SQLite cache for translated phrases with normalized hash keys to prevent redundant API calls.

## Out-of-Scope Features

- Android / iOS / macOS / Linux builds.
- Continuous per-frame video OCR or live background streaming.
- Inpainting, image text erasing, or balloon redraw over original art.
- User accounts, cloud sync, or subscription mechanisms.
- Scraping or reverse-engineering `translate.google.com` HTML.
- Bypassing DRM or protected video content.
- Uploading whole screenshots to third-party cloud servers.
