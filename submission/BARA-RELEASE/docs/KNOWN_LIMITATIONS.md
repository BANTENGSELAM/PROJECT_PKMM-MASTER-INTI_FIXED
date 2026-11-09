# Batasan Sistem & Keterbatasan Ilmiah (Known Limitations)
## BARA — Sistem Pemantauan Indikasi Kebakaran Hutan dan Lahan

Dokumen ini mencatat secara transparan batasan teknis, karakteristik sensor satelit, dan fitur-fitur yang belum tersedia pada prototipe **BARA** (inisiatif historis BARA / KARSA-FIRE) saat ini.

---

## 1. Keterbatasan Ilmiah & Penginderaan Jauh

### A. Anomali Panas Satelit Bukan Kebakaran Terkonfirmasi
- Sensor satelit inframerah (VIIRS pada Suomi-NPP/NOAA-20/NOAA-21 dan MODIS pada Terra/Aqua) mendeteksi **anomali radiasi termal (thermal anomalies)** pada panjang gelombang inframerah tengah (~3,9–4,0 µm).
- Sumber anomali termal dapat berasal dari:
  1. Kebakaran hutan, gambut, atau lahan (*target utama*).
  2. Suar gas industri (*gas flaring*) pada fasilitas kilang minyak atau petrokimia.
  3. Aktivitas vulkanik atau manifestasi geotermal.
  4. Permukaan buatan yang sangat menyerap panas (atap pabrik seng besar, aspal terbuka).
- Oleh karena itu, seluruh deteksi NASA FIRMS harus diperlakukan sebagai **indikasi awal yang memerlukan verifikasi lapangan**, bukan kebakaran darat yang pasti.

### B. Waktu Keterlambatan Data Satelit (Near Real-Time vs Real-Time Instan)
- Sistem bekerja secara **Near Real-Time (NRT)**, bukan *real-time* instan layaknya streaming video atau CCTV.
- Satelit pengorbit kutub (polar-orbiting) hanya melintas di atas wilayah Indonesia pada jam-jam tertentu (biasanya 2 kali sehari per satelit).
- Terdapat jeda waktu (*latency*) sekitar 1 hingga 3 jam antara waktu pengamatan satelit di antariksa, pengunduhan data ke stasiun bumi, pemrosesan oleh NASA FIRMS, hingga dapat diakses oleh API.

### C. Celah Orbit Khatulistiwa pada NASA GIBS (Pita Diagonal Hitam)
- Pada peta dasar citra satelit harian **NASA GIBS (MODIS Terra TrueColor)**, sering terlihat garis atau pita diagonal berwarna hitam di wilayah khatulistiwa Indonesia.
- **Penyebab:** Ini adalah celah alami antar-lintasan orbit (*orbital swath gaps*) sensor MODIS di garis ekuator bumi pada hari yang sama. Fenomena ini normal dalam data penginderaan jauh harian dan bukan merupakan galat (*bug*) pada aplikasi.

### D. Tutupan Awan Tropis pada Citra Sentinel-2
- Indonesia memiliki tutupan awan tropis (*cumulus/cumulonimbus*) yang tinggi sepanjang tahun.
- Analisis optik Sentinel-2 mengandalkan kanal reflektansi permukaan (Level-2A). Jika suatu lokasi tertutup awan tebal, kabut asap pekat, atau bayangan awan, algoritma *Scene Classification Layer* (SCL) akan menolak piksel tersebut demi menjaga keakuratan.
- Jika 5 adegan terakhir tertutup awan, analisis grid akan berstatus *error / kualitas citra*. **Kegagalan analisis karena awan bukan berarti lokasi tersebut aman dari kebakaran.**

---

## 2. Batasan Pemodelan & Machine Learning

### A. Sampel Titik Diskrit (Grid 3 × 3)
- Pemantauan otomatis area membagi kotak pilihan ke dalam grid titik diskrit berukuran 3 × 3 (maksimal 9 titik daratan).
- Ini adalah **metode pensampelan titik diskrit**, bukan pembuatan peta raster kontur risiko kontinu di seluruh lanskap wilayah.
- Area di antara titik-titik grid tidak dianalisis secara otomatis oleh model.

### B. Karakteristik Model XGBoost & Serialisasi
- Berkas model `model_early_warning_sentinel2_xgb.joblib` dilatih pada kombinasi 10 fitur spektral (`B2, B3, B4, B8, B11, B12, NDVI, NDWI, longitude, latitude`).
- Model diserialisasi menggunakan **XGBoost versi 2.0.3**. Jika dijalankan pada lingkungan Python dengan XGBoost versi 3.x, sistem dapat mengalami peringatan atau galat ketidakcocokan serialisasi C-API (`XGBoostError: input stream corrupted`). Pengguna diwajibkan menggunakan *virtual environment* yang telah disediakan (`.venv`).
- Nilai probabilitas model (misalnya 75% Kelas 1) mencerminkan derajat kemiripan karakteristik spektral vegetasi kering dengan data latih, bukan kepastian probabilitas absolut kebakaran di lapangan.

---

## 3. Fitur yang Belum Diimplementasikan (Not Implemented / Partial)

| Fitur | Status | Penjelasan & Rencana |
|---|---|---|
| **Laporan Masyarakat (Citizen Reporting)** | `NOT IMPLEMENTED` | Antarmuka pengaduan warga publik dan basis data laporan saksi mata darat belum dibuat. Kartu indikator telah dirapikan dari dashboard agar tidak membingungkan pengguna. |
| **Gateway SMS / WhatsApp / Email Otomatis** | `PARTIAL` | Arsitektur penanganan notifikasi dan tabel log pengiriman (*delivery audit*) telah tersedia secara internal (in-app). Namun, integrasi ke penyedia gateway SMS/WhatsApp (seperti Twilio, WhatsApp Cloud API, atau SMTP eksternal) belum diaktifkan. |
| **Pelacakan GPS Petugas (Live Ground Tracking)** | `NOT IMPLEMENTED` | Pelacakan posisi koordinat personel damkar secara langsung di lapangan belum didukung dan tidak termasuk dalam cakupan tahap prototipe ini. |
| **Penyimpanan Multi-Layer WMS Simultan** | `PARTIAL` | Endpoint proxy mendukung 8 layer WMS NASA secara bergantian (satu layer aktif per waktu). Penggabungan beberapa layer WMS sekaligus dalam satu kanvas peta belum didukung oleh struktur path upstream NASA. |
| **Penyimpanan Basis Data Terdistribusi (PostGIS/FastAPI)** | `FUTURE SPEC` | Prototipe saat ini menggunakan persistensi file JSON atomik (`monitor_state.json`, `notification_state.json`). Spesifikasi enterprise berbasis FastAPI + PostGIS + H3 disimpan terpisah pada `docs/future/`. |

