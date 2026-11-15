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


def test_cli_train() -> None:
    result = runner.invoke(app, ["train", "--steps", "2", "--batch-size", "2", "--seed", "42"])
    assert result.exit_code == 0
    assert "Training complete" in result.stdout
    assert "Updates executed: 2" in result.stdout


def test_cli_evaluate() -> None:
    result = runner.invoke(app, ["evaluate", "--rounds", "2", "--persistent-ticks", "5", "--seed", "42"])
    assert result.exit_code == 0
    assert "EVOLZEN EVALUATION REPORT" in result.stdout
    assert "Held-out RHAE score:" in result.stdout
    assert "Reused-vs-fresh score gap:" in result.stdout


def test_cli_inspect() -> None:
    result = runner.invoke(app, ["inspect", "--seed", "42", "--num-agents", "2"])
    assert result.exit_code == 0
    assert "EvolZen System State Inspection" in result.stdout
    assert "Gini Inequality:" in result.stdout
    assert "Founder Agent Behavioral Descriptor:" in result.stdout


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
