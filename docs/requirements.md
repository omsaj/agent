# Requirements

This document captures the functional and non‑functional requirements for the local LLM agent contained in this repository.

## Functional Requirements

1. **Offline Inference**
   - After the initial model download and setup the agent must not rely on external API calls for inference.
2. **Command Line Interface**
   - The project shall provide a CLI entry point that allows users to send queries to the agent and execute available tools.
3. **HTTP API**
   - A FastAPI server shall expose at least `/chat` and `/tool` endpoints.
4. **Tool Execution**
   - The agent must include a mechanism for registering tools. The repository currently provides an echo tool, a paper download tool and a PDF text extraction tool.
5. **Short‑Term Memory**
   - User prompts must be stored in a short‑term memory buffer so future prompts can be processed in context.
6. **Configuration File**
   - The agent must load settings from a YAML file located in the `config` directory by default.

## Non‑Functional Requirements

1. **Performance**
   - Initial response latency should be no more than two seconds and sustained generation throughput should be at least thirty tokens per second on a machine with an RTX 5080 GPU.
2. **Modularity**
   - Components such as the memory backend and tool interfaces should be simple to replace with more sophisticated implementations.
3. **Reproducibility**
   - The repository shall include a single‑command environment setup and tests runnable via `pytest`.

## Out of Scope

The current version does not implement the actual LLM inference logic. All responses are placeholders and further development is required to integrate a model backend, vector memory and planning capabilities.
