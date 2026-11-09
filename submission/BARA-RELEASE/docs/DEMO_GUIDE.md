# Panduan Skenario Demonstrasi (Demo Guide)
## BARA — Sistem Pemantauan Indikasi Kebakaran Hutan dan Lahan

Dokumen ini disusun sebagai panduan langkah-demi-langkah bagi pemateri dalam melaksanakan presentasi atau pengujian langsung (*live demonstration*) aplikasi BARA (inisiatif historis BARA / KARSA-FIRE) di hadapan audiens atau penguji.

---

## 1. Persiapan Pra-Demonstrasi (Checklist)

Pastikan langkah-langkah berikut telah selesai 10 menit sebelum demonstrasi dimulai:

- [ ] **Koneksi Internet Aktif:** Diperlukan untuk mengakses NASA FIRMS, NASA GIBS, dan AWS STAC Sentinel-2.
- [ ] **Konfigurasi `.env`:** Pastikan berkas `.env` di dalam `project_pkmm-master/` sudah terisi dengan `FIRMS_MAP_KEY` yang valid.
- [ ] **Virtual Environment Python:** Gunakan Python dari `.venv` yang telah terpasang dependensi kompatibel (`rasterio`, `xgboost==2.0.3`):
  ```powershell
  cd project_pkmm-master
  .\.venv\Scripts\python.exe server.py
  ```
- [ ] **Buka Peramban:** Buka browser (Chrome / Edge / Firefox) dan arahkan ke:  
  `http://127.0.0.1:5000`
- [ ] **Muat Ulang Halaman:** Tekan `Ctrl + F5` (Hard Reload) untuk memastikan aset CSS dan JS termuat bersih tanpa cache lama.

---

## 2. Urutan Demonstrasi (Langkah Demi Langkah)

### Langkah 1: Menampilkan Peta Nasional & Sebaran Hotspot FIRMS
1. **Narasi:** Jelaskan bahwa BARA adalah sistem pemantauan anomali panas inframerah near real-time untuk wilayah Indonesia.
2. **Aksi:**
   - Tunjukkan sebaran titik anomali panas di kepulauan Indonesia.
   - Sorot kartu indikator utama di bagian atas (**Deteksi Anomali Panas**, **Insiden Terverifikasi**, **Area Pemantauan**).
   - Klik salah satu titik anomali panas (warna oranye/merah) di peta.
   - Tunjukkan kotak detail di sudut kanan bawah peta: koordinat, satelit (VIIRS/MODIS), waktu pengamatan (UTC & Lokal), tingkat keyakinan, dan daya radiasi api (FRP).
   - Jelaskan catatan integritas: *"Titik ini adalah anomali panas inframerah satelit, bukan kebakaran darat yang otomatis terkonfirmasi."*

### Langkah 2: Menguji Peta Dasar Satelit (NASA GIBS) & WMS Overlay
1. **Narasi:** Jelaskan kemampuan BARA menampilkan citra satelit bumi harian dari NASA GIBS.
2. **Aksi:**
   - Pada toolbar peta, ubah dropdown **Peta dasar** dari `OpenStreetMap` ke `NASA GIBS · MODIS Terra`.
   - Perlihatkan citra satelit asli bumi yang langsung termuat dari server NASA.
   - Jika terlihat garis celah diagonal, jelaskan secara ilmiah bahwa itu adalah *orbital swath gap* normal di ekuator.
   - Aktifkan kotak centang **"Lapisan WMS FIRMS"** untuk menampilkan lapisan ubin visual WMS yang diproxy secara aman oleh backend Flask tanpa membocorkan API key.
   - Kembalikan ke `OpenStreetMap` untuk kenyamanan visual berikutnya.

### Langkah 3: Menjalankan Analisis Manual Satu Titik (XGBoost & Sentinel-2)
1. **Narasi:** Jelaskan bagaimana model Machine Learning XGBoost menganalisis citra multispektral Sentinel-2 resolusi tinggi (10–20 meter).
2. **Aksi:**
   - Pada panel kanan, pilih tab **"Analisis Titik"**.
   - Klik salah satu titik daratan di peta (misalnya area perkebunan atau hutan di Kalimantan atau Sumatra). Koordinat otomatis terisi di form.
   - Klik tombol **"Analisis dengan XGBoost →"**.
   - Tunjukkan proses loading: sistem mencari katalog AWS STAC, memfilter awan dengan masker SCL, mengunduh 6 band spektral via COG, dan melakukan inferensi.
   - Tunjukkan hasil analisis: Status (**Berpotensi terbakar** atau **Aman menurut model**), rincian probabilitas kelas, tanggal citra yang dipakai, dan nilai fitur spektral (B2, B3, B4, B8, B11, B12, NDVI, NDWI).

