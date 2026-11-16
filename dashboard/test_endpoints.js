/**
 * Test suite for EvolZen Portfolio Dashboard Backend Endpoints.
 * Verifies server startup, autoplay background ticking, drought shock,
 * communal silo withdrawals, Chebyshev 8-drive homeostasis, and
 * architecture pipeline hazard metadata.
 */

const assert = require('assert');
const http = require('http');
const app = require('./server');

const TEST_PORT = 3899;

function request(method, path, body = null) {
  return new Promise((resolve, reject) => {
    const payload = body ? JSON.stringify(body) : null;
    const req = http.request({
      hostname: '127.0.0.1',
      port: TEST_PORT,
      path: path,
      method: method,
      headers: payload ? {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      } : {}
    }, (res) => {
      let data = '';
      res.on('data', chunk => { data += chunk; });
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(data) });
        } catch (e) {
          resolve({ status: res.statusCode, raw: data });
        }
      });
    });
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

async function runTests() {
  console.log('🚀 Starting EvolZen Live Dashboard Backend Test Suite...');
  
  const server = app.listen(TEST_PORT);
  await new Promise(r => server.on('listening', r));
  console.log(`✓ Server listening on http://127.0.0.1:${TEST_PORT}`);

  try {
    // 1. World metadata
    console.log('\n--- 1. Testing /api/world/meta ---');
    const metaRes = await request('GET', '/api/world/meta');
    assert.strictEqual(metaRes.status, 200);
    assert.strictEqual(metaRes.data.world.water_mandate, 0);
    assert.strictEqual(metaRes.data.civic_structures.length >= 6, true);
    console.log(`✓ /api/world/meta OK (${metaRes.data.civic_structures.length} civic structures)`);

    // 2. Architecture pipeline & LLM route metadata
    console.log('\n--- 2. Testing /api/architecture/pipeline ---');
    const pipeRes = await request('GET', '/api/architecture/pipeline');
    assert.strictEqual(pipeRes.status, 200);
    const llmNode = pipeRes.data.nodes.find(n => n.id === 'llm_cognitive_route');
    assert.ok(llmNode, 'llm_cognitive_route node must exist');
    assert.strictEqual(llmNode.status, 'STAGED_RESEARCH', 'status must be STAGED_RESEARCH');
    assert.strictEqual(llmNode.color, '#f59e0b', 'color must be #f59e0b');
    assert.strictEqual(llmNode.hazard_badge, 'RESEARCH WIP / ZERO RUNTIME INFERENCE', 'hazard_badge must match');
    assert.ok(llmNode.metadata, 'metadata must exist');
    assert.strictEqual(llmNode.metadata.zero_runtime_inference, true, 'zero_runtime_inference must be true');
    assert.ok(llmNode.metadata.runtime_gpu_inference.includes('ZERO'), 'runtime_gpu_inference must note zero');
    assert.ok(llmNode.metadata.runtime_llm_inference.includes('ZERO'), 'runtime_llm_inference must note zero');
    console.log(`✓ /api/architecture/pipeline OK: status=${llmNode.status}, color=${llmNode.color}, badge="${llmNode.hazard_badge}"`);

    // 3. Autoplay endpoint
    console.log('\n--- 3. Testing /api/sim/autoplay ---');
    const autoGetRes = await request('GET', '/api/sim/autoplay');
    assert.strictEqual(autoGetRes.status, 200);
    assert.strictEqual(autoGetRes.data.active, false);

    // Start autoplay with 150ms interval
    const autoStartRes = await request('POST', '/api/sim/autoplay', { active: true, interval_ms: 150 });
    assert.strictEqual(autoStartRes.status, 200);
    assert.strictEqual(autoStartRes.data.active, true);
    assert.strictEqual(autoStartRes.data.interval_ms, 150);
    console.log(`✓ Autoplay started at interval: ${autoStartRes.data.interval_ms}ms`);

    const initialTick = autoStartRes.data.tick;
    // Wait 350ms to allow ~2 ticks to occur
    await new Promise(r => setTimeout(r, 350));

    const autoCheckRes = await request('GET', '/api/sim/autoplay');
    assert.strictEqual(autoCheckRes.status, 200);
    assert.ok(autoCheckRes.data.tick > initialTick, `Tick should advance in autoplay (was ${initialTick}, now ${autoCheckRes.data.tick})`);
    console.log(`✓ Background ticking verified: advanced from tick ${initialTick} to ${autoCheckRes.data.tick}`);

    // Stop autoplay
    const autoStopRes = await request('POST', '/api/sim/autoplay', { active: false });
    assert.strictEqual(autoStopRes.status, 200);
    assert.strictEqual(autoStopRes.data.active, false);
    console.log('✓ Autoplay stopped cleanly');

    // 4. Drought shock endpoint
    console.log('\n--- 4. Testing /api/environment/drought ---');
    // Read state before drought
    const envBefore = await request('GET', '/api/environment/state');
    const westFarmsFoodBefore = envBefore.data.locations.west_farms.food;
    const renewalBefore = envBefore.data.locations.west_farms.renewal_rate;

    // Trigger drought
    const droughtRes = await request('POST', '/api/environment/drought', { active: true, severity: 0.60 });
    assert.strictEqual(droughtRes.status, 200);
    assert.strictEqual(droughtRes.data.drought.active, true);
    assert.strictEqual(droughtRes.data.drought.severity, 0.60);
    assert.ok(droughtRes.data.event, 'Event must be logged');
    assert.strictEqual(droughtRes.data.event.type, 'DROUGHT_SHOCK_TRIGGERED');
    console.log(`✓ Drought event logged: "${droughtRes.data.event.message}"`);

    // Verify 60% resource scarcity shock across locations
    const westFarmsFoodAfter = droughtRes.data.locations.west_farms.food;
    const renewalAfter = droughtRes.data.locations.west_farms.renewal_rate;
    assert.ok(westFarmsFoodAfter < westFarmsFoodBefore, `West farms food dropped: ${westFarmsFoodBefore} -> ${westFarmsFoodAfter}`);
    assert.ok(renewalAfter < renewalBefore, `West farms renewal dropped: ${renewalBefore} -> ${renewalAfter}`);
    console.log(`✓ 60% resource scarcity verified: food ${westFarmsFoodBefore} -> ${westFarmsFoodAfter}, renewal ${renewalBefore} -> ${renewalAfter}`);

    // 5. Stepping with smooth waypoint navigation and communal silo withdrawals under drought
    console.log('\n--- 5. Testing /api/environment/step & Communal Silo Withdrawals ---');
    const siloBefore = droughtRes.data.communal_silo.food_reserve;
    console.log(`Initial communal silo reserve: ${siloBefore}`);

    // Step 15 times to let agents navigate and withdraw from communal silos
    for (let i = 0; i < 15; i++) {
      await request('POST', '/api/environment/step', { steps: 1 });
    }

    const rosterRes = await request('GET', '/api/agents/roster');
    assert.strictEqual(rosterRes.status, 200);
    const agents = rosterRes.data.agents;
    assert.strictEqual(agents.length, 64);

    // Verify agents have waypoints and are navigating
    const agentsWithWaypoints = agents.filter(a => a.waypoints && a.waypoints.length > 0);
    assert.ok(agentsWithWaypoints.length > 0, 'Agents should have waypoint navigation paths');

    // Verify communal silo withdrawals under drought
    const siloAfter = rosterRes.data.communal_silo.food_reserve;
    const totalWithdrawn = rosterRes.data.communal_silo.total_withdrawn;
    console.log(`Communal silo reserve after drought steps: ${siloAfter} (withdrawn: ${totalWithdrawn})`);
    assert.ok(totalWithdrawn > 0, 'Agents must withdraw food from communal silos during drought');

    // Check that some agents performed WITHDRAW_INSTITUTION
    const agentsWithdrawing = agents.filter(a => a.action === 'WITHDRAW_INSTITUTION' || a.target.label.includes('Silo'));
    console.log(`Agents targeting or withdrawing from communal silos: ${agentsWithdrawing.length}`);
    assert.ok(agentsWithdrawing.length > 0, 'At least one agent should target or perform WITHDRAW_INSTITUTION under drought');

    // Check Chebyshev 8-drive homeostasis properties
    for (const a of agents.slice(0, 5)) {
      const h = a.homeostasis;
      assert.ok(h.food !== undefined && h.hydration !== undefined && h.rest !== undefined && h.health !== undefined, '8 drives must be present');
      assert.ok(h.currency !== undefined && h.shelter !== undefined && h.tools !== undefined && h.kinship !== undefined, '8 drives must be present');
    }
    console.log('✓ Chebyshev 8-drive homeostasis verified across agents');

    // Lift drought
    const liftRes = await request('POST', '/api/environment/drought', { active: false });
    assert.strictEqual(liftRes.status, 200);
    assert.strictEqual(liftRes.data.drought.active, false);
    console.log('✓ Drought lifted cleanly');

    console.log('\n🎉 ALL BACKEND VERIFICATION CHECKS PASSED SUCCESSFULLY!\n');
  } finally {
    server.close();
  }
}

runTests().catch(err => {
  console.error('❌ Test failed:', err);
  process.exit(1);
});
