# Local LLM Agent

## Overview

This repository hosts an agent-based AI assistant designed to run entirely on-device, targeting Windows/Linux laptops equipped with an NVIDIA RTX 5080 (16 GB VRAM). The full codebase is collaboratively generated using ChatGPT’s Codex environment.

---

## Goals

* **Offline Inference**: Completely local execution with no external API calls after initial model download.
* **Modular Codebase**: All code generated through Codex, enabling iterative development via chat.
* **Performance**: ≤ 2 s initial latency, ≥ 30 tokens/s sustained throughput.
* **Reproducibility**: Single-command environment setup and comprehensive test suite.

---

## Model Choice

| Model                        | Params | License        | VRAM FP16 | VRAM Q4 | Notes                              |
| ---------------------------- | ------ | -------------- | --------- | ------- | ---------------------------------- |
| **Meta Llama-3 8B-Instruct** | 8 B    | Meta C-license | \~20 GB\* | 9–10 GB | Best instruction-following, 8k ctx |
| Mistral-7B-Instruct-v0.3     | 7 B    | Apache-2.0     | \~16 GB   | 7–8 GB  | Slightly faster, smaller context   |
| Phi-3-mini-4k-instruct       | 3.8 B  | MIT            | \~8 GB    | 4 GB    | Lightweight alternative            |

*\*Llama-3 8B loaded via 4-bit GPTQ or GGUF quantization fits within 16 GB VRAM comfortably.*

### Recommended Config

```yaml
model:
  name: llama-3-8b-instruct
  quantization: q4_0
  context_length: 8192
backend:
  engine: vllm
  dtype: fp16
```

---

## Technology Stack

| Component           | Choice                                      | Justification                    |
| ------------------- | ------------------------------------------- | -------------------------------- |
| **Inference**       | **vLLM** with CUDA ≥ 12.4                   | TensorRT kernels, paged KV-cache |
| Quantization        | GPTQ/GGUF via **AutoGPTQ** or **llama.cpp** | Optimizes VRAM usage             |
| **Agent Framework** | **LangGraph** (LangChain 1.2)               | Reliable ReAct/planning support  |
| Vector Store        | **FAISS** (IVF-Flat, on-disk)               | Efficient semantic retrieval     |
| Orchestrator        | **Typer CLI**, **FastAPI server**           | Easy CLI/API integration         |
| Testing             | **pytest**, **pytest-asyncio**              | Async-compatible testing         |

---

## Architecture

```plaintext
┌────────┐ query ┌─────────────┐ tool call ┌────────────┐
│ CLI/   │─────▶ │    AGENT    │─────────▶ │ Tool Suite │
│ HTTP   │◀───── │  (ReAct)    │◀───────── │ (search,   │
└────────┘ reply │             │ results   │ files etc.)│
      ▲          │ ┌───────┐   │           └────────────┘
      │          │ │MEMORY │   │
      │          │ └───────┘   │
      │          └─────┬───────┘
      │                │
      │          ┌─────▼──────┐
      └───────── │  LLM BACK  │
                 └────────────┘
```

* **Memory**: Short-term buffer + FAISS-based long-term store.
* **Tools**: Modular via entry points.

---

## Repository Structure

```plaintext
llm-agent/
├─ README.md
├─ pyproject.toml
├─ .env.example
├─ scripts/
│  └─ setup_gpu.ps1|sh
├─ config/
│  └─ config.yaml
├─ agent/
│  ├─ __init__.py
│  ├─ core.py
│  ├─ memory.py
│  ├─ tools.py
│  ├─ planner.py
│  └─ evaluator.py
├─ server/
│  ├─ __init__.py
│  └─ api.py
├─ cli.py
└─ tests/
   ├─ test_agent.py
   └─ test_tools.py
```

---

## Installation & Usage

```bash
# Setup
conda create -n llm-agent python=3.11 -y
conda activate llm-agent
pip install -r requirements.txt

# Model download & quantization
python -m scripts.download_weights --model meta-llama/Meta-Llama-3-8B-Instruct
python -m scripts.quantize --bits 4

# Run agent (CLI)
python cli.py

# Run HTTP server
uvicorn server.api:app --host 0.0.0.0 --port 11434
```

***Note:** CPU fallback occurs if VRAM < 10 GB.*

---

## Codex Integration Workflow

* Generate scaffolding via Codex prompts.
* Iteratively implement modules (`agent/core.py`, `tools.py`).
* Write unit tests and benchmarks directly in Codex.

---

## Performance

* Use vLLM paged KV-cache to limit memory usage.
* Compile model for best performance:

```bash
vllm.compile --model-dir ./models/llama3-8b-q4
```

* Activate Flash-Attention:

```bash
export VLLM_USE_FLASH_ATTENTION=1
```

---

## Roadmap

| Milestone | Objective                       |
| --------- | ------------------------------- |
| M1        | Repo setup & model runs locally |
| M2        | Agent passes unit tests         |
| M3        | Vector memory & RAG integration |
| M4        | CPU fallback support            |
| M5        | GUI integration (Electron/Qt)   |

---

## Licensing

* Llama-3 weights under Meta research license (commercial use with attribution).
* Code licensed under MIT.
* Verify compliance with third-party APIs.

---
