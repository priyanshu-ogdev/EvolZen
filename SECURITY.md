# Security

## Scope

This is a research codebase, not a deployed service. The security concerns that do apply are
specific to this project's architecture.

## Containment is not optional, including in development

`evolzen.agents` is both **self-modifying** (Phase 1.2's Darwin-Gödel-Machine-style proposals)
and, via `evolzen.exploration` / `evolzen.library`, produces **executable code**. Any code
originating from either source — even a two-line toy example — must execute inside
`evolzen.containment.Sandbox`, never directly in the host Python process. This is structural,
not a suggestion. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §7 and
[ADR 0002](docs/adr/0002-dependency-stack-and-optional-extras.md).

`evolzen.containment.Sandbox` is an **interface only** — it assumes a Firecracker-microVM- or
gVisor-backed executor provisioned on the DGX Spark. Do not merge an implementation backed by a
plain subprocess call or a bare container with a shared kernel.

## Dependency supply chain

`uv.lock` pins exact resolved versions for every dependency — do not hand-edit it. Re-resolve
with `uv lock --upgrade` on a deliberate, reviewed cadence.

## Reporting a concern

No dedicated security contact or bug bounty. If you find a containment-boundary issue, open an
issue tagged `security` rather than a public PR with exploit details.

## Data handling

Transition logs, manuals, and checkpoints (`data/`, `checkpoints/`, `runs/`) are excluded from
version control by default. None of this project's environments are designed to process
personal data; revisit this section if the Phase 1.1 domain choice changes that.
