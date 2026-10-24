# ScanWitMe — Known Limitations and Operational Boundaries

This document records the architectural, OCR, capture, and translation limitations of **ScanWitMe PC (MVP)**.

## 1. Local OCR (PaddleOCR) Limitations

- **Manga Reading Order**:
  - ScanWitMe implements a top-to-bottom, left-to-right line grouping spatial sorter suited for modern digital manhwa/manhua (webtoons).
  - Traditional Japanese manga (right-to-left) or complex non-linear comic layouts with floating sound effects (SFX) may not follow standard horizontal reading order.
- **Stylized Typography and Sound Effects (SFX)**:
  - Dialogue with heavy decorative distortions, hand-drawn brush lettering, or integrated action SFX glyphs can yield lower OCR confidence or partial character omissions.
- **Vertical Text**:
  - Vertical dialogue columns common in Japanese manga are recognized on a best-effort basis; horizontal manhwa/manhua text bubbles have the highest recognition accuracy.
- **Speech Bubble Overlap**:
  - If the user selects a region containing multiple intersecting speech bubbles from different speakers, the text may be merged into a single sequential block.

## 2. Screen Capture Limitations

- **Capture Mechanism**:
  - Uses `QScreen.grabWindow()` in PySide6.
  - Windows display scaling factors (e.g. 125%, 150%, 175%) are normalized via `screen.devicePixelRatio()`.
- **DRM Protected Content**:
  - Applications utilizing hardware-protected overlays (such as Widevine DRM or certain protected reader apps with `WDA_EXCLUDEFROMCAPTURE`) may render as black/empty rectangles.
  - ScanWitMe does not attempt to bypass OS or DRM security controls.
- **Future Extensibility**:
  - The `CaptureProvider` abstract interface is isolated so that a future `WindowsGraphicsCaptureProvider` (utilizing WinRT `Windows.Graphics.Capture`) can be dropped in without changing application or presentation code.

## 3. Translation Providers & Google Cloud API

- **Costs and Quotas**:
  - Google Cloud Translation Basic (v2) is a commercial cloud API. Google Cloud offers a free tier (e.g. 500,000 characters free per month as of current terms), but usage exceeding the quota incurs standard Google Cloud billing.
  - Rate limits (e.g. queries per second) apply; transient 429 errors are retried automatically up to 3 times before raising `QuotaExceededError`.
- **Offline Mode**:
  - OCR operates 100% offline. Translation requires an active internet connection.
- **Website Launcher Fallback**:
  - `GoogleTranslateWebLauncher` opens the official `translate.google.com` URL in the default browser without requiring API credentials.
  - Translations completed in the browser do not synchronize back into the desktop overlay to strictly comply with Google Terms of Service (no scraping).

## 4. Performance Expectations

- **End-to-End Latency**:
  - Screen capture: ~10–30 ms.
  - OCR inference (CPU): ~200–600 ms for average dialogue bubbles on modern multi-core PCs.
  - Cloud Translation v2 API: ~80–250 ms depending on network latency.
  - Median end-to-end latency is comfortably under the 3.0-second benchmark target for typical dialogue selections.
