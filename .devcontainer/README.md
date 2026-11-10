# .devcontainer/

A reproducible dev environment (VS Code Dev Containers / GitHub Codespaces) so every
contributor and CI build against the same base image and Python version.

- **VS Code:** Command Palette -> "Dev Containers: Reopen in Container."
- **GitHub Codespaces:** "Code" -> "Codespaces" -> "Create codespace on main."
- **Manually:** `docker build -f .devcontainer/Dockerfile -t evolzen-dev .` then
  `docker run -it -v $(pwd):/workspace evolzen-dev bash`.

Installs `uv` and runs `uv sync` on creation — base, CPU-friendly dependencies only. Does not
install the `gpu` extra; that requires the actual AGX Spark / DGX Spark hardware.
