# Laporan Paket Pengumpulan BARA / KARSA-FIRE (Submission Package Report)
## Indonesia Fire Watch — Forest & Land Fire Geospatial Early Warning

> **Status Rilis:** Final Submission Freeze (`v0.1.0-alpha.10`)  
> **Tanggal Pembuatan Paket:** 2026-11-09  
> **Lokasi Paket Distribusi:** `submission/BARA-RELEASE/`  
> **Berkas Arsip Distribusi:** `submission/BARA-RELEASE.zip`  
> **Status Verifikasi:** **VERIFIKASI PENUH LULUS (ALL CHECKS PASSED)**

---

## 1. Struktur Paket Distribusi Final

Paket pengumpulan telah diisolasi ke dalam direktori mandiri `submission/BARA-RELEASE/` tanpa menyertakan secret privat, virtual environment lokal, maupun data cache runtime:

```
BARA-RELEASE/
├── README.md                                 # Panduan cepat instalasi, konfigurasi, & uji
├── AGENTS.md                                 # Standar teknis dan tata kelola sistem
├── CHANGELOG.md                              # Catatan riwayat versi (v0.1.0-alpha.1 hingga alpha.10)
├── .gitignore                                # Proteksi ganda secrets, cache, dan venv
├── docs/                                     # Dokumentasi lengkap Bahasa Indonesia
│   ├── USER_GUIDE.md                         # Panduan operasional bagi pengguna/operator
│   ├── SYSTEM_WORKFLOW.md                    # Arsitektur & diagram alir data (Mermaid)
│   ├── KNOWN_LIMITATIONS.md                  # Batasan ilmiah sensor satelit & sistem
│   ├── DEMO_GUIDE.md                         # Skenario 7 langkah live demo
│   ├── FINAL_RELEASE_CHECKLIST.md            # Audit kepatuhan pra-rilis
│   ├── SUBMISSION_PACKAGE_REPORT.md          # Berkas laporan pengumpulan ini
│   ├── PROJECT_STATE.md                      # Lembar fakta status proyek terkini
│   ├── DATA_DICTIONARY.md                    # Kamus data skema entitas & fitur
│   ├── DECISIONS.md                          # Rekaman keputusan arsitektur (ADR 001–008)
│   ├── ROADMAP.md                            # Rencana pengembangan jangka panjang
│   └── future/                               # Spesifikasi arsitektur enterprise masa depan
└── project_pkmm-master/                      # Aplikasi aktif BARA (Flask, Leaflet, XGBoost)
    ├── server.py                             # Server utama Flask (API, STAC, XGBoost)
    ├── firms_wms.py                          # Reverse proxy WMS NASA FIRMS
    ├── firms_sources.py                      # Multi-source CSV parser FIRMS
    ├── monitoring.py                         # Worker pemantauan grid 3x3 otomatis
    ├── notifications.py                      # Engine notifikasi & audit event
    ├── model_early_warning_sentinel2_xgb.joblib # Model terlatih XGBoost (10 fitur spektral)
    ├── indonesia.geojson                     # Geometri batas daratan kepulauan Indonesia
    ├── requirements.txt                      # Dependensi Python terkunci (xgboost==2.0.3)
    ├── .env.example                          # Template konfigurasi tanpa rahasia
    ├── .gitignore                             # Proteksi berkas lokal modul
    ├── start.bat                             # Peluncur instan Windows (auto-detect .venv)
    ├── PETUNJUK.md                           # Petunjuk lokal operasional
    ├── static/                               # Aset frontend web
    │   ├── index.html                        # Konsol dashboard operasional
    │   ├── app.js                            # Logika interaktif peta & polling
    │   └── style.css                         # Desain visual responsif BARA
    ├── screenshots/                          # 9 tangkapan layar bukti verifikasi peramban
    ├── test_app.py                           # Unit test Flask API & STAC
    ├── test_monitoring.py                    # Unit test pemantauan grid
    ├── test_notifications.py                 # Unit test engine notifikasi
    ├── test_wms.py                           # Unit test reverse proxy WMS
    ├── test_frontend.cjs                     # Suite pengujian frontend Node.js
    └── verify_browser.cjs                    # Skrip pengujian otomatis Chrome CDP
```

---

## 2. Daftar Berkas Penting & Integritas Data

