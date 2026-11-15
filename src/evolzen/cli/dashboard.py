"""Interactive Visual Dashboard & Generative UI generator for EvolZen (Phases 1.1-1.3).

Generates standalone, responsive, dark-themed HTML5/SVG/CSS dashboard files with zero
external network dependencies (hermetic offline rendering).

Visualizes:
1. View 1: 5D CVTArchive Voronoi Niche Map (Centroidal Voronoi Tessellation MAP-Elites;
   Vassiliades et al., IEEE TEVC 2018, DOI:10.1109/TEVC.2017.2735550; Wang et al., ICML 2024).
2. View 2: Agent Lineage Family Tree (Multi-generation parent-offspring genealogical tree
   with roles, status, and institutional norms; docs/phases/1.2-agents.md).
3. View 3: Spatial Resource & Agent Heatmap (Location network nodes with food, wood, stone
   bars, carrying capacities, and agent occupancy; docs/phases/1.1-environment.md).
4. View 4: Macroeconomic Lorenz & Gini Visualizer (Exact SVG Lorenz curve plotted from agent
   wealth distributions, line of perfect equality, and Gini index; docs/phases/1.3-economy.md).
"""
from __future__ import annotations

import html
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from evolzen.agents.qd_archive import CVTArchive, QDArchiveEntry
    from evolzen.schemas.world import WorldAgentState, WorldState


def generate_dashboard_html(
    world: WorldState,
    archive: CVTArchive,
    gini: float,
    desc: tuple[float, ...],
) -> str:
    """Generate a hermetic standalone HTML5/SVG interactive dashboard.

    Args:
        world: Current persistent WorldState containing agents, locations, norms.
        archive: 5D CVTArchive containing Voronoi centroids and occupied elites.
        gini: Macroeconomic Gini inequality coefficient in [0.0, 1.0].
        desc: Normalized 5D behavioral descriptor tuple of founder agent.

    Returns:
        Complete self-contained HTML5 string with dark theme and responsive layout.
    """
    header_html = _render_header(world, archive, gini, desc)
    view1_html = _render_view1_cvt_archive(archive, desc)
    view2_html = _render_view2_lineage_tree(world)
    view3_html = _render_view3_spatial_heatmap(world)
    view4_html = _render_view4_lorenz_gini(world, gini)
    styles = _render_styles()
    scripts = _render_scripts()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EvolZen Visual State Dashboard</title>
  <style>
{styles}
  </style>
</head>
<body>
  <div class="dashboard-container">
    {header_html}

    <nav class="view-tabs" id="tabNav" aria-label="Dashboard Navigation">
      <button class="tab-btn active" data-tab="all" onclick="switchTab('all')">All Views</button>
      <button class="tab-btn" data-tab="view-1" onclick="switchTab('view-1')">1. Voronoi Niche Map</button>
      <button class="tab-btn" data-tab="view-2" onclick="switchTab('view-2')">2. Lineage Family Tree</button>
      <button class="tab-btn" data-tab="view-3" onclick="switchTab('view-3')">3. Spatial Heatmap</button>
      <button class="tab-btn" data-tab="view-4" onclick="switchTab('view-4')">4. Lorenz &amp; Gini</button>
    </nav>

    <main class="views-wrapper">
      <section id="view-1" class="dashboard-section">
        {view1_html}
      </section>

      <section id="view-2" class="dashboard-section">
        {view2_html}
      </section>

      <section id="view-3" class="dashboard-section">
        {view3_html}
      </section>

      <section id="view-4" class="dashboard-section">
        {view4_html}
      </section>
    </main>

    <footer class="dashboard-footer">
      <p>EvolZen Research Platform &bull; Hermetic Offline Generative UI &bull; Seed {world.seed} &bull; World Version {html.escape(world.world_version)}</p>
    </footer>
  </div>

  <script>
{scripts}
  </script>
