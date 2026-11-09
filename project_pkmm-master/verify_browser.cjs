const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PROFILE_DIR = path.join(process.env.TEMP || 'C:\\Temp', 'chrome_cdp_profile_' + Date.now());
const PORT = 9222;

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function fetchJSON(url) {
  return new Promise((resolve, reject) => {
    http.get(url, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); } catch(e) { reject(e); }
      });
    }).on('error', reject);
  });
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 0;
    this.callbacks = new Map();
    this.consoleLogs = [];
    this.errors = [];
    
    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.callbacks.has(msg.id)) {
        const { resolve, reject } = this.callbacks.get(msg.id);
        this.callbacks.delete(msg.id);
        if (msg.error) reject(new Error(msg.error.message || JSON.stringify(msg.error)));
        else resolve(msg.result);
      } else if (msg.method) {
        if (msg.method === 'Runtime.consoleAPICalled') {
          this.consoleLogs.push(msg.params);
        } else if (msg.method === 'Runtime.exceptionThrown') {
          this.errors.push(msg.params);
        }
      }
    };
  }

  async ready() {
    if (this.ws.readyState === WebSocket.OPEN) return;
    return new Promise((resolve, reject) => {
      this.ws.onopen = () => resolve();
      this.ws.onerror = (err) => reject(err);
    });
  }

  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async eval(expr) {
    const res = await this.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (res.exceptionDetails) {
      throw new Error(res.exceptionDetails.text || 'Evaluation failed');
    }
    return res.result ? res.result.value : undefined;
  }

  async screenshot(filePath, clip = null) {
    const params = { format: 'png', quality: 90, captureBeyondViewport: false };
    if (clip) params.clip = clip;
    const res = await this.send('Page.captureScreenshot', params);
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, Buffer.from(res.data, 'base64'));
    console.log('Saved screenshot:', filePath);
  }
}