### Langkah 4: Mendemonstrasikan Pemantauan Grid Otomatis (3 × 3)
1. **Narasi:** Tunjukkan kemampuan sistem menjalankan pemantauan latar belakang (*background automated worker*) tanpa campur tangan pengguna terus-menerus.
2. **Aksi:**
   - Buka tab **"Pemantauan Area"**.
   - Klik tombol **"Pilih area di peta (2 sudut)"**.
   - Di peta, klik dua sudut diagonal untuk membentuk kotak pemantauan (maksimal 2°).
   - Tunjukkan kotak putus-putus yang terbentuk.
   - Klik tombol **"Simpan area & mulai →"**.
   - Tunjukkan bahwa sistem membentuk titik-titik sampel grid 3 × 3 pada daratan.
   - Klik tombol **"Analisis sekarang"** untuk memajukan siklus dan menunjukkan proses analisis titik satu demi satu pada tabel **"Status tiap titik grid"**.

### Langkah 5: Memeriksa Prioritas Respons
1. **Narasi:** Tunjukkan bagaimana BARA membantu komando darurat menentukan prioritas penanganan di lapangan.
2. **Aksi:**
   - Gulir ke bagian **"Prioritas Respons"**.
   - Tunjukkan **Kolom 01 (Deteksi Anomali Panas 24 Jam):** Hotspot aktif NASA FIRMS terbaru yang harus diverifikasi terlebih dahulu oleh tim patroli darat.
   - Tunjukkan **Kolom 02 (Potensi Kerawanan Terbakar):** Titik grid hasil analisis model Sentinel-2 berstatus Kelas 1 (≤14 hari) untuk pencegahan dini.
   - Klik tombol **"↗ Peta"** pada salah satu baris prioritas: perlihatkan peta otomatis bergeser dan memperbesar lokasi titik tersebut.

### Langkah 6: Pusat Notifikasi & Tata Kelola Penanganan Event
1. **Narasi:** Jelaskan tata kelola notifikasi dan integritas bahwa status notifikasi dan insiden dikelola secara terstruktur dan transparan oleh petugas.
2. **Aksi:**
   - Klik tombol lonceng di header kanan atas untuk membuka panel **Pusat Notifikasi**.
   - Tunjukkan daftar notifikasi dengan badge tingkat keparahan (`INFO`, `WASPADA`, `DARURAT`).
   - Tunjukkan tombol aksi yang kontekstual dan rapi (`↗ Lihat lokasi`, `Detail`, `Akui`, `Selesaikan event`).
   - Klik tombol **"Detail"** pada salah satu notifikasi untuk melihat riwayat bukti dan log pengiriman.
   - Klik tombol **"Akui"** untuk mengonfirmasi penanganan.
   - Klik tombol **"Selesaikan event"** untuk menutup siklus insiden setelah penanganan tuntas.

### Langkah 7: Mengunduh Data Deteksi (Ekspor CSV)
1. **Aksi:**
   - Gulir ke tabel **"Log deteksi anomali panas"**.
   - Klik tombol **"Unduh CSV"**.
   - Buka berkas `firms_indonesia.csv` yang terunduh dan tunjukkan struktur data lengkap yang siap digunakan oleh analis GIS atau instansi terkait.

---

## 3. Antisipasi & Mitigasi Kendala Live Demo

| Potensi Kendala | Penyebab Umum | Tindakan Mitigasi Cepat |
|---|---|---|
| **Peta tidak memuat hotspot** | Koneksi lambat atau kuota FIRMS habis | Klik tombol "Perbarui data". Jika API lambat, server otomatis menggunakan data cache 5 menit terakhir yang sudah tersimpan. |
| **Sentinel-2 gagal di satu titik** | Lokasi tertutup awan tebal | Jelaskan bahwa sistem sengaja menolak citra berawan demi akurasi (masker SCL). Klik titik daratan lain yang lebih cerah atau pilih rentang tanggal yang lebih lebar (60 hari). |
| **Model error pada Python 3.13** | Menggunakan Python global, bukan virtual environment | Pastikan server dijalankan dengan `.\.venv\Scripts\python.exe server.py` yang memiliki XGBoost versi 2.0.3 yang sesuai dengan serialisasi model. |

