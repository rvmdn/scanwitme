# ScanWitMe PC

**ScanWitMe** is a Windows desktop application for readers of manga, manhwa, and manhua who need instant translation of foreign-language text displayed on their PC screen.

## Features (v1.0)

- **🔄 Mode Live Auto-Scan**: Otomatis mendeteksi saat halaman komik di-scroll dan langsung menerjemahkan panel baru tanpa perlu menekan tombol berulang kali.
- **💬 Direct Comic Bubble Inpainting**: Menempelkan teks terjemahan Bahasa Indonesia langsung di atas balon percakapan asli manga/manhwa dengan tipografi khas komik, penskalaan font otomatis, dan fitur *click-to-peek* untuk melihat teks aslinya.
- **⛩️ Manga-OCR & Teks Vertikal Jepang (縦書き)**: Deteksi otomatis orientasi vertikal (*Smart Detect*) dan pengurutan kolom tradisional Jepang dari Kanan ke Kiri (*Right-to-Left*) serta baris Atas ke Bawah (*Top-to-Bottom*).
- **⚡ In-App Direct Free Translation**: Menerjemahkan dialog langsung di dalam aplikasi ke Bahasa Indonesia secara instan tanpa perlu mendaftar atau memiliki API key.
- **🎯 Bingkai Pemindai (Sniper Frame Mode)**: Jendela bidik transparan yang mengambang di atas komik, siap memindai area pilihan berulang kali dengan satu klik atau tombol `Enter`.
- **🔍 Deteksi Bahasa Otomatis**: Mendeteksi skrip Korea (Hangul), Mandarin (Hanzi), Jepang (Kana/Kanji), dan Latin secara otomatis.
- **⌨️ Global Hotkey & Seleksi Cepat**: Tekan `Ctrl+Shift+S` di mana saja di Windows untuk memicu seleksi area persegi.
- **🧠 OCR Lokal Cepat (PaddleOCR & Manga-OCR)**: Berjalan 100% lokal di komputer tanpa mengirimkan gambar ke internet demi privasi data dan kecepatan maksimal.
- **📋 Floating Translation Card**: Kartu pop-up mengambang dan dapat digeser yang menampilkan teks asli dan terjemahan dengan tombol 1-klik salin (*copy*).
- **🌐 Integrasi Multi-Provider & Web Fallbacks**: Tombol akses cepat ke Google Search, Google Translate Web, dan Google Lens, serta dukungan opsional untuk Google Cloud Translation v2 dengan kunci API pribadi.
- **💾 Smart Caching (SQLite)**: Cache persisten lokal mencegah permintaan terjemahan berulang untuk menghemat kuota dan mempercepat pembacaan.
- **🧩 Arsitektur Metadata Terpusat**: Seluruh opsi bahasa, provider, dan mode terparameterisasi secara modular (*Single Source of Truth*).

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
