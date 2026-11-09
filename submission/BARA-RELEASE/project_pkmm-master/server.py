from pathlib import Path
import os, time, math, threading
from datetime import datetime, timedelta, timezone
import joblib, pandas as pd, requests
from flask import Flask, request, jsonify, send_from_directory
from notifications import NotificationEngine, NotificationWorker
from firms_wms import firms_wms_bp
from firms_sources import (
    DEFAULT_SOURCES,
    SUPPORTED_SOURCES,
    deduplicate_hotspots,
    parse_firms_csv,
    source_label,
)

ROOT = Path(__file__).resolve().parent
env_file = ROOT / '.env'
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8-sig').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip().strip(chr(34)).strip(chr(39)))
app = Flask(__name__, static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024
app.register_blueprint(firms_wms_bp)
BUNDLE = joblib.load(ROOT / 'model_early_warning_sentinel2_xgb.joblib')
MODEL = BUNDLE['model'] if isinstance(BUNDLE, dict) else BUNDLE
FEATURES = list(BUNDLE['features']) if isinstance(BUNDLE, dict) and BUNDLE.get('features') else list(getattr(MODEL, 'feature_names_in_', getattr(MODEL, 'feature_names_', [])))
CACHE = {}
SESSION = requests.Session()
ANALYSIS_LOCK = threading.Lock()
FIRMS_LOCK = threading.Lock()


class FirmsRetrievalError(Exception):
    """Raised when every configured FIRMS source fails.

    An empty successful response is *not* an error; this exception is reserved
    for complete source failure so callers never treat missing data as safety.
    """

    def __init__(self, message, sources=None):
        super().__init__(message)
        self.sources = sources or []


def firms_source_ids():
    """Return the configured, de-duplicated FIRMS source identifiers.

    ``FIRMS_SOURCES`` is an optional comma-separated override using official
    NASA identifiers. The default queries all supported NRT products.
    """
    raw = os.getenv('FIRMS_SOURCES', '')
    if not str(raw or '').strip():
        return list(DEFAULT_SOURCES)
    requested = [part.strip().upper() for part in str(raw).split(',') if part.strip()]
    unknown = [source for source in requested if source not in SUPPORTED_SOURCES]
    if unknown:
        raise ValueError(
            'FIRMS_SOURCES memuat sumber tidak didukung: %s. Pilihan: %s.'
            % (', '.join(unknown), ', '.join(DEFAULT_SOURCES))
        )
    ordered = []
    for source in requested:
        if source not in ordered:
            ordered.append(source)
    return ordered

def _env_float(name, default):
    try:
        return float(os.getenv(name, default) or default)
    except (TypeError, ValueError):
        return float(default)

def _env_int(name, default):
    try:
        return int(os.getenv(name, default) or default)
    except (TypeError, ValueError):
        return int(default)

NOTIFIER = NotificationEngine(
    ROOT / 'notification_state.json',
    min_score=_env_float('WASPADA_MIN_SCORE', 0.5),
    max_notifications=_env_int('NOTIFICATION_MAX_RECORDS', 2000),
    max_events=_env_int('NOTIFICATION_MAX_EVENTS', 1000),
    logger=app.logger,
)

def notify_point(point):
    NOTIFIER.evaluate_monitor_point(point)

def notify_cycle(state):
    NOTIFIER.evaluate_cycle(state)

def notify_firms(result):
    try:
        NOTIFIER.evaluate_firms(result.get('points') or [])
    except Exception:
        app.logger.exception('Notification evaluation failed for FIRMS batch')

def record_monitor_info(action, message):
    try:
        NOTIFIER.record_system_info(
            'system:monitor:{}:{}'.format(action, time.time()),
            'Status pemantauan berubah',
            message,
        )
    except Exception:
        app.logger.exception('Could not store monitoring status notification')

def http(url, **kwargs):
    r = SESSION.get(url, timeout=45, **kwargs)
    r.raise_for_status()
    return r

def boundary():
    if 'boundary' not in CACHE:
        saved = ROOT / 'indonesia.geojson'
        if saved.exists():
            import json
            CACHE['boundary'] = json.loads(saved.read_text(encoding='utf-8'))
            return CACHE['boundary']
        geo = http('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson').json()
        country = next(f for f in geo['features'] if f['properties'].get('ISO3166-1-Alpha-3') == 'IDN' or f['properties'].get('name') == 'Indonesia')
        CACHE['boundary'] = country
    return CACHE['boundary']

def in_ring(x, y, ring):
    inside = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            inside = not inside
    return inside

def indonesia(lon, lat):
    geo = boundary()['geometry']
    polygons = geo['coordinates'] if geo['type'] == 'MultiPolygon' else [geo['coordinates']]
    return any(in_ring(lon, lat, p[0]) and not any(in_ring(lon, lat, hole) for hole in p[1:]) for p in polygons)

@app.errorhandler(Exception)
def error(exc):
    from werkzeug.exceptions import HTTPException
    if isinstance(exc, HTTPException):
        return jsonify(error=exc.description), exc.code
    app.logger.warning('%s: %s', type(exc).__name__, str(exc).replace(os.getenv('FIRMS_MAP_KEY') or '__NO_KEY__', '[KEY]'))
    if isinstance(exc, FirmsRetrievalError):
        return jsonify(error=str(exc), status='error', sources=exc.sources), 502
    messages = {ValueError: str(exc), requests.Timeout: 'Layanan satelit melewati batas waktu. Coba kembali.'}
    return jsonify(error=messages.get(type(exc), 'Data belum dapat diproses. Periksa koneksi dan log server.')), 400 if isinstance(exc, ValueError) else 502

@app.get('/')
def home():
    return send_from_directory(ROOT / 'static', 'index.html')

@app.get('/api/status')
def status():
    return jsonify(model=type(MODEL).__name__, features=FEATURES, classes=[str(x) for x in getattr(MODEL, 'classes_', [])], firms_configured=bool(os.getenv('FIRMS_MAP_KEY')))

@app.get('/api/boundary')
def borders():
    return jsonify(boundary())

def fetch_hotspots(days):
    with FIRMS_LOCK:
        return _fetch_hotspots(days)

def _firms_source_url(key, source, days):
    # Indonesian bounding box; neighbouring-country detections are excluded
    # after parsing by the existing land-boundary filter.
    return (
        'https://firms.modaps.eosdis.nasa.gov/api/area/csv/'
        f'{key}/{source}/94,-12,142,7/{days}'
    )


def _fetch_one_firms_source(key, source, days):
    """Fetch and parse one source without affecting any other source."""
    report = dict(
        source=source,
        label=source_label(source),
        status='error',
        count=0,
        total_rows=0,
        skipped_invalid=0,
        skipped_outside=0,
        error=None,
    )
    try:
        raw = http(_firms_source_url(key, source, days)).text
        parsed = parse_firms_csv(raw, source, indonesia)
    except requests.Timeout:
        report['error'] = 'waktu permintaan habis'
        return report, []
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else 'unknown'
        report['error'] = 'HTTP %s' % code
        return report, []
    except requests.RequestException:
        report['error'] = 'koneksi gagal'
        return report, []
    except ValueError as exc:
        # Parser messages are localised and contain no MAP_KEY or request URL.
        report['error'] = str(exc)
        return report, []
    except Exception:
        # One malformed source must never suppress the others.
        report['error'] = 'kesalahan pemrosesan sumber'
        return report, []

    points = parsed['points']
    report.update(
        status='ok' if points else 'empty',
        count=len(points),
        total_rows=parsed['total_rows'],
        skipped_invalid=parsed['skipped_invalid'],
        skipped_outside=parsed['skipped_outside'],
    )
    return report, points


def _fetch_hotspots(days):
    key = os.getenv('FIRMS_MAP_KEY', '')
    if not key:
        raise ValueError('NASA FIRMS MAP_KEY belum diisi. Ikuti PETUNJUK.md, lalu restart server.')
    if days not in (1, 2, 3):
        raise ValueError('Rentang waktu harus 1–3 hari.')
    cached = CACHE.get(('firms', days))
    if cached and time.time() - cached[0] < 300:
        return cached[1]

    sources = firms_source_ids()
    collected = []
    reports = []
    for source in sources:
        report, points = _fetch_one_firms_source(key, source, days)
        reports.append(report)
        collected.extend(points)

    successful = [report for report in reports if report['status'] in ('ok', 'empty')]
    failed = [report for report in reports if report['status'] == 'error']
    if not successful:
        raise FirmsRetrievalError(
            'Semua sumber NASA FIRMS gagal diperbarui. Data tidak dapat '
            'dinyatakan aman; periksa MAP_KEY, kuota API, dan koneksi.',
            reports,
        )

    points, duplicates_removed = deduplicate_hotspots(collected)
    if failed:
        status = 'partial'
        warning = (
            'Sebagian sumber FIRMS gagal diperbarui (%s). Data yang tampil '
            'tidak lengkap; kondisi ini bukan jaminan wilayah aman.'
            % ', '.join(report['label'] for report in failed)
        )
    elif points:
        status = 'ok'
        warning = None
    else:
        status = 'empty'
        warning = (
            'Tidak ada deteksi termal pada sumber yang berhasil diperiksa. '
            'Kondisi ini bukan jaminan tidak ada kebakaran di lapangan.'
        )

    labels = [report['label'] for report in successful]
    result = dict(
        points=points,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        source='NASA FIRMS • ' + ', '.join(labels),
        days=days,
        status=status,
        sources=reports,
        requested_source_count=len(sources),
        successful_source_count=len(successful),
        failed_source_count=len(failed),
        duplicates_removed=duplicates_removed,
        warning=warning,
    )
    CACHE[('firms', days)] = time.time(), result
    return result

@app.get('/api/hotspots')
def hotspots():
    result = fetch_hotspots(int(request.args.get('days', 1)))
    notify_firms(result)
    return jsonify(result)

def extract_scene(item, lon, lat):
    import importlib.util
    spec = importlib.util.find_spec('rasterio')
    # Keep GDAL isolated from the PostgreSQL/PostGIS PROJ database on this machine.
    if spec and spec.origin:
        proj_data = Path(spec.origin).parent / 'proj_data'
        if proj_data.exists():
            os.environ['PROJ_DATA'] = str(proj_data)
            os.environ['PROJ_LIB'] = os.environ['PROJ_DATA']
    import rasterio
    from rasterio.warp import transform
    aliases = {'B2':'blue', 'B3':'green', 'B4':'red', 'B8':'nir', 'B11':'swir16', 'B12':'swir22'}
    values = {}
    assets = item['assets']
    scl = assets.get('scl')
    if not scl:
        raise ValueError('Masker awan SCL tidak tersedia; prediksi dibatalkan.')
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_HTTP_TIMEOUT='35', AWS_NO_SIGN_REQUEST='YES'):
        with rasterio.open(scl['href']) as src:
            xs, ys = transform('EPSG:4326', src.crs, [lon], [lat])
            quality = int(next(src.sample([(xs[0], ys[0])]))[0])
    if quality in (0, 1, 3, 8, 9, 10, 11):
        raise ValueError('Piksel tertutup awan/bayangan atau tidak valid. Pilih tanggal atau lokasi lain.')
    for band, alias in aliases.items():
        asset = assets.get(alias) or assets.get(band)
        if not asset:
            raise ValueError(f'Kanal {band} tidak tersedia pada citra.')
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', GDAL_HTTP_TIMEOUT='35', AWS_NO_SIGN_REQUEST='YES'):
            with rasterio.open(asset['href']) as src:
                xs, ys = transform('EPSG:4326', src.crs, [lon], [lat])
                val = float(next(src.sample([(xs[0], ys[0])]))[0])
                if val == src.nodata or not math.isfinite(val) or val <= 0:
                    raise ValueError('Piksel kosong atau tidak valid. Pilih titik atau tanggal lain.')
                # Earth Search COGs store DN; retain the model training scale (0–10000).
                meta = asset.get('raster:bands', [{}])[0]
                scale, offset = meta.get('scale', 0.0001), meta.get('offset', 0)
                if item['properties'].get('earthsearch:boa_offset_applied'):
                    offset = 0
                values[band] = (val * scale + offset) * 10000
    return values

