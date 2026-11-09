# Panduan Pengguna BARA (BARA User Guide)
## Sistem Pemantauan Indikasi Kebakaran Hutan dan Lahan

---

## 1. Pengenalan BARA
**BARA** adalah Sistem Pemantauan Indikasi Kebakaran Hutan dan Lahan berupa dashboard interaktif berbasis web yang memadukan data pengamatan satelit cuaca/termal (NASA FIRMS & NASA GIBS) dengan citra multispektral resolusi tinggi (Copernicus Sentinel-2) serta model kecerdasan buatan (*Machine Learning* XGBoost). (Secara historis dikembangkan dalam inisiatif BARA / KARSA-FIRE).

> [!IMPORTANT]
> **Prinsip Dasar Data:**
> - Titik panas yang ditampilkan adalah **deteksi anomali panas inframerah** satelit, bukan kebakaran darat yang otomatis terkonfirmasi.
> - Data bersifat **near real-time (hampir seketika)** sesuai jadwal lintasan satelit, bukan tayangan video/CCTV langsung.
> - Hasil model Sentinel-2 menyatakan **potensi kerawanan spektral** vegetasi, bukan kepastian terjadinya api.

---

## 2. Mengenal Tampilan Dashboard

Dashboard BARA dirancang dalam satu halaman (*single-page console*) yang terdiri dari:

1. **Header Sistem:**
   - **Logo & Status Koneksi:** Menampilkan indikator sinkronisasi data (*Pemantauan Near Real-Time*).
   - **Rincian Waktu Data:** Klik pil status untuk melihat waktu pengamatan satelit, waktu data diterima, dan waktu pembaruan aplikasi.
   - **Pusat Notifikasi (Ikon Lonceng):** Menampilkan jumlah peringatan yang belum dibaca dan membuka panel notifikasi.
   - **Jam Digital:** Waktu lokal perangkat Anda.
   - **Tautan Cepat:** Navigasi cepat ke bagian Peta, Pemantauan, Prioritas, dan Log Deteksi.

2. **Ringkasan Indikator Utama (Statistik):**
   - **Deteksi Anomali Panas:** Total titik panas aktif yang terdeteksi di daratan Indonesia pada rentang hari terpilih.
   - **Insiden Terverifikasi:** Jumlah titik yang telah diverifikasi langsung oleh petugas di lapangan.
   - **Area Pemantauan:** Status grid pemantauan Sentinel-2 yang sedang aktif.

3. **Detail Teknis & Kualitas Data (Dapat Dibuka/Ditutup):**
   - Rincian jumlah titik berkeyakinan tinggi (*High Confidence*).
   - Puncak *Fire Radiative Power* (FRP dalam satuan MegaWatt / MW).
   - Kesiapan model lokal XGBoost (10 fitur spektral).
   - Rincian kontribusi masing-masing satelit (VIIRS S-NPP, NOAA-20, NOAA-21, MODIS).

---

## 3. Menggunakan Peta Interaktif

### A. Navigasi Peta
- **Geser & Perbesar:** Gunakan *drag* mouse atau *pinch* pada layar sentuh untuk menggeser. Gunakan *scroll wheel* atau tombol `+` / `-` untuk zoom.
- **Kembali ke Seluruh Indonesia:** Klik tombol **"Seluruh Indonesia"** di kanan atas peta untuk mengembalikan sudut pandang ke seluruh wilayah kepulauan Indonesia.
- **Tutup/Buka Panel:** Klik tombol **"Tutup panel"** untuk memperluas tampilan peta.

### B. Mengatur Periode & Filter Hotspot
Pada bilah kontrol (*toolbar*) di atas peta:
- **Periode Deteksi:** Pilih rentang **24 jam terakhir**, **2 hari terakhir**, atau **3 hari terakhir**.
- **Keyakinan Tinggi Saja:** Centang opsi ini untuk menyaring dan hanya menampilkan titik panas berkeyakinan tinggi (*high confidence*).
- **Perbarui Data:** Klik tombol **"Perbarui data"** untuk mengambil data terbaru dari NASA FIRMS (data otomatis disimpan dalam memori/cache selama 5 menit untuk efisiensi kuota).

### C. Mengganti Peta Dasar (Basemap) & Overlay WMS
- **Pilihan Peta Dasar:**
  1. **OpenStreetMap (OSM):** Peta jalan dan batas administrasi standar (ringan dan jelas).
  2. **NASA GIBS · MODIS Terra:** Citra satelit optik harian dunia nyata dari instrumen MODIS Terra.
  3. **NASA GIBS · VIIRS NOAA-20:** Citra satelit resolusi 250m harian dari satelit NOAA-20.
  *(Catatan: Jika citra hari ini belum dirilis oleh NASA, sistem otomatis memundurkan tanggal ke hari sebelumnya yang tersedia).*
- **Lapisan WMS FIRMS:** Centang kotak **"Lapisan WMS FIRMS"** untuk menampilkan lapisan titik panas visual langsung dari server NASA WMS, dengan pilihan rentang 24 jam, 48 jam, 72 jam, hingga 7 hari.

