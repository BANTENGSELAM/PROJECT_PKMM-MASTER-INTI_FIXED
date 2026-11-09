# Checklist Kesiapan Rilis Akhir (Final Release Checklist)
## BARA — Sistem Pemantauan Indikasi Kebakaran Hutan dan Lahan

> **Versi Rilis:** `v0.1.0-alpha.9` (Release Freeze)  
> **Tanggal Audit:** 2026-11-09  
> **Lingkungan Produksi/Prototipe:** `project_pkmm-master/`  
> **Status:** **SIAP PENGUMPULAN & SIAP DEMONSTRASI (READY FOR SUBMISSION)**

---

## 1. Ringkasan Status Verifikasi

| Kategori Pemeriksaan | Status | Rincian Bukti Verifikasi |
|---|---|---|
| **Integritas Kode Sumber** | ✅ LULUS | Backend Flask, WMS proxy, monitoring worker, dan notification engine stabil tanpa error. |
| **Keamanan & Secrets** | ✅ LULUS | `.env` tidak masuk Git; `FIRMS_MAP_KEY` tidak bocor ke client; `.gitignore` aktif di root & modul. |
| **Dependensi Python** | ✅ LULUS | `requirements.txt` terkunci rapi (`xgboost==2.0.3`, `rasterio>=1.4,<2`); kompatibel dengan model. |
| **Pengujian Backend** | ✅ LULUS | 75/75 unit test lulus (100% OK dalam ~2.5 detik). |
| **Pengujian Frontend** | ✅ LULUS | 15 skenario keamanan/responsif + 11 skenario WMS/GIBS lulus pada `node test_frontend.cjs`. |
| **Verifikasi Peramban (CDP)** | ✅ LULUS | Google Chrome headless (1440×900 desktop & 390×844 mobile): 0 JS exceptions, 0 console errors. |
| **Konsistensi Dokumentasi** | ✅ LULUS | Seluruh panduan (USER_GUIDE, SYSTEM_WORKFLOW, KNOWN_LIMITATIONS, DEMO_GUIDE) sinkron. |
| **Kebersihan Distribusi** | ✅ LULUS | Cache `.DS_Store` dihapus; berkas runtime `.tmp` dan profil peramban sementara bersih. |

---

## 2. Checklist Detail Komponen Proyek

### A. Keamanan Konfigurasi & Berkas Sensitif
- [x] Berkas `.env` dipastikan **TIDAK** disertakan ke repositori Git publik.
- [x] Berkas `.env.example` terdokumentasi lengkap dengan nilai dummy (`YOUR_MAP_KEY_HERE`) tanpa rahasia asli.
- [x] Berkas `.gitignore` tersedia di root proyek dan di dalam `project_pkmm-master/`, mencakup `.env`, `.venv/`, `__pycache__/`, `monitor_state.json`, `notification_state.json`, `.DS_Store`, dan `.dist/`.
- [x] Endpoint proxy WMS (`/api/firms/wms`) menyisipkan MAP_KEY di path upstream internal dan memfilter header upstream sensitif.
- [x] Penanganan error di `server.py` membersihkan token/kredensial dari log sebelum dicetak ke terminal atau respons JSON.

