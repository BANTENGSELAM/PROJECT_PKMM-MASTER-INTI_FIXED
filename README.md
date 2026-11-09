# BARA / KARSA-FIRE — Indonesia Fire Watch

> **Sistem Pemantauan Anomali Panas & Deteksi Dini Kebakaran Hutan dan Lahan Indonesia**  
> Prototipe Operasional: `project_pkmm-master/` | Dokumentasi: `docs/` | Versi: `0.1.0-alpha.6`

---

## 1. Ringkasan Proyek

**BARA (Indonesia Fire Watch)** / **KARSA-FIRE** adalah sistem pemantauan geospasial interaktif yang dirancang untuk mendukung deteksi dini dan pemantauan anomali panas di seluruh daratan Indonesia.

Aplikasi memadukan:
1. **NASA FIRMS API (CSV Hotspots):** Data deteksi anomali panas harian dari 4 sumber satelit (*VIIRS S-NPP*, *VIIRS NOAA-20*, *VIIRS NOAA-21*, dan *MODIS NRT*).
2. **NASA FIRMS WMS Proxy:** Lapisan ubin visual transparan resmi NASA dengan 8 pilihan layer yang dialirkan secara aman tanpa membocorkan API key ke publik.
3. **NASA GIBS WMTS Basemap:** Peta dasar citra satelit optik dunia nyata (*MODIS Terra TrueColor* dan *VIIRS NOAA-20*) lengkap dengan penanganan fallback tanggal otomatis.
4. **AWS Earth Search STAC & Sentinel-2 L2A COG:** Pengambilan kanal reflektansi spektral permukaan bumi resolusi 10–20 meter dengan penyaringan tutupan awan otomatis (*Scene Classification Layer* / SCL).
5. **Machine Learning XGBoost:** Model klasifikasi kerawanan vegetasi berbasis 10 fitur spektral (`B2, B3, B4, B8, B11, B12, NDVI, NDWI, bujur, lintang`).
6. **Pemantauan Grid Otomatis:** Pemantauan berkala area daratan menggunakan sampel grid 3 × 3 berbasis proses latar belakang (*background worker thread*).
7. **Pusat Notifikasi & Tata Kelola Event:** Manajemen notifikasi berbasis severity (`INFO`, `WASPADA`, `DARURAT`) dengan syarat verifikasi petugas manusia.

> [!IMPORTANT]
> **Prinsip Integritas Ilmiah:**
> - Titik deteksi satelit adalah **anomali panas inframerah (thermal anomalies)**, bukan kebakaran darat yang otomatis terkonfirmasi.
> - Data bekerja secara **near real-time**, mengikuti siklus orbit satelit (bukan tayangan CCTV seketika).
> - Hasil model Sentinel-2 adalah **potensi kondisi spektral**, bukan ramalan mutlak api.

---

## 2. Struktur Repositori

```
PROJECT_PKMM/
├── project_pkmm-master/          # Kode sumber prototipe aktif
│   ├── server.py                 # Server utama Flask (API, STAC, XGBoost pipeline)
│   ├── firms_wms.py              # Blueprint reverse proxy WMS NASA FIRMS
│   ├── firms_sources.py          # Parser multi-source CSV FIRMS & normalisasi
│   ├── monitoring.py             # Engine pemantauan grid 3x3 otomatis
│   ├── notifications.py          # Engine pusat notifikasi & siklus event
│   ├── model_early_warning_sentinel2_xgb.joblib  # Model trained XGBoost
│   ├── indonesia.geojson         # Batas wilayah daratan kepulauan Indonesia
│   ├── .env.example              # Contoh konfigurasi variabel lingkungan
│   ├── requirements.txt          # Daftar pustaka Python yang dibutuhkan
│   ├── start.bat                 # Skrip peluncuran instan Windows
│   ├── static/                   # Antarmuka frontend (HTML5, Vanilla JS, CSS)
│   │   ├── index.html            # Halaman konsol dashboard
│   │   ├── app.js                # Logika Leaflet, interaksi UI, & polling
│   │   └── style.css             # Tema desain operasional BARA
│   ├── test_app.py               # Unit test Flask API & STAC
│   ├── test_monitoring.py        # Unit test grid monitoring
│   ├── test_notifications.py     # Unit test engine notifikasi
│   ├── test_wms.py               # Unit test WMS proxy
│   └── test_frontend.cjs         # Pengujian integrasi antarmuka Node.js
├── docs/                         # Pusat dokumentasi lengkap
│   ├── USER_GUIDE.md             # Panduan pengoperasian untuk pengguna & operator
│   ├── SYSTEM_WORKFLOW.md        # Penjelasan arsitektur dan alur kerja aktual
│   ├── KNOWN_LIMITATIONS.md      # Batasan sistem, sensor, & fitur yang belum siap
│   ├── DEMO_GUIDE.md             # Skenario demonstrasi langkah-demi-langkah
│   ├── PROJECT_STATE.md          # Status riwayat pengembangan dan pengujian
│   └── future/                   # Rencana arsitektur enterprise skala besar
└── README.md                     # Berkas ini
```

---

## 3. Prasyarat Sistem

- **Sistem Operasi:** Windows 10/11, macOS, atau Linux.
- **Python:** Versi 3.11 atau lebih baru (sangat disarankan menggunakan virtual environment `.venv` dengan `xgboost==2.0.3` dan `rasterio`).
- **Node.js:** v18+ (diperlukan untuk menjalankan pengujian frontend `test_frontend.cjs`).
- **NASA FIRMS MAP_KEY:** Kunci API gratis dari NASA EOSDIS.  
  Dapatkan di: https://firms.modaps.eosdis.nasa.gov/api/map_key/

---

