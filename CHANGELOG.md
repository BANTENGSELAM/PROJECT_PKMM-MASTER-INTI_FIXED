# Changelog — KARSA-FIRE & BARA

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0-alpha.10] - 2026-11-09

### Added
- **FINALIZATION-03 Release Freeze & Submission Packaging:**
  - `docs/FINAL_RELEASE_CHECKLIST.md`: Audit kepatuhan komprehensif, daftar periksa keamanan, integritas kode, panduan pengemasan distribusi, dan ringkasan batasan sistem yang diketahui.
  - Root `.gitignore` yang memproteksi seluruh repository dari kebocoran secrets (`.env`), virtual environment (`.venv/`), runtime states, dan file metadata OS (`.DS_Store`).

### Changed
- **Penguncian Dependensi Reproduksibel (`project_pkmm-master/requirements.txt`):**
  - Mengunci dependensi `xgboost` ke `2.0.3` agar cocok secara biner dengan model terserialisasi `model_early_warning_sentinel2_xgb.joblib` pada instalasi lingkungan baru.
  - Membersihkan file metadata cache OS (`.DS_Store`) dari direktori kerja.

### Verified
- `python -m unittest test_app test_monitoring test_notifications test_wms -v` — 75 tests PASS.
- `node test_frontend.cjs` — ALL FRONTEND SUITE TESTS PASSED.

---

## [0.1.0-alpha.9] - 2026-11-09

### Added
- **FINALIZATION-02 UI/UX Review & Browser Verification:**
  - Skrip pengujian otomatis browser headless Chrome via Chrome DevTools Protocol (`verify_browser.cjs`).
  - Verifikasi tampilan desktop (1440 × 900) dan mobile (390 × 844) dengan penangkapan tangkapan layar visual aktual di `project_pkmm-master/screenshots/`.
  - Verifikasi eksekusi live pipeline STAC + COG Sentinel-2 & inferensi XGBoost untuk analisis manual satu titik dan pemantauan grid background.

### Changed
- **Penyempurnaan Usability Tampilan Mobile (`static/style.css`):**
  - Menambahkan visual indikator scroll horizontal (`::-webkit-scrollbar`) pada `.toolbar` peta di layar seluler.
  - Memperluas `max-width` pada teks sub-status status pill header seluler agar deskripsi waktu dan jumlah anomali termal terbaca utuh tanpa terpotong.

### Verified
- `python -m unittest test_app test_monitoring test_notifications test_wms -v` — 75 tests PASS.
- `node test_frontend.cjs` — ALL FRONTEND SUITE TESTS PASSED.
- Verifikasi browser headless Chrome: 0 unhandled exceptions, 0 console errors.

---

## [0.1.0-alpha.8] - 2026-11-09

### Added
- **Dokumentasi Lengkap Finalisasi (Bahasa Indonesia):**
  - `docs/USER_GUIDE.md`: Panduan lengkap pengoperasian dashboard BARA, pembacaan legenda, penyaringan titik anomali panas, analisis manual XGBoost, pemantauan grid Sentinel-2, dan pengelolaan notifikasi.
  - `docs/SYSTEM_WORKFLOW.md`: Arsitektur sistem aktual dengan diagram alir Mermaid (multi-source FIRMS, reverse proxy WMS, AWS STAC COG sampling, XGBoost inference, background grid worker, dan notification/event lifecycle).
  - `docs/KNOWN_LIMITATIONS.md`: Transparansi batasan teknis dan ilmiah (anomali termal $\neq$ kebakaran terkonfirmasi, keterlambatan near real-time, celah orbital swath MODIS pada NASA GIBS, tutupan awan tropis, sampel diskrit 3x3, dan daftar fitur belum siap).
  - `docs/DEMO_GUIDE.md`: Panduan langkah-demi-langkah skenario demonstrasi langsung (*live demo script*) bagi penguji atau audiens lengkap dengan panduan mitigasi kendala.
  - Memperbarui `README.md`: Panduan instalasi, konfigurasi `.env`, menjalankan aplikasi, pengujian, dan tautan dokumentasi.

### Changed
- **Pembersihan UI & Metrik Operasional (`static/index.html` & `static/style.css`):**
  - Menghilangkan kartu placeholder "Laporan Masyarakat" yang belum diimplementasikan.
  - Menyesuaikan tata letak grid indikator utama `.stats` menjadi 3 kolom seimbang (`repeat(3, 1fr)`) dengan responsivitas mobile terjaga.