| Berkas Penting | Ukuran | Status Integritas | Deskripsi |
|---|---|---|---|
| `model_early_warning_sentinel2_xgb.joblib` | ~501 KB | Asli / Terjaga | Model XGBoost pra-latih (10 fitur spektral Sentinel-2). Tidak diubah/dilatih ulang. |
| `indonesia.geojson` | ~469 KB | Asli / Terjaga | MultiPolygon batas daratan kepulauan Indonesia untuk filter ray-casting hotspot. |
| `requirements.txt` | 115 B | Terkunci | `Flask>=3.0,<4`, `requests>=2.31,<3`, `joblib>=1.3,<2`, `xgboost==2.0.3`, `scikit-learn>=1.4,<2`, `pandas>=2.0,<3`, `rasterio>=1.4,<2`. |
| `.env.example` | 1,085 B | Aman | Template variabel lingkungan tanpa rahasia asli (`YOUR_MAP_KEY_HERE`). |
| `server.py` | ~23 KB | Teruji | Endpoint Flask, integrasi AWS STAC COG, dan pipeline inferensi model. |
| `firms_wms.py` | ~4.4 KB | Teruji | Reverse proxy WMS 8 layer resmi NASA dengan MAP_KEY terlindungi di backend. |
| `firms_sources.py` | ~8.2 KB | Teruji | Parser 4 sumber satelit (VIIRS SNPP, NOAA-20, NOAA-21, MODIS) & deduplikasi. |
| `monitoring.py` | ~10 KB | Teruji | Grid 3x3 daratan, worker thread, round-robin, dan persistensi atomik. |
| `notifications.py` | ~31 KB | Teruji | Engine notifikasi severity INFO/WASPADA/DARURAT dengan audit trail. |
| `static/index.html` | ~24 KB | Bersih | Antarmuka dashboard (3 kartu operasional, tanpa elemen dummy). |
| `static/app.js` | ~38 KB | Teruji | Logika pemetaan Leaflet, sanitasi XSS, guard tab visibility, dan kontrol. |
| `static/style.css` | ~68 KB | Teruji | Tema operasional BARA, responsif mobile, scrollbar indikator toolbar. |

---

## 3. Hasil Pemeriksaan Keamanan Konfigurasi

1. **Pemeriksaan Secret & API Key:**
   - Berkas `.env` asli **TIDAK disertakan** di dalam paket `submission/BARA-RELEASE/`.
   - Tidak ada string rahasia yang pernah terlacak secara publik.
   - Variabel lingkungan hanya membaca dari `.env` lokal pengguna saat aplikasi berjalan.
2. **Pemeriksaan .gitignore:**
   - Aturan `.gitignore` diperiksa dan dipastikan **tidak menggunakan wildcard `*.json` yang berbahaya**.
   - Hanya berkas runtime yang diabaikan: `monitor_state.json`, `notification_state.json`, `*.tmp`, `*.corrupt`.
   - Berkas `indonesia.geojson` dan dokumentasi aman serta terlacak dengan benar.
3. **Pembersihan Berkas Sementara:**
   - Tidak ada berkas `.DS_Store`, `Thumbs.db`, `.venv/`, `__pycache__/`, atau profil browser sementara di dalam paket distribusi.

---

## 4. Hasil Pengujian Akhir

### A. Pengujian Instalasi Lingkungan Bersih (Clean Venv Test)
Pengujian instalasi dijalankan pada virtual environment baru yang dibuat dari nol di direktori sementara (`%TEMP%`):
- Pemasangan seluruh dependensi dari `requirements.txt` selesai dengan sukses tanpa kompilasi C++ tambahan.
- Eksekusi seluruh 75 tes unit backend langsung dari folder paket distribusi menghasilkan:
  `Ran 75 tests in 0.624s — OK`.
- Virtual environment pengujian kemudian dibersihkan secara otomatis.

### B. Pengujian Backend Python (75 Unit Tests)
```powershell
cd project_pkmm-master
.\.venv\Scripts\python.exe -m unittest test_app test_monitoring test_notifications test_wms -v
```
**Hasil:** 75/75 tes lulus (100% PASS).

### C. Pengujian Frontend Node.js
```powershell
cd project_pkmm-master
node test_frontend.cjs
```
**Hasil:** 15 tes keamanan/responsif/XSS + 11 skenario WMS & GIBS lulus (ALL FRONTEND SUITE TESTS PASSED).

