import json
from pathlib import Path

from typer.testing import CliRunner

from evolzen.cli.main import app
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.schemas.transition import Action, Emission, State, Transition
from evolzen.storage.transition_log import TransitionLogStore

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "EvolZen" in result.stdout
    assert "run" in result.stdout
    assert "train" in result.stdout
    assert "evaluate" in result.stdout
    assert "replay" in result.stdout
    assert "inspect" in result.stdout
    assert "ablate" in result.stdout
    assert "cluster" in result.stdout
    assert "daemon" in result.stdout


def test_cli_run(tmp_path: Path) -> None:
    db_path = tmp_path / "test_run.duckdb"
    result = runner.invoke(
        app,
        ["run", "--generations", "2", "--ticks-per-gen", "2", "--seed", "42", "--db-path", str(db_path)],
    )
    assert result.exit_code == 0
    assert "Simulation completed successfully" in result.stdout
    assert "Total generations: 2" in result.stdout
    assert "Transitions logged:" in result.stdout
    assert "Active population:" in result.stdout
    assert "Wealth Gini coefficient:" in result.stdout
    assert "Active lineages:" in result.stdout
    assert db_path.exists()


def test_cli_run_with_drought(tmp_path: Path) -> None:
    db_path = tmp_path / "test_run_drought.duckdb"
    result = runner.invoke(
        app,
        [
            "run",
            "--generations",
            "2",
            "--ticks-per-gen",
            "10",
            "--drought-interval",
            "5",
            "--seed",
            "42",
            "--db-path",
            str(db_path),
        ],
    )
    assert result.exit_code == 0
    assert "Simulation completed successfully" in result.stdout
    assert "Total generations: 2" in result.stdout
    assert "Drought interval: 5" in result.stdout
    assert "Cultural retention (recipe adoptions in ManualStore):" in result.stdout
    assert "Gini stability under drought:" in result.stdout
    assert "Active lineages:" in result.stdout
    assert db_path.exists()


def test_cli_train() -> None:
    result = runner.invoke(app, ["train", "--steps", "2", "--batch-size", "2", "--seed", "42"])
    assert result.exit_code == 0
    assert "Training complete" in result.stdout
    assert "Total GRPO updates executed: 2" in result.stdout
    assert "JEPA representation variance:" in result.stdout
    assert "JEPA dimension health:" in result.stdout


def test_cli_train_with_db_path(tmp_path: Path) -> None:
    db_path = tmp_path / "train_transitions.duckdb"
    with TransitionLogStore(db_path) as store:
        engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=20)
        state = engine.reset(seed=42)
        cur = state
        for i in range(12):
            action = Action(agent_id="agent_0", action_type="wait" if i % 2 == 0 else "gather")
            t = engine.step(cur, action)
            store.append(t)
            cur = t.next_state

    result = runner.invoke(
        app,
        ["train", "--db-path", str(db_path), "--steps", "3", "--batch-size", "4", "--seed", "42"],
    )
    assert result.exit_code == 0
    assert "Training complete" in result.stdout
    assert "Transitions source: DuckDB" in result.stdout
    assert "Transitions count: 12" in result.stdout
    assert "Total GRPO updates executed: 3" in result.stdout
    assert "JEPA representation variance:" in result.stdout
    assert "JEPA dimension health:" in result.stdout
    assert "Rehearsal buffer size: 12" in result.stdout


def test_cli_train_fallback_bootstrap(tmp_path: Path) -> None:
    nonexistent_db = tmp_path / "nonexistent.duckdb"
    result = runner.invoke(
        app,
        ["train", "--db-path", str(nonexistent_db), "--steps", "2", "--batch-size", "2", "--seed", "42"],
    )
    assert result.exit_code == 0
    assert "Training complete" in result.stdout
    assert "Transitions source: engine bootstrap" in result.stdout
    assert "Total GRPO updates executed: 2" in result.stdout


def test_cli_evaluate() -> None:
    result = runner.invoke(app, ["evaluate", "--rounds", "2", "--persistent-ticks", "5", "--seed", "42"])
    assert result.exit_code == 0
    assert "EVOLZEN EVALUATION REPORT" in result.stdout
    assert "Held-out RHAE score:" in result.stdout
    assert "Reused-vs-fresh score gap:" in result.stdout