- **Peningkatan Robustness Backend (`server.py`):**
  - Membersihkan logika pembacaan `.env` dari ekspresi ternary sebaris menjadi blok kondisional standar yang aman dari urutan evaluasi.

### Verified
- `python -m unittest test_app test_monitoring test_notifications test_wms -v` — 75 tests PASS.
- `node test_frontend.cjs` — ALL FRONTEND SUITE TESTS PASSED.

---

## [0.1.0-alpha.7] - 2026-11-09

### Added
- **MAP-06 Multi-Satellite FIRMS Integration:**
  - `firms_sources.py`: official source definitions and per-source CSV parsers for `VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `VIIRS_NOAA21_NRT`, and `MODIS_NRT`.
  - `FIRMS_SOURCES` environment variable (comma-separated) to override the default four-source set; invalid IDs are rejected.
  - `/api/hotspots` now aggregates all configured NRT sources and returns per-source reports (`status`, `count`, `total_rows`, `skipped_invalid`, `skipped_outside`, `error`), `requested_source_count`, `successful_source_count`, `failed_source_count`, `duplicates_removed`, and `status` (`ok`/`empty`/`partial`).
  - Optional NASA GIBS `VIIRS_NOAA20_CorrectedReflectance_TrueColor` basemap (JPEG, `GoogleMapsCompatible_Level9`, zoom 0–9) alongside OpenStreetMap and MODIS Terra, with independent date fallback and layer cleanup.
  - Source-aware map markers, popups, hotspot table, and CSV export; source legend and distinct colors per instrument/satellite.
  - Tests for parsing, aggregation, partial/empty/complete failure, metadata preservation, deduplication, frontend rendering, basemap switching, and dependency reproducibility.

### Changed
- Hotspot points now preserve `source`, `source_label`, `satellite`, `instrument`, `acquired_at`, `confidence`, `confidence_raw`, and `frp` (missing FRP is `null`, not `0`).
- MODIS numeric confidence is normalized to `l`/`n`/`h` while retaining the original value in `confidence_raw`; VIIRS letter confidence is preserved.
- Deduplication matches on `(source, satellite, instrument, acquisition date/time, lat/lon to 4 dp)` and never merges detections across different sources.
- A successful-but-empty retrieval returns HTTP `200` with `status: "empty"` and an explicit warning; complete source failure returns HTTP `502` with `status: "error"` and per-source reports. Missing data is never treated as evidence of safety.

### Verified
- `python -m unittest test_app test_monitoring test_notifications test_wms -v` — 75 tests PASS.
- `node test_frontend.cjs` — all suites PASS (including source marker, refresh idempotency, and VIIRS basemap tests).
- Live `/api/hotspots?days=1`: HTTP 200, `status="ok"`, 1,924 in-boundary points, 0 duplicates; per-source counts VIIRS S-NPP 0 (empty), NOAA-20 787, NOAA-21 1,075, MODIS 62; 0 source failures.
- NASA GIBS WMTS capabilities and real Indonesian tiles verified for VIIRS NOAA-20 (JPEG, zoom 0–9); coverage is swath/date-dependent and not complete.
- Browser automation (headless Chrome via CDP): 27/27 checks passed — 1,924 markers rendered, source metadata in popups, VIIRS tiles HTTP 200/JPEG, refresh idempotency, clean basemap switching, no console errors.
- Clean temporary virtual environment installed `requirements.txt` successfully (Python 3.14.4, Rasterio 1.5.2, XGBoost 3.4.1); app import and live Sentinel-2 extraction succeeded.

---

## [0.1.0-alpha.6] - 2026-11-08

### Fixed
- **NASA FIRMS WMS Proxy (`firms_wms.py`):**
  - Added forwarded parameters `SERVICE` and `REQUEST`, and ensured default `VERSION=1.1.1` in `_FORWARD_PARAMS`. Upstream NASA MapServer strictly requires these parameters for WMS `GetMap` requests; omitting them caused HTTP 400 Bad Request responses.
  - Verified all 8 FIRMS WMS layers live (`fires_viirs_24`, `fires_viirs_48`, `fires_viirs_72`, `fires_viirs_7`, `fires_modis_24`, `fires_modis_48`, `fires_modis_72`, `fires_modis_7`) returning valid HTTP 200 PNG images without exposing credentials.
- **Monitoring Grid Sentinel-2 Inference (`server.py` & `.venv`):**
  - Diagnosed 9/9 grid point inspection failures: `rasterio` was missing from `.venv`, triggering `AttributeError: 'NoneType' object has no attribute 'origin'` at `server.py:159`.
  - Installed `rasterio==1.5.2` in `.venv` and guarded `spec and spec.origin` and `proj_data.exists()`.
  - Verified live AWS STAC query and COG remote sampling: points successfully extract all 10 Sentinel-2 features and execute XGBoost model inference.
- **NASA GIBS Tile Fallback (`static/app.js`):**
  - Corrected `tryGibsFallbackDate()` so it steps back to prior days (`D-1`, `D-2`, etc.) when the current UTC date has not finished processing or has tile errors.
  - Documented empirical cause of equatorial diagonal black swathes in MODIS Terra imagery (sun-synchronous orbit swath gaps).

### Verified
- `.\.venv\Scripts\python.exe -m unittest test_app test_monitoring test_notifications test_wms -v` — 58 tests PASS.
- `node test_frontend.cjs` — all suites PASS.
- Live service verification: NASA GIBS WMTS, NASA FIRMS status API (key accepted, 5000 transaction limit), FIRMS CSV hotspot endpoint (HTTP 200), FIRMS WMS GetMap endpoint (HTTP 200 PNG for all 8 layers), and Element84 Earth Search Sentinel-2 STAC.

---

## [0.1.0-alpha.5] - 2026-11-07

### Added
- **Notification lifecycle completion:**
  - `POST /api/events/<id>/resolve` records `resolved_by`, `resolved_at`, and an optional `resolution_note` without altering notification read state.
  - Notification status accepts `RESOLVED`; the dashboard now supports marking notifications back to `UNREAD`.
  - Notification detail displays resolution metadata.
- **Unlimited retention option:** `NOTIFICATION_MAX_RECORDS=0` and `NOTIFICATION_MAX_EVENTS=0` retain history without pruning.
- **Tests:** resolve workflow, token protection for resolve, UNREAD round-trip, RESOLVED notification status, and zero-limit retention.

### Security
- `VERIFY_TOKEN` now guards both `POST /api/events/<id>/verify` and `POST /api/events/<id>/resolve`.

### Verified
- `./.venv/bin/python -m unittest test_app.py test_monitoring.py test_notifications.py` — 39 tests PASS.
- `node test_frontend.cjs` — all suites PASS (including UNREAD and resolve actions).

---

## [0.1.0-alpha.4] - 2026-11-07

### Added
- **Notification System (N1–N7, MVP in-app):**
  - `notifications.py`: persistent JSON store with atomic writes, event identity/deduplication, severity rules, delivery log, bounded FIRMS background worker.
  - Severity levels `INFO`, `WASPADA`, `DARURAT`; automatic engine is capped at `WASPADA` so XGBoost Class 1 and single FIRMS hotspots can never self-declare an emergency.
  - Authorized `POST /api/events/<id>/verify` escalation to `DARURAT`, optionally protected by `VERIFY_TOKEN`.
  - Notification APIs: list/filter, summary, detail, read, read-all, status, events, and verification.
  - Notification Center drawer in the dashboard with unread badge, severity/status filters, read/acknowledge/dismiss actions, and map deep links.
  - `test_notifications.py` plus extended `test_frontend.cjs` coverage.
- **Configuration:** `WASPADA_MIN_SCORE`, `NOTIFICATION_FIRMS_INTERVAL`, `NOTIFICATION_MAX_RECORDS`, `NOTIFICATION_MAX_EVENTS`, `VERIFY_TOKEN` documented in `.env.example`.
- **Documentation:** Notification endpoint contract in `docs/current/API_SPEC.md`, notification schemas in `docs/DATA_DICTIONARY.md`, and operational notes.

### Changed
- `monitoring.py` now exposes optional `on_update`/`on_cycle` hooks; hook failures are isolated and never stop the monitoring loop.
- FIRMS cache access is serialized with a lock so background polling and request handlers cannot fetch concurrently.
- Active documentation now consistently names the deployed XGBoost model instead of CatBoost.

### Verified
- `./.venv/bin/python -m unittest test_app.py test_monitoring.py test_notifications.py` — 35 tests PASS.
- `node test_frontend.cjs` — all suites PASS (including notification escaping, filtering, and read/acknowledge actions).

---

## [0.1.0-alpha.3] - 2026-11-07

### Fixed
- **macOS Local Run (`project_pkmm-master/`):**
  - Documented and applied the OpenMP workaround for XGBoost: the `libomp.dylib` bundled with scikit-learn is copied into `xgboost/lib/`, with `@loader_path` added via `install_name_tool`. This removes the `xgboost._c_api.XGBoostError` crash on macOS without Homebrew.
- **Environment Configuration:**
  - Added `.env.example`; the active `.env` is now present locally and remains Git-ignored.

### Changed
- **Run Instructions:** `README.md` and `PETUNJUK.md` now describe the macOS virtual-environment workflow (`.venv/bin/python server.py`) and warn against opening `static/index.html` directly.

### Verified
- `python -m unittest test_app test_monitoring` — 16 tests PASS.
- `node test_frontend.cjs` — all frontend suites PASS.
- Live smoke test: `GET /`, `/api/status` (`firms_configured: true`), `/api/boundary`, `/api/hotspots` return HTTP 200.

---

## [0.1.0-alpha.2] - 2026-11-05

### Security & Bug Fixes (UI/UX Stage 1: P0 Criticals)
- **Frontend DOM Protection (`static/app.js`):**
  - Sanitized dynamic string injection on monitor headline and status messages via `escapeHTML()` to eliminate XSS surface.
- **Resource Optimization (`static/app.js`):**
  - Added `document.hidden` guards to background monitor polling (10s) and priority ordering polling (60s) to prevent tab background resource waste and API flooding.
- **Data Integrity & User Communication (`static/app.js`, `static/index.html`):**
  - Added `#tableNotice` banner communicating the 300-row limit on the active hotspot detection table with guidance to download CSV for full datasets.
