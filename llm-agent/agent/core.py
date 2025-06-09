"""Core components of the local LLM agent.

This module defines the ``LocalAgent`` class responsible for loading
configuration, managing short‑term memory and providing hooks for
processing user input and executing tools. Both the memory backend and
tool interface are designed to be easily replaced with more
sophisticated implementations in the future.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

import yaml


class LocalAgent:
    """Simple local LLM agent.

    Parameters
    ----------
    config_path:
        Optional path to the YAML configuration file. If omitted the
        default ``config/config.yaml`` relative to the project root is
        loaded.
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        if config_path is None:
            config_path = Path(__file__).resolve().parents[1] / "config" / "config.yaml"
        else:
            config_path = Path(config_path)

        with open(config_path, "r", encoding="utf-8") as f:
            self.config: dict[str, Any] = yaml.safe_load(f)

        # short-term memory buffer (ordered list of strings)
        self.memory: List[str] = []

    # ------------------------------------------------------------------
    # Placeholder interfaces
    # ------------------------------------------------------------------
    def process_input(self, text: str) -> str:
        """Process input text and return a dummy response."""
        # Future versions will call the LLM and utilize memory and tools
        self.memory.append(text)
        return "Processed: " + text

    def run_tool(self, name: str, input: str) -> str:
        """Execute a tool by name with the given input.

        This is currently a stub and always returns ``"Tool executed"``.
        """
        _ = name, input
        return "Tool executed"
