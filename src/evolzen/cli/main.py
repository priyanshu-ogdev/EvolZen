"""CLI entry point: `evolzen run / train / evaluate / replay / inspect / ablate`.

See src/evolzen/cli/README.md for the command-to-subsystem map. Registered as a console script
via [project.scripts] in pyproject.toml.
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from evolzen.agents.development.motivation import sample_genome
from evolzen.agents.qd_archive import CVTArchive, compute_behavioral_descriptor
from evolzen.agents.scheduler import PopulationScheduler
from evolzen.economy.metrics import compute_gini_coefficient
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.evaluation.dual_track import DualTrackRunner
from evolzen.logging import configure_logging, logger
from evolzen.predictor.planner import Planner
from evolzen.predictor.rehearsal_buffer import RehearsalBuffer
from evolzen.recognition.ablations import AblationRunner
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.transition import Action, Transition
from evolzen.schemas.world import WorldState
from evolzen.storage.transition_log import TransitionLogStore

app = typer.Typer(
    help="EvolZen — a grounded, evolutionarily-diverse, continually-learning multi-agent observer.",
    no_args_is_help=True,
)


@app.command()
def run(
    generations: Annotated[int, typer.Option(help="Number of agent-population generations/cycles to run.")] = 5,
    ticks_per_gen: Annotated[int, typer.Option(help="Number of environment ticks per generation cycle.")] = 4,
    seed: Annotated[int, typer.Option(help="Simulation PRNG seed.")] = 42,
    run_id: Annotated[str, typer.Option(help="Unique run identifier.")] = "cli-run",
    db_path: Annotated[Path, typer.Option(help="Path to DuckDB transition store.")] = Path("data/transitions.duckdb"),
) -> None:
    """Run the environment + agent-population loop (Phases 1.1-1.5)."""
    configure_logging(phase="1.x")
    logger.info(
        "Starting simulation run: generations={} ticks_per_gen={} seed={} run_id={} db_path={}",
        generations,
        ticks_per_gen,
        seed,
        run_id,
        db_path,
    )

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with TransitionLogStore(db_path) as store:
        engine = SocialSandboxEngine(
            default_seed=seed,
            num_locations=4,
            num_agents=4,
            max_ticks=max(2000, (generations * ticks_per_gen * 16) + 1000),
        )
        init_state = engine.reset(seed=seed, run_id=run_id)
        scheduler = PopulationScheduler(
            engine=engine,
            initial_state=init_state,
            run_id=run_id,
            store=store,
        )

        total_transitions = 0
        for gen in range(generations):
            metrics = scheduler.run_generation(steps=ticks_per_gen, seed=seed + gen)
            total_transitions += metrics.total_transitions
            logger.info(
                "Generation {} complete: world_tick={} transitions={} living_agents={}",
                gen + 1,
                metrics.ticks_elapsed,
                metrics.total_transitions,
                metrics.active_population,
            )

        final_world = WorldState.from_state(scheduler.state)
        living_agents = [a for a in final_world.agents.values() if a.alive]
        active_pop = len(living_agents)
        wealths = [float(a.currency + sum(a.inventory.values())) for a in living_agents]
        gini = compute_gini_coefficient(wealths) if wealths else 0.0
        active_lineages = len({a.lineage_id for a in living_agents})
        total_ticks = final_world.tick

        typer.echo(
            f"Simulation completed successfully:\n"
            f"  Total generations: {generations}\n"
            f"  World ticks: {total_ticks}\n"
            f"  Transitions logged: {total_transitions}\n"
            f"  Active population: {active_pop}\n"
            f"  Wealth Gini coefficient: {gini:.4f}\n"
            f"  Active lineages: {active_lineages}\n"
            f"  Lineages active: {scheduler.archive.coverage()}"
        )


@app.command()
def train(
    steps: Annotated[int, typer.Option(help="Number of planner GRPO training steps.")] = 5,
    batch_size: Annotated[int, typer.Option(help="Batch size per training step.")] = 4,
    replay_ratio: Annotated[float, typer.Option(help="CLEAR replay ratio [0.0, 1.0].")] = 0.5,
    seed: Annotated[int, typer.Option(help="Training seed.")] = 42,
) -> None:
    """Run the grounded-predictor / recognition-model training loop (Phases 2.1, 2.3)."""
    configure_logging(phase="2.1")
    logger.info("Training requested: steps={} batch_size={} replay_ratio={}", steps, batch_size, replay_ratio)

    engine = SocialSandboxEngine(default_seed=seed, num_locations=2, num_agents=2, max_ticks=100)
    state = engine.reset(seed=seed)

    # Generate bootstrap training transitions
    transitions: list[Transition] = []
    cur_state = state
    for i in range(max(batch_size * 2, 8)):
        action = Action(agent_id="agent_0", action_type="wait" if i % 2 == 0 else "gather")
        t = engine.step(cur_state, action)
        transitions.append(t)
        cur_state = t.next_state

    rehearsal_buffer = RehearsalBuffer(capacity=100)
    planner = Planner(rehearsal_buffer=rehearsal_buffer, lr=0.05)

    last_metrics: dict[str, float] = {}
    for _step in range(steps):
        batch = transitions[:batch_size]
        last_metrics = planner.train_step(batch, replay_ratio=replay_ratio)

    typer.echo(
        f"Training complete:\n"
        f"  Updates executed: {planner.update_count}\n"
        f"  Final step loss: {last_metrics.get('loss', 0.0):.4f}\n"
        f"  Policy entropy: {last_metrics.get('policy_entropy', 0.0):.4f}\n"
        f"  Rehearsal buffer size: {len(rehearsal_buffer)}"
    )


@app.command()
def evaluate(
    rounds: Annotated[int, typer.Option(help="Number of held-out fresh evaluation rounds.")] = 4,
    persistent_ticks: Annotated[int, typer.Option(help="Number of persistent-track ticks.")] = 20,
    seed: Annotated[int, typer.Option(help="Evaluation seed.")] = 42,
) -> None:
    """Run held-out dual-track generalization testing (Phases 2.4-2.5)."""
    configure_logging(phase="2.4")
    logger.info("Evaluation requested: rounds={} persistent_ticks={} seed={}", rounds, persistent_ticks, seed)

    runner = DualTrackRunner(seed=seed)
    report = runner.run_full_evaluation(persistent_ticks=persistent_ticks, fresh_rounds=rounds)

    typer.echo("=================================================")
    typer.echo("          EVOLZEN EVALUATION REPORT               ")
    typer.echo("=================================================")
    if report.persistent_result is not None:
        p = report.persistent_result
        typer.echo("Track 1 (Persistent World):")
        typer.echo(f"  ticks: {p.total_ticks}")
        typer.echo(f"  survival ratio: {p.living_agents_ratio:.4f}")
        typer.echo(f"  invariant violations: {0 if p.invariants_passed else 1}")
        typer.echo(f"  cumulative growth events: {p.growth_events_count}")
        typer.echo(f"  gini inequality: {p.gini_coefficient:.4f}")
        typer.echo(f"  active capabilities: {p.capabilities_count}")
        typer.echo(f"  artifact count: {p.artifact_count}")
        typer.echo("")
    if report.fresh_result is not None:
        f = report.fresh_result
        typer.echo("Track 2 (Held-out Fresh Worlds):")
        typer.echo(f"  rounds: {f.rounds_evaluated}")
        typer.echo(f"  average EAE_B action efficiency: {f.mean_eae_score:.4f}")
        typer.echo(f"  fresh solve rate: {f.solve_rate:.4f}")
        typer.echo(f"  reused world score: {f.reused_env_score:.4f}")
        typer.echo(f"  generalization gap (EAE_reused - EAE_fresh): {f.reused_vs_fresh_score_gap:.4f}")
        typer.echo("")
    typer.echo("Calibration & Benchmark References:")
    typer.echo(report.summary())
    typer.echo("=================================================")


@app.command()
def replay(
    db_path: Annotated[Path, typer.Option(help="Path to DuckDB transition store.")] = Path("data/transitions.duckdb"),
    run_id: Annotated[str | None, typer.Option(help="Filter by specific run_id.")] = None,
) -> None:
    """Hermetically verify and replay transition logs from DuckDB storage."""
    configure_logging(phase="1.1")
    if not db_path.exists():
        typer.echo(f"Transition log file not found at: {db_path}", err=True)
        raise typer.Exit(code=1)

    with TransitionLogStore(db_path) as store:
        count = store.count(run_id=run_id)
        integrity = store.verify_integrity()
        typer.echo(
            f"Transition Log Replay Verification:\n"
            f"  Database path: {db_path}\n"
            f"  Transitions logged: {count}\n"
            f"  SHA-256 Hash Chain Integrity: {'VERIFIED' if integrity else 'CORRUPTED'}"
        )


@app.command()
def inspect(
    seed: Annotated[int, typer.Option(help="Seed to inspect default world layout.")] = 42,
    num_agents: Annotated[int, typer.Option(help="Number of agents in inspect world.")] = 4,
    num_locations: Annotated[int, typer.Option(help="Number of locations.")] = 4,
) -> None:
    """Query CVTArchive diversity and economy health indicators."""
    configure_logging(phase="1.2")
    engine = SocialSandboxEngine(default_seed=seed, num_locations=num_locations, num_agents=num_agents)
    state = engine.reset(seed=seed)
    world = WorldState.from_state(state)

    archive = CVTArchive.uniform_hypercube(num_centroids=10, dimensions=5, seed=seed)
    genome = sample_genome(seed)
    profile = AgentProfile(agent_id="agent_0", lineage_id="lineage_0")
    desc = compute_behavioral_descriptor(
        genome=genome,
        profile=profile,
        dimension=5,
    )

    wealths = [a.currency for a in world.agents.values()]
    gini = compute_gini_coefficient(wealths) if wealths else 0.0

    typer.echo(
        f"EvolZen System State Inspection (Seed={seed}):\n"
        f"  World Version: {world.world_version}\n"
        f"  Agents Registered: {len(world.agents)}\n"
        f"  Locations: {len(world.locations)}\n"
        f"  Gini Inequality: {gini:.4f}\n"
        f"  CVT Archive Centroid Niches: {archive.total_niches()}\n"
        f"  Founder Agent Behavioral Descriptor: {[round(v, 3) for v in desc]}"
    )


@app.command()
def ablate(
    db_path: Annotated[Path, typer.Option(help="Path to DuckDB transition store.")] = Path("data/transitions.duckdb"),
    steps: Annotated[int, typer.Option(help="Number of transitions to evaluate in ablation matrix.")] = 50,
    seed: Annotated[int, typer.Option(help="PRNG seed.")] = 42,
    output: Annotated[Path | None, typer.Option(help="Optional path to output Markdown report.")] = None,
) -> None:
    """Benchmark the pre-registered 4-cell recognition ablation matrix (Phase 2.3)."""
    configure_logging(phase="2.3")
    logger.info("Recognition ablation benchmark requested: steps={} seed={} db_path={}", steps, seed, db_path)

    transitions: list[Transition] = []
    if db_path.exists():
        with TransitionLogStore(db_path) as store:
            loaded = store.list_transitions()
            if loaded:
                transitions = loaded[:steps]

    if not transitions:
        engine = SocialSandboxEngine(
            default_seed=seed,
            num_locations=2,
            num_agents=2,
            max_ticks=max(2000, (steps * 2) + 100),
        )
        cur_state = engine.reset(seed=seed)
        for i in range(steps):
            action = Action(agent_id="agent_0", action_type="wait" if i % 2 == 0 else "gather")
            t = engine.step(cur_state, action)
            transitions.append(t)
            cur_state = t.next_state

    runner = AblationRunner(seed=seed)
    matrix = runner.run_full_matrix(transitions)
    report = runner.format_report(matrix)
    typer.echo(report)

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")


if __name__ == "__main__":
    app()
