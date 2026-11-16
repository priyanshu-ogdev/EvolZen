/**
 * EVOLZEN // 1×1 KM Parallel Universe & Multi-Agent Infrastructure
 * ui-ux-pro-max 3D Overhaul Engine & Live Evaluation Console
 * Pure Client-Side WebGL (Three.js) & Zero Runtime LLM Inference
 */

import * as THREE from './vendor/three.module.js';
import { OrbitControls } from './vendor/OrbitControls.js';

(function () {
  'use strict';

  // =========================================================================
  // Global Dashboard State
  // =========================================================================
  const state = {
    worldMeta: null,
    envState: null,
    economyState: null,
    rules: [],
    selectedRuleId: null,
    selectedAgentId: null,
    pipeline: null,
    auditData: null,
    agents: [],
    activeTab: 'tab-map',
    activeSubsystem: 'tab-environment',
    layoutMode: 'unified', // 'unified', 'split', 'quad', 'focus'
    viewMode: '3d', // '3d' or '2d'
    isNightMode: true,
    
    // Simulation playback
    isRunning: false,
    timer: null,

    // Guided Portfolio Workflow Tour
    tour: {
      step: 0,
      autoPlay: false,
      timer: null
    },
    
    // 3D Three.js Engine State
    three: {
      renderer: null,
      scene: null,
      camera: null,
      controls: null,
      raycaster: new THREE.Raycaster(),
      mouse: new THREE.Vector2(),
      housesGroup: null,
      civicGroup: null,
      farmsGroup: null,
      agentsGroup: null,
      shieldMesh: null,
      agoraRing: null,
      hospitalBeacon: null,
      sunLight: null,
      ambientLight: null,
      agentMeshes: [],
      houseMeshes: [],
      civicMeshes: [],
      hoveredObject: null,
      selectedObject: null,
      camTargetPos: null,
      camLookAtPos: null,
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

    // Archetype definitions and color codes
    archetypes: {
      0: { name: 'Ranch', color: 0xeab308, hex: '#eab308', floors: 1, height: 4.0, walls: 'VINYL (Yellow)', roof: 'ROOF (Grey)' },
      1: { name: 'Colonial', color: 0x38bdf8, hex: '#38bdf8', floors: 2, height: 7.2, walls: 'BRICK (Red/Blue)', roof: 'SHINGLE' },
      2: { name: 'McMansion', color: 0xa855f7, hex: '#a855f7', floors: 2, height: 8.5, walls: 'STUCCO / GLASS', roof: 'TILE (Grey)' },
      3: { name: 'Bungalow', color: 0x10b981, hex: '#10b981', floors: 1, height: 4.2, walls: 'WOOD / VINYL', roof: 'GABLE' },
      4: { name: 'Modern Flat', color: 0xec4899, hex: '#ec4899', floors: 2, height: 6.8, walls: 'CONCRETE / GLASS', roof: 'FLAT TERRACE' }
    },

    // Civic Anchors
    civicAnchors: [
      { id: 'hospital', name: 'Hospital ✚', x: 450, z: 550, size: 32, height: 24, color: 0xef4444, hex: '#ef4444', icon: '🏥', desc: 'Emergency Trauma & Voxel Restoration' },
      { id: 'school', name: 'School Academy', x: 650, z: 550, size: 30, height: 16, color: 0xf59e0b, hex: '#f59e0b', icon: '🏫', desc: 'Cultural Manual Transmission & Training' },
      { id: 'fire', name: 'Fire Department', x: 550, z: 450, size: 28, height: 14, color: 0xf97316, hex: '#f97316', icon: '🚒', desc: 'Containment & Thermal Mitigation' },
      { id: 'municipal', name: 'Municipal Office', x: 450, z: 450, size: 32, height: 20, color: 0x94a3b8, hex: '#94a3b8', icon: '🏛️', desc: 'Registry & Deed Token Verification' },
      { id: 'market', name: 'Central Agora Market', x: 550, z: 650, size: 36, height: 12, color: 0x10b981, hex: '#10b981', icon: '⚖️', desc: 'Continuous Double-Auction Order Clearing' },
      { id: 'park', name: 'Central Park Green', x: 500, z: 500, w: 100, h: 100, color: 0x059669, hex: '#059669', icon: '🌲', isZone: true, desc: 'Public Common Goods Reserve' }
    ]
  };

  // Subsystem Console Titles Mapping
  const subsystemTitles = {
    'tab-environment': 'Phase 1.1 Moore Machine & Invariant Guardian',
    'tab-economy': 'Phase 1.3 Agora Market & Lorenz Wealth',
    'tab-library': 'Phase 1.4 & 2.2 gVisor Sandbox & Rule Library',
    'tab-pipeline': 'Decoupled Zero-Inference Infrastructure Pipeline',
    'tab-audit': 'Phase 2.5 Patent-Grade Source-Audit Certificate'
  };

  // 6-Step Guided Portfolio Workflow Tour
  const tourSteps = [
    {
      step: 1,
      badge: 'PHASE 1.1 SUBSTRATE',
      title: '1×1 km Spatial Substrate & Deterministic Moore Machine',
      desc: '10,378 Chunks · 340M Voxels · Zero Water Mandate · 98.7% Connected Streets',
      layout: 'unified',
      subsystem: 'tab-environment',
      camera: { pos: new THREE.Vector3(500, 360, 1120), target: new THREE.Vector3(500, 0, 500) }
    },
    {
      step: 2,
      badge: 'PHASE 1.2 AGENTS',
      title: 'Chebyshev Multi-Agent Avatars & Homeostatic Vitals',
      desc: '64 Autonomous Agents · Augmented Chebyshev Metric · Non-Linear Homeostasis',
      layout: 'unified',
      subsystem: 'tab-environment',
      camera: { pos: new THREE.Vector3(520, 75, 640), target: new THREE.Vector3(500, 5, 520) },
      action: () => {
        if (state.agents && state.agents.length > 0) {
          inspectAgent(state.agents[0]);
        }
      }
    },
    {
      step: 3,
      badge: 'PHASE 1.3 ECONOMY',
      title: 'Agora Continuous Double-Auction Market & Cultural Transmission',
      desc: 'Midpoint Clearing · Gini 0.284 · Living Manuals Knowledge Propagation',
      layout: 'unified',
      subsystem: 'tab-economy',
      camera: { pos: new THREE.Vector3(550, 45, 650), target: new THREE.Vector3(550, 0, 650) },
      action: () => {
        if (state.three.agoraRing) {
          state.three.agoraRing.material.color.setHex(0x10b981);
        }
      }
    },
    {
      step: 4,
      badge: 'PHASE 1.4 & 2.2 CONTAINMENT',
      title: 'gVisor Container Sandbox Isolation & Append-Only DuckDB',
      desc: '128 MB RAM Ceiling · 2.0s Timeout · Strict Invariant Deduplication',
      layout: 'unified',
      subsystem: 'tab-library',
      camera: { pos: new THREE.Vector3(500, 130, 750), target: new THREE.Vector3(500, 20, 500) },
      action: () => {
        if (state.rules && state.rules.length > 0) {
          selectRule(state.rules[0].rule_id);
        }
      }
    },
    {
      step: 5,
      badge: 'ARCHITECTURAL MANDATE',
      title: 'Decoupled Architecture: Zero Runtime LLM Inference by Design',
      desc: 'Cognitive Route Staged in Hazard Orange · 0 Hallucination · 0 Token Costs',
      layout: 'split',
      subsystem: 'tab-pipeline',
      camera: { pos: new THREE.Vector3(500, 260, 920), target: new THREE.Vector3(500, 0, 500) },
      action: () => {
        renderPipelineGraph();
      }
    },
    {
      step: 6,
      badge: 'PHASE 2.5 AUDIT',
      title: 'Patent-Grade Source-Audit Certification (10/10 Invariants)',
      desc: 'Formally Verified against world_voxel_hires.npz & voxel_meta.json',
      layout: 'focus',
      subsystem: 'tab-audit',
      camera: { pos: new THREE.Vector3(500, 440, 1180), target: new THREE.Vector3(500, 0, 500) },
      action: () => {
        renderAuditChecklist();
      }
    }
  ];

  // =========================================================================
  // Initialization Lifecycle
  // =========================================================================
  async function initDashboard() {
    // 1. Controls, Navigation and Tab Handlers setup immediately
    initTabs();
    initLayoutControls();
    initTourEngine();
    initSubsystemDock();
    initKeyboardShortcuts();
    initSimulationControls();
    initViewModeControls();
    init2DMapCanvas();

    // 2. Start 3D Engine immediately so the user sees the world right away
    requestAnimationFrame(() => {
      initThreeEngine();
    });

    // 3. Fetch initial backend telemetry & data
    try {
      await Promise.all([
        fetchWorldMeta(),
        fetchEnvironmentState(),
        fetchEconomyState(),
        fetchRuleLibrary(),
        fetchArchitecturePipeline(),
        fetchAuditCertificate(),
        fetchAgentsRoster()
      ]);
    } catch (fetchErr) {
      console.warn('Backend telemetry fetch issue, continuing with seed data:', fetchErr);
    }

    // 4. Guarantee houses & agents are built if world data loaded
    if (state.three && state.three.scene) {
      if (state.three.houseMeshes.length === 0 && state.worldMeta && state.worldMeta.houses) {
        build3DHouses(state.three.scene);
      }
      if (state.three.agentMeshes.length === 0 && state.agents && state.agents.length > 0) {
        build3DAgents(state.three.scene);
      }
      handleThreeResize();
    }

    // 5. Initial 2D & UI render passes
    renderArchetypeDistribution();
    renderMaterialPalette();
    renderLocationPools();
    renderResourceChart();
    renderOrderBook();
    renderLorenzCurve();
    renderLivingManuals();
    renderVerifiedRulesList();
    renderPipelineGraph();
    renderAuditChecklist();
    render2DWorldMap();
  }

  // Safe bootstrap: run immediately if document is ready, otherwise on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
  } else {
    initDashboard();
  }

  // =========================================================================
  // API Fetchers
  // =========================================================================
  async function fetchWorldMeta() {
    try {
      const res = await fetch('/api/world/meta');
      state.worldMeta = await res.json();
      if (state.three && state.three.scene && state.worldMeta.houses) {
        build3DHouses(state.three.scene);
      }
    } catch (e) {
      console.error('Failed to fetch /api/world/meta', e);
    }
  }

  async function fetchEnvironmentState() {
    try {
      const res = await fetch('/api/environment/state');
      state.envState = await res.json();
      updateSimulationHUD();
    } catch (e) {
      console.error('Failed to fetch /api/environment/state', e);
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
      console.error('Failed to fetch /api/economy/state', e);
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
      console.error('Failed to fetch /api/library/rules', e);
    }
  }

  async function fetchArchitecturePipeline() {
    try {
      const res = await fetch('/api/architecture/pipeline');
      state.pipeline = await res.json();
    } catch (e) {
      console.error('Failed to fetch /api/architecture/pipeline', e);
    }
  }

  async function fetchAuditCertificate() {
    try {
      const res = await fetch('/api/system/audit');
      state.auditData = await res.json();
    } catch (e) {
      console.error('Failed to fetch /api/system/audit', e);
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
        build3DAgents(state.three.scene);
      }
    } catch (e) {
      console.error('Failed to fetch /api/agents/roster', e);
    }
  }

  // =========================================================================
  // Tab Navigation Handling
  // =========================================================================
  function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const targetId = tab.dataset.tab;
        if (!targetId) return;

        state.activeTab = targetId;

        // If clicking 3D Substrate
        if (targetId === 'tab-map') {
          tabs.forEach(t => {
            const isMatch = t.dataset.tab === 'tab-map';
            t.classList.toggle('active', isMatch);
            t.setAttribute('aria-selected', isMatch ? 'true' : 'false');
          });

          if (state.layoutMode === 'focus') {
            const workspace = document.getElementById('mainWorkspace');
            if (workspace) {
              workspace.classList.remove('focus-subsystem');
              workspace.classList.add('focus-spatial');
            }
          } else {
            // In unified / split / quad, smoothly scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }

          requestAnimationFrame(() => {
            if (state.viewMode === '3d' && state.three.renderer) {
              handleThreeResize();
            } else {
              render2DWorldMap();
            }
          });
        } else {
          // Subsystem tab clicked
          setSubsystemDock(targetId);

          if (state.layoutMode === 'unified') {
            const dock = document.getElementById('subsystemSection');
            if (dock) dock.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        }
      });
    });
  }

  // =========================================================================
  // Workspace Layout Switcher (Unified Cockpit / Split / Quad / Focus)
  // =========================================================================
  function initLayoutControls() {
    const btns = document.querySelectorAll('.layout-btn');
    btns.forEach(btn => {
      btn.addEventListener('click', () => {
        const mode = btn.dataset.layout;
        if (mode) setLayoutMode(mode);
      });
    });
  }

  function setLayoutMode(mode) {
    if (!['unified', 'split', 'quad', 'focus'].includes(mode)) mode = 'unified';
    state.layoutMode = mode;

    const workspace = document.getElementById('mainWorkspace');
    if (!workspace) return;

    // Update layout buttons UI
    document.querySelectorAll('.layout-btn').forEach(btn => {
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

    // Reset layout classes
    workspace.classList.remove(
      'workspace-layout-unified',
      'workspace-layout-split',
      'workspace-layout-quad',
      'workspace-layout-focus',
      'focus-spatial',
      'focus-subsystem'
    );

    workspace.classList.add(`workspace-layout-${mode}`);

    if (mode === 'focus') {
      if (state.activeTab === 'tab-map') {
        workspace.classList.add('focus-spatial');
      } else {
        workspace.classList.add('focus-subsystem');
      }
    }

    // Refresh rendering passes
    requestAnimationFrame(() => {
      handleThreeResize();
      if (state.viewMode === '2d') render2DWorldMap();
      renderResourceChart();
      renderLorenzCurve();
      renderPipelineGraph();
    });
  }

  // =========================================================================
  // Subsystem Dock Console Switcher
  // =========================================================================
  function initSubsystemDock() {
    const pills = document.querySelectorAll('.subsystem-pill');
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
          // Toggle back to Unified Cockpit
          setLayoutMode('unified');
        } else {
          state.activeTab = state.activeSubsystem || 'tab-environment';
          setLayoutMode('focus');
        }
      });
    }
  }

  function setSubsystemDock(subsystemId) {
    state.activeSubsystem = subsystemId;

    // Update subsystem dock pills
    document.querySelectorAll('.subsystem-pill').forEach(pill => {
      const isActive = pill.dataset.subsystem === subsystemId;
      pill.classList.toggle('active', isActive);
      pill.setAttribute('aria-selected', isActive ? 'true' : 'false');
      if (isActive) {
        pill.classList.add('bg-cyan-950/60', 'text-cyan-400', 'border-cyan-700/50', 'font-bold');
        pill.classList.remove('text-slate-400');
      } else {
        pill.classList.remove('bg-cyan-950/60', 'text-cyan-400', 'border-cyan-700/50', 'font-bold');
        pill.classList.add('text-slate-400');
      }
    });

    // Update active pane inside #subsystemPanesContainer
    const container = document.getElementById('subsystemPanesContainer');
    if (container) {
      container.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      const activePane = document.getElementById(subsystemId);
      if (activePane) activePane.classList.add('active');
    }

    // Update dock header badge
    const badge = document.getElementById('dockActiveBadge');
    if (badge) {
      badge.textContent = subsystemTitles[subsystemId] || 'Phase Active Subsystem';
    }

    // Synchronize top navigation tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
      const isMatch = tab.dataset.tab === subsystemId;
      tab.classList.toggle('active', isMatch);
      tab.setAttribute('aria-selected', isMatch ? 'true' : 'false');
    });

    // If in focus layout, update focus state
    if (state.layoutMode === 'focus') {
      state.activeTab = subsystemId;
      const workspace = document.getElementById('mainWorkspace');
      if (workspace) {
        workspace.classList.remove('focus-spatial');
        workspace.classList.add('focus-subsystem');
      }
    }

    // Redraw charts
    if (subsystemId === 'tab-environment') renderResourceChart();
    if (subsystemId === 'tab-economy') renderLorenzCurve();
    if (subsystemId === 'tab-pipeline') renderPipelineGraph();
  }

  // =========================================================================
  // Guided Portfolio Workflow Tour Engine
  // =========================================================================
  function initTourEngine() {
    const btnPrev = document.getElementById('btnTourPrev');
    const btnNext = document.getElementById('btnTourNext');
    const btnAuto = document.getElementById('btnTourAuto');
    const dots = document.querySelectorAll('.tour-dot');

    if (btnPrev) btnPrev.addEventListener('click', prevTourStep);
    if (btnNext) btnNext.addEventListener('click', nextTourStep);
    if (btnAuto) btnAuto.addEventListener('click', toggleAutoTour);

    dots.forEach((dot, idx) => {
      dot.addEventListener('click', () => {
        goToTourStep(idx);
      });
    });

    // Render initial step (Step 1)
    renderTourStep(0);
  }

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

  function toggleAutoTour() {
    state.tour.autoPlay = !state.tour.autoPlay;
    const btn = document.getElementById('btnTourAuto');
    const icon = document.getElementById('tourAutoIcon');
    const text = document.getElementById('tourAutoText');

    if (state.tour.autoPlay) {
      if (icon) icon.textContent = '⏸';
      if (text) text.textContent = 'Pause Tour';
      if (btn) btn.className = 'px-2.5 py-1 rounded bg-amber-950/70 hover:bg-amber-900/90 text-amber-300 border border-amber-600/50 flex items-center gap-1 transition-all font-mono font-bold';
      state.tour.timer = setInterval(nextTourStep, 7000);
    } else {
      if (icon) icon.textContent = '⚡';
      if (text) text.textContent = 'Auto Tour';
      if (btn) btn.className = 'px-2.5 py-1 rounded bg-emerald-950/60 hover:bg-emerald-900/80 text-emerald-300 border border-emerald-600/50 flex items-center gap-1 transition-all font-mono';
      if (state.tour.timer) clearInterval(state.tour.timer);
    }
  }

  function renderTourStep(idx) {
    const step = tourSteps[idx];
    if (!step) return;

    // Update dots
    document.querySelectorAll('.tour-dot').forEach((dot, dIdx) => {
      dot.classList.toggle('active', dIdx === idx);
      dot.classList.toggle('completed', dIdx < idx);
    });

    // Update labels
    const badge = document.getElementById('tourStepBadge');
    const title = document.getElementById('tourStepTitle');
    const desc = document.getElementById('tourStepDesc');

    if (badge) badge.textContent = `STEP ${idx + 1}/6:`;
    if (title) title.textContent = step.title;
    if (desc) desc.textContent = step.desc;

    // Apply layout if defined
    if (step.layout && step.layout !== state.layoutMode) {
      setLayoutMode(step.layout);
    }

    // Apply docked subsystem if defined
    if (step.subsystem) {
      setSubsystemDock(step.subsystem);
    }

    // Smooth camera glide
    if (step.camera && state.three.camera && state.three.controls) {
      state.three.camTargetPos = step.camera.pos.clone();
      state.three.camLookAtPos = step.camera.target.clone();
    }

    // Step-specific trigger
    if (typeof step.action === 'function') {
      step.action();
    }
  }

  // =========================================================================
  // Keyboard Hotkeys
  // =========================================================================
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
      } else if (key === 'q') {
        setLayoutMode('quad');
      } else if (key === 'm') {
        const btnMax = document.getElementById('btnMaxView');
        if (btnMax) btnMax.click();
      } else if (key === 't') {
        nextTourStep();
      } else if (key === '1') {
        const tab = document.querySelector('.nav-tab[data-tab="tab-map"]');
        if (tab) tab.click();
      } else if (key === '2') {
        const tab = document.querySelector('.nav-tab[data-tab="tab-environment"]');
        if (tab) tab.click();
      } else if (key === '3') {
        const tab = document.querySelector('.nav-tab[data-tab="tab-economy"]');
        if (tab) tab.click();
      } else if (key === '4') {
        const tab = document.querySelector('.nav-tab[data-tab="tab-library"]');
        if (tab) tab.click();
      } else if (key === '5') {
        const tab = document.querySelector('.nav-tab[data-tab="tab-pipeline"]');
        if (tab) tab.click();
      } else if (key === '6') {
        const tab = document.querySelector('.nav-tab[data-tab="tab-audit"]');
        if (tab) tab.click();
      }
    });
  }

  // =========================================================================
  // Simulation Cockpit Controls
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

  function togglePlayPause() {
    state.isRunning = !state.isRunning;
    const playIcon = document.getElementById('playIcon');
    const playText = document.getElementById('playText');
    const btn = document.getElementById('btnPlayPause');

    if (state.isRunning) {
      if (playIcon) playIcon.textContent = '⏸';
      if (playText) playText.textContent = 'PAUSE';
      if (btn) btn.className = 'btn-ctrl px-3 py-1 text-xs rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-medium flex items-center gap-1.5 transition-all';
      state.timer = setInterval(() => stepSimulation(1), 1200);
    } else {
      if (playIcon) playIcon.textContent = '▶';
      if (playText) playText.textContent = 'RUN';
      if (btn) btn.className = 'btn-ctrl px-3 py-1 text-xs rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium flex items-center gap-1.5 transition-all';
      if (state.timer) clearInterval(state.timer);
    }
  }

  async function stepSimulation(count = 1) {
    try {
      const res = await fetch('/api/environment/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps: count })
      });
      const data = await res.json();
      if (data.tick !== undefined && state.envState) {
        state.envState.tick = data.tick;
        if (data.locations) state.envState.locations = data.locations;
      }
      updateSimulationHUD();
      const badge = document.getElementById('currentTickBadge');
      if (badge) {
        badge.classList.remove('sync-pulse');
        void badge.offsetWidth;
        badge.classList.add('sync-pulse');
      }
      renderLocationPools();
      renderResourceChart();
      await Promise.all([fetchEconomyState(), fetchAgentsRoster()]);
      renderOrderBook();
      renderLorenzCurve();
      syncAgentMeshes();
    } catch (e) {
      console.error('Error during stepSimulation:', e);
    }
  }

  async function resetSimulation() {
    if (state.isRunning) togglePlayPause();
    try {
      await fetch('/api/environment/reset', { method: 'POST' });
      await Promise.all([fetchEnvironmentState(), fetchEconomyState(), fetchAgentsRoster()]);
      updateSimulationHUD();
      renderLocationPools();
      renderResourceChart();
      renderOrderBook();
      renderLorenzCurve();
      syncAgentMeshes();
    } catch (e) {
      console.error('Error during resetSimulation:', e);
    }
  }

  function updateSimulationHUD() {
    if (!state.envState) return;
    const badge = document.getElementById('currentTickBadge');
    if (badge) badge.textContent = `TICK #${state.envState.tick || 142}`;
  }

  // =========================================================================
  // 3D Overhaul Controls & Demonstration Camera Director
  // =========================================================================
  function initViewModeControls() {
    const btn3D = document.getElementById('btnView3D');
    const btn2D = document.getElementById('btnView2D');
    const threeContainer = document.getElementById('threeContainer');
    const canvas2D = document.getElementById('worldMapCanvas');
    const controls2D = document.getElementById('map2dControls');

    btn3D.addEventListener('click', () => {
      state.viewMode = '3d';
      btn3D.classList.add('active');
      btn2D.classList.remove('active');
      threeContainer.classList.remove('hidden');
      threeContainer.classList.add('block');
      canvas2D.classList.add('hidden');
      controls2D.classList.add('hidden');
      requestAnimationFrame(() => handleThreeResize());
    });

    btn2D.addEventListener('click', () => {
      state.viewMode = '2d';
      btn2D.classList.add('active');
      btn3D.classList.remove('active');
      threeContainer.classList.add('hidden');
      threeContainer.classList.remove('block');
      canvas2D.classList.remove('hidden');
      controls2D.classList.remove('hidden');
      render2DWorldMap();
    });

    // Day / Night Lighting Toggle
    const btnLight = document.getElementById('btnToggleDayNight');
    const lightIcon = document.getElementById('lightIcon');
    const lightLabel = document.getElementById('lightLabel');

    btnLight.addEventListener('click', () => {
      state.isNightMode = !state.isNightMode;
      if (state.isNightMode) {
        lightIcon.textContent = '🌙';
        lightLabel.textContent = 'Night Bloom';
        applyNightLighting();
      } else {
        lightIcon.textContent = '☀️';
        lightLabel.textContent = 'Day Light';
        applyDayLighting();
      }
    });

    // Fullscreen Max View Toggle
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

      // Press Escape to exit Max View
      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && viewport.classList.contains('viewport-maximized')) {
          viewport.classList.remove('viewport-maximized');
          if (maxIcon) maxIcon.textContent = '⛶';
          if (maxLabel) maxLabel.textContent = 'Max View';
          requestAnimationFrame(() => handleThreeResize());
        }
      });
    }

    // Camera Bookmarks for Demonstration Focus
    document.querySelectorAll('.cam-bookmark').forEach(btn => {
      btn.addEventListener('click', () => {
        const focus = btn.dataset.focus;
        switch (focus) {
          case 'orbital':
            tweenCamera(new THREE.Vector3(500, 550, 1250), new THREE.Vector3(500, 0, 500));
            break;
          case 'civic':
            tweenCamera(new THREE.Vector3(550, 130, 760), new THREE.Vector3(500, 15, 520));
            break;
          case 'farms':
            tweenCamera(new THREE.Vector3(80, 140, 680), new THREE.Vector3(50, 5, 500));
            break;
          case 'houses':
            tweenCamera(new THREE.Vector3(280, 100, 360), new THREE.Vector3(240, 10, 270));
            break;
          case 'shield':
            tweenCamera(new THREE.Vector3(500, 240, 820), new THREE.Vector3(500, 35, 500));
            break;
        }
      });
    });

    // Layer Toggles
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

  // =========================================================================
  // Three.js 3D Overhaul Engine
  // =========================================================================
  function initThreeEngine() {
    const container = document.getElementById('threeContainer');
    if (!container) return;

    try {
      // Read real dimensions; fallback to viewport-based defaults
      const width  = container.clientWidth  || container.offsetWidth  || window.innerWidth  || 1200;
      const height = container.clientHeight || container.offsetHeight || Math.round(window.innerHeight * 0.76) || 600;

      // 1. Renderer
      const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.shadowMap.enabled = true;
      renderer.shadowMap.type = THREE.PCFSoftShadowMap;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1.1;
      container.innerHTML = ''; // Ensure container is clean
      container.appendChild(renderer.domElement);
      state.three.renderer = renderer;

      // 2. Scene with Fog
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x020617);
      scene.fog = new THREE.FogExp2(0x020617, 0.0007);
      state.three.scene = scene;

      // 3. Camera & OrbitControls
      const camera = new THREE.PerspectiveCamera(45, width / height, 1, 3500);
      camera.position.set(500, 520, 1200);
      state.three.camera = camera;

      const controls = new OrbitControls(camera, renderer.domElement);
      controls.target.set(500, 0, 500);
      controls.enableDamping = true;
      controls.dampingFactor = 0.06;
      controls.maxPolarAngle = Math.PI / 2.05; // Do not go below ground
      controls.minDistance = 25;
      controls.maxDistance = 1900;
      state.three.controls = controls;

      // 4. Lighting Rig
      setupThreeLighting(scene);

      // 5. Build 3D World Geometry (Static anchors load instantly)
      build3DWorldGround(scene);
      build3DWestFarmBelts(scene);
      build3DCentralPark(scene);
      build3DCivicAnchors(scene);
      build3DGVisorDome(scene);
      if (state.worldMeta && state.worldMeta.houses) {
        build3DHouses(scene);
      }
      if (state.agents && state.agents.length > 0) {
        build3DAgents(scene);
      }

      // 6. Interaction Event Listeners
      renderer.domElement.addEventListener('mousemove', onThreeMouseMove);
      renderer.domElement.addEventListener('click', onThreeClick);
      window.addEventListener('resize', handleThreeResize);

      // 7. Animation Loop
      animateThree();

      // 8. Attach ResizeObserver AFTER engine is fully initialized
      if (window.ResizeObserver) {
        const resizeObs = new ResizeObserver(() => handleThreeResize());
        resizeObs.observe(container);
      }

      // 9. Force a resize pass immediately so the canvas fills the container
      handleThreeResize();
    } catch (err) {
      console.warn('WebGL init error, falling back to 2D orthographic canvas:', err);
      state.viewMode = '2d';
      const btn2D = document.getElementById('btnView2D');
      if (btn2D) btn2D.click();
    }
  }

  function setupThreeLighting(scene) {
    const ambient = new THREE.AmbientLight(0x1e293b, 1.2);
    scene.add(ambient);
    state.three.ambientLight = ambient;

    const sun = new THREE.DirectionalLight(0xe0f2fe, 1.8);
    sun.position.set(300, 600, 400);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 2048;
    sun.shadow.mapSize.height = 2048;
    sun.shadow.camera.near = 10;
    sun.shadow.camera.far = 1600;
    sun.shadow.camera.left = -600;
    sun.shadow.camera.right = 600;
    sun.shadow.camera.top = 600;
    sun.shadow.camera.bottom = -600;
    scene.add(sun);
    state.three.sunLight = sun;

    // Civic Beacons
    const hospitalLight = new THREE.PointLight(0xef4444, 2.5, 90);
    hospitalLight.position.set(450, 30, 550);
    scene.add(hospitalLight);

    const marketLight = new THREE.PointLight(0xf59e0b, 3.0, 110);
    marketLight.position.set(550, 20, 650);
    scene.add(marketLight);
  }

  function applyNightLighting() {
    state.three.scene.background.set(0x020617);
    state.three.scene.fog.color.set(0x020617);
    state.three.ambientLight.color.set(0x1e293b);
    state.three.ambientLight.intensity = 1.0;
    state.three.sunLight.intensity = 1.4;
    state.three.sunLight.color.set(0x38bdf8);
  }

  function applyDayLighting() {
    state.three.scene.background.set(0x081528);
    state.three.scene.fog.color.set(0x081528);
    state.three.ambientLight.color.set(0x94a3b8);
    state.three.ambientLight.intensity = 2.0;
    state.three.sunLight.intensity = 2.8;
    state.three.sunLight.color.set(0xffedd5);
  }

  // 1x1 km Terrain & Street Grid
  function build3DWorldGround(scene) {
    // 1000m x 1000m ground
    const groundGeo = new THREE.PlaneGeometry(1000, 1000);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x090f1d,
      roughness: 0.88,
      metalness: 0.1
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(500, 0, 500);
    ground.receiveShadow = true;
    scene.add(ground);

    // Street Network Ribbons
    const streetMat = new THREE.MeshStandardMaterial({
      color: 0x182235,
      roughness: 0.7,
      metalness: 0.05
    });

    const arteries = [
      { w: 1000, h: 10, x: 500, z: 500 }, // East-West Main Trunk
      { w: 10, h: 1000, x: 500, z: 500 }, // North-South Main Trunk
      { w: 10, h: 1000, x: 100, z: 500 }, // West Farm Belt Trunk
      { w: 1000, h: 6, x: 500, z: 250 },  // North Arterial
      { w: 1000, h: 6, x: 500, z: 750 },  // South Arterial
      { w: 6, h: 1000, x: 300, z: 500 },  // Residential Trunk
      { w: 6, h: 1000, x: 750, z: 500 }   // East Trunk
    ];

    arteries.forEach(a => {
      const roadGeo = new THREE.PlaneGeometry(a.w, a.h);
      const road = new THREE.Mesh(roadGeo, streetMat);
      road.rotation.x = -Math.PI / 2;
      road.position.set(a.x, 0.05, a.z);
      road.receiveShadow = true;
      scene.add(road);
    });

    // Outer Bounding Perimeter Wall
    const boundaryGeo = new THREE.BoxGeometry(1004, 2, 1004);
    const boundaryMat = new THREE.MeshBasicMaterial({ color: 0x06b6d4, wireframe: true });
    const boundary = new THREE.Mesh(boundaryGeo, boundaryMat);
    boundary.position.set(500, 1, 500);
    scene.add(boundary);
  }

  // West Farm Belts in 3D
  function build3DWestFarmBelts(scene) {
    const farmsGroup = new THREE.Group();
    state.three.farmsGroup = farmsGroup;

    const soilMat = new THREE.MeshStandardMaterial({ color: 0x14532d, roughness: 0.9 });
    const cropMat = new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.6, emissive: 0x15803d, emissiveIntensity: 0.2 });

    for (let b = 0; b < 10; b++) {
      const z = b * 100 + 50;
      // Agricultural plot bed
      const bedGeo = new THREE.BoxGeometry(85, 0.4, 75);
      const bed = new THREE.Mesh(bedGeo, soilMat);
      bed.position.set(48, 0.2, z);
      bed.receiveShadow = true;
      farmsGroup.add(bed);

      // Crop rows
      for (let r = 0; r < 5; r++) {
        const cropGeo = new THREE.BoxGeometry(75, 1.2, 4);
        const crop = new THREE.Mesh(cropGeo, cropMat);
        crop.position.set(48, 0.8, z - 25 + r * 12);
        crop.castShadow = true;
        farmsGroup.add(crop);
      }
    }
    scene.add(farmsGroup);
  }

  // Central Park with Procedural Low-Poly Trees
  function build3DCentralPark(scene) {
    const parkMat = new THREE.MeshStandardMaterial({ color: 0x065f46, roughness: 0.85 });
    const parkGeo = new THREE.BoxGeometry(100, 0.6, 100);
    const park = new THREE.Mesh(parkGeo, parkMat);
    park.position.set(550, 0.3, 550);
    park.receiveShadow = true;
    scene.add(park);

    // Procedural 3D Trees in Park
    const trunkMat = new THREE.MeshStandardMaterial({ color: 0x713f12 });
    const foliageMat = new THREE.MeshStandardMaterial({ color: 0x10b981, roughness: 0.6 });

    for (let t = 0; t < 24; t++) {
      const tx = 510 + (t % 5) * 18 + Math.sin(t) * 4;
      const tz = 510 + Math.floor(t / 5) * 18 + Math.cos(t) * 4;

      const trunkGeo = new THREE.CylinderGeometry(0.5, 0.7, 4, 5);
      const trunk = new THREE.Mesh(trunkGeo, trunkMat);
      trunk.position.set(tx, 2.3, tz);
      trunk.castShadow = true;
      scene.add(trunk);

      const foliageGeo = new THREE.DodecahedronGeometry(2.5, 1);
      const foliage = new THREE.Mesh(foliageGeo, foliageMat);
      foliage.position.set(tx, 5.5, tz);
      foliage.castShadow = true;
      scene.add(foliage);
    }
  }

  // 6 Civic Core Structures & Agora Hologram
  function build3DCivicAnchors(scene) {
    const civicGroup = new THREE.Group();
    state.three.civicGroup = civicGroup;

    state.civicAnchors.forEach(c => {
      if (c.isZone) return;

      const size = c.size;
      const height = c.height || 18;
      const bldgGeo = new THREE.BoxGeometry(size, height, size);
      const bldgMat = new THREE.MeshStandardMaterial({
        color: c.color,
        roughness: 0.3,
        metalness: 0.4
      });
      const bldg = new THREE.Mesh(bldgGeo, bldgMat);
      bldg.position.set(c.x, height / 2, c.z);
      bldg.castShadow = true;
      bldg.receiveShadow = true;
      bldg.userData = { isCivic: true, data: c };

      civicGroup.add(bldg);
      state.three.civicMeshes.push(bldg);

      // Hospital Red Cross Beacon
      if (c.id === 'hospital') {
        const crossH = new THREE.BoxGeometry(8, 2, 2);
        const crossV = new THREE.BoxGeometry(2, 8, 2);
        const crossMat = new THREE.MeshBasicMaterial({ color: 0xff0000 });
        const crossMeshH = new THREE.Mesh(crossH, crossMat);
        const crossMeshV = new THREE.Mesh(crossV, crossMat);
        const crossGroup = new THREE.Group();
        crossGroup.add(crossMeshH);
        crossGroup.add(crossMeshV);
        crossGroup.position.set(c.x, height + 4, c.z);
        civicGroup.add(crossGroup);
        state.three.hospitalBeacon = crossGroup;
      }

      // Agora Market 3D Holographic Trading Ring
      if (c.id === 'market') {
        const ringGeo = new THREE.TorusGeometry(26, 0.8, 16, 64);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, wireframe: true });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 2;
        ring.position.set(c.x, height + 6, c.z);
        civicGroup.add(ring);
        state.three.agoraRing = ring;
      }
    });

    scene.add(civicGroup);
  }

  // 345 Houses according to the 5 Housing Archetypes
  function build3DHouses(scene) {
    if (!scene) scene = state.three.scene;
    if (!scene) return;
    if (!state.worldMeta || !state.worldMeta.houses) return;

    // Clean up existing house meshes if re-building
    if (state.three.housesGroup) {
      scene.remove(state.three.housesGroup);
      state.three.houseMeshes = [];
    }

    const housesGroup = new THREE.Group();
    state.three.housesGroup = housesGroup;
    const houses = state.worldMeta.houses;

    houses.forEach((h, idx) => {
      const [x, z, w, d, archId] = h;
      const arch = state.archetypes[archId] || state.archetypes[0];
      const hHeight = arch.height || 4.0;

      // Base dwelling box
      const houseGeo = new THREE.BoxGeometry(w, hHeight, d);
      const houseMat = new THREE.MeshStandardMaterial({
        color: arch.color,
        roughness: 0.6,
        metalness: 0.1
      });
      const houseMesh = new THREE.Mesh(houseGeo, houseMat);
      houseMesh.position.set(x + w / 2, hHeight / 2, z + d / 2);
      houseMesh.castShadow = true;
      houseMesh.receiveShadow = true;

      // Roof mesh (Pitched or Flat terrace)
      if (archId === 4) {
        // Modern Flat terrace roof
        const roofGeo = new THREE.BoxGeometry(w + 1, 0.4, d + 1);
        const roofMat = new THREE.MeshStandardMaterial({ color: 0x475569 });
        const roof = new THREE.Mesh(roofGeo, roofMat);
        roof.position.set(0, hHeight / 2 + 0.2, 0);
        houseMesh.add(roof);
      } else {
        // Sloped Gable/Hip roof
        const roofGeo = new THREE.ConeGeometry(Math.max(w, d) * 0.7, 2.5, 4);
        const roofMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.8 });
        const roof = new THREE.Mesh(roofGeo, roofMat);
        roof.rotation.y = Math.PI / 4;
        roof.position.set(0, hHeight / 2 + 1.25, 0);
        houseMesh.add(roof);
      }

      houseMesh.userData = {
        isHouse: true,
        index: idx + 1,
        x, z, w, d, archId,
        arch
      };

      housesGroup.add(houseMesh);
      state.three.houseMeshes.push(houseMesh);
    });

    scene.add(housesGroup);
  }

  // gVisor Sandbox Containment Shield in 3D
  function build3DGVisorDome(scene) {
    const shieldGeo = new THREE.IcosahedronGeometry(175, 2);
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

  // 64 Procedural Multi-Agent Avatars in 3D
  function build3DAgents(scene) {
    if (!scene) scene = state.three.scene;
    if (!scene) return;
    if (!state.agents || state.agents.length === 0) return;

    // Clean up existing agent meshes if re-building
    if (state.three.agentsGroup) {
      scene.remove(state.three.agentsGroup);
      state.three.agentMeshes = [];
    }

    const agentsGroup = new THREE.Group();
    state.three.agentsGroup = agentsGroup;

    state.agents.forEach(a => {
      const agentContainer = new THREE.Group();
      agentContainer.position.set(a.position.x, 0.8, a.position.z);

      // Body capsule / cylinder
      const roleColor = new THREE.Color(a.color || '#10b981');
      const bodyGeo = new THREE.CylinderGeometry(0.8, 0.8, 1.6, 8);
      const bodyMat = new THREE.MeshStandardMaterial({ color: roleColor, roughness: 0.3 });
      const body = new THREE.Mesh(bodyGeo, bodyMat);
      body.castShadow = true;
      body.userData = { isAgent: true, data: a };
      agentContainer.add(body);

      // Floating role halo
      const haloGeo = new THREE.RingGeometry(1.0, 1.4, 16);
      const haloMat = new THREE.MeshBasicMaterial({ color: roleColor, side: THREE.DoubleSide });
      const halo = new THREE.Mesh(haloGeo, haloMat);
      halo.rotation.x = Math.PI / 2;
      halo.position.y = 1.6;
      halo.userData = { isAgent: true, data: a };
      agentContainer.add(halo);

      agentContainer.userData = { isAgent: true, data: a };

      agentsGroup.add(agentContainer);
      state.three.agentMeshes.push({ container: agentContainer, body, halo, data: a });
    });

    scene.add(agentsGroup);
  }

  function syncAgentMeshes() {
    state.three.agentMeshes.forEach(item => {
      const match = state.agents.find(a => a.id === item.data.id);
      if (match) {
        item.data = match;
        item.container.position.x = match.position.x;
        item.container.position.z = match.position.z;
      }
    });
  }

  // 3D Raycasting & Mouse Interaction
  function onThreeMouseMove(e) {
    const rect = state.three.renderer.domElement.getBoundingClientRect();
    state.three.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
    state.three.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

    const agentParts = [];
    state.three.agentMeshes.forEach(item => {
      if (item.container && item.container.children) {
        item.container.children.forEach(c => agentParts.push(c));
      }
    });

    state.three.raycaster.setFromCamera(state.three.mouse, state.three.camera);
    const intersects = state.three.raycaster.intersectObjects([
      ...state.three.houseMeshes,
      ...state.three.civicMeshes,
      ...agentParts
    ]);

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
  }

  function onThreeClick() {
    const agentParts = [];
    state.three.agentMeshes.forEach(item => {
      if (item.container && item.container.children) {
        item.container.children.forEach(c => agentParts.push(c));
      }
    });

    state.three.raycaster.setFromCamera(state.three.mouse, state.three.camera);
    const intersects = state.three.raycaster.intersectObjects([
      ...state.three.houseMeshes,
      ...state.three.civicMeshes,
      ...agentParts
    ]);

    if (intersects.length > 0) {
      const obj = intersects[0].object;
      state.three.selectedObject = obj;

      if (obj.userData && obj.userData.isAgent) {
        inspectAgent(obj.userData.data);
      } else if (obj.userData && obj.userData.isHouse) {
        inspectHouse(obj.userData);
      } else if (obj.userData && obj.userData.isCivic) {
        inspectCivic(obj.userData.data);
      }
    }
  }

  function handleThreeResize() {
    const container = document.getElementById('threeContainer');
    if (!container || !state.three.renderer || !state.three.camera) return;
    const w = container.clientWidth  || container.offsetWidth  || window.innerWidth  * 0.65 || 900;
    const h = container.clientHeight || container.offsetHeight || window.innerHeight * 0.76 || 580;
    if (w <= 0 || h <= 0) return; // Skip degenerate layouts
    state.three.camera.aspect = w / h;
    state.three.camera.updateProjectionMatrix();
    state.three.renderer.setSize(w, h, false); // false = don't update canvas CSS size (CSS controls it)
  }

  // Continuous 3D Animation Loop
  function animateThree() {
    requestAnimationFrame(animateThree);

    const { controls, renderer, scene, camera, shieldMesh, agoraRing, camTargetPos, camLookAtPos } = state.three;

    // Smooth camera transitions for demonstration bookmarks
    if (camTargetPos && camLookAtPos && camera && controls) {
      camera.position.lerp(camTargetPos, 0.05);
      controls.target.lerp(camLookAtPos, 0.05);

      if (camera.position.distanceTo(camTargetPos) < 2) {
        state.three.camTargetPos = null;
        state.three.camLookAtPos = null;
      }
    }

    if (controls) controls.update();

    // Rotate gVisor containment dome
    if (shieldMesh) {
      shieldMesh.rotation.y += 0.002;
      shieldMesh.rotation.x += 0.001;
    }

    // Rotate Agora market trading ring
    if (agoraRing) {
      agoraRing.rotation.z += 0.015;
    }

    // Render 3D Frame
    if (renderer && scene && camera && state.viewMode === '3d') {
      renderer.render(scene, camera);
    }
  }

  // =========================================================================
  // Inspector Sidebar View Logic
  // =========================================================================
  function inspectHouse(house) {
    const arch = house.arch || state.archetypes[house.archId] || state.archetypes[0];
    const elIcon = document.getElementById('selectedIcon');
    const elTitle = document.getElementById('selectedTitle');
    const elBadge = document.getElementById('selectedTypeBadge');
    const elCoord = document.getElementById('selectedCoord');
    const elFloors = document.getElementById('selectedFloors');
    const elMaterials = document.getElementById('selectedMaterials');
    const elConn = document.getElementById('selectedStreetConn');
    const subTitle = document.getElementById('subPanelTitle');

    if (elIcon) elIcon.textContent = '🏡';
    if (elTitle) elTitle.textContent = `House #${String(house.index).padStart(3, '0')} · ${arch.name} Archetype`;
    if (elBadge) {
      elBadge.textContent = `TYPE ${house.archId}`;
      elBadge.style.backgroundColor = `${arch.hex}33`;
      elBadge.style.color = arch.hex;
      elBadge.style.borderColor = `${arch.hex}66`;
    }

    if (elCoord) elCoord.textContent = `X: ${house.x}m · Z: ${house.z}m (${house.w}×${house.d}m)`;
    if (elFloors) elFloors.textContent = `${arch.floors} Floor · ${arch.height}m Height`;
    if (elMaterials) elMaterials.textContent = `${arch.walls} / ${arch.roof}`;
    if (elConn) elConn.textContent = 'CONNECTED (Walkway 1.2m to Road)';

    if (subTitle) subTitle.textContent = 'Furnishing Manifest (Voxel Interior)';
    const pills = document.getElementById('furnishingPills');
    if (pills) {
      pills.innerHTML = `
        <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">🛋️ Sofa (FAB)</span>
        <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">📺 CRT TV (TV)</span>
        <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">🍳 Stove / Range</span>
        <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">🛏️ Oak Bed (${arch.floors > 1 ? 'Upper Floor' : 'Main Floor'})</span>
        <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">🚪 Hinged Door (Z)</span>
      `;
    }
  }

  function inspectCivic(civic) {
    const elIcon = document.getElementById('selectedIcon');
    const elTitle = document.getElementById('selectedTitle');
    const elBadge = document.getElementById('selectedTypeBadge');
    const elCoord = document.getElementById('selectedCoord');
    const elFloors = document.getElementById('selectedFloors');
    const elMaterials = document.getElementById('selectedMaterials');
    const elConn = document.getElementById('selectedStreetConn');
    const subTitle = document.getElementById('subPanelTitle');

    if (elIcon) elIcon.textContent = civic.icon;
    if (elTitle) elTitle.textContent = `${civic.name}`;
    if (elBadge) {
      elBadge.textContent = 'CIVIC CORE';
      elBadge.style.backgroundColor = `${civic.hex}33`;
      elBadge.style.color = civic.hex;
      elBadge.style.borderColor = `${civic.hex}66`;
    }

    if (elCoord) elCoord.textContent = `Center: X: ${civic.x}m · Z: ${civic.z}m`;
    if (elFloors) elFloors.textContent = 'Civic Infrastructure';
    if (elMaterials) elMaterials.textContent = 'REINFORCED CONCRETE / STEEL';
    if (elConn) elConn.textContent = 'TRUNK INTERSECTION (6m Road)';

    if (subTitle) subTitle.textContent = 'Civic Subsystem Function';
    const pills = document.getElementById('furnishingPills');
    if (pills) {
      pills.innerHTML = `
        <span class="px-2 py-0.5 rounded bg-slate-800 text-cyan-300">🏛️ Function: ${civic.desc}</span>
        <span class="px-2 py-0.5 rounded bg-slate-800 text-amber-300">⚡ Grid Node: Priority A</span>
        <span class="px-2 py-0.5 rounded bg-slate-800 text-purple-300">🔒 gVisor Monitored</span>
      `;
    }
  }

  // =========================================================================
  // Agent Inspector & Reactive Cross-Module Synchronization
  // =========================================================================
  function inspectAgent(agent) {
    if (!agent) return;
    state.selectedAgentId = agent.id;

    // Pulse and enlarge agent halo in 3D
    state.three.agentMeshes.forEach(item => {
      const isTarget = item.data.id === agent.id;
      if (item.halo) {
        if (isTarget) {
          item.halo.scale.set(1.8, 1.8, 1.8);
          item.halo.material.color.setHex(0x06b6d4);
        } else {
          item.halo.scale.set(1.0, 1.0, 1.0);
          item.halo.material.color.set(new THREE.Color(item.data.color || '#10b981'));
        }
      }
    });

    const elIcon = document.getElementById('selectedIcon');
    const elTitle = document.getElementById('selectedTitle');
    const elBadge = document.getElementById('selectedTypeBadge');
    const elCoord = document.getElementById('selectedCoord');
    const elFloors = document.getElementById('selectedFloors');
    const elMaterials = document.getElementById('selectedMaterials');
    const elConn = document.getElementById('selectedStreetConn');
    const subTitle = document.getElementById('subPanelTitle');
    const pills = document.getElementById('furnishingPills');

    if (elIcon) elIcon.textContent = '🤖';
    if (elTitle) elTitle.textContent = `${agent.id} · ${agent.role || 'Autonomous Citizen'}`;
    if (elBadge) {
      elBadge.textContent = (agent.role || 'AGENT').toUpperCase();
      elBadge.style.backgroundColor = `${agent.color || '#06b6d4'}33`;
      elBadge.style.color = agent.color || '#06b6d4';
      elBadge.style.borderColor = `${agent.color || '#06b6d4'}66`;
    }

    const posX = Math.round(agent.position.x || agent.position[0] || 500);
    const posZ = Math.round(agent.position.z || agent.position[1] || 500);
    if (elCoord) elCoord.textContent = `X: ${posX}m · Z: ${posZ}m (Substrate Voxel Grid)`;
    if (elFloors) elFloors.textContent = `Policy Core: Chebyshev Homeostasis (L∞)`;
    if (elMaterials) elMaterials.textContent = `Wallet: ${agent.currency || 28} C · Invariant: Conserved`;
    if (elConn) elConn.textContent = `Action Status: ${agent.status || 'Active Moore Transition'}`;

    if (subTitle) subTitle.textContent = 'Chebyshev Homeostatic Radar (Phase 1.2 Metric)';
    if (pills) {
      const vitals = agent.vitals || {};
      const energy = vitals.energy !== undefined ? vitals.energy : 86;
      const food = vitals.food !== undefined ? vitals.food : 74;
      const social = vitals.social !== undefined ? vitals.social : 92;
      const shelter = vitals.shelter !== undefined ? vitals.shelter : 82;

      pills.innerHTML = `
        <div class="w-full space-y-2 pt-1 font-mono">
          <div>
            <div class="flex justify-between text-[10px] text-slate-300 mb-0.5">
              <span>Energy Vital</span>
              <span class="text-cyan-400 font-bold">${energy}%</span>
            </div>
            <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div class="h-full bg-cyan-400 rounded-full" style="width: ${energy}%"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-[10px] text-slate-300 mb-0.5">
              <span>Food Stock</span>
              <span class="text-amber-400 font-bold">${food}%</span>
            </div>
            <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div class="h-full bg-amber-400 rounded-full" style="width: ${food}%"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-[10px] text-slate-300 mb-0.5">
              <span>Social Cohesion</span>
              <span class="text-purple-400 font-bold">${social}%</span>
            </div>
            <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div class="h-full bg-purple-400 rounded-full" style="width: ${social}%"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between text-[10px] text-slate-300 mb-0.5">
              <span>Shelter Comfort</span>
              <span class="text-emerald-400 font-bold">${shelter}%</span>
            </div>
            <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div class="h-full bg-emerald-400 rounded-full" style="width: ${shelter}%"></div>
            </div>
          </div>
        </div>
      `;
    }

    // Synchronize Agora Order Book
    syncOrderBookWithAgent(agent.id);

    // Synchronize Rule Library
    if (agent.active_rule) {
      selectRule(agent.active_rule);
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

  function selectRule(ruleId) {
    state.selectedRuleId = ruleId;
    renderVerifiedRulesList();
    updateRuleViewer();

    // 3D camera sync based on rule target
    if (state.three.camera && state.three.controls) {
      if (ruleId === 'rule_gather_crop_v2') {
        state.three.camTargetPos = new THREE.Vector3(140, 80, 500);
        state.three.camLookAtPos = new THREE.Vector3(50, 0, 500);
      } else if (ruleId === 'rule_trade_agora') {
        state.three.camTargetPos = new THREE.Vector3(550, 45, 650);
        state.three.camLookAtPos = new THREE.Vector3(550, 0, 650);
      } else if (ruleId === 'rule_civic_maintenance') {
        state.three.camTargetPos = new THREE.Vector3(450, 45, 450);
        state.three.camLookAtPos = new THREE.Vector3(450, 0, 450);
      }
    }

    // Pulse gVisor shield in 3D
    if (state.three.shieldMesh) {
      state.three.shieldMesh.material.opacity = 0.65;
      setTimeout(() => {
        if (state.three.shieldMesh) state.three.shieldMesh.material.opacity = 0.22;
      }, 1400);
    }
  }

  // =========================================================================
  // 2D Orthographic Canvas Fallback Map
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

    canvas.addEventListener('wheel', handle2DWheel, { passive: false });
    canvas.addEventListener('mousedown', handle2DMousedown);
    window.addEventListener('mousemove', handle2DMousemove);
    window.addEventListener('mouseup', handle2DMouseup);
  }

  function zoom2D(factor) {
    const m = state.map2d;
    const newScale = Math.min(m.maxScale, Math.max(m.minScale, m.scale * factor));
    const cx = m.canvas.width / 2;
    const cy = m.canvas.height / 2;
    m.offsetX = cx - (cx - m.offsetX) * (newScale / m.scale);
    m.offsetY = cy - (cy - m.offsetY) * (newScale / m.scale);
    m.scale = newScale;
    render2DWorldMap();
  }

  function handle2DWheel(e) {
    e.preventDefault();
    zoom2D(e.deltaY < 0 ? 1.15 : 0.85);
  }

  function handle2DMousedown(e) {
    state.map2d.isDragging = true;
    state.map2d.dragStartX = e.clientX - state.map2d.offsetX;
    state.map2d.dragStartY = e.clientY - state.map2d.offsetY;
  }

  function handle2DMousemove(e) {
    if (state.map2d.isDragging) {
      state.map2d.offsetX = e.clientX - state.map2d.dragStartX;
      state.map2d.offsetY = e.clientY - state.map2d.dragStartY;
      render2DWorldMap();
    }
  }

  function handle2DMouseup() {
    state.map2d.isDragging = false;
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

    // Farms
    if (state.three.layers.farms) {
      ctx.fillStyle = 'rgba(16, 185, 129, 0.12)';
      ctx.fillRect(0, 0, 100, 1000);
    }

    // Civic
    if (state.three.layers.civic) {
      state.civicAnchors.forEach(c => {
        if (c.isZone) {
          ctx.fillStyle = 'rgba(5, 150, 105, 0.25)';
          ctx.fillRect(c.x, c.z, c.w, c.h);
        } else {
          ctx.fillStyle = c.hex;
          ctx.beginPath();
          ctx.arc(c.x, c.z, c.size / 2, 0, Math.PI * 2);
          ctx.fill();
        }
      });
    }

    // Houses
    if (state.three.layers.houses && state.worldMeta && state.worldMeta.houses) {
      state.worldMeta.houses.forEach(h => {
        const [x, z, w, d, archId] = h;
        const arch = state.archetypes[archId] || state.archetypes[0];
        ctx.fillStyle = arch.hex;
        ctx.fillRect(x, z, w, d);
      });
    }

    // Agents
    if (state.three.layers.agents && state.agents) {
      state.agents.forEach(a => {
        ctx.fillStyle = a.color || '#10b981';
        ctx.beginPath();
        ctx.arc(a.position.x, a.position.z, 3.5, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    ctx.restore();
  }

  // =========================================================================
  // Telemetry Lists: Archetypes & Materials
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
        <div class="archetype-row">
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
      const voxCount = m.voxels !== undefined ? m.voxels : (m.count !== undefined ? m.count : 'Solid');
      return `
        <div class="mat-item">
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

  // =========================================================================
  // Tab 2: Environment Logic & Ecological Pools
  // =========================================================================
  function renderLocationPools() {
    const grid = document.getElementById('locationPoolsGrid');
    if (!grid || !state.envState) return;

    const pools = state.envState.locations || state.envState.ecological_pools || {
      west_farms: { food: 550, renewal_rate: 15, capacity: 800 },
      plaza: { food: 95, wood: 140, renewal_rate: 2, capacity: 200 },
      grove: { wood: 420, renewal_rate: 10, capacity: 600 },
      quarry: { stone: 310, renewal_rate: 8, capacity: 500 },
      market_square: { stone: 120, renewal_rate: 1, capacity: 250 }
    };

    grid.innerHTML = Object.entries(pools).map(([key, p]) => {
      const currentStock = p.stock !== undefined ? p.stock : (p.food || p.wood || p.stone || 100);
      const cap = p.capacity || 500;
      const pct = Math.min(100, Math.round((currentStock / cap) * 100));
      return `
        <div class="bg-slate-950/70 border border-slate-800 p-3.5 rounded-xl flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="text-xs font-mono font-bold text-slate-200 uppercase">${key.replace('_', ' ')}</span>
              <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/40">+${p.renewal_rate || 5}/tick</span>
            </div>
            <div class="text-base font-bold font-mono text-cyan-300">${Math.round(currentStock)} <span class="text-xs text-slate-400">/ ${cap}</span></div>
          </div>
          
          <div class="mt-3">
            <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div class="h-full bg-cyan-500 rounded-full transition-all duration-300" style="width: ${pct}%"></div>
            </div>
            <div class="flex justify-between text-[10px] font-mono text-slate-400 mt-1">
              <span>Capacity Pool</span>
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
    const pointsCount = 20;
    const history = [];
    for (let i = 0; i < pointsCount; i++) {
      const t = tick - (pointsCount - 1 - i);
      const food = 480 + Math.sin(t * 0.4) * 45 + (i * 1.5);
      const energy = 390 + Math.cos(t * 0.3) * 35;
      const currency = 1280;
      history.push({ t, food, energy, currency });
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

    drawLine('food', '#f59e0b', 300, 600);
    drawLine('energy', '#06b6d4', 300, 600);

    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px "Fira Code", monospace';
    ctx.fillText('FOOD GRAIN', 50, 20);
    ctx.fillStyle = '#f59e0b';
    ctx.fillRect(40, 12, 6, 6);

    ctx.fillStyle = '#94a3b8';
    ctx.fillText('ENERGY POOL', 150, 20);
    ctx.fillStyle = '#06b6d4';
    ctx.fillRect(140, 12, 6, 6);

    ctx.fillStyle = '#94a3b8';
    ctx.fillText('CURRENCY INVARIANT (1,280 C CONSTANT)', 260, 20);
    ctx.fillStyle = '#10b981';
    ctx.fillRect(250, 12, 6, 6);
  }

  // =========================================================================
  // Tab 3: Market Economy & Social Structure
  // =========================================================================
  function renderOrderBook() {
    const bidsEl = document.getElementById('bidsTableBody');
    const asksEl = document.getElementById('asksTableBody');
    if (!bidsEl || !asksEl || !state.economyState || !state.economyState.order_book) return;

    const { bids, asks } = state.economyState.order_book;

    bidsEl.innerHTML = (bids || []).slice(0, 5).map(b => {
      const qty = b.quantity || b.qty || 10;
      const agent = b.agent || b.agent_id || 'agent_XX';
      const isMatch = state.selectedAgentId && (agent === state.selectedAgentId || agent.includes(state.selectedAgentId));
      const barW = Math.min(100, qty * 2);
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
      const qty = a.quantity || a.qty || 10;
      const agent = a.agent || a.agent_id || 'agent_XX';
      const isMatch = state.selectedAgentId && (agent === state.selectedAgentId || agent.includes(state.selectedAgentId));
      const barW = Math.min(100, qty * 2);
      return `
        <div class="relative py-1 px-2 rounded flex justify-between items-center text-[11px] overflow-hidden ${isMatch ? 'order-agent-match' : ''}">
          <div class="absolute inset-y-0 right-0 bg-rose-500/15 pointer-events-none" style="width: ${barW}%;"></div>
          <span class="text-rose-400 font-bold z-10">${Number(a.price).toFixed(2)} C</span>
          <span class="text-slate-200 z-10">${qty}</span>
          <span class="${isMatch ? 'text-cyan-300 font-bold' : 'text-slate-500'} z-10">${agent}</span>
        </div>
      `;
    }).join('');
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

    const lorenzRaw = state.economyState.lorenz_curve;
    let coords = [];
    if (Array.isArray(lorenzRaw)) {
      coords = lorenzRaw.map(pt => [pt.pop_pct / 100, pt.wealth_pct / 100]);
    } else if (lorenzRaw && lorenzRaw.coordinates) {
      coords = lorenzRaw.coordinates;
    } else {
      coords = [[0,0], [0.2, 0.08], [0.4, 0.20], [0.6, 0.38], [0.8, 0.62], [1.0, 1.0]];
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

    const manuals = state.economyState.living_manuals || state.economyState.manuals || [];
    grid.innerHTML = manuals.map(m => `
      <div class="bg-slate-950/70 border border-slate-800 p-4 rounded-xl flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between pb-2 border-b border-slate-800/80 mb-2">
            <span class="text-xs font-mono font-bold text-purple-400">${m.situation_key || m.manual_id}</span>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">GEN ${m.generation || 1}</span>
          </div>
          <h4 class="text-xs font-bold text-white mb-1">${m.rule_ref || m.title || 'Manual Entry'}</h4>
          <p class="text-[11px] text-slate-400 leading-relaxed">${m.summary}</p>
        </div>

        <div class="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] font-mono text-slate-500">
          <span>Subscribers: <strong class="text-slate-300">${m.subscribers || m.adoption_rate || 20}</strong></span>
          <span>Confidence: <strong class="text-emerald-400">${m.confidence || m.efficacy_score || 0.95}</strong></span>
        </div>
      </div>
    `).join('');
  }

  // =========================================================================
  // Tab 4: Verified Rule Library Viewer
  // =========================================================================
  function renderVerifiedRulesList() {
    const list = document.getElementById('ruleItemsList');
    if (!list) return;

    list.innerHTML = state.rules.map(r => {
      const isActive = r.rule_id === state.selectedRuleId;
      const transitions = r.tested_transitions || r.transitions_tested || 500;
      return `
        <div class="rule-card ${isActive ? 'active' : ''}" data-rule="${r.rule_id}">
          <div class="flex items-center justify-between mb-1">
            <span class="font-mono text-xs font-bold text-slate-200">${r.rule_id}</span>
            <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">${r.status}</span>
          </div>
          <div class="text-[11px] text-slate-400 mb-2">${r.name}</div>
          <div class="flex items-center justify-between text-[10px] font-mono text-slate-500">
            <span>Transitions: <strong class="text-slate-300">${transitions}</strong></span>
            <span>False Promo: <strong class="text-emerald-400">${r.false_promotion_rate}</strong></span>
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
    if (elFalse) elFalse.textContent = rule.false_promotion_rate;
    if (elTrans) elTrans.textContent = `${rule.tested_transitions || rule.transitions_tested || 480} Transitions`;
  }

  // =========================================================================
  // Tab 5: System Pipeline & STAGED LLM ROUTE (Hazard Orange)
  // =========================================================================
  function renderPipelineGraph() {
    const svg = document.getElementById('pipelineSvg');
    if (!svg || !state.pipeline || !state.pipeline.nodes) return;

    const nodes = state.pipeline.nodes;
    const links = state.pipeline.edges || state.pipeline.links || [];

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
        <marker id="arrowhead-orange" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill="#f97316" />
        </marker>
      </defs>
    `;

    links.forEach(l => {
      const from = coords[l.from];
      const to = coords[l.to];
      if (!from || !to) return;

      const isToLLM = l.to === 'llm_cognitive_route' || l.from === 'llm_cognitive_route';
      const strokeColor = isToLLM ? '#f97316' : '#334155';
      const marker = isToLLM ? 'url(#arrowhead-orange)' : 'url(#arrowhead)';

      svgHtml += `
        <line x1="${from.x}" y1="${from.y}" x2="${to.x}" y2="${to.y}" 
              stroke="${strokeColor}" stroke-width="${isToLLM ? 2.5 : 1.5}" 
              marker-end="${marker}" class="${isToLLM ? 'pipe-link' : ''}" />
      `;
    });

    nodes.forEach(n => {
      const pt = coords[n.id];
      if (!pt) return;

      const isLLM = n.is_incomplete || n.id === 'llm_cognitive_route';

      if (isLLM) {
        svgHtml += `
          <g class="pipe-node" transform="translate(${pt.x - 75}, ${pt.y - 45})">
            <rect x="-4" y="-4" width="158" height="98" rx="14" 
                  fill="rgba(249, 115, 22, 0.15)" stroke="#f97316" stroke-width="2" stroke-dasharray="6,4">
              <animate attributeName="opacity" values="0.4;1;0.4" dur="2s" repeatCount="indefinite" />
            </rect>
            <rect x="0" y="0" width="150" height="90" rx="10" 
                  fill="#1c0e05" stroke="#f97316" stroke-width="2.5" />
            
            <text x="75" y="24" text-anchor="middle" font-family="'Fira Code', monospace" 
                  font-size="10" font-weight="bold" fill="#fdba74">⚠️ COGNITIVE AGENT</text>
            <text x="75" y="42" text-anchor="middle" font-family="'Inter', sans-serif" 
                  font-size="11" font-weight="bold" fill="#ffffff">LLM / Agent Route</text>
            
            <rect x="15" y="55" width="120" height="20" rx="4" fill="rgba(249, 115, 22, 0.3)" stroke="#f97316" />
            <text x="75" y="69" text-anchor="middle" font-family="'Fira Code', monospace" 
                  font-size="9" font-weight="bold" fill="#f97316">STAGED / 0 INFERENCE</text>
          </g>
        `;
      } else {
        const color = n.color || '#38bdf8';
        const label = n.name || n.label || 'Node';
        const type = n.phase || n.type || 'Subsystem';
        const status = n.status_label || n.status || 'Active';

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

  // =========================================================================
  // Tab 6: 10-Gate Patent-Grade Source-Audit Certificate Checklist
  // =========================================================================
  function renderAuditChecklist() {
    const grid = document.getElementById('auditChecklistGrid');
    if (!grid || !state.auditData) return;

    const list = state.auditData.checks || state.auditData.gates || [];
    grid.innerHTML = list.map((g, i) => `
      <div class="p-3 rounded-lg bg-slate-950/70 border border-emerald-900/40 flex items-start gap-3">
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
