"""CLI entry point: `evolzen run / train / evaluate`.

See src/evolzen/cli/README.md for the command-to-subsystem map. Registered as a console script
via [project.scripts] in pyproject.toml.
"""
from __future__ import annotations

import typer

app = typer.Typer(help="EvolZen — a grounded, evolutionarily-diverse, continually-learning multi-agent observer.")


@app.command()
def run(generations: int = typer.Option(5, help="Number of agent-population generations to run.")) -> None:
    """Run the environment + agent-population loop (Phases 1.1-1.5)."""
    from evolzen.config import EvolZenSettings
    from evolzen.logging import configure_logging, logger

    configure_logging(phase="1.x")
    settings = EvolZenSettings()
    logger.info(
        "Run requested: generations={} device={} population_size={}",
        generations, settings.agents.device, settings.agents.population_size,
    )
    raise NotImplementedError(
        "Wire this up once Phase 1.1's environment domain is chosen and "
        "evolzen.environment.engine.Environment has a concrete implementation."
    )


@app.command()
def train(steps: int = typer.Option(1000, help="Number of planner training steps.")) -> None:
    """Run the grounded-predictor / recognition-model training loop (Phases 2.1, 2.3)."""
    from evolzen.config import EvolZenSettings
    from evolzen.logging import configure_logging, logger

    configure_logging(phase="2.1")
    settings = EvolZenSettings()
    logger.info("Training requested: steps={} device={}", steps, settings.predictor.device)
    raise NotImplementedError("Wire this up once evolzen.predictor.planner.Planner is implemented.")


@app.command()
def evaluate(rounds: int = typer.Option(10, help="Number of held-out evaluation rounds.")) -> None:
    """Run held-out generalization testing (Phase 2.4)."""
    from evolzen.config import EvolZenSettings
    from evolzen.logging import configure_logging, logger

    configure_logging(phase="2.4")
    settings = EvolZenSettings()
    logger.info(
        "Evaluation requested: rounds={} ablation={}",
        rounds, settings.recognition.ablation_enabled,
    )
    raise NotImplementedError(
        "Wire this up once evolzen.evaluation.procedural_env_gen is implemented."
    )


if __name__ == "__main__":
    app()
