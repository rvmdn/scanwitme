# Changelog — ScanWitMe PC

Semua pembaruan penting pada proyek **ScanWitMe PC** didokumentasikan dalam berkas ini. Format penulisan mengacu pada [Keep a Changelog](https://keepachangelog.com/id/1.1.0/) dan mengikuti standar [Semantic Versioning](https://semver.org/).

---

## [1.2.0] - 2026-11-14

### ✨ Ditambahkan
- **Header Quick Theme Switcher (1-Klik Ganti Tema)**:
  - Tombol icon di header jendela utama untuk merotasi tema secara instan: **Dark (Slate)** ➔ **AMOLED (Pure Black)** ➔ **Light (Bersih)** dengan indikator ikon dinamis (`🌙` / `⚫` / `☀️`).
- **Live Radar Status Hero Card (Diadaptasi dari Mobile ScanWitMe.ai)**:
  - Kartu visual status pemindai di jendela utama dengan indikator denyut radar `⚡ RADAR SIAP • STANDBY` dan transisi otomatis ke `🟢 RADAR AKTIF • MEMANTAU KOMIK` berlatar emerald saat Live Auto-Scan aktif.
  - Badge ringkasan konfigurasi aktif real-time (contoh: `JA ➔ ID • Manga RTL`).
- **Quick Comic Readers Launcher**:
  - Tombol akses 1-klik untuk membuka platform baca komik populer desktop (Webtoon, MangaDex, AsuraScan) langsung di web browser sekaligus menyiapkan pemindai.
- **Persistent Floating AI Quick Trigger Widget (Diadaptasi dari Mobile ScanWitMe.ai)**:
  - Tombol melayang *StayOnTop* bergaya squircle dengan gradasi signature ScanWitMe (`#6366F1` ➔ `#8B5CF6`) dan ikon bintang AI Sparkle.
  - Dapat digeser (*draggable*) ke posisi mana pun di tepi layar.
  - *Klik Kiri*: Memicu pemindaian area layar seketika tanpa perlu membuka jendela utama atau menekan hotkey keyboard.
  - *Klik Kanan*: Menu konteks cepat untuk Scan Area, Buka Sniper Frame, Toggle Live Auto-Scan, dan Buka Jendela Utama.
  - Indikator cincin neon berputar saat proses OCR dan terjemahan sedang berlangsung.
- **Interactive Bubble Action Toolbar (Diadaptasi dari Mobile ScanWitMe.ai)**:
  - Mini toolbar melayang yang otomatis muncul tepat di atas/bawah balon percakapan manga saat balon diklik.
  - Tombol **`📋 Salin`** (*1-Click Copy*): Menyalin teks dialog (asli maupun terjemahan) langsung ke clipboard dengan indikator visual *✓ Disalin!*.
  - Tombol **`🔍 Cari`** (*Google Search*): Membuka pencarian Google di browser default untuk mencari referensi istilah, nama karakter, atau lore komik.
  - Tombol **`✖ Tutup`**: Menutup mini toolbar secara instan tanpa menutup overlay balon lainnya.
  - Sinyal event baru `bubble_copied` dan `bubble_searched` untuk integrasi eksternal.

---

## [1.1.0] - 2026-10-25

### ✨ Ditambahkan
- **Kamus Istilah Komik & Glosarium Kustom (Custom Glossary)**:
  - 40+ preset istilah populer untuk Manga (JA), Manhwa (KO), dan Manhua / Wuxia (ZH).
  - Penggantian kata pintar berbasis regex word boundary dan pencocokan substring CJK.
- **Riwayat Dialog Komik & Bookmark Favorit (SQLite WAL Mode)**:
  - Penyimpanan lokal persisten untuk setiap teks yang dipindai.
  - Filter tab bahasa, filter dialog favorit (⭐), pencarian instan, dan ekspor data ke JSON / TXT.
- **Inno Setup Installer Script**:
  - Script installer profesional `ScanWitMe-Installer.iss` dengan kompresi LZMA2 ultra (~154 MB) dan pembuatan shortcut otomatis.

---

## [1.0.0] - 2026-10-21

### ✨ Rilis Perdana
- Mode Live Auto-Scan dengan deteksi scroll komik (*Live Watcher*).
- Balon percakapan inpainting langsung (*Direct Bubble Overlay*).
- Deteksi orientasi vertikal Manga Jepang (*Tategaki*) dan sortir urutan baca Kanan ke Kiri (*RTL*).
- OCR lokal berbasis PaddleOCR & Manga-OCR.
- Sniper Frame Mode (jendela bidik transparan mengambang).
- Integrasi Google Translate API & MyMemory Translation.