### D. Melihat Detail Titik
- Klik pada salah satu penanda titik di peta (baik titik FIRMS, grid Sentinel-2, maupun insiden terverifikasi).
- Kotak informasi detail akan muncul di sudut kanan bawah peta yang memuat koordinat, waktu akuisisi, sumber satelit, tingkat keyakinan, dan nilai FRP.

---

## 4. Pemantauan Grid Area (Sentinel-2)

Fitur ini memeriksa vegetasi daratan secara berkala menggunakan citra Sentinel-2 L2A bebas awan.

1. Buka tab **"Pemantauan Area"** pada panel samping kanan.
2. Klik tombol **"Pilih area di peta (2 sudut)"**.
3. Di peta, klik sudut pertama area yang ingin dipantau, lalu klik sudut kedua (diagonal).
   *(Batas maksimal ukuran area adalah 2 derajat atau sekitar 220 km).*
4. Pilih interval waktu pengecekan: **Setiap 30 menit**, **Setiap 1 jam**, atau **Setiap 3 jam**.
5. Klik **"Simpan area & mulai →"**.
6. Sistem akan membentuk grid 3 × 3 (maksimal 9 titik daratan) dan menjalankan analisis latar belakang secara bergiliran (maksimal 5 titik per siklus).
7. Tombol Operasional:
   - **Analisis sekarang:** Memajukan jadwal dan langsung menganalisis batch berikutnya tanpa menunggu jeda waktu.
   - **Jeda / Lanjutkan:** Menghentikan sementara atau melanjutkan kembali pemantauan berkala.

Hasil pemeriksaan masing-masing titik dapat dilihat pada tabel **"Status tiap titik grid"** di bawah peta.

---

## 5. Analisis Manual Satu Titik (XGBoost)

Untuk menguji tingkat kerawanan satu koordinat tertentu:
1. Buka tab **"Analisis Titik"** pada panel samping kanan.
2. Klik sembarang lokasi daratan di peta, atau ketik langsung koordinat **Lintang (Lat)** dan **Bujur (Lon)**.
3. Tentukan rentang tanggal pencarian citra Sentinel-2 (disarankan rentang 30 hari terakhir).
4. Klik **"Analisis dengan XGBoost →"**.
5. Sistem akan:
   - Mencari citra Sentinel-2 terbaru di katalog AWS STAC.
   - Memastikan piksel lokasi bebas awan (*Scene Classification Layer* valid).
   - Membaca 6 kanal spektral (B2, B3, B4, B8, B11, B12) serta menghitung NDVI dan NDWI.
   - Mengeluarkan hasil probabilitas: **Berpotensi terbakar (Kelas 1)** atau **Aman menurut model (Kelas 0)**.

---

## 6. Memahami Prioritas Respons

Bagian **Prioritas Respons** menyusun rekomendasi urutan tindakan di lapangan:
- **Prioritas 01 — Deteksi Anomali Panas 24 Jam:**
  Daftar titik anomali panas terbaru dari NASA FIRMS dalam 24 jam terakhir. Diurutkan berdasarkan tingkat keyakinan tertinggi dan nilai FRP terbesar untuk segera diverifikasi oleh tim patroli darat.
- **Prioritas 02 — Potensi Kerawanan Terbakar:**
  Daftar titik hasil analisis Sentinel-2 yang masuk kategori Kelas 1 (berpotensi terbakar) dengan citra berumur tidak lebih dari 14 hari, diurutkan dari skor probabilitas tertinggi untuk langkah pencegahan dini.
- Klik tombol **"↗ Peta"** pada salah satu baris prioritas untuk langsung mengarahkan peta ke koordinat tersebut.

---

## 7. Pusat Notifikasi & Verifikasi Petugas

Klik ikon lonceng pada bilah navigasi atas untuk membuka Pusat Notifikasi:
- **Tingkat Keparahan (Severity):**
  - `INFO`: Informasi sistem dan ringkasan siklus pemantauan berkala.
  - `WASPADA`: Deteksi anomali panas baru atau hasil analisis model Kelas 1.
  - `DARURAT`: Status darurat yang **hanya dapat ditetapkan setelah verifikasi petugas**.
- **Aksi Notifikasi:**
  - **Lihat lokasi:** Mengarahkan tampilan peta ke koordinat titik anomali terkait.
  - **Detail:** Melihat riwayat rekaman bukti dan log pengiriman.
  - **Akui:** Mengonfirmasi bahwa notifikasi telah diketahui petugas pemantau.
  - **Selesaikan event:** Menutup dan menyelesaikan insiden setelah penanganan lapangan selesai.

---

## 8. Mengunduh Data (Ekspor CSV)

Pada tabel **"Log deteksi anomali panas"** di bagian bawah halaman:
- Klik tombol **"Unduh CSV"** untuk mengekspor seluruh data deteksi anomali panas yang sedang aktif ke dalam berkas `firms_indonesia.csv`.
- Berkas CSV mencakup koordinat, waktu akuisisi UTC, tingkat keyakinan, FRP (MW), satelit, instrumen, dan penanda siang/malam.

