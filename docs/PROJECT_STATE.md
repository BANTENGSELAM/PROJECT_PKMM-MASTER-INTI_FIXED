# Project State — KARSA-FIRE & BARA

> **Current Sprint / Phase:** Phase 0 — Foundation & Baseline Consolidation  
> **Status:** Baseline Prototype Consolidated & Enterprise Specs Partitioned  
> **Last Synchronized:** 2026-11-09

---

## 1. Executive Summary

The KARSA-FIRE and BARA project state has been consolidated. The functional prototype in `project_pkmm-master/` serves as the primary implementation source of truth (Flask, Leaflet, AWS STAC Sentinel-2 COG sampling, XGBoost inference). The future enterprise architecture specifications (Next.js, FastAPI, PostGIS, H3 hexagonal binning, ERA5-Land/CHIRPS pipelines) are partitioned under `docs/future/` to govern subsequent scaling phases without obscuring active code.

---

## 2. Fact Sheet & Current Baseline

- **Repository Root:** `c:\Users\kenyi\OneDrive\Desktop\project_pkmm-master`
- **Active Codebase:** `project_pkmm-master/`
  - Application Server: Flask 3.x (`server.py`)
  - Background Monitor: Worker thread with persistent state (`monitoring.py`, `monitor_state.json`)
  - Notification Engine: Persistent event/notification/delivery log (`notifications.py`, `notification_state.json`, Git-ignored)
  - ML Model: Pretrained XGBoost classifier (`model_early_warning_sentinel2_xgb.joblib`)
  - Geospatial Filter: Ray-casting on Indonesian MultiPolygon (`indonesia.geojson`)
  - FIRMS Multi-Source Layer: Source definitions, CSV parsers, confidence normalization, and deduplication (`firms_sources.py`)
  - Web Client: Vanilla JS + Leaflet 1.9.4 (`static/index.html`, `app.js`, `style.css`)
- **Verified Test Suites:**
  - `python -m unittest test_app test_monitoring test_notifications test_wms -v` (75 tests PASS)
  - `node test_frontend.cjs` (PASS)
  - Headless Chrome CDP browser verification: 27/27 checks PASS (markers, source metadata, VIIRS basemap, refresh idempotency, console errors)
- **Target Enterprise Architecture (Planned — Phase 1+):**
  - Frontend: Next.js 14+ (TypeScript), MapLibre GL, Deck.gl
  - Backend: FastAPI (Python 3.11+), Pydantic v2
  - Spatial Store: PostgreSQL 16 + PostGIS 3.4 + H3-pg extension
  - ML Pipeline: LightGBM / XGBoost with Purged Spatio-Temporal CV

---

## 3. Completed Actions Log

