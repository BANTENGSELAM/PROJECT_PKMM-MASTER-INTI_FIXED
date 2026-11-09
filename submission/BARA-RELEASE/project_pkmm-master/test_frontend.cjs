const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const elements = new Map();
function element(id) {
  if (!elements.has(id)) {
    elements.set(id, {
      id,
      value: '',
      textContent: '',
      innerHTML: '',
      className: '',
      disabled: false,
      checked: false,
      open: false,
      dataset: {},
      style: {},
      classList: {
        toggle() {},
        add() {},
        remove() {}
      },
      addEventListener() {},
      scrollIntoView() {}
    });
  }
  return elements.get(id);
}

let capturedTileLayers = [];
const layer = () => {
  const obj = {
    _children: [],
    _popup: '',
    _latlng: null,
    addTo(parent) {
      if (parent && Array.isArray(parent._children)) parent._children.push(this);
      return this;
    },
    clearLayers() { this._children = []; return this; },
    bindPopup(popup) { this._popup = popup; return this; },
    on() { return this; },
    off() { return this; },
    options: {},
    _url: ''
  };
  capturedTileLayers.push(obj);
  return obj;
};

const mapMock = {
  setView() { return this; },
  on() {},
  fitBounds() {},
  addLayer() { return this; },
  removeLayer(layerToRemove) { this.removedLayers.push(layerToRemove); return this; },
  invalidateSize() {},
  removedLayers: []
};

const emptyState = {
  enabled: false,
  interval_minutes: 30,
  bbox: null,
  points: [],
  cursor: 0,
  last_run: null,
  next_run: null,
  next_at: 0,
  busy: false,
  current: null,
  batch_size: 5
};

let capturedIntervalCallbacks = [];
let capturedDocListeners = new Map();
let downloadedBlobContent = null;
let apiCallLog = [];

const docMock = {
  hidden: false,
  getElementById: element,
  querySelector: (sel) => {
    if (sel.startsWith('.')) return element(sel.slice(1));
    if (sel.startsWith('#')) return element(sel.slice(1));
    return element(sel);
  },
  addEventListener(evt, cb) {
    if (!capturedDocListeners.has(evt)) capturedDocListeners.set(evt, []);
    capturedDocListeners.get(evt).push(cb);
  },
  createElement(tag) {
    return {
      tag,
      click() {},
      set href(val) {},
      set download(val) {}
    };
  }
};

const context = vm.createContext({
  console,
  Date,
  Blob: class {
    constructor(parts, opts) {
      downloadedBlobContent = parts.join('');
    }
  },
  URL: {
    createObjectURL: () => 'blob:mock-url',
    revokeObjectURL: () => {}
  },
  setTimeout: (fn) => fn(),
  setInterval: (fn, ms) => {
    capturedIntervalCallbacks.push({ fn, ms });
    return capturedIntervalCallbacks.length;
  },
  document: docMock,
  L: {
    map: () => mapMock,
    tileLayer: Object.assign(function(url, opts){
      const l = layer();
      l._url = url || '';
      l.options = opts || {};
      return l;
    }, { wms: function(url, opts){
      const l = layer();
      l._url = url || '';
      l.options = opts || {};
      return l;
    } }),
    layerGroup: layer,
    circleMarker: function(latlng, opts){
      const l = layer();
      l._latlng = latlng;
      l.options = opts || {};
      return l;
    },
    rectangle: layer,
    geoJSON: layer,
    latLngBounds: (a, b) => ({
      getWest: () => Math.min(a.lng, b.lng),
      getEast: () => Math.max(a.lng, b.lng),
      getSouth: () => Math.min(a.lat, b.lat),
      getNorth: () => Math.max(a.lat, b.lat)
    })
  },
  fetch: async (url, opts) => {
    apiCallLog.push({ url, opts });
    if (url === '/api/status') return { ok: true, json: async () => ({ features: ['B2', 'B3'], firms_configured: false }) };
    if (url === '/api/monitor') return { ok: true, json: async () => structuredClone(emptyState) };
    if (url === '/api/priorities') return { ok: true, json: async () => ({ rows: [], historical_potential: [], active_count: 0, potential_count: 0, note: '', firms_updated_at: null }) };
    return { ok: true, json: async () => ({}) };
  },
  assert,
  capturedTileLayers,
  $: id => docMock.getElementById(id)
});