def scene(lon, lat, start, end):
    body = {'collections':['sentinel-2-l2a'], 'intersects':{'type':'Point','coordinates':[lon,lat]}, 'datetime':f'{start}T00:00:00Z/{end}T23:59:59Z', 'query':{'eo:cloud_cover':{'lt':40}}, 'limit':40, 'sortby':[{'field':'properties.datetime','direction':'desc'}]}
    r = SESSION.post('https://earth-search.aws.element84.com/v1/search', json=body, timeout=45)
    r.raise_for_status()
    items = r.json().get('features', [])
    if not items:
        raise ValueError('Tidak ada citra Sentinel-2 dengan awan scene <40% pada rentang tanggal tersebut.')
    errors = []
    for item in sorted(items, key=lambda i:i['properties']['datetime'], reverse=True)[:5]:
        try:
            cache_key = ('sentinel', lon, lat, item['id'])
            if cache_key not in CACHE:
                values = extract_scene(item, lon, lat)
                keys = [k for k in list(CACHE) if isinstance(k, tuple) and k[0] == 'sentinel']
                if len(keys) >= 128:
                    CACHE.pop(keys[0], None)
                CACHE[cache_key] = values
            return dict(CACHE[cache_key]), dict(id=item['id'], datetime=item['properties']['datetime'], cloud=item['properties'].get('eo:cloud_cover'))
        except ValueError as exc:
            errors.append(str(exc))
    raise ValueError('Lima citra terbaru tidak memiliki piksel layak: ' + errors[-1])