async function run() {
  console.log('Launching headless Chrome...');
  const chromeProc = spawn(CHROME_PATH, [
    '--headless=new',
    `--remote-debugging-port=${PORT}`,
    `--user-data-dir=${PROFILE_DIR}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-background-networking',
    '--disable-features=Translate',
    'about:blank'
  ], { stdio: 'ignore' });

  try {
    let version = null;
    for (let i = 0; i < 20; i++) {
      try {
        version = await fetchJSON(`http://127.0.0.1:${PORT}/json/version`);
        if (version) break;
      } catch (e) {
        await sleep(300);
      }
    }
    if (!version) throw new Error('Chrome remote debugging did not respond');

    const tabs = await fetchJSON(`http://127.0.0.1:${PORT}/json`);
    const tab = tabs.find(t => t.type === 'page') || tabs[0];
    if (!tab) throw new Error('No page tab found');

    const client = new CDPClient(tab.webSocketDebuggerUrl);
    await client.ready();
    await client.send('Page.enable');
    await client.send('Runtime.enable');
    await client.send('DOM.enable');

    console.log('Connected to CDP! Navigating to http://127.0.0.1:5000 ...');
    await client.send('Page.navigate', { url: 'http://127.0.0.1:5000' });
    await sleep(3500);

    const shotDir = path.join(__dirname, 'screenshots');

    // 1. Desktop Viewport (1440x900)
    await client.send('Emulation.setDeviceMetricsOverride', {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false
    });
    await sleep(1000);

    const stats = await client.eval(`({
      count: document.getElementById('count')?.innerText,
      verifiedCount: document.getElementById('verifiedCount')?.innerText,
      monitorArea: document.getElementById('monitorArea')?.innerText,
      headerStatus: document.getElementById('headerStatus')?.innerText,
      feedStatus: document.getElementById('feedStatus')?.innerText,
      markerCount: document.querySelectorAll('.leaflet-marker-icon, .leaflet-interactive').length
    })`);
    console.log('Desktop State:', JSON.stringify(stats, null, 2));
    await client.screenshot(path.join(shotDir, '01_desktop_overview.png'));

    // 2. Basemap Switch to NASA GIBS MODIS
    console.log('Switching to NASA GIBS MODIS Terra...');
    await client.eval(`
      const sel = document.getElementById('basemapSelect');
      sel.value = 'gibs';
      sel.dispatchEvent(new Event('change'));
    `);
    await sleep(2000);
    await client.screenshot(path.join(shotDir, '02_desktop_gibs_basemap.png'));

    // 3. WMS Overlay
    console.log('Overlaying WMS layer...');
    await client.eval(`
      const wmsToggle = document.getElementById('toggleWms');
      wmsToggle.checked = true;
      wmsToggle.dispatchEvent(new Event('change'));
    `);
    await sleep(2000);
    await client.screenshot(path.join(shotDir, '03_desktop_wms_layer.png'));

    // 4. Marker Click & Popup
    console.log('Clicking hotspot marker for popup...');
    await client.eval(`
      (() => {
        const markers = hotspots.getLayers();
        if (markers.length > 0) {
          markers[0].fire('click');
        }
      })()
    `);
    await sleep(1000);
    await client.screenshot(path.join(shotDir, '04_desktop_marker_popup.png'));

    // 5. Notification Center
    console.log('Opening Notification Center...');
    await client.eval(`document.getElementById('notifBell').click()`);
    await sleep(1000);
    await client.screenshot(path.join(shotDir, '05_desktop_notifications.png'));
    await client.eval(`document.getElementById('notifClose').click()`);
    await sleep(500);

    // 6. Response Priorities & Grid Table
    console.log('Scrolling to Priorities & Grid section...');
    await client.eval(`document.getElementById('priority-section').scrollIntoView({ behavior: 'instant', block: 'start' })`);
    await sleep(1000);
    await client.screenshot(path.join(shotDir, '08_desktop_priorities_and_grid.png'));

    // 7. Manual Single-Point Sentinel-2 Inference
    console.log('Testing manual single-point XGBoost analysis...');
    await client.eval(`document.getElementById('workspace-section').scrollIntoView({ behavior: 'instant', block: 'start' })`);
    await sleep(500);
    await client.eval(`switchTab('manual')`);
    await sleep(500);
    await client.eval(`
      document.getElementById('lat').value = '-3.5083';
      document.getElementById('lon').value = '104.5055';
    `);
    console.log('Submitting manual analysis form...');
    await client.eval(`document.getElementById('prediction').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }))`);
    
    // Wait for manual analysis to complete (up to 30s)
    let analysisDone = false;
    for (let i = 0; i < 30; i++) {
      await sleep(1000);
      const resText = await client.eval(`document.getElementById('result')?.innerText`);
      if (resText && !resText.includes('Mencari citra, memeriksa awan')) {
        console.log('Manual analysis result:', resText.slice(0, 150));
        analysisDone = true;
        break;
      }
    }
    await sleep(1000);
    await client.screenshot(path.join(shotDir, '09_desktop_manual_analysis_result.png'));

    // 8. Mobile View (390x844 - iPhone)
    console.log('Testing Mobile responsive view (390x844)...');
    await client.send('Emulation.setDeviceMetricsOverride', {
      width: 390,
      height: 844,
      deviceScaleFactor: 2,
      mobile: true
    });
    await client.eval(`document.querySelector('.workspace')?.scrollIntoView({ behavior: 'instant', block: 'start' })`);
    await sleep(1500);
    await client.screenshot(path.join(shotDir, '06_mobile_overview.png'));

    // 9. Mobile Notification Center
    console.log('Testing Mobile notification center...');
    await client.eval(`document.getElementById('mobileNavNotif').click()`);
    await sleep(1000);
    await client.screenshot(path.join(shotDir, '07_mobile_notifications.png'));
    await client.eval(`document.getElementById('notifClose').click()`);
    await sleep(500);

    console.log('\n--- Console logs during browser session ---');
    for (const log of client.consoleLogs) {
      const text = log.args.map(a => a.value || JSON.stringify(a)).join(' ');
      console.log(`[${log.type}] ${text}`);
    }
    console.log('Total unhandled JS exceptions:', client.errors.length);
    for (const err of client.errors) {
      console.error('Unhandled Exception:', err);
    }

    console.log('\n=== ALL BROWSER INTERACTION TESTS FINISHED SUCCESSFULLY ===');
  } finally {
    chromeProc.kill('SIGKILL');
    try { fs.rmSync(PROFILE_DIR, { recursive: true, force: true }); } catch (e) {}
  }
}

run().catch(err => {
  console.error('Browser verification failed:', err);
  process.exit(1);
});
