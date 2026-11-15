"""Phase 1.1 / Phase 1.5 — Live real-time dashboard and transition streaming server.

Provides a standard-library based HTTP and Server-Sent Events (SSE) server for EvolZen:
- `GET /`: Interactive, reactive dark-themed single-page HTML5/SVG application that connects
  to `/api/events` via browser `EventSource`. Displays live world ticks, active agent count,
  wealth Gini meter, 5D CVTArchive niche map, and real-time transition event log.
- `GET /api/status`: JSON summary of current database state (total transitions, latest tick,
  alive agents count, Gini index, archive niche count).
- `GET /api/events`: Server-Sent Events stream (`text/event-stream`) streaming new transition
  records from `TransitionLogStore(db_path)` with monotonically increasing sequence IDs.

Zero external network or third-party web dependencies (pure Python standard library
`http.server.ThreadingHTTPServer` and `http.server.BaseHTTPRequestHandler`).

Citations:
- Vassiliades et al., IEEE TEVC 2018 (CVT MAP-Elites).
- Tycho (arXiv:2607.28287) for transition sequence logging and event streaming.
- W3C Server-Sent Events (WHATWG EventSource standard).
"""
from __future__ import annotations

import json
import threading
import urllib.parse
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from evolzen.agents.development.motivation import sample_genome
from evolzen.agents.qd_archive import CVTArchive, QDArchiveEntry, compute_behavioral_descriptor
from evolzen.economy.metrics import compute_gini_coefficient
from evolzen.logging import logger
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.transition import State
from evolzen.schemas.world import WorldState
from evolzen.storage.transition_log import TransitionLogStore


class ThreadedHTTPServer(ThreadingHTTPServer):
    """Threaded HTTP server with immediate socket reuse and daemon worker threads."""

    daemon_threads = True
    allow_reuse_address = True
    dashboard_server: EvolZenDashboardServer


class EvolZenRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler dispatching `/`, `/api/status`, and `/api/events`."""

    server: ThreadedHTTPServer

    @property
    def dashboard_server(self) -> EvolZenDashboardServer:
        """Reference to parent EvolZenDashboardServer."""
        return self.server.dashboard_server

    def log_message(self, format: str, *args: Any) -> None:
        """Route standard HTTP server logs through loguru at DEBUG level."""
        logger.debug("EvolZen HTTP: " + (format % args))

    def do_GET(self) -> None:
        """Handle incoming GET requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "/index.html"):
            self._handle_root()
        elif path == "/api/status":
            self._handle_api_status()
        elif path == "/api/events":
            self._handle_api_events(query)
        else:
            self.send_response(HTTPStatus.NOT_FOUND)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"404 Not Found")

    def _handle_root(self) -> None:
        """Serve the interactive reactive single-page HTML5/SVG dashboard."""
        html_content = generate_live_dashboard_html()
        body = html_content.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _handle_api_status(self) -> None:
        """Serve the JSON database status summary."""
        status = self.dashboard_server.get_status()
        payload = json.dumps(status, indent=2).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(payload)

    def _handle_api_events(self, query: dict[str, list[str]]) -> None:
        """Stream real-time transition records via Server-Sent Events."""
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        self.dashboard_server.stream_sse(self, query)