def predict(values):
    missing = [f for f in FEATURES if f not in values]
    if missing:
        raise ValueError('Fitur model belum dapat dihitung otomatis: ' + ', '.join(missing))
    frame = pd.DataFrame([[values[f] for f in FEATURES]], columns=FEATURES)
    label = str(MODEL.predict(frame).reshape(-1)[0])
    probabilities = MODEL.predict_proba(frame)[0].tolist() if hasattr(MODEL,'predict_proba') else None
    return dict(label=label, probabilities=probabilities, classes=[str(x) for x in getattr(MODEL,'classes_',[])], features=values)

def analyze_location(lon, lat, start, end):
    with ANALYSIS_LOCK:
        return analyze_unlocked(lon, lat, start, end)

def analyze_unlocked(lon, lat, start, end):
    values, current = scene(lon, lat, start.isoformat(), end.isoformat())
    values['longitude'], values['latitude'] = lon, lat
    values['NDVI'] = (values['B8']-values['B4'])/(values['B8']+values['B4'])
    mode = os.getenv('NDWI_FORMULA', 'green_nir')
    if mode not in ('green_nir', 'nir_swir'):
        raise ValueError('NDWI_FORMULA harus green_nir atau nir_swir.')
    a, b = (values['B3'], values['B8']) if mode == 'green_nir' else (values['B8'], values['B11'])
    values['NDWI'] = (a-b)/(a+b)
    baseline = None
    if 'dNBR' in FEATURES:
        before_end = start - timedelta(days=1)
        previous, baseline = scene(lon, lat, (before_end-timedelta(days=60)).isoformat(), before_end.isoformat())
        nbr = lambda v:(v['B8']-v['B12'])/(v['B8']+v['B12'])
        values['dNBR'] = nbr(previous)-nbr(values)
    result = predict(values)
    result.update(lon=lon, lat=lat, scene=current, baseline=baseline, warning='Kelas 1 = berpotensi terbakar; kelas 0 = aman menurut model (sesuai keterangan pemilik model). Formula NDWI dan kalibrasi skor perlu dicocokkan dengan pelatihan. Hasil bukan konfirmasi kebakaran atau jaminan keamanan.')
    return result

