"""EvolZen — a grounded, evolutionarily-diverse, continually-learning multi-agent observer.

Concept-research testbed for measuring generalization efficiency on genuinely novel tasks — not
an AGI claim. See docs/PRD.md and docs/ARCHITECTURE.md for the full design.

This package is organized as nine subsystems (matching the ten phases in the research design;
predictor covers 2.1, containment 2.2, recognition 2.3, evaluation covers both 2.4 and 2.5) on
top of a shared foundation (config, logging, tracking, schemas, storage) defined directly in
this top-level package.
"""

__version__ = "0.1.0"
