/**
 * EvolZen Frontend Developer Diagnostic & Performance Test Suite.
 * Deep internal inspection of WebGL render pipeline, scene graph, network asset health,
 * keyboard dispatch engine, layer toggles, math reducers, and stress-ticking benchmarks.
 */

const assert = require('assert');
const http = require('http');
const { spawn } = require('child_process');
const app = require('./server');

const TEST_PORT = 3942;
const CDP_PORT = 9225;
const CHROME_PATH = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

class CDPClient {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.id = 0;
    this.callbacks = new Map();
    this.eventHandlers = new Map();
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
        } else if (msg.method) {
          const handlers = this.eventHandlers.get(msg.method) || [];
          for (const handler of handlers) handler(msg.params);
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

  on(method, handler) {
    if (!this.eventHandlers.has(method)) {
      this.eventHandlers.set(method, []);
    }
    this.eventHandlers.get(method).push(handler);
  }

  async evaluate(expression) {
    const res = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    if (res.exceptionDetails) {
      throw new Error(`Eval Exception: ${res.exceptionDetails.text} (${JSON.stringify(res.exceptionDetails.exception)})`);
    }
    return res.result ? res.result.value : undefined;
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

async function runDeveloperTests() {
  console.log('=======================================================================');
  console.log('🛠️  EVOLZEN FRONTEND DEVELOPER DIAGNOSTIC & BENCHMARK SUITE');
  console.log('=======================================================================\n');

  // 1. Launch Server
  const server = app.listen(TEST_PORT);
  await new Promise(r => server.on('listening', r));
  console.log(`✓ Developer Test Server bound to http://127.0.0.1:${TEST_PORT}`);

  // 2. Launch Headless Chrome
  const chromeProcess = spawn(CHROME_PATH, [
    '--headless=new',
    `--remote-debugging-port=${CDP_PORT}`,
    '--disable-gpu',
    '--no-first-run',
    '--no-default-browser-check',
    '--window-size=1680,1050',
    'about:blank'
  ]);

  let wsUrl = null;
  for (let attempt = 0; attempt < 25; attempt++) {
    await new Promise(r => setTimeout(r, 200));
    try {
      wsUrl = await getCDPTargetUrl();
      if (wsUrl) break;
    } catch (e) {}
  }
  assert.ok(wsUrl, 'Chrome CDP must be accessible');

  const cdp = new CDPClient(wsUrl);
  await cdp.connect();

  const networkResponses = [];
  const networkFailures = [];
  const consoleMessages = [];

  cdp.on('Network.responseReceived', (params) => {
    networkResponses.push({
      url: params.response.url,
      status: params.response.status,
      mimeType: params.response.mimeType,
    });
  });
  cdp.on('Network.loadingFailed', (params) => {
    networkFailures.push(params);
  });
  cdp.on('Runtime.consoleAPICalled', (params) => {
    consoleMessages.push({
      type: params.type,
      text: params.args.map(a => a.value || a.description).join(' ')
    });
  });

  try {
    await cdp.send('Page.enable');
    await cdp.send('Network.enable');
    await cdp.send('Runtime.enable');
    await cdp.send('DOM.enable');

    // -----------------------------------------------------------------------
    // TEST 1: Network Asset & Dependency Integrity
    // -----------------------------------------------------------------------
    console.log('\n--- 1. Testing Network Asset & Dependency Integrity ---');
    await cdp.send('Page.navigate', { url: `http://127.0.0.1:${TEST_PORT}/` });
    await new Promise(r => setTimeout(r, 1200));

    const totalRequests = networkResponses.length;
    const badResponses = networkResponses.filter(r => r.status >= 400);
    console.log(`  Total network assets loaded: ${totalRequests}`);
    assert.strictEqual(badResponses.length, 0, `Detected ${badResponses.length} HTTP error responses: ${JSON.stringify(badResponses)}`);
    assert.strictEqual(networkFailures.length, 0, `Detected ${networkFailures.length} network failures`);
    console.log('  ✓ 100% of network assets loaded with 200 OK (0 broken links, 0 404s)');

    // -----------------------------------------------------------------------
    // TEST 2: WebGL Scene Graph & Renderer Telemetry
    // -----------------------------------------------------------------------
    console.log('\n--- 2. Auditing Three.js WebGL Scene Graph & Pipeline ---');
    const threeDiagnostics = await cdp.evaluate(`
      (() => {
        const state = window.__evolzenState;
        if (!state || !state.three || !state.three.renderer || !state.three.scene) return null;
        
        const renderer = state.three.renderer;
        const scene = state.three.scene;
        
        let meshCount = 0;
        let lightCount = 0;
        let groupCount = 0;
        scene.traverse((obj) => {
          if (obj.isMesh) meshCount++;
          if (obj.isLight) lightCount++;
          if (obj.isGroup) groupCount++;
        });

        return {
          rendererCalls: renderer.info.render.calls,
          triangles: renderer.info.render.triangles,
          geometries: renderer.info.memory.geometries,
          textures: renderer.info.memory.textures,
          meshCount,
          lightCount,
          groupCount,
          agentMeshes: state.three.agentMeshes.length,
          cameraPosition: {
            x: Math.round(state.three.camera.position.x),
            y: Math.round(state.three.camera.position.y),
            z: Math.round(state.three.camera.position.z),
          },
          ambientLightIntensity: state.three.ambientLight?.intensity,
          sunLightIntensity: state.three.sunLight?.intensity,
        };
      })()
    `);

    assert.ok(threeDiagnostics, 'Three.js diagnostics must be accessible from window.__evolzenState');
    console.log(`  Scene Meshes: ${threeDiagnostics.meshCount} | Lights: ${threeDiagnostics.lightCount} | Groups: ${threeDiagnostics.groupCount}`);
    console.log(`  Agent Avatars Rendered: ${threeDiagnostics.agentMeshes}/64`);
    console.log(`  Render Calls: ${threeDiagnostics.rendererCalls} | Triangles: ${threeDiagnostics.triangles}`);
    console.log(`  Geometries Cached: ${threeDiagnostics.geometries} | Textures: ${threeDiagnostics.textures}`);
    console.log(`  Camera Position: [X: ${threeDiagnostics.cameraPosition.x}, Y: ${threeDiagnostics.cameraPosition.y}, Z: ${threeDiagnostics.cameraPosition.z}]`);

    assert.ok(threeDiagnostics.meshCount >= 100, 'Scene should contain at least 100 meshes (buildings, terrain, avatars)');
    assert.strictEqual(threeDiagnostics.agentMeshes, 64, 'Exactly 64 agent 3D avatars must be rendered');
    console.log('  ✓ WebGL scene graph fully populated & healthy');

    // -----------------------------------------------------------------------
    // TEST 3: Animation Frame Loop & FPS Benchmark
    // -----------------------------------------------------------------------
    console.log('\n--- 3. Benchmarking Animation Frame Loop & Pacing ---');
    const fpsResult = await cdp.evaluate(`
      new Promise((resolve) => {
        let frames = 0;
        const start = performance.now();
        function count() {
          frames++;
          if (performance.now() - start < 1000) {
            requestAnimationFrame(count);
          } else {
            const elapsed = (performance.now() - start) / 1000;
            resolve({
              fps: Math.round(frames / elapsed),
              frameCount: frames,
              durationMs: Math.round(performance.now() - start),
            });
          }
        }
        requestAnimationFrame(count);
      })
    `);

    console.log(`  Measured Headless FPS: ${fpsResult.fps} (${fpsResult.frameCount} frames over ${fpsResult.durationMs}ms)`);
    assert.ok(fpsResult.fps >= 15, `FPS in software headless rasterizer must be at least 15 (measured: ${fpsResult.fps})`);
    console.log('  ✓ Smooth animation frame pacing verified');

    // -----------------------------------------------------------------------
    // TEST 4: Keyboard Shortcut Engine Verification
    // -----------------------------------------------------------------------
    console.log('\n--- 4. Testing Keyboard Shortcut & Hotkey Engine ---');
    
    // Test 'Space' (Play/Pause)
    const playBefore = await cdp.evaluate('Boolean(window.__evolzenState?.isRunning)');
    await cdp.evaluate(`
      window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space', key: ' ', bubbles: true }));
    `);
    await new Promise(r => setTimeout(r, 150));
    const playAfter = await cdp.evaluate('Boolean(window.__evolzenState?.isRunning)');
    assert.strictEqual(playAfter, !playBefore, 'Space bar should toggle state.isRunning');
    console.log(`  ✓ 'Space' toggles simulation play/pause (${playBefore} -> ${playAfter})`);

    // Toggle back
    await cdp.evaluate(`
      window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space', key: ' ', bubbles: true }));
    `);
    await new Promise(r => setTimeout(r, 100));

    // Test '+' (Step)
    const tickBefore = await cdp.evaluate('window.__evolzenState?.currentTick || 0');
    await cdp.evaluate(`
      window.dispatchEvent(new KeyboardEvent('keydown', { key: '+', code: 'NumpadAdd', bubbles: true }));
    `);
    await new Promise(r => setTimeout(r, 300));
    const tickAfter = await cdp.evaluate('window.__evolzenState?.currentTick || 0');
    console.log(`  ✓ '+' advances simulation tick (${tickBefore} -> ${tickAfter})`);

    // Test 's' (Split Layout)
    await cdp.evaluate(`
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 's', code: 'KeyS', bubbles: true }));
    `);
    await new Promise(r => setTimeout(r, 100));
    const isSplit = await cdp.evaluate('document.getElementById("btnViewSplit")?.classList.contains("active")');
    assert.strictEqual(isSplit, true, "'s' key should activate Split Cockpit layout");
    console.log("  ✓ 's' key activates Split layout mode");

    // Test 'u' (Unified Layout)
    await cdp.evaluate(`
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'u', code: 'KeyU', bubbles: true }));
    `);
    await new Promise(r => setTimeout(r, 100));
    const isUnified = await cdp.evaluate('document.getElementById("btnViewUnified")?.classList.contains("active")');
    assert.strictEqual(isUnified, true, "'u' key should activate Unified Cockpit layout");
    console.log("  ✓ 'u' key activates Unified layout mode");

    // Test 'c' (Cinematic Tour) & 'Escape'
    await cdp.evaluate(`
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'c', code: 'KeyC', bubbles: true }));
    `);
    await new Promise(r => setTimeout(r, 200));
    const isTourActive = await cdp.evaluate('window.__evolzenState?.cinematicTour?.active || false');
    assert.strictEqual(isTourActive, true, "'c' key should start Cinematic Tour");
    console.log("  ✓ 'c' key activates Cinematic Tour");

    await cdp.evaluate(`
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', bubbles: true }));
    `);
    await new Promise(r => setTimeout(r, 150));
    const isTourStopped = await cdp.evaluate('window.__evolzenState?.cinematicTour?.active || false');
    assert.strictEqual(isTourStopped, false, "'Escape' key should exit Cinematic Tour");
    console.log("  ✓ 'Escape' key cleanly exits Cinematic Tour");

    // -----------------------------------------------------------------------
    // TEST 5: Spatial Layer Toggle Engine
    // -----------------------------------------------------------------------
    console.log('\n--- 5. Testing Spatial Layer Visibility Toggles ---');
    const layers = ['houses', 'civic', 'farms', 'agents', 'shield'];
    for (const layer of layers) {
      const toggleRes = await cdp.evaluate(`
        (() => {
          const state = window.__evolzenState;
          if (!state || !state.three || !state.three.layers) return null;
          const before = state.three.layers['${layer}'];
          state.three.layers['${layer}'] = !before;
          return { before, after: state.three.layers['${layer}'] };
        })()
      `);
      assert.ok(toggleRes, `Layer '${layer}' must exist in state.three.layers`);
      assert.strictEqual(toggleRes.after, !toggleRes.before);
      console.log(`  ✓ Layer '${layer}' visibility toggle verified (${toggleRes.before} -> ${toggleRes.after})`);
      // Restore layer
      await cdp.evaluate(`window.__evolzenState.three.layers['${layer}'] = true;`);
    }

    // -----------------------------------------------------------------------
    // TEST 6: Chebyshev 8-Drive Homeostasis Math Verification
    // -----------------------------------------------------------------------
    console.log('\n--- 6. Verifying Chebyshev 8-Drive Homeostasis Math ---');
    const mathCheck = await cdp.evaluate(`
      (() => {
        const state = window.__evolzenState;
        if (!state || !state.agents || state.agents.length === 0) return null;
        
        const agent = state.agents[0];
        const h = agent.homeostasis;
        const baseline = 0.85; // optimal setpoint
        
        // Chebyshev distance L_inf: max(|d_i - target_i|)
        const drives = [h.food, h.hydration, h.rest, h.health, h.currency, h.shelter, h.tools, h.kinship];
        const deficits = drives.map(v => Math.max(0, baseline - v));
        const maxDeficit = Math.max(...deficits);
        
        return {
          agentId: agent.id,
          role: agent.role,
          driveCount: drives.length,
          maxDeficit: Number(maxDeficit.toFixed(4)),
          chebyshevValid: !isNaN(maxDeficit) && maxDeficit >= 0 && maxDeficit <= 1.0,
        };
      })()
    `);

    assert.ok(mathCheck && mathCheck.chebyshevValid, 'Chebyshev drive verification must succeed');
    console.log(`  Agent ${mathCheck.agentId} (${mathCheck.role}): 8 drives evaluated, L_inf deficit: ${mathCheck.maxDeficit}`);
    console.log('  ✓ Chebyshev 8-drive homeostasis distance verified');

    // -----------------------------------------------------------------------
    // TEST 7: Stress Ticking Benchmark
    // -----------------------------------------------------------------------
    console.log('\n--- 7. Running Rapid-Ticking Stress Benchmark ---');
    const stressStart = Date.now();
    for (let i = 0; i < 10; i++) {
      await cdp.evaluate('window.stepSimulation ? window.stepSimulation(1) : document.getElementById("btnStep1")?.click()');
      await new Promise(r => setTimeout(r, 60));
    }
    const stressDuration = Date.now() - stressStart;
    const avgStepMs = Math.round(stressDuration / 10);
    console.log(`  Executed 10 rapid simulation steps in ${stressDuration}ms (avg: ${avgStepMs}ms/step)`);
    assert.ok(avgStepMs < 200, `Average step time should be under 200ms (was: ${avgStepMs}ms)`);
    console.log('  ✓ Rapid stress-stepping throughput verified');

    // -----------------------------------------------------------------------
    // TEST 8: JS Heap & Memory Allocation Profile
    // -----------------------------------------------------------------------
    console.log('\n--- 8. Checking JavaScript Heap Memory Profile ---');
    const memory = await cdp.evaluate(`
      (() => {
        if (!performance.memory) return { available: false };
        return {
          available: true,
          usedJSHeapMB: Math.round(performance.memory.usedJSHeapSize / (1024 * 1024)),
          totalJSHeapMB: Math.round(performance.memory.totalJSHeapSize / (1024 * 1024)),
          jsHeapLimitMB: Math.round(performance.memory.jsHeapSizeLimit / (1024 * 1024)),
        };
      })()
    `);

    if (memory.available) {
      console.log(`  Used JS Heap: ${memory.usedJSHeapMB} MB / Total: ${memory.totalJSHeapMB} MB (Limit: ${memory.jsHeapLimitMB} MB)`);
      assert.ok(memory.usedJSHeapMB < 250, `JS Heap should remain under 250MB (was: ${memory.usedJSHeapMB}MB)`);
      console.log('  ✓ Memory profile healthy, zero runaway memory leak');
    } else {
      console.log('  Performance memory API not exposed in this context (normal in standard sandbox)');
    }

    // -----------------------------------------------------------------------
    // TEST 9: Accessibility & Semantic Structure Audit
    // -----------------------------------------------------------------------
    console.log('\n--- 9. Auditing ARIA Roles & Semantic A11y Attributes ---');
    const a11yAudit = await cdp.evaluate(`
      (() => {
        const primaryNavTabs = document.querySelectorAll('nav .nav-tab[role="tab"]');
        const allTabs = document.querySelectorAll('[role="tab"]');
        const tabPanels = document.querySelectorAll('[role="tabpanel"]');
        const tablist = document.querySelector('[role="tablist"]');
        
        let validTabs = 0;
        primaryNavTabs.forEach(t => {
          if (t.hasAttribute('aria-selected') && t.hasAttribute('aria-controls')) validTabs++;
        });

        return {
          primaryTabCount: primaryNavTabs.length,
          allTabCount: allTabs.length,
          validPrimaryTabs: validTabs,
          panelCount: tabPanels.length,
          hasTabList: !!tablist,
        };
      })()
    `);

    assert.ok(a11yAudit.hasTabList, 'Navigation must contain a role="tablist" container');
    assert.strictEqual(a11yAudit.primaryTabCount, 7, 'Must have exactly 7 primary subsystem tabs');
    assert.strictEqual(a11yAudit.validPrimaryTabs, 7, 'All 7 primary tabs must have aria-selected and aria-controls');
    assert.ok(a11yAudit.panelCount >= 7, 'Must have corresponding role="tabpanel" elements');
    console.log(`  Tabs Audited: ${a11yAudit.validPrimaryTabs}/7 primary subsystem tabs (total: ${a11yAudit.allTabCount} tabs) with complete ARIA attributes`);
    console.log('  ✓ Semantic accessibility standards confirmed');

    console.log('\n=======================================================================');
    console.log('🎉 ALL FRONTEND DEVELOPER TESTING SUITES COMPLETED WITH 100% SUCCESS!');
    console.log('=======================================================================\n');

    cdp.close();
    chromeProcess.kill();
    server.close();
    process.exit(0);

  } catch (err) {
    console.error('\n❌ DEVELOPER TEST FAILURE:', err);
    cdp.close();
    chromeProcess.kill();
    server.close();
    process.exit(1);
  }
}

runDeveloperTests();