- **Error State Styling (`static/style.css`, `static/app.js`):**
  - Added `.status-error` visual alert treatment for FIRMS, Sentinel STAC, and background monitor connection failures.

## [0.1.0-alpha.1] - 2026-11-05

### Added
- **Baseline Prototype Documentation (`docs/current/`):**
  - Added `docs/current/SYSTEM_MANUAL.md`: Preserved complete operational manual from `PETUNJUK.md` with English technical executive summary.
  - Added `docs/current/API_SPEC.md`: Formally documented live Flask REST endpoints (`/api/status`, `/api/boundary`, `/api/hotspots`, `/api/predict`, `/api/monitor`, `/api/priorities`).
  - Added `docs/current/ML_MODEL_CONTRACT.md`: Documented CatBoost 10-feature schema, SCL cloud-mask filtering rules, and reflectance scaling factors.
- **Architectural Decision Record (ADR-008):**
  - Formally recorded adoption of existing Sentinel-2 / CatBoost prototype in `project_pkmm-master/` as the functional baseline for KARSA-FIRE.
- **Agent Governance & Customizations (`.agents/`):**
  - Established persistent rules in `.agents/rules/` (`01-empirical-integrity.md`, `02-codebase-boundaries.md`, `03-geospatial-standards.md`).
  - Established reusable skills in `.agents/skills/` (`karsa-backend`, `karsa-geo`, `karsa-ml`).
