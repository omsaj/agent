"""Core components of the local LLM agent.

This module defines the ``LocalAgent`` class responsible for loading
configuration, managing short‑term memory and providing hooks for
processing user input and executing tools. Both the memory backend and
the tool interface are intentionally simple so they can be replaced by
more complex implementations later on.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List

from agent.tools import EchoTool, PaperDownloadTool, PDFExtractTool

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

        # very short‑term memory buffer (ordered list of strings)
        self.memory: List[str] = []

        # available tools by name
        self.tools = {
            "echo": EchoTool(),
            "download_papers": PaperDownloadTool(),
            "pdf_extract": PDFExtractTool(),
        }

    # ------------------------------------------------------------------
    # Placeholder interfaces
    # ------------------------------------------------------------------
    def process_input(self, text: str) -> str:
        """Process a piece of text and return a dummy response."""
        # In the future this will call the LLM and integrate memory and tools.
        self.memory.append(text)
        return "Processed: " + text

    def run_tool(self, name: str, input: str) -> str:
        """Execute a tool by name with the given input.

        Look up the tool by ``name`` and run it with ``input`` if available.
        """
        tool = self.tools.get(name)
        if tool is None:
            return "Tool not found"
        return tool.run(input)
