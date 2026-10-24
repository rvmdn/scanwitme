# ADR-002: Local OCR Engine Selection

## Status
Accepted

## Context
ScanWitMe targets manga, manhwa, and manhua dialogue translation. The OCR solution must:
1. Run entirely locally on the user's desktop without cloud API costs or privacy violations.
2. Provide high recognition accuracy for CJK scripts (specifically Korean Hangul and Chinese characters).
3. Return bounding box coordinates and confidence scores for reading order determination.
4. Support fast CPU inference on standard Windows machines.

Options considered:
1. **PaddleOCR**: State-of-the-art lightweight DBNet detection + SVTR/CRNN recognition models, out-of-the-box support for Korean (`korean`) and Chinese (`ch`), fast ONNX/Paddle inference on CPU.
2. **Tesseract (pytesseract)**: Poor recognition on stylized CJK fonts, sound effects, and vertical manga dialogue without extensive custom training.
3. **EasyOCR**: Solid accuracy, but PyTorch runtime dependency is significantly heavier (~800MB) compared to PaddleOCR on CPU.

## Decision
We select **PaddleOCR** as the local OCR provider.

## Consequences
- **Positive**:
  - Superior detection and recognition accuracy on Korean manhwa and Chinese manhua dialogue fonts.
  - Bounding box coordinates allow spatial sorting into natural reading order (top-to-bottom, left-to-right).
  - Works offline with zero per-request network costs.
- **Negative / Mitigations**:
  - First-time startup requires model weights download (~15-20MB per language). Mitigated by lazy initialization on first scan and informative progress indicators in the UI.