### D. Verifikasi Peramban (Headless Chrome via CDP)
- Viewport Desktop (1440 × 900) dan Mobile (390 × 844) teruji dengan 0 unhandled exceptions dan 0 console errors.
- 9 berkas tangkapan layar aktual tersimpan di `screenshots/`.

---

## 5. Cara Instalasi & Menjalankan di Komputer Lain

Langkah-langkah berikut ditujukan bagi pengguna baru atau penguji yang memindahkan paket ini ke komputer lain:

### Prasyarat:
- Python 3.11 atau lebih baru (direkomendasikan Python 3.11 – 3.13).
- Node.js v18+ (hanya jika ingin menjalankan pengujian frontend).
- Akses internet untuk mengunduh data satelit NASA dan AWS STAC.
- NASA FIRMS MAP_KEY gratis dari: https://firms.modaps.eosdis.nasa.gov/api/map_key/

### Langkah 1: Ekstraksi & Masuk ke Folder Proyek
Ekstrak berkas `BARA-RELEASE.zip` dan buka terminal di dalam folder `project_pkmm-master`:
```powershell
cd BARA-RELEASE\project_pkmm-master
```

### Langkah 2: Buat Virtual Environment & Pasang Dependensi
```powershell
# Membuat virtual environment
python -m venv .venv

# Mengaktifkan virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Memasang pustaka yang dibutuhkan
python -m pip install -r requirements.txt
```

### Langkah 3: Konfigurasi Berkas `.env`
Salin template konfigurasi:
```powershell
cp .env.example .env
```
Buka `.env` dengan teks editor dan masukkan kunci NASA FIRMS Anda:
```ini
FIRMS_MAP_KEY=masukkan_map_key_anda_di_sini
```

### Langkah 4: Jalankan Aplikasi Web
- Di Windows: Cukup klik ganda berkas `start.bat` (otomatis mendeteksi `.venv`), atau jalankan:
  ```powershell
  .\.venv\Scripts\python.exe server.py
  ```
- Di macOS / Linux:
  ```bash
  .venv/bin/python server.py
  ```

Buka peramban di: **`http://127.0.0.1:5000`**

### Langkah 5: Menjalankan Pengujian Verifikasi
```powershell
# Menjalankan tes backend
.\.venv\Scripts\python.exe -m unittest test_app test_monitoring test_notifications test_wms -v

# Menjalankan tes frontend
node test_frontend.cjs
```

---

## 6. Batasan Sistem yang Perlu Diketahui Penguji

1. **Deteksi Anomali Panas $\neq$ Kebakaran Terkonfirmasi:**  
   Satelit inframerah mendeteksi anomali radiasi termal (termasuk cerobong industri gas flaring atau permukaan seng panas). Kebakaran darat resmi tetap membutuhkan verifikasi lapangan.
2. **Near Real-Time (NRT):**  
   Data mengikuti siklus orbit satelit polar (jeda pengolahan ~1–3 jam), bukan rekaman streaming langsung/CCTV.
3. **Celah Orbit Khatulistiwa NASA GIBS:**  
   Garis diagonal hitam pada basemap MODIS Terra TrueColor adalah celah antar lintasan satelit alami di garis khatulistiwa.
4. **Penyaringan Awan Sentinel-2:**  
   Algoritma masker SCL menolak piksel berawan tebal demi akurasi ilmiah. Keterangan kendala analisis awan bukan jaminan wilayah aman.
5. **Kesesuaian Versi XGBoost:**  
   Model wajib dijalankan menggunakan `xgboost==2.0.3` (yang telah terpasang melalui `requirements.txt`).

---

## 7. Hal yang Memerlukan Konfigurasi Pengguna

- **Pengisian `FIRMS_MAP_KEY`:**  
  Karena alasan keamanan dan kepatuhan privasi, kunci API privat tidak dibagikan dalam paket distribusi. Pengguna baru harus mendaftar MAP_KEY gratis di portal NASA FIRMS dan menyalinnya ke berkas `.env` lokal sebelum menjalankan server. Jika belum diisi, aplikasi akan menampilkan panduan konfigurasi yang jelas pada antarmuka web tanpa menimbulkan galat *crash*.

