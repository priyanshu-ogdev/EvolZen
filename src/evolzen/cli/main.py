"""CLI entry point: `evolzen run / train / evaluate / replay / inspect / ablate / cluster / serve`.

See src/evolzen/cli/README.md for the command-to-subsystem map. Registered as a console script
via [project.scripts] in pyproject.toml.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Annotated

import numpy as np
import typer

from evolzen.agents.development.lifecycle import stage_at
from evolzen.agents.development.motivation import sample_genome
from evolzen.agents.qd_archive import CVTArchive, QDArchiveEntry, compute_behavioral_descriptor
from evolzen.agents.scheduler import PopulationScheduler
from evolzen.cli.cluster import TargetNodeRole, diagnose_host_node, format_cluster_report
from evolzen.cli.dashboard import generate_dashboard_html
from evolzen.cli.server import EvolZenDashboardServer
from evolzen.economy.manuals import ManualStore
from evolzen.economy.metrics import compute_gini_coefficient
from evolzen.environment.engine import SocialSandboxEngine
from evolzen.evaluation.dual_track import DualTrackRunner
from evolzen.logging import configure_logging, logger
from evolzen.predictor.dynamics import WorldDynamicsPredictor
from evolzen.predictor.planner import Planner
from evolzen.predictor.rehearsal_buffer import RehearsalBuffer
from evolzen.recognition.ablations import AblationRunner
from evolzen.recognition.jepa import GroundedJEPAEncoder
from evolzen.schemas.agent_profile import AgentProfile
from evolzen.schemas.development import DevelopmentConfig, LifeStage
from evolzen.schemas.manual import ProvenanceCategory, ProvenanceRecord
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
    drought_interval: Annotated[int, typer.Option(help="Period (in ticks) between exogenous resource scarcity droughts. 0 disables.")] = 0,
    drought_severity: Annotated[float, typer.Option(help="Fractional severity [0.0, 1.0] of resource scarcity during drought.")] = 0.5,
) -> None:
    """Run the environment + agent-population loop (Phases 1.1-1.5)."""
    configure_logging(phase="1.x")
    logger.info(
        "Starting simulation run: generations={} ticks_per_gen={} seed={} run_id={} db_path={} drought_interval={} drought_severity={}",
        generations,
        ticks_per_gen,
        seed,
        run_id,
        db_path,
        drought_interval,
        drought_severity,
    )

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    dev_config = DevelopmentConfig(
        adolescence=15,
        adulthood=25,
        elderhood=200,
        lifespan=350,
    )
    manual_store = ManualStore(real_data_floor=0.2)
    prov = ProvenanceRecord.create(
        provenance_id="prov-crafting-recipe",
        category=ProvenanceCategory.HUMAN_AUTHORED,
        uri_or_source="seeds/crafting.md",
        description="Human-authored tool-crafting recipe",
    )
    manual_store.add_entry(
        situation_key="crafting",
        text="Gather wood and stone to craft specialized tools",
        category=ProvenanceCategory.HUMAN_AUTHORED,
        provenance=prov,
        written_by="human_expert",
    )

    with TransitionLogStore(db_path) as store:
        engine = SocialSandboxEngine(
            default_seed=seed,
            num_locations=4,
            num_agents=4,
            max_ticks=max(2000, (generations * ticks_per_gen * 16) + 1000),
            adulthood_age=dev_config.adulthood,
            lifespan=dev_config.lifespan,
        )
        init_state = engine.reset(
            seed=seed,
            run_id=run_id,
            adulthood_age=dev_config.adulthood,
            lifespan=dev_config.lifespan,
        )
        scheduler = PopulationScheduler(
            engine=engine,
            initial_state=init_state,
            config=dev_config,
            manual_store=manual_store,
            run_id=run_id,
            store=store,
        )

        total_transitions = 0
        total_births = 0
        total_deaths = 0
        total_teachings = 0
        all_metrics = []
        for gen in range(generations):
            metrics = scheduler.run_generation(
                steps=ticks_per_gen,
                seed=seed + gen,
                drought_interval=drought_interval,
                drought_severity=drought_severity,
            )
            all_metrics.append(metrics)
            total_transitions += metrics.total_transitions
            total_births += metrics.births
            total_deaths += metrics.deaths
            total_teachings += metrics.teachings
            logger.info(
                "Generation {} complete: world_tick={} transitions={} births={} deaths={} teachings={} living_agents={} drought_periods={}",
                gen + 1,
                metrics.ticks_elapsed,
                metrics.total_transitions,
                metrics.births,
                metrics.deaths,
                metrics.teachings,
                metrics.active_population,
                metrics.metadata.get("drought_periods", 0),
            )

        final_world = WorldState.from_state(scheduler.state)
        living_agents = [
            w_a for a_id, a in scheduler.agents.items()
            if stage_at(a.development, final_world.tick) != LifeStage.DEAD
            and (w_a := final_world.agents.get(a_id)) is not None
            and w_a.alive
        ]
        active_pop = len(living_agents)
        wealths = [float(a.currency + sum(a.inventory.values())) for a in living_agents]
        gini = compute_gini_coefficient(wealths) if wealths else 0.0
        active_lineages = len({a.lineage_id for a in living_agents})
        max_gen = max((a.generation for a in final_world.agents.values()), default=0)
        total_ticks = final_world.tick
        archive_cov = scheduler.archive.coverage()

        recipe_adoptions = sum(
            1 for a in scheduler.agents.values() for lesson in a.development.lessons if lesson.manual_entry is not None
        )

        gen_ginis = [float(m.metadata.get("final_gini", gini)) for m in all_metrics]
        gen_volatilities = [float(m.metadata.get("gini_volatility", 0.0)) for m in all_metrics]
        if len(gen_ginis) > 1:
            mean_gg = sum(gen_ginis) / len(gen_ginis)
            std_g = math.sqrt(sum((g - mean_gg) ** 2 for g in gen_ginis) / len(gen_ginis))
            gini_stability = max(0.0, round(1.0 - std_g, 4))
        else:
            mean_vol = sum(gen_volatilities) / len(gen_volatilities) if gen_volatilities else 0.0
            gini_stability = max(0.0, round(1.0 - mean_vol, 4))

        typer.echo(
            f"Simulation completed successfully:\n"
            f"  Total generations: {generations}\n"
            f"  World ticks: {total_ticks}\n"
            f"  Transitions logged: {total_transitions}\n"
            f"  Births: {total_births}\n"
            f"  Deaths: {total_deaths}\n"
            f"  Teachings: {total_teachings}\n"
            f"  Active population: {active_pop}\n"
            f"  Wealth Gini coefficient: {gini:.4f}\n"
            f"  Active lineages: {active_lineages}\n"
            f"  Max generation reached: {max_gen}\n"
            f"  CVTArchive coverage: {archive_cov}\n"
            f"  Drought interval: {drought_interval}\n"
            f"  Drought severity: {drought_severity:.2f}\n"
            f"  Cultural retention (recipe adoptions in ManualStore): {recipe_adoptions}\n"
            f"  Gini stability under drought: {gini_stability:.4f}"
        )


@app.command()
def train(
    steps: Annotated[int, typer.Option(help="Number of planner GRPO training steps.")] = 5,
    batch_size: Annotated[int, typer.Option(help="Batch size per training step.")] = 4,
    replay_ratio: Annotated[float, typer.Option(help="CLEAR replay ratio [0.0, 1.0].")] = 0.5,
    seed: Annotated[int, typer.Option(help="Training seed.")] = 42,
    db_path: Annotated[Path, typer.Option(help="Path to DuckDB transition store.")] = Path("data/transitions.duckdb"),
) -> None:
    """Run the grounded-predictor / recognition-model training loop (Phases 2.1, 2.3)."""
    configure_logging(phase="2.1")
    logger.info(
        "Training requested: steps={} batch_size={} replay_ratio={} seed={} db_path={}",
        steps,
        batch_size,
        replay_ratio,
        seed,
        db_path,
    )

    transitions: list[Transition] = []
    source: str = "engine bootstrap"
    if db_path.exists():
        try:
            with TransitionLogStore(db_path) as store:
                if store.count() > 0:
                    transitions = store.list_transitions()
                    source = f"DuckDB ({db_path})"
        except Exception as exc:
            logger.warning("Could not read transitions from {}: {}", db_path, exc)

    if not transitions:
        source = "engine bootstrap"
        engine = SocialSandboxEngine(default_seed=seed, num_locations=2, num_agents=2, max_ticks=100)
        state = engine.reset(seed=seed)
        cur_state = state
        for i in range(max(batch_size * 2, 8)):
            action = Action(agent_id="agent_0", action_type="wait" if i % 2 == 0 else "gather")
            t = engine.step(cur_state, action)
            transitions.append(t)
            cur_state = t.next_state

    rehearsal_buffer = RehearsalBuffer(capacity=100)
    predictor = WorldDynamicsPredictor()
    planner = Planner(dynamics=predictor, rehearsal_buffer=rehearsal_buffer, lr=0.05)
    jepa = GroundedJEPAEncoder(seed=seed)

    last_planner_metrics: dict[str, float] = {}

    for step in range(steps):
        start_idx = (step * batch_size) % len(transitions)
        end_idx = start_idx + batch_size
        if end_idx <= len(transitions):
            batch = transitions[start_idx:end_idx]
        else:
            batch = transitions[start_idx:] + transitions[: end_idx % len(transitions)]

        last_planner_metrics = planner.train_step(batch, replay_ratio=replay_ratio)
        jepa.train_step([t.state for t in batch])
        predictor.train_batch(batch)

    # JEPA representation variance and dimension health across transitions
    sample_size = min(len(transitions), 64)
    sample_stride = max(1, len(transitions) // sample_size)
    sample_states = [t.state for t in transitions[::sample_stride][:sample_size]]
    if len(sample_states) > 1:
        encoded = np.asarray([jepa.encode(s) for s in sample_states], dtype=np.float32)
        dim_vars = np.var(encoded, axis=0)
        jepa_rep_var = float(np.mean(dim_vars))
        active_dims = int(np.sum(dim_vars > 1e-4))
    else:
        jepa_rep_var = 0.0
        active_dims = 0

    typer.echo(
        f"Training complete:\n"
        f"  Transitions source: {source}\n"
        f"  Transitions count: {len(transitions)}\n"
        f"  Total GRPO updates executed: {planner.update_count}\n"
        f"  Final step loss: {last_planner_metrics.get('loss', 0.0):.4f}\n"
        f"  Policy entropy: {last_planner_metrics.get('policy_entropy', 0.0):.4f}\n"
        f"  JEPA representation variance: {jepa_rep_var:.6f}\n"
        f"  JEPA dimension health: {active_dims}/{jepa.embedding_dim} active dimensions\n"
        f"  Rehearsal buffer size: {len(rehearsal_buffer)}"
    )


@app.command()
def evaluate(
    rounds: Annotated[int, typer.Option(help="Number of held-out fresh evaluation rounds.")] = 4,
    persistent_ticks: Annotated[int, typer.Option(help="Number of persistent-track ticks.")] = 20,
    seed: Annotated[int, typer.Option(help="Evaluation seed.")] = 42,
    use_planner: Annotated[
        bool,
        typer.Option("--use-planner/--no-use-planner", help="Enable model-based policy rollout planner."),
    ] = False,
    planning_horizon: Annotated[
        int,
        typer.Option(help="Lookahead horizon for model-based rollout."),
    ] = 3,
    db_path: Annotated[Path, typer.Option(help="Path to DuckDB transition store.")] = Path("data/transitions.duckdb"),
) -> None:
    """Run held-out dual-track generalization testing (Phases 2.4-2.5)."""
    configure_logging(phase="2.4")
    logger.info(
        "Evaluation requested: rounds={} persistent_ticks={} seed={} use_planner={} planning_horizon={}",
        rounds,
        persistent_ticks,
        seed,
        use_planner,
        planning_horizon,
    )

    planner: Planner | None = None
    if use_planner:
        rehearsal_buffer = RehearsalBuffer(capacity=500)
        predictor = WorldDynamicsPredictor()
        planner = Planner(dynamics=predictor, rehearsal_buffer=rehearsal_buffer, lr=0.05)
        transitions: list[Transition] = []
        if db_path.exists():
            try:
                with TransitionLogStore(db_path) as store:
                    if store.count() > 0:
                        transitions = store.list_transitions()[:100]
            except Exception as exc:
                logger.warning("Could not load transitions for planner from {}: {}", db_path, exc)

        if not transitions:
            bootstrap_engine = SocialSandboxEngine(default_seed=seed, num_locations=2, num_agents=2, max_ticks=40)
            b_state = bootstrap_engine.reset(seed=seed)
            for i in range(16):
                b_action = Action(agent_id="agent-0", action_type="gather" if i % 2 == 0 else "wait")
                b_trans = bootstrap_engine.step(b_state, b_action)
                transitions.append(b_trans)
                b_state = b_trans.next_state

        planner.train_step(transitions)

    runner = DualTrackRunner(seed=seed)
    report = runner.run_full_evaluation(
        persistent_ticks=persistent_ticks,
        fresh_rounds=rounds,
        planner=planner,
        planning_horizon=planning_horizon,
    )

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
        if f.planner_enabled:
            typer.echo(f"  model-based planning: ENABLED (horizon={f.planning_horizon})")
            if f.baseline_eae_score is not None:
                typer.echo(f"  baseline EAE without planner: {f.baseline_eae_score:.4f}")
                typer.echo(f"  planning efficiency delta: {f.mean_eae_score - f.baseline_eae_score:+.4f}")
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
    export_html: Annotated[Path | None, typer.Option(help="Path to export interactive HTML5 visualization dashboard.")] = None,
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

    for a_id, a_state in world.agents.items():
        a_profile = AgentProfile(
            agent_id=a_id,
            lineage_id=a_state.lineage_id,
            adopted_norms=tuple(a_state.adopted_norms),
            institutional_affiliations=tuple(a_state.institution_ids),
        )
        a_genome = sample_genome(seed + (hash(a_id) % 1000))
        a_desc = compute_behavioral_descriptor(a_genome, a_profile, dimension=5)
        archive.consider(
            QDArchiveEntry(
                agent_id=a_id,
                profile=a_profile,
                behavioral_descriptor=a_desc,
                fitness=float(a_state.currency + 10.0),
            )
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

    if export_html is not None:
        dashboard_content = generate_dashboard_html(world, archive, gini, desc)
        export_html.parent.mkdir(parents=True, exist_ok=True)
        export_html.write_text(dashboard_content, encoding="utf-8")
        typer.echo(f"Dashboard exported to: {export_html}")


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


@app.command()
def cluster(
    role: Annotated[
        TargetNodeRole,
        typer.Option(
            help="Target cluster node role to diagnose (dgx_spark, jetson_agx, rtx_a6000, standalone).",
            case_sensitive=False,
        ),
    ] = TargetNodeRole.STANDALONE,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output diagnostics in structured JSON format.",
        ),
    ] = False,
    address: Annotated[
        str | None,
        typer.Option(
            help="Ray cluster head node address (e.g. 'auto' or 'ray://IP:10001').",
        ),
    ] = None,
    export_json: Annotated[
        Path | None,
        typer.Option(
            help="Path to export cluster diagnostic JSON.",
        ),
    ] = None,
) -> None:
    """Pre-flight hardware diagnostics & cluster topology activation (Horizon 4)."""
    configure_logging(phase="cluster")
    logger.info("Host cluster pre-flight diagnostic requested: role={} address={}", role.value, address)
    diag = diagnose_host_node(role=role, ray_address=address)
    if export_json is not None:
        export_json.parent.mkdir(parents=True, exist_ok=True)
        export_json.write_text(json.dumps(diag, indent=2), encoding="utf-8")
        typer.echo(f"Cluster diagnostics exported to: {export_json}")

    if json_output:
        typer.echo(json.dumps(diag, indent=2))
    else:
        report = format_cluster_report(diag)
        typer.echo(report)


@app.command()
def serve(
    port: Annotated[int, typer.Option(help="Port to bind server to.")] = 8000,
    host: Annotated[str, typer.Option(help="Host interface.")] = "127.0.0.1",
    db_path: Annotated[Path, typer.Option(help="Path to DuckDB transition store.")] = Path("data/transitions.duckdb"),
    poll_interval: Annotated[float, typer.Option(help="Polling interval in seconds for SSE tailing.")] = 1.0,
    once: Annotated[bool, typer.Option(help="Serve status once and exit (for CI/diagnostics).")] = False,
) -> None:
    """Launch the live real-time dashboard and transition event streaming server (Frontier 3)."""
    configure_logging(phase="serve")
    logger.info("Dashboard server requested on {}:{} (db: {}, poll: {}s)", host, port, db_path, poll_interval)
    server = EvolZenDashboardServer(
        host=host,
        port=port,
        db_path=db_path,
        poll_interval=poll_interval,
    )
    if once:
        server.start(background=True)
        try:
            status = server.get_status()
            typer.echo(json.dumps(status, indent=2))
        finally:
            server.stop()
        return

    typer.echo(f"Serving EvolZen real-time dashboard at http://{host}:{port}/ (Ctrl+C to quit)")
    try:
        server.start(background=False)
    except KeyboardInterrupt:
        typer.echo("\nServer stopped.")
    finally:
        server.stop()


if __name__ == "__main__":
    app()
