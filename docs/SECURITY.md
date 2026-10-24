# Security and Privacy Policy

## 1. Credential Management

- **No Hardcoded Secrets**: Secrets such as `GOOGLE_TRANSLATE_API_KEY` are never hardcoded in source code, default configurations, or test fixtures.
- **Environment & AppData Storage**: The API key is sourced from the `GOOGLE_TRANSLATE_API_KEY` environment variable or saved in a user-local configuration file located in the user's OS AppData folder.
- **Log Sanitization**: Logs and UI error dialogs must never display raw API keys or bearer tokens. If an authentication failure occurs, the error message reports the failure code without displaying credentials.
- **Git Protection**: `.gitignore` explicitly prevents `.env`, `.env.*`, and credential files from being tracked.

## 2. Data Privacy & Image Handling

- **Local OCR**: PaddleOCR executes 100% locally on the user's CPU/GPU. No images or screen crops leave the machine.
- **Zero Screenshot Uploads**: Screenshots are strictly used in memory for local OCR and are discarded immediately after inference unless debug persistence is explicitly configured by the developer.
- **Text Transmission**: Only recognized OCR text strings are transmitted over HTTPS to Google Cloud Translation API when Provider A is chosen.
- **No Telemetry or Analytics**: ScanWitMe does not include trackers, metrics beacons, crash telemetry, or user analytics.

## 3. Web Interaction & Browser Safety

- **URL Construction**: External links (Google Search, Google Translate web) use strict URL encoding (`urllib.parse.quote_plus`) to avoid injection attacks.
- **No Scraping**: ScanWitMe opens the system's default browser safely via OS shell execution (`webbrowser.open`). It never scrapes, evaluates, or injects JavaScript into external web pages.
