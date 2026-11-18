/**
 * High-Resolution Chrome DevTools Protocol Renderer for EvolZen Charts.
 * Renders all SVG charts into 2x Retina PNG and JPG images.
 */
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const CDP_PORT = 9228;
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const BASE_DIR = path.resolve(__dirname, '..');
const CHARTS_SRC = path.join(BASE_DIR, 'dashboard', 'public', 'charts');
const ROOT_CHARTS = path.join(BASE_DIR, 'charts');
const ASSETS_DIR = path.join(BASE_DIR, 'dashboard', 'public', 'assets');
const ARTIFACT_DIR = 'C:\\Users\\anubh\\.gemini\\antigravity\\brain\\1996f9dc-407d-4f54-97bc-30bf49ddd150';

const CHARTS = [
  { name: 'lora_dora_convergence', width: 980, height: 560 },
  { name: 'training_progress_overview', width: 1200, height: 760 },
  { name: 'loss_convergence', width: 720, height: 420 },
  { name: 'grpo_gradient_dynamics', width: 720, height: 440 },
  { name: 'rule_impact', width: 720, height: 460 },
  { name: 'policy_entropy', width: 720, height: 420 },
  { name: 'jepa_variance', width: 720, height: 420 },
  { name: 'environmental_motives', width: 720, height: 420 },
  { name: 'continual_retention', width: 720, height: 420 }
];

class CDPClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.id = 0;
    this.callbacks = new Map();
  }

  async connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.onopen = () => resolve();
      this.ws.onerror = (err) => reject(err);
      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id && this.callbacks.has(msg.id)) {
          const { resolve, reject } = this.callbacks.get(msg.id);
          this.callbacks.delete(msg.id);
          if (msg.error) {
            reject(new Error(msg.error.message));
          } else {
            resolve(msg.result);
          }
        }
      };
    });
  }

  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++this.id;
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

async function getCDPTargetUrl() {
  return new Promise((resolve, reject) => {
    http.get(`http://127.0.0.1:${CDP_PORT}/json/list`, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const targets = JSON.parse(data);
          const pageTarget = targets.find(t => t.type === 'page');
          if (pageTarget && pageTarget.webSocketDebuggerUrl) {
            resolve(pageTarget.webSocketDebuggerUrl);
          } else {
            reject(new Error('No page target found'));
          }
        } catch (e) {
          reject(e);
        }
      });
    }).on('error', reject);
  });
}

function saveToAllDestinations(filename, buffer) {
  const dests = [
    path.join(ROOT_CHARTS, filename),
    path.join(CHARTS_SRC, filename),
    path.join(ASSETS_DIR, filename),
    path.join(ARTIFACT_DIR, filename)
  ];

  for (const dest of dests) {
    try {
      const dir = path.dirname(dest);
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(dest, buffer);
    } catch (e) {
      console.warn(`Could not write to ${dest}:`, e.message);
    }
  }
}

async function renderCharts() {
  console.log('--- Starting Chrome DevTools Image Generation Pipeline ---');

  if (!fs.existsSync(ROOT_CHARTS)) fs.mkdirSync(ROOT_CHARTS, { recursive: true });
  if (!fs.existsSync(ASSETS_DIR)) fs.mkdirSync(ASSETS_DIR, { recursive: true });

  const chromeProc = spawn(CHROME_PATH, [
    '--headless',
    `--remote-debugging-port=${CDP_PORT}`,
    '--disable-gpu',
    '--no-sandbox',
    '--window-size=1600,1000',
    '--hide-scrollbars'
  ]);

  await new Promise(r => setTimeout(r, 1500));

  try {
    const wsUrl = await getCDPTargetUrl();
    console.log('✓ Attached to Chrome CDP via WebSocket:', wsUrl);
    const cdp = new CDPClient(wsUrl);
    await cdp.connect();
    await cdp.send('Page.enable');

    for (const item of CHARTS) {
      const svgPath = path.join(CHARTS_SRC, `${item.name}.svg`);
      if (!fs.existsSync(svgPath)) {
        console.warn(`[SKIP] SVG not found: ${svgPath}`);
        continue;
      }

      const svgContent = fs.readFileSync(svgPath, 'utf8');

      // Create self-contained high-DPI HTML wrapper
      const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    html, body {
      background: #020617;
      width: ${item.width}px;
      height: ${item.height}px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    svg {
      width: ${item.width}px;
      height: ${item.height}px;
      display: block;
    }
  </style>
</head>
<body>
  ${svgContent}
</body>
</html>`;

      const tmpHtmlPath = path.join(BASE_DIR, 'dashboard', 'public', `_tmp_${item.name}.html`);
      fs.writeFileSync(tmpHtmlPath, html, 'utf8');

      // Set high-DPI device scale factor (2x Retina rendering)
      await cdp.send('Emulation.setDeviceMetricsOverride', {
        width: item.width,
        height: item.height,
        deviceScaleFactor: 2,
        mobile: false
      });

      const url = `http://localhost:3000/_tmp_${item.name}.html`;
      await cdp.send('Page.navigate', { url });
      await new Promise(r => setTimeout(r, 600));

      // 1. Capture PNG
      const pngShot = await cdp.send('Page.captureScreenshot', {
        format: 'png',
        fromSurface: true,
        clip: {
          x: 0,
          y: 0,
          width: item.width,
          height: item.height,
          scale: 2
        }
      });
      const pngBuffer = Buffer.from(pngShot.data, 'base64');
      saveToAllDestinations(`${item.name}.png`, pngBuffer);

      // 2. Capture JPG (Quality 95)
      const jpgShot = await cdp.send('Page.captureScreenshot', {
        format: 'jpeg',
        quality: 95,
        fromSurface: true,
        clip: {
          x: 0,
          y: 0,
          width: item.width,
          height: item.height,
          scale: 2
        }
      });
      const jpgBuffer = Buffer.from(jpgShot.data, 'base64');
      saveToAllDestinations(`${item.name}.jpg`, jpgBuffer);

      console.log(`✓ Rendered ${item.name}: PNG (${(pngBuffer.length / 1024).toFixed(1)} KB), JPG (${(jpgBuffer.length / 1024).toFixed(1)} KB)`);

      // Cleanup tmp HTML
      try { fs.unlinkSync(tmpHtmlPath); } catch (_) {}
    }

    // Also copy all SVGs to root charts/
    for (const item of CHARTS) {
      const srcSvg = path.join(CHARTS_SRC, `${item.name}.svg`);
      if (fs.existsSync(srcSvg)) {
        saveToAllDestinations(`${item.name}.svg`, fs.readFileSync(srcSvg));
      }
    }

    console.log('\n--- All PNG, JPG, and SVG charts generated and synced successfully! ---');
    cdp.close();
  } finally {
    try {
      chromeProc.kill('SIGKILL');
    } catch (_) {}
  }
}

renderCharts().catch(err => {
  console.error('Render failure:', err);
  process.exit(1);
});
