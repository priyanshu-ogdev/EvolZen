# Target Rig & Hardware Deployment Guide

This document provides deployment, configuration, and operational procedures for deploying EvolZen
on physical target hardware: the **DGX Spark**, the **Jetson AGX Spark**, and the **RTX A6000**.

> [!IMPORTANT]
> **Safety and Sandboxing Boundary (`AGENTS.md` Rule #1)**:
> Agent-generated code and self-modifications from `evolzen.exploration.synthesizer`,
> `evolzen.library`, and `evolzen.agents.self_modification` **must never execute outside
> `evolzen.containment.GVisorSandbox`**. A standard kernel-sharing container (Docker/Podman without
> gVisor) is insufficient. Verify `runsc` availability before launching any exploration run.

> [!NOTE]
> **Empirical Disclosure (`AGENTS.md` Rules #4 and #5)**:
> Multi-thousand-tick persistent simulation runs and live GPU-accelerated inference remain
> unmeasured until physical execution on the target hardware documented below. Passing unit tests
> does not constitute empirical benchmark validation.

---

## 1. Hardware Topology & Subsystem Allocation

EvolZen allocates subsystem responsibilities across three physical machines to balance memory
bandwidth, compute density, and security isolation:

| Rig | Architecture & Specs | Subsystems Allocated | Primary Role |
|---|---|---|---|
| **DGX Spark** | Linux x86_64, High-memory multi-core host | `environment`, `economy`, `exploration`, `library`, `containment` | Environment engine (Moore machine), DuckDB transition log with SHA-256 hash chains, market clearing, rule library storage, capability verifier, and gVisor containment coordinator. |
| **Jetson AGX Spark** | Linux aarch64 (JetPack / Orin), 32–64GB Unified Memory | `agents` | Population scheduler (10–30 agents), Ray worker, structured LLM inference (`VLLMBackend` / `TransformersBackend`), 8-drive developmental decision policies. |
| **RTX A6000** | Linux x86_64, 48GB GDDR6 VRAM, Ampere architecture | `predictor`, `recognition`, `evaluation` | Grounded world model predictor training (GRPO/PPO), CLEAR rehearsal buffer, Grounded JEPA representation learning (VICReg/LeJEPA), DreamCoder Wake-Sleep MDL compression, and dual-track evaluation harness. |

---

## 2. Environment Setup & uv GPU Profile

EvolZen uses `uv` with a single lockfile. The project maintains mutually exclusive compute profiles
(`cpu` vs `gpu`) to prevent CUDA/CPU wheel version drift (see [ADR 0002](adr/0002-dependency-stack-and-optional-extras.md)).

### 2.1 Host Prerequisites

- **OS**: Ubuntu 22.04 LTS or 24.04 LTS (x86_64 or aarch64).
- **Python**: `>=3.11,<3.13` (installed automatically via `uv`).
- **NVIDIA Driver**: `>=535.xx` (JetPack 6.x on Jetson AGX Spark, CUDA 12.4+ driver on DGX/A6000).
- **uv**: Latest release (`curl -LsSf https://astral.sh/uv/install.sh | sh`).

### 2.2 Installing with the GPU Extra

On all GPU-equipped targets (DGX Spark, Jetson AGX Spark, RTX A6000), synchronize the environment
with the `gpu` extra:

```bash
# Clone the repository
git clone https://github.com/priyanshu-ogdev/EvolZen.git
cd EvolZen

# Sync dependencies with GPU extras (vllm, deepspeed, bitsandbytes, flash-attn, faiss-gpu)
uv sync --extra gpu
```

> [!WARNING]
> Do **not** install `--extra cpu` and `--extra gpu` in the same environment. Never hand-edit
> `uv.lock`; regenerate with `uv lock` if dependency ranges change in `pyproject.toml`.

---

## 3. gVisor (`runsc`) Sandboxing Setup

`evolzen.containment.GVisorSandbox` requires Google gVisor's `runsc` runtime binary to isolate
untrusted agent code. The sandbox uses `runsc do` to construct default-deny, hardware-isolated
execution boundaries with strict wall-clock timeouts (default: 2.0s) and memory caps (default: 128MB).

### 3.1 Installing `runsc` on Ubuntu / Debian (DGX Spark & RTX A6000)

```bash
# Install gVisor signing key and repository
sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates curl gnupg
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null

# Install runsc package
sudo apt-get update && sudo apt-get install -y runsc

# Verify installation
runsc --version
```

### 3.2 Installing `runsc` on Jetson AGX Spark (aarch64)

The official Google gVisor APT repository provides aarch64 binaries. If your package manager
fails to locate the arm64 binary, download the standalone release:

```bash
ARCH=$(uname -m)
URL="https://storage.googleapis.com/gvisor/releases/release/latest/${ARCH}"
curl -fsSL "${URL}/runsc" -o runsc
curl -fsSL "${URL}/runsc.sha512" -o runsc.sha512
sha512sum -c runsc.sha512
chmod +x runsc
sudo mv runsc /usr/local/bin/
runsc --version
```

### 3.3 Validating gVisor Availability in EvolZen

Verify that EvolZen detects `runsc` and can execute an isolated payload:

```bash
uv run python -c "from evolzen.containment import is_gvisor_available, GVisorSandbox; assert is_gvisor_available(); res = GVisorSandbox().run('print(1 + 1)'); assert res.is_success and res.stdout.strip() == '2'; print('gVisor validation succeeded!')"
```

Run the containment test suite:

```bash
uv run pytest tests/containment/test_sandbox.py -v
```

---

## 4. vLLM Engine Configuration (`VLLMBackend`)

`evolzen.agents.inference.VLLMBackend` serves structured action generation for 10–30 live agents
using continuous batching, PagedAttention, and schema-guided decoding.

### 4.1 Backend Architecture & Guarantees

- **Guided JSON Decoding**: Constrains generation to output valid JSON matching `evolzen.schemas.transition.Action`.
- **Action Type Verification**: Every generated action is validated against `evolzen.schemas.world.ActionType` (`wait`, `gather`, `move`, `consume`, `craft`, `trade`, `propose_contract`, etc.).
- **Deterministic Safe Fallback**: If vLLM raises an engine exception (e.g. CUDA OOM), outputs unparseable text, returns an unauthorized `action_type`, or mismatches `agent_id`, `VLLMBackend` falls through to the highest-priority permitted candidate from `evolzen.environment.adapter.action_from_candidate`.

### 4.2 Configuration Parameters

`VLLMBackend` accepts engine kwargs passed directly to `vllm.LLM`:

```python
from evolzen.agents.inference import VLLMBackend

backend = VLLMBackend(
    model_id="Qwen/Qwen2.5-0.5B-Instruct",
    tensor_parallel_size=1,            # 1 for Jetson AGX or single GPU; >1 for multi-GPU
    gpu_memory_utilization=0.70,       # Fraction of GPU memory allocated to vLLM
    max_model_len=1024,                # Bounded context window for agent decision prompts
    trust_remote_code=True,
)
```

### 4.3 Rig-Specific vLLM Optimization Guidelines

#### Jetson AGX Spark (Orin 32GB/64GB Unified Memory)
- **Memory Utilization**: Set `gpu_memory_utilization=0.60`–`0.70`. Because CPU and GPU share physical RAM on Jetson, leaving 30–40% unallocated ensures the OS, Ray runtime, and DuckDB transition store do not trigger out-of-memory kernel kills.
- **Quantization**: For larger models (e.g., 3B or 7B parameters), enable 4-bit or 8-bit quantization via AWQ or bitsandbytes:
  ```python
  backend = VLLMBackend(
      model_id="Qwen/Qwen2.5-3B-Instruct",
      quantization="bitsandbytes",
      load_format="bitsandbytes",
      gpu_memory_utilization=0.65,
  )
  ```
- **Concurrency**: Target 10–15 concurrent agent streams with continuous batching.

#### RTX A6000 (48GB GDDR6 VRAM)
- **High Throughput**: Full FP16/BF16 precision for 0.5B–8B models without quantization degradation.
- **Batching & Context**: Can comfortably set `gpu_memory_utilization=0.85` and `max_model_len=2048` to support the entire 30-agent population with near-zero latency overhead.
- **Multi-GPU Tensor Parallelism**: If pairing multiple A6000 GPUs, set `tensor_parallel_size=2` or `tensor_parallel_size=4`.

---

## 5. Distributed Orchestration with Ray

EvolZen utilizes Ray (`ray[default]>=2.38`) to orchestrate the 10–30 agent population across
compute nodes.

### 5.1 Starting the Ray Cluster

1. **On the DGX Spark (Cluster Head)**:
   ```bash
   ray start --head --port=6379 --dashboard-host=0.0.0.0 --num-cpus=32
   ```

2. **On the Jetson AGX Spark (Inference Worker)**:
   ```bash
   ray start --address='<DGX_SPARK_IP>:6379' --num-gpus=1 --resources='{"jetson_inference": 1}'
   ```

3. **On the RTX A6000 (Learning Worker)**:
   ```bash
   ray start --address='<DGX_SPARK_IP>:6379' --num-gpus=1 --resources='{"a6000_training": 1}'
   ```

### 5.2 Checking Cluster Status

```bash
ray status
```

---

## 6. Pre-Flight Verification & Smoke-Test Checklist

Before beginning an empirical multi-generation run, execute the following validation ladder:

```bash
# 1. Codebase hygiene and static typing
uv run ruff check .
uv run mypy src tests

# 2. Containment isolation under runsc
uv run pytest tests/containment/test_sandbox.py -v

# 3. Structured inference & fallback verification
uv run pytest tests/agents/test_inference.py -v

# 4. Full test suite execution
uv run pytest

# 5. Build and verify documentation
uv run --group docs mkdocs build --strict

# 6. Run short simulation smoke test
uv run evolzen run --ticks 50 --seed 42 --config configs/environment.yaml
```

---

## 7. Troubleshooting & Common Issues

| Symptom | Probable Cause | Remedy |
|---|---|---|
| `ImportError: VLLMBackend requires the 'gpu' extra` | Running under CPU profile | Run `uv sync --extra gpu`. Ensure CUDA drivers are installed on the host. |
| `runsc: command not found` | gVisor not installed or not in `$PATH` | Install gVisor per Section 3 and verify with `which runsc`. Set `runsc_path` in configuration if installed in non-standard location. |
| `gVisorSandbox: Operation not permitted (ptrace/kvm)` | Host virtualization or seccomp restriction | Ensure `/dev/kvm` exists and has proper permissions (`chmod 666 /dev/kvm`), or pass `--platform=ptrace` to `runsc`. |
| `CUDA out of memory in vLLM initialization` | `gpu_memory_utilization` set too high | Lower `gpu_memory_utilization` to `0.60` or use a smaller quantized model. |
| Agent action fallback triggered frequently | LLM generating malformed JSON or illegal action verbs | Check that the model is fine-tuned or instructed for JSON mode. Inspect prompts generated by `backend.build_prompt()`. |
