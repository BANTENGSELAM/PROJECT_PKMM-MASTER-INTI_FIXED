const { spawn } = require('child_process');
const http = require('http');
const fs = require('fs');
const path = require('path');

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PROFILE_DIR = path.join(process.env.TEMP || 'C:\\Temp', 'chrome_readme_profile_' + Date.now());
const PORT = 9223;

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
    console.log('Saved screenshot:', path.basename(filePath));
  }
}

async function run() {
  console.log('Launching headless Chrome for README screenshots...');
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

    const outDir = path.join(__dirname, '..', 'docs', 'images');
    fs.mkdirSync(outDir, { recursive: true });

    // 1. dashboard-overview.png (1440x900)
    console.log('1. Capturing dashboard-overview.png...');
    await client.send('Emulation.setDeviceMetricsOverride', {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false
    });
    await sleep(1000);
    await client.screenshot(path.join(outDir, 'dashboard-overview.png'));

    // 2. hotspot-map.png (Focus on map workspace with hotspot clusters)
    console.log('2. Capturing hotspot-map.png...');
    await client.eval(`document.getElementById('workspace-section').scrollIntoView({ behavior: 'instant', block: 'start' })`);
    await sleep(800);
    await client.screenshot(path.join(outDir, 'hotspot-map.png'));

    // 3. hotspot-popup.png (Click a hotspot marker to display detail panel)
    console.log('3. Capturing hotspot-popup.png...');
    await client.eval(`
      (() => {
        const markers = hotspots.getLayers();
        if (markers.length > 0) {
          markers[0].fire('click');
        }
      })()
    `);
    await sleep(1000);
    await client.screenshot(path.join(outDir, 'hotspot-popup.png'));

    // 4. basemap-layers.png (Switch to NASA GIBS MODIS Terra + overlay WMS)
    console.log('4. Capturing basemap-layers.png...');
    await client.eval(`
      const sel = document.getElementById('basemapSelect');
      sel.value = 'gibs';
      sel.dispatchEvent(new Event('change'));
      const wms = document.getElementById('toggleWms');
      wms.checked = true;
      wms.dispatchEvent(new Event('change'));
    `);
    await sleep(2500);
    await client.screenshot(path.join(outDir, 'basemap-layers.png'));

    // 5. notification-center.png (Open Notification Center panel)
    console.log('5. Capturing notification-center.png...');
    await client.eval(`document.getElementById('notifBell').click()`);
    await sleep(1000);
    await client.screenshot(path.join(outDir, 'notification-center.png'));
    await client.eval(`document.getElementById('notifClose').click()`);
    await sleep(500);

    // 6. monitoring-grid.png (Scroll to Sentinel-2 monitoring grid table)
    console.log('6. Capturing monitoring-grid.png...');
    await client.eval(`document.getElementById('grid-section').scrollIntoView({ behavior: 'instant', block: 'start' })`);
    await sleep(1000);
    await client.screenshot(path.join(outDir, 'monitoring-grid.png'));

    // 7. sentinel-analysis.png (Sentinel-2 & XGBoost single-point inference result)
    console.log('7. Capturing sentinel-analysis.png...');
    await client.eval(`document.getElementById('workspace-section').scrollIntoView({ behavior: 'instant', block: 'start' })`);
    await sleep(500);
    await client.eval(`
      switchTab('manual');
      document.getElementById('lat').value = '-3.5083';
      document.getElementById('lon').value = '104.5055';
    `);
    await sleep(500);
    await client.eval(`document.getElementById('prediction').dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }))`);
    
    // Wait for STAC & XGBoost analysis (up to 30s)
    for (let i = 0; i < 30; i++) {
      await sleep(1000);
      const resText = await client.eval(`document.getElementById('result')?.innerText`);
      if (resText && !resText.includes('Mencari citra, memeriksa awan')) {
        console.log('Analysis ready:', resText.slice(0, 100));
        break;
      }
    }
    await sleep(1000);
    await client.screenshot(path.join(outDir, 'sentinel-analysis.png'));

    // 8. mobile-view.png (Mobile responsive 390x844)
    console.log('8. Capturing mobile-view.png...');
    await client.send('Emulation.setDeviceMetricsOverride', {
      width: 390,
      height: 844,
      deviceScaleFactor: 2,
      mobile: true
    });
    await client.eval(`window.scrollTo(0, 0)`);
    await sleep(1500);
    await client.screenshot(path.join(outDir, 'mobile-view.png'));

    console.log('\n--- Checking console logs during session ---');
    console.log('Total unhandled JS exceptions:', client.errors.length);
    for (const err of client.errors) {
      console.error('Unhandled Exception:', err);
    }

    console.log('\n=== ALL 8 README SCREENSHOTS CAPTURED SUCCESSFULLY ===');
  } finally {
    chromeProc.kill('SIGKILL');
    try { fs.rmSync(PROFILE_DIR, { recursive: true, force: true }); } catch (e) {}
  }
}

run().catch(err => {
  console.error('Screenshot capture failed:', err);
  process.exit(1);
});