### B. Dependensi & Lingkungan Eksekusi
- [x] Model machine learning `model_early_warning_sentinel2_xgb.joblib` diverifikasi memerlukan `xgboost==2.0.3` untuk deserialisasi yang aman pada Python 3.13.
- [x] `requirements.txt` diperbarui dan dikunci ke `xgboost==2.0.3` dan `rasterio>=1.4,<2`.
- [x] Virtual environment `.venv` di dalam `project_pkmm-master/` telah terpasang paket lengkap (`rasterio==1.5.2`, `xgboost==2.0.3`, `joblib`, `Flask`, `requests`, `scikit-learn`, `pandas`).
- [x] Skrip peluncuran Windows [**`project_pkmm-master/start.bat`**](file:///c:/Users/kenyi/Downloads/Ravenfield/PROJECT_PKMM-MASTER-INTI_REVISI-main/PROJECT_PKMM-MASTER-INTI_REVISI-main/project_pkmm-master/start.bat) tersedia untuk memudahkan penguji menjalankan server secara lokal.

### C. Antarmuka Pengguna & Responsivitas (UI/UX)
- [x] Tidak ada tombol atau menu palsu/dummy tanpa fungsi nyata.
- [x] Kartu placeholder *"Laporan Masyarakat"* telah dihilangkan dari dashboard utama.
- [x] Tata letak grid metrik operasional `.stats` menggunakan 3 kolom proporsional pada desktop dan 1 kolom rapi pada mobile.
- [x] Toolbar filter peta seluler dilengkapi indikator scrollbar horizontal agar kontrol lapisan peta dan basemap mudah ditemukan di ponsel.
- [x] Teks status pemantauan header seluler tidak terpotong pada layar 390px.
- [x] Tangkapan layar bukti demonstrasi tersedia lengkap di [**`project_pkmm-master/screenshots/`**](file:///c:/Users/kenyi/Downloads/Ravenfield/PROJECT_PKMM-MASTER-INTI_REVISI-main/PROJECT_PKMM-MASTER-INTI_REVISI-main/project_pkmm-master/screenshots/):
  - `01_desktop_overview.png`: Tampilan dashboard utama desktop.
  - `02_desktop_gibs_basemap.png`: Basemap satelit NASA GIBS MODIS Terra.
  - `03_desktop_wms_layer.png`: Overlay visual titik panas WMS FIRMS.
  - `04_desktop_marker_popup.png`: Pop-up rincian anomali panas satelit.
  - `05_desktop_notifications.png`: Pusat notifikasi & aksi penanganan event.
  - `08_desktop_priorities_and_grid.png`: Prioritas respons dan status grid Sentinel-2.
  - `09_desktop_manual_analysis_result.png`: Hasil inferensi live XGBoost satu titik.
  - `06_mobile_overview.png`: Antarmuka responsif seluler (iPhone).
  - `07_mobile_notifications.png`: Panel notifikasi versi seluler.

### D. Rangkaian Pengujian Otomatis
- [x] **Backend Unit Tests:** 75/75 lulus (`python -m unittest test_app test_monitoring test_notifications test_wms -v`).
- [x] **Frontend Tests:** Seluruh suite lulus (`node test_frontend.cjs`).
- [x] **Browser End-to-End CDP Test:** 0 exceptions (`node verify_browser.cjs`).

---

## 3. Struktur Berkas Utama Paket Distribusi

```
PROJECT_PKMM/
├── .gitignore                                # Proteksi secrets, venv, dan build cache
├── AGENTS.md                                 # Tata kelola teknis & aturan integritas data
├── CHANGELOG.md                              # Log riwayat pembaruan hingga v0.1.0-alpha.9
├── README.md                                 # Panduan ringkas setup, konfigurasi, & uji
├── docs/                                     # Dokumentasi sistem lengkap (Bahasa Indonesia)
│   ├── USER_GUIDE.md                         # Panduan operasional bagi pengguna
│   ├── SYSTEM_WORKFLOW.md                    # Arsitektur & alur diagram data Mermaid
│   ├── KNOWN_LIMITATIONS.md                  # Batasan ilmiah sensor & fitur parsial
│   ├── DEMO_GUIDE.md                         # Skenario demonstrasi langsung (live demo)
│   ├── FINAL_RELEASE_CHECKLIST.md            # Berkas ini (Audit kepatuhan rilis)
│   ├── PROJECT_STATE.md                      # Lembar fakta status proyek saat ini
│   ├── DATA_DICTIONARY.md                    # Kamus data skema payload & model
│   ├── DECISIONS.md                          # Rekaman keputusan arsitektur (ADR 001–008)
│   ├── ROADMAP.md                            # Peta jalan pengembangan jangka panjang
│   └── future/                               # Rencana arsitektur enterprise skala besar
└── project_pkmm-master/                      # Aplikasi aktif BARA (Source of Truth)
    ├── server.py                             # Server utama Flask (API, STAC, XGBoost)
    ├── firms_wms.py                          # Proxy WMS NASA FIRMS
    ├── firms_sources.py                      # Parser multi-source CSV NASA FIRMS
    ├── monitoring.py                         # Worker pemantauan grid 3x3 otomatis
    ├── notifications.py                      # Engine notifikasi & audit trail insiden
    ├── model_early_warning_sentinel2_xgb.joblib # Model terlatih XGBoost (10 fitur)
    ├── indonesia.geojson                     # Geometri batas daratan kepulauan Indonesia
    ├── requirements.txt                      # Dependensi pustaka Python
    ├── .env.example                          # Template konfigurasi variabel lingkungan
    ├── .gitignore                            # Proteksi secrets lokal direktori modul
    ├── start.bat                             # Peluncur instan Windows
    ├── static/                               # Berkas frontend antarmuka web
    │   ├── index.html                        # Konsol dashboard operasional
    │   ├── app.js                            # Logika Leaflet & integrasi frontend
    │   └── style.css                         # Lembar gaya desain operasional BARA
    ├── screenshots/                          # Tangkapan layar bukti verifikasi peramban
    ├── test_app.py                           # Unit test Flask API & STAC
    ├── test_monitoring.py                    # Unit test pemantauan grid
    ├── test_notifications.py                 # Unit test pusat notifikasi & event
    ├── test_wms.py                           # Unit test reverse proxy WMS
    ├── test_frontend.cjs                     # Suite pengujian frontend Node.js
    └── verify_browser.cjs                    # Skrip audit peramban Chrome CDP
```

---

## 4. Batasan Sistem yang Perlu Diketahui Penguji

1. **Anomali Panas $\neq$ Kebakaran Terkonfirmasi:**  
   Deteksi satelit inframerah mendeteksi anomali suhu (termasuk flare industri atau tanah sangat panas). Verifikasi patroli darat tetap diperlukan untuk menyatakan kebakaran resmi.
2. **Near Real-Time:**  
   Data mengikuti jadwal lintasan satelit polar (~1–3 jam delay pemrosesan), bukan kamera pengawas seketika.
3. **Celah Orbit MODIS Khatulistiwa:**  
   Pita celah hitam diagonal pada basemap NASA GIBS adalah fenomena alami rotasi bumi antar lintasan satelit kutub di ekuator.
4. **Tutupan Awan Sentinel-2:**  
   Lokasi dengan tutupan awan tebal ditolak oleh masker SCL demi integritas ilmiah. Status *kualitas citra* bukan bukti wilayah aman.
5. **Kesesuaian Versi XGBoost:**  
   Model harus dijalankan menggunakan XGBoost versi 2.0.3 (tersedia di `.venv`) agar tidak terjadi galat ketidakcocokan serialisasi C-API.

---

## 5. Panduan Pembuatan Paket Pengumpulan (Packaging)

Jika proyek hendak dikompresi menjadi arsip `.zip` untuk pengumpulan tugas akhir/evaluasi:

1. **JANGAN sertakan folder virtual environment (`.venv/`)** — folder ini berukuran besar (>500MB) dan spesifik terhadap mesin pengguna. Penerima paket cukup menjalankan `python -m pip install -r requirements.txt`.
2. **JANGAN sertakan berkas `.env` asli** — berkas `.env` memuat kunci API privat. Sertakan `.env.example` agar penerima dapat mengisi kuncinya sendiri.
3. **JANGAN sertakan folder profil cache sementara (`.dist/`, `chrome_cdp_profile*`, `__pycache__/`)**.
4. **PASTIKAN berkas model (`model_early_warning_sentinel2_xgb.joblib`) dan batas wilayah (`indonesia.geojson`) tetap ada** di dalam `project_pkmm-master/`.