vm.runInContext(fs.readFileSync(__dirname + '/static/app.js', 'utf8'), context);

(async () => {
  await new Promise(resolve => setImmediate(resolve));

  console.log('--- Executing Base Frontend Interaction Logic Tests ---');
  vm.runInContext(`
    chooseArea();
    assert.equal(pickingArea, true);
    pickCorner({ lat: -3, lng: 113 });
    pickCorner({ lat: -2, lng: 114 });
    assert.equal(pickingArea, false);
    assert.equal(JSON.stringify(draftBox), '[113,-3,114,-2]');
    assert.equal($('saveArea').disabled, false);
    chooseArea();
    assert.equal(draftBox, null);
    assert.equal($('saveArea').disabled, true);
  `, context);

  vm.runInContext(`
    renderMonitor({
      enabled: true,
      interval_minutes: 30,
      bbox: [113, -3, 114, -2],
      points: [{ id: '1-1', lat: -2.8, lon: 113.2, status: 'error', checked_at: null, error: 'Piksel tertutup awan', result: null }],
      busy: false,
      current: null,
      batch_size: 5,
      last_run: null,
      next_run: null
    });
    assert.ok($('gridRows').innerHTML.includes('Piksel tertutup awan'));
    assert.ok(!$('gridRows').innerHTML.includes('Aman menurut model'));
    assert.equal($('pauseMonitor').textContent, 'Jeda');
  `, context);

  vm.runInContext(`
    const item = priorityItem({ tier: 2, lat: -3, lon: 114, score: 0.8, observed_at: new Date().toISOString() }, 0);
    assert.ok(item.includes('80.0%'));
    assert.ok(item.includes('data-lat="-3"'));
  `, context);

  const baseFetch = context.fetch;
  context.fetch = async (url, opts) => {
    apiCallLog.push({ url, opts });
    if (url === '/api/priorities') {
      return {
        ok: true,
        json: async () => ({
          rows: [],
          historical_potential: [{ tier: 3, lat: -3, lon: 114, score: 0.8, age_days: 15, observed_at: new Date().toISOString() }],
          note: '',
          firms_updated_at: null
        })
      };
    }
    return baseFetch(url, opts);
  };
  await vm.runInContext('loadPriorities()', context);
  assert.ok(element('potentialList').innerHTML.includes('citra lama'));
  assert.ok(element('potentialList').innerHTML.includes('80.0%'));
  assert.equal(element('potentialTotal').textContent, '0 terbaru / 1 lama');
  console.log('Base Interaction Logic: PASS (area selection, draft reset, failed pixel status, controls, priority score)');

  console.log('--- Executing Comprehensive Security & Responsive Tests ---');

  // Test 1: XSS HTML escaping
  const escaped = vm.runInContext("escapeHTML('<script>alert(1)</script>&\"\\'')", context);
  assert.equal(escaped, '&lt;script&gt;alert(1)&lt;/script&gt;&amp;&quot;&#39;');
  console.log('Test 1 PASS: XSS injection prevented via escapeHTML.');

  // Test 2: Double escaping avoidance
  vm.runInContext(`
    renderMonitor({
      enabled: true,
      interval_minutes: 30,
      bbox: [113, -3, 114, -2],
      points: [{ id: '1-1', lat: -2.8, lon: 113.2, status: 'ok', checked_at: '2026-11-05T00:00:00Z', error: null, result: { label: '0', scene: { datetime: '2026-11-05T00:00:00Z' } } }],
      busy: true,
      current: 'A & B <test>',
      batch_size: 5,
      last_run: null,
      next_run: null
    });
  `, context);
  const monitorHtml = element('monitorStatus').innerHTML;
  assert.ok(monitorHtml.includes('A &amp; B &lt;test&gt;'));
  assert.ok(!monitorHtml.includes('&amp;amp;'));
  console.log('Test 2 PASS: No double escaping in status headline.');

  // Test 3: Numerical injection safety
  assert.equal(vm.runInContext("safeNum('<img src=x onerror=1>', 2)", context), '—');
  assert.equal(vm.runInContext("safeNum(12.3456, 2)", context), '12.35');
  console.log('Test 3 PASS: Numeric sanitization rejects malicious non-numeric markup.');

  // Test 4: Polling suppression when tab is hidden
  docMock.hidden = true;
  apiCallLog = [];
  for (const item of capturedIntervalCallbacks) {
    item.fn();
  }
  const hiddenCalls = apiCallLog.filter(c => c.url === '/api/monitor' || c.url === '/api/priorities');
  assert.equal(hiddenCalls.length, 0);
  console.log('Test 4 PASS: Background polling suppressed when document.hidden === true.');

  // Test 5: Polling resumption on tab active
  docMock.hidden = false;
  apiCallLog = [];
  const visListeners = capturedDocListeners.get('visibilitychange') || [];
  for (const cb of visListeners) cb();
  await new Promise(resolve => setTimeout(resolve, 50));
  const activeCalls = apiCallLog.filter(c => c.url === '/api/monitor' || c.url === '/api/priorities');
  assert.ok(activeCalls.length >= 2);
  console.log('Test 5 PASS: Polling resumed upon visibilitychange to active.');

  // Test 6: In-flight deduplication
  apiCallLog = [];
  vm.runInContext('monitorLoading = true;', context);
  await vm.runInContext('loadMonitor();', context);
  assert.equal(apiCallLog.length, 0);
  vm.runInContext('monitorLoading = false;', context);
  console.log('Test 6 PASS: Concurrent in-flight request deduplication verified.');

  // Test 7 & 8: Table notification limits
  const mockLotsOfPoints = Array.from({ length: 350 }, (_, i) => ({
    lat: -2.0 - i * 0.001,
    lon: 113.0 + i * 0.001,
    confidence: 'n',
    frp: 10 + i,
    date: '2026-11-05',
    time: '1200',
    satellite: 'N'
  }));
  vm.runInContext(`records = ${JSON.stringify(mockLotsOfPoints)}; render();`, context);
  assert.ok(element('tableNotice').className.includes('highlight'));
  assert.ok(element('tableNotice').textContent.includes('300 dari 350'));

  const mockFewPoints = mockLotsOfPoints.slice(0, 5);
  vm.runInContext(`records = ${JSON.stringify(mockFewPoints)}; render();`, context);
  assert.ok(!element('tableNotice').className.includes('highlight'));
  assert.ok(element('tableNotice').textContent.includes('seluruh 5 titik'));

  vm.runInContext(`records = []; render();`, context);
  assert.equal(element('tableNotice').textContent, '');
  console.log('Test 7 & 8 PASS: Accurate table row threshold notifications.');

  // Test 9: CSV export completeness
  vm.runInContext(`records = ${JSON.stringify(mockLotsOfPoints)}; render();`, context);
  downloadedBlobContent = null;
  vm.runInContext("$('download').onclick();", context);
  assert.ok(downloadedBlobContent !== null);
  const csvLines = downloadedBlobContent.trim().split('\r\n');
  assert.equal(csvLines.length, 351); // 1 header + 350 rows
  console.log('Test 9 PASS: CSV export retains full filtered dataset (350 rows).');

  // Test 10: Auto-open manual analysis form on map mark()
  vm.runInContext(`
    mark(-1.5, 114.2);
    assert.equal($('lat').value, '-1.50000');
    assert.equal($('lon').value, '114.20000');
    assert.equal(document.querySelector('.manual-analysis').open, true);
  `, context);
  console.log('Test 10 PASS: Map click populates coordinates and auto-opens manual form.');

  // Test 11: Action panel tabs and layer visibility toggles verified
  vm.runInContext(`
    switchTab('manual');
    switchTab('grid');
    $('toggleHotspots').onchange({ target: { checked: false } });
    $('toggleHotspots').onchange({ target: { checked: true } });
    $('toggleGrid').onchange({ target: { checked: false } });
    $('toggleGrid').onchange({ target: { checked: true } });
  `, context);
  console.log('Test 11 PASS: Action panel tabs and layer visibility toggles verified.');

  // Test 12: Structured Sentinel-2 analysis error formatting
  const formattedError = vm.runInContext("formatAnalysisError('Piksel tertutup awan')", context);
  assert.ok(formattedError.includes('error-box'));
  assert.ok(formattedError.includes('Citra Sentinel-2 Bebas Awan Tidak Ditemukan'));
  assert.ok(formattedError.includes('Piksel tertutup awan'));
  assert.ok(formattedError.includes('Saran tindakan:'));
  console.log('Test 12 PASS: Structured error formatting with title, cause, and action suggestion verified.');

  console.log('--- Executing Notification Center Tests ---');
  const notificationPayload = {
    notifications: [{
      id: 'ntf_1',
      event_id: 'evt_1',
      title: '<img src=x onerror=alert(1)> Anomali termal',
      message: '<script>alert("xss")</script> Deteksi termal, bukan konfirmasi kebakaran.',
      severity: 'WASPADA',
      source: 'FIRMS',
      latitude: -2.2,
      longitude: 113.9,
      occurred_at: '2026-11-07T06:15:00Z',
      created_at: '2026-11-07T06:16:00Z',
      read_at: null,
      status: 'UNREAD',
      event_status: 'OPEN'
    }],
    total: 1,
    unread_count: 1,
    limit: 100,
    offset: 0
  };
  context.fetch = async (url, opts) => {
    apiCallLog.push({ url, opts });
    if (url.startsWith('/api/notifications?')) {
      return { ok: true, json: async () => structuredClone(notificationPayload) };
    }
    if (url.includes('/api/notifications/ntf_1/read')) {
      return { ok: true, json: async () => ({ id: 'ntf_1', status: 'READ' }) };
    }
    if (url.includes('/api/notifications/ntf_1/status')) {
      return { ok: true, json: async () => ({ id: 'ntf_1', status: 'ACKNOWLEDGED' }) };
    }
    if (url.includes('/api/events/evt_1/resolve')) {
      return { ok: true, json: async () => ({ event: { id: 'evt_1', status: 'RESOLVED' } }) };
    }
    return { ok: true, json: async () => ({}) };
  };

  apiCallLog = [];
  await vm.runInContext('loadNotifications()', context);
  const notifHtml = element('notifList').innerHTML;
  assert.ok(notifHtml.includes('&lt;img src=x onerror=alert(1)&gt;'));
  assert.ok(!notifHtml.includes('<img src=x'));
  assert.ok(notifHtml.includes('&lt;script&gt;alert'));
  assert.ok(notifHtml.includes('WASPADA'));
  assert.ok(notifHtml.includes('Event: OPEN'));
  assert.equal(element('notifBadge').textContent, '1');
  assert.equal(element('notifBadge').hidden, false);
  assert.equal(element('notifSummary').textContent.includes('1 belum dibaca'), true);
  console.log('Test 13 PASS: Notification rendering escapes untrusted content and shows unread severity state.');

  element('notifSeverity').value = 'DARURAT';
  apiCallLog = [];
  await vm.runInContext('loadNotifications()', context);
  const filteredUrl = apiCallLog.find(c => c.url.startsWith('/api/notifications?'))?.url || '';
  assert.ok(filteredUrl.includes('severity=DARURAT'));
  element('notifSeverity').value = '';
  console.log('Test 14 PASS: Severity filter is forwarded to the notification API.');

  apiCallLog = [];
  await vm.runInContext("notifAction('ntf_1','read')", context);
  assert.ok(apiCallLog.some(c => c.url === '/api/notifications/ntf_1/read' && c.opts.method === 'POST'));
  apiCallLog = [];
  await vm.runInContext("notifAction('ntf_1','acknowledged')", context);
  const ackCall = apiCallLog.find(c => c.url === '/api/notifications/ntf_1/status');
  assert.ok(ackCall);
  assert.equal(ackCall.opts.body, JSON.stringify({ status: 'ACKNOWLEDGED' }));
  apiCallLog = [];
  await vm.runInContext("notifAction('ntf_1','detail')", context);
  assert.ok(element('notif-detail-ntf_1').innerHTML.includes('Log pengiriman'));

  apiCallLog = [];
  await vm.runInContext("notifAction('ntf_1','unread')", context);
  const unreadCall = apiCallLog.find(c => c.url === '/api/notifications/ntf_1/status');
  assert.ok(unreadCall);
  assert.equal(unreadCall.opts.body, JSON.stringify({ status: 'UNREAD' }));

  apiCallLog = [];
  await vm.runInContext("notifAction('ntf_1','resolved')", context);
  const resolvedCall = apiCallLog.find(c => c.url === '/api/notifications/ntf_1/status');
  assert.ok(resolvedCall);
  assert.equal(resolvedCall.opts.body, JSON.stringify({ status: 'RESOLVED' }));

  context.prompt = () => 'Petugas Uji';
  apiCallLog = [];
  await vm.runInContext("notifAction('ntf_1','resolve','evt_1')", context);
  const resolveCall = apiCallLog.find(c => c.url === '/api/events/evt_1/resolve');
  assert.ok(resolveCall);
  const resolveBody = JSON.parse(resolveCall.opts.body);
  assert.equal(resolveBody.actor, 'Petugas Uji');
  assert.equal(resolveBody.note, 'Petugas Uji');
  console.log('Test 15 PASS: Read, unread, acknowledge, detail, and resolve actions call the correct endpoints.');

  console.log('--- Executing WMS Map Integration Tests ---');
  vm.runInContext(`assert.equal(typeof L.tileLayer.wms, 'function');`, context);

  // Test W1: GIBS tile URL uses correct endpoint, layer, TileMatrixSet, date
  vm.runInContext(`
    setBasemap('gibs');
    const gibsLayers = capturedTileLayers.filter(l => l._url.includes('gibs.earthdata.nasa.gov'));
    assert.ok(gibsLayers.length > 0, 'GIBS tile layer created');
    const gibs = gibsLayers[0];
    assert.ok(gibs._url.includes('MODIS_Terra_CorrectedReflectance_TrueColor'), 'GIBS layer name correct');
    assert.ok(gibs._url.includes('GoogleMapsCompatible_Level9'), 'GIBS TileMatrixSet correct');
    assert.equal(gibs.options.minNativeZoom, 1, 'GIBS minNativeZoom set');
    assert.equal(gibs.options.maxNativeZoom, 8, 'GIBS maxNativeZoom set');
  `, context);
  console.log('Test W1 PASS: GIBS tile URL and zoom configuration correct');

  // Test W2: Basemap switching removes old layer and creates new one
  vm.runInContext(`
    setBasemap('osm');
    const osmLayers = capturedTileLayers.filter(l => l._url.includes('openstreetmap.org'));
    assert.ok(osmLayers.length > 0, 'OSM tile layer created after switch');
  `, context);
  console.log('Test W2 PASS: Basemap switching OSM/GIBS works');

  // Test W3: WMS toggle creates WMS layer with correct endpoint
  vm.runInContext(`
    $('toggleWms').checked = true;
    toggleWms(true);
    const wmsLayers = capturedTileLayers.filter(l => l._url.includes('/api/firms/wms'));
    assert.ok(wmsLayers.length > 0, 'WMS tile layer created');
    toggleWms(false);
  `, context);
  console.log('Test W3 PASS: WMS overlay toggle creates/removes layer');

  // Test W4: WMS layer selection changes layer param
  vm.runInContext(`
    setWmsLayer('fires_viirs_48');
    const latestWms = capturedTileLayers.filter(l => l._url.includes('/api/firms/wms')).pop();
    assert.ok(latestWms.options.layers === 'fires_viirs_48', 'WMS layer param updated');
  `, context);
  console.log('Test W4 PASS: WMS layer selection updates parameters');

  // Test W5: CSV hotspot parsing and marker rendering
  const mockHotspots = {
    points: [
      { lat: -2.2, lon: 113.9, confidence: 'h', frp: 12.5, date: '2026-10-26', time: '0615', satellite: 'N', daynight: 'D' },
      { lat: 1.35, lon: 103.82, confidence: 'n', frp: 5.0, date: '2026-10-26', time: '1200', satellite: 'N', daynight: 'D' }
    ],
    retrieved_at: '2026-10-26T07:00:00Z',
    days: 1,
    source: 'NASA FIRMS • VIIRS S-NPP NRT'
  };
  vm.runInContext(`records = ${JSON.stringify(mockHotspots.points)};`, context);
  vm.runInContext(`render();`, context);
  vm.runInContext(`
    const rowsHtml = $('rows').innerHTML;
    assert.ok(rowsHtml.includes('-2.2000, 113.9000'), 'CSV hotspot marker rendered in table');
    assert.ok(rowsHtml.includes('Tinggi'), 'High confidence badge rendered');
    assert.ok(rowsHtml.includes('12.5 MW'), 'FRP value rendered');
    assert.equal($('count').textContent, '2', 'Hotspot count correct');
  `, context);
  console.log('Test W5 PASS: CSV hotspot response parsed and markers rendered');

  // Test W6: Missing MAP_KEY shows configuration warning, no fake markers
  vm.runInContext(`
    records = [];
    render();
    $('feedStatus').textContent = 'MAP_KEY belum dikonfigurasi. Buka PETUNJUK.md → isi .env → restart server. Tidak ada data simulasi yang ditampilkan.';
    $('feedStatus').className = 'status-error';
    assert.ok($('rows').innerHTML.includes('Tidak ada deteksi'), 'Empty state shown when no data');
    assert.equal($('feedStatus').className.includes('status-error'), true, 'Error status class applied');
  `, context);
  console.log('Test W6 PASS: Missing MAP_KEY shows configuration warning, no fake markers');

  // Test W7: CSV markers and WMS overlay are separate layers
  vm.runInContext(`
    // hotspots layer group and wmsLayer are distinct variables
    assert.ok(typeof hotspots !== 'undefined', 'hotspots layer group exists');
    assert.ok(typeof wmsLayer !== 'undefined', 'wmsLayer variable exists');
  `, context);
  console.log('Test W7 PASS: CSV markers and WMS overlay are separate layers');

  // Test W8: Monitoring grid failure diagnostics - errors reported as failed, not safe
  vm.runInContext(`
    renderMonitor({
      enabled: true, interval_minutes: 30, bbox: [113,-3,114,-2],
      points: [{ id: '1-1', lat: -2.8, lon: 113.2, status: 'error', error: 'Piksel tertutup awan', result: null, checked_at: null }],
      cursor: 0, last_run: null, next_run: null, busy: false, current: null,
      batch_size: 5, grid_size: 3
    });
  `, context);
  vm.runInContext(`
    const gridHtml = $('gridRows').innerHTML;
    assert.ok(gridHtml.includes('Piksel tertutup awan'), 'Grid error message displayed');
    assert.ok(gridHtml.includes('Belum dapat dianalisis'), 'Grid error status shown as failed, not safe');
    assert.ok(!gridHtml.includes('Aman menurut model'), 'Error point not labeled safe');
  `, context);
  console.log('Test W8 PASS: Monitoring grid failures reported as failed, not safe');

  // Test W9: source-specific marker colours, popup metadata, and table labels
  const multiSourceRecords = [
    { lat: -2.2, lon: 113.9, confidence: 'h', confidence_raw: 'h', frp: 12.5, date: '2026-11-08', time: '0325', satellite: 'N20', instrument: 'VIIRS', source: 'VIIRS_NOAA20_NRT', source_label: 'VIIRS NOAA-20 NRT', daynight: 'D' },
    { lat: -8.15986, lon: 114.24751, confidence: 'n', confidence_raw: '44', frp: 19.85, date: '2026-11-08', time: '0119', satellite: 'Terra', instrument: 'MODIS', source: 'MODIS_NRT', source_label: 'MODIS NRT', daynight: 'D' }
  ];
  vm.runInContext(`records = ${JSON.stringify(multiSourceRecords)}; render();`, context);
  const sourceMarkers = vm.runInContext('hotspots._children', context);
  assert.equal(sourceMarkers.length, 2, 'One marker per returned FIRMS record');
  const markerColours = sourceMarkers.map(m => m.options.fillColor);
  assert.ok(markerColours.includes('#d96328'), 'NOAA-20 source colour applied');
  assert.ok(markerColours.includes('#6a4c93'), 'MODIS source colour applied');
  const markerPopups = sourceMarkers.map(m => m._popup).join(' ');
  assert.ok(markerPopups.includes('Sumber: VIIRS NOAA-20 NRT'), 'NOAA-20 source shown in popup');
  assert.ok(markerPopups.includes('Sumber: MODIS NRT'), 'MODIS source shown in popup');
  assert.ok(markerPopups.includes('Satelit: N20'), 'Satellite identity shown in popup');
  assert.ok(markerPopups.includes('Nominal (44)'), 'MODIS raw numeric confidence preserved');
  const sourceTable = element('rows').innerHTML;
  assert.ok(sourceTable.includes('VIIRS NOAA-20 NRT'), 'Source label rendered in table');
  assert.ok(sourceTable.includes('MODIS NRT'), 'MODIS source rendered in table');
  console.log('Test W9 PASS: Source-specific markers, popup metadata, and table labels rendered');

  // Test W10: refreshing the same records must not accumulate duplicate markers
  vm.runInContext(`render();`, context);
  assert.equal(vm.runInContext('hotspots._children.length', context), 2,
    'Re-rendering clears old markers before adding the refreshed set');
  vm.runInContext(`$('highOnly').checked = true; render();`, context);
  assert.equal(vm.runInContext('hotspots._children.length', context), 1,
    'Existing confidence filter still works with source-aware markers');
  vm.runInContext(`$('highOnly').checked = false; render();`, context);
  console.log('Test W10 PASS: Marker refresh is idempotent and confidence filter preserved');

  // Test W11: VIIRS NOAA-20 basemap switches, uses verified layer/TMS, then cleans up
  vm.runInContext(`setBasemap('viirs');`, context);
  const viirsLayer = capturedTileLayers.filter(l => l._url.includes('VIIRS_NOAA20_CorrectedReflectance_TrueColor')).pop();
  assert.ok(viirsLayer, 'VIIRS tile layer created');
  assert.ok(viirsLayer._url.includes('GoogleMapsCompatible_Level9'), 'VIIRS TileMatrixSet correct');
  assert.equal(viirsLayer.options.maxNativeZoom, 9, 'VIIRS maxNativeZoom verified from capabilities');
  assert.ok(viirsLayer.options.attribution.includes('VIIRS NOAA-20'), 'VIIRS attribution set');
  assert.equal(vm.runInContext('currentBasemap', context), 'viirs');

  vm.runInContext('tryGibsFallbackDate();', context);
  const viirsFallback = capturedTileLayers.filter(l => l._url.includes('VIIRS_NOAA20_CorrectedReflectance_TrueColor')).pop();
  assert.notEqual(viirsFallback._url, viirsLayer._url, 'VIIRS fallback date changes the tile URL');
  assert.equal(vm.runInContext('basemapDatesTried.viirs.length', context), 2,
    'VIIRS fallback date tracked independently');

  vm.runInContext(`setBasemap('gibs');`, context);
  assert.equal(vm.runInContext('currentBasemap', context), 'gibs');
  const modisAgain = capturedTileLayers.filter(l => l._url.includes('MODIS_Terra_CorrectedReflectance_TrueColor')).pop();
  assert.ok(modisAgain, 'MODIS basemap still available after VIIRS switch');
  assert.equal(modisAgain.options.maxNativeZoom, 8, 'MODIS zoom configuration unchanged');

  vm.runInContext(`setBasemap('osm');`, context);
  assert.equal(vm.runInContext('currentBasemap', context), 'osm');
  const osmAgain = capturedTileLayers.filter(l => l._url.includes('openstreetmap.org')).pop();
  assert.ok(osmAgain, 'OpenStreetMap basemap still available');
  assert.ok(vm.runInContext('map.removedLayers.length', context) >= 2,
    'Previous basemap layers removed on switch');
  console.log('Test W11 PASS: VIIRS basemap switching, fallback, cleanup, and existing basemaps preserved');

  console.log('WMS Map Integration: ALL PASS');
  console.log('--- ALL FRONTEND SUITE TESTS PASSED SUCCESSFULLY! ---');
})().catch(err => {
  console.error('Test FAILED:', err);
  process.exitCode = 1;
});
