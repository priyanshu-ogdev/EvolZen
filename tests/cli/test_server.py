"""Unit and integration tests for EvolZen live dashboard streaming server (Frontier 3)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from typer.testing import CliRunner

from evolzen.cli.main import app
from evolzen.cli.server import EvolZenDashboardServer
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.schemas.transition import Action
from evolzen.storage.transition_log import TransitionLogStore

runner = CliRunner()


def _populate_test_db(db_path: Path, count: int = 5) -> None:
    """Helper to populate a DuckDB database with real transitions."""
    engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=100)
    state = engine.reset(seed=42)
    cur = state
    with TransitionLogStore(db_path) as store:
        for i in range(count):
            action = Action(agent_id="agent_0", action_type="gather" if i % 2 == 0 else "wait")
            t = engine.step(cur, action)
            store.append(t, run_id="test-run", branch_id="main")
            cur = t.next_state


def test_server_empty_db_status_and_root(tmp_path: Path) -> None:
    """Server starts gracefully against a fresh empty database."""
    db_path = tmp_path / "empty.duckdb"
    server = EvolZenDashboardServer(host="127.0.0.1", port=0, db_path=db_path)
    with server:
        port = server.server_port
        assert port > 0

        # GET /
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type", "")
            body = resp.read().decode("utf-8")
            assert "EvolZen Live Dashboard" in body
            assert "EventSource" in body
            assert "5D CVTArchive Voronoi Niche Map" in body
            assert "Real-Time Transition Event Stream" in body

        # GET /api/status
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5) as resp:
            assert resp.status == 200
            assert "application/json" in resp.headers.get("Content-Type", "")
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "ok"
            assert data["total_transitions"] == 0
            assert data["latest_tick"] == 0
            assert data["alive_agents_count"] == 0
            assert data["gini_index"] == 0.0
            assert data["archive_niche_count"] == 0
            assert data["archive_total_niches"] == 10


def test_server_endpoints_with_transitions(tmp_path: Path) -> None:
    """Server correctly serves status and streams events from a populated DB."""
    db_path = tmp_path / "transitions.duckdb"
    _populate_test_db(db_path, count=5)

    with EvolZenDashboardServer(host="127.0.0.1", port=0, db_path=db_path, poll_interval=0.1) as server:
        port = server.server_port

        # 1. Test /api/status
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5) as resp:
            assert resp.status == 200
            data = json.loads(resp.read().decode("utf-8"))
            assert data["status"] == "ok"
            assert data["total_transitions"] == 5
            assert data["latest_tick"] >= 0
            assert data["alive_agents_count"] >= 1
            assert isinstance(data["gini_index"], float)
            assert data["archive_niche_count"] >= 1
            assert data["archive_total_niches"] == 10
            assert len(data["niches"]) == 10

        # 2. Test /api/events SSE stream
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/events?since=0",
            headers={"Accept": "text/event-stream"},
        )
        with urllib.request.urlopen(req, timeout=5) as stream_resp:
            assert stream_resp.status == 200
            assert "text/event-stream" in stream_resp.headers.get("Content-Type", "")

            # Read lines until first transition event block is captured
            lines: list[str] = []
            for _ in range(15):
                line = stream_resp.readline().decode("utf-8")
                lines.append(line.strip())
                if line.strip() == "" and len(lines) > 2:
                    break

            id_line = next((line_item for line_item in lines if line_item.startswith("id: ")), "")
            event_line = next((line_item for line_item in lines if line_item.startswith("event: ")), "")
            data_line = next((line_item for line_item in lines if line_item.startswith("data: ")), "")

            assert id_line == "id: 1"
            assert event_line == "event: transition"
            assert data_line.startswith("data: ")

            event_data = json.loads(data_line[6:])
            assert event_data["seq_no"] == 1
            assert "transition_id" in event_data
            assert "agent_id" in event_data
            assert "action_type" in event_data


def test_server_404_not_found(tmp_path: Path) -> None:
    """Non-existent endpoints return HTTP 404."""
    db_path = tmp_path / "test_404.duckdb"
    with EvolZenDashboardServer(host="127.0.0.1", port=0, db_path=db_path) as server:
        port = server.server_port
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/nonexistent", timeout=5)
        assert exc_info.value.code == 404


def test_cli_serve_once(tmp_path: Path) -> None:
    """CLI `evolzen serve --once` outputs JSON status and exits 0."""
    db_path = tmp_path / "cli_transitions.duckdb"
    _populate_test_db(db_path, count=3)

    result = runner.invoke(
        app,
        ["serve", "--once", "--port", "0", "--db-path", str(db_path)],
    )
    assert result.exit_code == 0

    # Parse stdout: find the JSON object block
    out = result.stdout
    json_start = out.find("{")
    assert json_start != -1
    json_str = out[json_start:]
    data = json.loads(json_str)

    assert data["status"] == "ok"
    assert data["total_transitions"] == 3
    assert data["alive_agents_count"] >= 1
    assert data["archive_total_niches"] == 10
    assert "niches" in data


def test_server_sse_streaming_live_appends(tmp_path: Path) -> None:
    """SSE client receives dynamically appended transitions in real time."""
    db_path = tmp_path / "live_stream.duckdb"
    _populate_test_db(db_path, count=2)

    with EvolZenDashboardServer(host="127.0.0.1", port=0, db_path=db_path, poll_interval=0.05) as server:
        port = server.server_port

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/events?since=2",
            headers={"Accept": "text/event-stream"},
        )
        with urllib.request.urlopen(req, timeout=5) as stream_resp:
            # Now append a 3rd transition to the database
            engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=100)
            state = engine.reset(seed=99)
            action = Action(agent_id="agent_1", action_type="trade", params={"qty": 3})
            t3 = engine.step(state, action)

            with TransitionLogStore(db_path) as store:
                store.append(t3, run_id="live-run", branch_id="main")

            # Read next event from SSE stream
            lines: list[str] = []
            for _ in range(20):
                line = stream_resp.readline().decode("utf-8").strip()
                if line:
                    lines.append(line)
                if line == "" and len(lines) >= 3:
                    break

            id_line = next((line_item for line_item in lines if line_item.startswith("id: ")), "")
            data_line = next((line_item for line_item in lines if line_item.startswith("data: ")), "")

            assert id_line == "id: 3"
            assert data_line.startswith("data: ")
            ev = json.loads(data_line[6:])
            assert ev["seq_no"] == 3
            assert ev["agent_id"] == "agent_1"
            assert ev["action_type"] == "trade"