@app.post('/api/predict')
def prediction():
    data = request.get_json() or {}
    if not all(k in data for k in ('lon', 'lat', 'start', 'end')):
        raise ValueError('Koordinat dan tanggal wajib diisi.')
    lon, lat = float(data['lon']), float(data['lat'])
    if not math.isfinite(lon) or not math.isfinite(lat) or not indonesia(lon, lat):
        raise ValueError('Pilih titik daratan di dalam wilayah Indonesia.')
    end = datetime.strptime(data['end'], '%Y-%m-%d').date()
    start = datetime.strptime(data['start'], '%Y-%m-%d').date()
    if start > end or (end-start).days > 90 or end > datetime.now(timezone.utc).date():
        raise ValueError('Rentang tanggal harus 0–90 hari dan tidak boleh di masa depan.')
    return jsonify(analyze_location(lon, lat, start, end))

from monitoring import Monitor, priorities, historical_potential
MONITOR = Monitor(ROOT / 'monitor_state.json', analyze_location, indonesia,
                  on_update=notify_point, on_cycle=notify_cycle)

@app.get('/api/monitor')
def monitor_status():
    return jsonify(MONITOR.snapshot())

@app.post('/api/monitor')
def monitor_control():
    data = request.get_json() or {}
    if data.get('action') == 'configure':
        snapshot = MONITOR.configure(data.get('bbox'), data.get('interval_minutes', 30))
        record_monitor_info('configure', 'Area pemantauan disimpan: {}. Grid akan dianalisis bergiliran.'.format(
            ', '.join(str(v) for v in (snapshot.get('bbox') or []))))
        return jsonify(snapshot)
    action = data.get('action')
    snapshot = MONITOR.control(action)
    labels = {
        'start': 'Pemantauan otomatis dilanjutkan.',
        'pause': 'Pemantauan otomatis dijeda.',
        'run': 'Siklus pemantauan diminta berjalan sekarang.',
    }
    record_monitor_info(str(action), labels.get(action, 'Status pemantauan diperbarui.'))
    return jsonify(snapshot)