- **Target Enterprise Specifications (`docs/future/`):**
  - Partitioned future scaling specs into `docs/future/` (`PRD_TARGET.md`, `ARCHITECTURE_TARGET.md`, `API_SPEC_TARGET.md`, `ML_SPEC_TARGET.md`, `UX_SPEC_TARGET.md`).

### Changed
- **Unified Root Instructions (`AGENTS.md`):**
  - Refactored root agent instructions to reflect the active prototype baseline, eliminating false greenfield workspace assumptions and broken `KarsaCipta` paths.
- **Project Index & Ledger (`README.md` & `docs/PROJECT_STATE.md`):**
  - Synchronized documentation indices and fact sheets with verified empirical code in `project_pkmm-master/`.
- **Data Dictionary (`docs/DATA_DICTIONARY.md`):**
  - Added Sentinel-2 L2A multispectral bands and SCL quality flags with explicit `IMPLEMENTED` vs. `PLANNED` status indicators.
- **Roadmap (`docs/ROADMAP.md`):**
  - Updated Phase 0 status to reflect completed baseline consolidation and verification gates.

---

## [0.1.0-alpha.0] - 2026-10-26

### Added
- Initial specifications for enterprise target architecture (PRD, Architecture, Data Dictionary, API Spec, ML Spec, UX Spec, Roadmap, ADR-001–007).
