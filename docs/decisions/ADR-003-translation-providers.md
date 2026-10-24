# ADR-003: Translation Providers and Browser Launch Strategy

## Status
Accepted

## Context
ScanWitMe requires translation of extracted Korean and Chinese text into Indonesian (`id`).
Key requirements:
1. Support high-quality translation via official Google Cloud Translation API.
2. Provide a zero-cost fallback for users without a Google Cloud API key.
3. Obey Google terms of service: No HTML scraping, no private API emulation, no brittle reverse engineering.

Options considered:
- **Provider A**: Google Cloud Translation Basic (v2) REST API.
  - Official, documented, reliable. Requires billing/API key on Google Cloud.
- **Provider B**: Browser launcher (`GoogleTranslateWebLauncher`).
  - Launches user's default browser with prefilled URL (`https://translate.google.com/?sl=...&tl=id&text=...`).
  - Completely legal, official, zero cost, works without API keys.
- **Scraping / Reverse Engineering**:
  - Strongly rejected. Violates Google TOS, breaks frequently on UI changes, can trigger IP bans or CAPTCHAs.

## Decision
We implement:
1. `CloudTranslationV2Provider` as the direct in-app translation provider using official Google Cloud Translation v2 REST endpoints.
2. `GoogleTranslateWebLauncher` as an independent fallback launcher opening the default browser.
3. Explicitly document that web launcher results remain in the browser and do not magically sync to the overlay card without scraping.

## Consequences
- **Positive**:
  - Clean separation of concerns.
  - Strict compliance with API terms of service.
  - Users without an API key can still translate any text instantly in their browser with one click.
- **Negative / Mitigations**:
  - Cloud API usage costs money if free monthly character quota is exceeded. Documented transparently in documentation and `.env.example`.
