# Arsitektur & Alur Kerja Sistem (System Workflow)
## BARA / KARSA-FIRE — Indonesia Fire Watch

Dokumen ini menjelaskan arsitektur aktual, topologi komponen, dan alur pergerakan data pada aplikasi **BARA / KARSA-FIRE** yang berada di dalam folder `project_pkmm-master/`.

---

## 1. Topologi Arsitektur Aktual

Sistem dibangun dengan arsitektur *monolitik modular berbasis layanan mikro data*, menghubungkan antarmuka web interaktif dengan beberapa penyedia data geospatial publik global.

```mermaid
flowchart TD
    subgraph Klien["Frontend (Web Browser)"]
        UI["Antarmuka Pengguna (HTML5 / Vanilla CSS)"]
        LeafletMap["Leaflet Map Engine (v1.9.4)"]
        AppJS["Logika Aplikasi & Polling (app.js)"]
    end

    subgraph Server["Backend Flask (server.py)"]
        FlaskCore["Flask Core App (Port 5000)"]
        WmsProxy["WMS Proxy Blueprint (firms_wms.py)"]
        MonitorWorker["Monitoring Engine & Thread (monitoring.py)"]
        NotifEngine["Notification & Event Engine (notifications.py)"]
        FirmsParser["Multi-Source Parser (firms_sources.py)"]
        XGBoostInference["XGBoost Engine (10 Fitur Spektral)"]
    end

    subgraph Penyimpanan["Persistensi Lokal"]
        GeoJSON["indonesia.geojson (Batas Daratan)"]
        ModelJoblib["model_early_warning_sentinel2_xgb.joblib"]
        MonitorState["monitor_state.json"]
        NotifState["notification_state.json"]
        EnvConfig[".env (Konfigurasi & MAP_KEY)"]
    end

    subgraph Eksternal["Layanan Geospatial Publik"]
        NASA_FIRMS["NASA FIRMS API (CSV Hotspots)"]
        NASA_WMS["NASA FIRMS WMS (Tile Overlay)"]
        NASA_GIBS["NASA GIBS WMTS (MODIS / VIIRS Basemap)"]
        AWS_STAC["AWS Earth Search STAC (Sentinel-2 L2A COG)"]
        OSM["OpenStreetMap Tile Server"]
    end

    UI --> AppJS
    LeafletMap --> AppJS
    AppJS <--> FlaskCore
    AppJS <--> WmsProxy
    LeafletMap --> NASA_GIBS
    LeafletMap --> OSM

    WmsProxy --> NASA_WMS
    FlaskCore --> FirmsParser
    FirmsParser --> NASA_FIRMS
    FlaskCore --> XGBoostInference
    XGBoostInference --> AWS_STAC
    FlaskCore --> MonitorWorker
    MonitorWorker --> XGBoostInference
    MonitorWorker --> NotifEngine
    FlaskCore --> NotifEngine

    FlaskCore --> GeoJSON
    XGBoostInference --> ModelJoblib
    MonitorWorker <--> MonitorState
    NotifEngine <--> NotifState
    FlaskCore <--> EnvConfig
```

---

## 2. Alur Pengambilan & Pengolahan Data

### A. Alur Deteksi Anomali Panas NASA FIRMS (CSV)

Pengambilan data hotspot dilakukan secara berkala dan disimpan dalam cache memori server selama 5 menit (*TTL = 300 detik*).

```mermaid
sequenceDiagram
    autonumber
    actor Pengguna
    participant Web as Frontend (app.js)
    participant Flask as Flask Server (/api/hotspots)
    participant Parser as firms_sources.py
    participant NASA as NASA FIRMS API
    participant GeoJSON as indonesia.geojson

    Pengguna->>Web: Buka dashboard / Ubah periode hari
    Web->>Flask: GET /api/hotspots?days=1
    alt Data ada di Cache (< 5 menit)
        Flask-->>Web: Kembalikan data cache
    else Cache kedaluwarsa atau baru
        Flask->>NASA: Request CSV (VIIRS SNPP, NOAA20, NOAA21, MODIS)
        NASA-->>Flask: Tanggapan CSV mentah
        Flask->>Parser: Parsing multi-source & normalisasi keyakinan
        Parser->>GeoJSON: Uji koordinat titik daratan Indonesia (Ray casting)
        Parser-->>Flask: Titik unik dalam daratan Indonesia
        Flask-->>Web: JSON payload (points, metadata, status)
    end
    Web->>Pengguna: Tampilkan marker di peta dan tabel log deteksi
```

### B. Alur WMS Proxy NASA FIRMS (Keamanan Kredensial)

Untuk melindungi kredensial `FIRMS_MAP_KEY` agar tidak terlihat oleh publik di peramban pengguna (*network inspector*), sistem menyediakan proxy terbalik (*reverse proxy*):

1. Frontend memanggil endpoint internal:  
   `/api/firms/wms?SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_viirs_24&BBOX=...`
