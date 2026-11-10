# Predictor integration

Authority: [Phase 2.1](../../phases/2.1-predictor.md).
Source package: `src/evolzen/predictor/`.

Predict behavior under partial observation, distinguishing hidden birth temperament, changing
activation, public actions and learned competence. Privileged access to drives is an oracle
baseline, not a realistic intent-inference result. A synthetic intent label is not ground truth
for real human intent. The agent's contextual EMA learner is separate from the system-level
predictor and does not implement the existing planner's neural training methods.