class EvolZenDashboardServer:
    """Live streaming dashboard HTTP and Server-Sent Events server."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        db_path: Path = Path("data/transitions.duckdb"),
        poll_interval: float = 1.0,
    ) -> None:
        self.host = host
        self.port = port
        self.db_path = Path(db_path)
        self.poll_interval = max(0.05, float(poll_interval))

        self._httpd: ThreadedHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._stopping = threading.Event()
        self._lock = threading.Lock()
        self._actual_port: int = port
        self._store: TransitionLogStore | None = None
        self._cached_status: dict[str, Any] | None = None
        self._cached_seq: int = -1

    @property
    def server_port(self) -> int:
        """The actual bound port of the server (useful when ephemeral port 0 is used)."""
        return self._actual_port

    def _get_or_create_store(self) -> TransitionLogStore:
        """Get or lazily instantiate the TransitionLogStore under lock."""
        if self._store is None:
            self._store = TransitionLogStore(self.db_path)
        return self._store

    def get_status(self) -> dict[str, Any]:
        """Compute the JSON database status summary.

        Returns:
            Dictionary containing `total_transitions`, `latest_tick`, `alive_agents_count`,
            `gini_index`, `archive_niche_count`, and centroid niche details.
        """
        with self._lock:
            store = self._get_or_create_store()
            total_transitions = store.count()
            latest_seq = store.latest_seq_no()

            if self._cached_status is not None and latest_seq == self._cached_seq:
                return dict(self._cached_status)

            if total_transitions == 0:
                empty_status: dict[str, Any] = {
                    "status": "ok",
                    "total_transitions": 0,
                    "latest_tick": 0,
                    "alive_agents_count": 0,
                    "gini_index": 0.0,
                    "archive_niche_count": 0,
                    "archive_total_niches": 10,
                    "db_path": str(self.db_path),
                    "timestamp": datetime.now(UTC).isoformat(),
                    "niches": [],
                }
                self._cached_status = empty_status
                self._cached_seq = 0
                return empty_status

            row = store._conn.execute(
                "SELECT tick, next_state_json FROM transitions ORDER BY seq_no DESC LIMIT 1"
            ).fetchone()

            latest_tick = int(row[0]) if row and row[0] is not None else 0
            raw_state_json = str(row[1]) if row and row[1] is not None else "{}"

            try:
                state = State.model_validate_json(raw_state_json)
                world = WorldState.from_state(state)
            except Exception as e:
                logger.warning("Could not parse WorldState from latest transition: {}", e)
                fallback_status: dict[str, Any] = {
                    "status": "partial",
                    "total_transitions": total_transitions,
                    "latest_tick": latest_tick,
                    "alive_agents_count": 0,
                    "gini_index": 0.0,
                    "archive_niche_count": 0,
                    "archive_total_niches": 10,
                    "db_path": str(self.db_path),
                    "timestamp": datetime.now(UTC).isoformat(),
                    "niches": [],
                }
                self._cached_status = fallback_status
                self._cached_seq = latest_seq
                return fallback_status

            living_agents = [a for a in world.agents.values() if a.alive]
            alive_count = len(living_agents)
            wealths = [float(a.currency + sum(a.inventory.values())) for a in living_agents]
            gini = compute_gini_coefficient(wealths) if wealths else 0.0

            archive = CVTArchive.uniform_hypercube(num_centroids=10, dimensions=5, seed=world.seed)
            for a in world.agents.values():
                a_profile = AgentProfile(
                    agent_id=a.agent_id,
                    lineage_id=a.lineage_id,
                    adopted_norms=tuple(a.adopted_norms),
                    institutional_affiliations=tuple(a.institution_ids),
                )
                a_genome = sample_genome(world.seed + (hash(a.agent_id) % 1000))
                a_desc = compute_behavioral_descriptor(a_genome, a_profile, dimension=5)
                archive.consider(
                    QDArchiveEntry(
                        agent_id=a.agent_id,
                        profile=a_profile,
                        behavioral_descriptor=a_desc,
                        fitness=float(a.energy + a.currency),
                    )
                )

            niche_list: list[dict[str, Any]] = []
            for idx, centroid in enumerate(archive.centroids):
                entry = archive.cells.get(idx)
                niche_list.append(
                    {
                        "niche_id": idx,
                        "centroid": [round(float(v), 4) for v in centroid],
                        "occupied": entry is not None,
                        "agent_id": entry.agent_id if entry else None,
                        "fitness": round(entry.fitness, 2) if entry else 0.0,
                    }
                )

            computed_status: dict[str, Any] = {
                "status": "ok",
                "total_transitions": total_transitions,
                "latest_tick": latest_tick,
                "alive_agents_count": alive_count,
                "gini_index": round(gini, 4),
                "archive_niche_count": archive.coverage(),
                "archive_total_niches": archive.total_niches(),
                "db_path": str(self.db_path),
                "timestamp": datetime.now(UTC).isoformat(),
                "niches": niche_list,
            }
            self._cached_status = computed_status
            self._cached_seq = latest_seq
            return computed_status

    def fetch_transitions(
        self,
        from_seq: int = 0,
        limit: int = 50,
    ) -> list[tuple[int, dict[str, Any]]]:
        """Fetch transition records after sequence `from_seq`."""
        with self._lock:
            store = self._get_or_create_store()
            rows = store.list_transitions_with_seq(from_seq=from_seq, limit=limit)
            records: list[tuple[int, dict[str, Any]]] = []
            for seq_no, trans in rows:
                tick = int(trans.state.data.get("tick", trans.exogenous_input.tick))
                next_data = trans.next_state.data
                alive_count = 0
                gini_val = 0.0
                if isinstance(next_data, dict):
                    agents = next_data.get("agents", {})
                    if isinstance(agents, dict):
                        alive_list = [
                            a for a in agents.values() if isinstance(a, dict) and a.get("alive", False)
                        ]
                        alive_count = len(alive_list)
                        wealths = [
                            float(a.get("currency", 0) + sum(a.get("inventory", {}).values()))
                            for a in alive_list
                        ]
                        gini_val = compute_gini_coefficient(wealths) if wealths else 0.0

                payload: dict[str, Any] = {
                    "seq_no": seq_no,
                    "transition_id": str(trans.transition_id),
                    "tick": tick,
                    "agent_id": trans.action.agent_id,
                    "action_type": trans.action.action_type,
                    "params": trans.action.params,
                    "seed": trans.seed,
                    "emission": trans.emission.data,
                    "alive_agents_count": alive_count,
                    "gini_index": round(gini_val, 4),
                    "timestamp": trans.timestamp.isoformat(),
                }
                records.append((seq_no, payload))
            return records

    def stream_sse(
        self,
        handler: BaseHTTPRequestHandler,
        query: dict[str, list[str]],
    ) -> None:
        """Stream transition records via Server-Sent Events until client disconnects."""
        last_event_id = handler.headers.get("Last-Event-ID")
        if last_event_id:
            try:
                since_seq = int(last_event_id)
            except ValueError:
                since_seq = 0
        elif "since" in query:
            try:
                since_seq = int(query["since"][0])
            except ValueError:
                since_seq = 0
        else:
            with self._lock:
                store = self._get_or_create_store()
                total = store.count()
            since_seq = max(0, total - 50) if total > 100 else 0

        heartbeat_ticks = 0
        while not self._stopping.is_set():
            records = self.fetch_transitions(from_seq=since_seq, limit=50)
            if records:
                for seq_no, payload in records:
                    since_seq = seq_no
                    chunk = (
                        f"id: {seq_no}\n"
                        f"event: transition\n"
                        f"data: {json.dumps(payload)}\n\n"
                    )
                    try:
                        handler.wfile.write(chunk.encode("utf-8"))
                        handler.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                        return
                heartbeat_ticks = 0
            else:
                heartbeat_ticks += 1
                if heartbeat_ticks >= 5:
                    try:
                        handler.wfile.write(b": heartbeat\n\n")
                        handler.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
                        return
                    heartbeat_ticks = 0

            if self._stopping.wait(timeout=self.poll_interval):
                break

    def start(self, background: bool = True) -> None:
        """Start the HTTP & SSE server."""
        if self._httpd is not None:
            return

        self._stopping.clear()
        server_address = (self.host, self.port)
        self._httpd = ThreadedHTTPServer(server_address, EvolZenRequestHandler)
        self._httpd.dashboard_server = self
        self._actual_port = self._httpd.server_address[1]
        logger.info("EvolZen dashboard server bound on http://{}:{}", self.host, self._actual_port)

        if background:
            self._thread = threading.Thread(
                target=self._httpd.serve_forever,
                daemon=True,
                name=f"EvolZenDashboardServer-{self._actual_port}",
            )
            self._thread.start()
        else:
            try:
                self._httpd.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                self.stop()

    def stop(self) -> None:
        """Stop the HTTP server cleanly and release all resources."""
        self._stopping.set()
        if self._httpd is not None:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception as e:
                logger.debug("Error during server shutdown: {}", e)
            finally:
                self._httpd = None

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=3.0)
            self._thread = None

        with self._lock:
            if self._store is not None:
                try:
                    self._store.close()
                except Exception as e:
                    logger.debug("Error closing TransitionLogStore: {}", e)
                finally:
                    self._store = None

    def __enter__(self) -> EvolZenDashboardServer:
        self.start(background=True)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        self.stop()


def generate_live_dashboard_html() -> str:
    """Generate the interactive reactive single-page HTML5/SVG application."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EvolZen Live Real-Time Dashboard</title>
  <style>
    :root {
      --bg-body: #0d1117;
      --bg-panel: #161b22;
      --bg-card: #21262d;
      --border-main: #30363d;
      --border-accent: #388bfd;
      --text-main: #c9d1d9;
      --text-bright: #f0f6fc;
      --text-muted: #8b949e;
      --cyan: #38bdf8;
      --green: #2ea043;
      --yellow: #d29922;
      --orange: #f0883e;
      --purple: #bc8cff;
      --red: #f85149;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg-body);
      color: var(--text-main);
      padding: 1.5rem;
      line-height: 1.5;
    }

    .container {
      max-width: 1400px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    /* Header */
    .top-header {
      background: var(--bg-panel);
      border: 1px solid var(--border-main);
      border-radius: 8px;
      padding: 1.25rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }
    .header-title-group h1 {
      font-size: 1.5rem;
      font-weight: 700;
      color: var(--text-bright);
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .badge-brand {
      background: linear-gradient(135deg, #1f6feb 0%, #388bfd 100%);
      color: #fff;
      font-size: 0.75rem;
      font-weight: 800;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      letter-spacing: 0.05em;
    }
    .header-sub {
      color: var(--text-muted);
      font-size: 0.85rem;
      margin-top: 0.25rem;
    }

    .stream-controls {
      display: flex;
      align-items: center;
      gap: 1rem;
    }
    .status-pill {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: var(--bg-card);
      border: 1px solid var(--border-main);
      padding: 0.35rem 0.75rem;
      border-radius: 20px;
      font-size: 0.8rem;
      font-weight: 600;
    }
    .status-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--green);
      box-shadow: 0 0 8px var(--green);
      animation: pulse-dot 2s infinite;
    }
    .status-dot.connecting { background: var(--yellow); box-shadow: 0 0 8px var(--yellow); }
    .status-dot.disconnected { background: var(--red); box-shadow: 0 0 8px var(--red); animation: none; }

    @keyframes pulse-dot {
      0% { opacity: 0.6; transform: scale(0.95); }
      50% { opacity: 1; transform: scale(1.1); }
      100% { opacity: 0.6; transform: scale(0.95); }
    }

    .btn {
      background: var(--bg-card);
      color: var(--text-bright);
      border: 1px solid var(--border-main);
      padding: 0.4rem 0.8rem;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
    }
    .btn:hover { background: #30363d; border-color: #8b949e; }
    .btn-active { background: #1f6feb; border-color: #388bfd; }

    /* KPI Row */
    .kpi-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
    }
    .kpi-card {
      background: var(--bg-panel);
      border: 1px solid var(--border-main);
      border-radius: 8px;
      padding: 1rem 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }
    .kpi-label {
      font-size: 0.75rem;
      text-transform: uppercase;
      font-weight: 700;
      color: var(--text-muted);
      letter-spacing: 0.05em;
    }
    .kpi-value {
      font-size: 1.85rem;
      font-weight: 700;
      color: var(--text-bright);
      font-variant-numeric: tabular-nums;
    }
    .kpi-sub {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    /* Main Visual Split */
    .vis-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
    }
    @media (max-width: 992px) {
      .vis-grid { grid-template-columns: 1fr; }
    }

    .vis-card {
      background: var(--bg-panel);
      border: 1px solid var(--border-main);
      border-radius: 8px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .vis-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-main);
      padding-bottom: 0.75rem;
    }
    .vis-title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--text-bright);
    }
    .vis-badge {
      font-size: 0.75rem;
      color: var(--cyan);
      background: rgba(56, 189, 248, 0.1);
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      font-weight: 600;
    }

    /* SVG Containers */
    .svg-container {
      width: 100%;
      height: 260px;
      background: #090d13;
      border: 1px solid var(--border-main);
      border-radius: 6px;
      position: relative;
      overflow: hidden;
    }
    svg { width: 100%; height: 100%; }

    /* Niche Map Styling */
    .niche-node {
      cursor: pointer;
      transition: all 0.3s ease;
    }
    .niche-node:hover circle {
      stroke: var(--text-bright);
      stroke-width: 3px;
    }

    /* Gini Meter */
    .gini-meter-container {
      margin-top: 0.5rem;
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }
    .gini-bar-track {
      height: 12px;
      background: #21262d;
      border-radius: 6px;
      position: relative;
      overflow: hidden;
      border: 1px solid var(--border-main);
    }
    .gini-bar-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, var(--green) 0%, var(--yellow) 40%, var(--red) 100%);
      transition: width 0.5s ease;
    }
    .gini-labels {
      display: flex;
      justify-content: space-between;
      font-size: 0.7rem;
      color: var(--text-muted);
    }

    /* Event Log Table */
    .event-card {
      background: var(--bg-panel);
      border: 1px solid var(--border-main);
      border-radius: 8px;
      padding: 1.25rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .table-container {
      max-height: 380px;
      overflow-y: auto;
      border: 1px solid var(--border-main);
      border-radius: 6px;
      background: #090d13;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8rem;
      text-align: left;
    }
    thead {
      position: sticky;
      top: 0;
      background: #161b22;
      border-bottom: 2px solid var(--border-main);
      z-index: 2;
    }
    th {
      padding: 0.6rem 0.75rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      font-size: 0.7rem;
      letter-spacing: 0.05em;
    }
    td {
      padding: 0.5rem 0.75rem;
      border-bottom: 1px solid #1c2128;
      color: var(--text-main);
      font-variant-numeric: tabular-nums;
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
    }
    tr.new-row {
      animation: highlight-row 1.2s ease-out;
    }
    @keyframes highlight-row {
      0% { background: rgba(56, 189, 248, 0.25); }
      100% { background: transparent; }
    }

    /* Badges */
    .badge {
      display: inline-block;
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: 700;
      text-transform: uppercase;
    }
    .badge-gather { background: rgba(46, 160, 67, 0.2); color: #3fb950; border: 1px solid rgba(46, 160, 67, 0.4); }
    .badge-craft { background: rgba(31, 111, 235, 0.2); color: #58a6ff; border: 1px solid rgba(31, 111, 235, 0.4); }
    .badge-trade { background: rgba(210, 153, 34, 0.2); color: #d29922; border: 1px solid rgba(210, 153, 34, 0.4); }
    .badge-move { background: rgba(188, 140, 255, 0.2); color: #bc8cff; border: 1px solid rgba(188, 140, 255, 0.4); }
    .badge-wait { background: rgba(139, 148, 158, 0.2); color: #8b949e; border: 1px solid rgba(139, 148, 158, 0.4); }
    .badge-other { background: rgba(240, 136, 62, 0.2); color: #f0883e; border: 1px solid rgba(240, 136, 62, 0.4); }

    /* Footer */
    .dashboard-footer {
      text-align: center;
      color: var(--text-muted);
      font-size: 0.75rem;
      padding: 1rem 0;
    }
  </style>
</head>
<body>
  <div class="container">
    <!-- Top Header -->
    <header class="top-header">
      <div class="header-title-group">
        <h1>
          <span>EvolZen Live Dashboard</span>
          <span class="badge-brand">FRONTIER 3</span>
        </h1>
        <div class="header-sub">Continuous Real-Time Multi-Agent Telemetry &bull; Server-Sent Events (SSE)</div>
      </div>
      <div class="stream-controls">
        <div class="status-pill">
          <div class="status-dot" id="status-dot"></div>
          <span id="status-text">CONNECTING...</span>
        </div>
        <button class="btn" id="btn-toggle" onclick="toggleStream()">Pause Stream</button>
        <button class="btn" onclick="clearEventLog()">Clear Log</button>
      </div>
    </header>

    <!-- KPI Row -->
    <section class="kpi-row">
      <div class="kpi-card">
        <span class="kpi-label">World Tick</span>
        <span class="kpi-value" id="kpi-tick">-</span>
        <span class="kpi-sub">Continuous time</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Active Agents</span>
        <span class="kpi-value" id="kpi-agents">-</span>
        <span class="kpi-sub" id="kpi-agents-sub">Alive population</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Wealth Gini</span>
        <span class="kpi-value" id="kpi-gini">-</span>
        <span class="kpi-sub" id="kpi-gini-sub">Macroeconomic metric</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">CVTArchive Niches</span>
        <span class="kpi-value" id="kpi-niches">-</span>
        <span class="kpi-sub">5D MAP-Elites niches</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-label">Transitions</span>
        <span class="kpi-value" id="kpi-transitions">-</span>
        <span class="kpi-sub" id="kpi-seq-sub">Sequence stream</span>
      </div>
    </section>

    <!-- Visualizations Row -->
    <div class="vis-grid">
      <!-- 5D CVTArchive Voronoi Niche Map -->
      <section class="vis-card">
        <div class="vis-header">
          <span class="vis-title">5D CVTArchive Voronoi Niche Map</span>
          <span class="vis-badge" id="niche-badge">10 Centroids</span>
        </div>
        <div class="svg-container">
          <svg id="niche-svg" viewBox="0 0 500 260">
            <defs>
              <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>
            <g id="niche-links" stroke="#21262d" stroke-dasharray="2,2"></g>
            <g id="niche-nodes"></g>
          </svg>
        </div>
        <div style="font-size:0.75rem; color:var(--text-muted); display:flex; justify-content:space-between;">
          <span><span style="color:var(--cyan);">&#9679;</span> Occupied Elite Niche</span>
          <span><span style="color:#484f58;">&#9675;</span> Vacant Centroid</span>
          <span id="niche-hover-info">Hover node to inspect 5D niche</span>
        </div>
      </section>

      <!-- Wealth Gini & Lorenz Meter -->
      <section class="vis-card">
        <div class="vis-header">
          <span class="vis-title">Macroeconomic Lorenz &amp; Gini Meter</span>
          <span class="vis-badge" id="gini-badge">Phase 1.3 Economy</span>
        </div>
        <div class="svg-container">
          <svg id="lorenz-svg" viewBox="0 0 500 260">
            <!-- Background Grid -->
            <line x1="60" y1="210" x2="440" y2="210" stroke="#30363d" stroke-width="1.5" />
            <line x1="60" y1="30" x2="60" y2="210" stroke="#30363d" stroke-width="1.5" />
            <line x1="60" y1="210" x2="440" y2="30" stroke="#8b949e" stroke-dasharray="4,4" stroke-width="1.5" />
            <!-- Lorenz Area & Path -->
            <path id="lorenz-area" fill="rgba(56, 189, 248, 0.12)" d="" />
            <path id="lorenz-path" fill="none" stroke="var(--cyan)" stroke-width="2.5" d="" />
            <!-- Axis Labels -->
            <text x="250" y="240" fill="#8b949e" font-size="11" text-anchor="middle">Cumulative Population %</text>
            <text x="25" y="120" fill="#8b949e" font-size="11" transform="rotate(-90 25 120)" text-anchor="middle">Wealth %</text>
          </svg>
        </div>
        <div class="gini-meter-container">
          <div class="gini-bar-track">
            <div class="gini-bar-fill" id="gini-bar-fill"></div>
          </div>
          <div class="gini-labels">
            <span>0.0 (Equality)</span>
            <span>0.3 (Moderate)</span>
            <span>0.6 (High)</span>
            <span>1.0 (Oligarchy)</span>
          </div>
        </div>
      </section>
    </div>

    <!-- Event Log -->
    <section class="event-card">
      <div class="vis-header">
        <span class="vis-title">Real-Time Transition Event Stream</span>
        <div style="display:flex; align-items:center; gap:0.75rem;">
          <label style="font-size:0.75rem; color:var(--text-muted); cursor:pointer;">
            <input type="checkbox" id="chk-autoscroll" checked> Auto-scroll
          </label>
          <span class="vis-badge" id="event-counter">0 events</span>
        </div>
      </div>
      <div class="table-container" id="table-wrap">
        <table>
          <thead>
            <tr>
              <th style="width: 70px;">Seq #</th>
              <th style="width: 70px;">Tick</th>
              <th style="width: 110px;">Agent</th>
              <th style="width: 100px;">Action</th>
              <th>Details</th>
              <th style="width: 140px;">Transition ID</th>
              <th style="width: 110px;">Time</th>
            </tr>
          </thead>
          <tbody id="event-tbody"></tbody>
        </table>
      </div>
    </section>

    <!-- Footer -->
    <footer class="dashboard-footer">
      EvolZen Research Platform &bull; Standard Library SSE Streaming &bull; Offline Hermetic Visualizer
    </footer>
  </div>

  <script>
    let evtSource = null;
    let isStreamActive = true;
    let eventCount = 0;
    let currentNiches = [];

    const defaultCentroids = [
      [0.15, 0.25, 0.35, 0.45, 0.55],
      [0.85, 0.75, 0.65, 0.55, 0.45],
      [0.22, 0.78, 0.45, 0.12, 0.88],
      [0.72, 0.18, 0.55, 0.90, 0.30],
      [0.50, 0.50, 0.50, 0.50, 0.50],
      [0.30, 0.60, 0.20, 0.80, 0.40],
      [0.65, 0.35, 0.85, 0.15, 0.75],
      [0.40, 0.85, 0.15, 0.65, 0.25],
      [0.80, 0.20, 0.70, 0.30, 0.90],
      [0.10, 0.90, 0.30, 0.70, 0.20]
    ];

    function init() {
      fetchStatus();
      connectSSE();
    }

    function fetchStatus() {
      fetch('/api/status')
        .then(res => res.json())
        .then(data => {
          updateStatusKPIs(data);
          if (data.niches && data.niches.length > 0) {
            currentNiches = data.niches;
            renderNicheMap(currentNiches);
          }
        })
        .catch(err => console.debug("Status fetch:", err));
    }

    function updateStatusKPIs(status) {
      if (!status) return;
      document.getElementById('kpi-tick').textContent = status.latest_tick ?? 0;
      document.getElementById('kpi-agents').textContent = status.alive_agents_count ?? 0;
      document.getElementById('kpi-gini').textContent = Number(status.gini_index ?? 0).toFixed(4);
      document.getElementById('kpi-niches').textContent = `${status.archive_niche_count ?? 0} / ${status.archive_total_niches ?? 10}`;
      document.getElementById('kpi-transitions').textContent = status.total_transitions ?? 0;

      updateGiniMeter(status.gini_index ?? 0);
    }

    function renderNicheMap(niches) {
      const nodesGroup = document.getElementById('niche-nodes');
      const linksGroup = document.getElementById('niche-links');
      nodesGroup.innerHTML = '';
      linksGroup.innerHTML = '';

      const items = (niches && niches.length > 0) ? niches : defaultCentroids.map((c, i) => ({
        niche_id: i,
        centroid: c,
        occupied: false,
        agent_id: null,
        fitness: 0.0
      }));

      // Project 5D centroids to 2D
      const projected = items.map(n => {
        const c = n.centroid || [0.5, 0.5, 0.5, 0.5, 0.5];
        const x = 50 + 400 * (0.65 * c[0] + 0.35 * (c[2] || 0.5));
        const y = 35 + 190 * (0.65 * c[1] + 0.35 * (c[3] || 0.5));
        return { ...n, x, y };
      });

      // Proximity Delaunay approximation links
      for (let i = 0; i < projected.length; i++) {
        for (let j = i + 1; j < projected.length; j++) {
          const dx = projected[i].x - projected[j].x;
          const dy = projected[i].y - projected[j].y;
          const dist = Math.hypot(dx, dy);
          if (dist < 130) {
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', projected[i].x);
            line.setAttribute('y1', projected[i].y);
            line.setAttribute('x2', projected[j].x);
            line.setAttribute('y2', projected[j].y);
            line.setAttribute('stroke', '#21262d');
            line.setAttribute('stroke-width', '1');
            linksGroup.appendChild(line);
          }
        }
      }

      // Render Nodes
      projected.forEach(n => {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'niche-node');

        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', n.x);
        circle.setAttribute('cy', n.y);
        circle.setAttribute('r', n.occupied ? '12' : '9');
        circle.setAttribute('fill', n.occupied ? '#38bdf8' : '#161b22');
        circle.setAttribute('stroke', n.occupied ? '#fff' : '#484f58');
        circle.setAttribute('stroke-width', n.occupied ? '2' : '1.5');
        if (n.occupied) {
          circle.setAttribute('filter', 'url(#glow)');
        }

        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        label.setAttribute('x', n.x);
        label.setAttribute('y', n.y + 3.5);
        label.setAttribute('text-anchor', 'middle');
        label.setAttribute('font-size', '9');
        label.setAttribute('font-weight', 'bold');
        label.setAttribute('fill', n.occupied ? '#000' : '#8b949e');
        label.textContent = `#${n.niche_id}`;

        g.appendChild(circle);
        g.appendChild(label);

        g.onmouseenter = () => {
          const coords = (n.centroid || []).map(v => Number(v).toFixed(2)).join(', ');
          const statusStr = n.occupied ? `Occupied by ${n.agent_id} (Fitness: ${n.fitness})` : 'Vacant';
          document.getElementById('niche-hover-info').textContent = `Niche #${n.niche_id}: [${coords}] — ${statusStr}`;
        };
        g.onmouseleave = () => {
          document.getElementById('niche-hover-info').textContent = 'Hover node to inspect 5D niche';
        };

        nodesGroup.appendChild(g);
      });
    }

    function updateGiniMeter(gini) {
      const g = Math.max(0, Math.min(1, Number(gini)));
      const pct = (g * 100).toFixed(1);
      document.getElementById('gini-bar-fill').style.width = pct + '%';

      // Update Lorenz curve SVG
      const x0 = 60, y0 = 210, x1 = 440, y1 = 30;
      const width = x1 - x0;
      const height = y0 - y1;

      // Model Lorenz curve approximation from Gini
      const exponent = Math.max(1, (1 + g) / Math.max(0.01, 1 - g));
      let points = [];
      const steps = 30;
      for (let i = 0; i <= steps; i++) {
        const p = i / steps;
        const l = Math.pow(p, exponent);
        const px = x0 + p * width;
        const py = y0 - l * height;
        points.push([px, py]);
      }

      const dPath = points.map((pt, idx) => (idx === 0 ? `M ${pt[0]} ${pt[1]}` : `L ${pt[0]} ${pt[1]}`)).join(' ');
      document.getElementById('lorenz-path').setAttribute('d', dPath);

      const dArea = dPath + ` L ${x1} ${y1} L ${x0} ${y0} Z`;
      document.getElementById('lorenz-area').setAttribute('d', dArea);

      // Severity diagnostic
      let badge = 'Low (Equality)';
      if (g >= 0.5) badge = 'Severe Inequality';
      else if (g >= 0.35) badge = 'High Inequality';
      else if (g >= 0.2) badge = 'Moderate Inequality';
      document.getElementById('gini-badge').textContent = `Gini ${g.toFixed(3)} • ${badge}`;
    }

    function connectSSE() {
      if (evtSource) {
        evtSource.close();
      }

      setConnectionStatus('connecting', 'CONNECTING...');
      evtSource = new EventSource('/api/events');

      evtSource.onopen = function() {
        setConnectionStatus('connected', 'STREAMING (LIVE)');
      };

      function handleTransition(event) {
        try {
          const data = JSON.parse(event.data);
          onEventReceived(data);
        } catch (e) {
          console.debug("SSE Parse Error:", e);
        }
      }

      evtSource.addEventListener('transition', handleTransition);
      evtSource.onmessage = handleTransition;

      evtSource.onerror = function() {
        setConnectionStatus('disconnected', 'RECONNECTING...');
      };
    }

    function setConnectionStatus(state, label) {
      const dot = document.getElementById('status-dot');
      const text = document.getElementById('status-text');
      dot.className = 'status-dot';
      if (state === 'connecting') dot.classList.add('connecting');
      if (state === 'disconnected') dot.classList.add('disconnected');
      text.textContent = label;
    }

    function toggleStream() {
      const btn = document.getElementById('btn-toggle');
      if (isStreamActive) {
        if (evtSource) evtSource.close();
        isStreamActive = false;
        btn.textContent = 'Resume Stream';
        setConnectionStatus('disconnected', 'PAUSED');
      } else {
        connectSSE();
        isStreamActive = true;
        btn.textContent = 'Pause Stream';
      }
    }

    function clearEventLog() {
      document.getElementById('event-tbody').innerHTML = '';
      eventCount = 0;
      document.getElementById('event-counter').textContent = '0 events';
    }

    function onEventReceived(data) {
      eventCount++;
      document.getElementById('event-counter').textContent = `${eventCount} events`;

      // Update KPIs
      if (data.tick !== undefined) document.getElementById('kpi-tick').textContent = data.tick;
      if (data.alive_agents_count !== undefined) document.getElementById('kpi-agents').textContent = data.alive_agents_count;
      if (data.gini_index !== undefined) {
        document.getElementById('kpi-gini').textContent = Number(data.gini_index).toFixed(4);
        updateGiniMeter(data.gini_index);
      }
      if (data.seq_no !== undefined) {
        document.getElementById('kpi-transitions').textContent = data.seq_no;
      }

      // Append row to event table
      const tbody = document.getElementById('event-tbody');
      const row = document.createElement('tr');
      row.className = 'new-row';

      const action = data.action_type || 'unknown';
      let badgeClass = 'badge-other';
      if (action === 'gather') badgeClass = 'badge-gather';
      else if (action === 'craft') badgeClass = 'badge-craft';
      else if (action === 'trade') badgeClass = 'badge-trade';
      else if (action === 'move') badgeClass = 'badge-move';
      else if (action === 'wait') badgeClass = 'badge-wait';

      const shortId = (data.transition_id || '').substring(0, 8);
      const paramsStr = data.params ? JSON.stringify(data.params) : '';
      const timeStr = data.timestamp ? new Date(data.timestamp).toLocaleTimeString() : '';

      row.innerHTML = `
        <td style="color:var(--text-muted);">#${data.seq_no || eventCount}</td>
        <td style="font-weight:600; color:var(--text-bright);">${data.tick ?? '-'}</td>
        <td style="color:var(--cyan);">${escapeHtml(data.agent_id || '-')}</td>
        <td><span class="badge ${badgeClass}">${escapeHtml(action)}</span></td>
        <td style="color:var(--text-muted); font-size:0.75rem;">${escapeHtml(paramsStr)}</td>
        <td style="color:#8b949e;" title="${escapeHtml(data.transition_id || '')}">${escapeHtml(shortId)}</td>
        <td style="color:#6e7681; font-size:0.75rem;">${escapeHtml(timeStr)}</td>
      `;

      tbody.appendChild(row);

      // Keep maximum 150 rows in DOM to avoid bloat
      if (tbody.children.length > 150) {
        tbody.removeChild(tbody.firstChild);
      }

      const chk = document.getElementById('chk-autoscroll');
      if (chk && chk.checked) {
        const wrap = document.getElementById('table-wrap');
        wrap.scrollTop = wrap.scrollHeight;
      }
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    window.onload = init;
  </script>
</body>
</html>
"""