def _int_arg(name, default, minimum, maximum=None):
    raw = request.args.get(name)
    try:
        value = int(raw) if raw not in (None, '') else int(default)
    except (TypeError, ValueError):
        raise ValueError('Parameter {} harus berupa angka.'.format(name)) from None
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError('Parameter {} di luar batas.'.format(name))
    return value

def _read_arg(name):
    raw = request.args.get(name)
    if raw in (None, ''):
        return None
    value = str(raw).lower()
    if value in ('1', 'true', 'yes'):
        return True
    if value in ('0', 'false', 'no'):
        return False
    raise ValueError('Parameter read harus true atau false.')

def _notification_not_found():
    return jsonify(error='Notifikasi tidak ditemukan.'), 404

def _verification_token_ok():
    expected = os.getenv('VERIFY_TOKEN', '')
    return not expected or request.headers.get('X-Verify-Token') == expected

@app.get('/api/notifications')
def notification_list():
    data = NOTIFIER.list_notifications(
        severity=request.args.get('severity') or None,
        status=request.args.get('status') or None,
        read=_read_arg('read'),
        limit=_int_arg('limit', 50, 1, 200),
        offset=_int_arg('offset', 0, 0),
    )
    return jsonify(data)

@app.get('/api/notifications/summary')
def notification_summary():
    return jsonify(NOTIFIER.summary())

