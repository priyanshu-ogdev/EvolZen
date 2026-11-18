/**
 * EVOLZEN // 1×1 KM Parallel Universe & Multi-Agent Infrastructure
 * 3D World Engine, Procedural Humanoid Figures & Interactive Client Logic
 * Pure Client-Side WebGL (Three.js) & Zero Runtime LLM Inference by Architectural Mandate
 * Author: Shreyan Mitra
 */

import * as THREE from './vendor/three.module.js';
import { OrbitControls } from './vendor/OrbitControls.js';

(function () {
  'use strict';

  // =========================================================================
  // 1. Global Dashboard & 3D Engine State
  // =========================================================================
  const state = {
    worldMeta: null,
    envState: null,
    economyState: null,
    rules: [],
    selectedRuleId: null,
    selectedAgentId: null,
    followingAgentId: null,
    pipeline: null,
    auditData: null,
    agents: [],
    activeTab: 'tab-map',
    activeSubsystem: 'tab-environment',
    layoutMode: 'unified', // 'unified', 'split', 'theater', 'focus'
    viewMode: '3d', // '3d' or '2d'
    isNightMode: true,
    isDroughtActive: false,

    // Simulation playback & speed
    isRunning: false,
    timer: null,
    simSpeed: '1x',
    simIntervalMs: 1200,
    simSpeedFactor: 1.0,

    // Guided Portfolio Workflow Tour
    tour: {
      step: 0,
      autoPlay: false,
      timer: null
    },

    // Single Unified Cinematic Tour Engine (combining Auto Tour & Spectate)
    cinematicTour: {
      active: false,
      roleIndex: 0,
      roles: ['Farmer', 'Trader', 'Builder', 'Medic', 'Crafter', 'Generalist'],
      landmarks: {
        Farmer: { name: 'West Farm Belt & Silos', pos: { x: 50, z: 500 } },
        Trader: { name: 'Central Agora Market', pos: { x: 550, z: 650 } },
        Builder: { name: 'Civic Core & Portico', pos: { x: 500, z: 500 } },
        Medic: { name: 'Civic Hospital Anchor', pos: { x: 450, z: 550 } },
        Crafter: { name: 'Engineering Workshop', pos: { x: 650, z: 550 } },
        Generalist: { name: 'Civic Conservatory & Commons', pos: { x: 350, z: 450 } }
      },
      currentShotType: 'CHASE', // 'CHASE', 'LOW_ANGLE', 'DRONE_ORBIT', 'FRONTAL'
      shotAngleIndex: 0,
      shotNames: {
        'CHASE': 'OVER-SHOULDER CHASE CAM',
        'LOW_ANGLE': 'LOW-ANGLE PAVEMENT DOLLY',
        'DRONE_ORBIT': 'HIGH 45° DRONE ORBIT',
        'FRONTAL': 'FRONTAL APPROACH DOLLY'
      },
      timer: null,
      countdownTimer: null,
      countdownSeconds: 6,
      orbitAngle: 0,
      currentAgent: null,
      agentIndexByRole: {
        'Farmer': 0,
        'Trader': 0,
        'Builder': 0,
        'Medic': 0,
        'Crafter': 0,
        'Generalist': 0
      }
    },
    // Backwards compatibility alias
    spectate: null,

    // Dedicated Fullscreen World View
    fullscreen: {
      active: false
    },

    // 3D Three.js Engine State
    three: {
      renderer: null,
      scene: null,
      camera: null,
      controls: null,
      clock: new THREE.Clock(),
      raycaster: new THREE.Raycaster(),
      mouse: new THREE.Vector2(),
      groundGroup: null,
      housesGroup: null,
      civicGroup: null,
      farmsGroup: null,
      agentsGroup: null,
      streetLightsGroup: null,
      celestialGroup: null,
      sunMesh: null,
      sunCorona: null,
      moonMesh: null,
      starField: null,
      starMat: null,
      zzzGroup: null,
      zzzParticles: [],
      harvestGroup: null,
      harvestBadges: [],
      cropPlots: [],
      cropStageMats: null,
      housePositions: {},
      shieldMesh: null,
      agoraRing: null,
      hospitalBeacon: null,
      hospitalLight: null,
      fireSirenLight: null,
      sunLight: null,
      ambientLight: null,
      agentMeshes: [], // array of agent avatar wrappers
      houseMeshes: [],
      civicMeshes: [],
      clickableMeshes: [],
      hoveredObject: null,
      selectedObject: null,
      camTargetPos: null,
      camLookAtPos: null,
      windowMaterials: [],
      cropMaterials: [],
      layers: {
        houses: true,
        civic: true,
        farms: true,
        agents: true,
        shield: true
      }
    },

    // 2D Map Canvas Fallback
    map2d: {
      canvas: null,
      ctx: null,
      bgImage: null,
      bgLoaded: false,
      scale: 1,
      minScale: 0.6,
      maxScale: 6.0,
      offsetX: 0,
      offsetY: 0,
      isDragging: false,
      dragStartX: 0,
      dragStartY: 0
    },

    // Archetype definitions and architectural specifications
    archetypes: {
      0: { name: 'Ranch', color: 0xfacc15, hex: '#facc15', floors: 1, height: 4.0, walls: 'VINYL (Yellow)', roof: 'WIDE GABLE (Grey)', roofColor: 0x475569, chimney: 'Brick' },
      1: { name: 'Colonial', color: 0xef4444, hex: '#ef4444', floors: 2, height: 7.2, walls: 'BRICK (Crimson)', roof: 'CLAY SHINGLE (Red)', roofColor: 0x991b1b, chimney: 'Twin Brick' },
      2: { name: 'McMansion', color: 0xf59e0b, hex: '#f59e0b', floors: 2, height: 8.5, walls: 'STUCCO / VINYL (Beige)', roof: 'MULTI-PITCH TILE', roofColor: 0x334155, chimney: 'Stone Wing' },
      3: { name: 'Bungalow', color: 0xb45309, hex: '#b45309', floors: 1, height: 4.2, walls: 'CEDAR WOOD (Brown)', roof: 'STEEP GABLE 45°', roofColor: 0x78350f, chimney: 'Fieldstone' },
      4: { name: 'Modern Flat', color: 0x38bdf8, hex: '#38bdf8', floors: 2, height: 6.8, walls: 'CONCRETE (White)', roof: 'FLAT TERRACE + RAILING', roofColor: 0x64748b, chimney: 'Flue Vent' }
    },

    // Civic Anchors & Key Facilities
    civicAnchors: [
      { id: 'hospital', name: 'Hospital ✚ Trauma Center', x: 450, z: 550, size: 42, height: 26, color: 0xef4444, hex: '#ef4444', icon: '🏥', desc: 'Regional triage & convalescence facility with rooftop pulsing red cross' },
      { id: 'school', name: 'Civic Academy', x: 650, z: 550, size: 38, height: 20, color: 0xb91c1c, hex: '#b91c1c', icon: '🏫', desc: 'Manual cultural transmission, clock tower & civic academy' },
      { id: 'fire', name: 'Fire Station Core', x: 550, z: 450, size: 32, height: 18, color: 0xdc2626, hex: '#dc2626', icon: '🚒', desc: 'Hazard containment & emergency siren dispatch with dual bay doors' },
      { id: 'municipal', name: 'Municipal Office', x: 450, z: 450, size: 36, height: 24, color: 0xeab308, hex: '#eab308', icon: '🏛️', desc: 'Civic governance hall, colonnade portico, deed registry & voting' },
      { id: 'market', name: 'Central Agora Market', x: 550, z: 650, size: 46, height: 14, color: 0xf97316, hex: '#f97316', icon: '⚖️', desc: 'Continuous double-auction order book, striped awnings & commodity crates' },
      { id: 'park', name: 'Central Park Conservatory', x: 500, z: 500, w: 100, h: 100, color: 0x10b981, hex: '#10b981', icon: '🌲', isZone: true, desc: 'Public green reserve, walking paths & Victorian glass greenhouse' },
      { id: 'silo', name: 'Communal Granary Silos', x: 520, z: 620, size: 32, height: 24, color: 0xf59e0b, hex: '#f59e0b', icon: '🌾', desc: 'Communal grain reserve silos buffering famine & drought stress' },
      { id: 'workshop', name: 'Timber & Quarry Workshops', x: 450, z: 250, size: 36, height: 16, color: 0x8b5cf6, hex: '#8b5cf6', icon: '🛠️', desc: 'Tool fabrication, masonry cutting & material processing facility' }
    ],

    // Role definitions for 64 agents
    roles: {
      'Farmer': { color: '#10b981', colorHex: 0x10b981, prop: 'pitchfork', hat: 'straw_hat', defaultAction: 'GATHER_CROP' },
      'Builder': { color: '#eab308', colorHex: 0xeab308, prop: 'hammer', hat: 'hardhat', defaultAction: 'CONSTRUCT' },
      'Crafter': { color: '#8b5cf6', colorHex: 0x8b5cf6, prop: 'wrench', hat: 'goggles', defaultAction: 'CRAFT_TOOL' },
      'Trader': { color: '#f59e0b', colorHex: 0xf59e0b, prop: 'coin_pouch', hat: 'beret', defaultAction: 'AUCTION_BID' },
      'Medic': { color: '#ef4444', colorHex: 0xef4444, prop: 'medkit', hat: 'red_cross_cap', defaultAction: 'MEDIC_CARE' },
      'Generalist': { color: '#06b6d4', colorHex: 0x06b6d4, prop: 'satchel', hat: 'cap', defaultAction: 'CIVIC_REST' }
    },

    // 10 Voronoi Centroids for CVTArchive 5D Niche Matrix
    cvtCentroids: [
      { id: 'C-01', name: 'Agricultural Optimizers', coords: [0.85, 0.20, 0.35, 0.90, 0.40], fitness: 94.2, count: 8, elite: 'agent_03' },
      { id: 'C-02', name: 'Civic Infrastructure Builders', coords: [0.25, 0.88, 0.40, 0.85, 0.70], fitness: 91.5, count: 7, elite: 'agent_14' },
      { id: 'C-03', name: 'Double-Auction Arbitrageurs', coords: [0.30, 0.45, 0.95, 0.75, 0.65], fitness: 96.8, count: 6, elite: 'agent_42' },
      { id: 'C-04', name: 'Emergency Trauma Medics', coords: [0.40, 0.30, 0.25, 0.98, 0.85], fitness: 89.0, count: 4, elite: 'agent_31' },
      { id: 'C-05', name: 'Composite Tool Fabricators', coords: [0.35, 0.92, 0.60, 0.82, 0.55], fitness: 93.4, count: 7, elite: 'agent_22' },
      { id: 'C-06', name: 'High-Velocity Logistics', coords: [0.70, 0.50, 0.80, 0.78, 0.60], fitness: 88.6, count: 6, elite: 'agent_08' },
      { id: 'C-07', name: 'Granary Stock Keepers', coords: [0.90, 0.40, 0.50, 0.88, 0.75], fitness: 90.1, count: 7, elite: 'agent_19' },
      { id: 'C-08', name: 'Quarry Extraction Engineers', coords: [0.30, 0.75, 0.35, 0.80, 0.50], fitness: 87.3, count: 6, elite: 'agent_48' },
      { id: 'C-09', name: 'Institutional Norm Curators', coords: [0.45, 0.60, 0.70, 0.92, 0.95], fitness: 95.0, count: 7, elite: 'agent_12' },
      { id: 'C-10', name: 'Adaptive Commons Generalists', coords: [0.60, 0.60, 0.60, 0.84, 0.70], fitness: 88.9, count: 6, elite: 'agent_07' }
    ]
  };
  state.spectate = state.cinematicTour;

  // Subsystem Console Titles Mapping
  const subsystemTitles = {
    'tab-environment': 'Phase 1.1 Moore Machine & Ecological Invariant Guardian',
    'tab-economy': 'Phase 1.3 Agora Market & Lorenz Wealth Distribution',
    'tab-library': 'Phase 1.4 & 1.5 gVisor Sandbox & CapabilityPackage DAG',
    'tab-cvt': 'Phase 2.3 CVTArchive 5D Niche Matrix & Voronoi Elite Fitness',
    'tab-archive': 'Phase 2.3 CVTArchive 5D Niche Matrix & Voronoi Elite Fitness',
    'tab-pipeline': 'Decoupled Zero-Inference Architecture Topology (Hazard Staged LLM Route)',
    'tab-audit': 'Phase 2.5 Patent-Grade Source-Audit Certificate (439 Passed / 0 Skipped)'
  };

  // 6-Step Guided Portfolio Workflow Tour (Multi-Role Auto Tour across all colony roles)
  const tourSteps = [
    {
      step: 1,
      badge: 'PHASE 1.1 SUBSTRATE & 1×1 KM MOORE MACHINE',
      title: '1×1 km Spatial Substrate & Deterministic Moore Machine',
      desc: 'Civic Core Aerial Overview · 10,378 Chunks · 340M Voxels Reconciled · Zero Water Mandate · 98.7% Street Grid',
      layout: 'unified',
      subsystem: 'tab-environment',
      camera: { pos: new THREE.Vector3(530, 85, 680), target: new THREE.Vector3(500, 10, 520) },
      action: () => {
        state.followingAgentId = null;
      }
    },
    {
      step: 2,
      badge: 'PHASE 1.2 POPULATION: AGRARIAN CORE',
      title: 'Population: Agrarian Core (Spectating Farmer)',
      desc: 'Spectating Farmer Harvesting Wheat & Transporting to Silo · 64 Articulated Chebyshev Humanoids',
      layout: 'unified',
      subsystem: 'tab-environment',
      camera: { pos: new THREE.Vector3(527, 18.5, 547), target: new THREE.Vector3(500, 6.0, 520) },
      action: () => {
        const farmer = (state.agents && state.agents.find(a => a.role === 'Farmer')) || (state.agents && state.agents[0]);
        if (farmer) {
          inspectAgent(farmer, true, false);
          if (state.three && state.three.camera && state.three.controls) {
            const camOffset = 38 / Math.SQRT2;
            state.three.camTargetPos = new THREE.Vector3(farmer.position.x - camOffset, 18.5, farmer.position.z - camOffset);
            state.three.camLookAtPos = new THREE.Vector3(farmer.position.x, 6.0, farmer.position.z);
          }
        }
      }
    },
    {
      step: 3,
      badge: 'PHASE 1.3 AGORA MARKET & DOUBLE-AUCTION',
      title: 'Agora Market & Double-Auction (Spectating Trader)',
      desc: 'Spectating Trader Bidding & Merchant Stalls · Continuous Midpoint Clearing · Lorenz Wealth Curve (Gini = 0.284)',
      layout: 'unified',
      subsystem: 'tab-economy',
      camera: { pos: new THREE.Vector3(550, 75, 760), target: new THREE.Vector3(550, 12, 650) },
      action: () => {
        const trader = (state.agents && state.agents.find(a => a.role === 'Trader')) || (state.agents && state.agents.find(a => a.role === 'Farmer'));
        if (trader) {
          inspectAgent(trader, true, false);
          if (state.three && state.three.camera && state.three.controls) {
            const camOffset = 38 / Math.SQRT2;
            state.three.camTargetPos = new THREE.Vector3(trader.position.x - camOffset, 18.5, trader.position.z - camOffset);
            state.three.camLookAtPos = new THREE.Vector3(trader.position.x, 6.0, trader.position.z);
          }
        }
      }
    },
    {
      step: 4,
      badge: 'PHASE 1.4 CIVIC ENGINEERING & FORGING',
      title: 'Civic Engineering & Forging (Spectating Builder & Crafter)',
      desc: 'Spectating Builder Constructing Portico & Crafter at Workshop · Verified Capability DAG · gVisor Sandbox',
      layout: 'unified',
      subsystem: 'tab-library',
      camera: { pos: new THREE.Vector3(500, 220, 840), target: new THREE.Vector3(500, 30, 500) },
      action: () => {
        const builder = (state.agents && (state.agents.find(a => a.role === 'Builder') || state.agents.find(a => a.role === 'Crafter'))) || (state.agents && state.agents[2]);
        if (builder) {
          inspectAgent(builder, true, false);
          if (state.three && state.three.camera && state.three.controls) {
            const camOffset = 38 / Math.SQRT2;
            state.three.camTargetPos = new THREE.Vector3(builder.position.x - camOffset, 18.5, builder.position.z - camOffset);
            state.three.camLookAtPos = new THREE.Vector3(builder.position.x, 6.0, builder.position.z);
          }
        }
      }
    },
    {
      step: 5,
      badge: 'PHASE 2.3 HEALTHCARE & COMMONS',
      title: 'Healthcare & Commons (Spectating Medic & Generalist)',
      desc: 'Spectating Medic at Hospital Trauma & Generalist at Conservatory · CVTArchive 5D Niche Matrix',
      layout: 'unified',
      subsystem: 'tab-cvt',
      camera: { pos: new THREE.Vector3(120, 90, 550), target: new THREE.Vector3(50, 15, 500) },
      action: () => {
        const medic = (state.agents && (state.agents.find(a => a.role === 'Medic') || state.agents.find(a => a.role === 'Generalist'))) || (state.agents && state.agents[3]);
        if (medic) {
          inspectAgent(medic, true, false);
          if (state.three && state.three.camera && state.three.controls) {
            const camOffset = 38 / Math.SQRT2;
            state.three.camTargetPos = new THREE.Vector3(medic.position.x - camOffset, 18.5, medic.position.z - camOffset);
            state.three.camLookAtPos = new THREE.Vector3(medic.position.x, 6.0, medic.position.z);
          }
        }
      }
    },
    {
      step: 6,
      badge: 'ARCHITECTURE MANDATE',
      title: 'Verified Capability DAG & STAGED LLM Route in Hazard Amber',
      desc: 'Zero Runtime Inference Evaluated · Deterministic Core in Emerald/Cyan · Staged LLM Route in Hazard Amber',
      layout: 'unified',
      subsystem: 'tab-pipeline',
      camera: { pos: new THREE.Vector3(500, 560, 1200), target: new THREE.Vector3(500, 0, 500) },
      action: () => {
        state.followingAgentId = null;
      }
    }
  ];

  // =========================================================================
  // 2. Core Bootstrapping & Lifecycle
  // =========================================================================
  async function initDashboard() {
    console.log('[EVOLZEN] Initializing 3D World Engine & Multi-Agent Cockpit...');

    // 1. Initialize UI Controls & Event Listeners
    initSimulationControls();
    initSpeedControls();
    initDroughtControl();
    initViewModeControls();
    initFullscreenWorldControl();
    initLayoutControls();
    initTabs();
    initSubsystemDock();
    initCinematicTourEngine();
    initKeyboardShortcuts();
    init2DMapCanvas();
    initCensusControls();

    // 2. Fetch Initial Server Data concurrently
    await Promise.all([
      fetchWorldMeta(),
      fetchEnvironmentState(),
      fetchEconomyState(),
      fetchRuleLibrary(),
      fetchArchitecturePipeline(),
      fetchAuditCertificate(),
      fetchAgentsRoster()
    ]);

    // 3. Initialize Three.js Engine & Volumetric Geometry
    initThreeEngine();

    // 4. Initial Telemetry Rendering Passes
    renderArchetypeDistribution();
    renderMaterialPalette();
    renderLocationPools();
    renderResourceChart();
    renderOrderBook();
    renderLorenzCurve();
    renderLivingManuals();
    renderVerifiedRulesList();
    renderRuleDag();
    renderCvtArchive();
    renderPipelineGraph();
    renderAuditChecklist();
    render2DWorldMap();
    renderPopulationCensus();

    // If agents are loaded, select the first agent for initial inspector display (docked, zero modal popups)
    if (state.agents && state.agents.length > 0) {
      inspectAgent(state.agents[0], false, false);
    }

    // 5. Automatically run simulation indefinitely on page load (calm, observable 1200ms pace)
    state.isRunning = true;
    state.simIntervalMs = 1200;
    state.simSpeedFactor = 1.0;
    if (state.timer) clearInterval(state.timer);
    state.timer = setInterval(() => stepSimulation(1), state.simIntervalMs);

    const playIcon = document.getElementById('playIcon');
    const playText = document.getElementById('playText');
    const btnPlay = document.getElementById('btnPlayPause');
    if (playIcon) playIcon.textContent = '⏸';
    if (playText) playText.textContent = 'PAUSE';
    if (btnPlay) {
      btnPlay.className = 'btn-tactile btn-tactile-cyan px-3.5 py-1.5 text-xs font-bold flex items-center gap-1.5 active';
    }

    fetch('/api/sim/autoplay', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: true, interval_ms: state.simIntervalMs })
    }).catch(() => {});

    console.log('[EVOLZEN] 3D World Engine & Interactive Telemetry fully operational.');
  }

  // Safe bootstrap
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
  } else {
    initDashboard();
  }

  // =========================================================================
  // 3. API Fetchers
  // =========================================================================
  async function fetchWorldMeta() {
    try {
      const res = await fetch('/api/world/meta');
      state.worldMeta = await res.json();
      if (state.three && state.three.scene && state.worldMeta.houses) {
        build3DHouses(state.three.scene);
      }
    } catch (e) {
      console.warn('Fallback: world/meta fetch failed, using default meta', e);
      state.worldMeta = {
        world: { extent_m: [1000, 1000, 40], total_chunks: 10378, total_voxels_reconciled: 340066304, water_mandate: 0 },
        houses: [],
        civic_structures: state.civicAnchors
      };
    }
  }

  async function fetchEnvironmentState() {
    try {
      let res = await fetch('/api/sim/state');
      if (!res.ok) res = await fetch('/api/environment/state');
      state.envState = await res.json();
      updateSimulationHUD();
    } catch (e) {
      console.warn('Failed to fetch sim state', e);
    }
  }

  async function fetchEconomyState() {
    try {
      const res = await fetch('/api/economy/state');
      state.economyState = await res.json();
      const gini = state.economyState.gini_coefficient || (state.economyState.lorenz_curve && state.economyState.lorenz_curve.gini) || 0.284;
      const elGini = document.getElementById('giniValue');
      const badgeGini = document.getElementById('badgeGini');
      if (elGini) elGini.textContent = Number(gini).toFixed(3);
      if (badgeGini) badgeGini.textContent = Number(gini).toFixed(3);
    } catch (e) {
      console.warn('Failed to fetch economy state', e);
    }
  }

  async function fetchRuleLibrary() {
    try {
      const res = await fetch('/api/library/rules');
      const data = await res.json();
      state.rules = data.rules || [];
      if (state.rules.length > 0 && !state.selectedRuleId) {
        state.selectedRuleId = state.rules[0].rule_id;
      }
    } catch (e) {
      console.warn('Failed to fetch rules', e);
    }
  }

  async function fetchArchitecturePipeline() {
    try {
      const res = await fetch('/api/architecture/pipeline');
      state.pipeline = await res.json();
    } catch (e) {
      console.warn('Failed to fetch architecture pipeline', e);
    }
  }

  async function fetchAuditCertificate() {
    try {
      const res = await fetch('/api/system/audit');
      state.auditData = await res.json();
    } catch (e) {
      console.warn('Failed to fetch audit certificate', e);
    }
  }

  async function fetchAgentsRoster() {
    try {
      const res = await fetch('/api/agents/roster');
      const data = await res.json();
      state.agents = data.agents || [];
      const badge = document.getElementById('activeAgentsBadge');
      if (badge) badge.textContent = `${state.agents.length} Active`;

      if (state.three && state.three.scene && state.agents.length > 0) {
        if (state.three.agentMeshes.length === 0) {
          build3DAgents(state.three.scene);
        } else {
          syncAgentMeshes();
        }
      }
    } catch (e) {
      console.warn('Failed to fetch agents roster', e);
    }
  }

  // =========================================================================
  // 4. Three.js 3D Engine Initialization
  // =========================================================================
  function initThreeEngine() {
    const container = document.getElementById('threeContainer');
    if (!container) return;

    try {
      const width = container.clientWidth || container.offsetWidth || window.innerWidth || 1200;
      const height = container.clientHeight || container.offsetHeight || Math.round(window.innerHeight * 0.76) || 600;

      // 1. Renderer: Optimized for Apple Silicon & WebKit GPUProcess Stability
      const renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: false,
        powerPreference: 'high-performance',
        stencil: false
      });
      renderer.setSize(width, height);
      const mobileViewport = width < 900;
      const pixelRatioCap = mobileViewport ? 1.75 : 2.25;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, pixelRatioCap));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.sortObjects = true;
      state.three.maxAnisotropy = renderer.capabilities.getMaxAnisotropy();
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFShadowMap;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.15;
      container.innerHTML = '';
      container.appendChild(renderer.domElement);
      state.three.renderer = renderer;

      // Robust WebGL Context Loss Recovery (guards against browser GPU process resets)
      renderer.domElement.addEventListener('webglcontextlost', (e) => {
        e.preventDefault();
        console.warn('WebGL context lost - holding animation loop to prevent crash');
        state.three.isContextLost = true;
      }, false);

      renderer.domElement.addEventListener('webglcontextrestored', () => {
        console.info('WebGL context restored - recovering 3D scene');
        state.three.isContextLost = false;
        initThreeEngine();
      }, false);

      // 2. Scene & Fog
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x020617);
      scene.fog = new THREE.FogExp2(0x020617, 0.00065);
      state.three.scene = scene;

      // 3. Perspective Camera
      const camera = new THREE.PerspectiveCamera(45, width / height, 1, 4000);
      camera.position.set(530, 85, 680);
      state.three.camera = camera;

      // 4. OrbitControls
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.target.set(500, 10, 520);
      controls.enableDamping = true;
      controls.dampingFactor = 0.06;
      controls.maxPolarAngle = Math.PI / 2.04;
      controls.minDistance = 15;
      controls.maxDistance = 2100;
      controls.addEventListener('start', () => {
        state.three.camTargetPos = null;
        state.three.camLookAtPos = null;
        state.followingAgentId = null;
      });
      state.three.controls = controls;

      // 5. Lighting Setup
      setupThreeLighting(scene);

      // 6. Volumetric World Geometry Construction
      build3DWorldGround(scene);
      build3DStreetLighting(scene);
      build3DWestFarmBelts(scene);
      build3DCentralPark(scene);
      build3DCivicAnchors(scene);
      build3DGVisorDome(scene);
      if (state.worldMeta && state.worldMeta.houses && state.worldMeta.houses.length > 0) {
        build3DHouses(scene);
      }
      if (state.agents && state.agents.length > 0) {
        build3DAgents(scene);
      }

      // Initialize 3D Floating Particle Systems (Zzz Sleep Particles & Crop Harvest Badges)
      initZzzParticleSystem(scene);
      initHarvestParticleSystem(scene);

      // 7. Event Listeners
      renderer.domElement.addEventListener('mousemove', onThreeMouseMove);
      renderer.domElement.addEventListener('click', onThreeClick);
      window.addEventListener('resize', handleThreeResize);

      // 8. Continuous Animation Loop
      animateThree();

      // 9. Attach ResizeObserver
      if (window.ResizeObserver) {
        const resizeObs = new ResizeObserver(() => handleThreeResize());
        resizeObs.observe(container);
      }

      handleThreeResize();
    } catch (err) {
      console.warn('WebGL init error, falling back to 2D canvas map:', err);
      state.viewMode = '2d';
      const btn2D = document.getElementById('btnView2D');
      if (btn2D) btn2D.click();
    }
  }

  function setupThreeLighting(scene) {
    const ambient = new THREE.AmbientLight(0x1e293b, 1.3);
    scene.add(ambient);
    state.three.ambientLight = ambient;

    const sun = new THREE.DirectionalLight(0xe0f2fe, 1.8);
    sun.position.set(350, 650, 450);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 2048;
    sun.shadow.mapSize.height = 2048;
    sun.shadow.bias = -0.00012;
    sun.shadow.normalBias = 0.02;
    sun.shadow.camera.near = 10;
    sun.shadow.camera.far = 1800;
    sun.shadow.camera.left = -650;
    sun.shadow.camera.right = 650;
    sun.shadow.camera.top = 650;
    sun.shadow.camera.bottom = -650;
    scene.add(sun);
    state.three.sunLight = sun;

    // Celestial Bodies: Orbiting Sun Mesh & Moon Mesh + Starfield
    const celestialGroup = new THREE.Group();
    state.three.celestialGroup = celestialGroup;

    // 1. Orbiting 3D Sun with Glowing Corona Halo
    const sunGeo = new THREE.SphereGeometry(18, 48, 32);
    const sunMat = new THREE.MeshBasicMaterial({ color: 0xffedd5 });
    const sunMesh = new THREE.Mesh(sunGeo, sunMat);
    sunMesh.position.set(350, 650, 450);

    const coronaGeo = new THREE.SphereGeometry(26, 32, 24);
    const coronaMat = new THREE.MeshBasicMaterial({
      color: 0xf59e0b,
      transparent: true,
      opacity: 0.38,
      wireframe: false
    });
    const sunCorona = new THREE.Mesh(coronaGeo, coronaMat);
    sunMesh.add(sunCorona);
    celestialGroup.add(sunMesh);
    state.three.sunMesh = sunMesh;
    state.three.sunCorona = sunCorona;

    // 2. Orbiting 3D Moon with Silver-Blue Disc & Soft Glow
    const moonGeo = new THREE.SphereGeometry(14, 48, 32);
    const moonMat = new THREE.MeshStandardMaterial({
      color: 0xe2e8f0,
      roughness: 0.85,
      metalness: 0.15,
      emissive: 0x38bdf8,
      emissiveIntensity: 0.45
    });
    const moonMesh = new THREE.Mesh(moonGeo, moonMat);
    moonMesh.position.set(650, -400, 550);
    celestialGroup.add(moonMesh);
    state.three.moonMesh = moonMesh;

    // 3. Starfield Dome with Twinkling Night Stars
    const starCount = 650;
    const starGeo = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2.0 * Math.PI;
      const phi = Math.acos(2.0 * v - 1.0) * 0.48; // Upper celestial dome
      const rad = 860 + Math.random() * 90;
      starPositions[i * 3] = 500 + rad * Math.sin(phi) * Math.cos(theta);
      starPositions[i * 3 + 1] = 120 + rad * Math.cos(phi);
      starPositions[i * 3 + 2] = 500 + rad * Math.sin(phi) * Math.sin(theta);
    }
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    const starMat = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 2.6,
      transparent: true,
      opacity: 0.0,
      sizeAttenuation: true
    });
    const starField = new THREE.Points(starGeo, starMat);
    celestialGroup.add(starField);
    state.three.starField = starField;
    state.three.starMat = starMat;

    scene.add(celestialGroup);

    // Hospital Red Cross Point Light (pulsing)
    const hospLight = new THREE.PointLight(0xef4444, 3.2, 120);
    hospLight.position.set(450, 32, 550);
    scene.add(hospLight);
    state.three.hospitalLight = hospLight;

    // Agora Market Amber Point Light
    const marketLight = new THREE.PointLight(0xf59e0b, 3.5, 130);
    marketLight.position.set(550, 22, 650);
    scene.add(marketLight);

    // Fire Station Siren Emergency Beacon
    const fireLight = new THREE.PointLight(0xdc2626, 2.8, 90);
    fireLight.position.set(550, 24, 450);
    scene.add(fireLight);
    state.three.fireSirenLight = fireLight;
  }

  function applyNightLighting() {
    state.three.scene.background.set(0x020617);
    state.three.scene.fog.color.set(0x020617);
    state.three.ambientLight.color.set(0x1e293b);
    state.three.ambientLight.intensity = 1.0;
    state.three.sunLight.intensity = 1.3;
    state.three.sunLight.color.set(0x38bdf8);

    if (state.three.streetLightsGroup) state.three.streetLightsGroup.visible = true;

    // Light up building windows
    state.three.windowMaterials.forEach(m => {
      m.emissive.setHex(0xfef08a);
      m.emissiveIntensity = 0.65;
    });
  }

  function applyDayLighting() {
    state.three.scene.background.set(0x081528);
    state.three.scene.fog.color.set(0x081528);
    state.three.ambientLight.color.set(0x94a3b8);
    state.three.ambientLight.intensity = 2.2;
    state.three.sunLight.intensity = 2.9;
    state.three.sunLight.color.set(0xffedd5);

    if (state.three.streetLightsGroup) state.three.streetLightsGroup.visible = false;

    // Cool reflective windows
    state.three.windowMaterials.forEach(m => {
      m.emissive.setHex(0x0e7490);
      m.emissiveIntensity = 0.25;
    });
  }

  function handleThreeResize(force = false) {
    const container = document.getElementById('threeContainer');
    if (!container || !state.three.renderer || !state.three.camera) return;
    const w = container.clientWidth || container.offsetWidth || window.innerWidth || 900;
    const h = container.clientHeight || container.offsetHeight || Math.round(window.innerHeight * 0.76) || 580;
    if (w <= 0 || h <= 0) return;
    if (!force && state.three.lastW === w && state.three.lastH === h) return;
    state.three.lastW = w;
    state.three.lastH = h;
    state.three.camera.aspect = w / h;
    state.three.camera.updateProjectionMatrix();
    const pixelRatioCap = w < 900 ? 1.75 : 2.25;
    state.three.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, pixelRatioCap));
    state.three.renderer.setSize(w, h, false);
  }

  // =========================================================================
  // 5. Volumetric 3D World Geometry Builder
  // =========================================================================

  // 1x1 km Terrain & Street Grid
  function build3DWorldGround(scene) {
    const groundGroup = new THREE.Group();
    state.three.groundGroup = groundGroup;

    // 1000m x 1000m ground plane
    const groundGeo = new THREE.PlaneGeometry(1000, 1000);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x090f1d,
      roughness: 0.90,
      metalness: 0.08
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(500, 0, 500);
    ground.receiveShadow = true;
    groundGroup.add(ground);

    // Street Network Ribbons (Asphalt + Sidewalks)
    const streetMat = new THREE.MeshStandardMaterial({ color: 0x182235, roughness: 0.72, metalness: 0.05 });
    const sidewalkMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.85 });
    const lineMat = new THREE.MeshBasicMaterial({ color: 0xfacc15, opacity: 0.75, transparent: true });

    const arteries = [
      { w: 1000, h: 12, x: 500, z: 500, isMain: true },
      { w: 12, h: 1000, x: 500, z: 500, isMain: true },
      { w: 10, h: 1000, x: 100, z: 500 },
      { w: 1000, h: 8, x: 500, z: 250 },
      { w: 1000, h: 8, x: 500, z: 750 },
      { w: 8, h: 1000, x: 300, z: 500 },
      { w: 8, h: 1000, x: 750, z: 500 },
      { w: 6, h: 1000, x: 450, z: 500 },
      { w: 6, h: 1000, x: 550, z: 500 },
      { w: 6, h: 1000, x: 650, z: 500 }
    ];

    arteries.forEach(a => {
      const roadGeo = new THREE.PlaneGeometry(a.w, a.h);
      const road = new THREE.Mesh(roadGeo, streetMat);
      road.rotation.x = -Math.PI / 2;
      road.position.set(a.x, 0.05, a.z);
      road.receiveShadow = true;
      groundGroup.add(road);

      const swW = a.w === 1000 ? 1000 : a.w + 2.5;
      const swH = a.h === 1000 ? 1000 : a.h + 2.5;
      const swGeo = new THREE.PlaneGeometry(swW, swH);
      const sw = new THREE.Mesh(swGeo, sidewalkMat);
      sw.rotation.x = -Math.PI / 2;
      sw.position.set(a.x, 0.03, a.z);
      sw.receiveShadow = true;
      groundGroup.add(sw);

      if (a.isMain) {
        const lineGeo = a.w === 1000 ? new THREE.PlaneGeometry(1000, 0.3) : new THREE.PlaneGeometry(0.3, 1000);
        const line = new THREE.Mesh(lineGeo, lineMat);
        line.rotation.x = -Math.PI / 2;
        line.position.set(a.x, 0.06, a.z);
        groundGroup.add(line);
      }
    });

    const boundaryGeo = new THREE.BoxGeometry(1004, 2.5, 1004);
    const boundaryMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, wireframe: true, transparent: true, opacity: 0.6 });
    const boundary = new THREE.Mesh(boundaryGeo, boundaryMat);
    boundary.position.set(500, 1.25, 500);
    groundGroup.add(boundary);

    scene.add(groundGroup);
  }

  // Street Lighting with Emissive Lantern Spheres (Optimized Geometry Sharing)
  function build3DStreetLighting(scene) {
    const lightsGroup = new THREE.Group();
    state.three.streetLightsGroup = lightsGroup;

    const poleMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.8, roughness: 0.2 });
    const lampMat = new THREE.MeshBasicMaterial({ color: 0xfef08a });
    const poleGeo = new THREE.CylinderGeometry(0.12, 0.16, 6.5, 6);
    const lanternGeo = new THREE.SphereGeometry(0.35, 8, 8);

    const lightPositions = [
      { x: 100, z: 250 }, { x: 100, z: 500 }, { x: 100, z: 750 },
      { x: 300, z: 250 }, { x: 300, z: 500 }, { x: 300, z: 750 },
      { x: 500, z: 250 }, { x: 500, z: 500 }, { x: 500, z: 750 },
      { x: 750, z: 250 }, { x: 750, z: 500 }, { x: 750, z: 750 },
      { x: 450, z: 450 }, { x: 450, z: 550 },
      { x: 550, z: 450 }, { x: 550, z: 650 },
      { x: 650, z: 550 }
    ];

    lightPositions.forEach(pos => {
      const pole = new THREE.Mesh(poleGeo, poleMat);
      pole.position.set(pos.x + 6, 3.25, pos.z + 6);
      lightsGroup.add(pole);

      const lantern = new THREE.Mesh(lanternGeo, lampMat);
      lantern.position.set(pos.x + 5.2, 6.4, pos.z + 5.2);
      lightsGroup.add(lantern);
    });

    scene.add(lightsGroup);
  }

  // West Farm Belts: 10 plots with Dynamic Lifecycle Crops, Fences, Barns & Silos
  function build3DWestFarmBelts(scene) {
    const farmsGroup = new THREE.Group();
    state.three.farmsGroup = farmsGroup;

    const soilMat = new THREE.MeshStandardMaterial({ color: 0x271e0c, roughness: 0.95 });

    // Distinct materials for 4 dynamic crop lifecycle stages:
    // 0: Stubble (0.15m), 1: Sprout (0.4m), 2: Growing (0.8m), 3: Golden Ripe (1.4m)
    const cropStageMats = {
      0: new THREE.MeshStandardMaterial({ color: 0x854d0e, roughness: 0.95 }),
      1: new THREE.MeshStandardMaterial({ color: 0x84cc16, roughness: 0.7, emissive: 0x14532d, emissiveIntensity: 0.1 }),
      2: new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.6, emissive: 0x15803d, emissiveIntensity: 0.15 }),
      3: new THREE.MeshStandardMaterial({ color: 0xfbbf24, roughness: 0.55, emissive: 0xd97706, emissiveIntensity: 0.25 })
    };
    state.three.cropStageMats = cropStageMats;
    state.three.cropPlots = [];

    const fenceMat = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.9 });
    const barnMat = new THREE.MeshStandardMaterial({ color: 0xb91c1c, roughness: 0.6 });
    const barnRoofMat = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.4 });
    const siloMat = new THREE.MeshStandardMaterial({ color: 0xcbd5e1, metalness: 0.85, roughness: 0.25 });

    const bedGeo = new THREE.BoxGeometry(82, 0.4, 76);
    const cropGeo = new THREE.BoxGeometry(72, 1.3, 4.5);
    const fenceGeo = new THREE.BoxGeometry(82, 0.8, 0.2);
    const barnGeo = new THREE.BoxGeometry(16, 9, 22);
    const barnRoofGeo = new THREE.ConeGeometry(14, 5, 4);
    const siloGeo = new THREE.CylinderGeometry(3.6, 3.6, 15, 14);
    const siloCapGeo = new THREE.ConeGeometry(3.8, 3.2, 14);

    for (let b = 0; b < 10; b++) {
      const z = b * 100 + 50;

      // 1. Agricultural plot bed
      const bed = new THREE.Mesh(bedGeo, soilMat);
      bed.position.set(48, 0.2, z);
      bed.receiveShadow = true;
      farmsGroup.add(bed);

      // 2. Dynamic crop rows
      const plotRows = [];
      for (let r = 0; r < 6; r++) {
        const crop = new THREE.Mesh(cropGeo, cropStageMats[3]);
        crop.position.set(48, 0.85, z - 28 + r * 11);
        crop.castShadow = true;
        crop.receiveShadow = true;
        farmsGroup.add(crop);
        plotRows.push(crop);
      }

      state.three.cropPlots.push({
        plotIndex: b,
        center: new THREE.Vector3(48, 0.85, z),
        rows: plotRows,
        currentStage: 3,
        currentScaleY: 1.08,
        targetScaleY: 1.08,
        progress: 100
      });

      // 3. Perimeter fences
      const fNorth = new THREE.Mesh(fenceGeo, fenceMat);
      fNorth.position.set(48, 0.6, z - 38);
      const fSouth = new THREE.Mesh(fenceGeo, fenceMat);
      fSouth.position.set(48, 0.6, z + 38);
      farmsGroup.add(fNorth);
      farmsGroup.add(fSouth);

      // 4. Rustic Red Farm Barn
      const barn = new THREE.Mesh(barnGeo, barnMat);
      barn.position.set(90, 4.5, z);
      barn.castShadow = true;
      barn.receiveShadow = true;

      const barnRoof = new THREE.Mesh(barnRoofGeo, barnRoofMat);
      barnRoof.rotation.y = Math.PI / 4;
      barnRoof.position.set(0, 7, 0);
      barn.add(barnRoof);
      farmsGroup.add(barn);

      // 5. Cylindrical Communal Grain Silo
      const silo = new THREE.Mesh(siloGeo, siloMat);
      silo.position.set(90, 7.5, z + 18);
      silo.castShadow = true;

      const siloCap = new THREE.Mesh(siloCapGeo, siloMat);
      siloCap.position.set(0, 9.1, 0);
      silo.add(siloCap);
      farmsGroup.add(silo);
    }

    scene.add(farmsGroup);
  }

  // Central Park with Lush Greenery & Victorian Glass Conservatory
  function build3DCentralPark(scene) {
    const parkGroup = new THREE.Group();

    const parkMat = new THREE.MeshStandardMaterial({ color: 0x065f46, roughness: 0.88 });
    const parkGeo = new THREE.BoxGeometry(100, 0.5, 100);
    const park = new THREE.Mesh(parkGeo, parkMat);
    park.position.set(500, 0.25, 500);
    park.receiveShadow = true;
    parkGroup.add(park);

    const pathMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.9 });
    const pathGeo = new THREE.PlaneGeometry(130, 4);
    const path1 = new THREE.Mesh(pathGeo, pathMat);
    path1.rotation.x = -Math.PI / 2;
    path1.rotation.z = Math.PI / 4;
    path1.position.set(500, 0.28, 500);
    const path2 = new THREE.Mesh(pathGeo, pathMat);
    path2.rotation.x = -Math.PI / 2;
    path2.rotation.z = -Math.PI / 4;
    path2.position.set(500, 0.28, 500);
    parkGroup.add(path1);
    parkGroup.add(path2);

    const trunkMat = new THREE.MeshStandardMaterial({ color: 0x713f12, roughness: 0.9 });
    const leafMat = new THREE.MeshStandardMaterial({ color: 0x15803d, roughness: 0.65 });
    const trunkGeo = new THREE.CylinderGeometry(0.5, 0.7, 4.5, 5);
    const crownGeo = new THREE.DodecahedronGeometry(2.6, 1);

    for (let t = 0; t < 28; t++) {
      const angle = (t / 28) * Math.PI * 2;
      const radius = 22 + (t % 3) * 14;
      const tx = 500 + Math.cos(angle) * radius;
      const tz = 500 + Math.sin(angle) * radius;

      const trunk = new THREE.Mesh(trunkGeo, trunkMat);
      trunk.position.set(tx, 2.3, tz);
      parkGroup.add(trunk);

      const crown = new THREE.Mesh(crownGeo, leafMat);
      crown.position.set(tx, 5.8, tz);
      crown.castShadow = true;
      parkGroup.add(crown);
    }

    const glassMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.45,
      roughness: 0.1,
      metalness: 0.7
    });
    const frameMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8, roughness: 0.2 });

    const consBase = new THREE.Mesh(new THREE.CylinderGeometry(11, 11, 4, 8), frameMat);
    consBase.position.set(500, 2.0, 500);
    parkGroup.add(consBase);

    const consDome = new THREE.Mesh(new THREE.SphereGeometry(11, 14, 10, 0, Math.PI * 2, 0, Math.PI * 0.5), glassMat);
    consDome.position.set(500, 4.0, 500);
    parkGroup.add(consDome);

    scene.add(parkGroup);
  }

  // 3D Floating Building Label Sprite Generator (High-DPI Neumorphic Billboard)
  function createBuildingLabelSprite(title, icon, colorHex, subtext) {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // 1. Neumorphic Plaque Background
    ctx.fillStyle = 'rgba(5, 9, 18, 0.94)';
    ctx.strokeStyle = colorHex || '#38bdf8';
    ctx.lineWidth = 4.5;
    drawRoundedRect(ctx, 4, 4, 504, 120, 22, true, true);

    // Inner subtle glow border
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 1.5;
    drawRoundedRect(ctx, 8, 8, 496, 112, 18, false, true);

    // 2. Icon + Title Header
    ctx.font = 'bold 27px "Inter", sans-serif';
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`${icon ? icon + '  ' : ''}${title}`, 256, 42);

    // Divider
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(32, 68);
    ctx.lineTo(480, 68);
    ctx.stroke();

    // 3. Subtext
    ctx.font = 'bold 16px "Fira Code", monospace';
    ctx.fillStyle = colorHex || '#38bdf8';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(subtext || 'Civic Infrastructure Facility', 256, 94);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.scale.set(18.0, 4.5, 1.0);
    sprite.userData = { canvas, texture, colorHex, isBuildingLabel: true };
    return sprite;
  }

  // Civic Anchors: Hospital, Agora, School, Municipal, Fire Station, Silos, Workshops
  function build3DCivicAnchors(scene) {
    const civicGroup = new THREE.Group();
    state.three.civicGroup = civicGroup;

    state.civicAnchors.forEach(c => {
      if (c.isZone) return;

      const size = c.size || 36;
      const height = c.height || 20;

      const bldgGeo = new THREE.BoxGeometry(size, height, size);
      const bldgMat = new THREE.MeshStandardMaterial({
        color: c.color,
        roughness: 0.35,
        metalness: 0.3
      });
      const bldg = new THREE.Mesh(bldgGeo, bldgMat);
      bldg.position.set(c.x, height / 2, c.z);
      bldg.castShadow = true;
      bldg.receiveShadow = true;
      bldg.userData = { isCivic: true, data: c };

      civicGroup.add(bldg);
      state.three.civicMeshes.push(bldg);
      state.three.clickableMeshes.push(bldg);

      const entranceGeo = new THREE.BoxGeometry(size * 0.35, 5, 4);
      const entranceMat = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.2 });
      const entrance = new THREE.Mesh(entranceGeo, entranceMat);
      entrance.position.set(0, -height / 2 + 2.5, size / 2 + 1.8);
      bldg.add(entrance);

      // 1. HOSPITAL: Rooftop Pulsing Red Cross
      if (c.id === 'hospital') {
        const crossGroup = new THREE.Group();
        const crossH = new THREE.BoxGeometry(9, 2.4, 2.4);
        const crossV = new THREE.BoxGeometry(2.4, 9, 2.4);
        const crossMat = new THREE.MeshStandardMaterial({
          color: 0xef4444,
          emissive: 0xef4444,
          emissiveIntensity: 0.95,
          roughness: 0.2
        });
        crossGroup.add(new THREE.Mesh(crossH, crossMat));
        crossGroup.add(new THREE.Mesh(crossV, crossMat));
        crossGroup.position.set(c.x, height + 5.5, c.z);
        civicGroup.add(crossGroup);
        state.three.hospitalBeacon = crossGroup;
      }

      // 2. AGORA MARKET: Striped Awnings, Commodity Crates & Holographic Ring
      if (c.id === 'market') {
        const awningGroup = new THREE.Group();
        const redCloth = new THREE.MeshStandardMaterial({ color: 0xdc2626, roughness: 0.7 });
        const whiteCloth = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.7 });
        const stripGeo = new THREE.BoxGeometry(4, 1.2, size + 6);

        for (let s = -size / 2; s < size / 2; s += 4) {
          const mat = Math.abs(s / 4) % 2 === 0 ? redCloth : whiteCloth;
          const strip = new THREE.Mesh(stripGeo, mat);
          strip.position.set(s + 2, height / 2 + 1, 0);
          awningGroup.add(strip);
        }
        bldg.add(awningGroup);

        const crateMat = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.8 });
        const stoneCrateMat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.8 });
        const crateGeo = new THREE.BoxGeometry(3, 3, 3);
        for (let cr = 0; cr < 8; cr++) {
          const crate = new THREE.Mesh(crateGeo, cr % 2 === 0 ? crateMat : stoneCrateMat);
          crate.position.set(c.x + size / 2 + 5, 1.5, c.z - 15 + cr * 4.5);
          crate.castShadow = true;
          civicGroup.add(crate);
        }

        const ringGeo = new THREE.TorusGeometry(size * 0.7, 0.9, 16, 32);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, wireframe: true });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 2;
        ring.position.set(c.x, height + 8, c.z);
        civicGroup.add(ring);
        state.three.agoraRing = ring;
      }

      // 3. SCHOOL: Clock Tower & Belfry
      if (c.id === 'school') {
        const towerGeo = new THREE.BoxGeometry(10, 16, 10);
        const towerMat = new THREE.MeshStandardMaterial({ color: 0x991b1b });
        const tower = new THREE.Mesh(towerGeo, towerMat);
        tower.position.set(0, height / 2 + 8, 0);
        bldg.add(tower);

        const clockMat = new THREE.MeshBasicMaterial({ color: 0xfacc15 });
        const clockMesh = new THREE.Mesh(new THREE.CircleGeometry(2.5, 16), clockMat);
        clockMesh.position.set(0, 3, 5.1);
        tower.add(clockMesh);

        const spire = new THREE.Mesh(new THREE.ConeGeometry(6, 9, 4), new THREE.MeshStandardMaterial({ color: 0x334155 }));
        spire.rotation.y = Math.PI / 4;
        spire.position.set(0, 12, 0);
        tower.add(spire);
      }

      // 4. MUNICIPAL OFFICE: Colonnade Columns & Pediment
      if (c.id === 'municipal') {
        const colMat = new THREE.MeshStandardMaterial({ color: 0xf1f5f9, roughness: 0.3 });
        const columnGeo = new THREE.CylinderGeometry(0.9, 0.9, height, 10);
        for (let col = -size / 2 + 4; col <= size / 2 - 4; col += 7) {
          const column = new THREE.Mesh(columnGeo, colMat);
          column.position.set(col, 0, size / 2 + 3);
          column.castShadow = true;
          bldg.add(column);
        }
        const pediment = new THREE.Mesh(new THREE.ConeGeometry(size * 0.6, 6, 3), colMat);
        pediment.rotation.z = Math.PI;
        pediment.rotation.y = Math.PI / 2;
        pediment.position.set(0, height / 2 + 3, size / 2 + 2);
        bldg.add(pediment);
      }

      // 5. FIRE STATION: Siren Beacon & Hose Drying Tower
      if (c.id === 'fire') {
        const hoseTower = new THREE.Mesh(new THREE.BoxGeometry(8, 22, 8), new THREE.MeshStandardMaterial({ color: 0x991b1b }));
        hoseTower.position.set(size / 2 - 5, height / 2 + 11, -size / 2 + 5);
        bldg.add(hoseTower);

        const sirenDome = new THREE.Mesh(new THREE.SphereGeometry(1.6, 10, 6), new THREE.MeshBasicMaterial({ color: 0xdc2626 }));
        sirenDome.position.set(0, 12, 0);
        hoseTower.add(sirenDome);
      }

      // 6. COMMUNAL GRANARY SILOS: Cylindrical Towers & Metal Domes
      if (c.id === 'silo') {
        const siloMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.85, roughness: 0.25 });
        const domeMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.9, roughness: 0.2 });
        const siloCylGeo = new THREE.CylinderGeometry(5.0, 5.0, height, 14);
        const siloCapGeo = new THREE.SphereGeometry(5.0, 14, 8, 0, Math.PI * 2, 0, Math.PI * 0.5);

        [-9, 0, 9].forEach(ox => {
          const cylinder = new THREE.Mesh(siloCylGeo, siloMat);
          cylinder.position.set(ox, 0, 0);
          cylinder.castShadow = true;
          bldg.add(cylinder);

          const cap = new THREE.Mesh(siloCapGeo, domeMat);
          cap.position.set(ox, height / 2, 0);
          bldg.add(cap);
        });
      }

      // 7. TIMBER & QUARRY WORKSHOPS: Yard Storage
      if (c.id === 'workshop') {
        const stoneMat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.9 });
        const woodMat = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.8 });
        const blockGeo = new THREE.BoxGeometry(3.5, 3.5, 3.5);
        for (let q = 0; q < 6; q++) {
          const block = new THREE.Mesh(blockGeo, q % 2 === 0 ? stoneMat : woodMat);
          block.position.set(c.x + size / 2 + 5, 1.8, c.z - 10 + q * 4.5);
          block.castShadow = true;
          civicGroup.add(block);
        }
      }

      // Floating 3D Building Label Plaque
      const labelSprite = createBuildingLabelSprite(c.name, c.icon, c.hex || '#38bdf8', c.desc);
      let labelY = height + 10;
      if (c.id === 'hospital') labelY = height + 16;
      if (c.id === 'school') labelY = height + 28;
      if (c.id === 'fire') labelY = height + 26;
      if (c.id === 'silo') labelY = height + 16;
      if (c.id === 'market') labelY = height + 18;
      if (c.id === 'municipal') labelY = height + 16;
      labelSprite.position.set(c.x, labelY, c.z);
      civicGroup.add(labelSprite);
    });

    // 8. Add District Wayfinding Plaques
    const districtMarkers = [
      { name: 'West Farm Belt', icon: '🌾', x: 60, y: 22, z: 500, color: '#10b981', desc: '10 Agrarian Plots · Primary Wheat Harvest' },
      { name: 'Central Park Conservatory', icon: '🌲', x: 500, y: 26, z: 500, color: '#22c55e', desc: 'Public Reserve & Victorian Greenhouse' },
      { name: 'North Residential District', icon: '🏡', x: 260, y: 18, z: 180, color: '#facc15', desc: 'Ranch & Bungalow Single-Floor Dwellings' },
      { name: 'East Colonial Enclave', icon: '🏡', x: 740, y: 20, z: 720, color: '#ef4444', desc: 'Colonial & McMansion Two-Story Estates' },
      { name: 'South Modern Terraces', icon: '🏡', x: 720, y: 18, z: 280, color: '#38bdf8', desc: 'Contemporary Flat Concrete & Glass Homes' }
    ];

    districtMarkers.forEach(dm => {
      const dmSprite = createBuildingLabelSprite(dm.name, dm.icon, dm.color, dm.desc);
      dmSprite.position.set(dm.x, dm.y, dm.z);
      dmSprite.scale.set(22.0, 5.5, 1.0);
      civicGroup.add(dmSprite);
    });

    scene.add(civicGroup);
  }

  // 345 Volumetric Houses across 5 Archetypes (Optimized Geometry & Material Caching)
  const houseAssets = {
    initialized: false,
    bodyGeos: {},
    roofGeos: {},
    mats: {},
    doorGeo: null,
    ribbonWinGeo: null,
    winGeo1: null,
    winGeo2: null,
    winGeoDef: null,
    chimGeo1: null,
    chimGeo2: null,
    chimGeoDef: null
  };

  function getHouseAssets() {
    if (houseAssets.initialized) return houseAssets;

    const archDims = {
      0: { w: 14, h: 4.0, d: 10 },
      1: { w: 12, h: 7.2, d: 14 },
      2: { w: 16, h: 8.5, d: 18 },
      3: { w: 8, h: 4.2, d: 10 },
      4: { w: 12, h: 6.8, d: 14 }
    };

    for (let id = 0; id <= 4; id++) {
      const dim = archDims[id];
      houseAssets.bodyGeos[id] = new THREE.BoxGeometry(dim.w, dim.h, dim.d);

      if (id === 4) {
        houseAssets.roofGeos[id] = new THREE.BoxGeometry(dim.w + 1.2, 0.45, dim.d + 1.2);
      } else if (id === 1) {
        houseAssets.roofGeos[id] = new THREE.ConeGeometry(Math.max(dim.w, dim.d) * 0.72, 3.2, 8);
      } else if (id === 2) {
        houseAssets.roofGeos[id] = new THREE.ConeGeometry(Math.max(dim.w, dim.d) * 0.75, 3.6, 8);
      } else {
        houseAssets.roofGeos[id] = new THREE.ConeGeometry(Math.max(dim.w, dim.d) * 0.68, 2.4, 8);
      }

      const arch = state.archetypes[id] || state.archetypes[0];
      houseAssets.mats[`body_${id}`] = new THREE.MeshStandardMaterial({
        color: arch.color,
        roughness: 0.65,
        metalness: 0.08
      });
      houseAssets.mats[`roof_${id}`] = new THREE.MeshStandardMaterial({
        color: arch.roofColor,
        roughness: id === 4 ? 0.5 : 0.75
      });
    }

    houseAssets.doorGeo = new THREE.BoxGeometry(1.4, 2.4, 0.15);
    houseAssets.ribbonWinGeo = new THREE.BoxGeometry(12 * 0.75, 1.4, 0.2);
    houseAssets.winGeo1 = new THREE.BoxGeometry(1.6, 1.4, 0.15);
    houseAssets.winGeo2 = new THREE.BoxGeometry(1.8, 1.6, 0.15);
    houseAssets.winGeoDef = new THREE.BoxGeometry(1.6, 1.3, 0.15);

    houseAssets.chimGeo1 = new THREE.BoxGeometry(1.2, 2.8, 1.2);
    houseAssets.chimGeo2 = new THREE.BoxGeometry(1.6, 3.8, 1.6);
    houseAssets.chimGeoDef = new THREE.BoxGeometry(1.0, 2.2, 1.0);

    const windowMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: state.isNightMode ? 0xfef08a : 0x0e7490,
      emissiveIntensity: state.isNightMode ? 0.65 : 0.25,
      roughness: 0.15,
      metalness: 0.85
    });
    houseAssets.mats.window = windowMat;
    state.three.windowMaterials.push(windowMat);

    houseAssets.mats.door = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.8 });
    houseAssets.mats.chimney = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.9 });

    houseAssets.initialized = true;
    return houseAssets;
  }

  function build3DHouses(scene) {
    if (!scene) scene = state.three.scene;
    if (!scene || !state.worldMeta || !state.worldMeta.houses) return;

    if (state.three.housesGroup) {
      scene.remove(state.three.housesGroup);
      state.three.houseMeshes = [];
      state.three.windowMaterials = [];
      state.three.housePositions = {};
    }

    const housesGroup = new THREE.Group();
    state.three.housesGroup = housesGroup;
    const houses = state.worldMeta.houses;
    const assets = getHouseAssets();

    houses.forEach((h, idx) => {
      const [x, z, w, d, archId] = h;
      const arch = state.archetypes[archId] || state.archetypes[0];
      const hHeight = arch.height || 4.0;

      const bodyGeo = assets.bodyGeos[archId] || assets.bodyGeos[0];
      const bodyMat = assets.mats[`body_${archId}`] || assets.mats.body_0;
      const houseMesh = new THREE.Mesh(bodyGeo, bodyMat);
      houseMesh.position.set(x + w / 2, hHeight / 2, z + d / 2);
      houseMesh.castShadow = true;
      houseMesh.receiveShadow = true;

      const roofGeo = assets.roofGeos[archId] || assets.roofGeos[0];
      const roofMat = assets.mats[`roof_${archId}`] || assets.mats.roof_0;
      const roof = new THREE.Mesh(roofGeo, roofMat);

      // 1. Architectural Roof Design
      if (archId === 4) {
        roof.position.set(0, hHeight / 2 + 0.22, 0);
        houseMesh.add(roof);

        const ribbonWin = new THREE.Mesh(assets.ribbonWinGeo, assets.mats.window);
        ribbonWin.position.set(0, 0.8, d / 2 + 0.1);
        houseMesh.add(ribbonWin);
      } else if (archId === 1) {
        roof.rotation.y = Math.PI / 4;
        roof.position.set(0, hHeight / 2 + 1.6, 0);
        houseMesh.add(roof);

        [-w / 3, w / 3].forEach(cx => {
          const chim = new THREE.Mesh(assets.chimGeo1, assets.mats.chimney);
          chim.position.set(cx, hHeight / 2 + 2.2, 0);
          houseMesh.add(chim);
        });

        [-w / 4, w / 4].forEach(wx => {
          [0.8, -1.2].forEach(wy => {
            const win = new THREE.Mesh(assets.winGeo1, assets.mats.window);
            win.position.set(wx, wy, d / 2 + 0.08);
            houseMesh.add(win);
          });
        });
      } else if (archId === 2) {
        roof.rotation.y = Math.PI / 4;
        roof.position.set(0, hHeight / 2 + 1.8, 0);
        houseMesh.add(roof);

        const chim = new THREE.Mesh(assets.chimGeo2, assets.mats.chimney);
        chim.position.set(-w / 2 + 1.2, hHeight / 2 + 2.2, 0);
        houseMesh.add(chim);

        [-w / 3, 0, w / 3].forEach(wx => {
          [1.0, -1.4].forEach(wy => {
            const win = new THREE.Mesh(assets.winGeo2, assets.mats.window);
            win.position.set(wx, wy, d / 2 + 0.08);
            houseMesh.add(win);
          });
        });
      } else {
        roof.rotation.y = Math.PI / 4;
        roof.position.set(0, hHeight / 2 + 1.2, 0);
        houseMesh.add(roof);

        const chim = new THREE.Mesh(assets.chimGeoDef, assets.mats.chimney);
        chim.position.set(w / 3, hHeight / 2 + 1.4, 0);
        houseMesh.add(chim);

        [-w / 3, w / 3].forEach(wx => {
          const win = new THREE.Mesh(assets.winGeoDef, assets.mats.window);
          win.position.set(wx, 0.2, d / 2 + 0.08);
          houseMesh.add(win);
        });
      }

      const door = new THREE.Mesh(assets.doorGeo, assets.mats.door);
      door.position.set(0, -hHeight / 2 + 1.2, d / 2 + 0.08);
      houseMesh.add(door);

      houseMesh.userData = {
        isHouse: true,
        index: idx + 1,
        x, z, w, d, archId,
        arch
      };

      // Rooftop / chimney emission point for 3D Zzz particle billboards
      state.three.housePositions[idx + 1] = new THREE.Vector3(x + w / 2, hHeight + 2.2, z + d / 2);

      housesGroup.add(houseMesh);
      state.three.houseMeshes.push(houseMesh);
      state.three.clickableMeshes.push(houseMesh);
    });

    scene.add(housesGroup);
  }

  // gVisor Sandbox Containment Shield
  function build3DGVisorDome(scene) {
    const shieldGeo = new THREE.IcosahedronGeometry(180, 2);
    const shieldMat = new THREE.MeshBasicMaterial({
      color: 0x8b5cf6,
      wireframe: true,
      transparent: true,
      opacity: 0.22
    });
    const shield = new THREE.Mesh(shieldGeo, shieldMat);
    shield.position.set(500, 30, 500);
    scene.add(shield);
    state.three.shieldMesh = shield;
  }

  // =========================================================================
  // 6. Procedural Humanoid Population (64 Articulated Figures)
  // =========================================================================
  function build3DAgents(scene) {
    if (!scene) scene = state.three.scene;
    if (!scene || !state.agents || state.agents.length === 0) return;

    if (state.three.agentsGroup) {
      scene.remove(state.three.agentsGroup);
      state.three.agentMeshes = [];
    }

    const agentsGroup = new THREE.Group();
    state.three.agentsGroup = agentsGroup;

    state.agents.forEach((agentData, idx) => {
      const avatar = createHumanoidAvatar(agentData, idx);
      agentsGroup.add(avatar.group);
      state.three.agentMeshes.push(avatar);

      avatar.group.traverse(child => {
        if (child.isMesh) {
          child.userData = { isAgent: true, data: agentData, avatarWrapper: avatar };
          state.three.clickableMeshes.push(child);
        }
      });
    });

    scene.add(agentsGroup);
  }

  // Shared Humanoid Geometry & Material Assets Pool (Reduces 1,000+ GPU buffers to ~20)
  const humanoidAssets = {
    initialized: false,
    geos: {},
    mats: {}
  };

  function getHumanoidAssets() {
    if (humanoidAssets.initialized) return humanoidAssets;

    const g = humanoidAssets.geos;
    g.torso = new THREE.BoxGeometry(0.65, 0.75, 0.38);
    g.belt = new THREE.BoxGeometry(0.67, 0.12, 0.40);
    g.neck = new THREE.CylinderGeometry(0.12, 0.14, 0.16, 12);
    g.head = new THREE.SphereGeometry(0.28, 16, 12);
    g.eye = new THREE.SphereGeometry(0.04, 8, 8);

    const armGeo = new THREE.BoxGeometry(0.18, 0.65, 0.18);
    armGeo.translate(0, -0.28, 0);
    g.arm = armGeo;

    const legGeo = new THREE.BoxGeometry(0.22, 0.65, 0.22);
    legGeo.translate(0, -0.32, 0);
    g.leg = legGeo;

    g.hand = new THREE.SphereGeometry(0.09, 12, 8);
    g.boot = new THREE.BoxGeometry(0.24, 0.14, 0.32);
    g.ring = new THREE.RingGeometry(0.85, 1.15, 32);

    // Hats and accessories
    g.strawBrim = new THREE.CylinderGeometry(0.65, 0.65, 0.04, 12);
    g.strawCrown = new THREE.CylinderGeometry(0.28, 0.35, 0.22, 12);
    g.strawBand = new THREE.CylinderGeometry(0.36, 0.36, 0.05, 12);
    g.hardhat = new THREE.SphereGeometry(0.32, 10, 8, 0, Math.PI * 2, 0, Math.PI * 0.55);
    g.hardhatBrim = new THREE.CylinderGeometry(0.38, 0.38, 0.04, 12);
    g.medicCap = new THREE.CylinderGeometry(0.30, 0.30, 0.18, 12);
    g.medicCrossH = new THREE.BoxGeometry(0.14, 0.04, 0.02);
    g.medicCrossV = new THREE.BoxGeometry(0.04, 0.14, 0.02);
    g.traderBeret = new THREE.CylinderGeometry(0.38, 0.22, 0.12, 12);
    g.crafterStrap = new THREE.CylinderGeometry(0.30, 0.30, 0.05, 12);
    g.crafterLens = new THREE.CylinderGeometry(0.08, 0.08, 0.08, 8);
    g.crafterGlass = new THREE.CircleGeometry(0.07, 8);
    g.genCap = new THREE.SphereGeometry(0.30, 10, 6, 0, Math.PI * 2, 0, Math.PI * 0.5);

    // Props
    g.pitchforkShaft = new THREE.CylinderGeometry(0.03, 0.03, 1.4, 6);
    g.pitchforkBar = new THREE.BoxGeometry(0.24, 0.03, 0.03);
    g.pitchforkTine = new THREE.CylinderGeometry(0.015, 0.005, 0.35, 4);
    g.hammerShaft = new THREE.CylinderGeometry(0.035, 0.035, 0.6, 6);
    g.hammerHead = new THREE.BoxGeometry(0.12, 0.10, 0.22);
    g.medkitBox = new THREE.BoxGeometry(0.28, 0.22, 0.14);
    g.pouchBag = new THREE.SphereGeometry(0.13, 6, 6);
    g.pouchCoin = new THREE.CylinderGeometry(0.05, 0.05, 0.02, 6);
    g.wrenchStem = new THREE.BoxGeometry(0.04, 0.45, 0.02);
    g.wrenchJaw = new THREE.BoxGeometry(0.12, 0.08, 0.03);
    g.satchel = new THREE.BoxGeometry(0.24, 0.20, 0.08);

    // Materials
    const m = humanoidAssets.mats;
    const skinTones = [0xfcd5b5, 0xe0ac69, 0xc68642, 0x8d5524, 0xd4a373];
    m.skin = skinTones.map(hex => new THREE.MeshStandardMaterial({ color: hex, roughness: 0.65 }));
    m.dark = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.85 });
    m.metal = new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.35, metalness: 0.8 });
    m.eye = new THREE.MeshBasicMaterial({ color: 0x0f172a });
    m.boot = new THREE.MeshStandardMaterial({ color: 0x0f172a, roughness: 0.9 });
    m.wood = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.9 });
    m.straw = new THREE.MeshStandardMaterial({ color: 0xd97706, roughness: 0.85 });
    m.strawBand = new THREE.MeshBasicMaterial({ color: 0x78350f });
    m.hardhat = new THREE.MeshStandardMaterial({ color: 0xfacc15, roughness: 0.3, metalness: 0.1 });
    m.medicCap = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.4 });
    m.redBasic = new THREE.MeshBasicMaterial({ color: 0xef4444 });
    m.beret = new THREE.MeshStandardMaterial({ color: 0x1e1b4b, roughness: 0.8 });
    m.brass = new THREE.MeshStandardMaterial({ color: 0xd97706, metalness: 0.8, roughness: 0.2 });
    m.cyanBasic = new THREE.MeshBasicMaterial({ color: 0x06b6d4 });
    m.genCap = new THREE.MeshStandardMaterial({ color: 0x0284c7 });
    m.ring = new THREE.MeshBasicMaterial({ color: 0x06b6d4, side: THREE.DoubleSide, transparent: true, opacity: 0.6 });

    m.roles = {};
    Object.keys(state.roles).forEach(r => {
      const cfg = state.roles[r];
      m.roles[r] = new THREE.MeshStandardMaterial({
        color: new THREE.Color(cfg.colorHex || cfg.color),
        roughness: 0.45,
        metalness: 0.1
      });
    });

    humanoidAssets.initialized = true;
    return humanoidAssets;
  }

  function createHumanoidAvatar(agentData, index) {
    const assets = getHumanoidAssets();
    const group = new THREE.Group();
    group.name = `agent_${agentData.id}`;
    group.position.set(agentData.position.x, 0, agentData.position.z);
    group.scale.set(3.5, 3.5, 3.5);
    group.userData = { isAgent: true, data: agentData };

    const roleName = agentData.role || 'Farmer';
    const roleMat = assets.mats.roles[roleName] || assets.mats.roles['Farmer'] || assets.mats.dark;
    const skinMat = assets.mats.skin[index % assets.mats.skin.length];

    // 1. Torso Group
    const torsoGroup = new THREE.Group();
    const baseTorsoY = 1.0;
    torsoGroup.position.y = baseTorsoY;

    const torsoMesh = new THREE.Mesh(assets.geos.torso, roleMat);
    torsoMesh.castShadow = true;
    torsoMesh.receiveShadow = true;
    torsoGroup.add(torsoMesh);

    const beltMesh = new THREE.Mesh(assets.geos.belt, assets.mats.dark);
    beltMesh.position.y = -0.32;
    torsoGroup.add(beltMesh);

    const neckMesh = new THREE.Mesh(assets.geos.neck, skinMat);
    neckMesh.position.y = 0.45;
    torsoGroup.add(neckMesh);

    // 2. Head
    const headMesh = new THREE.Mesh(assets.geos.head, skinMat);
    headMesh.position.y = 0.68;
    torsoGroup.add(headMesh);

    // Eyes
    const eyeL = new THREE.Mesh(assets.geos.eye, assets.mats.eye);
    eyeL.position.set(-0.09, 0.72, 0.25);
    const eyeR = new THREE.Mesh(assets.geos.eye, assets.mats.eye);
    eyeR.position.set(0.09, 0.72, 0.25);
    torsoGroup.add(eyeL);
    torsoGroup.add(eyeR);

    // Role-Specific Hat
    if (roleName === 'Farmer') {
      const hatGroup = new THREE.Group();
      const brim = new THREE.Mesh(assets.geos.strawBrim, assets.mats.straw);
      hatGroup.add(brim);
      const crown = new THREE.Mesh(assets.geos.strawCrown, assets.mats.straw);
      crown.position.y = 0.11;
      hatGroup.add(crown);
      const band = new THREE.Mesh(assets.geos.strawBand, assets.mats.strawBand);
      band.position.y = 0.03;
      hatGroup.add(band);
      hatGroup.position.set(0, 0.94, 0);
      torsoGroup.add(hatGroup);
    } else if (roleName === 'Builder') {
      const hardhat = new THREE.Mesh(assets.geos.hardhat, assets.mats.hardhat);
      hardhat.position.set(0, 0.78, 0);
      const brim = new THREE.Mesh(assets.geos.hardhatBrim, assets.mats.hardhat);
      brim.position.set(0, 0.78, 0.05);
      torsoGroup.add(hardhat);
      torsoGroup.add(brim);
    } else if (roleName === 'Medic') {
      const cap = new THREE.Mesh(assets.geos.medicCap, assets.mats.medicCap);
      cap.position.set(0, 0.92, 0);
      torsoGroup.add(cap);
      const crossH = new THREE.Mesh(assets.geos.medicCrossH, assets.mats.redBasic);
      crossH.position.set(0, 0.92, 0.31);
      const crossV = new THREE.Mesh(assets.geos.medicCrossV, assets.mats.redBasic);
      crossV.position.set(0, 0.92, 0.31);
      torsoGroup.add(crossH);
      torsoGroup.add(crossV);
    } else if (roleName === 'Trader') {
      const beret = new THREE.Mesh(assets.geos.traderBeret, assets.mats.beret);
      beret.rotation.z = -0.22;
      beret.position.set(0.06, 0.94, -0.02);
      torsoGroup.add(beret);
    } else if (roleName === 'Crafter') {
      const strap = new THREE.Mesh(assets.geos.crafterStrap, assets.mats.wood);
      strap.position.set(0, 0.78, 0);
      torsoGroup.add(strap);
      [-0.11, 0.11].forEach(lx => {
        const goggle = new THREE.Mesh(assets.geos.crafterLens, assets.mats.brass);
        goggle.rotation.x = Math.PI / 2;
        goggle.position.set(lx, 0.78, 0.28);
        const glass = new THREE.Mesh(assets.geos.crafterGlass, assets.mats.cyanBasic);
        glass.position.set(lx, 0.78, 0.32);
        torsoGroup.add(goggle);
        torsoGroup.add(glass);
      });
    } else {
      const cap = new THREE.Mesh(assets.geos.genCap, assets.mats.genCap);
      cap.position.set(0, 0.80, 0);
      torsoGroup.add(cap);
    }

    // 3. Articulated Arms
    const armLGroup = new THREE.Group();
    armLGroup.position.set(-0.42, 0.28, 0);
    const armLMesh = new THREE.Mesh(assets.geos.arm, roleMat);
    armLGroup.add(armLMesh);
    const handL = new THREE.Mesh(assets.geos.hand, skinMat);
    handL.position.y = -0.60;
    armLGroup.add(handL);
    torsoGroup.add(armLGroup);

    const armRGroup = new THREE.Group();
    armRGroup.position.set(0.42, 0.28, 0);
    const armRMesh = new THREE.Mesh(assets.geos.arm, roleMat);
    armRGroup.add(armRMesh);
    const handR = new THREE.Mesh(assets.geos.hand, skinMat);
    handR.position.y = -0.60;
    armRGroup.add(handR);

    // Handheld Props
    if (roleName === 'Farmer') {
      const pitchfork = new THREE.Group();
      const shaft = new THREE.Mesh(assets.geos.pitchforkShaft, assets.mats.wood);
      shaft.position.y = 0.15;
      pitchfork.add(shaft);
      const bar = new THREE.Mesh(assets.geos.pitchforkBar, assets.mats.metal);
      bar.position.y = 0.85;
      pitchfork.add(bar);
      [-0.10, 0, 0.10].forEach(tx => {
        const tine = new THREE.Mesh(assets.geos.pitchforkTine, assets.mats.metal);
        tine.position.set(tx, 1.02, 0);
        pitchfork.add(tine);
      });
      pitchfork.position.set(0, -0.45, 0.15);
      pitchfork.rotation.x = 0.3;
      armRGroup.add(pitchfork);
    } else if (roleName === 'Builder') {
      const hammer = new THREE.Group();
      const shaft = new THREE.Mesh(assets.geos.hammerShaft, assets.mats.wood);
      hammer.add(shaft);
      const head = new THREE.Mesh(assets.geos.hammerHead, assets.mats.metal);
      head.position.y = 0.30;
      hammer.add(head);
      hammer.position.set(0, -0.55, 0.12);
      hammer.rotation.x = Math.PI / 4;
      armRGroup.add(hammer);
    } else if (roleName === 'Medic') {
      const medkit = new THREE.Group();
      const box = new THREE.Mesh(assets.geos.medkitBox, assets.mats.medicCap);
      medkit.add(box);
      [-0.075, 0.075].forEach(zPos => {
        const cH = new THREE.Mesh(assets.geos.medicCrossH, assets.mats.redBasic);
        cH.position.z = zPos;
        const cV = new THREE.Mesh(assets.geos.medicCrossV, assets.mats.redBasic);
        cV.position.z = zPos;
        medkit.add(cH);
        medkit.add(cV);
      });
      medkit.position.set(0, -0.68, 0.05);
      armRGroup.add(medkit);
    } else if (roleName === 'Trader') {
      const pouch = new THREE.Group();
      const bag = new THREE.Mesh(assets.geos.pouchBag, assets.mats.wood);
      bag.scale.set(1.0, 1.2, 0.9);
      pouch.add(bag);
      const coin = new THREE.Mesh(assets.geos.pouchCoin, assets.mats.hardhat);
      coin.position.y = 0.12;
      pouch.add(coin);
      pouch.position.set(0, -0.65, 0.08);
      armRGroup.add(pouch);
    } else if (roleName === 'Crafter') {
      const wrench = new THREE.Group();
      const stem = new THREE.Mesh(assets.geos.wrenchStem, assets.mats.metal);
      wrench.add(stem);
      const jaw = new THREE.Mesh(assets.geos.wrenchJaw, assets.mats.metal);
      jaw.position.y = 0.22;
      wrench.add(jaw);
      wrench.position.set(0, -0.55, 0.10);
      wrench.rotation.x = Math.PI / 4;
      armRGroup.add(wrench);
    } else {
      const satchel = new THREE.Mesh(assets.geos.satchel, assets.mats.dark);
      satchel.position.set(0, -0.65, 0.08);
      armRGroup.add(satchel);
    }

    torsoGroup.add(armRGroup);
    group.add(torsoGroup);

    // 4. Articulated Legs
    const legLGroup = new THREE.Group();
    legLGroup.position.set(-0.18, 0.65, 0);
    const legLMesh = new THREE.Mesh(assets.geos.leg, assets.mats.dark);
    legLGroup.add(legLMesh);
    const bootL = new THREE.Mesh(assets.geos.boot, assets.mats.boot);
    bootL.position.set(0, -0.60, 0.04);
    legLGroup.add(bootL);
    group.add(legLGroup);

    const legRGroup = new THREE.Group();
    legRGroup.position.set(0.18, 0.65, 0);
    const legRMesh = new THREE.Mesh(assets.geos.leg, assets.mats.dark);
    legRGroup.add(legRMesh);
    const bootR = new THREE.Mesh(assets.geos.boot, assets.mats.boot);
    bootR.position.set(0, -0.60, 0.04);
    legRGroup.add(bootR);
    group.add(legRGroup);

    // 5. High-Resolution Floating 3D Billboard Sprite (Name, Role, Real-Time Activity & Vitals)
    const roleConfig = state.roles[roleName] || state.roles['Farmer'];
    const roleColorHex = agentData.color || roleConfig.color;
    const badgeSprite = createAgentBillboardSprite(agentData, roleColorHex);
    badgeSprite.position.set(0, 3.4, 0);
    badgeSprite.scale.set(5.0, 1.35, 1.0);
    group.add(badgeSprite);

    // 6. Ground Role Aura Ring (Permanent glowing circle on ground in role color)
    const auraMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(roleColorHex),
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.85
    });
    const auraRing = new THREE.Mesh(assets.geos.ring, auraMat);
    auraRing.rotation.x = -Math.PI / 2;
    auraRing.position.y = 0.04;
    auraRing.scale.set(1.4, 1.4, 1.4);
    group.add(auraRing);

    // 7. Ground Selection Highlight Ring (Enlarged on focused agent)
    const selRing = new THREE.Mesh(assets.geos.ring, assets.mats.ring);
    selRing.rotation.x = -Math.PI / 2;
    selRing.position.y = 0.06;
    selRing.scale.set(2.0, 2.0, 2.0);
    selRing.visible = false;
    group.add(selRing);

    return {
      group,
      torsoGroup,
      baseTorsoY,
      armLGroup,
      armRGroup,
      legLGroup,
      legRGroup,
      badgeSprite,
      auraRing,
      selRing,
      currentPos: new THREE.Vector3(agentData.position.x, 0, agentData.position.z),
      targetPos: new THREE.Vector3(agentData.position.x, 0, agentData.position.z),
      walkPhase: Math.random() * Math.PI * 2,
      idlePhase: Math.random() * Math.PI * 2,
      isMoving: false,
      heading: 0,
      data: agentData
    };
  }

  function getAgentRoleIcon(role) {
    switch (role) {
      case 'Farmer': return '🌾';
      case 'Trader': return '⚖️';
      case 'Builder': return '🔨';
      case 'Medic': return '✚';
      case 'Crafter': return '⚒️';
      case 'Generalist': return '📜';
      default: return '👤';
    }
  }

  function isAgentSleeping(agent) {
    if (!agent) return false;
    if (agent.inside_house === true) return true;
    if (agent.action === 'SLEEP_NIGHT') return true;
    const worldTime = state.envState && state.envState.world_time;
    const isNight = worldTime ? worldTime.is_night : false;
    if (isNight && agent.home_house_index) {
      let homePos = null;
      if (state.three && state.three.housePositions && state.three.housePositions[agent.home_house_index]) {
        homePos = state.three.housePositions[agent.home_house_index];
      } else if (state.worldMeta && state.worldMeta.houses && state.worldMeta.houses[agent.home_house_index - 1]) {
        const [hx, hz, hw, hd] = state.worldMeta.houses[agent.home_house_index - 1];
        homePos = new THREE.Vector3(hx + hw / 2, 0, hz + hd / 2);
      }
      if (homePos) {
        const posX = (agent.position && agent.position.x !== undefined) ? agent.position.x : 500;
        const posZ = (agent.position && agent.position.z !== undefined) ? agent.position.z : 500;
        const distToHome = Math.hypot(posX - homePos.x, posZ - homePos.z);
        if (distToHome < 7.0) return true;
      }
    }
    return false;
  }

  function getAgentDisplayActivity(agent) {
    if (!agent) return 'Standby in World';
    const house = agent.home_house_index || 1;
    if (agent.inside_house === true || agent.action === 'SLEEP_NIGHT' || isAgentSleeping(agent)) {
      return `💤 Sleeping peacefully inside House #${house}`;
    }
    if (agent.action === 'HYDRATE') {
      return '💧 Drinking refreshing spring water at Central Fountain';
    }

    const role = agent.role || 'Citizen';
    let text = agent.activity_text;

    if (!text || text === 'Standby in World' || text.startsWith('Active')) {
      switch (role) {
        case 'Medic': {
          if (agent.target?.label?.includes('Dwelling') || agent.routine_state === 'HOUSE_CALL') {
            text = `Conducting medical house call at Dwelling #${house}`;
          } else {
            text = 'Delivering trauma triage & care at Hospital Center';
          }
          break;
        }
        case 'Builder': {
          if (agent.routine_state === 'HAUL_MATERIALS' || agent.target?.label?.includes('Workshop')) {
            text = 'Hauling materials from Workshop';
          } else {
            text = 'Raising masonry walls at Municipal Site';
          }
          break;
        }
        case 'Crafter': {
          text = 'Forging iron tools at Workshop forge';
          break;
        }
        case 'Trader': {
          text = 'Bidding & asking on commodity order book at Central Agora';
          break;
        }
        case 'Generalist': {
          text = 'Studying civic governance manuals at Civic Academy';
          break;
        }
        case 'Farmer':
        default: {
          const plot = agent.farm_plot_index || ((house % 10) + 1);
          text = `Harvesting golden wheat at West Farm Belt (Plot #${plot})`;
          break;
        }
      }
    }

    if (agent.action === 'HYDRATE' || text.toLowerCase().includes('water') || text.toLowerCase().includes('fountain') || text.toLowerCase().includes('hydrate')) {
      return text.startsWith('💧') ? text : `💧 ${text}`;
    }
    if (agent.action === 'WITHDRAW_INSTITUTION' || text.toLowerCase().includes('silo')) {
      return text.startsWith('🌾') ? text : `🌾 ${text}`;
    }
    if (agent.action === 'REST_HOME') {
      return text.startsWith('🏠') ? text : `🏠 ${text}`;
    }

    const roleIcons = {
      Farmer: '🌾',
      Trader: '⚖️',
      Builder: '🔨',
      Medic: '✚',
      Crafter: '⚒️',
      Generalist: '📜'
    };
    const icon = roleIcons[role] || '👤';
    if (!text.startsWith(icon) && !text.startsWith('🌾') && !text.startsWith('⚖️') &&
        !text.startsWith('🔨') && !text.startsWith('✚') && !text.startsWith('⚒️') &&
        !text.startsWith('📜') && !text.startsWith('💧') && !text.startsWith('💤') &&
        !text.startsWith('🏠')) {
      return `${icon} ${text}`;
    }
    return text;
  }

  function renderAgentBillboardCanvas(ctx, canvas, agent, colorHex) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const isHydrating = agent.action === 'HYDRATE';
    const roleName = agent.role || 'Farmer';
    const roleIcon = isHydrating ? '💧' : getAgentRoleIcon(roleName);
    const accentColor = isHydrating ? '#06b6d4' : (colorHex || agent.color || '#10b981');

    // 1. Outer Neumorphic Pill Card with cyan glow if hydrating
    if (isHydrating) {
      ctx.shadowColor = 'rgba(6, 182, 212, 0.6)';
      ctx.shadowBlur = 12;
      ctx.fillStyle = 'rgba(6, 22, 38, 0.96)';
      ctx.strokeStyle = '#22d3ee';
      ctx.lineWidth = 4.5;
    } else {
      ctx.shadowBlur = 0;
      ctx.fillStyle = 'rgba(6, 10, 20, 0.94)';
      ctx.strokeStyle = accentColor;
      ctx.lineWidth = 4;
    }
    drawRoundedRect(ctx, 4, 4, 504, 132, 22, true, true);
    ctx.shadowBlur = 0; // reset shadow

    // Inner subtle glow border
    ctx.strokeStyle = isHydrating ? 'rgba(6, 182, 212, 0.45)' : 'rgba(255, 255, 255, 0.12)';
    ctx.lineWidth = isHydrating ? 2 : 1.5;
    drawRoundedRect(ctx, 7, 7, 498, 126, 19, false, true);

    // 2. Header Line (y: 34)
    // Left Role Icon Circle
    ctx.beginPath();
    ctx.arc(36, 34, 18, 0, Math.PI * 2);
    ctx.fillStyle = isHydrating ? 'rgba(6, 182, 212, 0.25)' : 'rgba(255, 255, 255, 0.1)';
    ctx.fill();
    ctx.strokeStyle = accentColor;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    ctx.font = '20px "Apple Color Emoji", "Segoe UI Emoji", sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(roleIcon, 36, 35);

    // Agent Name & Role
    ctx.font = 'bold 23px "Inter", sans-serif';
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    const agentName = agent.name || `Agent ${agent.id || ''}`;
    ctx.fillText(`${agentName} • ${roleName}`, 64, 34);

    // Right Badge on Header:
    if (isHydrating) {
      ctx.font = 'bold 16px "Fira Code", monospace';
      ctx.fillStyle = '#22d3ee';
      ctx.textAlign = 'right';
      ctx.fillText('💧 DRINK_WATER', 492, 34);
    } else {
      ctx.font = 'bold 15px "Fira Code", monospace';
      ctx.fillStyle = accentColor;
      ctx.textAlign = 'right';
      ctx.fillText(agent.id ? agent.id.toUpperCase() : 'EZ-01', 492, 34);
    }

    // Divider
    ctx.strokeStyle = isHydrating ? 'rgba(6, 182, 212, 0.35)' : 'rgba(255, 255, 255, 0.12)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(20, 56);
    ctx.lineTo(492, 56);
    ctx.stroke();

    // 3. Plain-English Real-Time Activity Text (y: 82)
    const activityText = getAgentDisplayActivity(agent);
    ctx.font = 'bold 20px "Inter", sans-serif';
    ctx.fillStyle = isHydrating ? '#22d3ee' : '#38bdf8';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';

    let displayAct = activityText;
    if (ctx.measureText(displayAct).width > 470) {
      while (displayAct.length > 10 && ctx.measureText(displayAct + '...').width > 470) {
        displayAct = displayAct.slice(0, -1);
      }
      displayAct += '...';
    }
    ctx.fillText(displayAct, 22, 82);

    // 4. Vital Progress Bar (y: 112)
    const h = agent.homeostasis || { food: 80, rest: 80, hydration: 80 };
    const foodVal = h.food !== undefined ? Math.min(100, Math.max(0, h.food)) : 80;
    const restVal = h.rest !== undefined ? Math.min(100, Math.max(0, h.rest)) : 80;
    const hydVal = h.hydration !== undefined ? Math.min(100, Math.max(0, h.hydration)) : 80;

    // Background track
    ctx.fillStyle = '#0f172a';
    drawRoundedRect(ctx, 22, 106, 260, 14, 7, true, false);

    // Fill track
    const barWidth = Math.max(8, (hydVal / 100) * 260);
    const grad = ctx.createLinearGradient(22, 0, 282, 0);
    if (isHydrating) {
      grad.addColorStop(0, '#06b6d4');
      grad.addColorStop(1, '#38bdf8');
    } else {
      grad.addColorStop(0, '#10b981');
      grad.addColorStop(1, '#06b6d4');
    }
    ctx.fillStyle = grad;
    drawRoundedRect(ctx, 22, 106, barWidth, 14, 7, true, false);

    // Text metrics
    ctx.font = 'bold 12px "Fira Code", monospace';
    ctx.fillStyle = isHydrating ? '#67e8f9' : '#cbd5e1';
    ctx.textAlign = 'right';
    ctx.fillText(`Water: ${Math.round(hydVal)}%  Food: ${Math.round(foodVal)}%`, 492, 113);
  }

  function createAgentBillboardSprite(agentData, colorHex) {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 140;
    const ctx = canvas.getContext('2d');

    renderAgentBillboardCanvas(ctx, canvas, agentData, colorHex);

    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.generateMipmaps = true;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.anisotropy = state.three.maxAnisotropy ? Math.min(state.three.maxAnisotropy, 8) : 1;
    const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
    const sprite = new THREE.Sprite(spriteMat);
    sprite.scale.set(5.0, 1.35, 1.0);
    sprite.userData = {
      canvas,
      texture,
      colorHex,
      lastActivity: getAgentDisplayActivity(agentData),
      lastAction: agentData.action || 'STANDBY',
      lastFood: Math.round(agentData.homeostasis?.food ?? 80),
      lastRest: Math.round(agentData.homeostasis?.rest ?? 80),
      lastHydration: Math.round(agentData.homeostasis?.hydration ?? 80)
    };
    return sprite;
  }

  function updateAgentBillboardSprite(sprite, agent) {
    if (!sprite || !sprite.userData || !sprite.userData.canvas) return;
    const canvas = sprite.userData.canvas;
    const ctx = canvas.getContext('2d');

    const activityText = getAgentDisplayActivity(agent);
    const action = agent.action || 'STANDBY';
    const h = agent.homeostasis || { food: 80, rest: 80, hydration: 80 };
    const foodVal = Math.round(h.food !== undefined ? h.food : 80);
    const restVal = Math.round(h.rest !== undefined ? h.rest : 80);
    const hydVal = Math.round(h.hydration !== undefined ? h.hydration : 80);

    // Dirty check: Only update canvas & re-upload texture to WebGL if text, action or vitals changed!
    if (sprite.userData.lastActivity === activityText &&
        sprite.userData.lastAction === action &&
        sprite.userData.lastFood === foodVal &&
        sprite.userData.lastRest === restVal &&
        sprite.userData.lastHydration === hydVal) {
      return;
    }

    sprite.userData.lastActivity = activityText;
    sprite.userData.lastAction = action;
    sprite.userData.lastFood = foodVal;
    sprite.userData.lastRest = restVal;
    sprite.userData.lastHydration = hydVal;

    renderAgentBillboardCanvas(ctx, canvas, agent, agent.color || sprite.userData.colorHex);
    sprite.userData.texture.needsUpdate = true;
  }

  function drawRoundedRect(ctx, x, y, width, height, radius, fill, stroke) {
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + width - radius, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
    ctx.lineTo(x + width, y + height - radius);
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    ctx.lineTo(x + radius, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
    if (fill) ctx.fill();
    if (stroke) ctx.stroke();
  }

  function syncAgentMeshes() {
    if ((!state.three.agentMeshes || state.three.agentMeshes.length === 0) && state.three.scene && state.agents && state.agents.length > 0) {
      build3DAgents(state.three.scene);
      return;
    }
    state.three.agentMeshes.forEach(avatar => {
      const match = state.agents.find(a => a.id === avatar.data.id);
      if (match) {
        avatar.data = match;
        avatar.targetPos.set(match.position.x, 0, match.position.z);
        updateAgentBillboardSprite(avatar.badgeSprite, match);

        const sleeping = isAgentSleeping(match);
        if (sleeping) {
          avatar.currentPos.copy(avatar.targetPos);
          avatar.group.position.set(avatar.targetPos.x, 0, avatar.targetPos.z);
          avatar.group.visible = false;
          if (avatar.badgeSprite) avatar.badgeSprite.visible = false;
          if (avatar.auraRing) avatar.auraRing.visible = false;
          if (avatar.selRing) avatar.selRing.visible = false;
        } else {
          avatar.group.visible = true;
          if (avatar.badgeSprite) avatar.badgeSprite.visible = true;
          if (avatar.auraRing) avatar.auraRing.visible = true;
          if (avatar.selRing) avatar.selRing.visible = (state.selectedAgentId === match.id);
        }
      }
    });
  }

  // =========================================================================
  // 6.5. Diurnal Celestial Lighting, House Sleep Particles & Crop Lifecycles
  // =========================================================================

  function initZzzParticleSystem(scene) {
    if (!scene) scene = state.three.scene;
    if (!scene) return;
    if (state.three.zzzGroup) {
      scene.remove(state.three.zzzGroup);
    }
    const zzzGroup = new THREE.Group();
    scene.add(zzzGroup);
    state.three.zzzGroup = zzzGroup;
    state.three.zzzParticles = [];

    // Pre-render 3 crisp billboard textures with emojis and glowing styling
    const zzzTexts = ['💤 Zzz', '💤 z Z', 'Z z z...'];
    const zzzTextures = zzzTexts.map(text => {
      const canvas = document.createElement('canvas');
      canvas.width = 512;
      canvas.height = 256;
      const ctx = canvas.getContext('2d');
      ctx.clearRect(0, 0, 512, 256);
      ctx.shadowColor = '#38bdf8';
      ctx.shadowBlur = 24;
      ctx.font = 'bold 88px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace';
      ctx.fillStyle = '#e0f2fe';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, 256, 128);
      const tex = new THREE.CanvasTexture(canvas);
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.generateMipmaps = true;
      tex.minFilter = THREE.LinearMipmapLinearFilter;
      tex.magFilter = THREE.LinearFilter;
      tex.anisotropy = state.three.maxAnisotropy ? Math.min(state.three.maxAnisotropy, 8) : 1;
      tex.needsUpdate = true;
      return tex;
    });

    // Pre-create pool of 128 floating sprite billboards
    for (let i = 0; i < 128; i++) {
      const tex = zzzTextures[i % zzzTextures.length];
      const mat = new THREE.SpriteMaterial({
        map: tex,
        transparent: true,
        opacity: 0.0,
        depthWrite: false
      });
      const sprite = new THREE.Sprite(mat);
      sprite.visible = false;
      zzzGroup.add(sprite);

      state.three.zzzParticles.push({
        sprite,
        houseIndex: null,
        basePos: new THREE.Vector3(),
        age: (i * 0.03) % 1.0,
        speed: 0.22 + Math.random() * 0.16,
        swaySpeed: 1.8 + Math.random() * 1.4,
        swayAmp: 0.8 + Math.random() * 0.9,
        swayPhase: Math.random() * Math.PI * 2,
        maxHeight: 7.5 + Math.random() * 5.0,
        active: false
      });
    }
  }

  function updateZzzParticles(dt, elapsedTime) {
    if (!state.three.zzzParticles || state.three.zzzParticles.length === 0) return;
    const worldTime = state.envState && state.envState.world_time;
    const isNight = worldTime ? worldTime.is_night : false;

    // Smoothly fade out all particles during daytime
    if (!isNight) {
      state.three.zzzParticles.forEach(p => {
        if (p.sprite.visible) {
          p.sprite.material.opacity = THREE.MathUtils.lerp(p.sprite.material.opacity, 0, dt * 6);
          if (p.sprite.material.opacity < 0.02) {
            p.sprite.visible = false;
            p.active = false;
          }
        }
      });
      return;
    }

    // Determine active sleeping houses
    const set = new Set();
    if (state.envState && state.envState.sleeping_houses && typeof state.envState.sleeping_houses === 'object') {
      Object.keys(state.envState.sleeping_houses)
        .map(Number)
        .filter(idx => (state.envState.sleeping_houses[idx] && state.envState.sleeping_houses[idx].length > 0))
        .forEach(idx => set.add(idx));
    }

    if (state.agents) {
      state.agents.forEach(a => {
        if (isAgentSleeping(a) || (isNight && a.home_house_index)) {
          if (a.home_house_index) set.add(a.home_house_index);
        }
      });
    }

    if (set.size === 0 && isNight) {
      for (let i = 1; i <= 64; i++) set.add(i);
    }
    const sleepingHouseIndices = Array.from(set);

    let pIdx = 0;
    for (let i = 0; i < sleepingHouseIndices.length && pIdx < state.three.zzzParticles.length; i++) {
      const hIdx = sleepingHouseIndices[i];
      let pos = state.three.housePositions[hIdx];
      if (!pos && state.worldMeta && state.worldMeta.houses && state.worldMeta.houses[hIdx - 1]) {
        const [hx, hz, hw, hd, archId] = state.worldMeta.houses[hIdx - 1];
        const arch = (state.archetypes && state.archetypes[archId]) || {};
        const hHeight = arch.height || 4.5;
        pos = new THREE.Vector3(hx + hw / 2, hHeight + 2.2, hz + hd / 2);
        state.three.housePositions[hIdx] = pos;
      }
      if (!pos) continue;

      // Assign up to 2 animated particles per sleeping dwelling
      for (let k = 0; k < 2 && pIdx < state.three.zzzParticles.length; k++) {
        const p = state.three.zzzParticles[pIdx++];
        p.houseIndex = hIdx;
        p.basePos.copy(pos);
        p.active = true;
        p.sprite.visible = true;

        p.age += p.speed * dt;
        if (p.age >= 1.0) {
          p.age = 0.0;
        }

        const t = p.age;
        // Drift slowly upward into the night sky
        p.sprite.position.y = p.basePos.y + t * p.maxHeight;
        // Soft horizontal sway with sin(t)
        p.sprite.position.x = p.basePos.x + Math.sin(elapsedTime * p.swaySpeed + p.swayPhase) * (p.swayAmp * (0.35 + 0.65 * t));
        p.sprite.position.z = p.basePos.z + Math.cos(elapsedTime * (p.swaySpeed * 0.7) + p.swayPhase) * (p.swayAmp * 0.35);

        // Sinusoidal opacity fade-in / fade-out envelope
        const opacity = Math.sin(t * Math.PI) * 0.95;
        p.sprite.material.opacity = opacity;

        // Gentle scale expansion as particle ascends
        const s = 1.6 + t * 1.5;
        p.sprite.scale.set(s * 2.4, s * 1.2, 1.0);
      }
    }

    // Hide remaining pool sprites
    while (pIdx < state.three.zzzParticles.length) {
      const p = state.three.zzzParticles[pIdx++];
      if (p.active) {
        p.active = false;
        p.sprite.visible = false;
      }
    }
  }

  function initHarvestParticleSystem(scene) {
    if (!scene) scene = state.three.scene;
    if (!scene) return;
    if (state.three.harvestGroup) {
      scene.remove(state.three.harvestGroup);
    }
    const harvestGroup = new THREE.Group();
    scene.add(harvestGroup);
    state.three.harvestGroup = harvestGroup;
    state.three.harvestBadges = [];
  }

  function triggerHarvestAnimation(plotIndex) {
    if (!state.three.cropPlots || !state.three.cropPlots[plotIndex]) return;
    const plot = state.three.cropPlots[plotIndex];

    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 80;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, 256, 80);

    // Neumorphic dark amber pill
    ctx.fillStyle = 'rgba(15, 23, 42, 0.90)';
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 3.5;
    drawRoundedRect(ctx, 8, 8, 240, 64, 28, true, true);

    ctx.font = 'bold 28px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace';
    ctx.fillStyle = '#fef08a';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('+🌾 Grain Harvest', 128, 40);

    const tex = new THREE.CanvasTexture(canvas);
    tex.needsUpdate = true;
    const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 1.0, depthWrite: false });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(16, 5, 1);
    sprite.position.set(plot.center.x, 3.5, plot.center.z);

    if (state.three.harvestGroup) {
      state.three.harvestGroup.add(sprite);
    } else if (state.three.scene) {
      state.three.scene.add(sprite);
    }

    state.three.harvestBadges.push({
      sprite,
      baseY: 3.5,
      timer: 0.0,
      duration: 2.2
    });
  }

  function updateHarvestBadges(dt) {
    if (!state.three.harvestBadges || state.three.harvestBadges.length === 0) return;
    for (let i = state.three.harvestBadges.length - 1; i >= 0; i--) {
      const b = state.three.harvestBadges[i];
      b.timer += dt;
      const progress = b.timer / b.duration;
      if (progress >= 1.0) {
        if (b.sprite.parent) b.sprite.parent.remove(b.sprite);
        b.sprite.material.dispose();
        state.three.harvestBadges.splice(i, 1);
      } else {
        b.sprite.position.y = b.baseY + progress * 9.0;
        b.sprite.material.opacity = Math.max(0, (1.0 - progress) * 1.3);
        b.sprite.scale.set(16 * (1.0 + progress * 0.2), 5 * (1.0 + progress * 0.2), 1);
      }
    }
  }

  function updateFarmCrops(dt, elapsedTime) {
    if (!state.three.cropPlots || state.three.cropPlots.length === 0) return;
    const plotsData = state.envState && state.envState.farm_plots;

    state.three.cropPlots.forEach((plot, b) => {
      let stage = 3;
      let progress = 100;
      if (plotsData && plotsData[b]) {
        stage = plotsData[b].growth_stage !== undefined ? plotsData[b].growth_stage : 3;
        progress = plotsData[b].progress !== undefined ? plotsData[b].progress : 100;
      } else {
        const cycle = ((state.envState?.tick || 142) + b * 18) % 100;
        if (cycle < 15) stage = 0;
        else if (cycle < 45) stage = 1;
        else if (cycle < 75) stage = 2;
        else stage = 3;
      }

      // Detect harvest transition: ripe -> stubble
      if (plot.currentStage === 3 && stage === 0) {
        triggerHarvestAnimation(b);
      }
      plot.currentStage = stage;

      let targetScaleY = 1.08;
      switch (stage) {
        case 0: targetScaleY = 0.115; break; // Stubble 0.15m height
        case 1: targetScaleY = 0.308; break; // Sprout 0.4m height
        case 2: targetScaleY = 0.615; break; // Growing 0.8m height
        case 3: default: targetScaleY = 1.08; break; // Golden Ripe 1.4m height
      }

      plot.targetScaleY = targetScaleY;
      plot.currentScaleY = THREE.MathUtils.lerp(plot.currentScaleY, plot.targetScaleY, dt * 5.0);

      const mat = state.three.cropStageMats ? state.three.cropStageMats[stage] : null;

      plot.rows.forEach((row, r) => {
        row.scale.y = plot.currentScaleY;
        row.position.y = 0.2 + (1.3 * plot.currentScaleY) / 2;
        if (mat && row.material !== mat) {
          row.material = mat;
        }
        // Gentle wind sway for ripe (stage 3) and growing (stage 2) wheat
        if (stage >= 2) {
          const windSway = Math.sin(elapsedTime * 2.8 + b * 0.9 + r * 0.45) * (stage === 3 ? 0.055 : 0.025);
          row.rotation.z = windSway;
        } else {
          row.rotation.z = 0;
        }
      });
    });
  }

  function updateDiurnalCelestial(elapsedTime, dt) {
    const { scene, sunLight, ambientLight, sunMesh, sunCorona, moonMesh, starMat, streetLightsGroup, windowMaterials } = state.three;
    if (!scene || !sunLight || !ambientLight) return;

    const worldTime = (state.envState && state.envState.world_time) || {
      hour: 8,
      minute: 0,
      phase: 'DAY',
      is_night: false,
      sun_progress: 0.33,
      formatted: '08:00 AM',
      day_count: 1
    };

    const hours = (worldTime.hour !== undefined ? worldTime.hour : 8) + (worldTime.minute || 0) / 60;

    // Celestial Orbit around world center (500, 500)
    const orbitProgress = (hours - 6.0) / 24.0;
    const angle = orbitProgress * Math.PI * 2;
    const R = 850;

    const sunX = 500 + Math.cos(angle) * R;
    const sunY = Math.sin(angle) * R;
    const sunZ = 500 + Math.sin(angle * 0.5) * 180;

    const moonAngle = angle + Math.PI;
    const moonX = 500 + Math.cos(moonAngle) * R;
    const moonY = Math.sin(moonAngle) * R;
    const moonZ = 500 + Math.sin(moonAngle * 0.5) * 180;

    if (sunMesh) {
      sunMesh.position.set(sunX, Math.max(-120, sunY), sunZ);
      sunMesh.visible = sunY > -100;
    }
    if (sunCorona) {
      sunCorona.scale.setScalar(1.0 + Math.sin(elapsedTime * 2.2) * 0.08);
    }
    if (moonMesh) {
      moonMesh.position.set(moonX, Math.max(-120, moonY), moonZ);
      moonMesh.visible = moonY > -100;
    }

    // Diurnal Phase Atmospheric Lighting
    let bgTargetHex = 0x081528;
    let fogTargetHex = 0x081528;
    let ambientTargetHex = 0x94a3b8;
    let ambientTargetIntensity = 2.2;
    let dirTargetHex = 0xffffff;
    let dirTargetIntensity = 2.9;
    let windowEmissiveHex = 0x0e7490;
    let windowEmissiveIntensity = 0.2;
    let streetLightsVisible = false;
    let starOpacity = 0.0;

    if (hours >= 5.0 && hours < 8.0) {
      // 1. Sunrise / Dawn (05:00-08:00): Warm amber/peach morning light, soft dawn fog
      const t = (hours - 5.0) / 3.0;
      const dawnBg = new THREE.Color(0x1e1b4b).lerp(new THREE.Color(0x431407), Math.min(1, t * 1.5)).lerp(new THREE.Color(0x081528), Math.max(0, (t - 0.5) * 2));
      bgTargetHex = dawnBg.getHex();
      fogTargetHex = bgTargetHex;
      ambientTargetHex = new THREE.Color(0x78350f).lerp(new THREE.Color(0xfb923c), t).getHex();
      ambientTargetIntensity = 1.2 + t * 0.9;
      dirTargetHex = new THREE.Color(0xfdba74).lerp(new THREE.Color(0xffedd5), t).getHex();
      dirTargetIntensity = 1.8 + t * 0.9;
      windowEmissiveHex = 0xfef08a;
      windowEmissiveIntensity = Math.max(0.2, (1.0 - t) * 0.7);
      streetLightsVisible = t < 0.5;
      starOpacity = Math.max(0, (0.4 - t) * 2.0);
    } else if (hours >= 8.0 && hours < 17.5) {
      // 2. High Noon / Day (08:00-17:30): Bright clean daylight (#ffffff), high sun angle, crisp shadows
      bgTargetHex = 0x081528;
      fogTargetHex = 0x081528;
      ambientTargetHex = 0x94a3b8;
      ambientTargetIntensity = 2.2;
      dirTargetHex = 0xffffff;
      dirTargetIntensity = 2.9;
      windowEmissiveHex = 0x0e7490;
      windowEmissiveIntensity = 0.2;
      streetLightsVisible = false;
      starOpacity = 0.0;
    } else if (hours >= 17.5 && hours < 20.5) {
      // 3. Sunset / Golden Hour (17:30-20:30): Rich crimson/golden glow (#f97316), long dramatic shadows
      const t = (hours - 17.5) / 3.0;
      const sunsetBg = new THREE.Color(0x081528).lerp(new THREE.Color(0x7f1d1d), Math.min(1, t * 1.3)).lerp(new THREE.Color(0x020617), Math.max(0, (t - 0.6) * 2.5));
      bgTargetHex = sunsetBg.getHex();
      fogTargetHex = bgTargetHex;
      ambientTargetHex = new THREE.Color(0xf97316).lerp(new THREE.Color(0x312e81), t).getHex();
      ambientTargetIntensity = 2.0 - t * 0.9;
      dirTargetHex = new THREE.Color(0xf97316).lerp(new THREE.Color(0xf43f5e), t * 0.5).getHex();
      dirTargetIntensity = 2.6 - t * 1.2;
      windowEmissiveHex = 0xfef08a;
      windowEmissiveIntensity = 0.25 + t * 0.55;
      streetLightsVisible = t > 0.45;
      starOpacity = Math.max(0, (t - 0.35) * 1.5);
    } else {
      // 4. Night (20:30-05:00): Deep midnight indigo (#020617), soft cool moonlight (#38bdf8), street lamps illuminate, house windows glow with warm interior light
      bgTargetHex = 0x020617;
      fogTargetHex = 0x020617;
      ambientTargetHex = 0x1e293b;
      ambientTargetIntensity = 0.95;
      dirTargetHex = 0x38bdf8;
      dirTargetIntensity = 1.35;
      windowEmissiveHex = 0xfef08a;
      windowEmissiveIntensity = 0.8;
      streetLightsVisible = true;
      starOpacity = 0.85;
    }

    // Smooth lerp scene background & fog
    scene.background.lerp(new THREE.Color(bgTargetHex), 0.08);
    if (scene.fog) scene.fog.color.lerp(new THREE.Color(fogTargetHex), 0.08);

    ambientLight.color.lerp(new THREE.Color(ambientTargetHex), 0.08);
    ambientLight.intensity = THREE.MathUtils.lerp(ambientLight.intensity, ambientTargetIntensity, 0.08);

    sunLight.color.lerp(new THREE.Color(dirTargetHex), 0.08);
    sunLight.intensity = THREE.MathUtils.lerp(sunLight.intensity, dirTargetIntensity, 0.08);

    // Directional light tracks Sun when high, Moon when Sun is below horizon
    if (sunY > 0) {
      sunLight.position.set(sunX, Math.max(60, sunY), sunZ);
    } else {
      sunLight.position.set(moonX, Math.max(60, moonY), moonZ);
    }

    if (starMat) {
      starMat.opacity = THREE.MathUtils.lerp(starMat.opacity, starOpacity, 0.06);
    }

    if (streetLightsGroup) {
      streetLightsGroup.visible = streetLightsVisible;
    }

    if (windowMaterials && windowMaterials.length > 0) {
      windowMaterials.forEach(m => {
        m.emissive.lerp(new THREE.Color(windowEmissiveHex), 0.08);
        m.emissiveIntensity = THREE.MathUtils.lerp(m.emissiveIntensity, windowEmissiveIntensity, 0.08);
      });
    }
  }

  // =========================================================================
  // 7. Simulation Stepping & Smooth Lerping Animation Loop
  // =========================================================================
  function animateThree() {
    requestAnimationFrame(animateThree);
    if (state.three.isContextLost) return;

    const rawDt = state.three.clock.getDelta();
    const dt = Math.min(rawDt, 0.1);
    const elapsedTime = state.three.clock.getElapsedTime();
    const { controls, renderer, scene, camera, shieldMesh, agoraRing, hospitalBeacon, fireSirenLight, camTargetPos, camLookAtPos } = state.three;

    // 0. Diurnal Celestial Sun/Moon, Sleep Particles, Crop Lifecycle & Harvest Badges
    updateDiurnalCelestial(elapsedTime, dt);
    updateZzzParticles(dt, elapsedTime);
    updateFarmCrops(dt, elapsedTime);
    updateHarvestBadges(dt);

    // 1. Smooth Agent Walking, Sinusoidal Oscillation & Torso Bobbing
    const baseWalkSpeed = 12 * state.simSpeedFactor;

    state.three.agentMeshes.forEach(avatar => {
      const sleeping = isAgentSleeping(avatar.data);
      if (sleeping) {
        avatar.group.visible = false;
        if (avatar.badgeSprite) avatar.badgeSprite.visible = false;
        if (avatar.auraRing) avatar.auraRing.visible = false;
        if (avatar.selRing) avatar.selRing.visible = false;
        avatar.isMoving = false;
        avatar.currentPos.copy(avatar.targetPos);
        avatar.group.position.set(avatar.targetPos.x, 0, avatar.targetPos.z);
        return;
      } else {
        avatar.group.visible = true;
        if (avatar.badgeSprite) avatar.badgeSprite.visible = true;
        if (avatar.auraRing) avatar.auraRing.visible = true;
        if (avatar.selRing) avatar.selRing.visible = (state.selectedAgentId === avatar.data.id);
      }

      const dx = avatar.targetPos.x - avatar.currentPos.x;
      const dz = avatar.targetPos.z - avatar.currentPos.z;
      const dist = Math.hypot(dx, dz);

      if (dist > 0.08) {
        avatar.isMoving = true;
        const step = Math.min(dist, dt * baseWalkSpeed);
        avatar.currentPos.x += (dx / dist) * step;
        avatar.currentPos.z += (dz / dist) * step;

        const targetHeading = Math.atan2(dx, dz);
        let diff = targetHeading - avatar.group.rotation.y;
        while (diff < -Math.PI) diff += Math.PI * 2;
        while (diff > Math.PI) diff -= Math.PI * 2;
        avatar.group.rotation.y += diff * Math.min(1, dt * 10);

        avatar.walkPhase += dt * 9 * state.simSpeedFactor;
        avatar.legLGroup.rotation.x = Math.sin(avatar.walkPhase) * 0.65;
        avatar.legRGroup.rotation.x = -Math.sin(avatar.walkPhase) * 0.65;
        avatar.armLGroup.rotation.x = -Math.sin(avatar.walkPhase) * 0.55;
        avatar.armRGroup.rotation.x = Math.sin(avatar.walkPhase) * 0.55;

        // Torso lean forward in walk direction & subtle torso twist
        avatar.torsoGroup.rotation.x = THREE.MathUtils.lerp(avatar.torsoGroup.rotation.x, 0.08, 0.1);
        avatar.torsoGroup.rotation.y = Math.sin(avatar.walkPhase) * 0.06;
        avatar.torsoGroup.rotation.z = THREE.MathUtils.lerp(avatar.torsoGroup.rotation.z, 0, 0.1);
        avatar.torsoGroup.position.y = avatar.baseTorsoY + Math.abs(Math.sin(avatar.walkPhase * 2)) * 0.08;
      } else {
        avatar.isMoving = false;
        avatar.legLGroup.rotation.x = THREE.MathUtils.lerp(avatar.legLGroup.rotation.x, 0, 0.15);
        avatar.legRGroup.rotation.x = THREE.MathUtils.lerp(avatar.legRGroup.rotation.x, 0, 0.15);
        avatar.armLGroup.rotation.x = THREE.MathUtils.lerp(avatar.armLGroup.rotation.x, 0, 0.15);
        avatar.armRGroup.rotation.x = THREE.MathUtils.lerp(avatar.armRGroup.rotation.x, 0, 0.15);
        avatar.torsoGroup.rotation.x = THREE.MathUtils.lerp(avatar.torsoGroup.rotation.x, 0, 0.15);
        avatar.torsoGroup.rotation.y = THREE.MathUtils.lerp(avatar.torsoGroup.rotation.y, 0, 0.15);

        // Lifelike idle breathing & weight-shift sway so agents never freeze rigidly
        const idleCycle = elapsedTime * 2.0 + (avatar.idlePhase || 0);
        avatar.torsoGroup.position.y = avatar.baseTorsoY + Math.sin(idleCycle) * 0.03;
        avatar.torsoGroup.rotation.z = Math.sin(idleCycle * 0.7) * 0.02;
      }

      avatar.group.position.set(avatar.currentPos.x, 0, avatar.currentPos.z);
    });

    // 2. Camera Direction: Single Unified Cinematic Tour or Third-Person Follow Cam
    const isCinematicActive = (state.cinematicTour && state.cinematicTour.active) || (state.spectate && state.spectate.active);
    if (isCinematicActive && camera && controls) {
      const tourState = state.cinematicTour || state.spectate;
      const followed = state.three.agentMeshes.find(a => a.data.id === state.followingAgentId)
        || (tourState.currentAgent && state.three.agentMeshes.find(a => a.data.id === tourState.currentAgent.id));
      if (followed) {
        const isSleeping = isAgentSleeping(followed.data);
        const heading = followed.group.rotation.y || 0;
        let posX = followed.currentPos.x;
        let posZ = followed.currentPos.z;
        let targetCamX, targetCamY, targetCamZ;
        let lookAtTarget;

        if (isSleeping) {
          // If spectating an agent who is inside sleeping, frame the camera on their dwelling's front facade and rooftop chimney with floating Zzz particles
          const hIdx = followed.data.home_house_index || 1;
          let hx = posX, hz = posZ, hw = 12, hd = 12, hHeight = 4.5;
          if (state.worldMeta && state.worldMeta.houses && state.worldMeta.houses[hIdx - 1]) {
            [hx, hz, hw, hd] = state.worldMeta.houses[hIdx - 1];
            const archId = state.worldMeta.houses[hIdx - 1][4] || 0;
            const arch = (state.archetypes && state.archetypes[archId]) || {};
            hHeight = arch.height || 4.5;
          }
          const centerX = hx + hw / 2;
          const centerZ = hz + hd / 2;
          posX = centerX;
          posZ = centerZ;

          const swayAngle = elapsedTime * 0.15;
          const camDist = Math.max(18.0, hd + 10.0);
          targetCamX = centerX + Math.sin(swayAngle) * 5.0;
          targetCamY = hHeight + 7.5;
          targetCamZ = centerZ + camDist;
          lookAtTarget = new THREE.Vector3(centerX, hHeight * 0.75 + 1.2, centerZ);

          const elShot = document.getElementById('spectateShotType');
          if (elShot) {
            elShot.textContent = 'DWELLING FACADE & CHIMNEY ZZZ';
          }
        } else {
          switch (tourState.currentShotType) {
            case 'LOW_ANGLE': {
              // Low-Angle Pavement Dolly: Generous vertical headroom (>10m clearance) above billboard badge (height 16.0m > 10m above 4.1m badge)
              const dist = 28.0;
              const angle = heading + 0.35;
              targetCamX = posX - Math.sin(angle) * dist;
              targetCamY = 16.0;
              targetCamZ = posZ - Math.cos(angle) * dist;
              lookAtTarget = new THREE.Vector3(posX, 5.0, posZ);
              break;
            }
            case 'DRONE_ORBIT': {
              // High 45° Drone Orbit: Distance 60m, height 32.0m (>27m clearance), looking at y = 7.0m, orbiting slowly around the active citizen and surrounding architecture
              tourState.orbitAngle = (tourState.orbitAngle || 0) + 0.005;
              const dist = 60.0;
              targetCamX = posX + Math.cos(tourState.orbitAngle) * dist;
              targetCamY = 32.0;
              targetCamZ = posZ + Math.sin(tourState.orbitAngle) * dist;
              lookAtTarget = new THREE.Vector3(posX, 7.0, posZ);
              break;
            }
            case 'FRONTAL': {
              // Frontal Approach Dolly: Moving ahead of the citizen as they walk forward along the avenue
              // Distance 32m, height 16.5m (>12m clearance), looking at y = 5.5m
              const dist = 32.0;
              targetCamX = posX + Math.sin(heading) * dist;
              targetCamY = 16.5;
              targetCamZ = posZ + Math.cos(heading) * dist;
              lookAtTarget = new THREE.Vector3(posX, 5.5, posZ);
              break;
            }
            case 'CHASE':
            default: {
              // Over-Shoulder Chase Cam: Distance 38m, height 18.5m (>14m clearance), looking at y = 6.0m (overhead billboard perfectly visible with full headroom)
              const dist = 38.0;
              targetCamX = posX - Math.sin(heading) * dist;
              targetCamY = 18.5;
              targetCamZ = posZ - Math.cos(heading) * dist;
              lookAtTarget = new THREE.Vector3(posX, 6.0, posZ);
              break;
            }
          }
        }

        const targetCamVec = new THREE.Vector3(targetCamX, targetCamY, targetCamZ);
        if (camera.position.distanceTo(targetCamVec) > 120) {
          camera.position.copy(targetCamVec).add(new THREE.Vector3(0, 8, 0));
        }
        camera.position.lerp(targetCamVec, 0.07);
        controls.target.lerp(lookAtTarget, 0.07);

        // Update live spectator position badge in HUD
        const elPos = document.getElementById('spectatePositionBadge');
        if (elPos) {
          if (isSleeping) {
            elPos.textContent = `HOUSE #${followed.data.home_house_index || 1} · 🏠 INSIDE · 💤 ASLEEP`;
          } else {
            elPos.textContent = `POS: X ${Math.round(posX)}m · Z ${Math.round(posZ)}m`;
          }
        }
      }
    } else if (state.followingAgentId && camera && controls) {
      const followed = state.three.agentMeshes.find(a => a.data.id === state.followingAgentId);
      if (followed) {
        if (isAgentSleeping(followed.data)) {
          const hIdx = followed.data.home_house_index || 1;
          let hx = followed.currentPos.x, hz = followed.currentPos.z, hw = 12, hd = 12, hHeight = 4.5;
          if (state.worldMeta && state.worldMeta.houses && state.worldMeta.houses[hIdx - 1]) {
            [hx, hz, hw, hd] = state.worldMeta.houses[hIdx - 1];
            const archId = state.worldMeta.houses[hIdx - 1][4] || 0;
            const arch = (state.archetypes && state.archetypes[archId]) || {};
            hHeight = arch.height || 4.5;
          }
          const centerX = hx + hw / 2;
          const centerZ = hz + hd / 2;
          const camDist = Math.max(18.0, hd + 10.0);
          const targetCamX = centerX + 2.0;
          const targetCamY = hHeight + 7.5;
          const targetCamZ = centerZ + camDist;
          camera.position.lerp(new THREE.Vector3(targetCamX, targetCamY, targetCamZ), 0.08);
          controls.target.lerp(new THREE.Vector3(centerX, hHeight * 0.75 + 1.2, centerZ), 0.08);
        } else {
          const heading = followed.group.rotation.y;
          const camDistance = 38.0;
          const camHeight = 18.5;
          const targetCamX = followed.currentPos.x - Math.sin(heading) * camDistance;
          const targetCamZ = followed.currentPos.z - Math.cos(heading) * camDistance;
          const targetCamY = camHeight;

          camera.position.lerp(new THREE.Vector3(targetCamX, targetCamY, targetCamZ), 0.08);
          controls.target.lerp(new THREE.Vector3(followed.currentPos.x, 6.0, followed.currentPos.z), 0.08);
        }
      }
    } else if (camTargetPos && camLookAtPos && camera && controls) {
      camera.position.lerp(camTargetPos, 0.05);
      controls.target.lerp(camLookAtPos, 0.05);

      if (camera.position.distanceTo(camTargetPos) < 2) {
        state.three.camTargetPos = null;
        state.three.camLookAtPos = null;
      }
    }

    if (controls) controls.update();

    // 3. Rotating & Pulsing Civic Beacons
    if (shieldMesh) {
      shieldMesh.rotation.y += 0.002;
      shieldMesh.rotation.x += 0.001;
    }

    if (agoraRing) {
      agoraRing.rotation.z += 0.018;
    }

    if (hospitalBeacon) {
      const pulse = 1.0 + Math.sin(elapsedTime * 4.5) * 0.22;
      hospitalBeacon.scale.set(pulse, pulse, pulse);
      if (state.three.hospitalLight) {
        state.three.hospitalLight.intensity = 2.5 + Math.sin(elapsedTime * 4.5) * 1.5;
      }
    }

    if (fireSirenLight) {
      fireSirenLight.intensity = 2.0 + Math.cos(elapsedTime * 6) * 1.2;
    }

    // 4. Render WebGL Frame
    if (renderer && scene && camera && state.viewMode === '3d') {
      renderer.render(scene, camera);
    }

    // 5. Update Real-Time Substrate Telemetry (Heading, Elevation, Coordinates, Sector, Agents)
    if (camera) {
      const dir = new THREE.Vector3();
      camera.getWorldDirection(dir);
      const deg = Math.round((Math.atan2(dir.x, dir.z) * 180 / Math.PI + 360) % 360);
      const cardinals = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
      const cardIdx = Math.round(deg / 22.5) % 16;
      const headingStr = `${String(deg).padStart(3, '0')}° ${cardinals[cardIdx]}`;
      const elev = Math.round(Math.asin(Math.max(-1, Math.min(1, dir.y))) * 180 / Math.PI);
      const elevStr = `${elev >= 0 ? '+' : ''}${elev}°`;

      let currentCoord = { x: 500, z: 500 };
      if (state.followingAgentId) {
        const ag = state.agents && state.agents.find(a => a.id === state.followingAgentId);
        if (ag && ag.position) {
          currentCoord = { x: Math.round(ag.position.x), z: Math.round(ag.position.z) };
        }
      } else if (controls && controls.target) {
        currentCoord = {
          x: Math.max(0, Math.min(1000, Math.round(controls.target.x))),
          z: Math.max(0, Math.min(1000, Math.round(controls.target.z)))
        };
      }

      updateBottomTelemetry(currentCoord, headingStr, elevStr);
    }
  }

  // Raycasting & Click Selection
  function onThreeMouseMove(e) {
    if (!state.three.renderer || !state.three.camera) return;
    const rect = state.three.renderer.domElement.getBoundingClientRect();
    state.three.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    state.three.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    state.three.raycaster.setFromCamera(state.three.mouse, state.three.camera);
    const intersects = state.three.raycaster.intersectObjects(state.three.clickableMeshes, false);

    if (intersects.length > 0) {
      const obj = intersects[0].object;
      if (state.three.hoveredObject !== obj) {
        state.three.hoveredObject = obj;
        state.three.renderer.domElement.style.cursor = 'pointer';
      }
    } else {
      state.three.hoveredObject = null;
      state.three.renderer.domElement.style.cursor = 'grab';
    }

    // Live Substrate Ground Coordinate Tracking into Bottom Status Bar
    const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
    const targetPoint = new THREE.Vector3();
    if (state.three.raycaster.ray.intersectPlane(groundPlane, targetPoint)) {
      const hoverX = Math.max(0, Math.min(1000, Math.round(targetPoint.x)));
      const hoverZ = Math.max(0, Math.min(1000, Math.round(targetPoint.z)));
      const elCoords = document.getElementById('substrateCoordinatesStatus') || document.getElementById('mouseCoords');
      if (elCoords) {
        elCoords.textContent = `X: ${hoverX}m · Z: ${hoverZ}m`;
      }
      const elSector = document.getElementById('sectorName');
      if (elSector) {
        elSector.textContent = getSectorNameForCoord(hoverX, hoverZ);
      }
    }
  }

  function onThreeClick() {
    if (!state.three.renderer || !state.three.camera) return;
    state.three.raycaster.setFromCamera(state.three.mouse, state.three.camera);
    const intersects = state.three.raycaster.intersectObjects(state.three.clickableMeshes, false);

    if (intersects.length > 0) {
      const obj = intersects[0].object;
      state.three.selectedObject = obj;

      if (obj.userData && obj.userData.isAgent) {
        inspectAgent(obj.userData.data, true, true);
      } else if (obj.userData && obj.userData.isHouse) {
        state.followingAgentId = null;
        inspectHouse(obj.userData, true);
      } else if (obj.userData && obj.userData.isCivic) {
        state.followingAgentId = null;
        inspectCivic(obj.userData.data, true);
      }
    }
  }

  // =========================================================================
  // 8. Inspector Drawer & 8-Drive Chebyshev Homeostasis
  // =========================================================================
  function inspectAgent(agent, enableFollow = true, openDrawer = false) {
    if (!agent) return;
    state.selectedAgentId = agent.id;
    if (enableFollow) state.followingAgentId = agent.id;

    // Toggle 3D selection rings
    state.three.agentMeshes.forEach(avatar => {
      const isTarget = avatar.data.id === agent.id;
      if (avatar.selRing) avatar.selRing.visible = isTarget;
    });

    // Populate Top Selected Element Card (below viewport)
    const elIcon = document.getElementById('selectedIcon');
    const elTitle = document.getElementById('selectedTitle');
    const elBadge = document.getElementById('selectedTypeBadge');
    const elCoord = document.getElementById('selectedCoord');
    const elFloors = document.getElementById('selectedFloors');
    const elMaterials = document.getElementById('selectedMaterials');
    const elConn = document.getElementById('selectedStreetConn');
    const subTitle = document.getElementById('subPanelTitle');
    const pills = document.getElementById('furnishingPills');

    const isSleepingInside = isAgentSleeping(agent);
    const houseNumber = agent.home_house_index || 1;

    const isHydrating = agent.action === 'HYDRATE';
    const roleIcon = getAgentRoleIcon(agent.role);
    const roleColor = agent.color || state.roles[agent.role]?.color || '#10b981';

    if (elIcon) elIcon.textContent = isSleepingInside ? '💤' : (isHydrating ? '💧' : roleIcon);
    if (elTitle) {
      if (isSleepingInside) {
        elTitle.textContent = `${agent.name || agent.id} · House #${houseNumber} Resident`;
      } else {
        elTitle.textContent = `${agent.name || agent.id} · ${agent.role || 'Citizen'}`;
      }
    }
    if (elBadge) {
      if (isSleepingInside) {
        elBadge.textContent = `🏠 Inside House #${houseNumber} 💤 ASLEEP`;
        elBadge.className = 'text-[10px] px-2.5 py-0.5 rounded font-mono font-bold badge-inside-sleep badge-inside-sleep-pulse';
        elBadge.style.backgroundColor = '';
        elBadge.style.color = '';
        elBadge.style.borderColor = '';
      } else if (isHydrating) {
        elBadge.textContent = '💧 DRINK_WATER';
        elBadge.className = 'text-[10px] px-2.5 py-0.5 rounded font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-400/60 shadow-[0_0_10px_rgba(6,182,212,0.4)]';
        elBadge.style.backgroundColor = 'rgba(6, 182, 212, 0.2)';
        elBadge.style.color = '#38bdf8';
        elBadge.style.borderColor = 'rgba(56, 189, 248, 0.6)';
      } else {
        elBadge.textContent = (agent.role || 'AGENT').toUpperCase();
        elBadge.className = 'text-[10px] px-2 py-0.5 rounded font-mono font-bold';
        elBadge.style.backgroundColor = `${roleColor}33`;
        elBadge.style.color = roleColor;
        elBadge.style.borderColor = `${roleColor}66`;
      }
    }

    const posX = Math.round(agent.position.x || 500);
    const posZ = Math.round(agent.position.z || 500);
    if (elCoord) elCoord.textContent = `X: ${posX}m · Z: ${posZ}m (Substrate Grid)`;
    if (elFloors) {
      elFloors.textContent = isSleepingInside
        ? `Home: Dwelling #${houseNumber} (Inside Resting)`
        : `Home: Dwelling #${houseNumber}`;
    }
    if (elMaterials) elMaterials.textContent = `Wallet: ${agent.homeostasis ? agent.homeostasis.currency : 25} C · Prop: ${state.roles[agent.role]?.prop || 'tool'}`;
    if (elConn) {
      elConn.textContent = isSleepingInside
        ? `Status: 🏠 Inside House #${houseNumber} 💤 ASLEEP`
        : `Action: ${getAgentDisplayActivity(agent)}`;
    }

    if (subTitle) subTitle.textContent = '8-Drive Chebyshev Homeostatic Gauges (Phase 1.2)';

    // Compute Augmented Chebyshev Scalarization Metric: L_inf = max_i w_i |s_i - s_i*|
    const h = agent.homeostasis || {
      food: 78, hydration: 84, rest: 72, health: 90,
      currency: 24, shelter: 95, tools: 65, kinship: 55
    };

    const drives = [
      { name: 'Food', val: h.food, target: 100, color: 'text-emerald-400', barBg: 'bg-emerald-500' },
      { name: 'Hydration', val: h.hydration, target: 100, color: 'text-cyan-400', barBg: 'bg-cyan-500' },
      { name: 'Rest', val: h.rest, target: 100, color: 'text-indigo-400', barBg: 'bg-indigo-500' },
      { name: 'Health', val: h.health, target: 100, color: 'text-rose-400', barBg: 'bg-rose-500' },
      { name: 'Currency', val: Math.min(100, Math.round(h.currency * 2)), target: 100, color: 'text-amber-400', barBg: 'bg-amber-500', rawText: `${h.currency} C` },
      { name: 'Shelter', val: h.shelter, target: 100, color: 'text-yellow-400', barBg: 'bg-yellow-500' },
      { name: 'Tools', val: h.tools, target: 100, color: 'text-purple-400', barBg: 'bg-purple-500' },
      { name: 'Kinship', val: h.kinship, target: 100, color: 'text-pink-400', barBg: 'bg-pink-500' }
    ];

    let maxDeficiency = 0;
    let bottleneckDrive = drives[0].name;
    drives.forEach(d => {
      const def = (d.target - d.val) / d.target;
      if (def > maxDeficiency) {
        maxDeficiency = def;
        bottleneckDrive = d.name;
      }
    });

    const chebyshevScore = (1 - maxDeficiency).toFixed(3);

    if (pills) {
      pills.innerHTML = `
        <div class="w-full space-y-2 pt-1 font-mono text-xs">
          <div class="p-2 rounded bg-slate-950/80 border border-cyan-800/40 flex items-center justify-between text-[11px]">
            <span>Chebyshev Metric (L∞): <strong class="text-cyan-300">${chebyshevScore}</strong></span>
            <span class="text-rose-400 font-bold">Bottleneck: ${bottleneckDrive}</span>
          </div>

          <div class="grid grid-cols-2 gap-2 text-[10px]">
            ${drives.map(d => `
              <div class="bg-slate-950/60 p-1.5 rounded border border-slate-800/80">
                <div class="flex justify-between mb-0.5">
                  <span class="text-slate-400">${d.name}</span>
                  <span class="${d.color} font-bold">${d.rawText || `${d.val}%`}</span>
                </div>
                <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div class="h-full ${d.barBg} rounded-full" style="width: ${Math.min(100, d.val)}%"></div>
                </div>
              </div>
            `).join('')}
          </div>

          <div class="flex items-center justify-between pt-2">
            <button id="btnToggleFollowCam" class="px-2.5 py-1 text-[11px] rounded bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-700/50 flex items-center gap-1">
              <span>📹</span> <span>${state.followingAgentId ? 'Exit Follow Cam' : 'Follow in 3rd Person'}</span>
            </button>
            <span class="text-slate-500 text-[10px]">Target: ${agent.target?.label || 'West Farms'}</span>
          </div>
        </div>
      `;

      const btnFollow = document.getElementById('btnToggleFollowCam');
      if (btnFollow) {
        btnFollow.addEventListener('click', () => {
          if (state.followingAgentId) {
            state.followingAgentId = null;
            btnFollow.innerHTML = '<span>📹</span> <span>Follow in 3rd Person</span>';
          } else {
            state.followingAgentId = agent.id;
            btnFollow.innerHTML = '<span>📹</span> <span>Exit Follow Cam</span>';
          }
        });
      }
    }

    // Populate Sliding Inspector Drawer Elements
    const drawerIcon = document.getElementById('agentDrawerIcon');
    const drawerName = document.getElementById('agentDrawerName');
    const drawerRole = document.getElementById('agentDrawerRole');
    const drawerBadge = document.getElementById('agentDrawerStateBadge');
    const drawerAct = document.getElementById('agentDrawerActivityText');
    const chebyshevVal = document.getElementById('chebyshevMetricValue');

    if (drawerIcon) {
      if (isSleepingInside) {
        drawerIcon.textContent = '💤';
      } else if (isHydrating) {
        drawerIcon.textContent = '💧';
      } else {
        drawerIcon.textContent = roleIcon;
      }
    }
    if (drawerName) drawerName.textContent = `${agent.name || agent.id}`;
    if (drawerRole) {
      drawerRole.textContent = isSleepingInside
        ? `Role: ${(agent.role || 'CITIZEN').toUpperCase()} · 🏠 Resting in House #${houseNumber}`
        : `Role: ${(agent.role || 'CITIZEN').toUpperCase()} · Home: House #${houseNumber}`;
    }
    if (drawerBadge) {
      if (isSleepingInside) {
        drawerBadge.textContent = `🏠 Inside House #${houseNumber} 💤 ASLEEP`;
        drawerBadge.className = 'text-[10px] px-2.5 py-1 rounded font-bold badge-inside-sleep badge-inside-sleep-pulse';
        drawerBadge.style.color = '';
        drawerBadge.style.borderColor = '';
        drawerBadge.style.backgroundColor = '';
      } else if (isHydrating) {
        drawerBadge.textContent = '💧 DRINK_WATER';
        drawerBadge.className = 'text-[10px] px-2.5 py-0.5 rounded font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-400/60 shadow-[0_0_10px_rgba(6,182,212,0.4)]';
        drawerBadge.style.color = '#38bdf8';
        drawerBadge.style.borderColor = 'rgba(56, 189, 248, 0.6)';
        drawerBadge.style.backgroundColor = 'rgba(6, 182, 212, 0.2)';
      } else {
        drawerBadge.textContent = agent.action || 'ACTIVE';
        drawerBadge.className = 'text-[10px] px-2 py-0.5 rounded font-bold';
        drawerBadge.style.color = roleColor;
        drawerBadge.style.borderColor = `${roleColor}80`;
        drawerBadge.style.backgroundColor = `${roleColor}26`;
      }
    }
    if (drawerAct) {
      drawerAct.textContent = getAgentDisplayActivity(agent);
    }
    if (chebyshevVal) {
      chebyshevVal.textContent = `${chebyshevScore} (${maxDeficiency < 0.25 ? 'Equilibrium' : 'Bottleneck: ' + bottleneckDrive})`;
    }

    // Update 8 Homeostasis Gauges in Drawer
    const updateGauge = (prefix, val, textSuffix = '%') => {
      const elText = document.getElementById(`gauge${prefix}Text`);
      const elBar = document.getElementById(`gauge${prefix}Bar`);
      if (elText) elText.textContent = `${val}${textSuffix}`;
      if (elBar) elBar.style.width = `${Math.min(100, Math.max(0, val))}%`;
    };

    updateGauge('Food', h.food);
    updateGauge('Hydration', h.hydration);
    updateGauge('Rest', h.rest);
    updateGauge('Health', h.health);
    updateGauge('Currency', Math.min(100, Math.round(h.currency * 2)), ` (${h.currency} C)`);
    updateGauge('Shelter', h.shelter, `% (House #${agent.home_house_index || 1})`);
    updateGauge('Tools', h.tools, `% (${state.roles[agent.role]?.prop || 'Tool'})`);
    updateGauge('Kinship', h.kinship, `% (${agent.role === 'Farmer' ? '3 Kin' : '2 Peers'})`);

    // Update Drawer Inventory Chips
    const invChips = document.getElementById('agentInventoryChips');
    if (invChips) {
      invChips.innerHTML = `
        <span class="px-2 py-0.5 rounded bg-slate-800 text-amber-300">🌾 Grain: ${Math.round(h.food * 0.1)}</span>
        <span class="px-2 py-0.5 rounded bg-slate-800 text-emerald-300">🪵 Wood: 3</span>
        <span class="px-2 py-0.5 rounded bg-slate-800 text-cyan-300">🪨 Stone: 2</span>
        <span class="px-2 py-0.5 rounded bg-purple-950/80 text-purple-300 border border-purple-700/50">COMMUNAL SILO: AUTHORIZED</span>
      `;
    }

    // Trigger sliding drawer open if helper is exposed and requested
    if (openDrawer && typeof window.evolzenOpenInspector === 'function') {
      window.evolzenOpenInspector('agent', agent);
    }

    // Synchronize Agora Order Book
    syncOrderBookWithAgent(agent.id);
  }

  function inspectHouse(house, openDrawer = false) {
    const arch = house.arch || state.archetypes[house.archId] || state.archetypes[0];
    const elIcon = document.getElementById('selectedIcon');
    const elTitle = document.getElementById('selectedTitle');
    const elBadge = document.getElementById('selectedTypeBadge');
    const elCoord = document.getElementById('selectedCoord');
    const elFloors = document.getElementById('selectedFloors');
    const elMaterials = document.getElementById('selectedMaterials');
    const elConn = document.getElementById('selectedStreetConn');
    const subTitle = document.getElementById('subPanelTitle');
    const pills = document.getElementById('furnishingPills');

    if (elIcon) elIcon.textContent = '🏡';
    if (elTitle) elTitle.textContent = `House #${String(house.index).padStart(3, '0')} · ${arch.name}`;
    if (elBadge) {
      elBadge.textContent = `TYPE ${house.archId}`;
      elBadge.style.backgroundColor = `${arch.hex}33`;
      elBadge.style.color = arch.hex;
      elBadge.style.borderColor = `${arch.hex}66`;
    }

    if (elCoord) elCoord.textContent = `X: ${house.x}m · Z: ${house.z}m (${house.w}×${house.d}m)`;
    if (elFloors) elFloors.textContent = `${arch.floors} Floors · ${arch.height}m Height · ${arch.chimney} Chimney`;
    if (elMaterials) elMaterials.textContent = `${arch.walls} / ${arch.roof}`;

    const residents = (state.agents || []).filter(a => a.home_house_index === house.index);
    const sleepingResidents = residents.filter(a => isAgentSleeping(a));
    if (sleepingResidents.length > 0) {
      if (elConn) elConn.textContent = `Occupancy: ${sleepingResidents.length} Citizen${sleepingResidents.length > 1 ? 's' : ''} Asleep Inside 💤`;
    } else if (residents.length > 0) {
      if (elConn) elConn.textContent = `Occupancy: ${residents.length} Resident${residents.length > 1 ? 's' : ''} (Outside Active)`;
    } else {
      if (elConn) elConn.textContent = 'WIRED: Connected to Road Network';
    }

    if (subTitle) subTitle.textContent = 'Architectural Manifest & Interior Voxel Inventory';
    if (pills) {
      pills.innerHTML = `
        <div class="flex flex-wrap gap-1.5 text-[11px] font-mono">
          <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">🛋️ Fabric Sofa (FAB)</span>
          <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">📺 CRT TV (TV)</span>
          <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">🍳 Cooking Range</span>
          <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">🛏️ Oak Bed (${arch.floors > 1 ? 'Upper Floor' : 'Ground Floor'})</span>
          <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">🚪 Front Door Facing Street</span>
          <span class="px-2 py-0.5 rounded bg-slate-800 text-cyan-300">🪟 Reflective Glass Windows</span>
        </div>
      `;
    }

    // Populate Drawer Building Section
    const bTitle = document.getElementById('drawerBuildingTitle');
    const bType = document.getElementById('drawerBuildingType');
    if (bTitle) bTitle.textContent = `House #${String(house.index).padStart(3, '0')} · ${arch.name}`;
    if (bType) bType.textContent = `Type ${house.archId} Archetype · ${arch.walls}`;

    if (openDrawer && typeof window.evolzenOpenInspector === 'function') {
      window.evolzenOpenInspector('building', house);
    }
  }

  function inspectCivic(civic, openDrawer = false) {
    const elIcon = document.getElementById('selectedIcon');
    const elTitle = document.getElementById('selectedTitle');
    const elBadge = document.getElementById('selectedTypeBadge');
    const elCoord = document.getElementById('selectedCoord');
    const elFloors = document.getElementById('selectedFloors');
    const elMaterials = document.getElementById('selectedMaterials');
    const elConn = document.getElementById('selectedStreetConn');
    const subTitle = document.getElementById('subPanelTitle');
    const pills = document.getElementById('furnishingPills');

    if (elIcon) elIcon.textContent = civic.icon;
    if (elTitle) elTitle.textContent = civic.name;
    if (elBadge) {
      elBadge.textContent = 'CIVIC CORE';
      elBadge.style.backgroundColor = `${civic.hex}33`;
      elBadge.style.color = civic.hex;
      elBadge.style.borderColor = `${civic.hex}66`;
    }

    if (elCoord) elCoord.textContent = `Center: X: ${civic.x}m · Z: ${civic.z}m`;
    if (elFloors) elFloors.textContent = `${civic.height}m Height · Reinforced Structural Grid`;
    if (elMaterials) elMaterials.textContent = 'CIVIC REINFORCED CONCRETE & STEEL';
    if (elConn) elConn.textContent = 'MAIN ARTERY INTERSECTION (Direct Access)';

    if (subTitle) subTitle.textContent = 'Civic Subsystem Function';
    if (pills) {
      pills.innerHTML = `
        <div class="space-y-1.5 text-[11px] font-mono">
          <div class="text-cyan-300">${civic.desc}</div>
          <div class="flex gap-2">
            <span class="px-2 py-0.5 rounded bg-slate-800 text-amber-300">⚡ Grid Priority: Tier 1</span>
            <span class="px-2 py-0.5 rounded bg-slate-800 text-purple-300">🔒 Invariant Guarded</span>
          </div>
        </div>
      `;
    }

    const bTitle = document.getElementById('drawerBuildingTitle');
    const bType = document.getElementById('drawerBuildingType');
    if (bTitle) bTitle.textContent = civic.name;
    if (bType) bType.textContent = `Civic Anchor · ${civic.desc}`;

    if (openDrawer && typeof window.evolzenOpenInspector === 'function') {
      window.evolzenOpenInspector('building', civic);
    }
  }

  function syncOrderBookWithAgent(agentId) {
    const rows = document.querySelectorAll('#bidsTableBody > div, #asksTableBody > div');
    rows.forEach(r => {
      const text = r.textContent;
      if (text.includes(agentId)) {
        r.classList.add('order-agent-match');
      } else {
        r.classList.remove('order-agent-match');
      }
    });
  }

  // =========================================================================
  // 9. Simulation Cockpit Controls, Speed & Drought Trigger
  // =========================================================================
  function initSimulationControls() {
    const btnPlayPause = document.getElementById('btnPlayPause');
    const btnStep1 = document.getElementById('btnStep1');
    const btnStep5 = document.getElementById('btnStep5');
    const btnStep25 = document.getElementById('btnStep25');
    const btnReset = document.getElementById('btnReset');

    if (btnPlayPause) btnPlayPause.addEventListener('click', togglePlayPause);
    if (btnStep1) btnStep1.addEventListener('click', () => stepSimulation(1));
    if (btnStep5) btnStep5.addEventListener('click', () => stepSimulation(5));
    if (btnStep25) btnStep25.addEventListener('click', () => stepSimulation(25));
    if (btnReset) btnReset.addEventListener('click', resetSimulation);
  }

  function initSpeedControls() {
    const speedConfigs = {
      '0.5x': { interval: 1600, factor: 0.6 },
      '1x': { interval: 850, factor: 1.0 },
      '2x': { interval: 450, factor: 1.8 },
      '5x': { interval: 200, factor: 3.5 },
      '10x': { interval: 100, factor: 6.0 }
    };

    const speedButtons = document.querySelectorAll('.speed-btn, .btn-speed, .neu-speed-btn, [data-speed]');
    speedButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        let sp = btn.dataset.speed;
        if (!sp.endsWith('x')) sp = `${sp}x`;
        if (speedConfigs[sp]) {
          setSimulationSpeed(sp, speedConfigs[sp].interval, speedConfigs[sp].factor);
        }
      });
    });

    // Listen to custom speed event from UI controller
    window.addEventListener('evolzen-speed-change', (e) => {
      if (e.detail && e.detail.speed) {
        let sp = e.detail.speed;
        if (!sp.endsWith('x')) sp = `${sp}x`;
        if (speedConfigs[sp]) {
          setSimulationSpeed(sp, speedConfigs[sp].interval, speedConfigs[sp].factor);
        }
      }
    });
  }

  function setSimulationSpeed(speed, intervalMs, factor) {
    state.simSpeed = speed;
    state.simIntervalMs = intervalMs;
    state.simSpeedFactor = factor;

    document.querySelectorAll('.speed-btn, .btn-speed, .neu-speed-btn, [data-speed]').forEach(b => {
      let sp = b.dataset.speed;
      if (!sp.endsWith('x')) sp = `${sp}x`;
      const isMatch = sp === speed;
      b.classList.toggle('active', isMatch);
    });

    if (state.isRunning) {
      if (state.timer) clearInterval(state.timer);
      state.timer = setInterval(() => stepSimulation(1), state.simIntervalMs);
      fetch('/api/sim/autoplay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: true, interval_ms: state.simIntervalMs })
      }).catch(() => {});
    }
  }

  function initDroughtControl() {
    const droughtButtons = [
      document.getElementById('btnDrought'),
      document.getElementById('btnDroughtShock'),
      document.getElementById('btnTriggerDrought')
    ].filter(Boolean);
    droughtButtons.forEach(btn => {
      btn.addEventListener('click', triggerDroughtShock);
    });
  }

  async function triggerDroughtShock() {
    state.isDroughtActive = true;
    console.log('[EVOLZEN] Triggering Drought Shock across 10 West Farm Belts...');

    // Parched crop visual effect in 3D
    state.three.cropMaterials.forEach(m => {
      m.color.setHex(0x78350f);
      m.emissive.setHex(0x451a03);
    });

    // Notify backend
    try {
      let res = await fetch('/api/environment/drought', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: true, severity: 0.60 })
      });
      if (!res.ok) {
        res = await fetch('/api/sim/drought', { method: 'POST' });
      }
    } catch (e) {
      console.warn('Backend drought call fallback', e);
    }

    // Visual HUD alert
    const badge = document.getElementById('currentTickBadge');
    if (badge) {
      badge.textContent = `${badge.textContent} [DROUGHT SHOCK]`;
      badge.style.color = '#ef4444';
    }

    await Promise.all([fetchEnvironmentState(), fetchEconomyState(), fetchAgentsRoster()]);
    renderLocationPools();
    renderResourceChart();
    renderOrderBook();
    renderLorenzCurve();
    syncAgentMeshes();
    if (typeof window.evolzenRenderCensus === 'function') window.evolzenRenderCensus();

    setTimeout(() => {
      state.isDroughtActive = false;
      state.three.cropMaterials.forEach(m => {
        m.color.setHex(0xfbbf24);
        m.emissive.setHex(0xd97706);
      });
      if (badge) badge.style.color = '#22d3ee';
      fetch('/api/environment/drought', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: false })
      }).catch(() => {});
    }, 7000);
  }

  function togglePlayPause() {
    state.isRunning = !state.isRunning;
    const playIcon = document.getElementById('playIcon');
    const playText = document.getElementById('playText');
    const btn = document.getElementById('btnPlayPause');

    if (state.isRunning) {
      if (playIcon) playIcon.textContent = '⏸';
      if (playText) playText.textContent = 'PAUSE';
      if (btn) btn.className = 'btn-tactile btn-tactile-cyan px-3.5 py-1.5 text-xs font-bold flex items-center gap-1.5 active';
      state.timer = setInterval(() => stepSimulation(1), state.simIntervalMs);
      fetch('/api/sim/autoplay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: true, interval_ms: state.simIntervalMs })
      }).catch(() => {});
    } else {
      if (playIcon) playIcon.textContent = '▶';
      if (playText) playText.textContent = 'RUN';
      if (btn) btn.className = 'btn-tactile px-3.5 py-1.5 text-xs font-bold flex items-center gap-1.5';
      if (state.timer) {
        clearInterval(state.timer);
        state.timer = null;
      }
      fetch('/api/sim/autoplay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: false })
      }).catch(() => {});
    }
  }

  async function stepSimulation(count = 1) {
    try {
      let res = await fetch('/api/environment/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps: count })
      });
      if (!res.ok) {
        res = await fetch('/api/sim/step', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ steps: count })
        });
      }
      const data = await res.json();
      if (data && state.envState) {
        if (data.tick !== undefined) state.envState.tick = data.tick;
        if (data.locations) state.envState.locations = data.locations;
        if (data.communal_silo) state.envState.communal_silo = data.communal_silo;
        if (data.drought) state.envState.drought = data.drought;
        if (data.step_index !== undefined) state.envState.step_index = data.step_index;
        if (data.world_time) state.envState.world_time = data.world_time;
        if (data.sleeping_houses) state.envState.sleeping_houses = data.sleeping_houses;
        if (data.farm_plots) state.envState.farm_plots = data.farm_plots;
      }
      if (data.order_book && state.economyState) {
        state.economyState.order_book = data.order_book;
        renderOrderBook();
      }
      if (data.agents && data.agents.length > 0) {
        state.agents = data.agents;
      }
      updateSimulationHUD();
      renderLocationPools();
      renderResourceChart();

      syncAgentMeshes();

      if (state.selectedAgentId) {
        const cur = state.agents.find(a => a.id === state.selectedAgentId);
        if (cur) inspectAgent(cur, false, false);
      }

      const activeTour = state.cinematicTour || state.spectate;
      if (activeTour && activeTour.active && activeTour.currentAgent) {
        const liveAgent = state.agents.find(a => a.id === activeTour.currentAgent.id);
        if (liveAgent) {
          activeTour.currentAgent = liveAgent;
          updateCinematicTourHUD(liveAgent);
        }
      }

      if (typeof window.evolzenRenderCensus === 'function') {
        window.evolzenRenderCensus();
      }
    } catch (e) {
      console.warn('Error during stepSimulation:', e);
    }
  }

  // Population Census Roster Controller
  let censusActiveRole = 'ALL';
  let censusSearchQuery = '';

  function renderPopulationCensus() {
    const container = document.getElementById('censusListContainer');
    const countBadge = document.getElementById('censusCountBadge');
    if (!container || !state.agents || state.agents.length === 0) return;

    let filtered = state.agents;
    if (censusActiveRole !== 'ALL') {
      filtered = filtered.filter(a => a.role === censusActiveRole);
    }
    if (censusSearchQuery && censusSearchQuery.trim()) {
      const q = censusSearchQuery.toLowerCase();
      filtered = filtered.filter(a => 
        (a.name && a.name.toLowerCase().includes(q)) ||
        (a.role && a.role.toLowerCase().includes(q)) ||
        (a.id && a.id.toLowerCase().includes(q)) ||
        (getAgentDisplayActivity(a).toLowerCase().includes(q))
      );
    }

    if (countBadge) {
      countBadge.textContent = `${filtered.length} / ${state.agents.length} Citizens`;
    }

    container.innerHTML = filtered.map(agent => {
      const roleIcon = getAgentRoleIcon(agent.role);
      const act = getAgentDisplayActivity(agent);
      const h = agent.homeostasis || { food: 80, rest: 80, health: 85, currency: 20 };
      const isSelected = state.selectedAgentId === agent.id;

      return `
        <div class="neu-panel p-2.5 rounded-lg border ${isSelected ? 'border-cyan-400 bg-cyan-950/30' : 'border-slate-800'} hover:border-cyan-500/60 transition-all cursor-pointer census-item" data-agent-id="${agent.id}">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="text-base">${roleIcon}</span>
              <div>
                <span class="text-xs font-bold text-white">${agent.name || agent.id}</span>
                <span class="text-[10px] px-1.5 py-0.2 rounded font-mono ml-1 font-bold" style="color: ${agent.color || '#38bdf8'}; background: ${agent.color || '#38bdf8'}22;">${agent.role}</span>
              </div>
            </div>
            <button class="btn-track-agent px-2 py-0.5 text-[10px] rounded bg-cyan-950/80 hover:bg-cyan-800 text-cyan-300 border border-cyan-700/50 font-mono" data-agent-id="${agent.id}">
              🎯 Focus
            </button>
          </div>
          <div class="mt-1.5 text-[11px] text-cyan-300 font-mono truncate" title="${act}">
            ${act}
          </div>
          <div class="mt-1 flex items-center justify-between text-[10px] text-slate-400 font-mono pt-1 border-t border-slate-800/80">
            <span>🏠 Dwelling #${agent.home_house_index || 1}</span>
            <span>❤️ ${Math.round(h.health || 85)}% · 🍎 ${Math.round(h.food || 80)}% · 💰 ${agent.homeostasis?.currency || 15}C</span>
          </div>
        </div>
      `;
    }).join('');

    container.querySelectorAll('.census-item').forEach(item => {
      item.addEventListener('click', (e) => {
        if (e.target.closest('.btn-track-agent')) return;
        const agId = item.dataset.agentId;
        const ag = state.agents.find(a => a.id === agId);
        if (ag) {
          inspectAgent(ag, true, true);
          const tabAgent = document.getElementById('drawerTabAgent');
          if (tabAgent) tabAgent.click();
        }
      });
    });

    container.querySelectorAll('.btn-track-agent').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const agId = btn.dataset.agentId;
        const ag = state.agents.find(a => a.id === agId);
        if (ag) {
          inspectAgent(ag, true, true);
          state.followingAgentId = ag.id;
          if (state.three.camera && state.three.controls) {
            if (isAgentSleeping(ag)) {
              const hIdx = ag.home_house_index || 1;
              let centerX = ag.position.x, centerZ = ag.position.z, hHeight = 4.5;
              if (state.worldMeta && state.worldMeta.houses && state.worldMeta.houses[hIdx - 1]) {
                const [hx, hz, hw, hd, archId] = state.worldMeta.houses[hIdx - 1];
                centerX = hx + hw / 2;
                centerZ = hz + hd / 2;
                const arch = (state.archetypes && state.archetypes[archId]) || {};
                hHeight = arch.height || 4.5;
              }
              state.three.camTargetPos = new THREE.Vector3(centerX + 3.0, hHeight + 8.0, centerZ + 22.0);
              state.three.camLookAtPos = new THREE.Vector3(centerX, hHeight * 0.75 + 1.2, centerZ);
            } else {
              const camOffset = 38 / Math.SQRT2;
              state.three.camTargetPos = new THREE.Vector3(ag.position.x - camOffset, 18.5, ag.position.z - camOffset);
              state.three.camLookAtPos = new THREE.Vector3(ag.position.x, 6.0, ag.position.z);
            }
          }
        }
      });
    });
  }

  window.evolzenRenderCensus = renderPopulationCensus;

  function initCensusControls() {
    const searchInput = document.getElementById('censusSearchInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        censusSearchQuery = e.target.value;
        renderPopulationCensus();
      });
    }

    const filterBtns = document.querySelectorAll('.census-role-filter');
    filterBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        filterBtns.forEach(b => {
          b.classList.remove('active', 'bg-cyan-950', 'border-cyan-700', 'text-cyan-300', 'font-bold');
          b.classList.add('text-slate-400');
        });
        btn.classList.add('active', 'bg-cyan-950', 'border-cyan-700', 'text-cyan-300', 'font-bold');
        btn.classList.remove('text-slate-400');
        censusActiveRole = btn.dataset.role || 'ALL';
        renderPopulationCensus();
      });
    });
  }

  async function resetSimulation() {
    if (state.isRunning) togglePlayPause();
    try {
      let res = await fetch('/api/environment/reset', { method: 'POST' });
      if (!res.ok) res = await fetch('/api/sim/reset', { method: 'POST' });
      await Promise.all([fetchEnvironmentState(), fetchEconomyState(), fetchAgentsRoster()]);
      updateSimulationHUD();
      renderLocationPools();
      renderResourceChart();
      renderOrderBook();
      renderLorenzCurve();
      syncAgentMeshes();
    } catch (e) {
      console.warn('Error during resetSimulation:', e);
    }
  }

  function updateSimulationHUD() {
    if (!state.envState) return;
    const badge = document.getElementById('currentTickBadge');
    if (badge) badge.textContent = `TICK #${state.envState.tick || 142}`;

    // Diurnal World Time & Sleep Manifest Telemetry
    const worldTime = state.envState.world_time || {
      hour: 8,
      minute: 0,
      phase: 'DAY',
      is_night: false,
      formatted: '08:00 AM',
      day_count: 1
    };

    const elTimeClock = document.getElementById('worldTimeClock') || document.getElementById('worldTimeDisplay');
    if (elTimeClock) {
      elTimeClock.textContent = worldTime.formatted || '08:00 AM';
    }

    const elPhaseBadge = document.getElementById('worldTimePhaseBadge');
    if (elPhaseBadge) {
      const phase = worldTime.phase || (worldTime.is_night ? 'NIGHT' : 'DAY');
      elPhaseBadge.textContent = phase;
      elPhaseBadge.className = 'text-[9px] font-mono font-black px-1.5 py-0.5 rounded border transition-colors';
      switch (phase) {
        case 'DAWN':
          elPhaseBadge.classList.add('diurnal-phase-dawn');
          break;
        case 'SUNSET':
          elPhaseBadge.classList.add('diurnal-phase-sunset');
          break;
        case 'NIGHT':
          elPhaseBadge.classList.add('diurnal-phase-night');
          break;
        case 'DAY':
        default:
          elPhaseBadge.classList.add('diurnal-phase-day');
          break;
      }
    }

    const elPhaseIcon = document.getElementById('worldTimePhaseIcon');
    if (elPhaseIcon) {
      let icon = '☀️';
      switch (worldTime.phase) {
        case 'DAWN': icon = '🌅'; break;
        case 'SUNSET': icon = '🌇'; break;
        case 'NIGHT': icon = '🌙'; break;
        case 'DAY': default: icon = '☀️'; break;
      }
      elPhaseIcon.textContent = icon;
    }

    const elDay = document.getElementById('worldTimeDay');
    if (elDay) {
      elDay.textContent = `DAY ${worldTime.day_count || 1}`;
    }

    // Calculate sleeping citizens count
    let sleepingCount = 0;
    if (state.envState.sleeping_houses && typeof state.envState.sleeping_houses === 'object') {
      for (const h in state.envState.sleeping_houses) {
        sleepingCount += (state.envState.sleeping_houses[h] || []).length;
      }
    } else if (state.agents) {
      sleepingCount = state.agents.filter(a => a.action === 'SLEEP_NIGHT').length;
      if (sleepingCount === 0 && worldTime.is_night) {
        sleepingCount = state.agents.length || 64;
      }
    } else if (worldTime.is_night) {
      sleepingCount = 64;
    }

    const elSleeping = document.getElementById('worldTimeSleepingCount');
    if (elSleeping) {
      elSleeping.textContent = `${sleepingCount} SLEEPING`;
      if (worldTime.is_night) {
        elSleeping.className = 'text-indigo-300 font-bold';
      } else {
        elSleeping.className = 'text-slate-400 font-normal';
      }
    }

    // Viewport bottom telemetry time
    const elBottomTime = document.getElementById('viewportBottomTime');
    if (elBottomTime) {
      elBottomTime.textContent = `${worldTime.formatted || '08:00 AM'} · ${worldTime.phase || 'DAY'}`;
    }
    const elBottomIcon = document.getElementById('viewportBottomTimeIcon');
    if (elBottomIcon) {
      let icon = '☀️';
      switch (worldTime.phase) {
        case 'DAWN': icon = '🌅'; break;
        case 'SUNSET': icon = '🌇'; break;
        case 'NIGHT': icon = '🌙'; break;
        case 'DAY': default: icon = '☀️'; break;
      }
      elBottomIcon.textContent = icon;
    }
  }

  // =========================================================================
  // 10. View Mode, Layout Switcher & Camera Bookmarks
  // =========================================================================
  function initViewModeControls() {
    const btn3D = document.getElementById('btnView3D');
    const btn2D = document.getElementById('btnView2D');
    const threeContainer = document.getElementById('threeContainer');
    const canvas2D = document.getElementById('worldMapCanvas');
    const controls2D = document.getElementById('map2dControls');

    if (btn3D) {
      btn3D.addEventListener('click', () => {
        state.viewMode = '3d';
        btn3D.classList.add('active');
        if (btn2D) btn2D.classList.remove('active');
        if (threeContainer) { threeContainer.classList.remove('hidden'); threeContainer.classList.add('block'); }
        if (canvas2D) canvas2D.classList.add('hidden');
        if (controls2D) controls2D.classList.add('hidden');
        requestAnimationFrame(() => handleThreeResize());
      });
    }

    if (btn2D) {
      btn2D.addEventListener('click', () => {
        state.viewMode = '2d';
        btn2D.classList.add('active');
        if (btn3D) btn3D.classList.remove('active');
        if (threeContainer) { threeContainer.classList.add('hidden'); threeContainer.classList.remove('block'); }
        if (canvas2D) canvas2D.classList.remove('hidden');
        if (controls2D) controls2D.classList.remove('hidden');
        render2DWorldMap();
      });
    }

    // Day / Night Bloom Lighting Toggle
    const btnLight = document.getElementById('btnToggleDayNight');
    const lightIcon = document.getElementById('lightIcon');
    const lightLabel = document.getElementById('lightLabel');

    if (btnLight) {
      btnLight.addEventListener('click', () => {
        state.isNightMode = !state.isNightMode;
        if (state.isNightMode) {
          if (lightIcon) lightIcon.textContent = '🌙';
          if (lightLabel) lightLabel.textContent = 'Night Bloom';
          applyNightLighting();
        } else {
          if (lightIcon) lightIcon.textContent = '☀️';
          if (lightLabel) lightLabel.textContent = 'Day Light';
          applyDayLighting();
        }
      });
    }

    // Max 3D Theater Toggle
    const btnMax = document.getElementById('btnMaxView');
    const viewport = document.getElementById('worldViewport');
    const maxIcon = document.getElementById('maxViewIcon');
    const maxLabel = document.getElementById('maxViewLabel');

    if (btnMax && viewport) {
      btnMax.addEventListener('click', () => {
        const isMax = viewport.classList.toggle('viewport-maximized');
        if (isMax) {
          if (maxIcon) maxIcon.textContent = '🗗';
          if (maxLabel) maxLabel.textContent = 'Exit Max';
        } else {
          if (maxIcon) maxIcon.textContent = '⛶';
          if (maxLabel) maxLabel.textContent = 'Max View';
        }
        requestAnimationFrame(() => handleThreeResize());
      });

      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && viewport.classList.contains('viewport-maximized')) {
          viewport.classList.remove('viewport-maximized');
          if (maxIcon) maxIcon.textContent = '⛶';
          if (maxLabel) maxLabel.textContent = 'Max View';
          requestAnimationFrame(() => handleThreeResize());
        }
      });
    }

    // Camera Director Bookmarks
    document.querySelectorAll('.cam-bookmark, [data-focus]').forEach(btn => {
      btn.addEventListener('click', () => {
        state.followingAgentId = null;
        const focus = btn.dataset.focus;
        switch (focus) {
          case 'orbital':
            tweenCamera(new THREE.Vector3(500, 520, 1200), new THREE.Vector3(500, 0, 500));
            break;
          case 'civic':
          case 'agora':
            tweenCamera(new THREE.Vector3(550, 75, 760), new THREE.Vector3(550, 12, 650));
            break;
          case 'farms':
            tweenCamera(new THREE.Vector3(80, 95, 620), new THREE.Vector3(50, 10, 500));
            break;
          case 'silo':
          case 'granary':
            tweenCamera(new THREE.Vector3(520, 75, 730), new THREE.Vector3(520, 15, 620));
            break;
          case 'hospital':
            tweenCamera(new THREE.Vector3(450, 65, 630), new THREE.Vector3(450, 18, 550));
            break;
          case 'residential':
          case 'houses':
            tweenCamera(new THREE.Vector3(280, 90, 360), new THREE.Vector3(240, 8, 270));
            break;
          case 'agent':
          case 'follow':
            if (state.selectedAgentId) {
              state.followingAgentId = state.selectedAgentId;
            } else if (state.agents && state.agents.length > 0) {
              inspectAgent(state.agents[0], true, true);
            }
            break;
          case 'shield':
            tweenCamera(new THREE.Vector3(500, 240, 840), new THREE.Vector3(500, 30, 500));
            break;
          case 'spectate':
            toggleSpectatorMode();
            break;
        }
      });
    });

    // Layer Visibility Toggles
    document.querySelectorAll('.layer-toggle').forEach(btn => {
      btn.addEventListener('click', () => {
        const layer = btn.dataset.layer;
        state.three.layers[layer] = !state.three.layers[layer];
        btn.classList.toggle('active', state.three.layers[layer]);

        if (layer === 'houses' && state.three.housesGroup) state.three.housesGroup.visible = state.three.layers.houses;
        if (layer === 'civic' && state.three.civicGroup) state.three.civicGroup.visible = state.three.layers.civic;
        if (layer === 'farms' && state.three.farmsGroup) state.three.farmsGroup.visible = state.three.layers.farms;
        if (layer === 'agents' && state.three.agentsGroup) state.three.agentsGroup.visible = state.three.layers.agents;
        if (layer === 'shield' && state.three.shieldMesh) state.three.shieldMesh.visible = state.three.layers.shield;

        render2DWorldMap();
      });
    });
  }

  function tweenCamera(targetPos, lookAtPos) {
    if (!state.three.camera || !state.three.controls) return;
    state.three.camTargetPos = targetPos;
    state.three.camLookAtPos = lookAtPos;
  }

  // Dynamic Workspace Layout Switcher (Unified Cockpit / Split / Theater / Focus)
  function initLayoutControls() {
    const btns = document.querySelectorAll('.layout-btn, [data-layout]');
    btns.forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.dataset.layout;
        if (mode) setLayoutMode(mode);
      });
    });
  }

  function setLayoutMode(mode) {
    if (!['unified', 'split', 'theater', 'focus', 'quad'].includes(mode)) mode = 'unified';
    state.layoutMode = mode;

    const workspace = document.getElementById('mainWorkspace');
    const viewport = document.getElementById('worldViewport');

    document.querySelectorAll('.layout-btn, [data-layout]').forEach(btn => {
      const isActive = btn.dataset.layout === mode;
      btn.classList.toggle('active', isActive);
      if (isActive) {
        btn.classList.add('text-cyan-300', 'bg-cyan-950/60', 'border', 'border-cyan-700/50', 'font-bold');
        btn.classList.remove('text-slate-400');
      } else {
        btn.classList.remove('text-cyan-300', 'bg-cyan-950/60', 'border', 'border-cyan-700/50', 'font-bold');
        btn.classList.add('text-slate-400');
      }
    });

    if (workspace) {
      workspace.classList.remove(
        'workspace-layout-unified',
        'workspace-layout-split',
        'workspace-layout-theater',
        'workspace-layout-quad',
        'workspace-layout-focus',
        'focus-spatial',
        'focus-subsystem'
      );
      workspace.classList.add(`workspace-layout-${mode}`);
    }

    if (viewport) {
      if (mode === 'theater') {
        viewport.classList.add('viewport-maximized');
      } else {
        viewport.classList.remove('viewport-maximized');
      }
    }

    if (mode === 'focus' && workspace) {
      if (state.activeTab === 'tab-map') {
        workspace.classList.add('focus-spatial');
      } else {
        workspace.classList.add('focus-subsystem');
      }
    }

    requestAnimationFrame(() => {
      handleThreeResize();
      if (state.viewMode === '2d') render2DWorldMap();
      renderResourceChart();
      renderLorenzCurve();
      renderPipelineGraph();
    });
  }

  // Subsystem Navigation Handling
  function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab, [data-tab]');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const targetId = tab.dataset.tab;
        if (!targetId) return;

        state.activeTab = targetId;

        if (targetId === 'tab-map') {
          tabs.forEach(t => {
            const isMatch = t.dataset.tab === 'tab-map';
            t.classList.toggle('active', isMatch);
          });
          window.scrollTo({ top: 0, behavior: 'smooth' });
          requestAnimationFrame(() => handleThreeResize());
        } else {
          setSubsystemDock(targetId);
          const dock = document.getElementById('subsystemSection');
          if (dock) dock.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });
    });
  }

  function initSubsystemDock() {
    const pills = document.querySelectorAll('.subsystem-pill, [data-subsystem]');
    pills.forEach(pill => {
      pill.addEventListener('click', () => {
        const subId = pill.dataset.subsystem;
        if (subId) setSubsystemDock(subId);
      });
    });

    const btnFocus = document.getElementById('btnFocusDock');
    if (btnFocus) {
      btnFocus.addEventListener('click', () => {
        if (state.layoutMode === 'focus' && state.activeTab !== 'tab-map') {
          setLayoutMode('unified');
        } else {
          state.activeTab = state.activeSubsystem || 'tab-environment';
          setLayoutMode('focus');
        }
      });
    }
  }

  function setSubsystemDock(subsystemId) {
    // Map between tab-cvt and tab-archive
    let normalizedId = subsystemId;
    if (subsystemId === 'tab-cvt' && !document.getElementById('tab-cvt') && document.getElementById('tab-archive')) {
      normalizedId = 'tab-archive';
    } else if (subsystemId === 'tab-archive' && !document.getElementById('tab-archive') && document.getElementById('tab-cvt')) {
      normalizedId = 'tab-cvt';
    }

    state.activeSubsystem = normalizedId;

    document.querySelectorAll('.subsystem-pill, [data-subsystem]').forEach(pill => {
      const pSub = pill.dataset.subsystem;
      const isActive = pSub === subsystemId || (pSub === 'tab-cvt' && normalizedId === 'tab-archive');
      pill.classList.toggle('active', isActive);
      if (isActive) {
        pill.classList.add('bg-cyan-950/60', 'text-cyan-400', 'border-cyan-700/50', 'font-bold');
        pill.classList.remove('text-slate-400');
      } else {
        pill.classList.remove('bg-cyan-950/60', 'text-cyan-400', 'border-cyan-700/50', 'font-bold');
        pill.classList.add('text-slate-400');
      }
    });

    const container = document.getElementById('subsystemPanesContainer');
    if (container) {
      container.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      const activePane = document.getElementById(normalizedId) || document.getElementById(subsystemId);
      if (activePane) activePane.classList.add('active');
    }

    const badge = document.getElementById('dockActiveBadge');
    if (badge) {
      badge.textContent = subsystemTitles[normalizedId] || subsystemTitles[subsystemId] || 'Phase Active Subsystem';
    }

    document.querySelectorAll('.nav-tab, [data-tab]').forEach(tab => {
      const tTab = tab.dataset.tab;
      const isMatch = tTab === subsystemId || (tTab === 'tab-cvt' && normalizedId === 'tab-archive');
      tab.classList.toggle('active', isMatch);
    });

    if (normalizedId === 'tab-environment') renderResourceChart();
    if (normalizedId === 'tab-economy') renderLorenzCurve();
    if (normalizedId === 'tab-library') renderRuleDag();
    if (normalizedId === 'tab-archive' || normalizedId === 'tab-cvt') renderCvtArchive();
    if (normalizedId === 'tab-pipeline') renderPipelineGraph();
  }

  // =========================================================================
  // 11. Single Unified Cinematic Tour Engine & Fullscreen World Viewing
  // =========================================================================

  function getSectorNameForCoord(x, z) {
    if (x < 140 && z > 250 && z < 750) return 'West Farm Belt & Silos';
    if (x > 420 && x < 580 && z > 420 && z < 580) return 'Central Civic Anchor';
    if (x >= 500 && x <= 650 && z >= 600 && z <= 750) return 'Agora Market & Double-Auction';
    if (x <= 480 && z >= 500 && z <= 620) return 'Civic Hospital Anchor';
    if (x >= 500 && x <= 650 && z <= 500 && z >= 380) return 'Fire Station Emergency Sector';
    if (x > 250 && x < 400 && z > 350 && z < 550) return 'Central Park & Conservatory';
    return 'Residential Dwelling Sector';
  }

  function updateBottomTelemetry(coords, headingStr, elevStr) {
    // 1. Substrate Coordinates (Cleanly docked in bottom bar)
    const elCoords = document.getElementById('substrateCoordinatesStatus') || document.getElementById('mouseCoords');
    if (elCoords && coords) {
      elCoords.textContent = `X: ${coords.x}m · Z: ${coords.z}m`;
    }

    // 2. Compass Heading & Elevation
    const elHdg = document.getElementById('hudCompassHeading');
    if (elHdg && headingStr) {
      elHdg.textContent = headingStr;
    }

    const elElev = document.getElementById('hudElevation');
    if (elElev && elevStr) {
      elElev.textContent = elevStr;
    }

    // 3. Sector Name
    const elSector = document.getElementById('sectorName');
    if (elSector && coords) {
      elSector.textContent = getSectorNameForCoord(coords.x, coords.z);
    }

    // 4. Active Agents Count
    const elAgents = document.getElementById('activeAgentsBadge') || document.getElementById('hudAgentCount');
    if (elAgents && state.agents) {
      elAgents.textContent = `${state.agents.length} Active`;
    }

    // 5. Ensure center floating HUD overlay is tucked away if present
    const centerOverlay = document.getElementById('viewportTopCompassHud');
    if (centerOverlay && centerOverlay.classList.contains('top-3')) {
      centerOverlay.style.pointerEvents = 'none';
    }
  }

  // --- Dedicated Fullscreen World Viewing ---

  function initFullscreenWorldControl() {
    const btnFs = document.getElementById('btnFullscreenWorld');
    const btnExitFs = document.getElementById('btnExitFullscreenWorld');
    const btnMax = document.getElementById('btnMaxView');

    if (btnFs) {
      btnFs.addEventListener('click', toggleFullscreenWorld);
    }
    if (btnExitFs) {
      btnExitFs.addEventListener('click', toggleFullscreenWorld);
    }
    if (btnMax) {
      btnMax.addEventListener('click', toggleFullscreenWorld);
    }

    const onFsChange = () => {
      const viewport = document.getElementById('worldViewport');
      const isNativeFs = Boolean(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
      if (!isNativeFs && viewport && !viewport.classList.contains('viewport-fullscreen-mode')) {
        // Native exited
      }
      updateFullscreenWorldUI();
      handleThreeResize(true);
      requestAnimationFrame(() => handleThreeResize(true));
      setTimeout(() => handleThreeResize(true), 100);
      setTimeout(() => handleThreeResize(true), 300);
    };

    document.addEventListener('fullscreenchange', onFsChange);
    document.addEventListener('webkitfullscreenchange', onFsChange);
    document.addEventListener('mozfullscreenchange', onFsChange);
    document.addEventListener('MSFullscreenChange', onFsChange);
  }

  function isWorldFullscreen() {
    const viewport = document.getElementById('worldViewport') || document.getElementById('threeContainer');
    const fsElem = document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement;
    return Boolean((fsElem && (fsElem === viewport || (viewport && viewport.contains(fsElem)))) || (viewport && (viewport.classList.contains('viewport-fullscreen-mode') || viewport.classList.contains('viewport-maximized'))));
  }

  async function toggleFullscreenWorld() {
    const viewport = document.getElementById('worldViewport') || document.getElementById('threeContainer');
    if (!viewport) return;

    const isFs = isWorldFullscreen();

    try {
      if (isFs) {
        if (document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement) {
          if (document.exitFullscreen) {
            await document.exitFullscreen();
          } else if (document.webkitExitFullscreen) {
            await document.webkitExitFullscreen();
          } else if (document.mozCancelFullScreen) {
            await document.mozCancelFullScreen();
          } else if (document.msExitFullscreen) {
            await document.msExitFullscreen();
          }
        }
        viewport.classList.remove('viewport-fullscreen-mode');
        viewport.classList.remove('viewport-maximized');
        state.fullscreen.active = false;
      } else {
        if (viewport.requestFullscreen) {
          await viewport.requestFullscreen();
        } else if (viewport.webkitRequestFullscreen) {
          await viewport.webkitRequestFullscreen();
        } else if (viewport.mozRequestFullScreen) {
          await viewport.mozRequestFullScreen();
        } else if (viewport.msRequestFullscreen) {
          await viewport.msRequestFullscreen();
        } else {
          viewport.classList.add('viewport-fullscreen-mode');
        }
        viewport.classList.add('viewport-maximized');
        state.fullscreen.active = true;
      }
    } catch (err) {
      console.warn('HTML5 Fullscreen API notice, using CSS fullscreen fallback:', err);
      viewport.classList.toggle('viewport-fullscreen-mode');
      viewport.classList.toggle('viewport-maximized');
      state.fullscreen.active = viewport.classList.contains('viewport-fullscreen-mode') || viewport.classList.contains('viewport-maximized');
    }

    updateFullscreenWorldUI();
    handleThreeResize(true);
    requestAnimationFrame(() => handleThreeResize(true));
    setTimeout(() => handleThreeResize(true), 100);
    setTimeout(() => handleThreeResize(true), 300);
  }

  function updateFullscreenWorldUI() {
    const isFs = isWorldFullscreen();
    const btnFs = document.getElementById('btnFullscreenWorld');
    const iconFs = document.getElementById('fullscreenIcon');
    const labelFs = document.getElementById('fullscreenLabel');
    if (btnFs) {
      if (isFs) {
        btnFs.classList.add('active');
        if (iconFs) iconFs.textContent = '🗗';
        if (labelFs) labelFs.textContent = 'Exit Fullscreen';
        btnFs.title = 'Exit Fullscreen World (Shortcut: F, M or ESC)';
      } else {
        btnFs.classList.remove('active');
        if (iconFs) iconFs.textContent = '⛶';
        if (labelFs) labelFs.textContent = 'Fullscreen World';
        btnFs.title = 'Enter Fullscreen 3D World (Shortcut: F or M)';
      }
    }

    const btnExitFs = document.getElementById('btnExitFullscreenWorld');
    if (btnExitFs) {
      btnExitFs.style.display = isFs ? 'flex' : 'none';
    }

    const btnMax = document.getElementById('btnMaxView');
    const maxIcon = document.getElementById('maxViewIcon');
    const maxLabel = document.getElementById('maxViewLabel');
    if (btnMax) {
      if (isFs) {
        if (maxIcon) maxIcon.textContent = '🗗';
        if (maxLabel) maxLabel.textContent = 'Exit Fullscreen';
      } else {
        if (maxIcon) maxIcon.textContent = '⛶';
        if (maxLabel) maxLabel.textContent = 'Fullscreen World';
      }
    }
  }

  // --- Single Unified Cinematic Tour Engine ---

  function initCinematicTourEngine() {
    const btnTour = document.getElementById('btnCinematicTour');
    const btnSpectate = document.getElementById('btnSpectateMode');
    const btnSpectateTop = document.getElementById('btnSpectateModeTop');
    const btnAuto = document.getElementById('btnTourAuto');
    const btnExit = document.getElementById('btnExitSpectate') || document.getElementById('btnExitTour');
    const btnNextAngle = document.getElementById('btnSpectateNextAngle');
    const btnNextAgent = document.getElementById('btnSpectateNextAgent');
    const bookmarkBtns = document.querySelectorAll('.btn-spectate, .btn-cinematic-tour, [data-focus="spectate"]');

    if (btnTour) {
      btnTour.addEventListener('click', () => toggleCinematicTour());
    }
    if (btnSpectate) {
      btnSpectate.addEventListener('click', () => toggleCinematicTour());
    }
    if (btnSpectateTop) {
      btnSpectateTop.addEventListener('click', () => toggleCinematicTour());
    }
    if (btnAuto) {
      btnAuto.addEventListener('click', () => toggleCinematicTour());
    }
    if (btnExit) {
      btnExit.addEventListener('click', () => stopCinematicTour());
    }
    if (btnNextAngle) {
      btnNextAngle.addEventListener('click', cycleCinematicTourShot);
    }
    if (btnNextAgent) {
      btnNextAgent.addEventListener('click', () => {
        state.cinematicTour.countdownSeconds = 6;
        updateCinematicTourCountdown(6);
        transitionCinematicTourTarget(false);
      });
    }

    bookmarkBtns.forEach(btn => {
      if (btn !== btnTour && btn !== btnSpectate) {
        btn.addEventListener('click', () => toggleCinematicTour());
      }
    });

    // Tour step dots (fallback/guided portfolio)
    const dots = document.querySelectorAll('.tour-dot');
    dots.forEach((dot, idx) => {
      dot.addEventListener('click', () => goToTourStep(idx));
    });
    const btnPrev = document.getElementById('btnTourPrev');
    const btnNext = document.getElementById('btnTourNext');
    if (btnPrev) btnPrev.addEventListener('click', prevTourStep);
    if (btnNext) btnNext.addEventListener('click', nextTourStep);

    renderTourStep(0);
  }

  function toggleCinematicTour(forceState) {
    const shouldBeActive = forceState !== undefined ? Boolean(forceState) : !state.cinematicTour.active;
    if (shouldBeActive) {
      startCinematicTour();
    } else {
      stopCinematicTour();
    }
  }

  function startCinematicTour() {
    if (state.cinematicTour.active) return;
    state.cinematicTour.active = true;
    state.tour.autoPlay = true;

    // Switch view to 3D if in 2D map mode
    if (state.viewMode !== '3d') {
      setViewMode('3d');
    }

    // Reveal Cinematic Letterbox Overlay
    const overlay = document.getElementById('spectateLetterboxOverlay');
    if (overlay) {
      overlay.classList.remove('hidden');
      requestAnimationFrame(() => {
        overlay.classList.remove('opacity-0');
        overlay.classList.add('opacity-100');
      });
    }

    // Update buttons
    updateCinematicTourButtonUI(true);

    // Start immediately with the first role
    transitionCinematicTourTarget(true);

    // Setup 6-second auto-transition timer with 1s countdown in HUD
    state.cinematicTour.countdownSeconds = 6;
    updateCinematicTourCountdown(6);

    if (state.cinematicTour.countdownTimer) clearInterval(state.cinematicTour.countdownTimer);
    state.cinematicTour.countdownTimer = setInterval(() => {
      if (!state.cinematicTour.active) return;
      state.cinematicTour.countdownSeconds--;
      if (state.cinematicTour.countdownSeconds <= 0) {
        state.cinematicTour.countdownSeconds = 6;
        transitionCinematicTourTarget(false);
      }
      updateCinematicTourCountdown(state.cinematicTour.countdownSeconds);
    }, 1000);
  }

  function stopCinematicTour() {
    state.cinematicTour.active = false;
    state.tour.autoPlay = false;

    if (state.cinematicTour.countdownTimer) clearInterval(state.cinematicTour.countdownTimer);
    state.cinematicTour.countdownTimer = null;
    if (state.tour.timer) clearInterval(state.tour.timer);
    state.tour.timer = null;

    // Hide letterbox overlay with fade out
    const overlay = document.getElementById('spectateLetterboxOverlay');
    if (overlay) {
      overlay.classList.remove('opacity-100');
      overlay.classList.add('opacity-0');
      setTimeout(() => {
        if (!state.cinematicTour.active) overlay.classList.add('hidden');
      }, 400);
    }

    // Revert button styling
    updateCinematicTourButtonUI(false);
  }

  function updateCinematicTourButtonUI(isActive) {
    const btnTour = document.getElementById('btnCinematicTour');
    if (btnTour) {
      const text = document.getElementById('cinematicTourText') || btnTour.querySelector('span:not(.rec-dot-indicator)');
      const icon = document.getElementById('cinematicTourIcon');
      if (isActive) {
        btnTour.classList.add('active', 'border-rose-500/80', 'bg-rose-950/80', 'text-rose-200');
        btnTour.classList.remove('border-slate-800');
        if (icon) icon.textContent = '⏹';
        if (text) text.textContent = 'EXIT TOUR';
        btnTour.title = 'Exit Cinematic Tour (Shortcut: C or ESC)';
      } else {
        btnTour.classList.remove('active', 'border-rose-500/80', 'bg-rose-950/80', 'text-rose-200');
        if (icon) icon.textContent = '🎬';
        if (text) text.textContent = 'CINEMATIC TOUR';
        btnTour.title = 'Launch Autonomous 1km Cinematic Tour (Shortcut: C)';
      }
    }

    const btnSpectate = document.getElementById('btnSpectateMode');
    const icon = document.getElementById('spectateIcon');
    const text = document.getElementById('spectateText');
    if (btnSpectate) {
      if (isActive) {
        btnSpectate.className = 'btn-spectate px-2.5 py-1 rounded bg-rose-950/80 hover:bg-rose-900 text-rose-200 border border-rose-500/80 flex items-center gap-1.5 transition-all font-mono font-bold shadow-lg shadow-rose-900/40 active';
        if (icon) icon.textContent = '⏹';
        if (text) text.textContent = 'Exit Tour';
      } else {
        btnSpectate.className = 'btn-spectate px-2.5 py-1 rounded bg-purple-950/70 hover:bg-purple-900/90 text-purple-300 border border-purple-600/50 flex items-center gap-1.5 transition-all font-mono font-bold shadow-sm';
        if (icon) icon.textContent = '🎬';
        if (text) text.textContent = 'Cinematic Tour';
      }
    }

    const btnAuto = document.getElementById('btnTourAuto');
    if (btnAuto) {
      const autoText = document.getElementById('tourAutoText');
      const autoIcon = document.getElementById('tourAutoIcon');
      if (isActive) {
        if (autoText) autoText.textContent = 'Pause Tour';
        if (autoIcon) autoIcon.textContent = '⏸';
      } else {
        if (autoText) autoText.textContent = 'Auto Tour';
        if (autoIcon) autoIcon.textContent = '⚡';
      }
    }
  }

  function cycleCinematicTourShot() {
    const SHOT_TYPES = ['CHASE', 'LOW_ANGLE', 'DRONE_ORBIT', 'FRONTAL'];
    state.cinematicTour.shotAngleIndex = (state.cinematicTour.shotAngleIndex + 1) % SHOT_TYPES.length;
    state.cinematicTour.currentShotType = SHOT_TYPES[state.cinematicTour.shotAngleIndex];

    const elShot = document.getElementById('spectateShotType');
    if (elShot) {
      elShot.textContent = state.cinematicTour.shotNames[state.cinematicTour.currentShotType] || 'OVER-SHOULDER CHASE CAM';
    }
  }

  function updateCinematicTourCountdown(sec) {
    const el = document.getElementById('spectateTimerCountdown');
    if (el) el.textContent = `${sec}s`;
  }

  const TOUR_ROLES = ['Farmer', 'Trader', 'Builder', 'Medic', 'Crafter', 'Generalist'];
  const ROLE_SHOTS = {
    Farmer: 'CHASE',
    Trader: 'LOW_ANGLE',
    Builder: 'DRONE_ORBIT',
    Medic: 'FRONTAL',
    Crafter: 'CHASE',
    Generalist: 'LOW_ANGLE'
  };
  const ROLE_GEAR = {
    Farmer: { hat: 'Straw Hat', tool: 'Pitchfork', landmark: 'West Farm Belt & Silos' },
    Trader: { hat: 'Merchant Beret', tool: 'Coin Pouch', landmark: 'Central Agora Market' },
    Builder: { hat: 'Safety Hardhat', tool: 'Builder Hammer', landmark: 'Municipal Construction Site' },
    Medic: { hat: 'Red Cross Cap', tool: 'Emergency Medkit', landmark: 'Hospital Trauma Center' },
    Crafter: { hat: 'Welding Goggles', tool: 'Tempered Wrench', landmark: 'Timber Workshop Forge' },
    Generalist: { hat: 'Scholar Cap', tool: 'Leather Satchel', landmark: 'Civic Academy & Commons' }
  };

  function transitionCinematicTourTarget(isInitial = false) {
    if (!state.agents || state.agents.length === 0) return;

    if (!isInitial) {
      // Guarantee strict round-robin role transitions: Farmer -> Trader -> Builder -> Medic -> Crafter -> Generalist -> Farmer
      state.cinematicTour.roleIndex = (state.cinematicTour.roleIndex + 1) % TOUR_ROLES.length;
    } else {
      // If user already had an agent selected, start with that agent's role or start at Farmer (0)
      if (state.selectedAgentId) {
        const curAgent = state.agents.find(a => a.id === state.selectedAgentId);
        const curIdx = curAgent ? TOUR_ROLES.indexOf(curAgent.role) : -1;
        state.cinematicTour.roleIndex = curIdx >= 0 ? curIdx : 0;
      } else {
        state.cinematicTour.roleIndex = 0;
      }
    }

    const currentRole = TOUR_ROLES[state.cinematicTour.roleIndex];
    // Showcase distinct camera shot angle tailored for this role
    state.cinematicTour.currentShotType = ROLE_SHOTS[currentRole] || 'CHASE';

    let matchingAgents = state.agents.filter(a => a.role === currentRole);
    if (!matchingAgents || matchingAgents.length === 0) {
      matchingAgents = state.agents;
    }

    // Prioritize active (awake) agents of this role if available
    const awakeAgents = matchingAgents.filter(a => !isAgentSleeping(a));
    const candidateList = awakeAgents.length > 0 ? awakeAgents : matchingAgents;

    const roleAgentIdx = (state.cinematicTour.agentIndexByRole[currentRole] || 0);
    const selectedAgent = candidateList[roleAgentIdx % candidateList.length];
    state.cinematicTour.agentIndexByRole[currentRole] = roleAgentIdx + 1;

    state.cinematicTour.currentAgent = selectedAgent;
    inspectAgent(selectedAgent, true, false);

    // Sync docked console tab for landmark context
    const roleTabs = {
      Farmer: 'tab-environment',
      Trader: 'tab-economy',
      Builder: 'tab-library',
      Medic: 'tab-cvt',
      Crafter: 'tab-library',
      Generalist: 'tab-environment'
    };
    if (roleTabs[currentRole]) {
      setSubsystemDock(roleTabs[currentRole]);
    }

    if (state.cinematicTour.currentShotType === 'DRONE_ORBIT') {
      state.cinematicTour.orbitAngle = Math.random() * Math.PI * 2;
    }

    updateCinematicTourHUD(selectedAgent);
  }

  function updateCinematicTourHUD(agent) {
    if (!agent) return;

    const elName = document.getElementById('spectateCitizenName');
    const elRole = document.getElementById('spectateCitizenRole');
    const elActivity = document.getElementById('spectateCitizenActivity');
    const elShot = document.getElementById('spectateShotType');
    const elPos = document.getElementById('spectatePositionBadge');
    const elVital = document.getElementById('spectateVitalBadge');

    const role = agent.role || 'Citizen';
    const gear = ROLE_GEAR[role] || { hat: 'Cap', tool: 'Tool', landmark: 'Civic Commons' };
    const roleIcon = getAgentRoleIcon(role);

    if (elName) elName.textContent = agent.name || agent.id;
    if (elRole) {
      elRole.textContent = `(${roleIcon} ${role})`;
      const roleColors = {
        Farmer: 'text-emerald-400',
        Trader: 'text-amber-400',
        Builder: 'text-yellow-400',
        Medic: 'text-rose-400',
        Crafter: 'text-purple-400',
        Generalist: 'text-cyan-400'
      };
      elRole.className = `${roleColors[role] || 'text-cyan-400'} font-bold`;
    }

    const isSleeping = isAgentSleeping(agent);
    const houseNumber = agent.home_house_index || 1;

    if (elActivity) {
      if (isSleeping) {
        elActivity.textContent = `🏠 INSIDE HOUSE #${houseNumber} 💤 ASLEEP`;
        elActivity.className = 'text-xs text-sky-300 font-mono font-bold tracking-wide animate-pulse';
      } else {
        const act = getAgentDisplayActivity(agent);
        elActivity.textContent = act.toUpperCase();
        elActivity.className = 'text-xs text-cyan-300 font-mono truncate max-w-[340px]';
      }
    }

    if (elShot) {
      if (isSleeping) {
        elShot.textContent = 'DWELLING FACADE & CHIMNEY ZZZ';
      } else {
        elShot.textContent = state.cinematicTour.shotNames[state.cinematicTour.currentShotType] || 'OVER-SHOULDER CHASE CAM';
      }
    }

    if (elPos) {
      if (isSleeping) {
        elPos.textContent = `HOUSE #${houseNumber} · 🏠 INSIDE · 💤 ASLEEP`;
      } else if (agent.position) {
        elPos.textContent = `📍 ${gear.landmark.toUpperCase()} · X ${Math.round(agent.position.x)}m · Z ${Math.round(agent.position.z)}m`;
      }
    }

    if (elVital) {
      let energy = 95;
      let hydration = 92;
      if (agent.homeostasis) {
        energy = Math.round(agent.homeostasis.rest !== undefined ? agent.homeostasis.rest : 80);
        hydration = Math.round(agent.homeostasis.hydration !== undefined ? agent.homeostasis.hydration : 85);
      } else if (agent.vitals) {
        energy = Math.round((agent.vitals.energy || 0.95) * 100);
        hydration = Math.round((agent.vitals.hydration || 0.9) * 100);
      } else if (agent.drives) {
        energy = Math.round((1 - (agent.drives.exhaustion || 0.05)) * 100);
        hydration = Math.round((1 - (agent.drives.thirst || 0.08)) * 100);
      }
      if (isSleeping) {
        elVital.textContent = `SLEEPING · RESTORING ENERGY (${energy}%)`;
      } else if (agent.action === 'HYDRATE') {
        elVital.textContent = `💧 HYDRATING · WATER ${hydration}% · ENERGY ${energy}%`;
      } else {
        elVital.textContent = `ENERGY: ${energy}% · HYDRATION: ${hydration}% · GEAR: ${gear.hat} & ${gear.tool}`;
      }
    }
  }

  // --- Guided Portfolio Step Navigators (Compatibility) ---

  function goToTourStep(idx) {
    if (idx < 0) idx = 0;
    if (idx >= tourSteps.length) idx = tourSteps.length - 1;
    state.tour.step = idx;
    renderTourStep(idx);
  }

  function nextTourStep() {
    let nextIdx = state.tour.step + 1;
    if (nextIdx >= tourSteps.length) nextIdx = 0;
    goToTourStep(nextIdx);
  }

  function prevTourStep() {
    let prevIdx = state.tour.step - 1;
    if (prevIdx < 0) prevIdx = tourSteps.length - 1;
    goToTourStep(prevIdx);
  }

  function renderTourStep(idx) {
    const step = tourSteps[idx];
    if (!step) return;

    const elBadge = document.getElementById('tourStepBadge');
    const elTitle = document.getElementById('tourStepTitle');
    const elDesc = document.getElementById('tourStepDesc');

    if (elBadge) elBadge.textContent = `STEP ${step.step}/6:`;
    if (elTitle) elTitle.textContent = step.title;
    if (elDesc) elDesc.textContent = step.desc;

    document.querySelectorAll('.tour-dot').forEach((dot, dIdx) => {
      dot.classList.toggle('active', dIdx === idx);
    });

    if (step.subsystem) setSubsystemDock(step.subsystem);
    if (step.camera && state.three.camera) {
      state.followingAgentId = null;
      tweenCamera(step.camera.pos, step.camera.target);
    }
    if (step.action) step.action();
  }

  // Keyboard Shortcuts (Space: Play/Pause, C: Cinematic Tour, F: Fullscreen World, Esc: Exit)
  function initKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;
      const key = e.key.toLowerCase();

      if (e.code === 'Space') {
        e.preventDefault();
        togglePlayPause();
      } else if (key === '+' || key === '=') {
        stepSimulation(1);
      } else if (key === 'u') {
        setLayoutMode('unified');
      } else if (key === 's') {
        setLayoutMode('split');
      } else if (key === 'm' || key === 'f') {
        toggleFullscreenWorld();
      } else if (key === 'c' || key === 't') {
        toggleCinematicTour();
      } else if (e.key === 'Escape') {
        if (isWorldFullscreen()) {
          toggleFullscreenWorld();
        }
        if ((state.cinematicTour && state.cinematicTour.active) || (state.spectate && state.spectate.active)) {
          stopCinematicTour();
        }
      }
    });
  }

  // Aliases for complete backward compatibility
  const initSpectatorEngine = initCinematicTourEngine;
  const initTourEngine = initCinematicTourEngine;
  const toggleSpectatorMode = toggleCinematicTour;
  const startSpectatorMode = startCinematicTour;
  const stopSpectatorMode = stopCinematicTour;
  const cycleSpectatorShot = cycleCinematicTourShot;
  const updateSpectatorCountdown = updateCinematicTourCountdown;
  const transitionSpectatorTarget = transitionCinematicTourTarget;
  const updateSpectatorHUD = updateCinematicTourHUD;
  const toggleAutoTour = toggleCinematicTour;

  // Window exports for UI header and toolbar controls
  window.evolzenToggleCinematicTour = toggleCinematicTour;
  window.evolzenToggleFullscreenWorld = toggleFullscreenWorld;
  window.__evolzenState = state;

  // =========================================================================
  // 12. 2D Orthographic Fallback Map
  // =========================================================================
  function init2DMapCanvas() {
    const canvas = document.getElementById('worldMapCanvas');
    if (!canvas) return;
    state.map2d.canvas = canvas;
    state.map2d.ctx = canvas.getContext('2d');

    const img = new Image();
    img.src = 'world_topdown_map.png';
    img.onload = () => {
      state.map2d.bgImage = img;
      state.map2d.bgLoaded = true;
      if (state.viewMode === '2d') render2DWorldMap();
    };

    const btnIn = document.getElementById('mapZoomIn');
    const btnOut = document.getElementById('mapZoomOut');
    const btnReset = document.getElementById('mapZoomReset');
    if (btnIn) btnIn.addEventListener('click', () => zoom2D(1.25));
    if (btnOut) btnOut.addEventListener('click', () => zoom2D(0.8));
    if (btnReset) btnReset.addEventListener('click', () => {
      state.map2d.scale = 1;
      state.map2d.offsetX = 0;
      state.map2d.offsetY = 0;
      render2DWorldMap();
    });

    canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      zoom2D(e.deltaY < 0 ? 1.15 : 0.85);
    }, { passive: false });
  }

  function zoom2D(factor) {
    const m = state.map2d;
    if (!m.canvas) return;
    const newScale = Math.min(m.maxScale, Math.max(m.minScale, m.scale * factor));
    const cx = m.canvas.width / 2;
    const cy = m.canvas.height / 2;
    m.offsetX = cx - (cx - m.offsetX) * (newScale / m.scale);
    m.offsetY = cy - (cy - m.offsetY) * (newScale / m.scale);
    m.scale = newScale;
    render2DWorldMap();
  }

  function render2DWorldMap() {
    const { ctx, canvas, scale, offsetX, offsetY, bgImage, bgLoaded } = state.map2d;
    if (!ctx || !canvas) return;

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.translate(offsetX, offsetY);
    ctx.scale(scale, scale);

    if (bgLoaded && bgImage) {
      ctx.drawImage(bgImage, 0, 0, 1000, 1000);
    } else {
      ctx.fillStyle = '#050a14';
      ctx.fillRect(0, 0, 1000, 1000);
    }

    if (state.three.layers.farms) {
      ctx.fillStyle = 'rgba(245, 158, 11, 0.18)';
      ctx.fillRect(0, 0, 100, 1000);
    }

    if (state.three.layers.civic) {
      state.civicAnchors.forEach(c => {
        if (c.isZone) {
          ctx.fillStyle = 'rgba(16, 185, 129, 0.25)';
          ctx.fillRect(c.x - c.w / 2, c.z - c.h / 2, c.w, c.h);
        } else {
          ctx.fillStyle = c.hex;
          ctx.beginPath();
          ctx.arc(c.x, c.z, (c.size || 36) / 2, 0, Math.PI * 2);
          ctx.fill();
        }
      });
    }

    if (state.three.layers.houses && state.worldMeta && state.worldMeta.houses) {
      state.worldMeta.houses.forEach(h => {
        const [x, z, w, d, archId] = h;
        const arch = state.archetypes[archId] || state.archetypes[0];
        ctx.fillStyle = arch.hex;
        ctx.fillRect(x, z, w, d);
      });
    }

    if (state.three.layers.agents && state.agents) {
      state.agents.forEach(a => {
        ctx.fillStyle = a.color || '#10b981';
        ctx.beginPath();
        ctx.arc(a.position.x, a.position.z, 3.8, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    ctx.restore();
  }

  // =========================================================================
  // 13. Subsystem Telemetries Rendering Passes
  // =========================================================================

  function renderArchetypeDistribution() {
    const list = document.getElementById('archetypeList');
    if (!list) return;
    const counts = { 0: 71, 1: 62, 2: 77, 3: 66, 4: 69 };
    const total = 345;

    list.innerHTML = Object.entries(state.archetypes).map(([id, arch]) => {
      const count = counts[id] || 0;
      const pct = ((count / total) * 100).toFixed(1);
      return `
        <div class="archetype-row flex items-center justify-between p-1.5 rounded bg-slate-950/40 border border-slate-800/60">
          <div class="flex items-center gap-2">
            <span class="w-3 h-3 rounded-full" style="background: ${arch.hex};"></span>
            <span class="font-bold text-slate-200">Type ${id}: ${arch.name}</span>
          </div>
          <div class="flex items-center gap-3 font-mono text-[11px]">
            <span class="text-slate-400">${count} units</span>
            <span class="font-bold" style="color: ${arch.hex}">${pct}%</span>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderMaterialPalette() {
    const container = document.getElementById('materialPaletteList');
    if (!container || !state.worldMeta) return;

    const mats = state.worldMeta.materials || state.worldMeta.material_palette || [];
    container.innerHTML = mats.slice(0, 14).map(m => {
      const isWater = m.id === 8;
      const voxCount = m.voxels !== undefined ? m.voxels.toLocaleString() : (m.count !== undefined ? m.count : 'Solid');
      return `
        <div class="mat-item flex items-center justify-between py-1 px-1.5 rounded hover:bg-slate-800/40">
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-sm" style="background: ${m.hex || '#64748b'}"></span>
            <span class="text-slate-300">ID ${m.id}: ${m.name}</span>
          </div>
          <span class="${isWater ? 'text-rose-400 font-bold' : 'text-slate-400'}">
            ${isWater ? '0 (MANDATE)' : voxCount}
          </span>
        </div>
      `;
    }).join('');
  }

  function renderLocationPools() {
    const grid = document.getElementById('locationPoolsGrid');
    if (!grid || !state.envState) return;

    const pools = state.envState.locations || {
      west_farms: { food: 620, renewal_rate: 4.5, capacity: 800 },
      plaza: { food: 95, wood: 140, renewal_rate: 1.2, capacity: 200 },
      grove: { wood: 450, renewal_rate: 2.8, capacity: 500 },
      quarry: { stone: 380, renewal_rate: 2.1, capacity: 450 },
      market_square: { stone: 110, food: 190, renewal_rate: 1.5, capacity: 250 }
    };

    grid.innerHTML = Object.entries(pools).map(([key, p]) => {
      const currentStock = p.stock !== undefined ? p.stock : (p.food || p.wood || p.stone || 120);
      const cap = p.capacity || 500;
      const pct = Math.min(100, Math.round((currentStock / cap) * 100));
      return `
        <div class="bg-slate-950/70 border border-slate-800 p-3.5 rounded-xl flex flex-col justify-between shadow-md">
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-xs font-mono font-bold text-slate-200 uppercase">${key.replace('_', ' ')}</span>
              <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/40">+${p.renewal_rate || 2.0}/tick</span>
            </div>
            <div class="text-base font-bold font-mono text-cyan-300">${Math.round(currentStock)} <span class="text-xs text-slate-400">/ ${cap}</span></div>
          </div>
          
          <div class="mt-3">
            <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div class="h-full bg-cyan-500 rounded-full transition-all duration-300" style="width: ${pct}%"></div>
            </div>
            <div class="flex justify-between text-[10px] font-mono text-slate-400 mt-1">
              <span>Communal Capacity</span>
              <span>${pct}%</span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function renderResourceChart() {
    const canvas = document.getElementById('resourceChartCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width || 600;
    canvas.height = rect.height || 240;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const tick = state.envState ? (state.envState.tick || 142) : 142;
    const pointsCount = 24;
    const history = [];
    for (let i = 0; i < pointsCount; i++) {
      const t = tick - (pointsCount - 1 - i);
      const food = 520 + Math.sin(t * 0.35) * 45 + (i * 1.5);
      const wood = 430 + Math.cos(t * 0.28) * 35;
      const stone = 360 + Math.sin(t * 0.2) * 25;
      const currency = 1280;
      history.push({ t, food, wood, stone, currency });
    }

    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let y = 30; y < canvas.height - 20; y += 40) {
      ctx.beginPath();
      ctx.moveTo(40, y);
      ctx.lineTo(canvas.width - 20, y);
      ctx.stroke();
    }

    const drawLine = (prop, color, minVal, maxVal) => {
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2.5;
      for (let i = 0; i < history.length; i++) {
        const x = 40 + (i / (pointsCount - 1)) * (canvas.width - 60);
        const norm = (history[i][prop] - minVal) / (maxVal - minVal);
        const y = canvas.height - 30 - norm * (canvas.height - 60);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    };

    drawLine('food', '#f59e0b', 300, 650);
    drawLine('wood', '#10b981', 300, 650);
    drawLine('stone', '#06b6d4', 300, 650);

    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px "Fira Code", monospace';
    ctx.fillText('FOOD GRAIN', 50, 20);
    ctx.fillStyle = '#f59e0b';
    ctx.fillRect(40, 12, 6, 6);

    ctx.fillStyle = '#94a3b8';
    ctx.fillText('TIMBER GROVE', 150, 20);
    ctx.fillStyle = '#10b981';
    ctx.fillRect(140, 12, 6, 6);

    ctx.fillStyle = '#94a3b8';
    ctx.fillText('QUARRY STONE', 270, 20);
    ctx.fillStyle = '#06b6d4';
    ctx.fillRect(260, 12, 6, 6);

    ctx.fillStyle = '#94a3b8';
    ctx.fillText('CURRENCY INVARIANT (1,280 C CONSTANT)', 390, 20);
    ctx.fillStyle = '#a855f7';
    ctx.fillRect(380, 12, 6, 6);
  }

  function renderOrderBook() {
    const bidsEl = document.getElementById('bidsTableBody');
    const asksEl = document.getElementById('asksTableBody');
    if (!bidsEl || !asksEl || !state.economyState || !state.economyState.order_book) return;

    const { bids, asks } = state.economyState.order_book;

    bidsEl.innerHTML = (bids || []).slice(0, 5).map(b => {
      const qty = b.quantity || 10;
      const agent = b.agent || 'agent_XX';
      const isMatch = state.selectedAgentId && agent === state.selectedAgentId;
      const barW = Math.min(100, qty * 1.5);
      return `
        <div class="relative py-1 px-2 rounded flex justify-between items-center text-[11px] overflow-hidden ${isMatch ? 'order-agent-match' : ''}">
          <div class="absolute inset-y-0 left-0 bg-emerald-500/15 pointer-events-none" style="width: ${barW}%;"></div>
          <span class="text-emerald-400 font-bold z-10">${Number(b.price).toFixed(2)} C</span>
          <span class="text-slate-200 z-10">${qty}</span>
          <span class="${isMatch ? 'text-cyan-300 font-bold' : 'text-slate-500'} z-10">${agent}</span>
        </div>
      `;
    }).join('');

    asksEl.innerHTML = (asks || []).slice(0, 5).map(a => {
      const qty = a.quantity || 10;
      const agent = a.agent || 'agent_XX';
      const isMatch = state.selectedAgentId && agent === state.selectedAgentId;
      const barW = Math.min(100, qty * 1.5);
      return `
        <div class="relative py-1 px-2 rounded flex justify-between items-center text-[11px] overflow-hidden ${isMatch ? 'order-agent-match' : ''}">
          <div class="absolute inset-y-0 right-0 bg-rose-500/15 pointer-events-none" style="width: ${barW}%;"></div>
          <span class="text-rose-400 font-bold z-10">${Number(a.price).toFixed(2)} C</span>
          <span class="text-slate-200 z-10">${qty}</span>
          <span class="${isMatch ? 'text-cyan-300 font-bold' : 'text-slate-500'} z-10">${agent}</span>
        </div>
      `;
    }).join('');

    const spreadEl = document.getElementById('orderBookSpread');
    const lastPriceEl = document.getElementById('orderBookLastPrice');
    if (spreadEl && state.economyState.order_book.spread !== undefined) {
      spreadEl.textContent = `${Number(state.economyState.order_book.spread).toFixed(2)} C`;
    }
    if (lastPriceEl && state.economyState.order_book.last_clearing_price !== undefined) {
      lastPriceEl.textContent = `${Number(state.economyState.order_book.last_clearing_price).toFixed(2)} C`;
    }
  }

  function renderLorenzCurve() {
    const canvas = document.getElementById('lorenzCanvas');
    if (!canvas || !state.economyState) return;
    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width || 380;
    canvas.height = rect.height || 200;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const pad = 30;
    const w = canvas.width - pad * 2;
    const h = canvas.height - pad * 2;

    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = '#475569';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(pad, pad + h);
    ctx.lineTo(pad + w, pad);
    ctx.stroke();
    ctx.setLineDash([]);

    const lorenzRaw = state.economyState.lorenz_curve || [];
    let coords = [];
    if (Array.isArray(lorenzRaw)) {
      coords = lorenzRaw.map(pt => [pt.pop_pct / 100, pt.wealth_pct / 100]);
    } else {
      coords = [[0, 0], [0.2, 0.08], [0.4, 0.20], [0.6, 0.38], [0.8, 0.62], [1.0, 1.0]];
    }

    ctx.beginPath();
    ctx.strokeStyle = '#f59e0b';
    ctx.lineWidth = 2.5;

    coords.forEach(([p, l], i) => {
      const x = pad + p * w;
      const y = pad + h - l * h;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    ctx.lineTo(pad + w, pad + h);
    ctx.closePath();
    ctx.fillStyle = 'rgba(245, 158, 11, 0.08)';
    ctx.fill();

    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1;
    ctx.strokeRect(pad, pad, w, h);
  }

  function renderLivingManuals() {
    const grid = document.getElementById('manualsGrid');
    if (!grid || !state.economyState) return;

    const manuals = state.economyState.living_manuals || [];
    grid.innerHTML = manuals.map(m => `
      <div class="bg-slate-950/70 border border-slate-800 p-4 rounded-xl flex flex-col justify-between shadow-md">
        <div>
          <div class="flex items-center justify-between pb-2 border-b border-slate-800/80 mb-2">
            <span class="text-xs font-mono font-bold text-purple-400">${m.situation_key}</span>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">GEN ${m.generation || 1}</span>
          </div>
          <h4 class="text-xs font-bold text-white mb-1">${m.rule_ref || 'Manual Entry'}</h4>
          <p class="text-[11px] text-slate-400 leading-relaxed">${m.summary}</p>
        </div>

        <div class="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] font-mono text-slate-500">
          <span>Subscribers: <strong class="text-slate-300">${m.subscribers || 24}</strong></span>
          <span>Confidence: <strong class="text-emerald-400">${m.confidence || 0.95}</strong></span>
        </div>
      </div>
    `).join('');
  }

  function renderVerifiedRulesList() {
    const list = document.getElementById('ruleItemsList');
    if (!list) return;

    list.innerHTML = state.rules.map(r => {
      const isActive = r.rule_id === state.selectedRuleId;
      return `
        <div class="rule-card ${isActive ? 'active' : ''} p-3 rounded-lg border border-slate-800 bg-slate-950/60 cursor-pointer hover:border-cyan-700/50 transition-all" data-rule="${r.rule_id}">
          <div class="flex items-center justify-between mb-1">
            <span class="font-mono text-xs font-bold text-slate-200">${r.rule_id}</span>
            <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${r.status}</span>
          </div>
          <div class="text-[11px] text-slate-400 mb-2">${r.name}</div>
          <div class="flex items-center justify-between text-[10px] font-mono text-slate-500">
            <span>Transitions: <strong class="text-slate-300">${r.tested_transitions || 480}</strong></span>
            <span>False Promo: <strong class="text-emerald-400">&lt; ${r.false_promotion_rate}</strong></span>
          </div>
        </div>
      `;
    }).join('');

    list.querySelectorAll('.rule-card').forEach(card => {
      card.addEventListener('click', () => {
        selectRule(card.dataset.rule);
      });
    });

    updateRuleViewer();
  }

  function selectRule(ruleId) {
    state.selectedRuleId = ruleId;
    renderVerifiedRulesList();
    updateRuleViewer();
  }

  function updateRuleViewer() {
    const rule = state.rules.find(r => r.rule_id === state.selectedRuleId) || state.rules[0];
    if (!rule) return;

    const elTitle = document.getElementById('viewerRuleTitle');
    const elName = document.getElementById('viewerRuleName');
    const elBadge = document.getElementById('viewerStatusBadge');
    const elCode = document.getElementById('viewerCodeBlock');
    const elEvi = document.getElementById('viewerEvidenceId');
    const elFalse = document.getElementById('viewerFalsePromo');
    const elTrans = document.getElementById('viewerTransitions');

    if (elTitle) elTitle.textContent = rule.rule_id;
    if (elName) elName.textContent = rule.name;
    if (elBadge) elBadge.textContent = rule.status;
    if (elCode) elCode.textContent = rule.code;
    if (elEvi) elEvi.textContent = rule.evidence_id;
    if (elFalse) elFalse.textContent = `< ${rule.false_promotion_rate}`;
    if (elTrans) elTrans.textContent = `${rule.tested_transitions || 480} Transitions`;
  }

  // CapabilityPackage Dependency DAG (Wood + Stone -> Handle + Blade -> Stone Axe)
  function renderRuleDag() {
    const container = document.getElementById('ruleDagContainer') || document.getElementById('capabilityDag');
    if (!container) return;

    container.innerHTML = `
      <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
        <h4 class="text-xs font-mono text-purple-400 uppercase tracking-wider mb-3 flex items-center justify-between">
          <span>CapabilityPackage Dependency DAG (Phase 1.5)</span>
          <span class="text-emerald-400 font-bold">SOLVE RATE: 100%</span>
        </h4>
        <svg viewBox="0 0 680 160" class="w-full h-auto">
          <defs>
            <marker id="dagArrow" markerWidth="7" markerHeight="5" refX="6" refY="2.5" orient="auto">
              <polygon points="0 0, 7 2.5, 0 5" fill="#8b5cf6" />
            </marker>
          </defs>
          <g transform="translate(40, 30)">
            <rect width="110" height="40" rx="6" fill="#0f172a" stroke="#06b6d4" stroke-width="1.5" />
            <text x="55" y="24" text-anchor="middle" fill="#38bdf8" font-family="'Fira Code', monospace" font-size="11" font-weight="bold">Wood (Grove)</text>
          </g>
          <g transform="translate(40, 90)">
            <rect width="110" height="40" rx="6" fill="#0f172a" stroke="#06b6d4" stroke-width="1.5" />
            <text x="55" y="24" text-anchor="middle" fill="#38bdf8" font-family="'Fira Code', monospace" font-size="11" font-weight="bold">Stone (Quarry)</text>
          </g>
          <line x1="150" y1="50" x2="250" y2="50" stroke="#8b5cf6" stroke-width="1.8" marker-end="url(#dagArrow)" />
          <line x1="150" y1="110" x2="250" y2="110" stroke="#8b5cf6" stroke-width="1.8" marker-end="url(#dagArrow)" />
          <g transform="translate(250, 30)">
            <rect width="130" height="40" rx="6" fill="#0f172a" stroke="#a855f7" stroke-width="1.5" />
            <text x="65" y="24" text-anchor="middle" fill="#c084fc" font-family="'Fira Code', monospace" font-size="11" font-weight="bold">Tool Handle</text>
          </g>
          <g transform="translate(250, 90)">
            <rect width="130" height="40" rx="6" fill="#0f172a" stroke="#a855f7" stroke-width="1.5" />
            <text x="65" y="24" text-anchor="middle" fill="#c084fc" font-family="'Fira Code', monospace" font-size="11" font-weight="bold">Stone Blade</text>
          </g>
          <line x1="380" y1="50" x2="490" y2="75" stroke="#8b5cf6" stroke-width="1.8" marker-end="url(#dagArrow)" />
          <line x1="380" y1="110" x2="490" y2="85" stroke="#8b5cf6" stroke-width="1.8" marker-end="url(#dagArrow)" />
          <g transform="translate(490, 55)">
            <rect width="150" height="50" rx="8" fill="#1e1b4b" stroke="#10b981" stroke-width="2" />
            <text x="75" y="24" text-anchor="middle" fill="#34d399" font-family="'Fira Code', monospace" font-size="12" font-weight="bold">Stone Axe</text>
            <text x="75" y="40" text-anchor="middle" fill="#94a3b8" font-family="'Inter', sans-serif" font-size="9">Verified EAE: 0.842</text>
          </g>
        </svg>
      </div>
    `;
  }

  // CVTArchive 5D Niche Matrix Viewer
  function renderCvtArchive() {
    const container = document.getElementById('cvtCentroidsGrid');
    if (!container) return;

    container.innerHTML = state.cvtCentroids.map((c, i) => `
      <div class="niche-card ${i === 0 ? 'active' : ''} p-3 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between hover:border-cyan-400 cursor-pointer transition-all shadow-md">
        <div>
          <div class="flex items-center justify-between pb-1.5 border-b border-slate-800/80 mb-2">
            <span class="font-bold text-cyan-400">${c.id}</span>
            <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${c.fitness} FIT</span>
          </div>
          <div class="text-[11px] text-white font-bold mb-1">${c.name}</div>
          <div class="text-[10px] text-slate-400 space-y-0.5">
            <div>Elite: <strong class="text-cyan-300">${c.elite}</strong></div>
            <div>Occupants: <strong class="text-slate-300">${c.count} citizens</strong></div>
          </div>
        </div>

        <div class="mt-2.5 pt-2 border-t border-slate-800/60 text-[9px] text-slate-500">
          <span>5D: [${c.coords.map(v => v.toFixed(2)).join(', ')}]</span>
        </div>
      </div>
    `).join('');

    container.querySelectorAll('.niche-card').forEach(card => {
      card.addEventListener('click', () => {
        container.querySelectorAll('.niche-card').forEach(c => c.classList.remove('active', 'border-cyan-400', 'border-cyan-700/60'));
        card.classList.add('active', 'border-cyan-400');
      });
    });
  }

  // System Pipeline Topology & Staged LLM Route (Hazard Amber)
  function renderPipelineGraph() {
    const svg = document.getElementById('pipelineSvg');
    if (!svg || !state.pipeline || !state.pipeline.nodes) return;

    const nodes = state.pipeline.nodes;
    const links = state.pipeline.edges || [];

    const coords = {
      'substrate': { x: 120, y: 80 },
      'moore_machine': { x: 380, y: 80 },
      'economy_market': { x: 380, y: 240 },
      'rule_library': { x: 680, y: 80 },
      'evaluator': { x: 680, y: 240 },
      'llm_cognitive_route': { x: 920, y: 160 }
    };

    let svgHtml = `
      <defs>
        <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#475569" />
        </marker>
        <marker id="arrowhead-amber" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#f59e0b" />
        </marker>
      </defs>
    `;

    links.forEach(l => {
      const from = coords[l.from];
      const to = coords[l.to];
      if (!from || !to) return;

      const isToLLM = l.to === 'llm_cognitive_route' || l.from === 'llm_cognitive_route';
      const strokeColor = isToLLM ? '#f59e0b' : '#334155';
      const marker = isToLLM ? 'url(#arrowhead-amber)' : 'url(#arrowhead)';

      svgHtml += `
        <line x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" 
              stroke="${strokeColor}" stroke-width="${isToLLM ? 2.5 : 1.5}" 
              stroke-dasharray="${isToLLM ? '6,4' : 'none'}"
              marker-end="${marker}" />
      `;
    });

    nodes.forEach(n => {
      const pt = coords[n.id];
      if (!pt) return;

      const isLLM = n.is_incomplete || n.id === 'llm_cognitive_route';

      if (isLLM) {
        // PROMINENT HAZARD AMBER STAGED NODE
        svgHtml += `
          <g class="pipe-node" transform="translate(${pt.x - 80}, ${pt.y - 48})">
            <!-- Pulsing Hazard Outer Glow -->
            <rect x="-4" y="-4" width="168" height="102" rx="14" 
                  fill="rgba(245, 158, 11, 0.15)" stroke="#f59e0b" stroke-width="2.5" stroke-dasharray="6,4">
              <animate attributeName="opacity" values="0.4;1;0.4" dur="2s" repeatCount="indefinite" />
            </rect>
            <!-- Core Box -->
            <rect x="0" y="0" width="160" height="94" rx="10" 
                  fill="#1c1103" stroke="#f59e0b" stroke-width="2.5" />
            
            <text x="80" y="24" text-anchor="middle" font-family="'Fira Code', monospace" 
                  font-size="10" font-weight="bold" fill="#fef08a">⚠️ STAGED RESEARCH ROUTE</text>
            <text x="80" y="44" text-anchor="middle" font-family="'Inter', sans-serif" 
                  font-size="11" font-weight="bold" fill="#ffffff">Neural LLM / Agent Synthesis</text>
            
            <rect x="12" y="58" width="136" height="22" rx="4" fill="rgba(245, 158, 11, 0.25)" stroke="#f59e0b" />
            <text x="80" y="73" text-anchor="middle" font-family="'Fira Code', monospace" 
                  font-size="9" font-weight="bold" fill="#f59e0b">ZERO RUNTIME INFERENCE</text>
          </g>
        `;
      } else {
        const color = n.color || '#38bdf8';
        const label = n.name || 'Node';
        const type = n.phase || 'Subsystem';
        const status = n.status_label || 'Active';

        svgHtml += `
          <g class="pipe-node" transform="translate(${pt.x - 70}, ${pt.y - 40})">
            <rect x="0" y="0" width="140" height="80" rx="10" 
                  fill="#0b1120" stroke="${color}" stroke-width="1.5" />
            <text x="70" y="24" text-anchor="middle" font-family="'Fira Code', monospace" 
                  font-size="10" font-weight="bold" fill="${color}">${type}</text>
            <text x="70" y="44" text-anchor="middle" font-family="'Inter', sans-serif" 
                  font-size="11" font-weight="bold" fill="#ffffff">${label}</text>
            
            <rect x="25" y="54" width="90" height="18" rx="4" fill="rgba(255, 255, 255, 0.05)" />
            <text x="70" y="67" text-anchor="middle" font-family="'Fira Code', monospace" 
                  font-size="9" fill="#94a3b8">${status}</text>
          </g>
        `;
      }
    });

    svg.innerHTML = svgHtml;
  }

  function renderAuditChecklist() {
    const grid = document.getElementById('auditChecklistGrid');
    if (!grid || !state.auditData) return;

    const list = state.auditData.checks || state.auditData.gates || [];
    grid.innerHTML = list.map((g, i) => `
      <div class="p-3 rounded-lg bg-slate-950/70 border border-emerald-900/40 flex items-start gap-3 shadow-md">
        <span class="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
          ✓
        </span>
        <div class="space-y-1">
          <div class="flex items-center gap-2">
            <span class="text-white font-bold">Gate #${i + 1}: ${g.name}</span>
          </div>
          <div class="text-[11px] text-slate-400 font-sans">${g.detail}</div>
          <div class="text-[10px] text-emerald-400 font-mono">STATUS: ${g.status}</div>
        </div>
      </div>
    `).join('');
  }

})();