| Timestamp | Document / Milestone | Summary of Action |
|---|---|---|
| 2026-10-26 | Phase 0 Governance | Established initial specifications for target architecture (PRD, Architecture, Data Dictionary, API Spec, ML Spec, UX Spec). |
| 2026-11-05 | Codebase Audit | Executed comprehensive documentation consolidation audit comparing root specs against `project_pkmm-master/` source code. |
| 2026-11-05 | Architecture Partitioning | Established `docs/current/` (implemented prototype contracts) and `docs/future/` (planned enterprise specs). |
| 2026-11-05 | Agent Governance Update | Created `.agents/rules/` and `.agents/skills/`; updated `AGENTS.md` to establish strict codebase boundaries and empirical integrity. |
| 2026-11-05 | ADR-008 | Adopted existing Sentinel-2 / XGBoost prototype as the formal functional baseline for KARSA-FIRE. |
| 2026-11-05 | UI/UX Stage 1 (P0) | Executed P0 security and stability patches: HTML sanitization in `app.js`, background tab visibility polling guards, 300-row table limit user notice, and unified `.status-error` styling. |
| 2026-11-07 | Notification System (N1–N7) | Implemented JSON-persistent events/notifications/delivery log, FIRMS background polling, WASPADA/XGBoost rules, INFO safety messaging, authorized DARURAT verification, Notification Center UI, and tests. Automatic DARURAT remains disabled by design. |
| 2026-11-07 | Notification Lifecycle | Added event resolution with actor/note, UNREAD round-trip in the UI, `RESOLVED` notification status, unlimited-retention option (`0`), and token protection for resolve. |
| 2026-11-08 | MAP-05 NASA & Grid Diagnostics | Fixed FIRMS WMS proxy query forwarding (`SERVICE`, `REQUEST`, `VERSION`), resolved 9/9 grid point inspection failures (installed `rasterio` in `.venv` and guarded PROJ path), fixed GIBS date fallback, verified live NASA GIBS/FIRMS APIs and AWS STAC COG sampling. All 58 unit tests and all frontend tests pass. |
| 2026-11-09 | MAP-06 Multi-Satellite FIRMS | Added `firms_sources.py` parsers and multi-source `/api/hotspots` aggregation (VIIRS S-NPP, NOAA-20, NOAA-21, MODIS) with independent failure reporting, source metadata, confidence normalization, documented deduplication, and `FIRMS_SOURCES`. Added VIIRS NOAA-20 GIBS basemap, source-aware markers/table/CSV, and tests. Verified live retrieval (1,924 points, 0 duplicates, 0 source failures), GIBS VIIRS tiles, clean-venv dependency install, and 27/27 headless-browser checks. All 75 backend tests and all frontend tests pass. |
| 2026-11-09 | FINALIZATION-01 Finalisasi BARA | Audit lengkap repository, pembersihan elemen placeholder/dummy (Laporan Masyarakat), penyesuaian layout grid responsif, standardisasi parsing `.env`, pembuatan dokumentasi komprehensif Bahasa Indonesia (README.md, docs/USER_GUIDE.md, docs/SYSTEM_WORKFLOW.md, docs/KNOWN_LIMITATIONS.md, docs/DEMO_GUIDE.md). Seluruh 75 tes unit Python dan seluruh suite tes frontend lolos verifikasi. Aplikasi siap untuk demonstrasi dan evaluasi akhir. |
| 2026-11-09 | FINALIZATION-02 Browser Verification | Pengujian langsung antarmuka peramban desktop & mobile via Chrome DevTools Protocol. Perbaikan usability baris kontrol peta seluler (horizontal scroll styling) dan pelonggaran text clipping status header. Verifikasi live eksekusi analisis manual STAC + XGBoost serta pemantauan grid background. Seluruh 75 tes backend Python dan suite frontend lulus tanpa regresi. |
| 2026-11-09 | FINALIZATION-03 Release Freeze & Checklist | Audit konsistensi seluruh dokumentasi (README, USER_GUIDE, SYSTEM_WORKFLOW, KNOWN_LIMITATIONS, DEMO_GUIDE, CHANGELOG, PROJECT_STATE). Penguncian dependensi requirements.txt ke `xgboost==2.0.3`, pengaktifan root `.gitignore`, pembersihan file metadata OS (`.DS_Store`), pembuatan `docs/FINAL_RELEASE_CHECKLIST.md`. Seluruh 75 tes unit backend dan tes frontend lulus. Proyek dibekukan dan siap untuk pengumpulan. |

---

## 4. Active Blockers & Decisions Requiring User Input

1. **Pilot Study Area Selection:**
   - *Status:* Pending User Input.
   - *Options:* (A) Riau Province, (B) South Sumatra, (C) Central Kalimantan, (D) National Scope.
2. **ML Prediction Target Formalization:**
   - *Status:* Pending User Input.
   - *Options:* (A) Binary Hotspot Occurrence in Cell $c$ over $24\text{h}$, (B) High-Confidence Severe Fire ($FRP \ge 20\text{ MW}$), (C) Continuous FRP Density.
3. **Primary Forecast Horizon:**
   - *Status:* Pending User Input.
   - *Options:* (A) 24 Hours, (B) 72 Hours, (C) 7 Days.
4. **Local Development Container Strategy:**
   - *Status:* Pending User Input.
   - *Options:* Docker Compose for PostGIS & backend vs. cloud-hosted managed database.

---

## 5. Recommended Next Task

**Task:** Stakeholder alignment on Open Decisions 1–4 to initiate Phase 1 Data Ingestion & PostGIS migration, or continue expanding features directly on the active Flask/Leaflet prototype.