2. `firms_wms.py` memvalidasi nama layer ke dalam daftar putih (*whitelist* 8 layer resmi).
3. Backend menyisipkan `FIRMS_MAP_KEY` ke dalam path upstream NASA:  
   `https://firms.modaps.eosdis.nasa.gov/mapserver/wms/fires/{MAP_KEY}/`
4. Backend mengambil citra PNG dari NASA dan mengalirkannya ke Leaflet tanpa membocorkan key atau header sensitif.

---

## 3. Alur Analisis Sentinel-2 & XGBoost

Inferensi kerawanan vegetasi dilakukan langsung pada kanal reflektansi spektral permukaan bumi:

```mermaid
sequenceDiagram
    autonumber
    participant Klien as Pengguna / Worker Grid
    participant Backend as Flask Engine (server.py)
    participant STAC as AWS Earth Search STAC
    participant S2 as AWS S3 (Sentinel-2 COG)
    participant ML as XGBoost Model

    Klien->>Backend: Request analisis (lat, lon, start_date, end_date)
    Backend->>STAC: Cari adegan Sentinel-2 L2A (tutupan awan < 40%)
    STAC-->>Backend: Daftar adegan terurut waktu terbaru
    loop Hingga 5 adegan terbaru
        Backend->>S2: Baca piksel SCL (Scene Classification Layer) via Rasterio
        alt SCL Awan / Air / Bayangan Awan
            Backend->>Backend: Tolak adegan (coba adegan berikutnya)
        else SCL Bebas Awan (Vegetasi / Tanah)
            Backend->>S2: Unduh piksel kanal B2, B3, B4, B8, B11, B12
            Backend->>Backend: Hitung NDVI & NDWI (Skala reflektansi ×10000)
            Backend->>ML: Prediksi 10 fitur spektral + koordinat
            ML-->>Backend: Kelas (0 atau 1) & Probabilitas
        end
    end
    Backend-->>Klien: Kembalikan hasil inferensi & metadata citra
```

---

## 4. Alur Pemantauan Grid Otomatis (Background Worker)

Pemantauan grid otomatis berjalan pada thread terpisah (*background worker thread*) di server:

1. **Konfigurasi:** Pengguna memilih area (2 sudut diagonal) di peta dan menentukan interval waktu (30, 60, atau 180 menit).
2. **Generasi Titik:** Titik-titik sampel 3 × 3 dibuat di dalam bounding box dan difilter hanya yang berada di daratan Indonesia.
3. **Siklus Eksekusi:**
   - Worker mengambil maksimal 5 titik per siklus secara *round-robin*.
   - Setiap titik diproses satu per satu melalui pipeline STAC + Rasterio + XGBoost.
   - Hasil disimpan secara atomik ke dalam berkas `monitor_state.json`.
4. **Pemicu Notifikasi:**
   - Jika suatu titik terdeteksi sebagai **Kelas 1 (berpotensi terbakar)**, worker memicu sinyal ke `NotificationEngine`.
   - Sebuah notifikasi berstatus `WASPADA` otomatis dibuat dan dicatat dalam riwayat event.
5. **Daya Tahan Sistem:**
   - Jika server mati atau direstart, status terakhir dibaca kembali dari `monitor_state.json`.
   - Titik yang sebelumnya terhenti pada status `running` direset kembali ke `pending` agar tidak ada sampel yang terabaikan.

---

## 5. Alur Siklus Hidup Notifikasi & Event

Pusat notifikasi menerapkan tata kelola insiden yang ketat demi menjaga integritas data:

```mermaid
stateDiagram-v2
    [*] --> INFO: Siklus pemantauan selesai / FIRMS unavailable
    [*] --> WASPADA: Hotspot baru (FIRMS) / Potensi terdeteksi (XGBoost)
    
    WASPADA --> UNREAD: Notifikasi baru diterbitkan
    UNREAD --> READ: Pengguna melihat / membuka notifikasi
    UNREAD --> ACKNOWLEDGED: Petugas mengakui penerimaan peringatan
    READ --> ACKNOWLEDGED: Petugas mengakui penerimaan peringatan

    state EventStatus {
        [*] --> OPEN: Anomali panas / potensi aktif
        OPEN --> VERIFIED: Verifikasi petugas lapangan
        VERIFIED --> RESOLVED: Penanganan selesai di lapangan
    }

    WASPADA --> DARURAT: Petugas memverifikasi insiden darat
    DARURAT --> RESOLVED: Penanganan lapangan tuntas
    WASPADA --> DISMISSED: Deteksi salah / flare industri
```

> [!NOTE]
> **Aturan Khusus DARURAT:**  
> Sistem otomatis tidak diizinkan menciptakan status `DARURAT`. Status `DARURAT` hanya dapat diaktifkan oleh tindakan manusia (petugas) melalui antarmuka resmi dengan memasukkan identitas verifikator.

