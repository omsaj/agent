"""Tool definitions for the local agent."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Tool(ABC):
    """Base interface for agent tools."""

    name: str
    description: str

    @abstractmethod
    def run(self, input: str) -> str:
        """Run the tool using ``input`` and return its result."""
        raise NotImplementedError


class EchoTool(Tool):
    """Tool that simply echoes the provided input."""

    name = "echo"
    description = "Return the input text prefixed with 'Echo:'"

    def run(self, input: str) -> str:
        """Return ``input`` wrapped in an echo string."""
        return f"Echo: {input}"