@app.post('/api/notifications/read-all')
def notification_read_all():
    return jsonify(changed=NOTIFIER.mark_all_read())

@app.get('/api/notifications/<notification_id>')
def notification_detail(notification_id):
    try:
        return jsonify(NOTIFIER.get_notification(notification_id))
    except KeyError:
        return _notification_not_found()

@app.post('/api/notifications/<notification_id>/read')
def notification_read(notification_id):
    try:
        return jsonify(NOTIFIER.mark_read(notification_id))
    except KeyError:
        return _notification_not_found()

@app.post('/api/notifications/<notification_id>/status')
def notification_status(notification_id):
    data = request.get_json() or {}
    status = str(data.get('status') or '').upper()
    if status not in ('UNREAD', 'READ', 'ACKNOWLEDGED', 'RESOLVED', 'DISMISSED'):
        raise ValueError('Status notifikasi harus UNREAD, READ, ACKNOWLEDGED, RESOLVED, atau DISMISSED.')
    try:
        return jsonify(NOTIFIER.set_status(notification_id, status))
    except KeyError:
        return _notification_not_found()

@app.get('/api/events')
def event_list():
    return jsonify(NOTIFIER.list_events(
        status=request.args.get('status') or None,
        limit=_int_arg('limit', 100, 1, 500),
        offset=_int_arg('offset', 0, 0),
    ))

@app.get('/api/events/<event_id>')
def event_detail(event_id):
    try:
        return jsonify(NOTIFIER.get_event(event_id))
    except KeyError:
        return jsonify(error='Event tidak ditemukan.'), 404

@app.post('/api/events/<event_id>/verify')
def event_verify(event_id):
    if not _verification_token_ok():
        return jsonify(error='Token verifikasi tidak valid.'), 403
    data = request.get_json() or {}
    verifier = str(data.get('verifier') or '').strip()
    try:
        return jsonify(NOTIFIER.verify_event(event_id, verifier))
    except KeyError:
        return jsonify(error='Event tidak ditemukan.'), 404

@app.post('/api/events/<event_id>/resolve')
def event_resolve(event_id):
    if not _verification_token_ok():
        return jsonify(error='Token verifikasi tidak valid.'), 403
    data = request.get_json() or {}
    actor = str(data.get('actor') or '').strip()
    note = str(data.get('note') or '').strip() or None
    try:
        return jsonify(NOTIFIER.resolve_event(event_id, actor, note))
    except KeyError:
        return jsonify(error='Event tidak ditemukan.'), 404

@app.get('/api/priorities')
def priority_list():
    warning = None
    try:
        firms = fetch_hotspots(1)
        notify_firms(firms)
    except (ValueError, requests.RequestException, FirmsRetrievalError):
        cached = CACHE.get(('firms', 1))
        firms = cached[1] if cached else dict(points=[], retrieved_at=None, status='error', warning=None)
        warning = 'FIRMS belum dapat diperbarui. Daftar ini belum lengkap; bukan berarti tidak ada kebakaran.'
    state = MONITOR.snapshot()
    rows = priorities(firms['points'], state['points'])
    return jsonify(rows=rows, historical_potential=historical_potential(state['points']), active_count=sum(r['tier']==1 for r in rows), potential_count=sum(r['tier']==2 for r in rows),
                   firms_updated_at=firms['retrieved_at'], warning=warning,
                   note='Prioritas 1: deteksi termal dalam 24 jam, belum konfirmasi lapangan. Prioritas 2: kelas 1 XGBoost dengan citra maksimal 14 hari. Sampel grid bukan peta risiko seluruh area.')

if __name__ == '__main__':
    MONITOR.start_worker()
    NotificationWorker(
        NOTIFIER, lambda: fetch_hotspots(1),
        interval_seconds=_env_int('NOTIFICATION_FIRMS_INTERVAL', 900),
        logger=app.logger,
    ).start()
    print('Buka http://127.0.0.1:5000 • fitur model:', FEATURES)
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