def test_cli_evaluate_with_planner() -> None:
    result = runner.invoke(
        app,
        [
            "evaluate",
            "--use-planner",
            "--planning-horizon",
            "2",
            "--rounds",
            "2",
            "--persistent-ticks",
            "5",
            "--seed",
            "42",
        ],
    )
    assert result.exit_code == 0
    assert "EVOLZEN EVALUATION REPORT" in result.stdout
    assert "model-based planning: ENABLED (horizon=2)" in result.stdout
    assert "planning efficiency delta:" in result.stdout


def test_cli_evaluate_with_planner_multi_tier() -> None:
    result = runner.invoke(
        app,
        [
            "evaluate",
            "--rounds",
            "2",
            "--use-planner",
            "--planning-horizon",
            "5",
            "--task-tier",
            "multi_tier",
            "--persistent-ticks",
            "5",
            "--seed",
            "42",
        ],
    )
    assert result.exit_code == 0
    assert "EVOLZEN EVALUATION REPORT" in result.stdout
    assert "task tier: multi_tier" in result.stdout
    assert "model-based planning: ENABLED (horizon=5)" in result.stdout
    assert "planning efficiency delta:" in result.stdout




def test_cli_inspect() -> None:
    result = runner.invoke(app, ["inspect", "--seed", "42", "--num-agents", "2"])
    assert result.exit_code == 0
    assert "EvolZen System State Inspection" in result.stdout
    assert "Gini Inequality:" in result.stdout
    assert "Founder Agent Behavioral Descriptor:" in result.stdout


def test_cli_inspect_export_html(tmp_path: Path) -> None:
    output_html = tmp_path / "dashboard.html"
    result = runner.invoke(
        app,
        ["inspect", "--seed", "42", "--num-agents", "4", "--num-locations", "3", "--export-html", str(output_html)],
    )
    assert result.exit_code == 0
    assert "EvolZen System State Inspection" in result.stdout
    assert f"Dashboard exported to: {output_html}" in result.stdout
    assert output_html.exists()

    content = output_html.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "View 1: 5D CVTArchive Voronoi Niche Map" in content
    assert "View 2: Agent Lineage Family Tree" in content
    assert "View 3: Spatial Resource &amp; Agent Heatmap" in content
    assert "View 4: Macroeconomic Lorenz &amp; Gini Visualizer" in content
    assert "<svg" in content
    assert "http://" not in content
    assert "https://" not in content


def test_cli_replay(tmp_path: Path) -> None:
    db_path = tmp_path / "replay_test.duckdb"
    with TransitionLogStore(db_path) as store:
        t = Transition(
            state=State(data={"tick": 0}),
            action=Action(agent_id="a0", action_type="wait"),
            emission=Emission(data={"accepted": True}),
            next_state=State(data={"tick": 1}),
        )
        store.append(t)

    result = runner.invoke(app, ["replay", "--db-path", str(db_path)])
    assert result.exit_code == 0
    assert "Transition Log Replay Verification:" in result.stdout
    assert "Transitions logged: 1" in result.stdout
    assert "SHA-256 Hash Chain Integrity: VERIFIED" in result.stdout


def test_cli_replay_missing_file() -> None:
    result = runner.invoke(app, ["replay", "--db-path", "nonexistent.duckdb"])
    assert result.exit_code == 1
    assert "Transition log file not found" in result.output


def test_cli_ablate_bootstrap(tmp_path: Path) -> None:
    output_path = tmp_path / "ablation_report.md"
    result = runner.invoke(
        app,
        ["ablate", "--steps", "10", "--seed", "42", "--output", str(output_path)],
    )
    assert result.exit_code == 0
    assert "| Condition |" in result.stdout
    assert "| baseline |" in result.stdout
    assert "| jepa_only |" in result.stdout
    assert "| wake_sleep_only |" in result.stdout
    assert "| combined |" in result.stdout
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "| Condition |" in content
    assert "| combined |" in content


def test_cli_ablate_from_db(tmp_path: Path) -> None:
    db_path = tmp_path / "test_transitions.duckdb"
    with TransitionLogStore(db_path) as store:
        engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=20)
        state = engine.reset(seed=42)
        cur = state
        for i in range(12):
            action = Action(agent_id="agent_0", action_type="wait" if i % 2 == 0 else "gather")
            t = engine.step(cur, action)
            store.append(t)
            cur = t.next_state

    result = runner.invoke(
        app,
        ["ablate", "--db-path", str(db_path), "--steps", "10", "--seed", "42"],
    )
    assert result.exit_code == 0
    assert "| Condition |" in result.stdout
    assert "| baseline |" in result.stdout
    assert "| combined |" in result.stdout