</body>
</html>
"""


def _render_header(
    world: WorldState,
    archive: CVTArchive,
    gini: float,
    desc: tuple[float, ...],
) -> str:
    """Render top summary KPIs and metadata banner."""
    cov = archive.coverage()
    total_niches = archive.total_niches()
    cov_pct = (cov / max(1, total_niches)) * 100.0
    desc_str = ", ".join(f"{v:.2f}" for v in desc)

    return f"""
    <header class="dashboard-header">
      <div class="header-titles">
        <div class="brand-badge">EVOLZEN 2.0</div>
        <h1>Interactive System State Dashboard</h1>
        <p class="subtitle">Multi-Agent Quality-Diversity, Genealogical Lineage, Spatial Ecology &amp; Macroeconomy</p>
      </div>
      <div class="kpi-grid">
        <div class="kpi-card">
          <span class="kpi-label">World Version</span>
          <span class="kpi-value highlight-cyan">{html.escape(world.world_version)}</span>
          <span class="kpi-sub">Tick #{world.tick} (Seed {world.seed})</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Registered Agents</span>
          <span class="kpi-value highlight-emerald">{len(world.agents)}</span>
          <span class="kpi-sub">{sum(1 for a in world.agents.values() if a.alive)} living population</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Spatial Locations</span>
          <span class="kpi-value highlight-indigo">{len(world.locations)}</span>
          <span class="kpi-sub">{len(world.artifacts)} artifacts, {len(world.norms)} norms</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">CVT Niche Coverage</span>
          <span class="kpi-value highlight-amber">{cov}/{total_niches}</span>
          <span class="kpi-sub">{cov_pct:.1f}% occupied</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Wealth Gini Index</span>
          <span class="kpi-value highlight-rose">{gini:.4f}</span>
          <span class="kpi-sub">{"Equal" if gini < 0.25 else "Moderate" if gini < 0.45 else "Concentrated"}</span>
        </div>
        <div class="kpi-card">
          <span class="kpi-label">Founder 5D Descriptor</span>
          <span class="kpi-value small-code highlight-purple">[{desc_str}]</span>
          <span class="kpi-sub">[Risk, Status, Social, Norm, Res]</span>
        </div>
      </div>
    </header>
    """


def _render_view1_cvt_archive(archive: CVTArchive, desc: tuple[float, ...]) -> str:
    """Render View 1: 5D CVTArchive Voronoi Niche Map."""
    centroids = archive.centroids
    cells = archive.cells
    total_niches = archive.total_niches()
    cov = archive.coverage()

    # SVG Canvas dimensions
    svg_w, svg_h = 720, 420
    pad_l, pad_r, pad_t, pad_b = 60, 40, 40, 50
    plot_w = svg_w - pad_l - pad_r
    plot_h = svg_h - pad_t - pad_b

    # Centroid projected coordinates (c[0] for x, c[1] for y)
    def to_canvas(c: tuple[float, ...]) -> tuple[float, float]:
        cx = pad_l + max(0.0, min(1.0, c[0])) * plot_w
        cy = (pad_t + plot_h) - max(0.0, min(1.0, c[1])) * plot_h
        return cx, cy

    # Generate Delaunay-like proximity mesh between centroids
    mesh_lines: list[str] = []
    for i, c1 in enumerate(centroids):
        x1, y1 = to_canvas(c1)
        for j in range(i + 1, len(centroids)):
            c2 = centroids[j]
            dist_5d = math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2, strict=True)))
            if dist_5d < 0.65:
                x2, y2 = to_canvas(c2)
                mesh_lines.append(
                    f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                    f'stroke="rgba(148,163,184,0.18)" stroke-width="1.5" stroke-dasharray="4,4" />'
                )

    # Render centroid Voronoi nodes
    nodes_svg: list[str] = []
    table_rows: list[str] = []

    for idx, centroid in enumerate(centroids):
        cx, cy = to_canvas(centroid)
        occupied_entry: QDArchiveEntry | None = cells.get(idx)
        is_occupied = occupied_entry is not None

        c_coords_str = ", ".join(f"{v:.2f}" for v in centroid)
        if is_occupied and occupied_entry is not None:
            fit = occupied_entry.fitness
            agent_id = occupied_entry.agent_id
            status_badge = '<span class="pill pill-success">OCCUPIED</span>'

            nodes_svg.append(f"""
            <g class="niche-node occupied" tabindex="0">
              <circle cx="{cx:.1f}" cy="{cy:.1f}" r="24" fill="rgba(16,185,129,0.2)" stroke="#10b981" stroke-width="2.5" filter="url(#glow-green)"/>
              <circle cx="{cx:.1f}" cy="{cy:.1f}" r="14" fill="#10b981" />
              <text x="{cx:.1f}" y="{cy + 4:.1f}" fill="#0f172a" font-size="11" font-weight="bold" text-anchor="middle">#{idx}</text>
              <text x="{cx:.1f}" y="{cy - 28:.1f}" fill="#34d399" font-size="11" font-weight="600" text-anchor="middle">{fit:.1f}</text>
              <title>Niche #{idx} [Occupied]&#10;Agent: {html.escape(agent_id)}&#10;Fitness: {fit:.2f}&#10;Coords: [{c_coords_str}]</title>
            </g>
            """)
        else:
            agent_id = "-"
            status_badge = '<span class="pill pill-muted">VACANT</span>'

            nodes_svg.append(f"""
            <g class="niche-node vacant" tabindex="0">
              <circle cx="{cx:.1f}" cy="{cy:.1f}" r="18" fill="#1e293b" stroke="#475569" stroke-width="1.5" stroke-dasharray="3,3"/>
              <text x="{cx:.1f}" y="{cy + 4:.1f}" fill="#94a3b8" font-size="11" text-anchor="middle">#{idx}</text>
              <title>Niche #{idx} [Vacant]&#10;Coords: [{c_coords_str}]</title>
            </g>
            """)

        table_rows.append(f"""
        <tr>
          <td><strong>#{idx}</strong></td>
          <td>{status_badge}</td>
          <td><code>{html.escape(agent_id)}</code></td>
          <td class="num-cell">{f"{occupied_entry.fitness:.2f}" if occupied_entry is not None else "-"}</td>
          <td class="code-cell">[{c_coords_str}]</td>
        </tr>
        """)

    # Render Founder Agent descriptor marker
    fx, fy = to_canvas(desc)
    founder_marker = f"""
    <g class="founder-marker" tabindex="0">
      <circle cx="{fx:.1f}" cy="{fy:.1f}" r="8" fill="#f43f5e" stroke="#ffffff" stroke-width="2" filter="url(#glow-rose)" />
      <circle cx="{fx:.1f}" cy="{fy:.1f}" r="16" fill="none" stroke="#f43f5e" stroke-width="1.5" stroke-dasharray="2,2" />
      <text x="{fx + 14:.1f}" y="{fy + 4:.1f}" fill="#fb7185" font-size="11" font-weight="bold">Founder (desc)</text>
      <title>Founder Agent Descriptor (Projected)&#10;Desc: [{', '.join(f'{v:.2f}' for v in desc)}]</title>
    </g>
    """

    mesh_svg_str = "\n".join(mesh_lines)
    nodes_svg_str = "\n".join(nodes_svg)
    table_rows_str = "\n".join(table_rows)

    return f"""
    <div class="card">
      <div class="card-header">
        <div class="card-title-group">
          <h2>View 1: 5D CVTArchive Voronoi Niche Map</h2>
          <span class="card-subtitle">Centroidal Voronoi Tessellation MAP-Elites Behavioral Space (Vassiliades et al., 2018)</span>
        </div>
        <div class="badge-cluster">
          <span class="badge info">Niches: {total_niches}</span>
          <span class="badge success">Occupied: {cov}</span>
          <span class="badge warning">Vacant: {total_niches - cov}</span>
        </div>
      </div>

      <div class="card-body">
        <div class="viz-row">
          <div class="svg-container">
            <svg viewBox="0 0 {svg_w} {svg_h}" class="dashboard-svg" aria-label="Voronoi Niche Map Chart">
              <defs>
                <filter id="glow-green" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
                <filter id="glow-rose" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              <!-- Grid & axes background -->
              <rect x="{pad_l}" y="{pad_t}" width="{plot_w}" height="{plot_h}" fill="#0f172a" stroke="#1e293b" rx="6" />

              <!-- Axis grid lines -->
              <line x1="{pad_l + plot_w * 0.25:.1f}" y1="{pad_t}" x2="{pad_l + plot_w * 0.25:.1f}" y2="{pad_t + plot_h}" stroke="#1e293b" stroke-width="1" />
              <line x1="{pad_l + plot_w * 0.50:.1f}" y1="{pad_t}" x2="{pad_l + plot_w * 0.50:.1f}" y2="{pad_t + plot_h}" stroke="#334155" stroke-width="1" stroke-dasharray="4,4" />
              <line x1="{pad_l + plot_w * 0.75:.1f}" y1="{pad_t}" x2="{pad_l + plot_w * 0.75:.1f}" y2="{pad_t + plot_h}" stroke="#1e293b" stroke-width="1" />

              <line x1="{pad_l}" y1="{pad_t + plot_h * 0.25:.1f}" x2="{pad_l + plot_w}" y2="{pad_t + plot_h * 0.25:.1f}" stroke="#1e293b" stroke-width="1" />
              <line x1="{pad_l}" y1="{pad_t + plot_h * 0.50:.1f}" x2="{pad_l + plot_w}" y2="{pad_t + plot_h * 0.50:.1f}" stroke="#334155" stroke-width="1" stroke-dasharray="4,4" />
              <line x1="{pad_l}" y1="{pad_t + plot_h * 0.75:.1f}" x2="{pad_l + plot_w}" y2="{pad_t + plot_h * 0.75:.1f}" stroke="#1e293b" stroke-width="1" />

              <!-- Axis Labels -->
              <text x="{pad_l + plot_w / 2:.1f}" y="{svg_h - 15}" fill="#94a3b8" font-size="12" text-anchor="middle">Dimension 0: Greed &amp; Risk Bias &rarr;</text>
              <text x="20" y="{pad_t + plot_h / 2:.1f}" fill="#94a3b8" font-size="12" text-anchor="middle" transform="rotate(-90, 20, {pad_t + plot_h / 2:.1f})">&larr; Dimension 1: Status &amp; Pride Momentum</text>

              <!-- Tessellation Mesh -->
              {mesh_svg_str}

              <!-- Niche Nodes -->
              {nodes_svg_str}

              <!-- Founder Descriptor -->
              {founder_marker}
            </svg>
          </div>

          <div class="legend-panel">
            <h3>Niche Legend &amp; Projection</h3>
            <p class="legend-desc">Fixed Voronoi centroids partition high-dimensional behavior space to prevent premature multi-agent diversity collapse.</p>
            <div class="legend-items">
              <div class="legend-item">
                <span class="legend-swatch occupied-swatch"></span>
                <span><strong>Occupied Niche</strong>: Elite agent stored with fitness</span>
              </div>
              <div class="legend-item">
                <span class="legend-swatch vacant-swatch"></span>
                <span><strong>Vacant Niche</strong>: Centroid awaiting phenotypic discovery</span>
              </div>
              <div class="legend-item">
                <span class="legend-swatch founder-swatch"></span>
                <span><strong>Founder Agent</strong>: Projected behavioral descriptor</span>
              </div>
            </div>

            <div class="table-scroll-mini">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Niche</th>
                    <th>Status</th>
                    <th>Elite Agent</th>
                    <th>Fitness</th>
                    <th>5D Coordinates</th>
                  </tr>
                </thead>
                <tbody>
                  {table_rows_str}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
    """


def _render_view2_lineage_tree(world: WorldState) -> str:
    """Render View 2: Agent Lineage Family Tree."""
    agents = world.agents
    if not agents:
        return """
        <div class="card">
          <div class="card-header"><h2>View 2: Agent Lineage Family Tree</h2></div>
          <div class="card-body"><p class="empty-state">No agents registered in world state.</p></div>
        </div>
        """

    # Group agents by generation
    gens_sorted = sorted(set(a.generation for a in agents.values()))
    lineages = sorted(set(a.lineage_id for a in agents.values()))

    # Build parent -> children map
    children_map: dict[str, list[str]] = {}
    for a in agents.values():
        for p in a.parents:
            children_map.setdefault(p, []).append(a.agent_id)

    # Render generation tiers
    gen_tiers_html: list[str] = []
    for g in gens_sorted:
        gen_agents = [a for a in agents.values() if a.generation == g]
        cards_html: list[str] = []

        for a in gen_agents:
            alive_pill = (
                '<span class="pill pill-success">ALIVE</span>'
                if a.alive
                else '<span class="pill pill-danger">DECEASED</span>'
            )
            parents_str = ", ".join(html.escape(p) for p in a.parents) if a.parents else "None (Founder)"
            norms_html = (
                "".join(f'<span class="norm-tag">{html.escape(n)}</span>' for n in a.adopted_norms)
                if a.adopted_norms
                else '<span class="text-muted">None</span>'
            )
            institutions_html = (
                "".join(f'<span class="inst-tag">{html.escape(i)}</span>' for i in a.institution_ids)
                if a.institution_ids
                else '<span class="text-muted">None</span>'
            )
            offspring_count = len(children_map.get(a.agent_id, []))

            cards_html.append(f"""
            <div class="agent-tree-node {'is-alive' if a.alive else 'is-dead'}">
              <div class="node-header">
                <span class="agent-id"><code>{html.escape(a.agent_id)}</code></span>
                <span class="badge gen-badge">Gen {a.generation}</span>
                {alive_pill}
              </div>
              <div class="node-body">
                <div class="node-row"><span class="k">Role:</span> <span class="v role-badge">{html.escape(a.role)}</span></div>
                <div class="node-row"><span class="k">Lineage:</span> <span class="v"><code>{html.escape(a.lineage_id)}</code></span></div>
                <div class="node-row"><span class="k">Parents:</span> <span class="v">{parents_str}</span></div>
                <div class="node-row"><span class="k">Location:</span> <span class="v"><code>{html.escape(a.location_id)}</code></span></div>
                <div class="node-row"><span class="k">Offspring:</span> <span class="v font-bold">{offspring_count} descendants</span></div>
                <div class="node-row"><span class="k">Wealth:</span> <span class="v highlight-amber">{a.currency} &cent;</span></div>
                <div class="node-row"><span class="k">Energy:</span>
                  <div class="meter-bar">
                    <div class="meter-fill" style="width: {a.energy * 100:.0f}%;"></div>
                  </div>
                </div>
                <div class="node-row-block">
                  <span class="k">Adopted Norms:</span>
                  <div class="tag-row">{norms_html}</div>
                </div>
                <div class="node-row-block">
                  <span class="k">Institutions:</span>
                  <div class="tag-row">{institutions_html}</div>
                </div>
              </div>
            </div>
            """)

        cards_str = "\n".join(cards_html)
        gen_tiers_html.append(f"""
        <div class="generation-tier">
          <div class="tier-label">
            <span class="gen-title">Generation {g}</span>
            <span class="gen-count">{len(gen_agents)} agents</span>
          </div>
          <div class="agent-nodes-grid">
            {cards_str}
          </div>
        </div>
        """)

    tiers_str = "\n".join(gen_tiers_html)

    return f"""
    <div class="card">
      <div class="card-header">
        <div class="card-title-group">
          <h2>View 2: Agent Lineage Family Tree</h2>
          <span class="card-subtitle">Multi-Generation Genealogical Lineage &amp; Cultural Norm Transmission</span>
        </div>
        <div class="badge-cluster">
          <span class="badge info">Generations: {len(gens_sorted)}</span>
          <span class="badge purple">Lineages: {len(lineages)}</span>
          <span class="badge success">Total Agents: {len(agents)}</span>
        </div>
      </div>

      <div class="card-body">
        <div class="lineage-tree-wrapper">
          {tiers_str}
        </div>
      </div>
    </div>
    """


def _render_view3_spatial_heatmap(world: WorldState) -> str:
    """Render View 3: Spatial Resource & Agent Heatmap."""
    locations = world.locations
    agents = world.agents
    if not locations:
        return """
        <div class="card">
          <div class="card-header"><h2>View 3: Spatial Resource &amp; Agent Heatmap</h2></div>
          <div class="card-body"><p class="empty-state">No locations configured in world state.</p></div>
        </div>
        """

    # Group agents by location
    agents_at_loc: dict[str, list[WorldAgentState]] = {}
    for a in agents.values():
        agents_at_loc.setdefault(a.location_id, []).append(a)

    loc_cards: list[str] = []
    for loc_id, loc in sorted(locations.items()):
        loc_agents = agents_at_loc.get(loc_id, [])
        agent_count = len(loc_agents)

        # Standard resources
        food_cur = loc.resources.get("food", 0)
        food_cap = max(1, loc.capacities.get("food", 100))
        food_pct = min(100.0, (food_cur / food_cap) * 100.0)

        wood_cur = loc.resources.get("wood", 0)
        wood_cap = max(1, loc.capacities.get("wood", 50))
        wood_pct = min(100.0, (wood_cur / wood_cap) * 100.0)

        stone_cur = loc.resources.get("stone", 0)
        stone_cap = max(1, loc.capacities.get("stone", 50))
        stone_pct = min(100.0, (stone_cur / stone_cap) * 100.0)

        # Agent badges
        if loc_agents:
            agent_badges = "".join(
                f'<span class="agent-chip"><code>{html.escape(a.agent_id)}</code> ({html.escape(a.role)})</span>'
                for a in loc_agents
            )
        else:
            agent_badges = '<span class="text-muted">No agents currently present</span>'

        neighbors_str = ", ".join(f"<code>{html.escape(n)}</code>" for n in loc.neighbors) if loc.neighbors else "Isolated"

        loc_cards.append(f"""
        <div class="location-card">
          <div class="loc-card-header">
            <div>
              <span class="loc-id"><code>{html.escape(loc.location_id)}</code></span>
              <h3 class="loc-name">{html.escape(loc.name)}</h3>
            </div>
            <span class="badge {'success' if agent_count > 0 else 'muted'}">
              {agent_count} { "Agent" if agent_count == 1 else "Agents" }
            </span>
          </div>

          <div class="loc-body">
            <div class="resource-bars">
              <div class="res-row">
                <div class="res-meta">
                  <span class="res-name color-food">&bull; Food</span>
                  <span class="res-vals">{food_cur} / {food_cap}</span>
                </div>
                <div class="res-track">
                  <div class="res-fill bar-food" style="width: {food_pct:.1f}%;"></div>
                </div>
              </div>

              <div class="res-row">
                <div class="res-meta">
                  <span class="res-name color-wood">&bull; Wood</span>
                  <span class="res-vals">{wood_cur} / {wood_cap}</span>
                </div>
                <div class="res-track">
                  <div class="res-fill bar-wood" style="width: {wood_pct:.1f}%;"></div>
                </div>
              </div>

              <div class="res-row">
                <div class="res-meta">
                  <span class="res-name color-stone">&bull; Stone</span>
                  <span class="res-vals">{stone_cur} / {stone_cap}</span>
                </div>
                <div class="res-track">
                  <div class="res-fill bar-stone" style="width: {stone_pct:.1f}%;"></div>
                </div>
              </div>
            </div>

            <div class="loc-meta-grid">
              <div><span class="k">Shock Factor:</span> <span class="v">{loc.shock_factor:.2f}x</span></div>
              <div><span class="k">Neighbors:</span> <span class="v">{neighbors_str}</span></div>
            </div>

            <div class="loc-agents-section">
              <span class="k">Present Agents:</span>
              <div class="agent-chip-list">{agent_badges}</div>
            </div>
          </div>
        </div>
        """)

    loc_cards_str = "\n".join(loc_cards)

    return f"""
    <div class="card">
      <div class="card-header">
        <div class="card-title-group">
          <h2>View 3: Spatial Resource &amp; Agent Heatmap</h2>
          <span class="card-subtitle">Persistent Environmental Discrete Location Graph, Resource Stocks &amp; Population Density</span>
        </div>
        <div class="badge-cluster">
          <span class="badge info">Locations: {len(locations)}</span>
          <span class="badge success">Active Nodes: {sum(1 for loc_node in locations.values() if loc_node.location_id in agents_at_loc)}</span>
        </div>
      </div>

      <div class="card-body">
        <div class="locations-grid">
          {loc_cards_str}
        </div>
      </div>
    </div>
    """


def _render_view4_lorenz_gini(world: WorldState, gini: float) -> str:
    """Render View 4: Macroeconomic Lorenz & Gini Visualizer."""
    wealths = sorted([float(a.currency) for a in world.agents.values()])
    n = len(wealths)
    total_wealth = sum(wealths)

    # Compute Lorenz points
    lorenz_pts: list[tuple[float, float]] = [(0.0, 0.0)]
    if n > 0 and total_wealth > 0:
        cum = 0.0
        for i, w in enumerate(wealths, start=1):
            cum += w
            lorenz_pts.append((i / n, cum / total_wealth))
    else:
        lorenz_pts.append((1.0, 1.0))

    # SVG geometry
    svg_w, svg_h = 640, 460
    pad_l, pad_r, pad_t, pad_b = 70, 40, 40, 60
    plot_w = svg_w - pad_l - pad_r
    plot_h = svg_h - pad_t - pad_b

    def to_xy(p: float, l_val: float) -> tuple[float, float]:
        x = pad_l + p * plot_w
        y = (pad_t + plot_h) - l_val * plot_h
        return x, y

    # Lorenz path
    path_cmds = [f"M {to_xy(lorenz_pts[0][0], lorenz_pts[0][1])[0]:.1f} {to_xy(lorenz_pts[0][0], lorenz_pts[0][1])[1]:.1f}"]
    for p, l_val in lorenz_pts[1:]:
        x, y = to_xy(p, l_val)
        path_cmds.append(f"L {x:.1f} {y:.1f}")
    lorenz_path_d = " ".join(path_cmds)

    # Shaded inequality polygon (between diagonal and Lorenz curve)
    diag_start_x, diag_start_y = to_xy(0.0, 0.0)
    diag_end_x, diag_end_y = to_xy(1.0, 1.0)
    area_polygon_d = f"{lorenz_path_d} L {diag_end_x:.1f} {diag_end_y:.1f} L {diag_start_x:.1f} {diag_start_y:.1f} Z"

    # Data point circles
    pts_svg: list[str] = []
    for idx, (p, l_val) in enumerate(lorenz_pts):
        x, y = to_xy(p, l_val)
        w_val = wealths[idx - 1] if 0 < idx <= len(wealths) else 0.0
        pts_svg.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#38bdf8" stroke="#0f172a" stroke-width="2">'
            f'<title>Percentile: {p*100:.1f}%&#10;Cumulative Wealth: {l_val*100:.1f}%&#10;Agent Wealth: {w_val:.0f} ¢</title>'
            f'</circle>'
        )
    pts_svg_str = "\n".join(pts_svg)

    # Economic metrics
    mean_wealth = total_wealth / max(1, n)
    median_wealth = wealths[n // 2] if n > 0 else 0.0
    gini_rating = (
        "Low (Egalitarian)" if gini < 0.25
        else "Moderate (Balanced)" if gini < 0.45
        else "High (Plutocratic)"
    )

    # Agent wealth table rows
    agent_wealth_rows: list[str] = []
    sorted_agents = sorted(world.agents.values(), key=lambda a: a.currency, reverse=True)
    for rank, a in enumerate(sorted_agents, start=1):
        share_pct = (a.currency / max(1.0, total_wealth)) * 100.0
        agent_wealth_rows.append(f"""
        <tr>
          <td>#{rank}</td>
          <td><code>{html.escape(a.agent_id)}</code></td>
          <td><span class="badge gen-badge">Gen {a.generation}</span></td>
          <td>{html.escape(a.role)}</td>
          <td class="num-cell font-bold">{a.currency} &cent;</td>
          <td class="num-cell">{share_pct:.1f}%</td>
        </tr>
        """)
    agent_wealth_rows_str = "\n".join(agent_wealth_rows)

    return f"""
    <div class="card">
      <div class="card-header">
        <div class="card-title-group">
          <h2>View 4: Macroeconomic Lorenz &amp; Gini Visualizer</h2>
          <span class="card-subtitle">Wealth Concentration, Lorenz Curve &amp; Endogenous Inequality Tracking</span>
        </div>
        <div class="badge-cluster">
          <span class="badge rose">Gini: {gini:.4f}</span>
          <span class="badge warning">Total Wealth: {int(total_wealth)} &cent;</span>
          <span class="badge info">Population: {n}</span>
        </div>
      </div>

      <div class="card-body">
        <div class="viz-row">
          <div class="svg-container">
            <svg viewBox="0 0 {svg_w} {svg_h}" class="dashboard-svg" aria-label="Lorenz Curve Chart">
              <!-- Plot background -->
              <rect x="{pad_l}" y="{pad_t}" width="{plot_w}" height="{plot_h}" fill="#0f172a" stroke="#1e293b" rx="6" />

              <!-- Grid lines -->
              <line x1="{pad_l + plot_w * 0.2:.1f}" y1="{pad_t}" x2="{pad_l + plot_w * 0.2:.1f}" y2="{pad_t + plot_h}" stroke="#1e293b" stroke-width="1" />
              <line x1="{pad_l + plot_w * 0.4:.1f}" y1="{pad_t}" x2="{pad_l + plot_w * 0.4:.1f}" y2="{pad_t + plot_h}" stroke="#1e293b" stroke-width="1" />
              <line x1="{pad_l + plot_w * 0.6:.1f}" y1="{pad_t}" x2="{pad_l + plot_w * 0.6:.1f}" y2="{pad_t + plot_h}" stroke="#1e293b" stroke-width="1" />
              <line x1="{pad_l + plot_w * 0.8:.1f}" y1="{pad_t}" x2="{pad_l + plot_w * 0.8:.1f}" y2="{pad_t + plot_h}" stroke="#1e293b" stroke-width="1" />

              <line x1="{pad_l}" y1="{pad_t + plot_h * 0.2:.1f}" x2="{pad_l + plot_w}" y2="{pad_t + plot_h * 0.2:.1f}" stroke="#1e293b" stroke-width="1" />
              <line x1="{pad_l}" y1="{pad_t + plot_h * 0.4:.1f}" x2="{pad_l + plot_w}" y2="{pad_t + plot_h * 0.4:.1f}" stroke="#1e293b" stroke-width="1" />
              <line x1="{pad_l}" y1="{pad_t + plot_h * 0.6:.1f}" x2="{pad_l + plot_w}" y2="{pad_t + plot_h * 0.6:.1f}" stroke="#1e293b" stroke-width="1" />
              <line x1="{pad_l}" y1="{pad_t + plot_h * 0.8:.1f}" x2="{pad_l + plot_w}" y2="{pad_t + plot_h * 0.8:.1f}" stroke="#1e293b" stroke-width="1" />

              <!-- Inequality Area Shading -->
              <path d="{area_polygon_d}" fill="rgba(244,63,94,0.18)" />

              <!-- Line of Perfect Equality -->
              <line x1="{diag_start_x:.1f}" y1="{diag_start_y:.1f}" x2="{diag_end_x:.1f}" y2="{diag_end_y:.1f}" stroke="#64748b" stroke-width="2" stroke-dasharray="6,4" />

              <!-- Empirical Lorenz Curve -->
              <path d="{lorenz_path_d}" stroke="#38bdf8" stroke-width="3.5" fill="none" stroke-linecap="round" />

              <!-- Data Points -->
              {pts_svg_str}

              <!-- Axis labels -->
              <text x="{pad_l + plot_w / 2:.1f}" y="{svg_h - 15}" fill="#94a3b8" font-size="12" text-anchor="middle">Cumulative Population Share (0% &rarr; 100%)</text>
              <text x="25" y="{pad_t + plot_h / 2:.1f}" fill="#94a3b8" font-size="12" text-anchor="middle" transform="rotate(-90, 25, {pad_t + plot_h / 2:.1f})">Cumulative Wealth Share (0% &rarr; 100%)</text>
            </svg>
          </div>

          <div class="legend-panel">
            <h3>Economic Inequality Diagnostics</h3>
            <div class="kpi-micro-grid">
              <div class="kpi-mini">
                <span class="lbl">Gini Coefficient</span>
                <span class="val highlight-rose">{gini:.4f}</span>
                <span class="sub">{gini_rating}</span>
              </div>
              <div class="kpi-mini">
                <span class="lbl">Total Currency</span>
                <span class="val highlight-amber">{int(total_wealth)} &cent;</span>
                <span class="sub">Active liquidity</span>
              </div>
              <div class="kpi-mini">
                <span class="lbl">Mean Wealth</span>
                <span class="val highlight-cyan">{mean_wealth:.1f} &cent;</span>
                <span class="sub">Per capita</span>
              </div>
              <div class="kpi-mini">
                <span class="lbl">Median Wealth</span>
                <span class="val highlight-emerald">{median_wealth:.1f} &cent;</span>
                <span class="sub">50th percentile</span>
              </div>
            </div>

            <div class="table-scroll-mini">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Agent</th>
                    <th>Gen</th>
                    <th>Role</th>
                    <th>Wealth</th>
                    <th>Share</th>
                  </tr>
                </thead>
                <tbody>
                  {agent_wealth_rows_str}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
    """


def _render_styles() -> str:
    """Return dark-mode responsive CSS styles for the dashboard."""
    return """
    :root {
      --bg-base: #090d16;
      --bg-card: #111827;
      --bg-card-sub: #1e293b;
      --border: #1f293d;
      --border-highlight: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-sub: #64748b;
      --cyan: #38bdf8;
      --emerald: #10b981;
      --amber: #f59e0b;
      --rose: #f43f5e;
      --purple: #a855f7;
      --indigo: #6366f1;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg-base);
      color: var(--text-main);
      line-height: 1.5;
      padding: 24px;
    }

    .dashboard-container {
      max-width: 1400px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    /* Header & KPIs */
    .dashboard-header {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    .brand-badge {
      display: inline-block;
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.1em;
      background: rgba(56, 189, 248, 0.15);
      color: var(--cyan);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 3px 8px;
      border-radius: 4px;
      margin-bottom: 6px;
    }
    .header-titles h1 {
      font-size: 26px;
      font-weight: 700;
      color: var(--text-main);
    }
    .header-titles .subtitle {
      color: var(--text-muted);
      font-size: 14px;
    }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
    }
    .kpi-card {
      background: var(--bg-card-sub);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .kpi-label { font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.05em; }
    .kpi-value { font-size: 22px; font-weight: 700; color: var(--text-main); }
    .kpi-sub { font-size: 11px; color: var(--text-sub); }
    .small-code { font-size: 13px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; word-break: break-all; }

    .highlight-cyan { color: var(--cyan); }
    .highlight-emerald { color: var(--emerald); }
    .highlight-amber { color: var(--amber); }
    .highlight-rose { color: var(--rose); }
    .highlight-purple { color: var(--purple); }
    .highlight-indigo { color: var(--indigo); }

    /* Navigation Tabs */
    .view-tabs {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 8px;
    }
    .tab-btn {
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 13px;
      font-weight: 600;
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .tab-btn:hover { background: var(--bg-card-sub); color: var(--text-main); }
    .tab-btn.active {
      background: var(--indigo);
      color: #ffffff;
      box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4);
    }

    /* Cards */
    .views-wrapper { display: flex; flex-direction: column; gap: 24px; }
    .dashboard-section { display: block; }
    .card {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
    }
    .card-header {
      padding: 18px 24px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    .card-title-group h2 { font-size: 18px; font-weight: 700; }
    .card-subtitle { font-size: 12px; color: var(--text-muted); display: block; margin-top: 2px; }
    .card-body { padding: 24px; }

    /* Badges & Pills */
    .badge-cluster { display: flex; gap: 8px; align-items: center; }
    .badge {
      font-size: 12px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 9999px;
      display: inline-flex;
      align-items: center;
    }
    .badge.info { background: rgba(56, 189, 248, 0.15); color: var(--cyan); border: 1px solid rgba(56, 189, 248, 0.3); }
    .badge.success { background: rgba(16, 185, 129, 0.15); color: var(--emerald); border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge.warning { background: rgba(245, 158, 11, 0.15); color: var(--amber); border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge.rose { background: rgba(244, 63, 94, 0.15); color: var(--rose); border: 1px solid rgba(244, 63, 94, 0.3); }
    .badge.purple { background: rgba(168, 85, 247, 0.15); color: var(--purple); border: 1px solid rgba(168, 85, 247, 0.3); }
    .badge.muted { background: var(--bg-card-sub); color: var(--text-sub); border: 1px solid var(--border); }
    .gen-badge { background: rgba(99, 102, 241, 0.2); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.4); }

    .pill {
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 2px 7px;
      border-radius: 4px;
    }
    .pill-success { background: rgba(16, 185, 129, 0.2); color: var(--emerald); }
    .pill-danger { background: rgba(244, 63, 94, 0.2); color: var(--rose); }
    .pill-muted { background: var(--bg-card-sub); color: var(--text-sub); }

    /* Visualizer Rows */
    .viz-row {
      display: grid;
      grid-template-columns: minmax(360px, 1.2fr) minmax(280px, 0.8fr);
      gap: 24px;
      align-items: start;
    }
    @media (max-width: 900px) {
      .viz-row { grid-template-columns: 1fr; }
    }
    .svg-container {
      background: var(--bg-base);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
    }
    .dashboard-svg {
      width: 100%;
      height: auto;
      display: block;
    }

    /* Voronoi / Legend */
    .legend-panel {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .legend-panel h3 { font-size: 15px; font-weight: 600; color: var(--text-main); }
    .legend-desc { font-size: 12px; color: var(--text-muted); line-height: 1.4; }
    .legend-items { display: flex; flex-direction: column; gap: 8px; font-size: 12px; }
    .legend-item { display: flex; align-items: center; gap: 8px; }
    .legend-swatch { width: 14px; height: 14px; border-radius: 4px; display: inline-block; }
    .occupied-swatch { background: var(--emerald); border: 1px solid #34d399; }
    .vacant-swatch { background: var(--bg-card-sub); border: 1px dashed var(--text-sub); }
    .founder-swatch { background: var(--rose); border: 1px solid #ffffff; }

    /* Tables */
    .table-scroll-mini {
      max-height: 240px;
      overflow-y: auto;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: var(--bg-card-sub);
    }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      text-align: left;
    }
    .data-table th {
      position: sticky;
      top: 0;
      background: #1e293b;
      padding: 8px 10px;
      color: var(--text-muted);
      font-weight: 600;
      border-bottom: 1px solid var(--border);
    }
    .data-table td {
      padding: 7px 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      color: var(--text-main);
    }
    .data-table tr:hover td { background: rgba(255, 255, 255, 0.03); }
    .num-cell { text-align: right; }
    .code-cell { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px; color: var(--text-muted); }

    /* View 2 Lineage Tree */
    .lineage-tree-wrapper { display: flex; flex-direction: column; gap: 24px; }
    .generation-tier {
      background: var(--bg-base);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .tier-label { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
    .gen-title { font-size: 14px; font-weight: 700; color: #a5b4fc; }
    .gen-count { font-size: 12px; color: var(--text-sub); }
    .agent-nodes-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
    }
    .agent-tree-node {
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      transition: border-color 0.15s ease;
    }
    .agent-tree-node:hover { border-color: var(--indigo); }
    .agent-tree-node.is-dead { opacity: 0.7; }
    .node-header { display: flex; justify-content: space-between; align-items: center; }
    .agent-id { font-size: 14px; font-weight: 700; }
    .node-body { display: flex; flex-direction: column; gap: 6px; font-size: 12px; }
    .node-row { display: flex; justify-content: space-between; align-items: center; }
    .node-row-block { display: flex; flex-direction: column; gap: 4px; margin-top: 2px; }
    .node-body .k { color: var(--text-muted); }
    .role-badge { background: var(--bg-card-sub); padding: 2px 6px; border-radius: 4px; font-weight: 600; color: var(--cyan); }
    .meter-bar { width: 100px; height: 6px; background: var(--bg-card-sub); border-radius: 3px; overflow: hidden; }
    .meter-fill { height: 100%; background: var(--emerald); }
    .tag-row { display: flex; gap: 4px; flex-wrap: wrap; }
    .norm-tag { font-size: 10px; background: rgba(245, 158, 11, 0.15); color: var(--amber); border: 1px solid rgba(245, 158, 11, 0.3); padding: 1px 6px; border-radius: 4px; }
    .inst-tag { font-size: 10px; background: rgba(168, 85, 247, 0.15); color: var(--purple); border: 1px solid rgba(168, 85, 247, 0.3); padding: 1px 6px; border-radius: 4px; }

    /* View 3 Spatial Heatmap */
    .locations-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 16px;
    }
    .location-card {
      background: var(--bg-base);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .loc-card-header { display: flex; justify-content: space-between; align-items: flex-start; }
    .loc-id { font-size: 11px; color: var(--text-sub); }
    .loc-name { font-size: 15px; font-weight: 700; color: var(--text-main); }
    .resource-bars { display: flex; flex-direction: column; gap: 8px; }
    .res-row { display: flex; flex-direction: column; gap: 3px; }
    .res-meta { display: flex; justify-content: space-between; font-size: 11px; }
    .color-food { color: var(--emerald); font-weight: 600; }
    .color-wood { color: var(--amber); font-weight: 600; }
    .color-stone { color: var(--cyan); font-weight: 600; }
    .res-track { width: 100%; height: 6px; background: var(--bg-card); border-radius: 3px; overflow: hidden; }
    .res-fill { height: 100%; border-radius: 3px; }
    .bar-food { background: var(--emerald); }
    .bar-wood { background: var(--amber); }
    .bar-stone { background: var(--cyan); }
    .loc-meta-grid { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); border-top: 1px solid var(--border); padding-top: 8px; }
    .loc-agents-section { border-top: 1px solid var(--border); padding-top: 8px; font-size: 11px; display: flex; flex-direction: column; gap: 4px; }
    .agent-chip-list { display: flex; gap: 4px; flex-wrap: wrap; }
    .agent-chip { font-size: 10px; background: var(--bg-card-sub); border: 1px solid var(--border-highlight); padding: 2px 6px; border-radius: 4px; }

    /* View 4 Mini KPIs */
    .kpi-micro-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .kpi-mini { background: var(--bg-card-sub); border: 1px solid var(--border); border-radius: 6px; padding: 10px; display: flex; flex-direction: column; gap: 2px; }
    .kpi-mini .lbl { font-size: 10px; text-transform: uppercase; color: var(--text-muted); }
    .kpi-mini .val { font-size: 18px; font-weight: 700; }
    .kpi-mini .sub { font-size: 10px; color: var(--text-sub); }

    /* Footer */
    .dashboard-footer {
      text-align: center;
      padding: 16px;
      font-size: 12px;
      color: var(--text-sub);
      border-top: 1px solid var(--border);
    }
    """


def _render_scripts() -> str:
    """Return inline Vanilla JS for interactive tab switching with zero external dependencies."""
    return """
    function switchTab(tabId) {
      const tabs = document.querySelectorAll('.tab-btn');
      tabs.forEach(btn => {
        if (btn.getAttribute('data-tab') === tabId) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });

      const sections = document.querySelectorAll('.dashboard-section');
      sections.forEach(sec => {
        if (tabId === 'all' || sec.id === tabId) {
          sec.style.display = 'block';
        } else {
          sec.style.display = 'none';
        }
      });
    }
    """
