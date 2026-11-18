# ADR 0009: Unified Vision-Language Base Model with Multi-Tier LoRA/DoRA Adapters

**Status:** Decided & Scaffolding Implemented (empirically **untested** in hardware pilot runs per AGENTS.md §5)

## Context

EvolZen agents require two distinct cognitive modalities during simulation:
1. **Tier-1 Tactical Action Selection:** Low-latency (<15 ms), high-frequency turn-by-turn action proposals constrained to strict JSON schemas (`Action` grammar) based on immediate spatial observations, current motive weights, and candidate legal sets.
2. **Tier-2 Deliberative Planning & Rule Synthesis:** Deeper, lower-frequency chain-of-thought exploration, social contract drafting, and executable rule synthesis inside the gVisor sandbox.

Previously considered options:
- **Dual-Model Deployment:** Running a small fast LLM (e.g., Qwen 2.5 3B/7B) for Tier 1 and a separate reasoning model (e.g., DeepSeek-R1 Distill 8B) for Tier 2. This requires $\ge 18\text{ GB}$ VRAM, evicts weights or causes high-latency PCIe model swaps ($\ge 2.5\text{ s}$ per tier switch), and lacks native visual grounding for the 3D grid and elevation slices.
- **Pure Text LLM without Vision:** Text-only models require serializing 2D/3D voxel grids and minimap projections into hundreds of coordinate tokens, inflating the context window and degrading spatial reasoning precision.

## Decision

Adopt a **single unified vision-language base model with multi-tier in-memory adapters**:

1. **Shared Base Model:**
   - **`Qwen/Qwen3.5-9B-VL-AWQ`** (8.90B parameters, quantized to 8-bit AWQ `W8A16`).
   - Retains 3D Multimodal Rotary Positional Embeddings (mRoPE) across $(\Delta t, \Delta y, \Delta x)$, aligning visual patches directly with the simulation's spatial grid and `GroundedJEPAEncoder` latent space ($z \in \mathbb{R}^{32}$).
   - 8-bit AWQ preserves 256 quantization bins (vs. 16 bins for 4-bit), avoiding visual feature outlier clipping and retaining sub-pixel coordinate grounding.

2. **Multi-Tier Adapter Topology:**
   - **Tier-1 Adapter (Tactical Action):** Standard LoRA ($r=8, \alpha=16, \sim 43\text{ MB}$) for constrained, direct-emission JSON action selection ($\le 256$ tokens, temperature $0.4$).
   - **Tier-2 Adapter (Deliberative Planning):** Weight-Decomposed Low-Rank Adaptation (**DoRA**; Liu et al., ICML 2024, arXiv:2402.09353; $r=16, \alpha=32$ with learnable magnitude vector $m$, $\sim 86.5\text{ MB}$) fine-tuned on distilled DeepSeek-R1 reasoning traces ($\le 2048$ tokens, temperature $0.7$, `<deliberate>` tags).
   - **Tier-0 Edge Fallback:** `Qwen/Qwen2.5-3B-Instruct-AWQ` or deterministic numerical Chebyshev heuristic for CPU-only environments.

3. **In-Memory Zero-Copy Tier Switching:**
   - Both adapters are loaded into vLLM concurrently via `--enable-lora` multi-adapter serving.
   - Tier switching is an in-memory pointer swap ($<5\text{ ms}$ overhead), eliminating GPU VRAM reloading.
   - Total VRAM footprint for weights is $9.78\text{ GB}$, comfortably scaling up to 30 agents with PagedAttention KV caches on 16GB–24GB commodity GPUs.

## Consequences

### Positive
- **Hardware Feasibility:** Whole multi-agent population runs on a single consumer GPU (11.12 GB for 10 agents on 12GB RTX 4070; 13.81 GB for 30 agents on 16GB/24GB GPUs).
- **Shared Spatial Context:** Both tactical actions and deliberative plans share the identical spatial vision encoder representation.
- **Modular Upgrades:** Lineages train private LoRA/DoRA adapters independently without altering base model weights.

### Negative / Trade-offs
- Requires `vllm` with Multi-LoRA support (`--enable-lora`) for concurrent adapter serving.
- DoRA training requires specialized decomposition hooks in `evolzen.agents.trainer.OfflineAdapterTrainer`.
- All neural inference and latency claims remain strictly design derivations until Phase 1.2 empirical benchmarks are executed.