def test_cli_cluster_diagnostics() -> None:
    # 1. Default standalone diagnosis
    res_standalone = runner.invoke(app, ["cluster", "--role", "standalone"])
    assert res_standalone.exit_code == 0
    assert "EVOLZEN DISTRIBUTED CLUSTER PRE-FLIGHT DIAGNOSTICS" in res_standalone.stdout
    assert "Target Role:        STANDALONE" in res_standalone.stdout
    assert "1. Host Platform & Environment" in res_standalone.stdout
    assert "2. Subsystem Hardware & Containment Probes" in res_standalone.stdout
    assert "3. Pre-Flight Readiness Matrix" in res_standalone.stdout
    assert "4. Deployment Recommendations & Remediations" in res_standalone.stdout

    # 2. JSON structured output mode for dgx_spark
    res_dgx = runner.invoke(app, ["cluster", "--role", "dgx_spark", "--json"])
    assert res_dgx.exit_code == 0
    parsed = json.loads(res_dgx.stdout)
    assert parsed["role"] == "dgx_spark"
    assert "environment, economy, exploration, library, containment" in parsed["role_subsystems"]
    assert "host" in parsed
    assert "gvisor" in parsed
    assert "accelerators" in parsed
    assert "ray" in parsed
    assert "storage" in parsed
    assert "readiness" in parsed
    assert "checks" in parsed["readiness"]
    assert len(parsed["readiness"]["checks"]) >= 5

    # 3. Role options: jetson_agx and rtx_a6000
    res_jetson = runner.invoke(app, ["cluster", "--role", "jetson_agx"])
    assert res_jetson.exit_code == 0
    assert "Target Role:        JETSON_AGX" in res_jetson.stdout

    res_rtx = runner.invoke(app, ["cluster", "--role", "rtx_a6000"])
    assert res_rtx.exit_code == 0
    assert "Target Role:        RTX_A6000" in res_rtx.stdout

    # 4. Invalid role validation
    res_invalid = runner.invoke(app, ["cluster", "--role", "supercomputer_9000"])
    assert res_invalid.exit_code != 0


def test_cli_daemon_once(tmp_path: Path) -> None:
    db_path = tmp_path / "daemon_once.duckdb"
    with TransitionLogStore(db_path) as store:
        engine = SocialSandboxEngine(num_locations=2, num_agents=2, max_ticks=20)
        state = engine.reset(seed=42)
        cur = state
        for i in range(12):
            action = Action(agent_id="agent_0", action_type="wait" if i % 2 == 0 else "gather")
            t = engine.step(cur, action)
            store.append(t)
            cur = t.next_state

    result = runner.invoke(app, ["daemon", "--once", "--db-path", str(db_path), "--batch-size", "8"])
    assert result.exit_code == 0
    assert "Online training daemon step completed:" in result.stdout
    assert "Batch size processed: 8" in result.stdout
    assert "Total updates executed: 1" in result.stdout
    assert "JEPA representation variance:" in result.stdout
    assert "JEPA dimension health:" in result.stdout


def test_cli_daemon_once_empty(tmp_path: Path) -> None:
    db_path = tmp_path / "nonexistent_daemon.duckdb"
    result = runner.invoke(app, ["daemon", "--once", "--db-path", str(db_path)])
    assert result.exit_code == 0
    assert "No transitions available to process" in result.stdout


def test_cli_run_online_train(tmp_path: Path) -> None:
    db_path = tmp_path / "run_online.duckdb"
    result = runner.invoke(
        app,
        [
            "run",
            "--generations",
            "2",
            "--ticks-per-gen",
            "5",
            "--online-train",
            "--seed",
            "42",
            "--db-path",
            str(db_path),
        ],
    )
    assert result.exit_code == 0
    assert "Simulation completed successfully:" in result.stdout
    assert "Online training telemetry:" in result.stdout
    assert "Online training daemon updates:" in result.stdout
    assert "Online training last seq_no:" in result.stdout
    assert "Online training JEPA representation variance:" in result.stdout
    assert "Online training rehearsal buffer size:" in result.stdout
    assert db_path.exists()