## 4. Instalasi & Konfigurasi

### Langkah 1: Pasang Dependensi Python

Buka terminal (PowerShell di Windows atau Bash di macOS/Linux):

```powershell
cd project_pkmm-master

# Membuat virtual environment (jika belum ada)
python -m venv .venv

# Mengaktifkan virtual environment
# Di Windows:
.\.venv\Scripts\Activate.ps1
# Di macOS / Linux:
source .venv/bin/activate

# Memasang pustaka dependensi
python -m pip install -r requirements.txt
```

*(Catatan: Pastikan `rasterio` dan `xgboost` terpasang dengan baik di dalam virtual environment).*

### Langkah 2: Konfigurasi Berkas `.env`

Salin berkas template konfigurasi:

```powershell
cp .env.example .env
```

Buka berkas `.env` dengan editor teks (Notepad, VS Code, dsb.) dan isi `FIRMS_MAP_KEY` Anda:

```ini
# Kunci API resmi dari NASA FIRMS (Wajib untuk data titik panas)
FIRMS_MAP_KEY=masukkan_map_key_anda_di_sini

# Sumber satelit FIRMS yang aktif (dipisahkan koma)
FIRMS_SOURCES=VIIRS_SNPP_NRT,VIIRS_NOAA20_NRT,VIIRS_NOAA21_NRT,MODIS_NRT

# Rumus NDWI (green_nir untuk McFeeters, nir_swir untuk Gao)
NDWI_FORMULA=green_nir

# Interval polling notifikasi FIRMS (detik)
NOTIFICATION_FIRMS_INTERVAL=300

# Batas kapasitas riwayat notifikasi & event
NOTIFICATION_MAX_RECORDS=2000
NOTIFICATION_MAX_EVENTS=1000
```

> [!WARNING]
> Jangan pernah membagikan berkas `.env` atau mengunggahnya ke repositori Git publik. Kunci API hanya diproses di backend dan tidak pernah dikirimkan ke peramban.

---

## 5. Menjalankan Aplikasi

### Di Windows:
Jalankan server Flask menggunakan virtual environment:

```powershell
cd project_pkmm-master
.\.venv\Scripts\python.exe server.py
```
*(Atau klik ganda berkas `start.bat` jika path virtual environment telah sesuai).*

### Di macOS / Linux:
```bash
cd project_pkmm-master
.venv/bin/python server.py
```

Setelah server aktif, buka peramban web dan kunjungi:
```
http://127.0.0.1:5000
```

*(Penting: Buka aplikasi melalui alamat server di atas. Jangan membuka berkas `static/index.html` secara langsung karena fungsionalitas API dan peta memerlukan server backend yang aktif).*

---

## 6. Menjalankan Rangkaian Pengujian

Seluruh komponen telah dilengkapi dengan pengujian otomatis (*unit tests* dan *integration tests*).

### A. Pengujian Backend (Python Unit Tests)
Jalankan 75 tes unit backend:

```powershell
cd project_pkmm-master
.\.venv\Scripts\python.exe -m unittest test_app test_monitoring test_notifications test_wms -v
```
*Hasil yang diharapkan: 75 tests passed (OK).*

### B. Pengujian Frontend (Node.js Test Suite)
Jalankan tes keamanan, sanitasi DOM, responsive logic, dan integrasi peta:

```powershell
cd project_pkmm-master
node test_frontend.cjs
```
*Hasil yang diharapkan: ALL FRONTEND SUITE TESTS PASSED SUCCESSFULLY.*

---

## 7. Indeks Dokumentasi Lengkap

Untuk panduan mendalam dan spesifikasi teknis, silakan merujuk pada dokumen di folder `docs/`:

1. [**Panduan Pengguna (docs/USER_GUIDE.md)**](docs/USER_GUIDE.md):  
   Tata cara pengoperasian dashboard, membaca legenda, menyaring titik anomali, melakukan analisis manual, mengatur pemantauan grid, dan mengelola notifikasi.
2. [**Alur Kerja & Arsitektur (docs/SYSTEM_WORKFLOW.md)**](docs/SYSTEM_WORKFLOW.md):  
   Diagram alir data lengkap (Mermaid), integrasi AWS STAC, reverse proxy WMS, worker thread pemantauan, dan tata kelola event darurat.
3. [**Batasan Sistem (docs/KNOWN_LIMITATIONS.md)**](docs/KNOWN_LIMITATIONS.md):  
   Keterbatasan ilmiah penginderaan jauh, celah orbit satelit, interferensi tutupan awan tropis, dan daftar fitur yang belum siap.
4. [**Panduan Demonstrasi (docs/DEMO_GUIDE.md)**](docs/DEMO_GUIDE.md):  
   Skenario presentasi dan demonstrasi langsung langkah-demi-langkah bagi penguji atau audiens.
5. [**Catatan Keputusan Desain (docs/DECISIONS.md)**](docs/DECISIONS.md):  
   Arsip Architecture Decision Records (ADR 001–008).
6. [**Kamus Data (docs/DATA_DICTIONARY.md)**](docs/DATA_DICTIONARY.md):  
   Spesifikasi skema data hotspot, citra, event, dan notifikasi.

---

## 8. Lisensi & Atribusi Data

- **NASA FIRMS:** Data titik panas disediakan oleh NASA LANCE / FIRMS MODAPS.
- **NASA GIBS:** Peta dasar satelit disediakan oleh NASA Global Imagery Browse Services (GIBS).
- **Copernicus Sentinel-2:** Citra multispektral Level-2A disediakan oleh Uni Eropa / ESA melalui AWS STAC Earth Search.
- **OpenStreetMap:** Peta dasar jalan dan wilayah © Kontributor OpenStreetMap.
